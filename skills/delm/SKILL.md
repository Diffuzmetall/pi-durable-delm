---
name: delm
version: 1.0.0
description: "Prepare approved prompts and plans for a shared-checkout DeLM team in Pi Durable, choose 2/4/8 useful participants, inspect an existing run, and reconcile exact-session delivery. USE WHEN prepare DeLM OR launch DeLM OR resume DeLM OR запусти DeLM OR подготовь команду DeLM. NOT FOR ordinary coding, another tracker, extra workers without authorization, or claiming an unsupported Native host can launch a team."
compatibility: "Python 3.10+ on POSIX for the board; Native SDK 1.4.0 plus a verified host admission/control integration for automatic workers. Tern is optional UI, not a core requirement."
---

# DeLM

One shared project, one board, separate conversations and one verified result. This Type 8 operations runbook supplies verified tools and failure boundaries, not a permanent model supervisor.

## Workflow Routing

| Intent | Workflow |
|---|---|
| Prepare approved inputs, plan and a justified 2/4/8 count without launching | [Prepare](Workflows/Prepare.md) |
| Check launch prerequisites and actual delivery capability | [Launch](Workflows/Launch.md) |
| Inspect exact saved sessions and an authorized continuation | [Resume](Workflows/Resume.md) |
| Reconcile uncertain input, unread receipts or producer state | [Recover](Workflows/Recover.md) |

## Gotchas

- **Stock Native automatic launch is BLOCKED**, not implemented by a private RPC fallback. Read the installed package's `docs/native-compatibility.md`; `Tools/Run.py capabilities` reports the gate before any models run.
- `prepare` freezes original approved prompt/plan/references and generates instructions. It starts no server/models and proves no actual instruction reading or input delivery.
- `Tools/NativeInput.mjs` is a component for an existing SDK host with its real protected admission and exact session binding. It does not create a host or certify production policy. Test faux callbacks are not production guards.
- Use exact recorded Native sessions, never shared-cwd `--continue`. Missing or uncertain identities/accepted input require reconciliation, not another team. Preserve unsent drafts without submitting them.
- A compact wake is a reference, not a read. Replay its original snapshot request, inspect its view, then explicitly ACK that receipt; newer snapshots and accepted notifications cannot substitute.
- `wait` watches exact named outputs; v4 `work` hints at claimable work only for a free actor. Hints do not reserve tasks. Finish when the approved plan is complete.
- Path/resource leases are advisory; expiry does not stop writers or establish producer death. Release leases before task completion/handoff.

## Tools and configuration

Resolve tool paths from this skill directory. `Tools/Run.py` locates the package from its installed path, not a source checkout or personal configuration. Optional `--config FILE` (or `DELM_CONFIG`) accepts only `runs_root` and `global_agents`; CLI `--global-agents` overrides that instruction path. No credentials belong in config or the skill. See [Run help](Tools/Run.help.md).

The exported directory and Pi command are both `delm`, following Pi's portable lowercase skill contract. No LifeOS runtime, private skill, notification service or global setup is required.

## Constraints

Preparation does not authorize real workers. Use the user's approved outcome/count and existing authentication; do not add models, spending, installs, publication or global changes by implication. Read global/project/ancestor rules fully and preserve the original request's constraints. DeLM `context` and `delm_wait` are the team's coordination channel, not Mail/Beads/another scheduler. See [WorkerAddendum](WorkerAddendum.md) and [TaskPlanning](TaskPlanning.md).

## Workflow notification

Announce the selected workflow in the user's language. Voice is optional only if the active runtime already exposes it; never require or start a notification service.

## Examples

- “Подготовь DeLM по готовому плану” → read it, select useful independent streams, freeze the exact approved inputs; report prepared versus launched separately.
- “Запусти четырёх участников” → check real host capabilities first; on the current public-host gate report BLOCKED rather than starting unprotected workers.
- “Продолжи существующий run” → inspect its saved identities and pending delivery, preserving drafts; never repeat init or an uncertain prompt.
