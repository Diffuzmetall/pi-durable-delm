# Launch

## Outcome and boundary

A prepared DeLM run connects to the user's **existing compatible Native owner**. The bundled board is a separate service; exact team sessions are created/bound through official Native management, with original approved input accepted under a durable request ID. Process setup, input acceptance, instruction reading, first useful claim and completion are different claims.

The package does not install/start Durable, copy private host code, create another Harness or read auth/settings. Verify the actual host's public loader and `delm.control` protocol 1 / local DurableSession capability first. The separate minimal API patch is an explicit compatibility prerequisite for the tested Native variant, not a hidden rebuild or proof every installed host supports it. See package `docs/native-compatibility.md`.

## Intent-to-Flag Mapping

| Intent | Command |
|---|---|
| Offline declared capabilities | `python3 Tools/Run.py capabilities` |
| Start the prepared team on an existing host | `python3 Tools/Run.py start --run-dir RUN --socket NATIVE_UUID_SOCKET` |
| Address one existing actor | add `--actor NAME` |
| Start/observe only the board | use the `serve` / `--observe` argv emitted by prepare |

The Native server must already load the DeLM facet in the approved workspace; the prepared board must be reachable. Matching public client peers resolve from the installed environment. No source checkout is normally required; the optional source-resolver flag is advanced test dependency resolution only.

IDs are reserved before RPC. Actual session/instance/workspace identity is saved before bind/input; stop on mismatch, partial activation or uncertain response without creating a new team. Retry unchanged input with its original ID after reconciliation. Do not bypass guards or grant model spending merely because a command exists. Drafts remain in the user's editor; the launcher never submits or clears them. [Run help](../Tools/Run.help.md) owns the full command and uncertainty contract.
