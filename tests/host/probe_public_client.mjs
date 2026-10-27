// A client of the unmodified official public server, NOT a host/Harness replacement.
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';

const source = process.env.DELM_PUBLIC_HOST_SOURCE;
if (!source || !process.env.DELM_PUBLIC_HOST_SOCKET) throw Error('Explicit isolated public source/socket required');
const load = path => import(pathToFileURL(join(source, path)).href);
const { BACKGROUND_CONTEXT: context } = await load('packages/chord/src/context/index.ts');
const { openClientRuntime, activateBuiltinClientServices } = await load('packages/coding-agent/src/experimental/client-runtime.ts');
const { ExampleFacetService } = await load('packages/coding-agent/examples/plugins/pi-example-plugin/src/contract.ts');
const runtime = await openClientRuntime({ command: 'client', connect: { transport: 'unix', path: process.env.DELM_PUBLIC_HOST_SOCKET } });
const results = [];
try {
  assert.equal(runtime.servers.length, 1);
  const server = await activateBuiltinClientServices(runtime.servers[0]);
  for (let actor = 0; actor < 2; actor++) {
    const sessionId = randomUUID();
    await server.management.create({ id: sessionId }, context);
    await server.plugins.prepareSession({ sessionId, packagePaths: null }, context);
    await server.management.attach(sessionId, context);
    await server.session.whenAttached(sessionId, context);
    const binding = server.session.open({ services: [ExampleFacetService], assertAccess() {}, onError(error) { throw error; } });
    try {
      await binding.ready(context);
      const reply = await binding.use(ExampleFacetService).greet({ name: `clean-user-${actor}` }, context);
      assert.match(reply.message, /bundled Session worker facet/);
      assert.equal(reply.workerActivations, 1);
      const accepted = await server.agent.prompt({ message: `isolated deterministic host smoke actor ${actor}`, images: null }, context);
      assert.equal(accepted.accepted, true);
      const answer = await server.agent.waitForPrompt(accepted.operationId, context);
      assert.equal(answer.status, 'done');
      assert.equal(answer.text, 'HOST_FIXTURE_ACK');
      results.push({ actor, sessionId, pluginGreet: true, activationCount: reply.workerActivations, modelAnswer: answer.text });
    } finally { await binding.dispose(context); }
    await server.management.detach(context);
  }
  console.log(JSON.stringify({ publicHost: true, officialPluginLoadedInActualWorkers: true, actors: results,
    replacedHarness: false, mockedAdmissionOrDiscovery: false, liveModelCalls: 0 }));
} finally { await runtime.dispose(); }
