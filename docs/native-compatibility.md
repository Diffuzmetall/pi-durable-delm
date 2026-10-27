# Native compatibility: public SDK component, production-host gate

## Current verdict

**The portable SDK component is implemented; turnkey stock-Native extension discovery and protected-input integration are BLOCKED / NOT VERIFIED.** Installing JavaScript files or passing a faux test does not resolve this gate. No private host, private controller, credentials, source workspace or second Native database owner is included.

This report concerns the public `@earendil-works/pi-durable` **1.4.0** API inspected and exercised locally. The package marks its API experimental. It does not claim that every past/future Native distribution has the same capabilities.

## Examined public surface

- `@earendil-works/pi-durable/package.json`: version 1.4.0, MIT, Node >=22.19.0; public root, tools, storage/sqlite/node and other documented exports.
- Full published SDK README, especially Extensions, Persist and Resume, Busy Conversations, Hooks and Abort/Subagents.
- Published `dist/harness/types.d.ts`: `ConversationHandle` exposes `id`, `submit`, `abort`, `waitForIdle`. `InputSubmissionDraft` supports `requestId` and `whenBusy`; `submit` implements durable input/busy/deduplication semantics.
- Published root exports: `defineExtension`, `defineTask`, `defineTool`, `createRegistry`, `ROOT_CONVERSATION_ID` are present. The actual export-name probe found no separate `admit`, `protect`, `trusted` or Hindsight host-admission export.
- The examined coding-agent source package manifest (1.0.2) excludes `dist/experimental` and exposes no public Durable registry/protected-input host integration. Its ordinary `ExtensionAPI` is not the Durable SDK registry interface. No stock CLI was newly installed to manufacture a discovery result.

The source installation obtained an extra per-input capability through `HINDSIGHT_CONTROLLER` (`pi.durable.hindsight.controller`), a private Hindsight controller symbol. Source inspection shows that its `admit` binds effective cwd/context state to the original request identity before submit. The portable package does not import that controller or silently replace it with `() => true`. Calling public `ConversationHandle.submit` alone proves durable scheduling, not preservation of an external host's extra protection/context policy.

## Exported component and host-owned capability

Runtime files are `extensions/delm/index.js`, compatibility `index.mjs` and `protocol.js`. They import only Node built-ins and public SDK packages. Both exact `wait` and available `work`, compact references, persisted tasks, pending/read/ack, request replay, admission recheck, cancellation, reopen and lock retry are preserved.

The default SDK adapter has this interface:

```js
import install from './extensions/delm/index.js'; // from this package root; a host may use its installed export

// Existing host registry and its REAL, documented policy implementation.
// This is an integration interface, not a supplied allow-all policy.
const registry = install(existingRegistry, {
  run: privateRunDirectory,
  actor: boundActor,
  admitInput: hostAdmissionCapability,
});
```

A host supplies `admitInput(conversation, requestId, context)`, which performs its actual input admission/context binding and throws on denial. The host owns that implementation and must preserve the same request identity on retry. The adapter requires it explicitly **before reading run configuration**; missing capability raises `DeLM requires an explicit host trusted admission capability ... stock Native host integration is not verified`. There is no default approval, private-symbol lookup or guard bypass.

`install` validates the bound workspace using real paths and checks actor membership. The model cannot choose run, actor, endpoint or admission policy through tool arguments. Tool execution is root-only. The adapter preserves already installed SDK extensions and registers one `delm` tool/task definition even after repeated registry replacement. It creates no Harness, storage owner or running watcher at import/install time. A supplied JavaScript function is not itself proof of a production host's policy; that integration remains gated.

`createDelmWait({run,actor,admitInput})` is the lower-level SDK factory used by tests and embedders. Production integrators must retain the adapter's workspace binding and their host's real policy; the factory is not a stock-Pi `ExtensionAPI` factory.

Required package peers: `@earendil-works/pi-durable`, `@earendil-works/pi-ai`, `@earendil-works/chord`, all 1.4.0 for this tested contract. The reload test additionally uses public `jiti` 2.7.0 as a test dependency. Runtime code has no jiti or private loader dependency.

## Portable tests, not a bundled host

The five scoped `tests/delm-*.test.mjs` retain their relative package layout and use the target's Python CLI/vendor/templates. No test reaches the original source project or a historical session. Node 24.19.0 is the tested execution version; no new dependency was installed.

With dependencies installed normally, Node resolves their standard package exports. For an environment where public dependencies are **already installed elsewhere**, the optional test-only `tests/native/sdk-loader.mjs` reads `DELM_TEST_NODE_MODULES` (platform-delimited node_modules roots) and delegates to Node's ordinary public-export resolver. It neither installs anything nor imports host implementation files. No machine-specific root is embedded in the payload.

```sh
# From the extracted package root. Omit the environment override with normal local dependencies.
# DELM_TEST_NODE_MODULES=/path/to/existing/node_modules:/other/public/test/dependencies/node_modules
PYTHONDONTWRITEBYTECODE=1 node --import ./tests/native/sdk-loader.mjs --test \
  tests/delm-durable.test.mjs tests/delm-reload.test.mjs \
  tests/delm-first-slice.test.mjs tests/delm-native-v2.test.mjs \
  tests/delm-remaining-integration.test.mjs
```

The default adapter's missing-capability refusal and explicit-capability registry replacement are tested separately from faux continuations. Faux callbacks are deliberately test policy stubs, never advertised as production admission. Actual scheduler/storage/HTTP/CLI tests are not a real-model or stock-host installation claim. Fresh target results/log hashes are published by the owning task and incorporated by independent artifact acceptance; old source baseline counts are not copied as target PASS.

## Fresh target verification

A fresh run from this target passed **24/24 scoped Node tests**, exit 0, on Node 24.19.0 and the published SDK 1.4.0. The generated log is `tests/native/evidence/native-tests.log`; it contains no real sessions or user payloads. This is a new target result, not the source baseline relabelled. The source project and its running processes were not changed.

Coverage includes real target Python HTTP/CLI and Native SQLite/scheduler with faux, exact ALL-DONE, work-mode availability/immediacy/competition/direct handoff on 4/8 identities, compact receipt pending until actual explicit replay/read/ack, admission rejection, root scope, cancellation, busy locks, stable request recovery and public jiti reload. The large actual persisted-receipt fixture produced a 461-byte wake for a 578058-byte body with 71 tasks. The default adapter's missing-capability rejection, unknown-actor/workspace refusal and explicit-capability registry replacement all passed; that is **not** a production host admission/discovery success.

SDK dependencies were resolved exclusively through their public package exports using the test-only resolver and existing installations. No private global runtime shim, experimental host source, second live-session owner, package install or real-model request was used. Full built-artifact installation/parity/rollback remains the independent package-acceptance milestone.

## Exact missing public contract / owner decision

To close the stock-Native gate, supply a **documented, supported host integration** that:

1. Discovers the installed Durable registry adapter (not ordinary Pi ExtensionAPI) and gives it the existing registry, exact workspace/actor/run binding and real per-input admission capability.
2. Runs protected admission/context binding before submission, with rejection and replay guarantees tied to the same conversation-scoped request ID.
3. Preserves the current owner/session on reload/reopen, permits no direct Native SQL writes and does not weaken tool or input guards.

The smallest next step is a supported host-provided adapter/capability implementing that contract, or a verified Native release exposing it publicly. An arbitrary callback, private controller path, copied host or new Harness is not a substitute. No owner approval for publication, own-code license or additional installation/model spending is inferred.

Meanwhile the Python product, package payload, documentation and public-SDK/faux verification can be delivered locally. Package metadata must not claim successful stock-Native extension discovery, automatic first-input admission or protected turnkey operation while this gate remains open. Public push/release is separately unapproved.
