#!/usr/bin/env node
/** Operator-only current Host adapter. Never creates sessions, imports model input, or rewrites launch.json. */
import { createHash, randomUUID } from 'node:crypto';
import { open, readFile, realpath, rename, lstat, unlink } from 'node:fs/promises';
import { dirname, join, resolve, isAbsolute } from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const fail = message => { throw new Error(message); };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.length > 0;
const json = async file => JSON.parse(await readFile(file, 'utf8'));

export async function privateFile(file) {
  const stat = await lstat(file);
  if (!stat.isFile() || stat.isSymbolicLink() || (stat.mode & 0o077) || stat.uid !== process.getuid())
    fail('Operator JSON must be an owner-only regular file');
  return json(file);
}

export async function save(file, value) {
  const temporary = `${file}.${randomUUID()}.tmp`;
  const fd = await open(temporary, 'wx', 0o600);
  try {
    await fd.writeFile(JSON.stringify(value, null, 2) + '\n');
    await fd.sync();
  } finally { await fd.close(); }
  await rename(temporary, file);
  const directory = await open(dirname(file), 'r');
  try { await directory.sync(); } finally { await directory.close(); }
}

async function frozen(file, parent, expected) {
  if (!text(file) || !isAbsolute(file) || await realpath(dirname(file)) !== parent ||
      (await lstat(file)).isSymbolicLink()) fail('Frozen input escapes prepared run');
  const bytes = await readFile(file);
  if (hash(bytes) !== expected) fail('Frozen input SHA mismatch');
  return bytes;
}

export async function prepared(run) {
  const bytes = await readFile(join(run, 'launch.json'));
  const legacy = JSON.parse(bytes.toString('utf8'));
  if (legacy.schema !== 2 || legacy.run !== run || !text(legacy.id) ||
      !text(legacy.workspace) || !object(legacy.actors) || !Object.keys(legacy.actors).length ||
      !object(legacy.inputs) || !Array.isArray(legacy.inputs.references)) fail('Unsupported prepared launch.json');
  const inputs = [];
  for (const [type, record] of [
    ...['prompt', 'plan', 'global_agents', 'project_agents'].map(type => [type, legacy.inputs[type]]),
    ...legacy.inputs.references.map((record, i) => [`reference:${i}`, record]),
  ]) {
    if (!object(record)) fail('Missing approved input');
    await frozen(record.captured, join(run, 'inputs'), record.sha256);
    inputs.push({ type, path: record.captured, sha256: record.sha256 });
  }
  const worker = join(run, 'WORKER.md');
  if (await realpath(worker) !== worker) fail('Worker instructions escape prepared run');
  inputs.push({ type: 'worker', path: worker, sha256: hash(await readFile(worker)) });
  const actors = {};
  for (const [actor, record] of Object.entries(legacy.actors)) {
    if (!/^[A-Za-z0-9_-]+$/.test(actor) || !object(record)) fail('Invalid prepared actor');
    const start = join(run, actor, 'START.md');
    if (await realpath(start) !== start) fail('Actor instructions escape prepared run');
    inputs.push({ type: `actor-start:${actor}`, path: start, sha256: hash(await readFile(start)) });
    const file = join(run, actor, 'records/bootstrap-input.txt');
    const bytes = await frozen(file, join(run, actor, 'records'), record.bootstrap_sha256);
    const content = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    // Do not regenerate the prepare bootstrap: its exact bytes are the approved submission.
    if (!content || !Buffer.from(content).equals(bytes)) fail('Invalid UTF-8 bootstrap');
    actors[actor] = { content, input: { type: 'bootstrap', path: file, sha256: hash(bytes) } };
  }
  return { legacy, actors, inputs, launchSha256: hash(bytes) };
}

export function validateBindings(bindings) {
  if (!object(bindings) || bindings.version !== 1 || !object(bindings.sessions)) fail('Invalid binding file');
  for (const record of Object.values(bindings.sessions)) {
    if (!object(record) || !text(record.run) || !text(record.actor) || !text(record.workspace) ||
        typeof record.enabled !== 'boolean') fail('Invalid session binding');
  }
  return bindings;
}

export async function exactRoot(client, hostId, workspace, rootId) {
  const session = await client.session(hostId).get();
  if (session.id !== hostId || session.cwd !== workspace || !Array.isArray(session.agents))
    fail('Host session identity/workspace mismatch');
  const roots = session.agents.filter(agent => agent.kind === 'root');
  // Current Host composition and native terminal bind exclusively to owner root 1.
  if (roots.length !== 1 || roots[0].id !== 1 ||
      (rootId !== undefined && roots[0].id !== rootId)) fail('Host root identity mismatch');
  return roots[0];
}

export async function runtimeRefreshSupported(client) {
  const protocol = await client.protocol();
  return Array.isArray(protocol?.capabilities) && protocol.capabilities.includes('runtime-refresh.v1');
}

async function runtimeTool(client, record, workspace) {
  const root = await exactRoot(client, record.hostId, workspace, record.rootId);
  const detail = await client.agent(record.hostId, root.id).get();
  if (detail.id !== root.id || detail.sessionId !== record.hostId || !Array.isArray(detail.tools))
    fail('Host runtime tool identity mismatch');
  return { root, ready: detail.tools.some(tool => tool.name === 'delm_wait' && tool.offered === true) };
}

/** Only bind may hot-attach. A successful endpoint receipt is not proof of offered tools. */
async function refreshBoundRuntime(client, state, bindings, stateFile) {
  const missing = [];
  let disabled = false;
  for (const [actor, record] of Object.entries(state.actors)) {
    if (!bindings.sessions[record.hostId].enabled) { disabled = true; continue; }
    const current = await runtimeTool(client, record, state.workspace);
    if (!current.ready) missing.push({ actor, record, root: current.root });
  }
  if (!missing.length) return { ready: !disabled, requiresHostUpgrade: false, requiresRuntimeRefresh: false };
  if (!await runtimeRefreshSupported(client))
    return { ready: false, requiresHostUpgrade: true, requiresRuntimeRefresh: false,
      missingActors: missing.map(item => item.actor), next: 'Operator Host upgrade required for runtime-refresh.v1; no restart or prompt was performed.' };
  for (const { record, root } of missing) {
    if (root.busy) fail('Selected session must be idle for runtime refresh; no prompt or restart performed');
    record.runtimeRefresh = { phase: 'requesting' };
    await save(stateFile, state);
    // Backend owns the selected-session idle check; never inspect or stop unrelated sessions.
    const receipt = await client.request('POST', `/v1/sessions/${encodeURIComponent(record.hostId)}/runtime/refresh`, {},
      { requiredCapabilities: ['runtime-refresh.v1'] });
    if (receipt?.sessionId !== record.hostId || receipt.refreshed !== true) fail('Invalid runtime refresh receipt');
    record.runtimeRefresh = { phase: 'refreshed', sessionId: receipt.sessionId, refreshed: true };
    await save(stateFile, state);
    if (!(await runtimeTool(client, record, state.workspace)).ready)
      fail('Runtime refresh did not offer delm_wait; bootstrap remains forbidden');
  }
  return { ready: !disabled, requiresHostUpgrade: false, requiresRuntimeRefresh: false };
}

/** Tests inject a deterministic SDK client; production imports only an operator CLI-selected module. */
export async function operate(options, client) {
  const { action } = options;
  if (!['bind', 'start', 'status', 'stop', 'resume'].includes(action)) fail('Unsupported operation');
  const run = await realpath(options.run);
  const bindingsFile = resolve(options.bindings);
  const stateFile = join(run, 'sdk-launch.json');
  // A single lock serializes all runs sharing the operator binding registry.
  // Never auto-steal after a crash: operator must inspect and remove the stale lock.
  const lockFile = `${bindingsFile}.delm-lock`;
  const lock = await open(lockFile, 'wx', 0o600);
  try {
    const bindings = validateBindings(await privateFile(bindingsFile));
    if (action === 'bind') {
      const preparedRun = await prepared(run);
      const { legacy, actors, inputs, launchSha256 } = preparedRun;
      const map = await privateFile(resolve(options.map));
      if (!object(map) || JSON.stringify(Object.keys(map).sort()) !== JSON.stringify(Object.keys(actors).sort()) ||
          Object.values(map).some(id => !text(id)) || new Set(Object.values(map)).size !== Object.keys(map).length)
        fail('Map must contain every actor once with distinct exact Host session IDs');
      const exists = await lstat(stateFile).then(() => true, error => error.code === 'ENOENT' ? false : Promise.reject(error));
      const previous = exists ? await privateFile(stateFile) : null;
      if (previous && (previous.version !== 1 || previous.run !== run || previous.workspace !== legacy.workspace ||
          previous.launchSha256 !== launchSha256 || previous.bindingsFile !== bindingsFile || previous.endpoint !== client.baseUrl ||
          JSON.stringify(Object.keys(previous.actors ?? {}).sort()) !== JSON.stringify(Object.keys(map).sort())))
        fail('Existing SDK launch identity mismatch; never rebind');
      const state = previous ?? { version: 1, run, runId: legacy.id, workspace: legacy.workspace,
        bindingsFile, endpoint: client.baseUrl, launchSha256, inputs, actors: {} };
      for (const [actor, hostId] of Object.entries(map)) {
        const binding = bindings.sessions[hostId];
        if (binding && (!previous || binding.run !== run || binding.actor !== actor || binding.workspace !== legacy.workspace))
          fail('Host session already has a binding; refusing reassignment');
        const priorActor = previous?.actors[actor];
        if (priorActor && priorActor.hostId !== hostId) fail('Existing SDK actor mapping changed; never rebind');
        const root = await exactRoot(client, hostId, legacy.workspace, priorActor?.rootId);
        const requestId = `delm-bootstrap:${legacy.id}:${actor}`;
        if (requestId.length > 128) fail('Prepared request ID exceeds Host limit');
        if (!priorActor) state.actors[actor] = { hostId, rootId: root.id, input: actors[actor].input, requestId,
          whenBusy: 'followUp', phase: 'bound' };
      }
      // Identity, approved fingerprints and stable IDs reach disk BEFORE publishing enabled bindings or send.
      await save(stateFile, state);
      for (const [actor, record] of Object.entries(state.actors))
        if (!Object.hasOwn(bindings.sessions, record.hostId))
          bindings.sessions[record.hostId] = { run, actor, workspace: legacy.workspace, enabled: true };
      await save(bindingsFile, bindings);
      const readiness = await refreshBoundRuntime(client, state, bindings, stateFile);
      return { operation: action, actors: Object.keys(state.actors), registered: true, ...readiness, sent: false };
    }
    const state = await privateFile(stateFile);
    if (state.version !== 1 || state.run !== run || state.bindingsFile !== bindingsFile || state.endpoint !== client.baseUrl ||
        !object(state.actors) || !Object.keys(state.actors).length) fail('SDK launch identity mismatch');
    const entries = Object.entries(state.actors);
    for (const [actor, record] of entries) {
      const binding = bindings.sessions[record.hostId];
      if (!binding || binding.run !== run || binding.actor !== actor || binding.workspace !== state.workspace)
        fail('Binding identity mismatch; reconcile operator registry');
    }
    if (action === 'resume' || action === 'stop') {
      for (const [, record] of entries) bindings.sessions[record.hostId].enabled = action === 'resume';
      await save(bindingsFile, bindings); // stop MUST disable tools before any Host abort.
      if (action === 'resume') return { operation: action, enabled: true, sent: false };
      const results = [];
      for (const [actor, record] of entries) {
        // Failure of one Host root must not prevent stopping the other bound actors.
        const outcome = await exactRoot(client, record.hostId, state.workspace, record.rootId)
          .then(() => client.agent(record.hostId, record.rootId).abort(false))
          .then(receipt => ({ ok: true, receipt }), () => ({ ok: false }));
        if (outcome.ok) record.stopReceipt = outcome.receipt;
        await save(stateFile, state);
        results.push({ actor, rootAborted: outcome.ok });
      }
      return { operation: action, enabled: false, complete: results.every(result => result.rootAborted), results,
        scope: 'Bound foreground roots only. Independent/background waiter cancellation unsupported by this adapter; no unrelated tasks aborted.' };
    }
    if (action === 'status') {
      const actors = [];
      for (const [actor, record] of entries) {
        const root = await exactRoot(client, record.hostId, state.workspace, record.rootId);
        const tasks = await client.session(record.hostId).tasks('live', 100);
        actors.push({ actor, hostId: record.hostId, rootId: record.rootId, enabled: bindings.sessions[record.hostId].enabled,
          phase: record.phase, requestId: record.requestId, submissionId: record.receipt?.submissionId,
          busy: root.busy, liveRootTaskIds: tasks.filter(task => task.conversationId === record.rootId).map(task => task.id) });
      }
      return { operation: action, actors };
    }
    const current = await prepared(run);
    if (current.launchSha256 !== state.launchSha256 || JSON.stringify(current.inputs) !== JSON.stringify(state.inputs))
      fail('Prepared manifest changed after binding');
    // Validate ALL actors before sending to any of them.
    for (const [actor, record] of entries) {
      if (!bindings.sessions[record.hostId].enabled) fail('Binding disabled; resume enables without submitting');
      if (JSON.stringify(current.actors[actor]?.input) !== JSON.stringify(record.input) ||
          record.requestId !== `delm-bootstrap:${state.runId}:${actor}` || record.whenBusy !== 'followUp')
        fail('SDK submission identity changed');
      if (!(await runtimeTool(client, record, state.workspace)).ready)
        fail('Registered runtime is not ready; bind must attach delm_wait before bootstrap');
    }
    for (const [actor, record] of entries) {
      if (record.receipt) continue;
      record.phase = 'sending';
      await save(stateFile, state);
      // On an ambiguous outcome leave 'sending'. Retry exact same bytes/key; Host admission ledger deduplicates.
      const receipt = await client.agent(record.hostId, record.rootId)
        .send(current.actors[actor].content, record.whenBusy, record.requestId, 0);
      if (!Number.isSafeInteger(receipt?.submissionId) || !['queued', 'pending', 'done', 'unanswered'].includes(receipt.status))
        fail('Unsupported Host send receipt; preserved stable request for reconciliation');
      record.receipt = { submissionId: receipt.submissionId, status: receipt.status };
      record.phase = 'accepted';
      await save(stateFile, state);
    }
    return { operation: action, actors: entries.map(([actor, record]) => ({ actor, ...record.receipt })) };
  } finally {
    await lock.close();
    await unlink(lockFile);
  }
}

export async function main(argv = process.argv.slice(2)) {
  const [action, ...args] = argv;
  const options = { action };
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i]?.replace(/^--/, '');
    if (!args[i]?.startsWith('--') || !['run', 'client', 'sdk', 'bindings', 'map'].includes(key) ||
        !args[i + 1] || Object.hasOwn(options, key)) fail('Usage: delm_host.mjs bind|start|status|stop|resume --run RUN --client FILE --bindings FILE [--sdk FILE] [--map FILE]');
    options[key] = args[i + 1];
  }
  if (!options.run || !options.client || !options.bindings || (action === 'bind' && !options.map)) fail('Explicit run, client, bindings (and bind map) required');
  return operate(options, await createClient(options));
}

/** Client module paths come only from operator CLI options, never run/model JSON. */
export async function createClient(options) {
  const config = await privateFile(resolve(options.client));
  if (!object(config) || Object.keys(config).some(key => !['url', 'baseUrl', 'token'].includes(key)) ||
      !text(config.token) || (Object.hasOwn(config, 'url') === Object.hasOwn(config, 'baseUrl')) ||
      !text(config.url ?? config.baseUrl)) fail('Client JSON requires token and exactly one of url or baseUrl');
  const endpoint = new URL(config.url ?? config.baseUrl);
  if (endpoint.protocol !== 'http:' || !['127.0.0.1', '[::1]', 'localhost'].includes(endpoint.hostname) ||
      endpoint.username || endpoint.password || endpoint.pathname !== '/' || endpoint.search || endpoint.hash)
    fail('Client endpoint must be private HTTP loopback origin');
  // No SDK import paths are accepted in client/map/launch JSON or model parameters.
  const sdk = options.sdk ? resolve(options.sdk) : createRequire(import.meta.url).resolve('dpi-sdk');
  const { DpiClient } = await import(pathToFileURL(await realpath(sdk)).href);
  if (typeof DpiClient !== 'function') fail('SDK must export DpiClient');
  return new DpiClient(endpoint.origin, config.token);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().then(result => {
    process.stdout.write(JSON.stringify(result) + '\n');
    if (result.complete === false) process.exitCode = 1;
  }, () => {
    // Host/network errors can contain credentials, paths or request bodies. Never echo them.
    process.stderr.write('DeLM Host operation failed; inspect private files and reconcile before retrying.\n');
    process.exitCode = 1;
  });
}
