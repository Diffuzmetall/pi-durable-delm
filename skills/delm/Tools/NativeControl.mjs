// Short-lived client of the OFFICIAL Native server. Never opens Native storage or owns a Harness.
import { readFileSync, realpathSync } from 'node:fs';
import { basename } from 'node:path';
import { pathToFileURL } from 'node:url';

function currentValue(state, predicate) {
  if (state.value !== undefined && predicate(state.value)) return Promise.resolve(state.value);
  return new Promise((resolve, reject) => {
    let unsubscribe = () => {};
    const timer = setTimeout(() => { unsubscribe(); reject(Error('Native replicated session directory timed out')); }, 15000);
    unsubscribe = state.subscribe(value => {
      if (value !== undefined && predicate(value)) { clearTimeout(timer); unsubscribe(); resolve(value); }
    });
  });
}

export async function nativeControl(request) {
  const { socket, sessionId, action, workspace, run, actor } = request;
  if (![socket, sessionId, workspace, run, actor].every(v => typeof v === 'string' && v.length))
    throw Error('Explicit existing Native socket/exact session/workspace/run/actor required');
  if (!['identity', 'bind', 'input', 'status', 'resume', 'stop'].includes(action)) throw Error('Unknown Native control operation');
  if (request.identity && request.identity.sessionId !== sessionId) throw Error('Recorded Native identity/session ledger mismatch');
  // Public CLIENT libraries only. No import of host internals, source checkout, server or scheduler.
  const { BACKGROUND_CONTEXT: context } = await import('@earendil-works/chord/context');
  const { defineService, createRemoteServiceBinding } = await import('@earendil-works/chord');
  const { Client, createClientServiceTransport } = await import('@earendil-works/pi-client');
  const { createUnixTransportFactory } = await import('@earendil-works/pi-client/unix');
  const DeLMControl = defineService('delm.control');
  const Directory = defineService('pi.session-directory');
  const Management = defineService('pi.session-management');
  const Plugins = defineService('pi.presentation-plugins');
  const serverId = request.serverId ?? basename(socket, '.sock');
  const client = await Client.connect({ serverId, transportFactory: createUnixTransportFactory({ path: socket }) });
  let services, binding, serverBinding;
  let phase = 'management service subscription';
  try {
    serverBinding = createRemoteServiceBinding({ services: [Directory, Management, Plugins], bound: true,
      transport: createClientServiceTransport(client, () => ({ serverId })),
      assertAccess() { if (!client.connected) throw Error('Native server disconnected'); },
      onError(error) { process.stderr.write(`Native management: ${error.message}\n`); } });
    services = { directory: serverBinding.use(Directory), management: serverBinding.use(Management),
      plugins: serverBinding.use(Plugins) };
    // Chord starts a subscription on use(), so acquire handles BEFORE awaiting readiness.
    await serverBinding.ready(context);
    const directory = await currentValue(services.directory.state, () => true);
    if (!directory.sessions.some(session => session.sessionId === sessionId)) {
      if (action !== 'identity' || request.create !== true || request.identity)
        throw Error('Exact recorded Native session absent; no replacement created');
      await services.management.create({ id: sessionId }, context);
    }
    phase = 'plugin preparation';
    await services.plugins.prepareSession({ sessionId, packagePaths: null }, context);
    phase = 'exact session attachment';
    await services.management.attach(sessionId, context);
    if (client.attachment?.sessionId !== sessionId) throw Error('Native did not attach the exact selected session');
    binding = createRemoteServiceBinding({ services: [DeLMControl], bound: true,
      transport: createClientServiceTransport(client, () => client.attachment),
      // Preserve the official client's attachment fence on every service call.
      assertAccess() {
        if (client.attachment?.sessionId !== sessionId) throw Error('Native control attachment changed');
      },
      onError(error) { process.stderr.write(`Native control connection: ${error.message}\n`); } });
    phase = 'DeLM control service subscription';
    const control = binding.use(DeLMControl);
    await binding.ready(context);
    phase = 'DeLM actual identity';
    const actual = await control.identity(context);
    if (actual.protocol !== 1 || actual.identity.sessionId !== sessionId ||
        actual.identity.workspace !== realpathSync(workspace)) throw Error('Unsupported Native protocol or exact session/workspace mismatch');
    for (const key of ['sessionId', 'sessionPath', 'workspace', 'conversationId', 'instanceId']) {
      if (actual.identity[key] === undefined || actual.identity[key] === null) throw Error('Incomplete actual Native identity');
      if (request.identity && request.identity[key] !== actual.identity[key]) throw Error('Exact Native session/instance identity mismatch');
    }
    if (actual.binding && (actual.binding.actor !== actor || actual.binding.run !== realpathSync(run)))
      throw Error('Native session belongs to a different run/actor');
    let result;
    if (action === 'identity') result = actual;
    else {
      if (!request.identity) throw Error('Persist the actual Native identity before any binding/control/input');
      const payload = { ...request.payload, identity: request.identity };
      if (action === 'bind') Object.assign(payload, { run: realpathSync(run), actor });
      result = await control[action](payload, context);
    }
    return { delm_control: 1, serverId, identity: actual.identity, result };
  } catch (error) {
    process.stderr.write(`Native operation phase: ${phase}\n`);
    throw error;
  } finally {
    try { if (binding) await binding.dispose(context); }
    finally {
      // Detach this short-lived client's attachment only, never the user's TUI/session owner.
      try { if (services && client.connected && client.attachment) await services.management.detach(context); }
      finally {
        try { if (serverBinding) await serverBinding.dispose(context); }
        finally { await client.dispose(); }
      }
    }
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try { console.log(JSON.stringify(await nativeControl(JSON.parse(readFileSync(0, 'utf8'))))); }
  catch (error) { console.error(`Native control failed: ${error.stack ?? error.message}`); process.exitCode = 1; }
}
