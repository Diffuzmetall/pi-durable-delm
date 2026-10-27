# Recover

Preserve the exact launch ledger, approved inputs, fresh board ownership and Native receipts. No direct Native SQL, lock stealing, broad process kills, healthy-owner restart or draft submission. A partial result or closed terminal does not prove completed work.

| Observation | Required action/boundary |
|---|---|
| Compact wake unread | Replay original snapshot, inspect view, explicitly ACK receipt |
| Accepted response lost | Retry/reconcile same ID/type/SHA in exact owner; never another request/team |
| Changed approval/instance/workspace or missing session | Refuse and retain data; establish exact intended identity |
| FAIL/correction or owner epoch changed | Inspect evidence; reevaluation is not all-DONE readiness |
| Process opening response/identity unrecorded | Reconcile saved attempt; never blind respawn |
| Recorded process still live | Use existing terminal/control endpoint; no second owner |
| Endpoint unavailable after known process exit | Same foreground open command reopens recorded existing session with a fresh private socket |
| Approved files damaged | Do not submit them; exact bound `stop` can still clean up |

`status --run-dir RUN` inspects integrity and board/Native state. `stop` reconciles root and owned waiters through the real owner, not process kills or deleted history; `resume` clears stopped state without input. Both preserve pending receipts and claims. Missing/unbound identity refuses hot control. Ordinary terminal placement is external to the product.

Board recovery uses `scripts/delm_local.py serve RUN` on the same run, never `init`. Before incompatible changes, drain/cancel owned waiters, reconcile accepted deliveries and back up state through supported ownership. Current reload is idle-only; exact process reopen is distinct and may resume already authorized work. Do independent authorized work before waiting on exact blockers. See [Run help](../Tools/Run.help.md).
