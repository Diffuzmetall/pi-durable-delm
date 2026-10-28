# Resume

## Outcome

Continue the same RUN and exact recorded sessions with histories, claims, pending receipts and unsent drafts intact. No count expansion, reinitialization, replacement session, shared-cwd `--continue` or dummy input.

## Tool contract

- Inspect: `python3 Tools/Run.py status --run-dir RUN`.
- Clear an explicitly stopped live owner without input: `python3 Tools/Run.py resume --run-dir RUN`, optionally `--actor NAME`.
- After its Native process exits, run the same emitted foreground `open --run-dir RUN --actor NAME` command in an ordinary terminal. Native MCP and builtin CodeMode are mandatory; any recorded explicit MCP profile is reused. Old MCP-off processes do not gain MCP from a source update or `/reload`: review project server restrictions and frozen instructions before a controlled exact-session restart, never silently reconnect forbidden servers. It uses only the recorded existing `--session`. This is process reopen, not the input-free resume RPC.
- Approved update: `python3 Tools/Run.py notify --run-dir RUN --actor NAME --input-file FILE --request-id STABLE_ID`.

A still-live recorded process refuses another open; use its existing terminal/endpoint. An unrecorded attempted launch or missing recorded physical session needs explicit reconciliation, not automatic discovery or replacement. New socket per process generation retains the same persistent Native identity.

Notifications bind original bytes/type/SHA to the stable ID. A changed replay refuses; an ambiguous accepted response reuses unchanged input/ID. Registry adapters and genuine admission remain installed; no model/auth/settings or draft change occurs. Exact reopen can resume previously authorized pending Native work; verify that authority before reopening. Reload requires the entire Harness idle, including background watchers. Board/peer messages grant no new spending, workers or install permissions. See [Run help](../Tools/Run.help.md).
