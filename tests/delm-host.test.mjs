import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, chmod, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { operate, main } from '../scripts/delm_host.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'delm-host-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const run = join(root, 'run');
  await mkdir(join(run, 'inputs'), { recursive: true });
  const legacy = { schema: 2, id: 'frozen-id', run, workspace: root, actors: {}, inputs: { references: [] } };
  for (const type of ['prompt', 'plan', 'global_agents', 'project_agents']) {
    const captured = join(run, 'inputs', type);
    await writeFile(captured, `approved ${type}`, { mode: 0o600 });
    legacy.inputs[type] = { captured, sha256: sha(`approved ${type}`) };
  }
  await writeFile(join(run, 'WORKER.md'), 'Frozen worker instructions');
  const bodies = {};
  for (const actor of ['worker-1', 'worker-2']) {
    await mkdir(join(run, actor, 'records'), { recursive: true });
    await writeFile(join(run, actor, 'START.md'), `Frozen start ${actor}`);
    const content = `[delm-bootstrap:frozen-id:${actor}]\nExact frozen UTF-8: π\n`;
    bodies[actor] = content;
    await writeFile(join(run, actor, 'records/bootstrap-input.txt'), content, { mode: 0o600 });
    legacy.actors[actor] = { bootstrap_sha256: sha(content), session: null };
  }
  await writeFile(join(run, 'launch.json'), JSON.stringify(legacy));
  const bindings = join(root, 'bindings.json'), map = join(root, 'map.json');
  await writeFile(bindings, JSON.stringify({ version: 1, sessions: {} }), { mode: 0o600 });
  await writeFile(map, JSON.stringify({ 'worker-1': 'host-exact-1', 'worker-2': 'host-exact-2' }), { mode: 0o600 });
  const calls = [], ledger = new Map();
  let ambiguous = false;
  const runtime = { supported: true, missing: new Set(), busy: new Set(), refuse: false, noOffer: false };
  const client = {
    baseUrl: 'http://127.0.0.1:19477',
    async protocol() { calls.push(['protocol']); return { capabilities: runtime.supported ? ['runtime-refresh.v1'] : [] }; },
    async request(method, path, body, options) {
      const id = decodeURIComponent(path.split('/')[3]);
      assert.equal(method, 'POST'); assert.equal(path, `/v1/sessions/${encodeURIComponent(id)}/runtime/refresh`);
      assert.deepEqual(body, {}); assert.deepEqual(options, { requiredCapabilities: ['runtime-refresh.v1'] });
      const registry = JSON.parse(await readFile(bindings, 'utf8'));
      assert.equal(registry.sessions[id].enabled, true, 'Register exact binding before refresh');
      calls.push(['refresh', id]);
      if (runtime.refuse) throw Error('Selected session busy: refresh refused');
      if (!runtime.noOffer) runtime.missing.delete(id);
      return { sessionId: id, refreshed: true };
    },
    session(id) {
      return {
        async get() { calls.push(['get', id]); return { id, cwd: root, agents: [{ id: 1, kind: 'root', busy: runtime.busy.has(id) }] }; },
        async tasks(status, limit) { calls.push(['tasks', id, status, limit]); return [{ id: id.endsWith('1') ? 90 : 92, conversationId: 1 }, { id: 91, conversationId: 999 }]; },
      };
    },
    agent(id, conversation) {
      return {
        async get() { return { id: conversation, sessionId: id,
          tools: runtime.missing.has(id) ? [] : [{ name: 'delm_wait', offered: true }] }; },
        async send(content, mode, requestId, waitMs) {
          const state = JSON.parse(await readFile(join(run, 'sdk-launch.json'), 'utf8'));
          const record = Object.values(state.actors).find(record => record.hostId === id);
          assert.equal(record.phase, 'sending');
          assert.equal(record.requestId, requestId);
          assert.equal(record.input.sha256, sha(content));
          calls.push(['send', id, conversation, content, mode, requestId, waitMs]);
          if (!ledger.has(requestId)) ledger.set(requestId, { submissionId: ledger.size + 1, status: 'queued' });
          if (ambiguous) { ambiguous = false; throw Error('secret transport payload'); }
          return ledger.get(requestId);
        },
        async abort(background) {
          const registry = JSON.parse(await readFile(bindings, 'utf8'));
          assert.equal(registry.sessions[id].enabled, false);
          calls.push(['abort', id, conversation, background]);
          return { ok: true };
        },
      };
    },
  };
  const options = { run, bindings, map };
  const exec = action => operate({ ...options, action }, client);
  return { root, run, legacy, bindings, map, client, calls, ledger, bodies, options, exec, runtime,
    ambiguous() { ambiguous = true; } };
}

test('bind records exact existing roots and approved fingerprints without send or legacy edits', async t => {
  const f = await fixture(t);
  const before = await readFile(join(f.run, 'launch.json'));
  await f.exec('bind');
  assert.ok(before.equals(await readFile(join(f.run, 'launch.json'))));
  assert.equal(f.calls.filter(call => call[0] === 'send').length, 0);
  const state = JSON.parse(await readFile(join(f.run, 'sdk-launch.json')));
  assert.equal(state.inputs.length, 7);
  assert.equal(state.actors['worker-1'].rootId, 1);
  assert.equal(state.actors['worker-2'].rootId, 1);
  assert.equal(state.actors['worker-1'].requestId, 'delm-bootstrap:frozen-id:worker-1');
});

test('bind refuses any non-1 owner root before publishing bindings or submitting', async t => {
  const f = await fixture(t);
  const original = f.client.session;
  f.client.session = id => ({ ...original(id), get: async () => ({ id, cwd: f.root,
    agents: [{ id: 10, kind: 'root', busy: false }] }) });
  await assert.rejects(f.exec('bind'), /Host root identity mismatch/);
  assert.deepEqual(JSON.parse(await readFile(f.bindings)).sessions, {});
  await assert.rejects(readFile(join(f.run, 'sdk-launch.json')), { code: 'ENOENT' });
  assert.equal(f.calls.filter(call => call[0] === 'send').length, 0);
});

test('start sends exact frozen bytes with stable IDs and saves receipts; repeated start does not send', async t => {
  const f = await fixture(t);
  await f.exec('bind');
  await f.exec('start');
  await f.exec('start');
  const sends = f.calls.filter(call => call[0] === 'send');
  assert.equal(sends.length, 2);
  assert.deepEqual(sends[0], ['send', 'host-exact-1', 1, f.bodies['worker-1'], 'followUp', 'delm-bootstrap:frozen-id:worker-1', 0]);
  assert.equal(JSON.parse(await readFile(join(f.run, 'sdk-launch.json'))).actors['worker-1'].receipt.submissionId, 1);
});

test('ambiguous acceptance persists intent then replays identical request through Host ledger', async t => {
  const f = await fixture(t);
  await f.exec('bind');
  f.ambiguous();
  await assert.rejects(f.exec('start'), /secret transport/);
  assert.equal(JSON.parse(await readFile(join(f.run, 'sdk-launch.json'))).actors['worker-1'].phase, 'sending');
  await f.exec('start');
  const sends = f.calls.filter(call => call[0] === 'send');
  assert.deepEqual(sends[0], sends[1]);
  assert.equal(f.ledger.size, 2);
});

test('stop disables before exact foreground root abort; resume sends nothing', async t => {
  const f = await fixture(t);
  await f.exec('bind');
  const result = await f.exec('stop');
  assert.match(result.scope, /waiter cancellation unsupported/);
  assert.deepEqual(f.calls.filter(call => call[0] === 'abort'), [['abort', 'host-exact-1', 1, false], ['abort', 'host-exact-2', 1, false]]);
  await assert.rejects(f.exec('start'), /disabled/);
  await f.exec('resume');
  assert.equal(f.calls.filter(call => call[0] === 'send').length, 0);
});

test('status uses live tasks but reports only root-correlated IDs without task aborts', async t => {
  const f = await fixture(t);
  await f.exec('bind');
  const result = await f.exec('status');
  assert.deepEqual(result.actors[0].liveRootTaskIds, [90]);
  assert.deepEqual(result.actors[1].liveRootTaskIds, [92]);
});

test('tampered approved input or bootstrap prevents all sends', async t => {
  for (const relative of ['inputs/prompt', 'worker-2/records/bootstrap-input.txt', 'WORKER.md', 'worker-2/START.md']) {
    const f = await fixture(t);
    await f.exec('bind');
    await writeFile(join(f.run, relative), 'changed');
    await assert.rejects(f.exec('start'), /SHA mismatch|manifest changed/);
    assert.equal(f.calls.filter(call => call[0] === 'send').length, 0);
  }
});

test('map must be exact and injective; cannot import SDK from map JSON', async t => {
  const f = await fixture(t);
  await writeFile(f.map, JSON.stringify({ 'worker-1': 'same', 'worker-2': 'same', sdk: '/bad.mjs' }));
  await assert.rejects(f.exec('bind'), /Map must/);
});

test('private operator files required; symlinked frozen inputs refused', async t => {
  const f = await fixture(t);
  await chmod(f.map, 0o644);
  await assert.rejects(f.exec('bind'), /owner-only/);
  await chmod(f.map, 0o600);
  const input = join(f.run, 'inputs/prompt');
  await rm(input);
  await symlink(f.map, input);
  await assert.rejects(f.exec('bind'), /escapes/);
});

test('changed root, endpoint, or binding identity refuses submission', async t => {
  const f = await fixture(t);
  await f.exec('bind');
  f.client.baseUrl = 'http://127.0.0.1:9999';
  await assert.rejects(f.exec('start'), /identity mismatch/);
  f.client.baseUrl = 'http://127.0.0.1:19477';
  const original = f.client.session;
  f.client.session = id => ({ ...original(id), get: async () => ({ id, cwd: f.root, agents: [{ id: 999, kind: 'root' }] }) });
  await assert.rejects(f.exec('start'), /root identity/);
  f.client.session = original;
  const registry = JSON.parse(await readFile(f.bindings));
  registry.sessions['host-exact-1'].actor = 'someone-else';
  await writeFile(f.bindings, JSON.stringify(registry));
  await assert.rejects(f.exec('start'), /Binding identity/);
});

test('shared registry lock rejects concurrent operations without removing their lock', async t => {
  const f = await fixture(t);
  await writeFile(f.bindings + '.delm-lock', 'existing');
  await assert.rejects(f.exec('bind'), { code: 'EEXIST' });
  assert.equal(await readFile(f.bindings + '.delm-lock', 'utf8'), 'existing');
});

test('CLI rejects remote endpoints and unknown client import configuration before loading SDK', async t => {
  const f = await fixture(t);
  const client = join(f.root, 'client.json');
  await writeFile(client, JSON.stringify({ baseUrl: 'https://example.com', token: 'private' }), { mode: 0o600 });
  const args = ['status', '--run', f.run, '--client', client, '--bindings', f.bindings, '--sdk', '/does-not-exist'];
  await assert.rejects(main(args), /loopback/);
  await writeFile(client, JSON.stringify({ baseUrl: 'http://127.0.0.1:19477', token: 'private', sdk: '/bad.mjs' }));
  await assert.rejects(main(args), /exactly one of url or baseUrl/);
  await writeFile(client, JSON.stringify({ url: 'http://127.0.0.1:19477', baseUrl: 'http://127.0.0.1:19478', token: 'private' }));
  await assert.rejects(main(args), /exactly one of url or baseUrl/);
});

test('bind replays safely after registry publication interruption, but never remaps or resumes', async t => {
  const f = await fixture(t);
  await f.exec('bind');
  await writeFile(f.bindings, JSON.stringify({ version: 1, sessions: {} }));
  await f.exec('bind');
  const stateBefore = await readFile(join(f.run, 'sdk-launch.json'), 'utf8');
  await f.exec('stop');
  await f.exec('bind');
  const registry = JSON.parse(await readFile(f.bindings));
  assert.equal(registry.sessions['host-exact-1'].enabled, false);
  assert.equal(JSON.parse(stateBefore).actors['worker-1'].requestId, 'delm-bootstrap:frozen-id:worker-1');
  await writeFile(f.map, JSON.stringify({ 'worker-1': 'other-host', 'worker-2': 'host-exact-2' }));
  await assert.rejects(f.exec('bind'), /mapping changed/);
});

test('operator CLI imports selected SDK and supplies authentication, without using Host or models', async t => {
  const f = await fixture(t);
  const sdk = join(f.root, 'fake-sdk.mjs'), client = join(f.root, 'client.json');
  await writeFile(client, JSON.stringify({ baseUrl: f.client.baseUrl, token: 'test-only-sentinel' }), { mode: 0o600 });
  await writeFile(sdk, `export class DpiClient {
    constructor(baseUrl, token) {
      if (token !== 'test-only-sentinel') throw Error('Missing authenticated client token');
      this.baseUrl = baseUrl;
    }
    session(id) { return { get: async () => ({ id, cwd: ${JSON.stringify(f.root)}, agents: [{id: 1, kind:'root'}] }) }; }
    agent(id, root) { return { get: async () => ({ id: root, sessionId: id, tools: [{ name:'delm_wait', offered:true }] }), send: async (content, mode, requestId, waitMs) => {
      if (!content.includes('π') || mode !== 'followUp' || !requestId.startsWith('delm-bootstrap:') || waitMs !== 0) throw Error('Invalid SDK arguments');
      return { submissionId: 7, status: 'queued' };
    } }; }
  }`);
  const args = ['--run', f.run, '--client', client, '--bindings', f.bindings, '--sdk', sdk];
  for (const key of ['url', 'baseUrl']) {
    await writeFile(client, JSON.stringify({ [key]: f.client.baseUrl, token: 'test-only-sentinel' }));
    await main(['bind', ...args, '--map', f.map]);
    const result = await main(['start', ...args]);
    assert.equal(result.actors.length, 2);
    assert.ok(!JSON.stringify(result).includes('test-only-sentinel'));
  }
});

test('hot bind publishes exact bindings before refreshing only the missing idle runtime', async t => {
  const f = await fixture(t);
  f.runtime.missing.add('host-exact-1'); f.runtime.busy.add('host-exact-2');
  const result = await f.exec('bind');
  assert.equal(result.registered, true); assert.equal(result.ready, true);
  assert.deepEqual(f.calls.filter(call => call[0] === 'refresh'), [['refresh', 'host-exact-1']]);
  const state = JSON.parse(await readFile(join(f.run, 'sdk-launch.json')));
  assert.deepEqual(state.actors['worker-1'].runtimeRefresh, { phase: 'refreshed', sessionId: 'host-exact-1', refreshed: true });
  assert.equal(state.actors['worker-1'].requestId, 'delm-bootstrap:frozen-id:worker-1');
  assert.equal(f.calls.filter(call => call[0] === 'send').length, 0);
});

test('unsupported Host remains registered but unready and cannot bootstrap', async t => {
  const f = await fixture(t);
  f.runtime.supported = false; f.runtime.missing.add('host-exact-1');
  const result = await f.exec('bind');
  assert.equal(result.registered, true); assert.equal(result.ready, false);
  assert.equal(result.requiresHostUpgrade, true); assert.equal(result.requiresRuntimeRefresh, false);
  await assert.rejects(f.exec('start'), /not ready/);
  assert.equal(f.calls.filter(call => ['send', 'refresh', 'abort'].includes(call[0])).length, 0);
});

test('refresh refusal retains durable registration and retries without bootstrap', async t => {
  const f = await fixture(t);
  f.runtime.missing.add('host-exact-1'); f.runtime.refuse = true;
  await assert.rejects(f.exec('bind'), /refresh refused/);
  assert.equal(JSON.parse(await readFile(f.bindings)).sessions['host-exact-1'].enabled, true);
  const state = JSON.parse(await readFile(join(f.run, 'sdk-launch.json')));
  assert.equal(state.actors['worker-1'].runtimeRefresh.phase, 'requesting');
  f.runtime.refuse = false;
  assert.equal((await f.exec('bind')).ready, true);
  assert.equal(f.calls.filter(call => call[0] === 'send').length, 0);
});

test('missing busy root refuses refresh while already-ready busy roots need no capability', async t => {
  const f = await fixture(t);
  f.runtime.busy.add('host-exact-1'); f.runtime.missing.add('host-exact-1');
  await assert.rejects(f.exec('bind'), /must be idle/);
  assert.equal(f.calls.filter(call => call[0] === 'refresh').length, 0);
  f.runtime.missing.clear();
  f.client.protocol = async () => { throw Error('Ready roots must not query upgrade capability'); };
  assert.equal((await f.exec('bind')).ready, true);
});

test('refresh receipt is insufficient without actually offered delm_wait', async t => {
  const f = await fixture(t);
  f.runtime.missing.add('host-exact-1'); f.runtime.noOffer = true;
  await assert.rejects(f.exec('bind'), /did not offer delm_wait/);
  await assert.rejects(f.exec('start'), /not ready/);
  assert.equal(f.calls.filter(call => call[0] === 'send').length, 0);
});

test('wrong-session refresh receipt fails closed', async t => {
  const f = await fixture(t);
  f.runtime.missing.add('host-exact-1');
  f.client.request = async () => ({ sessionId: 'unrelated', refreshed: true });
  await assert.rejects(f.exec('bind'), /Invalid runtime refresh receipt/);
  assert.equal(f.calls.filter(call => call[0] === 'send').length, 0);
});

test('bind never refreshes or enables stopped bindings', async t => {
  const f = await fixture(t);
  await f.exec('bind'); await f.exec('stop');
  f.runtime.missing.add('host-exact-1'); f.runtime.missing.add('host-exact-2');
  const result = await f.exec('bind');
  assert.equal(result.ready, false);
  assert.equal(f.calls.filter(call => call[0] === 'refresh').length, 0);
  assert.equal(JSON.parse(await readFile(f.bindings)).sessions['host-exact-1'].enabled, false);
});

test('stop continues other roots after an unavailable Host and reports incomplete scope', async t => {
  const f = await fixture(t);
  await f.exec('bind');
  const original = f.client.agent;
  f.client.agent = (id, root) => id.endsWith('1') ? { abort: async () => { throw Error('private token'); } } : original(id, root);
  const result = await f.exec('stop');
  assert.equal(result.complete, false);
  assert.deepEqual(result.results, [{ actor: 'worker-1', rootAborted: false }, { actor: 'worker-2', rootAborted: true }]);
  assert.ok(!JSON.stringify(result).includes('private token'));
  assert.equal(JSON.parse(await readFile(f.bindings)).sessions['host-exact-1'].enabled, false);
});
