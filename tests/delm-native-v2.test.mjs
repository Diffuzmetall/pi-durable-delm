import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rename, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync, spawn } from 'node:child_process';
import { once } from 'node:events';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage } from '@earendil-works/pi-ai/providers/faux';
import { Harness, createRegistry } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';
import { createDelmWait, DelmWaitDoc, projectEvents, waitTrigger, readBoard, wakeRequestId, wakeMessage } from '../extensions/delm/index.js';

const project = new URL('../', import.meta.url).pathname;
async function until(check) {
  const deadline = Date.now() + 10000;
  while (!await check()) {
    if (Date.now() > deadline) throw Error('condition timed out');
    await new Promise(resolve => setTimeout(resolve, 15));
  }
}

// Python owns the canonical projection; compare whole values rather than selected fields.
test('canonical Python/JS conformance includes full task replacements, legacy and sticky resolution', () => {
  const task = { id: 'a', subject: 'contract', detail: 'output', state: 'blocked', owner: 'alice', generation: 3,
    revision: 999, deps: [], criteria: ['usable'], parent: null, outputs: ['out'], mapping: {}, handoff: 'salvage' };
  const bodies = [
    ['session', { actor: 'alice', state: 'starting' }], ['status', { text: 'active' }],
    ['item', { id: 'a', subject: 'contract', detail: 'output' }], ['claim', { item: 'a' }],
    ['done', { item: 'a', summary: 'early output' }], ['task', { task }],
    ['publication', { id: 'fail', type: 'FAIL', text: 'broken', task: 'a', related: [], resolves: [] }],
    ['publication', { id: 'repair', type: 'CORRECTION', text: 'fixed', task: 'a', related: [], resolves: ['fail'] }],
    ['task', { task: { ...task, id: 'out', outputs: [], parent: 'a' } }],
    ['publication', { id: 'output-fail', type: 'FAIL', text: 'child revoked', task: null, output: 'out', related: [], resolves: [] }],
    ['note', { id: 'old-fail', type: 'FAIL', text: 'legacy blocker' }],
    ['lifecycle', { actor: 'alice', state: 'ended', reason: 'explicit stop', generation: 2 }],
    ['session', { actor: 'alice', state: 'starting' }],
    ['body', { id: 'a', files: [{ path: 'contract.md', hash: 'fixture-hash' }] }],
    ['body', { id: 'old-fail', files: [{ path: 'failure.log', hash: 'fixture-failure' }] }],
    ['read', { via: 'read', view: { privateNestedView: 'not forwarded' } }], ['unknown', { retained: true }],
  ];
  const rows = bodies.map(([kind, payload], i) => ({ sequence: i + 1, actor: 'alice', kind, payload }));
  const python = JSON.parse(execFileSync('python3', ['-c',
    `import sys,json;sys.path.insert(0,${JSON.stringify(join(project, 'scripts'))});from delm_domain import project_events;print(json.dumps(project_events(json.load(sys.stdin),['alice','bob'])))`],
    { input: JSON.stringify(rows), encoding: 'utf8' }));
  assert.deepEqual(projectEvents(rows, ['alice', 'bob']), python);
  assert.equal(python.sessions[0].generation, 2); assert.equal(python.sessions[0].state, 'ended');
  assert.equal(python.queue.find(x => x.id === 'a').files[0].path, 'contract.md');
  assert.equal(python.notes.find(x => x.id === 'old-fail').files[0].path, 'failure.log');
  const snapshot = { ...python, tasks: Object.fromEntries(python.queue.map(x => [x.id, x])) };
  assert.equal(waitTrigger({ items: ['a'], sequence: 0 }, snapshot).kind, 'reevaluate');
});

async function fixture(n = 4) {
  const directory = await mkdtemp(join(tmpdir(), 'delm-v2-native-'));
  const source = join(directory, 'source'), run = join(directory, 'board');
  await mkdir(source);
  execFileSync('python3', [join(project, 'scripts/delm_local.py'), 'init', run, '--shared-workspace', source, '--n', String(n), '--task', 'fixture']);
  const server = spawn('python3', [join(project, 'scripts/delm_local.py'), 'serve', run], { stdio: ['ignore', 'pipe', 'pipe'] });
  await once(server.stdout, 'data');
  let request = 0;
  const domain = (actor, payload) => JSON.parse(execFileSync(join(run, actor, 'bin/context'), ['domain', JSON.stringify({ request_id: `test-${++request}`, ...payload })], { encoding: 'utf8' }));
  const task = domain('alice', { op: 'create', subject: 'needed', detail: 'output', criteria: ['usable'] });
  // Operation responses carry the task directly (or under task on compatible wrappers).
  const item = (task.task ?? task).id;
  let current = readBoard(run).tasks[item];
  domain('alice', { op: 'claim', item, expected_revision: current.revision });
  const faux = fauxProvider(), models = createModels(); models.setProvider(faux.provider);
  const registry = createRegistry(), admissions = [];
  let deny = false, host, root, afterAdmission;
  registry.install(createDelmWait({ run, actor: 'bob', admitInput: async (_conversation, id) => {
    admissions.push(id); if (deny) throw Error('denied');
    await afterAdmission?.(_conversation);
  } }));
  const storage = join(directory, 'native.sqlite');
  async function open() {
    host = await Harness.open(await openNodeSqliteStorage(storage), { registry, models }, context);
    root = await host.root(context, { agent: { model: { provider: 'faux', modelId: 'faux-1' } } }); host.resume();
  }
  await open();
  const doc = () => host.snapshot(DelmWaitDoc, root.id, context);
  const tool = registry.snapshot().extension('delm').tools[0];
  const direct = async (args, key = 'arm') => (await tool.execute(args, { taskId: key, callId: key, conversationId: root.id,
    commit: fn => host.commit(fn, context) }, context)).structuredOutput.result;
  return { run, item, domain, admissions, faux, doc, direct, get host() { return host; }, get root() { return root; },
    deny(value) { deny = value; },
    afterAdmit(callback) { afterAdmission = callback; },
    complete() { current = readBoard(run).tasks[item]; return domain('alice', { op: 'complete', item,
      expected_revision: current.revision, generation: current.generation, summary: 'verified' }); },
    async reopen() { await host.close(context); await open(); },
    legacyInline() {
      // Seed the historical accepted-full-inline checkpoint using SDK writes, not Native SQL.
      afterAdmission = conversation => {
        const submit = conversation.submit;
        conversation.submit = async (input, callContext) => {
          const receipt = domain('bob', { op: 'snapshot', request_id: input.requestId });
          await host.commit(async tx => {
            const entry = Object.values((await tx.doc(DelmWaitDoc, root.id)).waits)
              .find(wait => wakeRequestId(wait.taskId) === input.requestId);
            entry.receipt = receipt; delete entry.deliveryMode;
          }, context);
          return submit.call(conversation, { ...input, content: `[delm] Legacy full-inline receipt: ${JSON.stringify(receipt)}` }, callContext);
        };
      };
    },
    async breakAckOnce() {
      const path = join(run, 'bob/bin/context'); await rename(path, `${path}.real`);
      await writeFile(path, `#!/usr/bin/env python3\nimport sys,os,json\nmarker=${JSON.stringify(join(run, 'ack-fault'))}\nif len(sys.argv)>2 and sys.argv[1]=='domain' and json.loads(sys.argv[2]).get('op')=='ack' and not os.path.exists(marker):\n open(marker,'w').close();sys.exit(9)\nos.execv(${JSON.stringify(`${path}.real`)},[${JSON.stringify(`${path}.real`)},*sys.argv[1:]])\n`, { mode: 0o700 });
    },
    async close() { await host.close(context); server.kill('SIGTERM'); await once(server, 'close'); await rm(directory, { recursive: true, force: true }); },
  };
}

test('compact ready and reevaluate messages bound Unicode reasons/IDs without truncating replay identity', () => {
  const entry = { items: Array.from({ length: 20 }, (_, i) => `${i}${'🧪'.repeat(127)}`), reason: 'NOT_FOR_INPUT'.repeat(1000),
    receipt: { receipt_id: 'a'.repeat(32), request_id: `delm-wake:${'9'.repeat(180)}`, actor: 'bob',
      from_sequence: 1, to_sequence: 999999, view: { queue: ['MUST_NOT_APPEAR'] } } };
  for (const kind of ['ready', 'reevaluate', 'work']) {
    const message = wakeMessage(entry, { kind, reason: '🧪'.repeat(1000), tasks: entry.items, publications: Array(70).fill('publication') });
    assert.ok(Buffer.byteLength(message, 'utf8') <= 2048);
    assert.ok(message.includes(entry.receipt.request_id)); assert.ok(message.includes(entry.receipt.receipt_id));
    assert.doesNotMatch(message, /NOT_FOR_INPUT|MUST_NOT_APPEAR|"view"|"queue"/);
    assert.match(message, kind === 'work' ? /WORK AVAILABLE/ : kind === 'ready' ? /READY:/ : /REEVALUATE-NOT-READY:/);
  }
});

test('compact reference for large persisted receipt stays unread until explicit CLI replay/read/ack', async t => {
  const f = await fixture();
  let wake;
  try {
    for (let i = 0; i < 70; i++) f.domain('alice', { op: 'create', subject: `other-${i}`,
      detail: 'QUEUE_BODY_NEVER_INLINE_'.repeat(160) });
    f.afterAdmit(conversation => {
      const submit = conversation.submit;
      conversation.submit = async (input, callContext) => {
        wake = input.content;
        return submit.call(conversation, input, callContext);
      };
    });
    const entry = await f.direct({ action: 'wait', items: [f.item], reason: 'д'.repeat(1000) });
    f.faux.setResponses([fauxAssistantMessage('will explicitly read receipt')]); f.complete();
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    assert.ok(Buffer.byteLength(wake, 'utf8') <= 2048, `wake is ${Buffer.byteLength(wake, 'utf8')} UTF8 bytes`);
    assert.doesNotMatch(wake, /QUEUE_BODY_NEVER_INLINE_|"view"|"queue"|"events"/);
    assert.match(wake, /READY/);
    const requestId = wakeRequestId(entry.taskId);
    assert.ok(wake.includes(requestId)); assert.match(wake, /context domain/);
    const pending = f.domain('bob', { op: 'pending' }).receipts;
    assert.equal(pending.length, 1, 'accepted reference must not consume unread body');
    const receipt = f.domain('bob', { op: 'snapshot', request_id: requestId });
    assert.ok(Buffer.byteLength(JSON.stringify(receipt)) > 200000, 'actual persisted receipt is large');
    t.diagnostic(`wake_utf8_bytes=${Buffer.byteLength(wake, 'utf8')} persisted_receipt_utf8_bytes=${Buffer.byteLength(JSON.stringify(receipt), 'utf8')} queue_tasks=${receipt.view.queue.length}`);
    assert.deepEqual(receipt, pending[0]); assert.equal(receipt.view.queue.length, 71);
    let status = (await f.direct({ action: 'status' }, 'before-read-ack')).find(x => x.id === entry.id);
    assert.equal(status.state, 'sent'); assert.equal(status.acked, false); assert.equal(status.deliveryState, 'awaiting-read');
    assert.equal(status.receipt.view, undefined, 'status returns references, not full bodies');
    const accepted = await f.host.commit(tx => tx.submissionByRequest(f.root.id, requestId), context);
    await f.reopen(); await f.direct({ action: 'retry', id: entry.id }, 'sent-retry');
    assert.equal(f.admissions.length, 1); assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 1);
    const same = await f.host.commit(tx => tx.submissionByRequest(f.root.id, requestId), context);
    assert.deepEqual(same, accepted);
    // The receipt above has been read by this simulated consumer before the explicit ack.
    f.domain('bob', { op: 'ack', receipt_id: receipt.receipt_id });
    assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 0);
    status = (await f.direct({ action: 'status' }, 'after-read-ack')).find(x => x.id === entry.id);
    assert.equal(status.acked, true); assert.equal(status.deliveryState, 'acked');
    assert.deepEqual(f.domain('bob', { op: 'snapshot', request_id: requestId }), receipt);
  } finally { await f.close(); }
});

test('real HTTP snapshot -> native denial -> reopen/retry -> submit -> ack retains unread and stable identity', async () => {
  const f = await fixture();
  try {
    f.deny(true);
    const entry = await f.direct({ action: 'wait', items: [f.item], reason: 'need output' });
    f.complete();
    await until(async () => (await f.doc()).waits[entry.id].state === 'failed');
    const failed = (await f.doc()).waits[entry.id]; assert.ok(failed.receipt.receipt_id);
    assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 1);
    await f.reopen(); f.deny(false); f.faux.setResponses([fauxAssistantMessage('resumed')]);
    await f.direct({ action: 'retry', id: entry.id }, 'retry');
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    const sent = (await f.doc()).waits[entry.id]; assert.equal(sent.requestId, wakeRequestId(entry.taskId)); assert.equal(sent.acked, false);
    assert.equal(sent.deliveryState, 'awaiting-read');
    assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 1);
    const read = f.domain('bob', { op: 'snapshot', request_id: wakeRequestId(entry.taskId) });
    assert.ok(read.view.queue.some(task => task.id === f.item && task.state === 'done'));
    f.domain('bob', { op: 'ack', receipt_id: read.receipt_id });
    assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 0);
    const status = (await f.direct({ action: 'status' }, 'after-ack')).find(wait => wait.id === entry.id);
    assert.equal(status.acked, true); assert.equal(status.deliveryState, 'acked');
    assert.deepEqual(f.admissions, [wakeRequestId(entry.taskId), wakeRequestId(entry.taskId)]);
  } finally { await f.close(); }
});

test('accepted compact reference survives lost submit response/reopen/retry without autoACK or duplicate input', async () => {
  const f = await fixture();
  try {
    f.afterAdmit(conversation => {
      const submit = conversation.submit;
      conversation.submit = async (input, callContext) => {
        await submit.call(conversation, input, callContext);
        throw Error('fixture loses response after accepted reference');
      };
    });
    const entry = await f.direct({ action: 'wait', items: [f.item], reason: 'need output' });
    f.faux.setResponses([fauxAssistantMessage('reference accepted once')]); f.complete();
    await until(async () => (await f.doc()).waits[entry.id].state === 'failed');
    const requestId = wakeRequestId(entry.taskId);
    const accepted = await f.host.commit(tx => tx.submissionByRequest(f.root.id, requestId), context);
    assert.ok(accepted); assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 1);
    await f.reopen(); await f.direct({ action: 'retry', id: entry.id }, 'retry-lost-reference');
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    const status = (await f.direct({ action: 'status' }, 'reference-recovered')).find(wait => wait.id === entry.id);
    assert.equal(status.deliveryState, 'awaiting-read'); assert.equal(status.acked, false);
    assert.equal(f.admissions.length, 1);
    assert.deepEqual(await f.host.commit(tx => tx.submissionByRequest(f.root.id, requestId), context), accepted);
    const read = f.domain('bob', { op: 'snapshot', request_id: requestId });
    assert.ok(read.view.queue.some(task => task.id === f.item && task.state === 'done'));
    f.domain('bob', { op: 'ack', receipt_id: read.receipt_id });
    assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 0);
  } finally { await f.close(); }
});

test('legacy accepted full-inline: submit-before-ack transport loss retries without duplicate continuation or admission', async () => {
  const f = await fixture();
  try {
    await f.breakAckOnce(); f.legacyInline();
    const upstream = f.domain('alice', { op: 'create', subject: 'upstream', detail: 'optional prior interface' });
    const upstreamId = (upstream.task ?? upstream).id;
    let current = readBoard(f.run).tasks[f.item];
    f.domain('alice', { op: 'update', item: f.item, expected_revision: current.revision, generation: current.generation,
      changes: { deps: [upstreamId] } });
    const entry = await f.direct({ action: 'wait', items: [f.item], reason: 'need output' });
    f.faux.setResponses([fauxAssistantMessage('resumed once')]);
    f.domain('alice', { op: 'publish', type: 'FAIL', text: 'prior interface invalid', task: upstreamId });
    await until(async () => (await f.doc()).waits[entry.id].state === 'failed');
    const accepted = await f.host.commit(tx => tx.submissionByRequest(f.root.id, wakeRequestId(entry.taskId)), context);
    assert.ok(accepted); assert.equal(f.admissions.length, 1);
    current = readBoard(f.run).tasks[f.item];
    f.domain('alice', { op: 'update', item: f.item, expected_revision: current.revision, generation: current.generation,
      changes: { deps: [] } });
    assert.equal(waitTrigger((await f.doc()).waits[entry.id], readBoard(f.run)), null, 'original FAIL no longer affects consumer');
    const cancel = await f.direct({ action: 'cancel', id: entry.id }, 'cancel'); assert.equal(cancel.cancelRefused, true);
    await f.reopen(); await f.direct({ action: 'retry', id: entry.id }, 'retry');
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    assert.equal(f.admissions.length, 1); assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 0);
    assert.equal((await f.doc()).waits[entry.id].acked, true, 'legacy inline body was actually accepted before ack');
  } finally { await f.close(); }
});

test('final dispatch is cancel-fenced and persists a FAIL arriving during trusted admission as reevaluation', async () => {
  const f = await fixture();
  let release, input;
  const gate = new Promise(resolve => { release = resolve; });
  try {
    const entry = await f.direct({ action: 'wait', items: [f.item], reason: 'need output' });
    f.afterAdmit(conversation => {
      f.domain('alice', { op: 'publish', type: 'FAIL', text: 'revoked during admission', task: f.item });
      const originalSubmit = conversation.submit;
      conversation.submit = async (submission, callContext) => {
        input = submission; await gate;
        return originalSubmit.call(conversation, submission, callContext);
      };
    });
    f.faux.setResponses([fauxAssistantMessage('reevaluating revocation')]); f.complete();
    await until(async () => input || (await f.doc()).waits[entry.id].state === 'failed');
    assert.ok(input, JSON.stringify((await f.doc()).waits[entry.id]));
    assert.match(input.content, /reevaluation required, NOT successful readiness/);
    assert.equal((await f.doc()).waits[entry.id].trigger.kind, 'reevaluate');
    const cancel = await f.direct({ action: 'cancel', id: entry.id }, 'cancel-during-dispatch');
    assert.equal(cancel.cancelRefused, true); assert.equal(cancel.accepted, false); assert.equal(cancel.dispatchCommitted, true);
    release();
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    assert.equal(f.admissions.length, 1);
  } finally { release(); await f.close(); }
});

test('available-work predicate does not change exact dependencies or let unrelated FAIL stop independent work', () => {
  const rows = [
    { sequence: 1, actor: 'alice', kind: 'task', payload: { task: { id: 'a', state: 'claimed', owner: 'alice', generation: 1, deps: [], outputs: [] } } },
    { sequence: 2, actor: 'alice', kind: 'task', payload: { task: { id: 'b', state: 'open', owner: null, generation: 0, deps: [], outputs: [] } } },
    { sequence: 3, actor: 'alice', kind: 'publication', payload: { id: 'fail-a', type: 'FAIL', task: 'a', related: [] } },
  ];
  const view = projectEvents(rows, ['alice', 'bob']);
  const snapshot = { ...view, tasks: Object.fromEntries(view.queue.map(t => [t.id, t])) };
  const work = waitTrigger({ mode: 'work', actor: 'bob', items: [], sequence: 0 }, snapshot);
  assert.equal(work.kind, 'work'); assert.deepEqual(work.tasks, ['b']);
  assert.equal(waitTrigger({ items: ['a'], sequence: 0 }, snapshot).kind, 'reevaluate');
  snapshot.blockers = []; snapshot.notes = [];
  assert.equal(waitTrigger({ items: ['a'], sequence: 0 }, snapshot), null, 'new B must not redefine named A wait');
});

test('work returns immediately for existing work, rejects busy actors/mixed modes and preserves single active wait', async () => {
  const f = await fixture();
  try {
    const entry = await f.direct({ action: 'work', reason: 'take the next useful output' });
    assert.equal(entry.mode, 'work'); assert.deepEqual(entry.items, []);
    await assert.rejects(f.direct({ action: 'work', reason: 'duplicate' }, 'duplicate-work'), /already active/);
    await f.direct({ action: 'cancel', id: entry.id }, 'cancel-work');
    await assert.rejects(f.direct({ action: 'work', items: [f.item], reason: 'mixed' }, 'mixed'), /without.*items/);
    const made = f.domain('alice', { op: 'create', subject: 'available', detail: 'independent output' });
    const item = (made.task ?? made).id;
    const immediate = await f.direct({ action: 'work', reason: 'take available output' }, 'ready-work');
    assert.equal(immediate.workAvailableNow, true); assert.equal(immediate.readyNow, false);
    assert.deepEqual(immediate.trigger.tasks, [item]);
    assert.equal(Object.keys((await f.doc()).waits).length, 1, 'immediate result must not create another watcher');
    const current = readBoard(f.run).tasks[item];
    f.domain('bob', { op: 'claim', item, expected_revision: current.revision });
    await assert.rejects(f.direct({ action: 'work', reason: 'cannot own two tasks' }, 'busy-work'), /unfinished claim/);
    assert.equal(f.admissions.length, 0);
  } finally { await f.close(); }
});

test('new claimable work wakes 4/8-identity HTTP + Native/faux fixtures; FACT and unready work do not', async () => {
  for (const n of [4, 8]) {
    const f = await fixture(n);
    try {
      let message;
      f.afterAdmit(conversation => {
        const submit = conversation.submit;
        conversation.submit = async (input, callContext) => { message = input.content; return submit.call(conversation, input, callContext); };
      });
      const entry = await f.direct({ action: 'work', reason: 'waiting for useful authorized work' });
      f.domain('alice', { op: 'publish', type: 'FACT', text: 'ordinary progress', task: null });
      f.domain('alice', { op: 'create', subject: 'not ready', detail: 'needs original output', deps: [f.item] });
      await new Promise(resolve => setTimeout(resolve, 80));
      assert.equal(f.admissions.length, 0);
      f.faux.setResponses([fauxAssistantMessage('read the work hint and claim atomically')]);
      const made = f.domain('alice', { op: 'create', subject: 'independent ready work', detail: 'can start now' });
      const item = (made.task ?? made).id;
      await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
      const sent = (await f.doc()).waits[entry.id];
      assert.equal(sent.trigger.kind, 'work'); assert.deepEqual(sent.trigger.tasks, [item]);
      assert.match(message, /WORK AVAILABLE/); assert.doesNotMatch(message, /READY: dependencies/);
      assert.ok(Buffer.byteLength(message) <= 2048);
      assert.equal(readBoard(f.run).tasks[f.item].state, 'claimed');
      assert.equal(readBoard(f.run).tasks[item].owner, null, 'a wake does not assign work');
      const receipt = f.domain('bob', { op: 'snapshot', request_id: sent.receipt.request_id });
      assert.ok(receipt.view.queue.some(task => task.id === item && task.readiness));
      assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 1);
      f.domain('bob', { op: 'ack', receipt_id: receipt.receipt_id });
      assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 0);
    } finally { await f.close(); }
  }
});

test('work rechecks a competing claim during admission and resumes only on later available work', async () => {
  const f = await fixture();
  try {
    const entry = await f.direct({ action: 'work', reason: 'wait for independent work' });
    let first = true;
    f.afterAdmit(() => {
      if (!first) return;
      first = false;
      const task = readBoard(f.run).queue.find(task => task.readiness);
      f.domain('carol', { op: 'claim', item: task.id, expected_revision: task.revision });
    });
    f.domain('alice', { op: 'create', subject: 'claimed by competitor', detail: 'race fixture' });
    await until(() => f.admissions.length === 1);
    await new Promise(resolve => setTimeout(resolve, 80));
    assert.equal((await f.doc()).waits[entry.id].state, 'waiting');
    assert.equal(await f.host.commit(tx => tx.submissionByRequest(f.root.id, wakeRequestId(entry.taskId)), context), undefined);
    f.faux.setResponses([fauxAssistantMessage('later output became available')]);
    const later = f.domain('alice', { op: 'create', subject: 'later work', detail: 'independent' });
    const id = (later.task ?? later).id;
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    const sent = (await f.doc()).waits[entry.id];
    assert.deepEqual(sent.trigger.tasks, [id]);
    const receipt = f.domain('bob', { op: 'snapshot', request_id: sent.receipt.request_id });
    assert.ok(receipt.view.queue.some(t => t.id === id && t.readiness), 'delivered receipt covers actual work, not withdrawn hint');
  } finally { await f.close(); }
});

test('work wait accepts direct handoff and survives accepted-response loss/reopen without duplicate input', async () => {
  const f = await fixture();
  try {
    const entry = await f.direct({ action: 'work', reason: 'available for handoff' });
    f.afterAdmit(conversation => {
      const submit = conversation.submit;
      conversation.submit = async (input, callContext) => { await submit.call(conversation, input, callContext); throw Error('lost accepted work response'); };
    });
    f.faux.setResponses([fauxAssistantMessage('continue assigned work')]);
    const task = readBoard(f.run).tasks[f.item];
    f.domain('alice', { op: 'handoff', item: task.id, generation: task.generation, expected_revision: task.revision,
      to: 'bob', summary: 'verified checkpoint; writer stopped' });
    await until(async () => (await f.doc()).waits[entry.id].state === 'failed');
    const requestId = wakeRequestId(entry.taskId);
    const accepted = await f.host.commit(tx => tx.submissionByRequest(f.root.id, requestId), context);
    assert.ok(accepted);
    await f.reopen(); await f.direct({ action: 'retry', id: entry.id }, 'retry-work');
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    assert.equal(f.admissions.length, 1);
    assert.deepEqual(await f.host.commit(tx => tx.submissionByRequest(f.root.id, requestId), context), accepted);
    assert.equal((await f.doc()).waits[entry.id].trigger.kind, 'work');
    assert.equal(f.domain('bob', { op: 'pending' }).receipts.length, 1, 'accepted work hint is not an ACK');
  } finally { await f.close(); }
});

test('unrelated FACT is ignored; linked FAIL and explicit ended producer cause reevaluation, never ready', async () => {
  const f = await fixture();
  try {
    const entry = await f.direct({ action: 'wait', items: [f.item], reason: 'need contract' });
    f.domain('alice', { op: 'publish', type: 'FACT', text: 'unrelated', task: null, related: [] });
    await new Promise(resolve => setTimeout(resolve, 80)); assert.equal(f.admissions.length, 0);
    f.faux.setResponses([fauxAssistantMessage('reevaluating failure')]);
    f.domain('alice', { op: 'publish', type: 'FAIL', text: 'contract revoked', task: f.item, related: [] });
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    assert.equal((await f.doc()).waits[entry.id].trigger.kind, 'reevaluate');
    const blocked = await f.direct({ action: 'wait', items: [f.item], reason: 'still bad' }, 'blocked');
    assert.equal(blocked.readyNow, false); assert.equal(blocked.reevaluateNow, true);
    const snapshot = readBoard(f.run); snapshot.blockers = []; snapshot.notes = [];
    snapshot.sessions = [{ actor: 'alice', state: 'idle' }];
    assert.equal(waitTrigger({ items: [f.item], sequence: snapshot.sequence }, snapshot), null);
    snapshot.sessions[0].state = 'ended';
    assert.equal(waitTrigger({ items: [f.item], sequence: snapshot.sequence }, snapshot).kind, 'reevaluate');
    assert.notEqual(readBoard(f.run).tasks[f.item].state, 'done');
  } finally { await f.close(); }
});
