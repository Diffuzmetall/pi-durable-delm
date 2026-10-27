import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createJiti } from 'jiti';
import * as ai from '@earendil-works/pi-ai';
import * as durable from '@earendil-works/pi-durable';
import * as durableTools from '@earendil-works/pi-durable/tools';
import install, { DELM_BUILD } from '../extensions/delm/index.js';

// The public jiti dependency exercises transitive reload; no private host imports.
const loader = () => createJiti(import.meta.url, { moduleCache: false, fsCache: false, tryNative: false,
  virtualModules: { '@earendil-works/pi-ai': ai, '@earendil-works/pi-durable': durable, '@earendil-works/pi-durable/tools': durableTools } });

test('actual installed loader refreshes JS adapter AND transitive JS implementation', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'delm-reload-'));
  try {
    const leaf = join(dir, 'implementation.js'), adapter = join(dir, 'adapter.js');
    await writeFile(adapter, "export { default } from './implementation.js';\n");
    for (const revision of [1, 2]) {
      await writeFile(leaf, `export default registry => ({ ...registry, revision: ${revision} });\n`);
      const factory = await loader().import(adapter, { default: true });
      assert.equal(factory({}).revision, revision);
    }
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('public SDK adapter refuses unknown actor and mismatched workspace before any admission', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'delm-public-binding-'));
  try {
    const base = durable.createRegistry();
    const admitInput = () => { throw Error('factory must not admit input'); };
    await writeFile(join(dir, 'config.json'), JSON.stringify({ workspace: process.cwd(), actors: { bob: {} } }));
    assert.throws(() => install(base, { run: dir, actor: 'unknown', admitInput }), /Unknown bound DeLM actor/);
    await writeFile(join(dir, 'config.json'), JSON.stringify({ workspace: dir, actors: { bob: {} } }));
    assert.throws(() => install(base, { run: dir, actor: 'bob', admitInput }), /another workspace/);
    assert.equal(base.snapshot().tools().length, 0);
  } finally { await rm(dir, { recursive: true, force: true }); }
});

test('public SDK adapter replaces one extension and requires explicit host admission without invoking it at install', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'delm-factory-'));
  try {
    await writeFile(join(dir, 'config.json'), JSON.stringify({ workspace: process.cwd(), actors: { bob: {} } }));
    const implementation = new URL('../extensions/delm/index.js', import.meta.url).pathname;
    const adapter = join(dir, 'adapter.js');
    await writeFile(adapter, `import install from ${JSON.stringify(implementation)};\nexport default (base, admitInput) => install(base, { ...${JSON.stringify({ run: dir, actor: 'bob' })}, admitInput });\n`);
    const base = durable.createRegistry();
    base.install(durable.defineExtension({ name: 'public-host-policy', sections: [durable.section('policy', () => 'existing host policy')] }));
    const admitInput = () => { throw Error('factory must not admit input'); };
    let registry = base;
    for (let revision = 0; revision < 2; revision++) {
      const factory = await loader().import(adapter, { default: true });
      assert.throws(() => factory(registry), /explicit host trusted admission capability/);
      registry = await factory(registry, admitInput);
      const tools = registry.snapshot().tools().filter(x => x.tool.name === 'delm_wait');
      assert.equal(tools.length, 1);
      assert.equal(tools[0].tool.structuredOutputSchema.properties.build.const, DELM_BUILD);
      assert.equal(registry.snapshot().tasks().filter(x => x.definition.name === 'delm.wait').length, 1);
      assert.equal(registry.snapshot().extension('public-host-policy').sections[0].render(), 'existing host policy');
    }
  } finally { await rm(dir, { recursive: true, force: true }); }
});
