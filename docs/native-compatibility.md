# Native compatibility — installed Native 1.4

[Current delivery status](project-status.md) · [Completed plan/tasks](delivery-plan.md) · [Developer guide](developer-guide.md) · [Documentation index](index.md)

## Current supported integration

The current product uses the user's existing **Native Pi Durable 1.4** process, registry loader and matching published Durable/AI/Chord SDK **1.4.0**. The authoritative interface is [native14-contract.md](native14-contract.md); setup and exact reopening are in [native14-operations.md](native14-operations.md).

`extensions/delm/native14.js` and `native14-owner.js` retain the existing selected owner and genuine trusted admission controller. A private Unix control socket lives inside that same process. It binds actor/run/workspace/session/instance and approved type/text/SHA/stable request ID before delivery. Missing required capabilities must fail, not fall back to another host or an allow-all policy.

This path does **not** require the historical public1.0.2 patch, `pi.durable-session` local service, session-facet loader, `pi-client`1.0.2 transport or terminal multiplexer. It does not ship a host, create another Harness or access Native SQL directly. SDK version alone does not establish host compatibility; the actual entrypoint, loader, controller and lifecycle must match the tested contract.

Local installed checks and two independent peer reviews accepted the exact runtime candidate. See [native14-acceptance.md](native14-acceptance.md) together with the authoritative [final review index](../evidence/native14/acceptance/final-review-index.json). The index supersedes the original unsupported post-removal flag: actual SDK delta replay proves no effective current DeLM skill/tool while historical messages remain. The proof uses 19 final-plus-correction faux requests, 36 including the disclosed earlier attempt, zero live/paid requests. It is not proof of a live-team reload, arbitrary stock host, public fresh-machine onboarding or model quality.

---

# Historical public-host implementation — Native 1.0.2

Everything below records the previous public-host and extraction variants. Its references to a selected/current HOST, optional admission policy, public-client requirements, permissions and unresolved gates are historical statements about those variants, **not the current Native1.4 contract**. Keep the old evidence distinct; do not apply its patch or replace the real current controller based on this archive.

## Selected host and truthful status

The HOST assignment targets **normal Native Durable**, not Pocket. The selected public source is `earendil-works/pi` v1.0.2, commit `cd32f7725fdbddbaecdff5b1e68491563394e0ca`, **plus the explicit minimal API proposal** in `extensions/delm/public-host-api.patch`. This is not an already released stock API. No private author installation, replacement host or second storage owner is shipped.

HOST-02 implementation checks pass: actual patched-Native discovery, two worker-owned sessions, identity/local-capability protection, exact/work wake/read-ACK, pending-wait restart, profile reload, cancellation, retained owner policy and actual editor-draft preservation. Normal launcher integration also passed independently. The subsequent HOST-05 installed-artifact checks are recorded separately in [user-host-acceptance.md](user-host-acceptance.md): 39 genuine Native deterministic-model HTTP requests cover the installed runtime, fresh Native claim competition, tool.cancel followed by actual dependency DONE, pending/accepted-generation stop, actual Native skill prompts, normal launcher and physical payload removal with preserved data. The report and external final manifest retain the independent review boundary; these results are not inferred from SDK tests. SDK regression results below are not substitutes for those checks. MIT publication of this repository remains in force: see [publication checks](publication-checks.md); the historical extraction record below does not undo it.

The product is only the DeLM plugin, Python board/CLI and skill, attached to an **existing user-owned compatible Durable host**. Public source snapshots are disposable test fixtures, not shipped host code or an installation prerequisite. Stock v1.0.2 lacks the proposed capability; no released stock version is claimed to provide it. A host without `pi.durable-session` API version 1 is unsupported until its owner explicitly provides a compatible API; the plugin must not provision, replace or silently rebuild that host.

Public coding-agent 1.4.0 is ordinary Pi, not this Native server. Its source removed the experimental server/client stack. Ordinary Pi ExtensionAPI or skill discovery does not install a Durable registry extension. Pocket was examined as a bounded alternative, but **is not the selected product host**.

## Admission correction

The earlier mandatory Hindsight-style `admitInput` premise was too broad. Actual public Native v1.0.2 `createAgentController` uses native `conversation.submit`; no private Hindsight admission controller is inherent to that host. The SDK adapter now accepts `install(existingRegistry, {run, actor})`, retaining the existing registry hooks and execution environment. Hosts with additional real policy may still supply `admitInput`; its rejection remains enforced. There is no approval stub or private-symbol lookup.

`Conversation.submit` is native durable admission, not a bypass. The selected DeLM facet also enforces its own persistent actor/run/session/instance/workspace scope before input or wake. Existing native tool guards still execute. Stock Native's actual missing seam is **access for admitted facets to the existing registry/session owner**, not a universal private policy. Its standard `AgentController` also lacks caller request IDs; the new DeLM control service uses the existing native submission API and preserved durable input-fingerprint binding instead.

## Minimal API proposal and actual loader

`public-host-api.patch` changes three public source files only. It exposes `DurableSession` from the existing experimental plugin API as a Chord **local service**, `pi.durable-session`. `get(context)` returns:

```text
{ apiVersion: 1, registry, harness, conversation,
  binding: { sessionId, workspace, sessionPath } }
```

All references are the real worker-owned objects. Registry creation, models, settings, execution environments, storage locks, scheduler and normal controller remain unchanged. The service uses `local:true`; the public worker RPC entry additionally rejects its service ID. Remote clients must never obtain these capabilities. The patch has been dry-run checked against the exact public source pin; it is for an isolated test/user-selected source variant, never a silent edit of a running author host.

The actual public loader is the existing server's `-e PACKAGE` → package `chord.facets.session` → host-owned Chord bundle builder/manifest → worker facet loader. The session module must **default-export** its facet array; a named `facets` export alone produces a misleading invalid-facet-ID error. Package entry metadata:

```json
{"chord":{"facets":{"session":"extensions/delm/session-facet.js"},"external":["@earendil-works/pi-coding-agent/experimental/plugin"]}}
```

`pi.extensions` must not point to this facet or the SDK registry factory. The host resolves its plugin API alias and uses its own physical Chord/AI/Durable modules. The manifest format is `chord.facet-bundle`, version 2, with a `session` entry and SHA-256 integrity. No private author path is embedded.

## Client ABI, version 1

The lightweight client token is `extensions/delm/control.js`: `DeLMControl`, service ID `delm.control`. Clients use the real supported Native transport and authenticated exact-session attachment. A returned identity is not a bearer token.

The launcher uses public external `@earendil-works/pi-client` and its `/unix` export, plus Chord client APIs. The selected wire/source version is 1.0.2; independent launcher integration passed through these public client APIs with no product host-source flag. Normal connection requires an explicit existing-host socket, not a host-source checkout. An optional source-resolution flag is for advanced/test dependency resolution only; it does not start or ship a Native host. Models, authentication, settings and existing sessions remain with their current owner.

`identity(context)` returns `{protocol:1, build, identity, binding, stopped}`. The inner identity contains `sessionId`, canonical `sessionPath`, canonical `workspace`, `conversationId` and a persistent `instanceId` stored through native documents. A recreated database/reused ID cannot satisfy a previous instance binding.

| Method | Request / behavior |
|---|---|
| `bind` | `{identity, run, actor}`; checks actual native identity, board actor/workspace and immutable existing binding before installing only the `delm` extension |
| `input` | `{identity, type:"input", requestId, text, expectedSha256}`; native durable approved-input/type binding, no changed-payload replay or duplicate accepted input |
| `status` | `{identity}`; reads only this bound native session's wait state |
| `resume` | `{identity}`; clears explicit stopped state; never invents a prompt or submits an editor draft |
| `stop` | `{identity}`; stops owned waiters, waits for their native termination, then aborts/waits for the exact bound conversation; does not erase history |

The public `SessionManagement.create({id})` supports a caller-chosen stable ID. The launcher must persist that ID before creation and reconcile an uncertain response through the exact session directory entry, not create another random session. The original server creates sessions in its process cwd: start from the approved workspace, or reject a mismatch. The launcher owns the serialized per-run actor/session ledger; an existing bound session cannot be reassigned to another actor/run by this service.

Native worker restart must preserve pending watchers. Facet teardown therefore does not cancel durable work; the next activation restores the binding and registry extension. Reload generations prevent a retired facet from uninstalling its replacement. **Explicit stop precedes disabling/uninstalling**; removing code is not proof that already admitted work stopped. A wake reference still requires actual snapshot read and explicit ACK.

The prompt gives the absolute actor-local `context` CLI, shell-quoted, without changing global PATH. No live session SQL is read/written directly, no additional Harness is constructed, and no editor API is invoked. Actual OS PTY checks independently confirmed editor-draft preservation during both a DeLM wake/reload and product launcher notify; neither test sent editor Enter, and the draft stayed absent from both Native histories.

## Fresh SDK checks and compatibility

Build `20261027-native-phases-v3` passes **26/26** scoped Node regressions on both public SDK 1.4.0 and the selected public v1.0.2 source runtime. This includes native admission without author policy, inherited beforeTool guard denial, optional actual policy denial, exact/work/compact/read-ACK, cancellation, locks, accepted-response loss, reopen and loader reload. New evidence belongs under `tests/native/host-evidence/`, separate from extraction logs.

The core uses committed watch/recheck/backoff phases rather than 1.4-only sleeping task states. Its single model-output channel follows the public built-in `ToolTask.definition.version`: v1 `content`, v2 `output`; unknown protocol versions fail clearly. It does not retain a shadow unredacted content channel. An initial public-source `package.json` import probe failed the source resolver's wildcard mapping; that approach was removed, not worked around through private imports.

These are SDK/faux checks. They do not prove actual host discovery, lifecycle, draft preservation or packaged installation. There is no live-model or spending approval and no new commit/push/publication permission.

## Actual Native evidence — completed HOST-02 checks

The existing fixture peer independently exercised the official Native server, loader, worker processes, scheduler, registry, storage ownership and normal controller. Only the model endpoint was a deterministic localhost HTTP fixture; there were **zero live-model calls**. The source variant is the public commit above plus the explicitly identified three-file API patch, **not unmodified stock Native**.

- Discovery/API: two actual workers loaded the real package through the official loader. `delm.control.identity` returned their actual session paths, workspace, root conversation and distinct persistent instance IDs. The server rejected remote access to `pi.durable-session` even when the client deliberately omitted `local:true`; unbound control requests were rejected, and the original Native controller remained usable. Evidence: [delm-plugin-result.json](../tests/host/evidence/native-delm/delm-plugin-result.json).

- Bound board: two actual workers bound Alice/Bob to one real Python board and shared workspace. Model-invoked Native Bash executed each bound actor's actual CLI, replayed stable claims, completed results and wrote the shared artifact. The exact waiter did not wake after only one of two stable-owner dependencies completed during a bounded 400 ms observation. Completion of both resumed the correct Bob root; model-invoked CLI read the exact persisted snapshot and explicitly ACKed it, and the actual `delm_wait` status reconciled to sent/acked. The expanded final case used **24 deterministic HTTP requests, zero live-model calls**. Evidence: [board-e2e/result.json](../tests/host/evidence/native-delm/board-e2e/result.json), generated by `tests/host/smoke_native_board.py` and `probe_native_board.mjs`.

- Restart/reload: the same server UUID, physical session paths, session/instance IDs and pending waiter survived a real server/worker restart without replaying model work. The official presentation-build plus worker-reload pair preserved that waiter; a test-only policy version change proved actual reload. A real OS PTY retained an unsent draft across reload and the subsequent DeLM wake; neither conversation history contained it. The original owner's actual `ToolTask.beforeTool` hook, installed before DeLM, still rejected a model tool call after install/restart/reload.

- Work/cancel/control: an actual available-work wake read/ACKed its receipt but left the new task open/unowned. A model explicitly cancelled another exact wait; a subsequent FACT did not resume it. Same-request input replay accepted without duplication; changed approved payload/type, wrong session/workspace/instance, actor rebinding and stopped-session input were rejected. Resume submitted no invented/editor input. Native server and TUI exited cleanly. These original component checks alone do **not** establish installed-package removal or stop during committed wake dispatch; the later HOST-05 installed results linked above do exercise those edges.

- Normal launcher: the public-client implementation ran with no product host-source flag against an already running isolated Native fixture. Exactly two sessions received only their own bootstrap; accepted-response loss reconciled with the same request ID, duplicate start did not add model work, changed notify and missing saved sessions were refused, and restart/resume preserved exact instances without dummy input. A real editor draft survived product notify and stayed absent from both histories. Evidence: [launcher result.json](../tests/launcher/host-evidence/real-native/result.json); three deterministic HTTP requests, zero live-model calls.

The frozen early API output is `tests/native/host-evidence/api-candidate/`: its `candidate.json` records all six runtime hashes, three patch preimages and bundle-member hashes; `control-abi.json` specifies the six-method interface. `tests/native/build-host-candidate.mjs FRESH_OUTPUT_DIRECTORY` reproduces this using an explicitly selected public test-source resolver. Its patch SHA-256 is `3460016c2130e2286ccd59c522b4318a2c13b0ad034dbb09f4e31776b23098ae`; all six runtime hashes match the independent actual-host evidence. This directory is a test/API candidate, not a bundled host or final package acceptance.

The final HOST-02 candidate is `tests/native/host-evidence/native-final/`; its bundle/ABI/patch member hashes match the early API candidate, while its root metadata hash matches the expanded actual-host run (`16991086d844cfb81270436290b359bd5b9a61d729bb619e081f4f33e23c791b`). All five runtime-source hashes are unchanged. The builder's `activation:NOT_TESTED` describes the build command alone; correlated actual activation/runtime evidence is linked above, not manufactured by the builder.

The original Native fixture was independently reviewed against all 73 frozen hashes by existing peers; its complete report is [clean-native-host-verification.md](clean-native-host-verification.md). Subsequent installed-runtime, update/rollback/disable/remove, actual packaged-skill and stop/claim edge evidence belongs to [HOST-05](user-host-acceptance.md), not this earlier component result. Neither result asserts released stock API availability or live-model permission.

---

# Historical extraction compatibility record

The remaining text records the earlier extraction build and pre-publication decision, **not the current HOST contract**. Its mandatory-policy and license-pending statements are superseded above and by publication-checks.md; its old logs remain historical evidence.

## Historical verdict

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
