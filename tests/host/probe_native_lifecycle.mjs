// Uses the official Native client/services only. No SQLite access or replacement Harness.
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
import { readFile, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import assert from 'node:assert/strict';

const source = process.env.DELM_PUBLIC_HOST_SOURCE;
const socket = process.env.DELM_PUBLIC_HOST_SOCKET;
const stateFile = process.env.DELM_NATIVE_LIFECYCLE_STATE;
const phase = process.env.DELM_NATIVE_LIFECYCLE_PHASE;
assert(source && socket && stateFile && ['create', 'resume', 'wake'].includes(phase));
const load = path => import(pathToFileURL(join(source, path)).href);
const { BACKGROUND_CONTEXT: context } = await load('packages/chord/src/context/index.ts');
const { openClientRuntime, activateBuiltinClientServices } = await load('packages/coding-agent/src/experimental/client-runtime.ts');
const { ExampleFacetService } = await load('packages/coding-agent/examples/plugins/pi-example-plugin/src/contract.ts');

function waitValue(state, predicate) {
  if (state.value !== undefined && predicate(state.value)) return Promise.resolve(state.value);
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { unsubscribe(); reject(Error('Actual Native replicated state timed out')); }, 12000);
    const unsubscribe = state.subscribe(value => {
      if (predicate(value)) { clearTimeout(timer); unsubscribe(); resolve(value); }
    });
  });
}

const records = phase === 'create'
  ? Array.from({length: 2}, (_, actor) => ({actor, sessionId: randomUUID(), marker: `native-lifecycle-${actor}-${randomUUID()}`}))
  : JSON.parse(await readFile(stateFile, 'utf8'));
const runtime = await openClientRuntime({command: 'client', connect: {transport: 'unix', path: socket}});
const tested = [];
try {
  assert.equal(runtime.servers.length, 1);
  const server = await activateBuiltinClientServices(runtime.servers[0]);
  const expectedAck = phase === 'wake' ? 'NATIVE_DRAFT_WAKE_ACK' : 'HOST_FIXTURE_ACK';
  for (const record of phase === 'wake' ? records.slice(0, 1) : records) {
    if (phase === 'create') await server.management.create({id: record.sessionId}, context);
    else await waitValue(server.directory.state, state => state.sessions.some(s => s.sessionId === record.sessionId));
    await server.plugins.prepareSession({sessionId: record.sessionId, packagePaths: null}, context);
    await server.management.attach(record.sessionId, context);
    await server.session.whenAttached(record.sessionId, context);
    const binding = server.session.open({services: [ExampleFacetService], assertAccess() {}, onError(error) { throw error; }});
    try {
      await binding.ready(context);
      const greeting = await binding.use(ExampleFacetService).greet({name: record.marker}, context);
      assert.equal(greeting.workerActivations, 1);
      if (phase === 'create' || phase === 'wake') {
        const submitted = await server.agent.prompt({message: phase === 'wake' ? 'NATIVE_EXTERNAL_WAKE_NOT_EDITOR' : record.marker, images: null}, context);
        assert.equal(submitted.accepted, true);
        const result = await server.agent.waitForPrompt(submitted.operationId, context);
        assert.equal(result.status, 'done');
        assert.equal(result.text, expectedAck);
      }
      const view = await waitValue(server.transcript.state, state => JSON.stringify(state).includes(record.marker)
        && JSON.stringify(state).includes(expectedAck));
      const text = JSON.stringify(view);
      if (process.env.DELM_NATIVE_FORBIDDEN_DRAFT) assert(!text.includes(process.env.DELM_NATIVE_FORBIDDEN_DRAFT), 'Unsent editor draft entered the actual conversation');
      assert(!text.includes(records.find(r => r.actor !== record.actor).marker), 'Wrong session history was attached');
      tested.push({actor: record.actor, sessionId: record.sessionId, ownHistory: true, otherActorHistory: false,
        actualWorkerPluginActivated: true});
    } finally { await binding.dispose(context); }
    await server.management.detach(context);
  }
  if (phase === 'create') await writeFile(stateFile, JSON.stringify(records));
  console.log(JSON.stringify({phase, sessions: tested, directSqliteAccess: false, mockedHost: false}));
} finally { await runtime.dispose(); }
