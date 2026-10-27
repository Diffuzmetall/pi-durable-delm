// Optional test-only resolution for already-installed PUBLIC dependencies.
// Normal package installs need no hook. No dependency installation or host import occurs.
import { registerHooks } from 'node:module';
import { delimiter, dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const roots = (process.env.DELM_TEST_NODE_MODULES ?? '').split(delimiter).filter(Boolean)
  .map(root => pathToFileURL(join(dirname(resolve(root)), '__delm_test_dependencies__.mjs')).href);
if (roots.length) registerHooks({
  resolve(specifier, context, nextResolve) {
    if (!specifier.startsWith('@earendil-works/') && specifier !== 'jiti') return nextResolve(specifier, context);
    let missing;
    for (const parentURL of roots) {
      try { return nextResolve(specifier, { ...context, parentURL }); }
      catch (error) {
        if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error;
        missing = error;
      }
    }
    throw missing;
  },
});
