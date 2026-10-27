// TEST ONLY: observe the actual official Native transcript in our own synthetic sessions.
import { readFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
import assert from 'node:assert/strict';
const state = JSON.parse(await readFile(process.env.DELM_LAUNCHER_MANIFEST, 'utf8'));
const source = process.env.DELM_PUBLIC_HOST_SOURCE;
const load = file => import(pathToFileURL(join(source, file)).href);
const { BACKGROUND_CONTEXT: context } = await load('packages/chord/src/context/index.ts');
const { openClientRuntime, activateBuiltinClientServices } = await load('packages/coding-agent/src/experimental/client-runtime.ts');
function until(view, predicate) {
  if (view.value !== undefined && predicate(view.value)) return Promise.resolve(view.value);
  return new Promise((resolve, reject) => {
    let unsubscribe = () => {};
    const timer = setTimeout(() => { unsubscribe(); reject(Error('Actual Native launcher transcript timed out')); }, 15000);
    unsubscribe = view.subscribe(value => {
      if (value !== undefined && predicate(value)) { clearTimeout(timer); unsubscribe(); resolve(value); }
    });
  });
}
const runtime = await openClientRuntime({command: 'client', connect: {transport: 'unix', path: state.native.socket}});
try {
  const server = await activateBuiltinClientServices(runtime.servers[0]);
  const results = [];
  for (const [actor, record] of Object.entries(state.actors)) {
    await server.management.attach(record.session, context);
    await server.session.whenAttached(record.session, context);
    const update = process.env.DELM_LAUNCHER_EXPECT_UPDATE === 'yes' && actor === 'alice';
    const view = await until(server.transcript.state, value => {
      const text = JSON.stringify(value);
      return text.includes(record.marker) && text.includes('HOST_FIXTURE_ACK')
        && (!update || (text.includes('NATIVE_LAUNCHER_UPDATE') && text.includes('NATIVE_LAUNCHER_NOTIFY_ACK')));
    });
    const text = JSON.stringify(view);
    if (process.env.DELM_LAUNCHER_FORBIDDEN_DRAFT)
      assert(!text.includes(process.env.DELM_LAUNCHER_FORBIDDEN_DRAFT), 'Unsent editor draft was submitted');
    for (const [other, otherRecord] of Object.entries(state.actors))
      if (other !== actor) assert(!text.includes(otherRecord.marker), 'Other actor bootstrap entered this session');
    results.push({actor, exactSession: record.session, ownBootstrapObserved: true, noOtherActorBootstrap: true,
      approvedUpdateObserved: update});
    await server.management.detach(context);
  }
  console.log(JSON.stringify({actualNativeHistory: true, results}));
} finally { await runtime.dispose(); }
