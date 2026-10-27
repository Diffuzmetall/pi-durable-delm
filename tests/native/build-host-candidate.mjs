// Build using the selected public Native source toolchain; no host activation/install.
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, readdir, copyFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { bundleFacetPackage } from '@earendil-works/chord/bundler';

const source = process.env.DELM_TEST_NATIVE_SOURCE;
if (!source || !process.argv[2]) throw Error('Set DELM_TEST_NATIVE_SOURCE to clean public v1.0.2 source; pass a fresh output directory');
const root = fileURLToPath(new URL('../../', import.meta.url));
const outdir = resolve(process.argv[2]);
await mkdir(outdir, { recursive: true });
if ((await readdir(outdir)).length) throw Error('Refusing to overwrite a nonempty candidate directory');
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const paths = ['packages/coding-agent/src/experimental/services/worker.ts',
  'packages/coding-agent/src/experimental/session-worker.ts', 'packages/coding-agent/src/experimental/plugin.ts'];
const preimages = {};
for (const path of paths) preimages[path] = digest(await readFile(join(source, path)));
const result = await bundleFacetPackage({ packagePath: root, outdir });
await copyFile(join(root, 'extensions/delm/public-host-api.patch'), join(outdir, 'public-host-api.patch'));
const abi = {
  protocol: 1, service: 'delm.control', localCapability: 'pi.durable-session', localCapabilityApi: 1,
  entry: 'session', facet: 'delm.native-session', export: 'default facet array',
  identity: ['sessionId', 'sessionPath', 'workspace', 'conversationId', 'instanceId'],
  methods: {
    identity: { request: [], response: ['protocol', 'build', 'identity', 'binding', 'stopped'] },
    bind: { request: ['identity', 'run', 'actor'], response: ['bound', 'identity', 'run', 'actor'] },
    input: { request: ['identity', 'type=input', 'requestId', 'text', 'expectedSha256'], response: ['accepted', 'replay', 'requestId', 'conversationId'] },
    status: { request: ['identity'], response: ['waits', 'stopped'] },
    resume: { request: ['identity'], response: ['resumed'], submitsInput: false },
    stop: { request: ['identity'], response: ['stopped', 'waits'], deletesHistory: false },
  },
  errors: 'Any RPC exception is not acceptance. Preserve intent and reconcile the same exact session/request; never recreate or silently replace payload.',
};
await writeFile(join(outdir, 'control-abi.json'), JSON.stringify(abi, null, 2) + '\n');
const members = {};
for (const name of (await readdir(outdir)).sort()) members[name] = digest(await readFile(join(outdir, name)));
const runtime = {};
for (const path of ['extensions/delm/index.js', 'extensions/delm/protocol.js', 'extensions/delm/session-facet.js',
  'extensions/delm/control.js', 'skills/delm/Tools/NativeInput.mjs', 'package.json'])
  runtime[path] = digest(await readFile(join(root, path)));
await writeFile(join(outdir, 'candidate.json'), JSON.stringify({
  status: 'API_CANDIDATE_NOT_HOST_ACCEPTANCE',
  upstream: 'https://github.com/earendil-works/pi', commit: 'cd32f7725fdbddbaecdff5b1e68491563394e0ca',
  preimages, members, runtime, manifest: result.manifest,
}, null, 2) + '\n');
console.log(JSON.stringify({ status: 'built', members, runtime, activation: 'NOT_TESTED' }));
