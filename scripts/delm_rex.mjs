#!/usr/bin/env node
/** Single frozen roster -> current Host bindings and one Rex tab. Never submits a prompt or restarts Host. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { access, lstat, open, readFile, realpath, unlink } from 'node:fs/promises';
import { constants } from 'node:fs';
import { join, resolve } from 'node:path';
import { execFile, spawn } from 'node:child_process';
import { promisify } from 'node:util';
import { pathToFileURL } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';
import { prepared, privateFile, save, exactRoot, validateBindings, operate, createClient, runtimeRefreshSupported } from './delm_host.mjs';

const exec = promisify(execFile);
const rosterNames = ['alice', 'bob', 'carol', 'dave', 'eve', 'frank', 'grace', 'heidi'];
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const title = actor => actor[0].toUpperCase() + actor.slice(1);
const same = (a, b, message) => assert.deepEqual(a, b, message);
const exists = path => lstat(path).then(() => true, error => { if (error.code === 'ENOENT') return false; throw error; });
const split = (direction, before, after, ratio = 0.5) => ({ split: { direction, before, after, ratio } });
const terminal = (label, command, cwd) => ({ block: { flavor: 'com.superlogical.terminal.shell', label,
  options: { command, cwd, shell: 'none', exit: { on_completion: false } } } });

export function makeLayout(roster, records, native, workspace, boardCommand) {
  const rows = [];
  for (let i = 0; i < roster.length; i += 2)
    rows.push(split('horizontal', ...roster.slice(i, i + 2).map(actor =>
      terminal(title(actor), [native, '--session', records[actor].hostId], workspace))));
  // Equal-height rows, rather than successively halving the last row.
  let grid = rows.at(-1);
  for (let i = rows.length - 2; i >= 0; i--) grid = split('vertical', rows[i], grid, 1 / (rows.length - i));
  return split('horizontal', terminal('Board', boardCommand, workspace), grid, 0.3);
}

/** Native control CLI only; no socket protocol or GUI automation. */
export function rexAdapter(session) {
  const call = async (method, args = {}) => JSON.parse((await exec('rex',
    ['--autostart=false', '--timeout', '20s', 'api', 'call', '-s', session, method, JSON.stringify({ session_id: session, ...args })],
    { timeout: 25_000, maxBuffer: 2 * 1024 * 1024 })).stdout);
  return {
    inspect: () => call('session.view'),
    newWindow: request => call('session.new_window', request),
    async command(blockId) {
      const process = await call('block.method', { block_id: blockId, method: 'process' });
      assert(process.last_exit === null && Number.isSafeInteger(process.child?.pid), 'Pane program is not running');
      const pid = process.child.pid;
      assert.equal((await lstat(`/proc/${pid}`)).uid, globalThis.process.getuid(), 'Foreign pane process');
      return { argv: (await readFile(`/proc/${pid}/cmdline`, 'utf8')).split('\0').filter(Boolean),
        cwd: await realpath(`/proc/${pid}/cwd`) };
    },
  };
}

/** Separate process group survives Rex pane/observer closure. Never terminate or steal an existing board. */
export function boardAdapter(run, packageRoot) {
  const script = join(packageRoot, 'scripts/delm_local.py');
  const command = ['python3', '-B', script, 'serve', run, '--port', '0'];
  return {
    async start() {
      assert(!await exists(join(run, 'endpoint.json')), 'Existing board endpoint: reconcile rather than create another server');
      const log = await open(join(run, 'rex-board-server.log'), 'a', 0o600);
      try {
        const child = spawn(command[0], command.slice(1), { cwd: run, detached: true,
          stdio: ['ignore', log.fd, log.fd], env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } });
        await new Promise((resolve, reject) => { child.once('spawn', resolve); child.once('error', reject); });
        child.unref();
        const stat = await readFile(`/proc/${child.pid}/stat`, 'utf8');
        return { pid: child.pid, startTicks: stat.slice(stat.lastIndexOf(')') + 2).split(' ')[19] };
      } finally { await log.close(); }
    },
    async verify(record) {
      assert(Number.isSafeInteger(record?.pid), 'Board process receipt missing');
      const stat = await readFile(`/proc/${record.pid}/stat`, 'utf8');
      assert.equal(stat.slice(stat.lastIndexOf(')') + 2).split(' ')[19], record.startTicks, 'Board PID reused');
      same((await readFile(`/proc/${record.pid}/cmdline`, 'utf8')).split('\0').filter(Boolean).slice(1), command.slice(1), 'Wrong board process');
      // Python serve writes endpoint.json after acquiring its exclusive server.lock and binding the socket.
      const endpoint = JSON.parse(await readFile(join(run, 'endpoint.json'), 'utf8'));
      const url = new URL(endpoint.url);
      assert(url.protocol === 'http:' && url.hostname === '127.0.0.1' && url.port && url.pathname === '/' &&
        !url.username && !url.password && !url.search && !url.hash, 'Invalid board endpoint');
      const response = await fetch(url, { method: 'GET', signal: AbortSignal.timeout(2000) });
      await response.body?.cancel(); // GET is read-only; do not submit a snapshot/read/ack or expose actor tokens.
      return true;
    },
  };
}

async function inputs(options) {
  const run = await realpath(options.run);
  const frozen = await prepared(run);
  const configBytes = await readFile(join(run, 'config.json'));
  const config = await privateFile(join(run, 'config.json')); // Contains credentials: never print/copy tokens.
  const roster = Object.keys(frozen.actors).sort();
  assert([2, 4, 8].includes(roster.length), 'Only 2/4/8 frozen actors supported');
  same(roster, rosterNames.slice(0, roster.length).sort(), 'Unsupported frozen actor roster');
  same(Object.keys(config.actors ?? {}).sort(), roster, 'Board/launch roster mismatch; prepare a NEW run with --agents 2/4/8');
  assert.equal(config.workspace, frozen.legacy.workspace, 'Board/launch workspace mismatch');
  const models = await privateFile(resolve(options.models));
  same(Object.keys(models).sort(), roster, 'Models/board roster mismatch; never add panels to a smaller frozen run');
  for (const actor of roster) {
    same(Object.keys(models[actor] ?? {}).sort(), ['modelId', 'provider'], 'Each model requires exactly provider/modelId');
    for (const value of Object.values(models[actor])) assert(typeof value === 'string' && value.trim(), 'Invalid exact model');
  }
  assert(typeof options.session === 'string' && /^session:[A-Za-z0-9-]+$/.test(options.session), 'Exact Rex session ID required');
  const native = resolve(options.native);
  assert((await lstat(native)).isFile() || (await lstat(native)).isSymbolicLink(), 'Native executable missing');
  await access(native, constants.X_OK);
  const packageRoot = await realpath(frozen.legacy.package_root);
  for (const script of ['delm_local.py', 'delm_board.py']) assert((await lstat(join(packageRoot, 'scripts', script))).isFile(), 'Prepared package script missing');
  // Preserve canonical actor order, shared by creation, mapping, layout and verification.
  return { run, frozen, models, roster: rosterNames.slice(0, roster.length), native, packageRoot,
    hostClient: resolve(options.client), configSha256: sha(configBytes) };
}

function checkLayout(view, state) {
  assert.equal(view.session_id, state.rexSession, 'Wrong Rex session');
  const windows = view.windows.filter(window => window.window_id === state.window.windowId);
  assert.equal(windows.length, 1, 'Exact Rex window missing');
  const window = windows[0];
  assert.equal(window.label, state.window.label, 'Rex tab name changed');
  assert(!window.zoomed_block_id, 'Zoom hides board/actor layout');
  assert.equal(window.layers.length, 1, 'Unexpected extra pane layer');
  const layer = window.layers[0];
  assert.equal(layer.kind, 'tiled');
  same(layer.bounds, [0, 0, 1, 1], 'Pane layer does not fill tab');
  const labels = new Map(layer.blocks.map(block => [block.block_id, block.label]));
  const expected = ['Board', ...state.roster.map(title)];
  assert.equal(layer.blocks.length, expected.length, 'Unexpected/missing actor panes');
  const leaves = [];
  function walk(actual, planned) {
    assert(actual, 'Missing pane tree');
    if (planned.block) {
      assert(actual.block_id && !actual.split, 'Expected pane leaf');
      leaves.push(actual.block_id);
      assert.equal(labels.get(actual.block_id), planned.block.label, 'Pane label mismatch');
    } else {
      assert(actual.split && !actual.block_id, 'Expected pane split');
      assert.equal(actual.split.direction, planned.split.direction, 'Wrong left/right grid direction');
      assert(Math.abs(actual.split.ratio - planned.split.ratio) < 0.001, 'Wrong board/grid pane ratio');
      walk(actual.split.before, planned.split.before); walk(actual.split.after, planned.split.after);
    }
  }
  walk(layer.layout, state.window.layout);
  same(leaves, state.window.blockIds, 'Rex pane identity/order changed');
  assert.equal(new Set(leaves).size, expected.length, 'Duplicate pane identity');
  return leaves;
}

async function inspectActor(client, actor, record, workspace, model) {
  const root = await exactRoot(client, record.hostId, workspace, record.rootId);
  const session = await client.session(record.hostId).get();
  const detail = await client.agent(record.hostId, root.id).get();
  assert.equal(session.name, title(actor), 'Host session name mismatch');
  assert.equal(root.name, title(actor), 'Host root name mismatch');
  assert.equal(detail.id, root.id); assert.equal(detail.sessionId, record.hostId);
  assert.equal(detail.name, title(actor)); assert.equal(detail.config.cwd, workspace);
  same(detail.config.model, model, 'Host exact model mismatch');
  return { root, toolReady: detail.tools.some(tool => tool.name === 'delm_wait' && tool.offered === true) };
}

async function verify(current, state, client, rex, board, bindingsFile) {
  const { run, roster, models, frozen } = current;
  const sdk = await privateFile(join(run, 'sdk-launch.json'));
  assert.equal(sdk.endpoint, client.baseUrl, 'SDK endpoint mismatch');
  assert.equal(sdk.run, run); assert.equal(sdk.bindingsFile, bindingsFile);
  assert.equal(sdk.launchSha256, frozen.launchSha256);
  same(sdk.inputs, frozen.inputs, 'Frozen approved SDK inputs changed');
  same(Object.keys(sdk.actors).sort(), [...roster].sort(), 'SDK/board roster mismatch');
  const bindings = validateBindings(await privateFile(bindingsFile));
  const actualRunBindings = Object.entries(bindings.sessions).filter(([, entry]) => entry.run === run);
  same(actualRunBindings.map(([, entry]) => entry.actor).sort(), [...roster].sort(), 'Extra/missing run bindings');
  let missingRuntime = false;
  const actors = [];
  for (const actor of roster) {
    const record = state.actors[actor], bound = sdk.actors[actor];
    assert.equal(bound.hostId, record.hostId); assert.equal(bound.rootId, record.rootId);
    same(bindings.sessions[record.hostId], { run, actor, workspace: frozen.legacy.workspace, enabled: true }, 'Wrong/disabled exact binding');
    const { root, toolReady } = await inspectActor(client, actor, record, frozen.legacy.workspace, models[actor]);
    missingRuntime ||= !toolReady;
    actors.push({ actor, hostId: record.hostId, rootId: root.id, delmWaitAvailable: toolReady });
  }
  assert(state.server?.phase === 'started', 'Board server launch is unresolved');
  await board.verify(state.server.receipt);
  assert(state.window?.phase === 'created', 'Rex window outcome unresolved; reconcile, do not blindly retry');
  const blockIds = checkLayout(await rex.inspect(), state);
  const boardProcess = await rex.command(blockIds[0]);
  same(boardProcess.argv.slice(-6), ['-B', join(current.packageRoot, 'scripts/delm_board.py'), run,
    '--observe', '--host-client', current.hostClient], 'Wrong board observer process');
  for (let i = 0; i < roster.length; i++) {
    const process = await rex.command(blockIds[i + 1]);
    same(process.argv.slice(-2), ['--session', state.actors[roster[i]].hostId], 'Pane attached to wrong exact Host session');
    assert.equal(process.cwd, frozen.legacy.workspace, 'Pane workspace mismatch');
  }
  const supported = missingRuntime ? await runtimeRefreshSupported(client) : true;
  return { operation: 'verify', run, roster, actors, windowId: state.window.windowId,
    layoutVerified: true, boardServerAlive: true, registered: true, ready: !missingRuntime,
    requiresHostUpgrade: missingRuntime && !supported, requiresRuntimeRefresh: missingRuntime && supported,
    requiresHostReload: false, bootstrapSent: false, runningTeamClaimed: false,
    next: missingRuntime ? (supported
      ? 'Rerun open to refresh only the exact registered idle sessions. Verification performs no refresh or bootstrap.'
      : 'Operator Host upgrade required for runtime-refresh.v1; no automatic restart or bootstrap.')
      : 'Use existing delm_host.mjs start explicitly when authorized; panels alone do not prove a running team.' };
}

/** Fake SDK/Rex/board adapters exercise the complete flow without processes, models, networking or UI. */
export async function launch(options, { client, rex, board } = {}) {
  assert(['open', 'verify'].includes(options.action), 'Use open or verify');
  const current = await inputs(options); // ALL roster/config/models validation BEFORE any side effects.
  client ??= await createClient(options);
  rex ??= rexAdapter(options.session);
  board ??= boardAdapter(current.run, current.packageRoot);
  const bindingsFile = resolve(options.bindings);
  validateBindings(await privateFile(bindingsFile));
  const identity = { version: 1, run: current.run, runId: current.frozen.legacy.id, launchSha256: current.frozen.launchSha256,
    configSha256: current.configSha256, models: current.models, roster: current.roster, native: current.native,
    rexSession: options.session, endpoint: client.baseUrl, bindingsFile, packageRoot: current.packageRoot };
  const stateFile = join(current.run, 'rex-launch.json');
  const lockFile = join(current.run, '.rex-launch.lock');
  const lock = options.action === 'open' ? await open(lockFile, 'wx', 0o600) : null;
  try {
    const previous = await exists(stateFile) ? await privateFile(stateFile) : null;
    if (previous) for (const [key, value] of Object.entries(identity)) same(previous[key], value, 'Rex launch identity changed; never silently rebind');
    assert(previous || options.action === 'open', 'No Rex launch state; open explicitly first');
    const state = previous ?? { ...identity, actors: {} };
    if (!previous) assert(!await exists(join(current.run, 'sdk-launch.json')), 'Run already SDK-bound without Rex state; reconcile existing actors, never create a second team');
    if (previous?.window) assert.equal(previous.window.phase, 'created', 'Ambiguous Rex window outcome; inspect/reconcile IDs before retrying');
    if (previous?.server) assert.equal(previous.server.phase, 'started', 'Ambiguous board spawn; reconcile exact existing process');
    if (options.action === 'verify') return await verify(current, state, client, rex, board, bindingsFile);
    assert.equal((await rex.inspect()).session_id, options.session, 'Exact Rex session unavailable');
    await save(stateFile, state);
    for (const actor of current.roster) {
      const name = title(actor);
      const expectedBody = { name, cwd: current.frozen.legacy.workspace, model: current.models[actor] };
      const record = state.actors[actor] ??= { key: `${state.runId}:${actor}`, body: expectedBody };
      assert.equal(record.key, `${state.runId}:${actor}`, 'Creation key changed');
      same(record.body, expectedBody, 'Creation request changed');
      assert(record.key.length <= 128, 'Host idempotency key too long');
      if (!record.hostId) {
        await save(stateFile, state); // Persist exact creation request BEFORE send; SDK ledger safely replays.
        const created = await client.createSession(record.body, record.key);
        assert(typeof created.id === 'string' && created.id, 'Missing exact created session ID');
        record.hostId = created.id;
        await save(stateFile, state);
      }
      const root = await exactRoot(client, record.hostId, current.frozen.legacy.workspace, record.rootId);
      assert.equal(root.id, 1, 'Current native terminal supports only exact owner root 1');
      if (!record.named) {
        record.rootId = root.id;
        await save(stateFile, state);
        await client.session(record.hostId).rename(name);
        await client.agent(record.hostId, root.id).rename(name);
        record.named = true;
        await save(stateFile, state);
      }
      await inspectActor(client, actor, record, current.frozen.legacy.workspace, current.models[actor]);
    }
    const mapFile = join(current.run, 'rex-actor-map.json');
    const map = Object.fromEntries(current.roster.map(actor => [actor, state.actors[actor].hostId]));
    assert.equal(new Set(Object.values(map)).size, current.roster.length, 'Host returned duplicate actor sessions');
    if (await exists(mapFile)) same(await privateFile(mapFile), map, 'Existing actor map changed');
    else await save(mapFile, map);
    await operate({ action: 'bind', run: current.run, bindings: bindingsFile, map: mapFile }, client);
    if (!state.server) {
      state.server = { phase: 'starting' };
      await save(stateFile, state);
      state.server.receipt = await board.start();
      state.server.phase = 'started';
      await save(stateFile, state);
      // Bounded startup probe only; an uncertain creation is NEVER repeated.
      let ready = false;
      for (let i = 0; i < 40; i++) {
        ready = await board.verify(state.server.receipt).then(() => true, () => false);
        if (ready) break;
        await sleep(100);
      }
      assert(ready, 'Board server did not become ready; inspect private log, never blindly start another');
    } else {
      assert.equal(state.server.phase, 'started', 'Ambiguous board spawn; reconcile exact existing process');
      await board.verify(state.server.receipt);
    }
    if (!state.window) {
      const layout = makeLayout(current.roster, state.actors, current.native, current.frozen.legacy.workspace,
        ['python3', '-B', join(current.packageRoot, 'scripts/delm_board.py'), current.run,
          '--observe', '--host-client', current.hostClient]);
      state.window = { phase: 'creating', label: `DeLM ${state.runId}`, layout };
      await save(stateFile, state);
      const receipt = await rex.newWindow({ window_label: state.window.label, layout, focus: false });
      assert(typeof receipt.window_id === 'string' && Array.isArray(receipt.block_ids) &&
        receipt.block_ids.length === current.roster.length + 1 && receipt.block_ids.every(id => typeof id === 'string'), 'Invalid Rex creation receipt');
      Object.assign(state.window, { phase: 'created', windowId: receipt.window_id, blockIds: receipt.block_ids });
      await save(stateFile, state);
    } else assert.equal(state.window.phase, 'created', 'Ambiguous Rex window outcome; inspect/reconcile IDs before retrying');
    const result = await verify(current, state, client, rex, board, bindingsFile);
    return { ...result, operation: 'open' };
  } finally {
    if (lock) { await lock.close(); await unlink(lockFile); }
  }
}

export async function main(argv = process.argv.slice(2)) {
  const [action, ...args] = argv, options = { action };
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i]?.replace(/^--/, '');
    assert(args[i]?.startsWith('--') && ['run', 'models', 'session', 'native', 'client', 'bindings', 'sdk'].includes(key) &&
      args[i + 1] && !Object.hasOwn(options, key), 'Invalid CLI arguments');
    options[key] = args[i + 1];
  }
  for (const key of ['run', 'models', 'session', 'native', 'client', 'bindings', 'sdk']) assert(options[key], `Explicit --${key} required`);
  return launch(options);
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href)
  main().then(result => console.log(JSON.stringify(result)), () => {
    console.error('DeLM Rex launch refused/unresolved. Inspect private rex-launch.json and reconcile exact IDs; no automatic restart or bootstrap.');
    process.exitCode = 1;
  });
