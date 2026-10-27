# Resume

## Outcome

The same RUN and actual recorded Native sessions/instances retain histories, pending receipts, claims and unsent editor drafts. No shared-cwd `--continue`, count expansion, reinitialization, replacement session or dummy input is permitted. The launcher contacts only the saved existing owner; missing identity is uncertainty, not permission to create another conversation.

## Intent-to-Flag Mapping

| Intent | Command |
|---|---|
| Inspect captured input integrity and actual board/Native state | `python3 Tools/Run.py status --run-dir RUN` |
| Re-enable exact bound sessions without input | `python3 Tools/Run.py resume --run-dir RUN` |
| New approved original instruction | `python3 Tools/Run.py notify --run-dir RUN --input-file FILE --request-id STABLE_ID` |
| Select one existing actor | add `--actor NAME` |

A notification's file is approved input, not a summary fabricated by the launcher. Reusing its ID with changed text refuses even if the new text has a valid digest. Reuse the same unchanged input/ID after uncertain delivery; native receipts and the local pending ledger reconcile accepted responses without duplicate work. `start` retry likewise retains the original bootstrap ID.

User updates, answers and permissions are distinct. A board event or peer publication grants no extra spending, workers, installation or publication. No command reads/submits editor drafts. Changing server, actor, session path/workspace or instance requires explicit reconciliation, not silent migration. Compatibility and existing-owner requirements remain those in [Run help](../Tools/Run.help.md).
