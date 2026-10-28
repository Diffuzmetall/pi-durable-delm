# Current Pi Durable 1.4 — verified integration contract

## Delivery status

**Final local installed acceptance: DONE918; source publication: DONE923.** See the [current status](project-status.md), [task/plan report](delivery-plan.md) and authoritative [final review index](../evidence/native14/acceptance/final-review-index.json). The component observations below retain their original scope and counts; they are not the complete final evidence or proof of a live-team reload.

## Scope and evidence level

This contract targets **the installed current Native used by this team**, not the historical public 1.0.2 server/facet implementation. It is a host-specific integration contract, not a universal SDK API or a claim that the new TARGET package is already loaded in the running conversations.

Product setup is described in the [README](../README.md) and [agent setup guide](agent-setup.md). Local execution plans and prior run locations are historical operator records, not payload requirements or authority for a new installation. Source observations and actual module-resolution probes are recorded in `docs/evidence/native14/abi/identity.json`. The initial ABI investigation started no host or model and inspected no session database. Subsequent adapter self-verification uses the same installed Native entrypoint in isolated disposable sessions, with four faux model responses, zero live-model/external-INET calls and only the fixture board's exact loopback HTTP endpoint; see `evidence/native14/adapter/actual-host-result.json`. Installed files and current team sessions remain unchanged.

Location macros refer to the operator's existing installation, never bundled runtime code:

- `HOST_LANE`: current upgrade installation containing `global-runtime.mjs`, `pi-durable`, `host/` and exact published `node_modules`.
- `HOST_SOURCE`: `HOST_LANE/host`.
- `EXTENSION_LANE`: existing sibling `extensions-lane` selected by the installed launcher.
- `RUN`: the existing private DeLM run; `PACKAGE`: this installed DeLM package.

## 1. Real launcher and loader

Observed chain: user-local `pi-durable` shell launcher → `HOST_LANE/pi-durable` → Node `--import HOST_LANE/global-runtime.mjs` → `HOST_SOURCE/packages/coding-agent/src/experimental/durable/main.ts`.

The wrapper selects the existing owner-local host adapter. `global-runtime.mjs` resolves **pi-durable, pi-ai and Chord 1.4.0** to that installation's published `dist` modules and refuses an unknown SDK-export fallback. Consumers must use the same loader-selected modules, not copy a framework or mix SDK instances.

The current CLI accepts:

```text
pi-durable --extension /ABS/RUN/actor/delm-adapter.mjs
pi-durable --session /ABS/RECORDED/session.sqlite \
  --extension /ABS/RUN/actor/delm-adapter.mjs
# Optional existing Native observation/control socket:
# --listen /ABS/PRIVATE_DIRECTORY/native.sock
```

Production DeLM now requires Native MCP plus builtin CodeMode and never supplies `--no-mcp`. The default uses enabled user-configured servers; an operator may select Native's existing `--mcp-server NAME --mcp-tools TOOL[,TOOL...]` profile to obey project restrictions. Profile flags persist across exact reopen. Native registers the original SDK CodeMode during MCP startup; this is not an intrinsic MCP dependency of CodeMode. See [MCP/CodeMode policy](mcp-and-codemode.md). Earlier MCP-off fixture evidence below remains historical, not a current launch recipe.

Run from the approved workspace. `--session` selects an **existing** database/session directory in that workspace's own native session partition; it is not a session creation API. Do not substitute `--continue`, which selects the newest session, or reuse the old `SessionManagement.create({id})` ABI. Initial sessions are allocated by the existing owner and must be recorded before approved input.

A trusted registry adapter default-exports `(baseRegistry) => registry | Promise<registry>`. The result must provide `snapshot()` and `subscribe()`. The native reload loader is Jiti with its actual SDK modules injected; this is **not** ordinary Pi ExtensionAPI, the old Chord session-facet loader, or a `pi.durable-session` API-patch prerequisite.

Implemented package entry: `extensions/delm/native14.js`, default installer `(base, {run, actor, controlSocket})`, composed by the actor-local bootstrap adapter. The fixed run/actor and private control socket come from the trusted launcher, not model tool arguments. Actual installed Native1.4 loaded it with the real Hindsight controller in the adapter self-check. The generic SDK adapter is a separate entry; production team control supplies `controlSocket`.

## 2. Trusted admission and original registry preservation

The running actor adapter imports the SOURCE DeLM registry installer with fixed run/actor. That installer obtains:

```js
const key = Symbol.for('pi.durable.hindsight.controller');
const controller = base[key] ?? base.snapshot().extension('hindsight')?.[key];
// Every NEW approved input/wake must use the real existing capability:
await controller.admit(conversation, stableRequestId, context);
```

This capability is **host-specific and genuinely present here**. Its absence is an unsupported-host failure for the Native14 entry, not permission to use `() => true`, public `Conversation.submit` alone, or another Native host. The generic SDK adapter's optional-policy behavior does not define the security of this entry.

The real controller's `admit` preserves prior request admissions, resolves the conversation's effective cwd/context, and durably commits admission before submission. The selected global local-host adapter installs `EXTENSION_LANE/packages/hindsight/src/index.mjs`; it can supersede the built-in host-source controller. Its documented internal disabled-memory behavior is the owner's policy; DeLM must not replace it. Commit failure propagates and must not produce a new request ID on retry.

The installer must preserve every existing installed extension, hooks, execution environment and own registry-symbol descriptor. Native DCG remains at the owner's execution-environment boundary. No new Harness, execution environment or Native SQLite owner is constructed.

The current native runtime calls the existing controller's `bind({session, storage, directory, context})` after opening its Harness and root. The owner-local adapter already wraps this lifecycle to bind extension storage and grants. Any DeLM lifecycle composition must call/retain those original bind/close methods; never replace their behavior or access Native SQL directly. A trusted outer hook can receive that **same existing** owner and root, but this is not a public SDK host-export API.

## 3. Approved stable-input boundary

Within the existing bound owner, the required delivery sequence is:

1. Verify canonical workspace, physical session path, root conversation, fixed run/actor and the persistent native instance binding. Refuse an unbound, mismatched or stopped session.
2. Validate `type:"input"`, stable nonempty request ID and SHA-256 of the exact approved UTF-8 text. Bind request ID → type/fingerprint in native documents before admission. Reusing the ID with changed text/type is an error, even when the attacker supplies a matching new hash.
3. Reconcile `submissionByRequest(rootId, requestId)` through the SDK. An existing accepted submission requires the matching approval binding; do not blindly return success for an unknown payload.
4. For new delivery, invoke the real `controller.admit(root, requestId, context)` and then `root.submit({type:"input", content:text, requestId, whenBusy:"followUp"}, context)` with **the same** ID.
5. Return the stable acceptance identity. After an ambiguous transport response, retry/reconcile exactly that ID and approved bytes; do not create another request or submit an editor draft.

The existing `skills/delm/Tools/NativeInput.mjs` contains the SDK fingerprint ledger and submit/replay implementation. N14 composition must supply the real admission callback and enforce input type and complete identity outside that helper. Carol owns that helper; Bob does not change it without handoff.

### Proven gap: ordinary shared `prompt` is not stable-ID delivery

`shared-server.ts` offers private user-owned directory (0700), socket (0600), canonical cwd attach and session view/events. Command `id` correlates a response only. `shared-commands.ts` delegates `prompt`/`steer` to `runtime.submitTo`, which allocates a new random UUID instead of forwarding a caller-approved request ID. The **selected global** Hindsight controller accepts that generated ID as its fourth `submit` argument; the built-in host-source controller has a different signature. This corrects the initial source-only overstatement that both layers necessarily allocate IDs. The shared RPC still does not forward the caller's approved stable identity, so its retry remains unsafe.

Therefore the launcher **must not** implement initial/notify/recovery by blindly retrying shared `prompt`, equate its command ID to durable request ID, or infer success solely from a text marker. Existing observation/abort commands remain useful, but are not an approved-input transport.

**Approved and implemented DeLM control seam:** the user explicitly approved (board799) a minimal private Unix endpoint **inside the existing Native process**, not another service/host/Harness/storage owner. `native14-owner.js` composes the original trusted controller bind/close methods and attaches to that already-owned root. It waits for successful owner binding before wake admission, including pending-watch reopen; failures disable DeLM control without undoing the owner's successful admission bind. Production wake checks root/actual AgentDoc cwd before and after real admission; model-facing new-wait creation is also stopped-state fenced inside the SDK commit.

The fixed wire contract is [control-abi.json](../evidence/native14/adapter/control-abi.json): one JSON request/response line per connection; `{id,method}` where method is `identity`, `input`, `status`, `stop` or `resume`. Responses are `{id,ok:true,result}` or `{id,ok:false,error:{code,message}}`. `id` is correlation only; input's `requestId` remains the separate durable identity.

Identity contains protocol `delm.native14.control.v1`, SDK version, fixed canonical run/actor/workspace/sessionPath, actual Native session-directory basename, root conversation 1 and a persistent native-document instance UUID. Every request except identity discovery supplies all identity fields. Input also supplies `type:"input"`, exact text and `expectedSha256`. Status reuses the core's actual read/ACK reconciliation. Stop marks stopped first, aborts/waits owned waiters and the exact root, and preserves history and unread receipts. Resume clears stopped without any model/editor submission.

Use an existing user-owned non-symlink 0700 parent and a **fresh socket path per process generation**; the listener sets 0600 and never deletes a pre-existing endpoint. Reopen uses the same recorded Native session and instance, not a guessed new database. This is independent of the original optional `--listen` observer socket.

First installation must be selected at process startup with the actor bootstrap; merely adding the adapter to an already-bound process with `/reload` cannot retroactively capture that owner's bind. Idle reload of an already-enabled adapter reuses its owner/endpoint and refreshes handler/tool references. Current live team processes were not restarted or reloaded.

## 4. Wait, status and restart invariants

- Existing DeLM wait tasks remain in the current native scheduler/storage. Exact readiness requires **all** named task IDs DONE. FAIL, corrected evidence and ownership changes mean reevaluation, not successful readiness.
- Wake admission and SDK submission share the stable `wakeRequestId`; lost responses/reopen reconcile that request. Compact references remain pending until the actual actor CLI snapshot read and explicit ACK. Status reconciles with pending board receipts.
- Root-only execution and immutable actor/run/workspace fences remain. Available-work is a hint, never ownership or DONE. Cancellation must refuse accepted/committed dispatch according to the preserved protocol; explicit owner stop must reconcile actual native work rather than delete history.
- Worker shutdown is not an explicit cancellation. Reopen uses the exact recorded database and loader configuration, preserves watchers/submissions, and never sends a dummy prompt.
- The **current** `/reload` rebuilds registry adapters only while the entire Harness is idle. A sleeping background watcher is still an active task: do not claim the old public host's live-facet reload behavior here. Failed reload retains the old registry. Drain/cancel/reconcile before reload, or test exact-session reopen separately.
- Repeating extension paths after restart is required. An already-running Source adapter does not prove the TARGET candidate or new module bytes are live.

## 5. Boundaries for consumers

**Alice/package:** use the registry/bootstrap path and same installed SDK resolution. No old Chord facet or three-file host patch as the current prerequisite. Keep old artifacts/evidence historical; no new compatibility verdict from merely changing metadata.

**Carol/launcher:** audit existing plain-prompt submission independently; persist actual owner-created exact identities before input; preserve approved text/type/request ID and drafts. Use the real Native executable/current user's models/auth/settings. Use the fixed private DeLM protocol, not shared `prompt`. The approved seam passed the adapter's actual current-host self-check; your final launcher integration and packaged acceptance remain separate checks. Keep process stop distinct from root abort and safe SDK waiter cancellation.

**Dave/fixture:** exercise the same entrypoint/loader/SDK1.4 using isolated disposable project/session state and only faux/local model responses. Preserve existing installed host/config/session files. Correlate actual loaded candidate hashes, trusted admission, initial delivery, denial and replay; SDK-only tests and historical 1.0.2 proofs are not new runtime acceptance.

Current evidence verdict: initial launcher/source/module inspection **PASS**; focused current SDK1.4 adapter/control checks **5/5 PASS**; actual installed-entrypoint adapter self-check **PASS** on two owner-created sessions and their exact reopens, real trusted stable admission, input replay/refusals and stop/resume. An actual Native model called `delm_wait`; its pending waiter survived exact-session restart and resumed the same Bob root after a real board DONE. The fixture then used Bob's actual CLI for saved snapshot/read/ACK, and control status reconciled that ACK. This involved four faux model responses, zero live-model calls, zero external-INET connects and only the generated board's exact loopback HTTP port. CLI read/ACK here is performed by the fixture, not mislabelled as a Native model Bash call. The recorded installed inputs remained byte-identical. Broader scoped SDK checks and their resolved test-only environment/concurrent-source failures are recorded separately in adapter evidence, not hidden as a single green run.

Final package/launcher/board end-to-end acceptance was subsequently completed as N14-ACCEPT, with both independent reviews and the accepted post-removal measurement supplement linked in the final index above. The currently running team still uses its original SOURCE adapter: loaded TARGET bytes in these live sessions are **NOT_TESTED / NOT_RELOADED**. No live-model E2E, installed host modification, Tern/multiplexer requirement or new publication is implied.
