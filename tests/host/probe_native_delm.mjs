// Genuine official Native transport -> actual product DeLM facet. Never constructs Harness/registry.
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
import { realpath } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import assert from 'node:assert/strict';
const source = process.env.DELM_PUBLIC_HOST_SOURCE;
const socket = process.env.DELM_PUBLIC_HOST_SOCKET;
const load = path => import(pathToFileURL(join(source, path)).href);
const { BACKGROUND_CONTEXT: context } = await load('packages/chord/src/context/index.ts');
const { defineService } = await load('packages/chord/src/index.ts');
const { openClientRuntime, activateBuiltinClientServices } = await load('packages/coding-agent/src/experimental/client-runtime.ts');
const DeLMControl = defineService('delm.control');
// Intentionally omit local:true here: the real SERVER must reject even a malicious remote definition.
const ForbiddenRemoteOwner = defineService('pi.durable-session');
const runtime = await openClientRuntime({command: 'client', connect: {transport: 'unix', path: socket}});
const results = [];
try {
  const server = await activateBuiltinClientServices(runtime.servers[0]);
  for (let actor = 0; actor < 2; actor++) {
    const sessionId = randomUUID();
    await server.management.create({id: sessionId}, context);
    await server.plugins.prepareSession({sessionId, packagePaths: null}, context);
    await server.management.attach(sessionId, context);
    await server.session.whenAttached(sessionId, context);
    const binding = server.session.open({services: [DeLMControl], assertAccess() {}, onError() {}});
    try {
      await binding.ready(context);
      const control = binding.use(DeLMControl);
      const actual = await control.identity(context);
      assert.equal(actual.protocol, 1);
      assert.equal(actual.identity.sessionId, sessionId);
      assert.equal(actual.identity.workspace, await realpath(process.env.DELM_NATIVE_EXPECTED_WORKSPACE));
      assert.equal(actual.identity.sessionPath, await realpath(join(process.env.DELM_NATIVE_EXPECTED_SESSIONS, sessionId, 'session.sqlite')));
      assert.equal(actual.identity.conversationId, 1);
      assert(actual.identity.instanceId);
      assert.equal(actual.binding, null);
      // This public host intentionally redacts internal exception text on the wire.
      await assert.rejects(control.status({identity: actual.identity}, context), error => error.code === 'internal_error');
      const forbidden = server.session.open({services: [ForbiddenRemoteOwner], assertAccess() {}, onError() {}});
      try {
        await assert.rejects((async () => {
          await forbidden.ready(context);
          return forbidden.use(ForbiddenRemoteOwner).get(context);
        })(), error => error.code === 'internal_error');
      } finally { await forbidden.dispose(context); }
      // Original Native controller is still usable with the product facet installed.
      const accepted = await server.agent.prompt({message: `native real DeLM facet actor ${actor}`, images: null}, context);
      assert(accepted.accepted);
      const answer = await server.agent.waitForPrompt(accepted.operationId, context);
      assert.equal(answer.status, 'done');
      assert.equal(answer.text, 'HOST_FIXTURE_ACK');
      results.push({actor, sessionId, identity: actual.identity, actualDeLMFacet: true,
        remoteOwnerCapabilityDeniedByServer: true, unboundControlRejected: true, originalNativeControllerUsable: true});
    } finally { await binding.dispose(context); }
    await server.management.detach(context);
  }
  assert.notEqual(results[0].identity.instanceId, results[1].identity.instanceId);
  console.log(JSON.stringify({actors: results, model: 'deterministic localhost HTTP', constructedHarness: false,
    fakeHostOrDiscoveryOrAdmission: false, boundDeLMBoardFlow: 'NOT_YET_TESTED'}));
} finally { await runtime.dispose(); }
