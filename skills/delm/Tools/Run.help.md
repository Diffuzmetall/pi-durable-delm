# Run: portable operator preparation and inspection

`python3 Tools/Run.py --help` works without a config, server, Tern or Native. Paths resolve from the installed skill, not a developer checkout.

```sh
python3 Tools/Run.py capabilities
python3 Tools/Run.py prepare --workspace PROJECT --plan PLAN --prompt-file APPROVED_PROMPT --global-agents GLOBAL_AGENTS --agents 2 --run-dir NEW_RUN
python3 Tools/Run.py status --run-dir EXISTING_RUN
```

Replace the uppercase values with authorized existing files and a new private run outside PROJECT. A plan is reused, not replaced by a new interview. Repeat `--reference FILE` only for explicitly permitted inputs. The original prompt, plan, references and instruction files are copied byte-for-byte into private `RUN/inputs`, with hashes; personal conversation history is not captured. Global/project instructions must exist and be nonempty; missing files are errors, not false reading receipts.

An optional `--config FILE` before the action, or `DELM_CONFIG`, accepts only:

```json
{"runs_root":"<private-runs-directory>","global_agents":"<global-instruction-file>"}
```

No config is bundled or inferred from a personal skill. With no explicit runs_root the per-user default is `~/.local/state/pi-durable-delm/runs`. The installed package owns its code/template path. Do not put auth/provider secrets in configuration.

## Available operations

- `prepare`: generates board artifacts/actor bindings, freezes worker addendum and bootstrap input, saves a mode-0600 schema-2 manifest. No service or model is started. Existing run/invalid project instructions are refused before generation.
- `capabilities`: reports installed package, optional Tern presence and the public Native launch-control gate. It does not contact a server or model.
- `status`: loads only this tool's exact existing manifest and probes its bound read-only board projection; does not consume receipts, submit drafts, cancel tasks or start services. A moved/unknown manifest is refused.
- `start/resume/notify/stop`: **BLOCKED before any process/config/socket access**, because the required public production host-control capability has not been verified. These commands do not pretend success or export private RPC. Core `serve` and read-only `--observe` commands are emitted as argv by prepare and can run separately without Tern/Native.

## Input delivery component and exact identity

`NativeInput.mjs` exports `createNativeInput({host,conversation,session,expectedSession,admitInput})`. This is an embedding component for an EXISTING public SDK host, not an executable host or stock-Native auto-launch. Its real admission capability is mandatory; current/recorded session paths must match, conversation must be root, and `deliver({requestId,text,expectedSha256},context)` rejects modified input. It atomically binds the request ID to input type and approved text SHA-256 in the existing host's conversation-scoped `delm.launch.inputs` SDK document before admission/submit. Changed replay is refused even when the caller supplies a correct new digest. An already accepted external/unbound or different-type request is not certified as this input; it requires explicit reconciliation. Matching accepted SDK submissions avoid repeated admission, including after reopening/response loss. The helper never inspects/submits a user's draft. Host policy implementation, recording session identity and lifetime remain the operator's responsibility.

Automatic session creation/reopening/stop and stock Native skill+extension discovery are NOT VERIFIED production capabilities. See installed `docs/native-compatibility.md`. Tests under `tests/launcher` use a real board and public SDK SQLite/faux with disposable inputs; they are not additional real models or a production policy. Preserve this distinction in reports.
