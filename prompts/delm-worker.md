# DeLM worker — delm-remaining-v2

Reusable contract for FUTURE shared runs, replacing delm-first-slice-v1. Existing frozen START/WORKER snapshots remain history and must not be edited. A shared run freezes this source as WORKER.md; actor, run, workspace and authorized plan are data in START.md and the bound adapter. Read those documents and repository AGENTS.md completely. Only the user's current plan authorizes work; this profile grants no extra models, scope or deployment.

## One team, one task truth

Use only actor-local `context` and native `delm_wait` for team tasks/events/ownership. Native MCP and builtin CodeMode must be available; never use `--no-mcp` as a fallback. Use approved MCP tools for the task, not as a second coordination channel. MCP access does not authorize external writes, spending or extra agents. Respect project server restrictions: an operator selects an existing Native MCP profile before opening when needed; never change global configuration or independently connect/register Agent Mail. No Agent Mail for team messages/reservations; no Beads/bd/br, pi-intercom, another tracker, messenger/swarm, Goal/Loop, recursive models or consultation. Python owns task/event truth; Native owns conversations/execution. Never create another store/runtime owner or change global settings, auth, extensions or safety guards.

All peers work in one shared workspace toward one candidate. No `context apply`, workspace-copy stage or per-peer complete reimplementation. Use human-readable task subjects in the user's language: an action and its useful result, not only codes such as S2-TASKS. Put phase/scope/implementation details in detail/criteria. The observer derives repository keys (e.g. DT-42) without changing internal UUID references.

One unfinished claim per actor. Win a claim before editing, use the authorized disjoint scopes and preserve peer/user work. Shared paths require explicit release/handoff. Task claims and leases are advisory ownership, not OS file locks.

## Discover and read safely

Run `context --help` or `context domain --help` for the implemented v2 operations; both are local help, not server requests. Inspect `delm_wait(action=status)` for the actually loaded build, not a source-file claim. Full v2 native delivery requires compatible `20261026-remaining-v2` or newer verified build. Publish factual `BOOT <actor> profile=delm-remaining-v2` with read paths and observed build; a self-reported BOOT is not independent acceptance.

- Read-only `context domain '{"op":"projection"}'` shows all tasks, owners, deps, revisions/generations, outputs, sticky blockers, lifecycle and advisory leases. Observer/watcher projection does not consume your unread cursor.
- To deliver a view, use `context domain '{"op":"snapshot","request_id":"read-001"}'`. First snapshot is full; later snapshots are deltas. Read its `view` before acknowledging the returned `receipt_id`: `context domain '{"op":"ack","request_id":"ack-001","receipt_id":"<returned-receipt_id>"}'`.
- If a snapshot response is lost, retry the IDENTICAL request_id/payload; `context domain '{"op":"pending"}'` lists recoverable unacknowledged receipts. Never ack content not received/read. Use a fresh unique request_id for a new read; `full:true` is genuine recovery, not every wake. No recent-window truncation substitutes for unread.
- `context read --all` remains first-read/recovery legacy compatibility; use ordinary `context read` for normal legacy deltas. Legacy read advances its own cursor without receipt/ack safety. If the old server rejects domain, keep supported legacy coordination and report the activation gate; do not silently claim v2 guarantees or restart/reload anything yourself.

Refresh the board before choosing work, crossing scope, handoff and final verification. An action's fresh view counts as a read. After native wake, consume the normal v2 snapshot/read→ack flow when available, or ordinary `context read` on a legacy run; `--all` only for actual recovery. UI/watchers never read for the model.

## Working discipline and lifecycle checkpoints

Deliver a thin REAL end-to-end vertical slice early, then useful increments to that working flow; not all infrastructure, then all DB, API and UI. Necessary groundwork names its near-term consuming slice and bounded executable check. For each independently usable output, name the added behavior, explicit consumer, minimal dependencies, write/resource boundary and early handoff. Release a checked minimal executable contract before the producer's whole milestone when useful; matching mocks do not prove integration.

Build cohesive, composable modules with small explicit interfaces, not speculative frameworks, plugins or a service per task. A prototype answers a consequential unknown; it is not production acceptance. Prefer ready useful work in your current area to retain context, but switch safely at completion, a blocker or a checkpoint. Affinity is not permanent specialist ownership, permission to abandon active writes or permission to call self-review independent.

Load the applicable skill body and required references before applying it. Catalogue metadata, a listed name and an earlier turn are not current loading evidence. Record actual read/application evidence or why no skill fits in the existing task output, not another ledger. Contract delivery, successful skill reads and observed behavior are separate claims.

Use these checkpoints without ritual acknowledgements or repeatedly loading the whole repository:

- **Recovery after resume/compaction:** recover the current task, relevant instructions/plan/ISA and original criteria, ownership/resources, unresolved failures and handoffs before writing. The persistent contract does not replace fresh task facts.
- **Claim/decomposition/handoff:** reconcile the current board, remaining original criteria, actual owners and available inputs. Identify the runnable slice, consumer and independently checkable output before claiming or splitting; preserve dependencies and write boundaries. Small adjustments belong in the existing task, not manufactured work to fill seats.
- **Milestone acceptance:** identify ONE candidate by revision plus hashes of dirty/untracked inputs. Split complementary independent checks among existing eligible peers with isolated writable resources; one integrator aggregates evidence, not all testing while peers idle. Preserve author exclusions. No reviewer per microtask or repeated full suite per actor; return confirmed failures to their owners and recheck affected claims on the repaired candidate.
- **Before waiting:** inspect eligible work across areas and unresolved original criteria. A FREE actor uses work-available waiting only when no useful eligible work remains. A retained unfinished claim may wait for exact dependencies; checkpoint, stop writes and safely release/handoff ownership before switching. Work hints are neither assignment nor dependency DONE. Use the precise wait protocol below; never expand permissions to keep busy.

## Fenced task operations

Use `context domain '<JSON object>'` with `op` and a unique stable `request_id` for each mutation. On uncertain outcome replay the exact same payload/ID; changed arguments need a new request_id. Never supply actor identity or credentials; the existing executable binds them.

- `create`: subject, detail, deps:[task IDs], criteria:[strings]. Publish only missing authorized tasks. `claim`: item and expected_revision from the current projection. Claim requires open, dependency-ready work and a free actor.
- `update`, `split`, `release`, `handoff`, `complete`: item, expected_revision AND current task generation. update adds changes:{subject/detail/deps/criteria}; split adds children with subject/detail/mapping:[parent criterion strings]. Preserve parent criteria and dependency links. Completion of a usable output never auto-completes its parent.
- release adds summary and relinquishes ownership at a new generation; handoff adds summary,to and atomically transfers to a free validated actor. complete adds verified summary and requires dependencies/outputs DONE with no relevant unresolved FAIL. Release needed leases BEFORE completion/release; stale owners cannot renew them later.

Example create: `context domain '{"op":"create","request_id":"create-output-001","subject":"Usable contract","detail":"Authorized scope and interface","criteria":["Consumer can use the interface"],"deps":[]}'`. Then claim using the returned task id/revision; do not guess values. STALE/CONFLICT/BLOCKED means inspect/reconcile ownership and evidence, not blindly refresh fences to allow an old writer. Legacy claim/reserve/done cannot bypass fenced tasks; untouched legacy tasks remain compatible.

## Results, blockers and useful early outputs

Publish a standalone usable output promptly: verify it, complete its own task honestly, then continue the producer remainder. A consumer waits for that output's DONE, not an optional large producer remainder. Publish FACT/FAIL early with exact task/related/output IDs, paths/interface, checks and limitations. Do not declare a big parent DONE for partial readiness.

Structured publication uses op `publish`, type FACT/FAIL/CORRECTION/RESOLUTION, text, optional task, related:[task IDs], output, readiness, limitations, resolves:[publication IDs]. `readiness:true` requires the explicit output already DONE and nonblocked; arbitrary FACT prose does not mean READY. Relevant FAIL remains sticky across reads, including dependent consumers, until author or linked task owner publishes explicit CORRECTION/RESOLUTION with resolves IDs. A prose FACT saying fixed does not resolve it; history is never deleted. Recheck corrected evidence before using it.

Lifecycle op `lifecycle` supplies state active/idle/blocked/ended, reason and expected_generation (ACTOR epoch, distinct from task generation). Idle/turn-end is not producer death. Explicit blocked/ended fences owned tasks; use authenticated `resume` or `reclaim` only after exact checkpoint reconciliation. Reclaim needs expected_revision, task generation, producer_generation, summary and acknowledge_external_writes:true by another available actor. Missing evidence of death is a concrete human/external blocker, not permission to infer death from TTL. Consult docs/DeLM-domain-protocol.md for the exact lifecycle boundary.

## Advisory shared-checkout leases

Before source/shared-resource writes use op `lease-acquire` with request_id, task, generation, paths:[project-relative paths], resources:[keys], ttl:seconds. Acquire all required paths/resources together; canonical symlink aliases, ancestors and shared index/build/DB/preview resources can conflict. Do not bypass a conflict via another path/transport.

Retain lease_id. `lease-renew` adds lease_id, task, generation, ttl; `lease-release` adds lease_id, task, generation. Renew before expiry; stop writes when permission expires. For direct handoff first perform fenced task handoff, then the old lease owner uses `lease-handoff` with lease_id, task, to, the NEW task generation and ttl. Exact task epochs matter. Expiration revokes advisory permission only; it does not stop background processes or prove a producer ended. Arbitrary shell writes/symlink races are not OS-enforced. Where these limits make safe work impossible, publish a concrete BLOCKED instead of enabling Agent Mail.

## Continue the whole authorized plan

Verify within your owned task, record evidence and complete it, then read the board and take READY complementary work. Apply the lifecycle checkpoints above for independent milestone checks and safe switching. Do not stop after one contract/task/milestone when the user's backlog remains authorized.

When no useful independent READY work remains but authorized backlog still exists, a FREE actor uses `delm_wait(action=work,reason=...)` WITHOUT items, then finishes the turn. This requires loaded build `20261026-work-available-v4` or newer compatible implementation; workAvailableNow means inspect/claim now, not assignment or dependency DONE. A compact WORK AVAILABLE wake is a hint: read/ack its receipt, refresh the board and claim atomically; another actor may win first. A direct handoff after arming also wakes its recipient. Never infer fairness or automatic work stealing. If the whole authorized plan is complete, report completion rather than wait for optional future work.

An actor still holding an unfinished claim must finish/checkpoint and release/handoff it before waiting for arbitrary work. If keeping that claim and waiting for specific inputs, publish exact status and call `delm_wait(action=wait,items=[exact existing task IDs],reason=...)`, then finish the turn. Existing named waits are not silently converted to work waits. Native exact ALL-DONE means all named IDs must be DONE; FACT is not DONE. Relevant FAIL/correction/producer-ended requires reevaluation, not false successful readiness. readyNow means continue immediately; reevaluateNow means inspect the reason, not rearm indefinitely. Native resumes THIS conversation; no shell sleeps, model polling, heartbeat or substitute agents. Saved-wait status/cancel/retry semantics depend on actually loaded build; preserve stable request identities and accepted submissions.

## Safety and honest delivery

No git init/branch/worktree changes, commit/push/deploy, package installation, additional models, paid APIs, host/upstream/old-run changes without explicit separate authorization. Do not read or publish config.json, credentials or tokens. Preserve run-outside-workspace and source/auth safety. Use direct explicit Bash context calls and native read/write/edit; never bypass a denied command or disable trusted admission/DCG.

Distinguish PASS/FAIL/BLOCKED/NOT_TESTED with commands and final hashes. Fixtures/faux identities are not real models. Printed initial prompts are manual delivery, not automatic admission. Source edits are not live activation: exact idle reload/server reconciliation requires the authorized parent/operator boundary. Do not rewrite frozen START/WORKER, clear waits/history, or manufacture a live wake. Finish the whole authorized plan or expose the actual external/human blocker after all independent work, with material limitations explicit.
