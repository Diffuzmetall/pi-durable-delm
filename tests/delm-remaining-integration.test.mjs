import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync, spawn } from 'node:child_process';
import { once } from 'node:events';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai/providers/faux';
import { Harness, createRegistry } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';
import { createDelmWait, DelmWaitDoc, readBoard, wakeRequestId } from '../extensions/delm/index.js';

const project = new URL('../', import.meta.url).pathname;
async function until(check) {
  const deadline = Date.now() + 10000;
  while (!await check()) {
    if (Date.now() > deadline) throw Error('condition timed out');
    await new Promise(resolve => setTimeout(resolve, 15));
  }
}

test('eight fixture identities: actual HTTP + native/faux early reuse, lease handoff, failure/correction and next output', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'delm-remaining-e2e-'));
  let host, server;
  try {
    const workspace = join(directory, 'shared'), run = join(directory, 'run');
    await mkdir(workspace);
    execFileSync('python3', [join(project, 'scripts/delm_local.py'), 'init', run,
      '--shared-workspace', workspace, '--n', '8', '--task', 'deterministic integration']);
    server = spawn('python3', [join(project, 'scripts/delm_local.py'), 'serve', run], { stdio: ['ignore', 'pipe', 'pipe'] });
    await once(server.stdout, 'data');
    let request = 0;
    const domain = (actor, payload) => JSON.parse(execFileSync(join(run, actor, 'bin/context'),
      ['domain', JSON.stringify({ request_id: `e2e-${++request}`, ...payload })], { encoding: 'utf8' }));
    const create = (subject, deps = []) => domain('alice', { op: 'create', subject, detail: 'shared output', deps }).task;
    const claim = (actor, task) => domain(actor, { op: 'claim', item: task.id, expected_revision: task.revision }).task;
    const owned = (actor, op, task, args = {}) => domain(actor, { op, item: task.id, expected_revision: task.revision, generation: task.generation, ...args });
    let output = claim('alice', create('early contract'));
    const faux = fauxProvider(), models = createModels(), registry = createRegistry(), admissions = [], transcripts = [];
    models.setProvider(faux.provider);
    registry.install(createDelmWait({ run, actor: 'heidi', admitInput: async (_conversation, id) => admissions.push(id) }));
    host = await Harness.open(await openNodeSqliteStorage(join(directory, 'native.sqlite')), { registry, models }, context);
    const root = await host.root(context, { agent: { model: { provider: 'faux', modelId: 'faux-1' } } });
    host.resume();
    const doc = () => host.snapshot(DelmWaitDoc, root.id, context);
    const tool = registry.snapshot().extension('delm').tools[0];
    const direct = async (args, key) => (await tool.execute(args, { taskId: key, callId: key, conversationId: root.id,
      commit: fn => host.commit(fn, context) }, context)).structuredOutput.result;
    let ackedThrough = 0;
    const readAndAckWake = async (entry, inspectView) => {
      const sent = (await doc()).waits[entry.id];
      assert.equal(sent.state, 'sent');
      assert.equal(sent.acked, false, 'accepting a compact reference is not reading its body');
      assert.equal(sent.deliveryState, 'awaiting-read');
      const pending = domain('heidi', { op: 'pending' }).receipts;
      assert.equal(pending.length, 1);
      assert.equal(pending[0].receipt_id, sent.receipt.receipt_id);
      assert.equal(sent.receipt.request_id, wakeRequestId(entry.taskId));
      const receipt = domain('heidi', { op: 'snapshot', request_id: sent.receipt.request_id });
      assert.deepEqual(receipt, pending[0], 'consumer replays the exact saved immutable receipt');
      assert.equal(receipt.actor, 'heidi');
      assert.equal(receipt.from_sequence, ackedThrough, 'notification did not advance the actor cursor');
      assert.ok(Array.isArray(receipt.view.queue));
      inspectView(receipt.view); // Inspect the needed evidence BEFORE explicitly acknowledging it.
      const ack = domain('heidi', { op: 'ack', request_id: `${receipt.request_id}:ack`, receipt_id: receipt.receipt_id });
      assert.equal(ack.actor, 'heidi'); assert.equal(ack.acked_sequence, receipt.to_sequence);
      ackedThrough = ack.acked_sequence;
      assert.equal(domain('heidi', { op: 'pending' }).receipts.length, 0);
      const status = (await direct({ action: 'status' }, `status-${entry.id}`)).find(wait => wait.id === entry.id);
      assert.equal(status.state, 'sent'); assert.equal(status.acked, true); assert.equal(status.deliveryState, 'acked');
      return receipt;
    };
    faux.setResponses([
      fauxAssistantMessage(fauxToolCall('delm_wait', { action: 'wait', items: [output.id], reason: 'consume usable contract' }), { stopReason: 'toolUse' }),
      fauxAssistantMessage('waiting'),
    ]);
    await (await root.submit({ type: 'input', content: 'wait for shared contract' }, context)).wait(context);
    const first = Object.values((await doc()).waits)[0];
    assert.equal(first.state, 'waiting');
    await writeFile(join(workspace, 'contract.txt'), 'shared usable contract');
    faux.setResponses([transcript => { transcripts.push(transcript); return fauxAssistantMessage('use early contract'); }]);
    output = owned('alice', 'complete', output, { summary: 'contract verified' }).task;
    const remainder = claim('alice', create('producer remainder'));
    await until(async () => (await doc()).waits[first.id].state === 'sent' && transcripts.length === 1);
    assert.equal(await readFile(join(workspace, 'contract.txt'), 'utf8'), 'shared usable contract');
    assert.equal(readBoard(run).tasks[remainder.id].state, 'claimed');
    await readAndAckWake(first, view => {
      assert.equal(view.queue.find(task => task.id === output.id).state, 'done');
    });
    assert.ok((await doc()).waits[first.id].receipt.receipt_id);
    assert.equal((await doc()).waits[first.id].acked, true);
    const consumer = claim('bob', create('reuse then handoff', [output.id]));
    const lease = domain('bob', { op: 'lease-acquire', task: consumer.id, generation: consumer.generation,
      paths: ['contract.txt'], resources: ['build:index'], ttl: 300 }).lease;
    const handed = owned('bob', 'handoff', consumer, { to: 'heidi', summary: 'same shared artifact' }).task;
    const transferred = domain('bob', { op: 'lease-handoff', task: handed.id, generation: handed.generation,
      lease_id: lease.lease_id, to: 'heidi', ttl: 300 }).lease;
    assert.equal(transferred.owner, 'heidi');
    assert.equal(domain('eve', { op: 'projection' }).agents.length, 8);
    let next = claim('carol', create('next output'));
    const second = await direct({ action: 'wait', items: [next.id], reason: 'need next output' }, 'second');
    domain('frank', { op: 'publish', type: 'FACT', text: 'unrelated' });
    await new Promise(resolve => setTimeout(resolve, 80));
    assert.equal(admissions.length, 1);
    faux.setResponses([transcript => { transcripts.push(transcript); return fauxAssistantMessage('reevaluate linked failure'); }]);
    const failure = domain('dave', { op: 'publish', type: 'FAIL', text: 'next output invalid', task: next.id }).publication;
    await until(async () => (await doc()).waits[second.id].state === 'sent' && transcripts.length === 2);
    assert.equal((await doc()).waits[second.id].trigger.kind, 'reevaluate');
    const message = JSON.stringify(transcripts[1]);
    assert.match(message, /NOT successful readiness/);
    assert.match(message, /REEVALUATE-NOT-READY/);
    assert.doesNotMatch(message, /next output invalid/, 'full failure body is not in the compact reference');
    await readAndAckWake(second, view => {
      const linked = view.blockers.find(note => note.id === failure.id);
      assert.ok(linked); assert.equal(linked.task, next.id); assert.equal(linked.text, 'next output invalid');
      assert.notEqual(view.queue.find(task => task.id === next.id).state, 'done', 'informational wake is not readiness');
    });
    domain('carol', { op: 'publish', type: 'CORRECTION', text: 'producer repaired output', task: next.id, resolves: [failure.id] });
    const third = await direct({ action: 'wait', items: [next.id], reason: 'corrected output must still finish' }, 'third');
    assert.equal(third.state, 'waiting');
    faux.setResponses([transcript => { transcripts.push(transcript); return fauxAssistantMessage('corrected output ready'); }]);
    next = owned('carol', 'complete', next, { summary: 'corrected and verified' }).task;
    await until(async () => (await doc()).waits[third.id].state === 'sent' && transcripts.length === 3);
    assert.equal((await doc()).waits[third.id].trigger.kind, 'ready');
    await readAndAckWake(third, view => {
      assert.equal(view.queue.find(task => task.id === next.id).state, 'done');
      assert.ok(view.notes.some(note => note.type === 'CORRECTION' && note.resolves.includes(failure.id)));
      assert.ok(!view.blockers.some(note => note.id === failure.id));
    });
    assert.deepEqual(admissions, [first, second, third].map(entry => wakeRequestId(entry.taskId)));
    assert.equal(domain('heidi', { op: 'pending' }).receipts.length, 0);
    domain('heidi', { op: 'lease-release', task: handed.id, generation: handed.generation, lease_id: lease.lease_id });
    assert.equal(owned('heidi', 'complete', handed, { summary: 'consumer verified shared candidate' }).task.state, 'done');
    assert.equal(readBoard(run).tasks[remainder.id].state, 'claimed', 'partial output is not parent DONE');
    const abandoned = claim('grace', create('salvage checkpoint'));
    const fourth = await direct({ action: 'wait', items: [abandoned.id], reason: 'wait for checkpoint owner' }, 'fourth');
    domain('grace', { op: 'lifecycle', state: 'idle', reason: 'turn ended, producer still alive', expected_generation: 0 });
    await new Promise(resolve => setTimeout(resolve, 80));
    assert.equal(admissions.length, 3, 'idle/turn-end is not producer death');
    faux.setResponses([transcript => { transcripts.push(transcript); return fauxAssistantMessage('reconcile ended producer'); }]);
    const ended = domain('grace', { op: 'lifecycle', state: 'ended', reason: 'explicit fixture producer termination', expected_generation: 1 });
    await until(async () => (await doc()).waits[fourth.id].state === 'sent' && transcripts.length === 4);
    assert.equal((await doc()).waits[fourth.id].trigger.kind, 'reevaluate');
    await readAndAckWake(fourth, view => {
      assert.equal(view.sessions.find(session => session.actor === 'grace').state, 'ended');
      const task = view.queue.find(task => task.id === abandoned.id);
      assert.equal(task.state, 'blocked'); assert.ok(task.generation > abandoned.generation);
    });
    const blocked = readBoard(run).tasks[abandoned.id];
    assert.equal(blocked.state, 'blocked');
    assert.throws(() => owned('grace', 'complete', abandoned, { summary: 'stale producer write' }));
    const salvaged = domain('frank', { op: 'reclaim', item: blocked.id, expected_revision: blocked.revision,
      generation: blocked.generation, producer_generation: ended.lifecycle.generation,
      acknowledge_external_writes: true, summary: 'inspected shared inputs; external writer risk acknowledged' }).task;
    assert.equal(salvaged.owner, 'frank');
    assert.ok(salvaged.generation > blocked.generation);
    const fifth = await direct({ action: 'wait', items: [salvaged.id], reason: 'need salvaged verified checkpoint' }, 'fifth');
    faux.setResponses([transcript => { transcripts.push(transcript); return fauxAssistantMessage('salvage verified'); }]);
    owned('frank', 'complete', salvaged, { summary: 'reconciled without lost files' });
    await until(async () => (await doc()).waits[fifth.id].state === 'sent' && transcripts.length === 5);
    assert.equal((await doc()).waits[fifth.id].trigger.kind, 'ready');
    await readAndAckWake(fifth, view => {
      const task = view.queue.find(task => task.id === salvaged.id);
      assert.equal(task.state, 'done'); assert.equal(task.owner, 'frank'); assert.equal(task.generation, salvaged.generation);
    });
    assert.equal(domain('heidi', { op: 'pending' }).receipts.length, 0);
    assert.deepEqual(admissions, [first, second, third, fourth, fifth].map(entry => wakeRequestId(entry.taskId)));
    assert.equal(await readFile(join(workspace, 'contract.txt'), 'utf8'), 'shared usable contract');
  } finally {
    if (host) await host.close(context);
    if (server && server.exitCode === null) { const closed = once(server, 'close'); server.kill('SIGTERM'); await closed; }
    await rm(directory, { recursive: true, force: true });
  }
});
