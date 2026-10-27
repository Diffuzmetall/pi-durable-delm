// Test-only fallback for already-installed public npm dependencies, never host/API mocks.
import { registerHooks } from 'node:module';
import { delimiter, dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const roots = (process.env.DELM_HOST_DEPENDENCY_ROOTS ?? '').split(delimiter).filter(Boolean)
  .map(root => pathToFileURL(join(dirname(resolve(root)), '__public_host_dependencies__.mjs')).href);
registerHooks({
  resolve(specifier, context, nextResolve) {
    try { return nextResolve(specifier, context); }
    catch (original) {
      if (original.code !== 'ERR_MODULE_NOT_FOUND' || specifier.startsWith('.') || specifier.startsWith('/') || specifier.startsWith('node:')) throw original;
      for (const parentURL of roots) {
        try { return nextResolve(specifier, { ...context, parentURL }); }
        catch (error) { if (error.code !== 'ERR_MODULE_NOT_FOUND') throw error; }
      }
      throw original;
    }
  },
});
