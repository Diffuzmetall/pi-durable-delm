# HOST-03: portable existing-Native control

Task `a2c89c645d0b4cf89618cb977151d4d1`; target-only skill/launcher work. This report supersedes the earlier in-progress status, not historical logs or publication metadata.

## Product boundary

Only DeLM plugin, Python board/CLI and skill/client are supplied. `NativeControl.mjs` imports external **public client libraries** (`pi-client`, its `/unix` export and Chord); no host internals, Native framework, model/auth settings or Harness are imported/copied/instantiated. Normal `start --socket` connects to an already running compatible owner. Source snapshots remain temporary test prerequisites outside the artifact; optional `--host-source` only selects source-backed test dependency resolution. It does not install/build/start a host and is not a normal installation requirement.

The tested Native variant is public 1.0.2 `cd32f7725fdbddbaecdff5b1e68491563394e0ca` with the explicitly declared three-file local API patch. Stock/released hosts lacking that capability are NOT claimed compatible. Client ABI is the released `delm.control` protocol 1; root package/API patch/bundle ownership remains Alice/Bob. MIT/publication metadata and historical source work are untouched.

## Implemented

- Approved prompt/rules/reference bytes are preserved once; prompt CRLF is retained. Bundled init's frozen plan is reused without rereading the mutable source. START/bootstrap/manifest refer to the same frozen plan.
- Load/status verify approved captures and actual bootstrap hashes, reject symlink/path escapes; source originals are not reread. Stop can clean exact known sessions without submitting damaged input bytes.
- Per-run flock serializes the launch ledger. Stable actor UUID5 session IDs precede RPC; actual server/session/path/workspace/root/instance identity precedes bind/input. No retargeting, actor collision or replacement of a previously identified missing session.
- Original/notify request ID → approved SHA/type/actor/pending bytes is persisted before control. Native independently enforces the same binding. Same-payload receipt loss/replay reconciles; changed text under the same ID refuses. Resume produces no input. Stop aborts only exact bound roots/owned waiters and waits for idle, not board/server shutdown.
- Existing native admission/guards are retained. An additional real host policy is optional, never an author-specific mandatory controller or default allow-all callback.

## Skill workflow

CreateSkill full body, UpdateSkill/ValidateSkill and authoritative PHILOSOPHY/SKILLS doctrine were loaded/applied. Portable lowercase `delm`, four TitleCase routes, generic public content and CLI-first mappings remain. No global skill/voice/execution-log/version writes are authorized or performed. The workflow is recorded in target-local evidence, not global state. Canonical scoped hygiene results and identity-policy coverage remain explicit: zero configured identity patterns is NOT a privacy certificate.

## Evidence

`host-evidence/launcher-public-client.log`: current launcher/preparation/ledger suite, 21 PASS. Bookkeeping units use synthetic RPC receipts and are labelled UNIT—not fake host acceptance. Initial seven fixture errors were a test method/Namespace name collision; only the affected seven tests were corrected/rerun, preserving the failed log. Earlier 12/14 preparation checks and 6 actual SDK/faux input checks are retained as scoped phase evidence.

`host-evidence/real-native/`: the **actual PRODUCT Run.py CLI**, public Native server/client, existing owner/scheduler/SQLite/Chord loader and a localhost deterministic MODEL provider. It uses new HOME/project/session data; only the declared three source patch files differ from pinned public source. Two own bootstraps appear in their correct real histories and not the other actor's. Actual acceptance response loss is injected only after the genuine Native RPC accepts input; pending state reconciles to replay. Duplicate start produces no new input, changed notification is refused, exact identities survive real server restart, resume submits no dummy input, and stop is acknowledged by the real owner.

The same test launches the **actual official Native CLI TUI in an OS PTY**, types a draft without Enter, invokes product `notify` and observes the new unique model answer plus the retained unsent draft on the current decoded screen. Both real histories exclude that draft. Exactly three localhost model requests total, no extra request on duplicate/restart/resume, zero live models/spend. This is not a mocked host, discovery/admission policy or standalone demo Harness.

Initial real probes failed in our private fixture: Unix endpoints include `server-UUID-NONCE.sock`, not merely the visible socket. A long nested test HOME produced EPIPE even with the official presentation client. The fixture now verifies the full backend path below 108 bytes before startup. Separately, Chord subscriptions start on `use()`, so handles must be obtained before `ready()`; the client follows that actual public API ordering. Earlier failed probe logs are retained with location-only redaction, not presented as PASS.

## Remaining acceptance boundary

This is owning-task self-verification. HOST-05 independently checks the final installed artifact/real scenario and reviews the fixture. Nothing here claims stock unpatched host compatibility, automatic host installation, real provider spending, fair work allocation, successful instruction reading merely from accepted input, or completion of the overall user task. Disable/removal must preserve project/RUN/conversations; package-level acceptance remains its owning milestone.
