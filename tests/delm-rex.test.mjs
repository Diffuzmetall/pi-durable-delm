import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm, stat } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { launch } from '../scripts/delm_rex.mjs';

const roster = ['alice', 'bob', 'carol', 'dave', 'eve', 'frank', 'grace', 'heidi'];
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const label = name => name[0].toUpperCase() + name.slice(1);
const load = async path => JSON.parse(await readFile(path, 'utf8'));
async function fixture(t, n = 8) {
  const root = await mkdtemp(join(tmpdir(), 'delm-rex-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const run = join(root, 'run'), workspace = join(root, 'workspace'), pkg = join(root, 'pinned-package');
  await mkdir(join(run, 'inputs'), { recursive: true }); await mkdir(workspace);
  await mkdir(join(pkg, 'scripts'), { recursive: true });
  for (const name of ['delm_local.py', 'delm_board.py']) await writeFile(join(pkg, 'scripts', name), '# fake: never executed\n');
  const native = join(root, 'native'); await writeFile(native, '#!/bin/sh\nexit 99\n', { mode: 0o700 });
  const manifest = { schema: 2, id: 'prepared-exact-id', run, workspace, package_root: pkg, actors: {}, inputs: { references: [] } };
  for (const type of ['prompt', 'plan', 'global_agents', 'project_agents']) {
    const captured = join(run, 'inputs', type); await writeFile(captured, `approved:${type}`);
    manifest.inputs[type] = { captured, sha256: hash(`approved:${type}`) };
  }
  const names = roster.slice(0, n);
  for (const actor of names) {
    await mkdir(join(run, actor, 'records'), { recursive: true });
    await writeFile(join(run, actor, 'START.md'), `Frozen ${actor} start`);
    const body = `Exact bootstrap ${actor}\n`;
    await writeFile(join(run, actor, 'records/bootstrap-input.txt'), body);
    manifest.actors[actor] = { bootstrap_sha256: hash(body) };
  }
  await writeFile(join(run, 'WORKER.md'), 'Frozen common worker');
  await writeFile(join(run, 'launch.json'), JSON.stringify(manifest));
  await writeFile(join(run, 'config.json'), JSON.stringify({ workspace, actors: Object.fromEntries(names.map(a => [a, `PRIVATE_TOKEN_${a}`])) }), { mode: 0o600 });
  const models = join(root, 'models.json');
  const selection = Object.fromEntries(names.map((actor, i) => [actor, { provider: `provider-${i % 2}`, modelId: `exact-${actor}` }]));
  await writeFile(models, JSON.stringify(selection), { mode: 0o600 });
  const bindings = join(root, 'bindings.json'); await writeFile(bindings, JSON.stringify({ version: 1, sessions: {} }), { mode: 0o600 });
  const options = { run, models, bindings, client: join(root, 'operator-client.json'), session: 'session:exact-rex-id', native };
  const calls = { create: [], rename: [], windows: [], refresh: [], serverStarts: 0, sends: 0 };
  const runtime = { supported: true, refuse: false, noOffer: false };
  const sessions = new Map(), keys = new Map();
  let loseCreation = false, loseWindow = false;
  const client = {
    baseUrl: 'http://127.0.0.1:19477',
    async protocol() { return { capabilities: runtime.supported ? ['runtime-refresh.v1'] : [] }; },
    async request(method, path, body, options) {
      assert.equal(method, 'POST'); assert.deepEqual(body, {});
      assert.deepEqual(options, { requiredCapabilities: ['runtime-refresh.v1'] });
      const id = decodeURIComponent(path.split('/')[3]);
      assert.equal(path, `/v1/sessions/${encodeURIComponent(id)}/runtime/refresh`);
      const registry = await load(bindings);
      assert.equal(registry.sessions[id].run, run, 'Private exact mapping registered before hot attach');
      assert.equal(registry.sessions[id].enabled, true);
      calls.refresh.push(id);
      if (runtime.refuse) throw Error('Selected session busy; runtime refresh refused');
      assert(!sessions.get(id).root.busy, 'Never refresh a busy selected session');
      if (!runtime.noOffer) sessions.get(id).toolReady = true;
      return { sessionId: id, refreshed: true };
    },
    async createSession(body, key) {
      const state = await load(join(run, 'rex-launch.json'));
      assert(Object.values(state.actors).some(record => record.key === key && JSON.stringify(record.body) === JSON.stringify(body)), 'Durable intent before SDK creation');
      calls.create.push({ body: structuredClone(body), key });
      if (!keys.has(key)) {
        const id = `host-exact-${keys.size + 1}`; keys.set(key, id);
        sessions.set(id, { id, name: body.name, cwd: body.cwd, model: body.model,
          root: { id: 1, name: 'unnamed', kind: 'root', busy: false }, toolReady: false });
      }
      if (loseCreation) { loseCreation = false; throw Error('Lost accepted creation response'); }
      return { id: keys.get(key) };
    },
    session(id) {
      return { async get() { const s = sessions.get(id); assert(s); return { ...s, agents: [{ ...s.root }] }; },
        async rename(name) { calls.rename.push([id, name]); sessions.get(id).name = name; } };
    },
    agent(id, rootId) {
      return { async rename(name) { assert.equal(rootId, 1); sessions.get(id).root.name = name; },
        async get() { const s = sessions.get(id); return { id: 1, name: s.root.name, sessionId: id,
          config: { cwd: s.cwd, model: s.model }, tools: s.toolReady ? [{ name: 'delm_wait', offered: true }] : [] }; },
        async send() { calls.sends++; throw Error('Bootstrap/model call forbidden'); } };
    },
  };
  const view = { session_id: options.session, windows: [] }, commands = new Map();
  const rex = {
    async inspect() { return structuredClone(view); },
    async command(id) { return structuredClone(commands.get(id)); },
    async newWindow(request) {
      assert.equal((await load(join(run, 'rex-launch.json'))).window.phase, 'creating');
      calls.windows.push(structuredClone(request));
      const blocks = [], ids = [];
      function layout(node) {
        if (node.block) {
          const id = `block:exact-${ids.length}`; ids.push(id);
          blocks.push({ block_id: id, label: node.block.label });
          commands.set(id, { argv: node.block.options.command, cwd: node.block.options.cwd });
          return { block_id: id, rect: [0, 0, 1, 1] };
        }
        return { split: { ...node.split, split_id: `split:${ids.length}`, before: layout(node.split.before), after: layout(node.split.after) }, rect: [0, 0, 1, 1] };
      }
      view.windows.push({ window_id: 'window:exact', label: request.window_label,
        layers: [{ kind: 'tiled', bounds: [0, 0, 1, 1], layout: layout(request.layout), blocks }] });
      if (loseWindow) throw Error('Lost Rex response after creation');
      return { window_id: 'window:exact', block_ids: ids };
    },
  };
  const board = { async start() { calls.serverStarts++; return { pid: 123, startTicks: '456' }; },
    async verify(receipt) { assert.deepEqual(receipt, { pid: 123, startTicks: '456' }); return true; } };
  const exec = action => launch({ ...options, action }, { client, rex, board });
  return { root, run, workspace, pkg, options, selection, sessions, keys, calls, view, commands, client, rex, board, exec, runtime,
    loseCreation() { loseCreation = true; }, loseWindow() { loseWindow = true; } };
}

for (const n of [2, 4, 8]) test(`${n} actors: one frozen roster, named roots and one tab with board left/right grid`, async t => {
  const f = await fixture(t, n);
  const before = await readFile(join(f.run, 'launch.json'));
  const result = await f.exec('open');
  assert.equal(result.registered, true); assert.equal(result.ready, true); assert.equal(result.requiresHostReload, false);
  assert.equal(result.requiresHostUpgrade, false); assert.equal(f.calls.refresh.length, n);
  assert.equal(result.bootstrapSent, false); assert.equal(result.runningTeamClaimed, false);
  assert.deepEqual(result.roster, roster.slice(0, n));
  assert.equal(f.calls.create.length, n); assert.equal(f.calls.windows.length, 1); assert.equal(f.calls.serverStarts, 1);
  const state = await load(join(f.run, 'rex-launch.json'));
  const bound = await load(join(f.run, 'sdk-launch.json'));
  assert.deepEqual(Object.keys(bound.actors), roster.slice(0, n));
  assert.equal(state.window.blockIds.length, n + 1);
  assert.equal(state.window.layout.split.direction, 'horizontal'); assert.equal(state.window.layout.split.ratio, 0.3);
  const rectangles = {};
  function positions(node, x = 0, y = 0, w = 1, h = 1) {
    if (node.block) { rectangles[node.block.label] = [x, y, w, h].map(v => Number(v.toFixed(6))); return; }
    const { direction, ratio, before, after } = node.split;
    if (direction === 'horizontal') { positions(before, x, y, w * ratio, h); positions(after, x + w * ratio, y, w * (1 - ratio), h); }
    else { positions(before, x, y, w, h * ratio); positions(after, x, y + h * ratio, w, h * (1 - ratio)); }
  }
  positions(state.window.layout);
  assert.deepEqual(rectangles.Board, [0, 0, 0.3, 1]);
  assert.deepEqual(f.commands.get('block:exact-0').argv.slice(-2), ['--host-client', f.options.client]);
  for (let i = 0; i < n; i++) assert.deepEqual(rectangles[label(roster[i])], [i % 2 ? 0.65 : 0.3, Math.floor(i / 2) / (n / 2), 0.35, 1 / (n / 2)]);
  assert.deepEqual(f.view.windows[0].layers[0].blocks.map(b => b.label), ['Board', ...roster.slice(0, n).map(label)]);
  assert.equal(before.equals(await readFile(join(f.run, 'launch.json'))), true);
  assert.equal((await stat(join(f.run, 'rex-launch.json'))).mode & 0o077, 0);
  assert.ok(!JSON.stringify(result).includes('PRIVATE_TOKEN'));
  assert.ok(!(await readFile(join(f.run, 'rex-launch.json'), 'utf8')).includes('PRIVATE_TOKEN'));
  for (const s of f.sessions.values()) { assert.equal(s.name, s.root.name); s.toolReady = true; }
  const ready = await f.exec('verify'); assert.equal(ready.ready, true); assert.equal(ready.requiresHostReload, false);
  assert.equal(f.calls.sends, 0);
});

test('eight models against frozen four actors refuses before SDK, process, file-state or UI side effects', async t => {
  const f = await fixture(t, 4);
  await writeFile(f.options.models, JSON.stringify(Object.fromEntries(roster.map(actor => [actor, { provider: 'p', modelId: 'm' }]))));
  await assert.rejects(f.exec('open'), /roster mismatch/);
  assert.equal(f.calls.create.length, 0); assert.equal(f.calls.windows.length, 0); assert.equal(f.calls.serverStarts, 0);
  await assert.rejects(readFile(join(f.run, 'rex-launch.json')), { code: 'ENOENT' });
});

test('board config eight vs frozen four is refused before side effects', async t => {
  const f = await fixture(t, 4);
  await writeFile(join(f.run, 'config.json'), JSON.stringify({ workspace: f.workspace, actors: Object.fromEntries(roster.map(a => [a, 'private'])) }));
  await assert.rejects(f.exec('open'), /Board\/launch roster mismatch/);
  assert.equal(f.calls.create.length, 0); assert.equal(f.calls.serverStarts, 0);
});

test('replay open has no duplicate sessions, windows, roots or boardservers', async t => {
  const f = await fixture(t);
  await f.exec('open');
  const stateBefore = await readFile(join(f.run, 'rex-launch.json'), 'utf8');
  await f.exec('open');
  assert.equal(f.calls.create.length, 8); assert.equal(f.keys.size, 8);
  assert.equal(f.calls.windows.length, 1); assert.equal(f.calls.serverStarts, 1); assert.equal(f.calls.sends, 0);
  assert.equal(await readFile(join(f.run, 'rex-launch.json'), 'utf8'), stateBefore);
});

test('lost SDK creation response replays exact stable key/body; no duplicate actor session', async t => {
  const f = await fixture(t, 2); f.loseCreation();
  await assert.rejects(f.exec('open'), /Lost accepted creation/);
  await f.exec('open');
  assert.equal(f.keys.size, 2); assert.equal(f.calls.create.length, 3);
  assert.deepEqual(f.calls.create[0], f.calls.create[1]);
});

test('ambiguous Rex outcome fails closed on replay rather than opening another tab', async t => {
  const f = await fixture(t, 2); f.loseWindow();
  await assert.rejects(f.exec('open'), /Lost Rex response/);
  await assert.rejects(f.exec('open'), /Ambiguous Rex window/);
  assert.equal(f.calls.windows.length, 1); assert.equal(f.view.windows.length, 1); assert.equal(f.calls.serverStarts, 1);
});

for (const [name, mutate, pattern] of [
  ['wrong exact Host identity', f => { const first = f.sessions.values().next().value; first.id = 'different'; }, /identity\/workspace/],
  ['wrong model', f => { f.sessions.values().next().value.model = { provider: 'p', modelId: 'substituted' }; }, /model mismatch/],
  ['wrong root name', f => { f.sessions.values().next().value.root.name = 'Other'; }, /root name mismatch/],
  ['wrong session name', f => { f.sessions.values().next().value.name = 'Other'; }, /session name mismatch/],
  ['wrong pane label', f => { f.view.windows[0].layers[0].blocks[1].label = 'Not Alice'; }, /Pane label mismatch/],
  ['wrong pane attached session', f => { f.commands.get('block:exact-1').argv = ['/native', '--session', 'foreign']; }, /wrong exact Host session/],
  ['observer without Host client', f => { f.commands.get('block:exact-0').argv.splice(-2); }, /Wrong board observer/],
  ['observer with wrong Host client', f => { f.commands.get('block:exact-0').argv.splice(-1, 1, '/wrong/client.json'); }, /Wrong board observer/],
  ['board right instead of left', f => { f.view.windows[0].layers[0].layout.split.ratio = 0.7; }, /pane ratio/],
  ['wrong Rex session', f => { f.view.session_id = 'session:other'; }, /Wrong Rex session/],
]) test(`verify rejects ${name}`, async t => {
  const f = await fixture(t, 2); await f.exec('open'); mutate(f);
  await assert.rejects(f.exec('verify'), pattern);
});

test('existing lower-level SDK team without Rex state refuses rather than creating another team', async t => {
  const f = await fixture(t, 2);
  await writeFile(join(f.run, 'sdk-launch.json'), JSON.stringify({ version: 1, actors: {} }), { mode: 0o600 });
  await assert.rejects(f.exec('open'), /already SDK-bound/);
  assert.equal(f.calls.create.length, 0); assert.equal(f.calls.windows.length, 0);
});

test('ambiguous detached server spawn is not blindly repeated', async t => {
  const f = await fixture(t, 2);
  f.board.start = async () => { f.calls.serverStarts++; throw Error('Ambiguous spawn'); };
  await assert.rejects(f.exec('open'), /Ambiguous spawn/);
  await assert.rejects(f.exec('open'), /Ambiguous board spawn/);
  assert.equal(f.calls.serverStarts, 1); assert.equal(f.calls.windows.length, 0);
});

test('old Host reports registered requiresHostUpgrade without reload, refresh or bootstrap', async t => {
  const f = await fixture(t, 2); f.runtime.supported = false;
  const opened = await f.exec('open');
  assert.equal(opened.registered, true); assert.equal(opened.ready, false);
  assert.equal(opened.requiresHostUpgrade, true); assert.equal(opened.requiresHostReload, false);
  assert.match(opened.next, /Host upgrade/);
  const paths = [join(f.run, 'rex-launch.json'), join(f.run, 'sdk-launch.json'), f.options.bindings];
  const before = await Promise.all(paths.map(path => readFile(path, 'utf8')));
  const verified = await f.exec('verify');
  assert.equal(verified.requiresHostUpgrade, true);
  assert.deepEqual(await Promise.all(paths.map(path => readFile(path, 'utf8'))), before);
  assert.equal(f.calls.refresh.length, 0); assert.equal(f.calls.sends, 0);
});

test('hot refresh refusal leaves exact binding durable and no UI; replay reuses created identities', async t => {
  const f = await fixture(t, 2); f.runtime.refuse = true;
  await assert.rejects(f.exec('open'), /refresh refused/);
  assert.equal(f.calls.windows.length, 0); assert.equal(f.calls.serverStarts, 0); assert.equal(f.calls.sends, 0);
  const ids = [...f.sessions.keys()];
  const registry = await load(f.options.bindings);
  assert.deepEqual(Object.keys(registry.sessions), ids);
  f.runtime.refuse = false;
  assert.equal((await f.exec('open')).ready, true);
  assert.equal(f.calls.create.length, 2); assert.deepEqual([...f.sessions.keys()], ids);
});

test('ready busy team replay skips protocol refresh and preserves exact panes', async t => {
  const f = await fixture(t, 2); const opened = await f.exec('open');
  for (const session of f.sessions.values()) session.root.busy = true;
  f.client.protocol = async () => { throw Error('Do not query protocol for ready team'); };
  f.client.request = async () => { throw Error('Never refresh ready busy team'); };
  const replay = await f.exec('open');
  assert.equal(replay.ready, true); assert.equal(replay.windowId, opened.windowId);
  assert.equal(f.calls.create.length, 2); assert.equal(f.calls.windows.length, 1);
  assert.equal(f.calls.refresh.length, 2); assert.equal(f.calls.sends, 0);
});

test('refresh success without offered tool cannot open panels or bootstrap', async t => {
  const f = await fixture(t, 2); f.runtime.noOffer = true;
  await assert.rejects(f.exec('open'), /did not offer delm_wait/);
  assert.equal(f.calls.windows.length, 0); assert.equal(f.calls.serverStarts, 0); assert.equal(f.calls.sends, 0);
});

test('verify reads only, while missing delm_wait is readiness false not invented runtime success', async t => {
  const f = await fixture(t, 4); await f.exec('open');
  for (const session of f.sessions.values()) session.toolReady = false;
  const before = await readFile(join(f.run, 'rex-launch.json'), 'utf8');
  const refreshCount = f.calls.refresh.length;
  const result = await f.exec('verify');
  assert.equal(result.ready, false); assert.equal(result.requiresRuntimeRefresh, true);
  assert.equal(result.requiresHostUpgrade, false); assert.equal(result.requiresHostReload, false);
  assert.equal(f.calls.refresh.length, refreshCount, 'Verify never performs refresh');
  assert.equal(result.runningTeamClaimed, false); assert.equal(f.calls.sends, 0);
  assert.equal(await readFile(join(f.run, 'rex-launch.json'), 'utf8'), before);
});
