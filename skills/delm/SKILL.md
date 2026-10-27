---
name: delm
version: 1.0.0
description: "Prepare approved inputs for a shared-checkout DeLM team, choose 2/4/8 useful participants, and start/resume/notify/stop exact bound sessions on an existing compatible Pi Durable host. USE WHEN prepare DeLM OR launch DeLM OR resume DeLM OR запусти DeLM OR подготовь команду DeLM. NOT FOR installing Durable itself, ordinary coding, another tracker, or extra workers without authorization."
compatibility: "Python 3.10+ and POSIX; Node and external matching public pi-client/Chord libraries. Existing Native host must load the DeLM session facet and expose delm.control protocol 1 plus the local DurableSession capability. Tern is optional."
---

# DeLM

One shared project, one board, separate exact conversations and one verified result. This operations runbook supplies a plugin, Python board and launcher—not another Durable installation, model supervisor or Native storage owner.

## Workflow Routing

| Intent | Workflow |
|---|---|
| Preserve approved prompt/plan/references and select 2/4/8 useful participants | [Prepare](Workflows/Prepare.md) |
| Connect a prepared run to the existing compatible Native host | [Launch](Workflows/Launch.md) |
| Resume exact saved sessions or deliver an approved new instruction | [Resume](Workflows/Resume.md) |
| Reconcile uncertain delivery, stop or preserve pending evidence | [Recover](Workflows/Recover.md) |

## Gotchas

- The package never installs, starts or ships Durable itself. Public source snapshots used in tests are not user runtime payload. A host lacking the documented local `DurableSession` capability is unsupported; the separate minimal API patch is not a hidden automatic rebuild or proof of stock compatibility. See package `docs/native-compatibility.md`.
- Normal launcher control needs an explicit existing server Unix socket and matching public client peers. It imports client libraries, not private host modules. The optional source-resolver flag is advanced test dependency resolution, not an installation prerequisite.
- `prepare` starts no service/model. Run the emitted bundled board `serve` command separately before `start`; the existing Native server must already load the DeLM facet in the approved workspace.
- Session UUIDs are reserved before RPC. Actual server/session/path/workspace/instance identity is saved before binding/input. Never replace a missing recorded session, use shared-cwd `--continue`, or create another team after uncertain input.
- An input request ID permanently binds approved bytes and input type. Reuse the same ID with unchanged input after response loss. Changed replay refuses even with a correct new SHA. `resume` sends no dummy input; `stop` touches only bound sessions/wakers, not the board or Native server.
- A compact wake is a reference, not a read: replay its original snapshot request, inspect its view, explicitly ACK that receipt. `wait` requires ALL exact outputs DONE; `work` only hints at claimable work and assigns nothing.
- Neither terminal presence, accepted input nor BOOT proves instruction reading or completion. The launcher never reads/submits editor drafts. Path/resource leases remain advisory, not OS locks.

## Tools and configuration

Resolve `Tools/Run.py` from this installed skill. Optional `--config FILE` / `DELM_CONFIG` accepts only `runs_root` and `global_agents`; no personal config or credentials are bundled. `--global-agents` overrides that explicit instruction path. [Run help](Tools/Run.help.md) defines the exact commands and ownership boundaries.

The Pi discovery name/directory is lowercase `delm`. Global LifeOS configuration, a private skill and notification service are not dependencies. Announce the chosen workflow in the user's language; voice is optional only when already provided by the active runtime.

## Constraints

Use the authorized count, inputs and existing model/auth settings. Do not add workers, spending, installs, publication or global changes by implication. Read permitted global/project/ancestor rules fully; preserve original constraints and unrelated work. Team coordination uses `context` and `delm_wait`, not Mail/Beads/another scheduler. See [WorkerAddendum](WorkerAddendum.md) and [TaskPlanning](TaskPlanning.md).

## Examples

- “Подготовь по готовому плану” → preserve that plan and original request, choose useful independent streams, report prepared rather than launched.
- “Подключи команду к моему Durable” → verify the existing host capability/plugin, start the board, connect the launcher to its exact socket; do not install another host.
- “Продолжи run” → inspect exact saved identities/pending requests, resume without model input, preserve the unsent editor draft.
