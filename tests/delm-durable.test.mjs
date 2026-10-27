import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync, spawn } from 'node:child_process';
import { once } from 'node:events';
import { BACKGROUND_CONTEXT as context } from '@earendil-works/chord/context';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxProvider, fauxAssistantMessage, fauxToolCall } from '@earendil-works/pi-ai/providers/faux';
import { Harness, createRegistry } from '@earendil-works/pi-durable';
import { openNodeSqliteStorage } from '@earendil-works/pi-durable/storage/sqlite/node';
import install, { createDelmWait, DelmWaitDoc, readBoard, wakeRequestId } from '../extensions/delm/index.js';

const project = new URL('../', import.meta.url).pathname;
async function until(check) {
  const deadline = Date.now() + 8000;
  while (!await check()) {
    if (Date.now() > deadline) throw Error('condition timed out');
    await new Promise(resolve => setTimeout(resolve, 15));
  }
}
async function fixture() {
  const directory = await mkdtemp(join(tmpdir(), 'delm-native-'));
  const source = join(directory, 'source'), run = join(directory, 'board');
  await mkdir(source); await writeFile(join(source, 'sample.txt'), 'baseline');
  execFileSync('python3', [join(project, 'scripts/delm_local.py'), 'init', run, '--source', source, '--task', 'fixture']);
  const board = expression => JSON.parse(execFileSync('python3', ['-c',
    `import sys,json;sys.path.insert(0,${JSON.stringify(join(project, 'scripts'))});from delm_local import board;from pathlib import Path;b=board(Path(${JSON.stringify(run)}));print(json.dumps(${expression}))`], { encoding: 'utf8' }));
  const item = board("b.reserve('alice','required dependency','fixture')").item;
  const faux = fauxProvider(), models = createModels(); models.setProvider(faux.provider);
  const registry = createRegistry(), admissions = [];
  let deny = false;
  registry.install(createDelmWait({ run, actor: 'bob', admitInput: async (_conversation, id) => {
    admissions.push(id); if (deny) throw Error('revoked');
  } }));
  const path = join(directory, 'native.sqlite');
  let host, root;
  async function open() {
    host = await Harness.open(await openNodeSqliteStorage(path), { registry, models }, context);
    root = await host.root(context, { agent: { model: { provider: 'faux', modelId: 'faux-1' } } });
    host.resume();
  }
  await open();
  const doc = () => host.snapshot(DelmWaitDoc, root.id, context);
  const tool = registry.snapshot().extension('delm').tools[0];
  async function direct(args, key='direct-test', conversationId=root.id) {
    return tool.execute(args, { taskId: key, callId: key, conversationId,
      commit: fn => host.commit(fn, context) }, context);
  }
  return { directory, run, item, board, faux, admissions, registry, doc, direct,
    get host() { return host; }, get root() { return root; }, deny: () => { deny = true; },
    async arm() {
      faux.setResponses([fauxAssistantMessage(fauxToolCall('delm_wait', { action: 'wait', items: [item], reason: 'need exact task' }), { stopReason: 'toolUse' }), fauxAssistantMessage('waiting')]);
      const submission = await root.submit({ type: 'input', content: 'arm wait' }, context);
      await submission.wait(context);
      const entry = Object.values((await doc()).waits)[0]; assert.equal(entry.state, 'waiting'); return entry;
    },
    done() { return board(`b.done('alice',${JSON.stringify(item)},'verified fixture complete')`); },
    async reopen() { await host.close(context); await open(); },
    async close() { await host.close(context); await rm(directory, { recursive: true, force: true }); },
  };
}

test('native registry fails closed without trusted admission; no importer starts services', () => {
  assert.throws(() => install(createRegistry(), {}), /trusted admission/);
});

test('real 1.4 SQLite + faux model: exact dependency wake in same conversation; unrelated events ignored', async () => {
  const f = await fixture();
  try {
    const entry = await f.arm();
    await writeFile(join(f.run, 'dcg-reopen-sessions.json'), JSON.stringify({ bob: { session: join(f.directory, 'native.sqlite') } }));
    const observed = JSON.parse(execFileSync('python3', ['-c',
      `import sys,json;sys.path.insert(0,${JSON.stringify(join(project, 'scripts'))});from delm_board import load_board;from pathlib import Path;print(json.dumps(load_board(Path(${JSON.stringify(f.run)}))['waits']['bob']))`], { encoding: 'utf8' }));
    assert.equal(observed.length, 1);
    assert.equal(observed[0].native_id, entry.taskId);
    assert.deepEqual(observed[0].items, entry.items);
    assert.equal(observed[0].reason, entry.reason);
    assert.equal(observed[0].state, 'waiting');
    const before = readBoard(f.run).sequence;
    f.board("b.note('alice','FACT','unrelated progress','other','test')");
    await new Promise(resolve => setTimeout(resolve, 80));
    assert.equal(f.admissions.length, 0);
    assert.equal((await f.doc()).waits[entry.id].state, 'waiting');
    f.faux.setResponses([fauxAssistantMessage('resumed exact dependency')]);
    f.done();
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    const receipt = await f.host.commit(tx => tx.submissionByRequest(f.root.id, wakeRequestId(entry.taskId)), context);
    assert.ok(receipt); assert.equal(receipt.conversationId, f.root.id);
    assert.equal(f.admissions.length, 1);
    f.board("b.note('alice','FACT','later progress','other','test')");
    await new Promise(resolve => setTimeout(resolve, 50));
    assert.equal(f.admissions.length, 1);
    assert.ok(readBoard(f.run).sequence > before);
  } finally { await f.close(); }
});

test('ready at arm, invalid dependency, cross-conversation and cancellation', async () => {
  const f = await fixture();
  try {
    await assert.rejects(f.direct({ action: 'wait', items: ['missing'], reason: 'no' }), /Unknown/);
    const sibling = await f.host.createConversation({ ownership: { kind: 'ownerless' } }, context);
    await assert.rejects(f.direct({ action: 'status' }, 'foreign', sibling.id), /root conversation/);
    const result = await f.direct({ action: 'wait', items: [f.item], reason: 'dependency' });
    const entry = result.structuredOutput.result;
    const replay = await f.direct({ action: 'wait', items: [f.item], reason: 'dependency' });
    assert.equal(replay.structuredOutput.result.id, entry.id);
    await assert.rejects(f.direct({ action: 'wait', items: [f.item], reason: 'duplicate' }, 'second'), /already active/);
    await f.direct({ action: 'cancel', id: entry.id }, 'cancel');
    f.done();
    await new Promise(resolve => setTimeout(resolve, 100));
    assert.equal(f.admissions.length, 0);
    assert.equal((await f.doc()).waits[entry.id].state, 'cancelled');
    const ready = await f.direct({ action: 'wait', items: [f.item], reason: 'already done' }, 'ready');
    assert.equal(ready.structuredOutput.result.readyNow, true);
    assert.equal(Object.keys((await f.doc()).waits).length, 1);
  } finally { await f.close(); }
});

test('reopen persisted native watch, same request identity, no duplicate wake after second reopen', async () => {
  const f = await fixture();
  try {
    const entry = await f.arm();
    await f.reopen();
    assert.equal((await f.doc()).waits[entry.id].state, 'waiting');
    f.faux.setResponses([fauxAssistantMessage('resumed after reopen')]); f.done();
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    assert.equal(f.admissions.length, 1);
    await f.reopen();
    const receipt = await f.host.commit(tx => tx.submissionByRequest(f.root.id, wakeRequestId(entry.taskId)), context);
    assert.ok(receipt); assert.equal(f.admissions.length, 1);
  } finally { await f.close(); }
});

test('temporary SQLite writer lock keeps the native wait armed and wakes after unlock', async () => {
  const f = await fixture(); let writer;
  try {
    const entry = await f.arm();
    writer = spawn('python3', ['-c', "import sqlite3,sys; d=sqlite3.connect(sys.argv[1]); d.execute('BEGIN EXCLUSIVE'); print('locked',flush=True); sys.stdin.read(); d.rollback(); d.close()", join(f.run, 'context.sqlite')], { stdio: ['pipe', 'pipe', 'pipe'] });
    await once(writer.stdout, 'data');
    await new Promise(resolve => setTimeout(resolve, 600));
    assert.equal((await f.doc()).waits[entry.id].state, 'waiting');
    assert.equal(f.admissions.length, 0);
    const stopped = once(writer, 'close'); writer.stdin.end(); await stopped;
    f.faux.setResponses([fauxAssistantMessage('resumed after board contention')]); f.done();
    await until(async () => (await f.doc()).waits[entry.id].state === 'sent');
    assert.equal(f.admissions.length, 1);
  } finally { if (writer?.exitCode === null) writer.kill(); await f.close(); }
});

test('trusted admission denial does not submit a wake', async () => {
  const f = await fixture();
  try {
    const entry = await f.arm(); f.deny(); f.done();
    await until(async () => (await f.doc()).waits[entry.id].state === 'failed');
    const receipt = await f.host.commit(tx => tx.submissionByRequest(f.root.id, wakeRequestId(entry.taskId)), context);
    assert.equal(receipt, undefined);
  } finally { await f.close(); }
});
