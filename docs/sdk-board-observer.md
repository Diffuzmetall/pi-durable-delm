# SDK Host board observation

`CLAIMED` is task ownership, not evidence of an active model. The read-only board
now observes each exact SDK root independently:

- `RUNNING` / `IDLE`: the bound Host root's current `busy` state.
- `WAIT → …`: current named dependencies or available-work mode.
- `WAIT FAILED`: the wait document records a failed delivery/watch.
- `WAIT UNKNOWN`: observation is unavailable; locally known claims remain visible.
- `DISABLED`: the operator binding is disabled; the board does not query that root.

`sent` and `cancelled` wait documents are historical, not active waits. Failed
waits remain visible instead of reverting to a misleading claim-only display.
Multiple named/work waits retain both kinds of dependency information.

## Invocation

```sh
python3 -B scripts/delm_board.py /absolute/prepared/run --observe \
  --host-client /absolute/private/terminal-client.json
```

Use `--once` instead of `--observe` for a single full text snapshot. The SDK/Rex
launcher supplies the same explicit client path automatically and verifies the
observer's actual command. Tokens are never command-line arguments or output.
The credential file must be canonical, regular, owner-owned and private (0600).
It contains `token` and exactly one of `url` or `baseUrl`.

The SDK observer reads `sdk-launch.json` before considering any legacy Native
manifest. Missing credentials, malformed metadata, wrong identities or an
unreachable Host yield UNKNOWN, never a legacy fallback or proof of no wait.
The saved run/workspace/actor/root, current operator bindings and actual Host
session/root must agree before reading a wait document. Only loopback HTTP is
allowed; redirects and environment HTTP proxies are disabled.

Observation uses only these public GET endpoints:

- `/v1/sessions/:sessionId`
- `/v1/sessions/:sessionId/agents/1`
- `/v1/sessions/:sessionId/agents/1/docs/delm.waits`

It never invokes tools/models, sends prompts, changes tasks, consumes receipts,
ACKs deliveries or opens Native session SQLite. The ordinary board projection
continues to use its read-only SQLite snapshot.

A disposable Python reader process polls up to eight actors concurrently. Each
actor has a two-second I/O budget, and the parent kills/reaps the reader after
three seconds even if HTTP headers/body make slow progress. Completed peer
observations are flushed independently and survive another actor's timeout.
Malformed/truncated HTTP and authentication errors are actor-local UNKNOWN;
exceptions containing private request context are not shown.

Rex's `shell: none` terminal can start Python with login-style `argv[0]`
(`-python3`), leaving `sys.executable` empty. On Linux the reader then resolves
`/proc/self/exe` to the running interpreter rather than searching PATH. This
startup path has a real-process/HTTP regression test.

## Verification

`tests/test_sdk_observer.py` exercises a real disposable loopback HTTP server:
wait states, work mode, wrong bindings/identities, malformed data, auth failures,
redirect refusal, private credential files, interrupted HTTP framing and slow
response deadlines. `tests/test_board.py` covers source selection, UI status and
claim preservation. `tests/delm-rex.test.mjs` covers client-path launch/verification
with faux SDK/Rex processes; it does not prove live model behavior.

A live board probe is read-only. It establishes observation, not all possible
wake/claim/receipt behavior. No new live models are needed to verify the observer.

## Local activation (2026-10-31)

The existing locally patched package `aa94a268…` received the board and its SDK
observer module; `local-patch.json` fingerprints both. The original board,
local-patch metadata, operator config and run's Rex manifest were retained in
`~/.local/share/pi-durable-delm/backups/sdk-board.kZwdfH/`. Historical archive
acceptance is not acceptance of these new bytes.

The operator config now points SDK/Rex launches at the separate launcher directory
`~/.local/share/pi-durable-delm/host-sdk/bc82f023…/`, retaining the previous launcher
and its Host integration module. Only the read-only Board terminal is replaced in
the active run `components-sdk-4-20261031T190459Z`; its Rex manifest tracks the new
block and explicit client argument. Actor pane IDs/PIDs and the board-server
PID/start ticks are checked unchanged. Neither Host nor workers are restarted.

For rollback, restore the backed-up board, local-patch metadata and operator
config, then replace **only** the Board terminal with the saved command. Reconcile
its new block ID into `rex-launch.json`; do not blindly restore a manifest that
names a closed block. The added SDK observer module can remain unused. No task,
worker session or Host state is part of this local patch.

Final checks: 71 Python tests, 47 SDK Host/Rex Node tests and 10 packaging tests
passed. The real Rex pane showed Alice `IDLE | NO CLAIM` and Bob, Carol and Dave
`IDLE | WAIT → available work`; all four actor PIDs and the board-server receipt
were unchanged. This proves current observation, not future delivery acceptance.
