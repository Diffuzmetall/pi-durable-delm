# Prepare

## Context sufficiency

An approved original request and plan, permitted input references, project/global instructions and meaningful parallel streams must be available. Read an existing plan before asking questions. Ask only for missing outcomes, permission or constraints that materially change the result; preparation alone grants no model launch authority.

## Outcome

A private run outside the shared project contains byte-preserved approved prompt, plan, explicit reference files and instruction snapshots; one frozen worker contract, per-actor START and bootstrap input, exact hashes and an operational `launch.json`. The board remains task truth; the launch manifest is not another tracker. No conversation history is exported by default.

Choose the smallest useful supported roster: 2 for complementary work, 4 for four independent streams, 8 only when eight useful streams and actual authorization exist. Do not invent work to fill panes. For a shared path assign one writer; an early contract output can unblock other writers before the producer finishes everything.

## Intent-to-Flag Mapping

| User input | Tool arguments |
|---|---|
| Shared project and approved plan | `prepare --workspace PROJECT --plan PLAN` |
| Exact approved request | `--prompt-file PROMPT_FILE` (not a paraphrased task string) |
| Approved reference file | repeat `--reference FILE` |
| Chosen authorized roster | `--agents 2`, `--agents 4` or `--agents 8` |
| Global instructions | `--global-agents GLOBAL_AGENTS` or explicit config `global_agents` |
| New run location | `--run-dir NEW_PATH`, outside PROJECT |
| Explicit user settings | `--config FILE` before the action |

Run `python3 Tools/Run.py prepare ...` from the installed skill tool path. Missing/nonempty instruction checks are enforced before creation. The first actor creates only missing initial useful tasks while implementing; no exhaustive task DAG gate for the whole team. `status --run-dir RUN` verifies captured approved prompt/plan/rules/references and every actor's actual bootstrap against the saved fingerprints, without rereading mutable original source files. Changed bytes or path escapes require reconciliation before control, not another run. This verifies preservation only: prepared files do not prove input admission, BOOT instruction compliance or completion. Report the input snapshots, roster rationale, run location and actual host capability status; a historical host limitation is not evidence about every future public host version.
