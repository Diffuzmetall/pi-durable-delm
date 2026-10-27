# Recover

## Preserve and diagnose

Read the exact run manifest, current board owners/epochs, saved Native request receipts and the user's approved plan. No direct Native SQL writes, lock stealing, broad process kills or healthy-service restarts. The public-host control gate remains explicit; `stop --run-dir RUN` fails closed rather than abandoning active writers while claiming success.

| Observation | Required boundary/evidence |
|---|---|
| Notification accepted, body unread | Replay the original snapshot request, read the saved view, explicitly ACK that receipt; pending survives reopen |
| Initial submit response lost | Reconcile the original request ID/approved-input digest in the exact conversation; missing proof is uncertain, not permission to resend |
| Relevant FAIL/correction or owner epoch changed | Inspect linked evidence; reevaluation is not successful readiness |
| Producer idle/turn ended/lease expired | No proof of writer death; obtain explicit lifecycle/checkpoint evidence before fenced salvage |
| Backend unreachable | Preserve board and attached bodies; diagnose the existing service owner before operator recovery |
| Existing work appears | On a verified v4+ tool a free actor may use `delm_wait(action=work,reason=...)`, without items; read/ACK the hint then claim atomically |

Named waits retain ALL-DONE for exact IDs; a work hint assigns nothing. Do not add model polling, a substitute agent or another task store. A busy actor finishes or checkpoints/releases ownership first. If the original plan is complete, finish rather than wait for optional scope.

## Rollback and stopping

Before downgrade from work-capable code to an older exact-only build, drain/cancel waiting/failed work watchers through the current supported tool and reconcile accepted deliveries. Older code may treat empty items as vacuously ready. Never erase history to hide this boundary. Board backup includes both context and attached bodies; Native lifecycle/backup belongs to its existing owner.

For manual core service operation, use the owning foreground terminal's normal shutdown, preserve the private run, then verify actual process exit and endpoint unavailability. This is not a Native crew stop. The launcher supplies no unverified stop/abort orchestration; obtain a supported operator path for each exact participant, preserving drafts and incomplete results. Mark stopped/partial/blocked honestly.

## Intent-to-Flag Mapping

| Intent | Tool |
|---|---|
| Read existing manifest and bounded board health | `python3 Tools/Run.py status --run-dir RUN` |
| Check available versus missing capabilities | `python3 Tools/Run.py capabilities` |
| Automatic crew stop/recovery | currently BLOCKED; no hidden fallback |
