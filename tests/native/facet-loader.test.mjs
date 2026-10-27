// Actual public Chord builder/loader regression; not session activation or host E2E.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const source = process.env.DELM_TEST_NATIVE_SOURCE;
test('Native package entry default-exports a valid facet for the real public loader',
  { skip: !source && 'Set DELM_TEST_NATIVE_SOURCE to the pinned public Native source' }, async () => {
    const { bundleFacetPackage } = await import('@earendil-works/chord/bundler');
    const { createFacetBundleLoader } = await import('@earendil-works/chord/node');
    const outdir = await mkdtemp(join(tmpdir(), 'delm-facet-loader-'));
    let loaded;
    try {
      const result = await bundleFacetPackage({ packagePath: fileURLToPath(new URL('../../', import.meta.url)), outdir });
      const api = pathToFileURL(join(source, 'packages/coding-agent/src/experimental/plugin.ts')).href;
      loaded = await createFacetBundleLoader({ manifestPath: result.manifestPath, entry: 'session',
        resolveExternal: name => name === '@earendil-works/pi-coding-agent/experimental/plugin' ? api : undefined,
      }).load();
      assert.equal(loaded.facets.length, 1);
      assert.equal(loaded.facets[0].id, 'delm.native-session');
      assert.equal(typeof loaded.facets[0].setup, 'function');
    } finally { await loaded?.dispose(); await rm(outdir, { recursive: true, force: true }); }
  });
