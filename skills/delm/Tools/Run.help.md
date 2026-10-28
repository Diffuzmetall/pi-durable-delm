# Run: use the existing Native 1.4 in ordinary terminals

Requires the existing `pi-durable` executable, matching SDK1.4 registry loader and genuine host admission controller. The package never installs Durable, constructs another Harness, writes Native SQL or changes models/auth/settings. Current protocol: `delm.native14.control.v1`; see package `docs/native14-contract.md` and `evidence/native14/adapter/control-abi.json`.

## Prepare without models

```sh
python3 "$PACKAGE/skills/delm/Tools/Run.py" prepare --workspace "$PROJECT" --plan "$PLAN" --prompt-file "$APPROVED_PROMPT" --global-agents "$GLOBAL_AGENTS" --agents 2 --run-dir "$RUN"
```

RUN must be new and outside PROJECT. Prompt/plan/rules/references are frozen byte-for-byte with hashes; no Native process or model starts. Use only the authorized roster. The JSON result emits actual packaged board/observer argv and a `native_open_commands` argv for every actor; no terminal manager is required.

## Ordinary terminal lifecycle

Run the board in one terminal:

```sh
python3 "$PACKAGE/scripts/delm_local.py" serve "$RUN"
```

Run each emitted `open` command in a separate ordinary foreground terminal, for example:

```sh
python3 "$PACKAGE/skills/delm/Tools/Run.py" open --run-dir "$RUN" --actor alice
python3 "$PACKAGE/skills/delm/Tools/Run.py" open --run-dir "$RUN" --actor bob
```

`open` execs the **existing** Native with MCP enabled by its ordinary configuration, a trusted actor-local registry adapter containing fixed run/actor and a fresh private control socket. It never passes `--no-mcp`; the production adapter requires an MCP registry and the SDK's builtin CodeMode. Disabled user-configured servers remain disabled. MCP-on does not mean every configured server is healthy: inspect the actual Native MCP status.

If a project prohibits some configured servers, select the existing Native single-server profile before startup:

```sh
python3 "$PACKAGE/skills/delm/Tools/Run.py" open --run-dir "$RUN" --actor alice \
  --mcp-server context-mode --mcp-tools ctx_search
```

This forwards Native's own flags, changes no global configuration and records the selected profile for that actor's exact reopen. Native enforces its explicit-profile tool permissions. Default startup may initialize a configured Mail identity; do not use that default in a project forbidding Mail connections. Never downgrade silently to MCP-off. CodeMode itself is built into the SDK and can call local tools without MCP; this installed Native registers it during MCP initialization. It requires an interactive terminal. `--native-executable FILE` selects an already installed executable; default is PATH `pi-durable`. No model/thinking/auth/settings flags are injected. Opening a process is not approved input acceptance.

From the setup/control terminal, after the actor endpoints are ready:

```sh
python3 "$PACKAGE/skills/delm/Tools/Run.py" start --run-dir "$RUN"
python3 "$PACKAGE/skills/delm/Tools/Run.py" status --run-dir "$RUN"
python3 "$PACKAGE/skills/delm/Tools/Run.py" notify --run-dir "$RUN" --actor alice --input-file "$APPROVED_UPDATE" --request-id UPDATE_ID
python3 "$PACKAGE/skills/delm/Tools/Run.py" stop --run-dir "$RUN"
python3 "$PACKAGE/skills/delm/Tools/Run.py" resume --run-dir "$RUN"
```

`--actor NAME` selects one already prepared actor. `start` does not spawn workers: it records each endpoint's actual full identity before delivering its frozen bootstrap. Missing/not-ready endpoints refuse; retry the same start after actual readiness, not with another run or input ID.

`stop` reconciles exact root/waiters through their owning Native; it does not kill the terminal/process or remove history. `resume` clears stopped state without any input. After a Native process exits, use that actor's **same open command**: it reopens only the recorded existing session through `--session`. It does not use `--continue` or create a replacement. A still-live recorded process refuses a second open; use its existing terminal. An earlier launch whose identity was never recorded requires explicit reconciliation, not blind respawn.

## Read-only DeLM BOARD

```sh
python3 "$PACKAGE/scripts/delm_board.py" "$RUN" --observe
```

This is the shipped read-only terminal board. It neither reads/ACKs receipts for agents nor restarts services/actors. Open it in any ordinary terminal. Terminal placement is outside DeLM.

## Identity, approved input and uncertainty

Private socket parent must be canonical user-owned 0700; socket must be user-owned 0600. A transport correlation ID is separate from the permanent approved input ID. Full fixed run/actor/workspace/root, physical session path/session ID and persistent instance must match. Root1 alone is not a session identity. Historical API1 manifests refuse rather than migrate silently.

The launch attempt is saved before Native exec. Approved input/type/SHA and pending status are saved before RPC. Native independently verifies/records approval and invokes genuine admission with the same request ID before SDK submit. Lost acceptance responses reconcile that same ID and bytes; changed replay refuses even with a matching new hash. Status and resume send no dummy input. No editor draft is inspected, cleared or submitted.

Current reload is idle-only, including background tasks; exact-session process reopen is distinct. No old Chord socket, public1.0.2 patch, shared `prompt` retry or author source checkout is required or substituted.

## Configuration and evidence

Optional `--config FILE` / `DELM_CONFIG` accepts only `runs_root` and `global_agents`; no private config/auth is inferred. Default runs root: `~/.local/state/pi-durable-delm/runs`. Native input helper is `NativeInput.mjs`; its generic unit admission spies are not real host-policy proof. Current source/unit evidence is under `evidence/native14/launcher/`; actual current-entrypoint/installed package acceptance remains separately verified. Historical HOST05 is not Native14 evidence.
