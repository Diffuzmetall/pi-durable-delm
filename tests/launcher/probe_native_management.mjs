// TEST ONLY: baseline the official Native presentation client against the same isolated server.
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
const load = file => import(pathToFileURL(join(process.env.DELM_PUBLIC_HOST_SOURCE, file)).href);
const { openClientRuntime, activateBuiltinClientServices } = await load('packages/coding-agent/src/experimental/client-runtime.ts');
const runtime = await openClientRuntime({command: 'client', connect: {transport: 'unix', path: process.env.DELM_PUBLIC_HOST_SOCKET}});
try {
  const server = await activateBuiltinClientServices(runtime.servers[0]);
  console.log(JSON.stringify({officialClientConnected: true, serverId: server.client.serverId,
    existingSessionCount: server.directory.state.value.sessions.length}));
} finally { await runtime.dispose(); }
