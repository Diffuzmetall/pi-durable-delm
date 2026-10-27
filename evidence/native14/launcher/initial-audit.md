# N14-LAUNCH initial audit — not runtime acceptance

Authority: `docs/Pi-Durable-1.4-current-host-plan.md` and N14-LAUNCH claim 779, generation 1. Read-only investigation of the installed launcher and host; no installed files, settings, sessions or drafts changed.

## Observed differences

- The current host entrypoint is `experimental/durable/main.ts`, with registry `--extension`, exact `--session` and optional private `--listen`. It is not the historical `experimental/cli.ts server` entrypoint.
- Resolved installed package metadata reports `@earendil-works/pi-durable`, Chord and pi-ai **1.4.0**. This is source/module evidence, not proof that the new package has executed in this host.
- The installed launcher (`$INSTALLED_SKILL/Tools/Run.py`) already uses the existing Native command and registry adapter. Its shared socket client attaches to the exact workspace, records the exposed session directory, checks exact session before notify, and does not write through the editor. These are useful owning-runtime seams to reuse.
- Shared-server attach verifies workspace realpath, requires a private user-owned socket directory and refuses to unlink an existing socket. Preserve these boundaries.
- The shared protocol `id` correlates a response to a transport call. `shared-commands.ts` passes only conversation, message and steering mode to `host.submitTo`; it does not pass that transport ID as a durable input request ID. Do not equate transport correlation with deduplicated delivery.
- Installed `Native.call` generates a fresh UUID on each command. Initial delivery recovery searches for a bootstrap marker in serialized view data; notify has no durable SHA/type/request ledger. A marker substring in a view is not sufficient proof of exact approved input acceptance, and an uncertain notify must not be blindly retried.
- The TARGET portable launcher currently calls a separate Chord/session management API via `NativeControl.mjs`. Its identity and approved-input fences are useful, but its historical API1 transport must not be presented as the current registry-host path.
- Installed `connect_actor` assigns a fresh socket, calls Tern `pane(...)`, then persists the pane/socket record. A lost pane-creation response can therefore leave an unrecorded attempted launch. Persist a recoverable attempt identity before any future launch side effect; uncertain launch must not silently create another owner.
- Current shared commands default to numeric root conversation **1**, while identity also contains the Native session ID and directory. Root conversation 1 alone does not distinguish separate actor sessions. The historical launcher instead reserves server-managed UUID sessions; its identity model cannot be copied unchanged.
- Current host shared commands also expose model/thinking setters. This launcher must **not** use them; keep the existing models, auth and settings. Abort/stop may use only the exact admitted owning-runtime operation after its ABI is established.

## Implementation boundary

Bob's usable N14-ABI output must be DONE before final control interfaces are chosen. In particular, it must identify a current trusted admission/SDK seam for stable initial/wake delivery and exact identity/reopen. A raw `prompt` retry, a second Harness, a private database writer, a patched historical host or an allow-all admission substitute is not an acceptable fallback.

Reuse existing preparation, locking, immutable approved bytes and SHA/type/request-ID validation where applicable. Implement only the current-host differences. Keep the old HOST05 records historical and distinguish source observations, isolated current-host fixture evidence, and live loaded build status.

## Inspected byte fingerprints

Paths below are labels rather than private installation locations.

| Label | SHA256 |
| --- | --- |
| current main.ts | `b5dcb4446384f88b38804fa0fc050dc8a2f2ecc7de9f8c1efe764a3e229aecf4` |
| current shared-commands.ts | `a8868ca5ce61aa321cb31f238bc5ac51dec62c25803f45262aadc0ded3dc45aa` |
| current shared-server.ts | `ed613f080bde00f201b67fbc4226b0798400fb9d32d7eca4f119026f15bea83f` |
| installed launcher, read-only | `d16d0c684082a1c466454a109d121863b17018b1cad2e351058cbc8ebf3882c1` |
| TARGET historical portable launcher | `52fd087fded71d7166815c65c4f24ab2c2e9337786aa8b036592172a6c0f1ee3` |

No Native execution, live model calls, private configuration reads or Tern input occurred during this audit. No current-host runtime PASS is claimed.
