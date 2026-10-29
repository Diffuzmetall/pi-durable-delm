---
task: "Plan and harden DeLM reliability and delivery"
slug: 20261029-delm-reliability-delivery-plan
project: pi-durable-delm
phase: climbing
progress: 1/11
started: 2026-10-29T17:53:43+03:00
updated: 2026-10-29T18:18:31+03:00
principal_stated_goal: "И потом напиши всё это в план через Planning Workflow, через Plan Pack и обязательно Plan Parallel используй, чтобы можно было это внедрить потом максимально параллельно."
principal_stated_goal_source: prompt
principal_stated_goal_signal: 4
principal_stated_goal_locked: 2026-10-29T17:53:43+03:00
context_sufficient: true
interview_invoked: false
---

# DeLM Improvement Initiative — ISA and Parallel Implementation Plan

## Problem

The project has a carefully guarded Native 1.4 integration and a large, evidence-rich delivery surface. The current branch also contains uncommitted worker-contract and board changes that are not part of the previously accepted frozen archive. A targeted synthetic probe found a concrete reliability defect: a valid 1,000-node dependency chain raises `RecursionError` during event projection; graph validation uses the same recursive traversal pattern. Independent-task projection scaled from 14 ms at 1,000 tasks to 139 ms at 10,000, while an 800-node chain took 241 ms, so a broad caching rewrite is not yet justified but dependency-heavy graphs deserve both a safe algorithm and reproducible measurements.

The main improvement questions are therefore: keep current source, accepted archive, and installed/live state unambiguously separate; remove recursion-depth fragility without changing graph semantics; make the exact host capability boundary easier to diagnose; prove whether packaging and test entrypoints are heavier or harder than necessary; and only then add optional operator-facing explanation features where existing evidence indicates real benefit.

## Vision

A maintainer can tell which exact source, package, and installed host were verified; a large dependency graph remains correct and inspectable; unsupported hosts fail with a clear, non-mutating explanation; and development checks are easy to run without accidentally invoking Native, changing user state, or calling a live model. Useful improvements land as small end-to-end increments with one owner per boundary and parallel work that does not create coordination overhead.

## Out of Scope

- Installing, patching, reloading, or changing the user's Native host, global settings, authentication, models, active sessions, or Native-owned SQLite.
- Live/paid model calls, fresh-machine public-host acceptance, a new Durable/Harness/storage owner, a compatibility fallback that weakens trusted admission, deployment, publication, or commits.
- Creating agents, Beads, Mail messages, a durable Goal, or a second task tracker while preparing this plan. The parallel lanes below are a proposed work design, not launched assignments.
- Deleting historical acceptance evidence, frozen worker instructions, the current-host plan, user drafts, or any unrelated uncommitted work.
- Claiming arbitrary Native 1.4 compatibility from an SDK version or from a fixture-only test.
- Adding a generic graph framework, background cache, scheduler, auto-scaler, or a public replay product without measured need and an explicit consumer.

## Principles

- Preserve one owner per fact: DeLM domain/events/receipts remain Python-owned; Native conversations, models, scheduling, guards, and admission remain Native-owned; the board remains an observer.
- Prefer a single clear graph algorithm that hides traversal details and keeps public projection semantics stable over caller-side recursion guards or layered caches.
- Make release and compatibility claims name the exact artifact, host, and evidence scope; historical evidence stays immutable and clearly historical.
- Fail closed: unavailable or unknown capability/state is UNKNOWN, never silently “no wait,” READY, or supported.
- Measure representative graph shapes and package composition before claiming speed or size improvements; keep optimizations behind the owning module.
- Keep test seams local and deterministic; use installed Native only for explicitly scoped acceptance, never to make routine unit tests pass.
- Parallelize only disjoint ownership paths with an agreed interface and a useful independently verifiable handoff.

## Constraints

- Base revision observed: `654284a` on `main`; the worktree is dirty. Modified paths: `extensions/delm/index.js`, `prompts/delm-worker.md`, `scripts/delm_board.py`, `tests/test_board.py`. Untracked paths include `.codegraph/`, `.pi/`, `docs/Pi-Durable-1.4-current-host-plan.md`, `docs/worker-contract.md`, and `tests/delm-worker-contract.test.mjs`. Preserve all of these; the current-host plan and worker contract are not to be rewritten or absorbed into this plan.
- The accepted installed archive is documented as `dist/pi-durable-delm-0.1.0-native14-candidate-v2.tgz`, SHA-256 `830e43da3e6119fad22507d29db7da0de94fa80817442b26ce4298ca323e7480`; the acceptance record says `NOT_RELOADED_NOT_TESTED` for the current live build. Do not extend that acceptance to current dirty sources.
- No existing project `ISA.md` or `PAI_ISA_PATH` was present. This file is the scoped initiative ISA and plan; it does not create a second tracker or replace the historical delivery plan.
- No new dependencies, live model calls, Native/global changes, source-history rewrites, commit, push, or deploy. Tests must use existing dependencies and disposable local fixtures only.
- When future parallel implementation is separately authorized, each writer first confirms the candidate/worktree, owns the paths below, obtains the project's required narrow exclusive reservation where applicable, and never writes through another owner's dirty paths. No simultaneous writers on `scripts/delm_board.py` or `tests/test_board.py` until the present user changes are reconciled.
- The project identity is explicitly the existing Native 1.4 integration, not a generic Durable abstraction. Keep current compatibility prerequisites explicit; never infer stock-host support from package metadata.

## Goal

"И потом напиши всё это в план через Planning Workflow, через Plan Pack и обязательно Plan Parallel используй, чтобы можно было это внедрить потом максимально параллельно." The resulting plan must be grounded in current source and prior decisions, include observable claims and safe verification, map genuinely independent future lanes, and implement only the bounded local reliability fix that can be proven now.

## Not yet specified

- fog: What is the intended distribution target for a “lighter” package—local source archive, future npm publication, or only an installed runtime payload? Resolve by measuring the current pack and naming the consumer before removing any files.
- fog: Which exact installed Native versions/capability revisions should a future `delm doctor` report as supported? Resolve from the actual versioned public contract and existing acceptance evidence; do not guess from SDK versions.
- fog: Is an “explain why blocked” path trace worth a new CLI/UI surface beyond the existing task details and blocker notes? Resolve with a disposable prototype or observed operator need before implementation.

## Test Strategy

|isc|type|check|threshold|tool|anchors_to|
|---|---|---|---|---|---|
|ISC-1|source/evidence|Compare current source commit, accepted archive fingerprint, and live-build status; mark the user worktree separately|All three scopes have distinct identities/status; no acceptance claim silently crosses them|`git rev-parse`, `git status`, `candidate.json`, final review index, `release-readiness.md`|current candidate and acceptance scope|
|ISC-2|preservation|Capture dirty/untracked inputs before and after the scoped change|All pre-existing user-owned paths retain their original bytes and status; no candidate acceptance is inferred from unverified edits|`git status --short`, scoped diff, file hashes before/after|user-worktree and acceptance preservation|
|ISC-3|regression|Project and validate a 1,500-node dependency chain and verify blocker propagation; exercise a cycle and a missing dependency|No `RecursionError`; valid chain passes; cycle/missing dependency retain their existing domain errors|`python3 -B -m unittest discover -s tests -p 'test_observer_v2.py' -v` and focused domain tests|stack-safe task graph|
|ISC-4|behavior|Compare graph readiness, blockers, deps/outputs, and task order for existing canonical fixtures before and after traversal change|Existing public projection outputs remain equivalent; deep chain includes the expected ancestor blocker|`tests/test_domain.py`, `tests/test_observer_v2.py`, `tests/test_scale.py`|graph projection semantics|
|ISC-5|measurement|Record independent-task and dependency-chain projection timings at named sizes on the same machine/runtime before and after the change|Publish input shape, runtime, repetitions, median, and output count; no fixed production SLO until a stable baseline exists|bounded local Python benchmark; no Native/model calls|graph scalability claims|
|ISC-6|documentation|Check that current status names the accepted archive SHA, source HEAD, and live-build evidence separately|Each status claim links to its own evidence; historical candidate reports remain unchanged|local docs/manifest review plus existing packaging/link tests|source-to-acceptance status|
|ISC-7|behavior|Run any proposed doctor against missing, malformed, mismatched, unavailable, and supported disposable fixtures|Correct PASS/UNKNOWN/UNSUPPORTED distinction; no DB writes, Native SQL, model calls, or identity leakage|focused unit/adapter tests with existing public protocol|native capability diagnostic|
|ISC-8|measurement|Inventory `npm pack` archive size and top file groups; compare only after an explicit distribution target is chosen|Reproducible size/count report; historical evidence stays in Git; no removal without pack/install regression proof|existing offline packaging test and temporary pack output|package payload decision|
|ISC-9|developer flow|Exercise documented local unit/faux commands from a clean temporary output area using already-installed compatible dependencies|Commands and prerequisites are explicit; no implicit live-host test or dependency installation|existing Python unittest commands and the documented `node --test` SDK-loader lane|test-entrypoint clarity|
|ISC-10|usability (conditional)|Ask an operator to use a disposable scenario to explain a blocked task from the proposed trace|Keep the feature only if it resolves a question not already answered by current task details/notes|throwaway prototype; no production code or live model|blocked-path explanation|
|ISC-11|anti-claim|Search changed diff and executed commands for forbidden host/data/model/publication actions|Zero changes to Native, global config/auth, active conversations, Native SQLite; zero paid/live calls, installs, or publication|`git status`, scoped diff, command evidence|explicit non-goals|

## Features

### F0 · Current candidate and preservation guard

Why: later implementation and acceptance must be tied to the bytes actually examined, without confusing a prior frozen archive with changed source or losing existing user work.

- [ ] ISC-1: The scoped plan records the observed HEAD, accepted candidate archive fingerprint, live-build status, and dirty/untracked inputs as separate evidence scopes; historical records and unrelated work remain untouched.
- [ ] ISC-2: The plan and implementation preserve all existing user/other-agent dirty paths, frozen evidence and live-work inputs; no accepted candidate is inferred from unverified source changes.
- [ ] ISC-11: Anti: no implementation, test, package, or documentation change modifies the installed Native/global configuration/auth, live sessions, Native SQLite, existing user drafts, paid/live model behavior, or any user/other-agent dirty path outside its explicit ownership.

### F1 · Stack-safe, semantics-preserving task graphs

Why: valid dependency graphs should not fail because their depth happens to match Python's recursion limit, and callers should not pay to reconstruct the same transitive closure independently for every task.

- [x] ISC-3: `project_events` and `validate_graph` use bounded-stack traversal for deep valid graphs, while preserving ordering, blocker propagation, readiness, unknown-dependency errors, and cycle rejection. Immediate fix is limited to the existing graph owner and focused tests.
- [ ] ISC-4: Existing graph projection fixtures preserve readiness, blocker, deps/outputs, and ordering behavior after the traversal change.
- [ ] ISC-5: A repeatable synthetic benchmark records independent and dependency-heavy graph sizes and timings before/after; any future incremental/cache optimization requires measured benefit and equivalence tests before adoption.

### F2 · One truthful source-to-acceptance status

Why: users and maintainers need to know what was accepted, which source bytes changed afterward, and what the current live host did or did not load.

- [ ] ISC-6: The current status surface distinctly reports the accepted archive/fingerprints, current Git source revision, worktree changes, and live-host reload status; immutable historical reports are not rewritten or presented as current HEAD acceptance.

### F3 · Fail-closed host capability diagnosis

Why: an operator should learn the exact missing versioned Native capability before interpreting an integration failure, without weakening the authority boundary.

- [ ] ISC-7: A proposed read-only compatibility diagnostic and matrix report exact evidence for supported/unsupported/unknown states, use only current public protocol/control surfaces, redact identities/paths as appropriate, and never read Native SQLite, submit input, wake/cancel work, create sessions, or call models.

### F4 · Reproducible lightweight development workflow

Why: developers should be able to run the relevant local checks and understand package cost without silently changing dependencies or discarding the evidence that justifies a release claim.

- [ ] ISC-8: A measured package inventory identifies runtime payload versus development tests/examples/evidence; any reduction keeps authoritative evidence in source control and passes offline pack/install/remove plus preservation tests.
- [ ] ISC-9: Safe Python and SDK/faux Node test lanes are explicitly documented or exposed through a single opt-in command with visible prerequisites; installed-host acceptance remains a separate explicit lane and no test installs dependencies.

### F5 · Operator-facing “why blocked” trace (conditional)

Why: if the existing detail view does not answer the operator's question, a compact causal path can reduce time spent reconstructing graph state without introducing a second truth source.

- [ ] ISC-10: Only if the fog is resolved in favor, a disposable read-only prototype shows a blocked task’s exact dependency/output path and linked unresolved blocker; it is retained for production only after an operator check demonstrates value beyond current board details.

## Parallel Work Map

The next implementation cycle is a proposed plan only; no workers are launched and no work is assigned here. Start by recording the agreed source baseline and checksums of the existing dirty inputs. Then use three independent implementation lanes, with a fourth lane doing read-only package inventory. The optional board explanation is held until the existing board edits are reconciled.

|lane|owner|exclusive paths|deliverable and check|dependency|
|---|---|---|---|---|
|A · evidence/status|documentation owner|`README.md`, `docs/project-status.md`, `release-readiness.md`|Truthful source/archive/live status crosswalk; check local docs and package links|Baseline snapshot; preserve historical reports|
|B · graph correctness|domain owner|`scripts/delm_domain.py`, `tests/test_domain.py`, `tests/test_observer_v2.py`, `tests/test_scale.py`|Stack-safe projection/validation plus equivalence and synthetic size probes|Baseline snapshot; no overlap with current dirty board files|
|C · host diagnosis|adapter owner|`bin/delm`, `scripts/delm_local.py`, `tests/test_local.py`, one new compatibility-matrix doc|Read-only PASS/UNKNOWN/UNSUPPORTED diagnosis through current public surfaces; exact host capability evidence|Agree status vocabulary and no-side-effect contract with lane A before editing; no Native installation/config changes|
|D · package/test inventory|read-only analyst, then package owner only if scope is decided|initially no writes; conditional writes limited to `package.json`, `tests/native14-package/test_package.py`|Initial archive composition/size report; later, if distribution target is chosen, an offline packaging correction with preservation tests|Measurement and explicit target decision before writes; do not remove evidence|
|E · blocked-path UX (conditional)|UI/board owner|future only: `scripts/delm_board.py`, `tests/test_board.py`|Disposable value check first; production change only if it answers a demonstrated unanswered operator question|Blocked until current uncommitted board and test changes are reconciled and frozen|

**Integration barrier:** freeze one candidate after lanes A–C finish; D may join only if the package target is decided. Run the complete existing local suite once against that exact candidate, then have a separate read-only reviewer inspect the integrated diff and a verifier run the acceptance checks. Do not convert this into Native/live-model acceptance: that requires a separately authorized, exact-host task. Resolve all shared interfaces before concurrent writes; if the shared checkout/reservation service is unavailable, serialize the affected writes rather than bypassing ownership.

## Decisions

- 2026-10-29 17:53: Existing project evidence and the user's explicit request are sufficient to plan without a blocking interview. Unknown distribution target, support matrix, and value of an explain-path are held as fog, not silently decided.
- 2026-10-29 17:53: `project_events` is the shared canonical projector used by the observer/domain; `validate_graph` is the write-boundary graph validator. Fix the recursion failure at these owning functions rather than patching the curses board or raising the process recursion limit.
- 2026-10-29 17:53: Prefer a reverse adjacency map plus iterative per-blocker reachability for projection, and iterative DFS for validation. This removes Python call-stack dependence and changes the projection work from recomputing every task’s closure to traversing parents per unresolved blocker; preserve behavior with red-before-build tests. Reconsider only if the comparative benchmark shows another simpler implementation is better.
- 2026-10-29 17:53: Synthetic evidence: 1,000 independent tasks projected in median 0.0141 s; 10,000 in 0.1392 s; an 800-node dependency chain took 0.2414 s; 1,000 and 1,500-node chains failed with `RecursionError`. These are local synthetic results, not real-user performance claims or an acceptance budget.
- 2026-10-29 17:53: Current dirty work includes the user's worker-contract and Native 1.4 observer changes. Treat it as a separate candidate; do not use it as justification to rewrite `scripts/delm_board.py`, `tests/test_board.py`, `extensions/delm/index.js`, `prompts/delm-worker.md`, or untracked worker-plan artifacts.
- 2026-10-29 17:53: ParallelPlan outcome is a proposed four-lane design, not live assignment: status/evidence docs; domain graph safety; read-only capability diagnosis; package/test inventory. The optional board trace is blocked until the current dirty board files are reconciled. A future integrator freezes one exact candidate and aggregates independent review outputs.
- 2026-10-29 17:53: No repository-defined project ISA was present; this scoped ISA is the durable definition for the requested improvement initiative. No Beads/Mail/Goal record or agent launch is created.

## Verification

- [x] ISC-3 — `test_observer_v2.py::ObserverV2Test.test_deep_graph_projection_and_validation_are_stack_safe` (red: `RecursionError` before fix; green: 1,500-node chain, blocker propagation, cycle and unknown-dependency checks; focused observer/domain/scale suites passed 20/20 on 2026-10-29).
