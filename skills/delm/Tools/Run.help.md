# Run: connect DeLM to an existing Native owner

The package supplies the plugin, Python board and client—not Durable itself. It never installs/starts/rebuilds a Native host, reads credentials or opens Native SQLite. Models, settings and conversations belong to the existing user host. Tern is optional.

## Prerequisites

The existing compatible Native host must already load the package's session facet through its public Chord loader and expose `delm.control` protocol 1 / the local-only `DurableSession` capability. Tested Native variant: public 1.0.2 pinned in `docs/native-compatibility.md`, with the explicit separate three-file API patch. This is **not** an unmodified-stock or universal-host compatibility claim. Applying a source patch/rebuilding a test host is not represented as easy plugin installation.

Normal control imports external public `@earendil-works/pi-client` (tested 1.0.2), its `/unix` export, and matching Chord libraries. No framework code is bundled. Missing peers or host capability must be resolved at that actual boundary, never by copying a private host or supplying an allow-all policy.

## Commands

Paths resolve from the installed skill, not an author checkout. Replace uppercase placeholders with actual authorized paths; do not send test input to personal conversations.

```sh
python3 Tools/Run.py capabilities
python3 Tools/Run.py prepare --workspace PROJECT --plan PLAN --prompt-file APPROVED_PROMPT --global-agents GLOBAL_AGENTS --agents 2 --run-dir NEW_RUN
python3 Tools/Run.py status --run-dir NEW_RUN
```

`prepare` preserves approved prompt/rules/references once, including prompt CRLF bytes. Bundled init freezes the approved plan before START generation; bootstrap and manifest point at that exact frozen plan. Original source paths are provenance, not a new task authority. RUN stays outside PROJECT; existing RUN is never initialized over. No conversation dump is captured. Missing instructions are errors, not false reading receipts.

Start the emitted bundled board `scripts/delm_local.py serve RUN` in its own foreground terminal. The existing Native server must already be running in the approved workspace with the DeLM facet loaded. Then:

```sh
python3 Tools/Run.py start --run-dir RUN --socket NATIVE_UUID_SOCKET
python3 Tools/Run.py status --run-dir RUN
python3 Tools/Run.py resume --run-dir RUN
python3 Tools/Run.py notify --run-dir RUN --actor alice --input-file APPROVED_UPDATE --request-id UPDATE_ID
python3 Tools/Run.py stop --run-dir RUN
```

`--actor NAME` selects one existing actor; omission addresses the already prepared roster. It never changes count. Native controls never start the board or host. `stop` aborts only exact bound roots and their own waiters, waits for idle and preserves history; it does not declare the user's task complete or stop the board/server. End those services separately through their actual owner's normal lifecycle.

`--host-source SOURCE` is an **optional advanced test/source-backed dependency resolver** for an already existing host. It does not fetch, copy, build, start or install anything. Normal installed matching client peers do not require this flag or a source checkout.

## Exact identities and uncertainty

A per-RUN advisory `flock` serializes launcher changes. Stable UUID5 session IDs are saved before creating anything through official SessionManagement. Actual server ID, session ID/path, workspace, root and persistent instance ID are saved before bind/input. A changed instance, actor collision, retargeted server or missing previously identified session refuses rather than creating a replacement. Native service binding is immutable for run/actor. The client retains its per-call attachment fence and existing host guards.

Original bootstrap and notification requests are saved with approved bytes, SHA-256, type and pending/accepted status before RPC. Native independently persists request-to-fingerprint binding. If a response is lost, retry the same `start` or `notify` ID with unchanged text; actual accepted receipts replay without duplicate admission/work. A new digest does not authorize changing an existing request. Inspect pending state rather than generating another ID/team. `resume` sends no dummy or first-input replay.

`status` verifies captured prompt/plan/rules/references and actor bootstrap bytes, then probes actual board/Native state. Unknown or changed input/path escapes require reconciliation. Partial/unavailable Native sessions are reported individually. `stop` can clean up the exact known sessions even when approved input files were damaged; it submits none of those bytes. No operation reads/writes/submits editor text.

## Configuration and input component

Optional `--config FILE` before the action (or `DELM_CONFIG`) accepts only:

```json
{"runs_root":"<private-runs-directory>","global_agents":"<global-instruction-file>"}
```

No personal config/auth file is inferred. Default runs root is per-user `~/.local/state/pi-durable-delm/runs`.

`NativeInput.mjs` is an existing-owner component: `createNativeInput({host,conversation,session,expectedSession,admitInput?})`. It requires root/exact path binding and stable approved SHA/type/request identity. Matching native receipts reconcile response loss/reopen; changed, unbound or different-type accepted requests refuse. Normal Native admission uses the existing guarded `Conversation.submit`; a supplied **additional real** host policy is optional and its denial remains enforced. Equal arbitrary path strings do not prove identity—the real control facet derives handles/metadata from its local existing owner.

## Evidence boundaries

New launcher evidence is under `tests/launcher/host-evidence/`. Bookkeeping units are not host mocks presented as acceptance. Actual Native tests use an independent real official host with only the declared API patch, localhost deterministic model provider, official server/client/SQLite/scheduler and real OS PTY. They distinguish accepted input, observed own transcript, unchanged replay, true instance preservation and editor safety. No live-model/spend claim is made. Final installed-artifact acceptance remains a separate milestone.
