# DeLM with the existing Native 1.4

Use the existing installed `pi-durable` and its matching SDK1.4 registry loader. The actual contract is [native14-contract.md](native14-contract.md) and `evidence/native14/adapter/control-abi.json`. No historical public1.0.2 host patch, Chord server, copied runtime, new Harness or Native SQL owner is needed.

## Ordinary-terminal setup

Prepare approved original inputs and an authorized roster:

```sh
python3 "$PACKAGE/skills/delm/Tools/Run.py" prepare --workspace "$PROJECT" --plan "$PLAN" --prompt-file "$APPROVED_PROMPT" --global-agents "$GLOBAL_AGENTS" --agents 2 --run-dir "$RUN"
```

The result emits real packaged board/observer argv and a foreground `native_open_commands` argv for every actor. Preparation starts no model/service and does not grant model launch authority. RUN is new and outside PROJECT; original input bytes, plan and bootstrap hashes are frozen.

Run the emitted board server in one ordinary terminal. Run each actor's `open --run-dir RUN --actor NAME` in a separate ordinary foreground terminal, then from the setup terminal:

```sh
python3 "$PACKAGE/skills/delm/Tools/Run.py" start --run-dir "$RUN"
python3 "$PACKAGE/skills/delm/Tools/Run.py" status --run-dir "$RUN"
python3 "$PACKAGE/scripts/delm_board.py" "$RUN" --observe
```

No terminal manager or terminal-control RPC is required. The observer is the shipped read-only DeLM BOARD; it does not read/ACK for agents, claim tasks or restart anything. Terminal placement is outside the product.

`open` execs the existing Native with fixed trusted actor registry adapter and fresh private control socket. It does not pass model/thinking/auth/settings flags or load installed private launcher config. Optional `--native-executable FILE` selects an already installed executable. The generated adapter imports the package's `extensions/delm/native14.js`; that entry requires the genuine existing admission controller and preserves the original owner lifecycle.

## Input, stop and exact reopen

- `start` connects already opened actor endpoints, saves actual full identity before input, then submits the frozen approved bootstrap. It does not spawn another owner. Retry the same start after endpoint readiness, not another run.
- `notify --run-dir RUN --actor NAME --input-file FILE --request-id STABLE_ID` binds approved bytes/type/SHA to that ID. Changed replay refuses, even with a matching new digest. Acceptance loss reconciles the original ID.
- `stop --run-dir RUN [--actor NAME]` marks/reconciles owned roots and waiters through Native, preserving process/history/receipts. It does not kill the terminal or declare completed work.
- `resume --run-dir RUN [--actor NAME]` clears stopped state without any input. After process exit, the **same foreground open command** uses only the recorded existing `--session`. It never uses `--continue`, discovers a newer session or replaces a missing one. Exact reopen may resume already authorized pending work.
- A still-live recorded process refuses another open. An unrecorded attempted launch needs explicit reconciliation. Native's own process lock is never bypassed. No draft is inspected, cleared or submitted by the launcher.

The attempt/socket/PID/adapter hash precede Native exec. Actual fixed run/actor/workspace/root, canonical physical session/session ID and persistent instance precede approved input. Root1 is not globally unique. The current private protocol uses one JSON request/response line, private canonical parent0700/socket0600 and bounded frames; transport correlation is separate from durable approved input identity. Current reload is globally idle-only, including sleeping watchers; process reopen is distinct.

## Evidence and limits

Focused fresh actual-run evidence: `evidence/native14/launcher/runtime-result.json`. The product's real `Run.py open` executed the installed launcher/main under Dave's independently reviewed MODEL-only fixture. Published SDKs physically resolved to1.4.0. Initial bootstrap and approved notify made two faux model calls; unchanged start/notify replay, an injected lost launcher receipt AFTER genuine Native acceptance with retained pending ledger/reconciled retry, changed update refusal, stop/resume, visible unsent synthetic draft and exact full-identity reopen passed. Reopened bootstrap replay made zero model calls. Both Native strace logs had zero INET connects. No new Harness was constructed by the fixture or production code.

The nine input-component SDK units and seven Python preparation/bookkeeping units remain **unit** evidence, not genuine runtime policy proof. Portable CreateSkill evidence is in the same directory; hygiene reports zero configured violations with `identityScan:unconfigured`, not a privacy certificate.

This is one focused actor plus exact reopen. Full two-actor board/wait/readACK/denial/installed-payload/TUI acceptance is separate milestone QA. The existing live team's loaded bytes/private provider configuration remain unchanged and not tested by this probe; no live-model E2E, host modification, global/auth mutation or publication is authorized/claimed. Historical HOST05 remains historical.
