---
name: delm
version: 1.0.0
description: "Prepare approved inputs for a shared-checkout DeLM team, choose 2/4/8 useful participants, and manage exact authorized conversations on the user's existing Pi Durable. USE WHEN prepare DeLM OR launch DeLM OR resume DeLM OR запусти DeLM OR подготовь команду DeLM. NOT FOR installing Durable itself, ordinary coding, another tracker, or extra workers without authorization."
compatibility: "Python 3.10+ and POSIX. Current target: existing Pi Durable 1.4 executable, registry loader and matching installed SDK, with the real host admission controller. Private in-process control protocol delm.native14.control.v1; ordinary foreground terminals, no terminal manager required. Current fixture acceptance is separate from source availability. Historical public 1.0.2 facet/API-patch evidence does not establish current compatibility."
---

# DeLM

One shared project, one board, separate exact conversations and one verified result. This operations runbook supplies the DeLM plugin, Python board and launcher—not a bundled Durable, another Harness, model supervisor or Native storage owner.

## Workflow Routing

| Intent | Workflow |
|---|---|
| Preserve approved prompt/plan/references and select 2/4/8 useful participants | [Prepare](Workflows/Prepare.md) |
| Verify and use the existing current Native integration | [Launch](Workflows/Launch.md) |
| Reopen exact saved sessions or deliver an approved new instruction | [Resume](Workflows/Resume.md) |
| Reconcile uncertain delivery, stop or preserve pending evidence | [Recover](Workflows/Recover.md) |

## Gotchas

- The current target is **Native 1.4's registry loader**, not the historical public 1.0.2 Chord server/facet. Read package `docs/native14-contract.md`. A three-file API patch and `pi.durable-session` are not current-host prerequisites. Historical HOST05 PASS is not current-host acceptance.
- Every production actor requires Native MCP and builtin CodeMode. `open` preserves Native's configured MCP default and never adds `--no-mcp`; the registry adapter fails closed when MCP/CodeMode is missing. Native registers the SDK's builtin CodeMode during its MCP initialization; CodeMode itself does not require an MCP server.
- Before opening, inspect the permitted server profile. Default Native startup connects enabled user-configured servers and may initialize Mail identity. Where project rules prohibit a server, use Native's existing explicit `--mcp-server NAME --mcp-tools TOOL[,TOOL...]` profile; the launcher records it for exact reopen. Do not edit global settings or silently fall back to MCP-off.
- `prepare` emits per-actor ordinary-terminal `open` commands. Run each foreground Native command, then `start` connects its private endpoint and sends approved input. No terminal manager, pane RPC, shared `prompt`, text-marker retry or historical `start --socket` route is used. Source availability is not actual runtime acceptance.
- Reuse the existing installed executable and its matching SDK/registry resolution. The current entry requires the genuine `pi.durable.hindsight.controller` admission capability. Absence means unsupported; public submit alone and an allow-all callback are not substitutes.
- `prepare` starts no service/model. Serve the emitted bundled board separately. Starting or reopening authorized conversations may use the **existing** Native executable; that is not permission to install a second Durable or change the user's model/auth/settings.
- The existing owner allocates initial sessions. Record exact Native session ID, physical session path, root and workspace before approved input. Root conversation 1 is not a unique team-session identity. Never replace a missing recorded session or use shared-cwd `--continue`.
- Bind each input request ID to its exact approved bytes/type/SHA before admission. Reconcile response loss with the same ID and bytes. A transport response ID is not a durable admission ID. Resume sends no dummy input; the launcher never reads or submits editor drafts.
- A JavaScript command through Bash is not a CodeMode test: call the actual `codemode` tool and verify a nested Native/MCP tool result.
- Compact wakes are references, not reads: replay the original snapshot, inspect its view, explicitly ACK that receipt. Wait needs **all** exact outputs DONE; a FACT or available-work hint is not DONE or ownership. FAIL/correction means reevaluation, not readiness.
- Current `/reload` requires the whole Harness idle, including background watchers. Use supported draining/reconciliation and exact-session reopen rather than assuming the historical host's facet reload behavior.

## Tools and configuration

Resolve `Tools/Run.py` from this installed skill. `open` runs the existing Native in an ordinary foreground terminal; `start/status/notify/stop/resume` use its private endpoint. Exact process reopen uses the same `open` command, not another live owner. [Run help](Tools/Run.help.md) defines the working commands and uncertainty boundaries.

Optional `--config FILE` / `DELM_CONFIG` accepts only `runs_root` and `global_agents`. No personal config or credentials are bundled or inferred. `--global-agents` selects explicit instruction input. Pi's discovery name/directory remains lowercase `delm`; global LifeOS settings and notification services are not dependencies.

## Constraints

Use only the authorized roster, inputs and existing models/auth/settings. Team coordination uses `context` and `delm_wait`, not Mail/Beads/another scheduler. No implicit spending, extra workers, installs, publication, Native SQL or guard bypass. Preserve unrelated work and read permitted rules fully. See [WorkerAddendum](WorkerAddendum.md) and [TaskPlanning](TaskPlanning.md).

## Examples

- “Подготовь по готовому плану” → preserve the original request and plan; report prepared, not launched.
- “Подключи команду к моему Durable” → establish the actual installed ABI and approved transport before input; never replace the host with the old public fixture.
- “Продолжи run” → preserve exact recorded sessions, pending receipts and unsent drafts; do not reinitialize or inject a dummy prompt.
