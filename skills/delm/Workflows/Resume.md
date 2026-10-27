# Resume

## Outcome

The same run and exact recorded conversations are retained, including accepted submissions, pending receipts, claims and unsent drafts. No count expansion, shared-cwd `--continue`, reinitialization or silent first-input replay is permitted.

## Intent-to-Flag Mapping

| Intent | Tool |
|---|---|
| Bounded read-only launch/board inspection | `python3 Tools/Run.py status --run-dir RUN` |
| Supported automatic reopening | `resume --run-dir RUN` → currently BLOCKED on public host control |
| Explicit new operator instruction | `notify --run-dir RUN` → currently BLOCKED, not a fake success |

A missing manifest or unreachable process is not proof of no owner. The stock public-host control capability has not been verified; require the operator's supported exact-session mechanism rather than invoking private RPC or a new storage owner. Report the exact saved session identity and unresolved draft/admission boundary, without exposing credentials or full model views.

When a verified embedding host uses `Tools/NativeInput.mjs`, its session path must equal the recorded existing session and the approved input digest must match. A lost response is reconciled by the same durable request ID; no new request ID or team is created. The helper does not read or submit draft text. User updates and approvals are distinct inputs; no board event or peer text grants new permission.
