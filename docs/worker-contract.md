# Frozen worker contract and lifecycle reminders

The authoritative execution guidance is `prompts/delm-worker.md`. `scripts/delm_local.py init` freezes it as a new shared run's `WORKER.md`; preparation may append the existing plan-specific addendum. START references that file rather than duplicating the contract.

`createDelmWait` reads the frozen file at construction and exposes it through the existing `delm` system section. Both the Native 1.4 registry adapter and historical session facet preserve that section. No scheduler, additional transcript owner, per-turn file read or idle timer was added. Source build: `20261029-worker-contract-v1`.

The contract includes early real vertical slices, independently usable contracts and consumers, cohesive modules, soft context affinity, actual skill loading, distributed independent milestone checks on one identified candidate, recovery and work discovery. Four lifecycle checkpoints live in that same contract: recovery, claim/decomposition/handoff, milestone acceptance and before waiting. The wait tool description and bounded wake reference point back to it; they do not reproduce a competing contract or expand authority.

## Regression evidence

`tests/delm-worker-contract.test.mjs` uses the existing public dependency resolver, real Durable 1.4 Harness/SQLite and the in-process faux provider. It inspects the actual provider requests, replaying positional system sections. Startup, tool continuation, subsequent inputs, real manual compaction with a deterministic summary, and exact storage reopen all retain the complete frozen contract. Old context is actually removed. Eight expected requests are counted: seven generation requests and one explicitly requested compaction summary; opening/resuming adds none. A separate historical-run case proves a new template is not substituted for old frozen instructions.

Run with existing compatible dependency roots; no install is required:

```sh
DELM_TEST_NODE_MODULES="$SDK_NODE_MODULES:$JITI_NODE_MODULES" \
  node --import ./tests/native/sdk-loader.mjs --test \
  tests/delm-worker-contract.test.mjs tests/delm-reload.test.mjs \
  tests/delm-native-v2.test.mjs tests/delm-remaining-integration.test.mjs
```

2026-10-29: **19/19 passed**, zero skipped. Existing tests also exercise actual HTTP board events, native/faux waits, receipt replay/ACK, lost response/reopen, competing claims and the 2048-byte wake limit. New regression fixtures verify WORKER/START bytes remain unchanged. The separate `native14-adapter.test.mjs` and `native14-adapter-control.test.mjs` run passed **6/6**, covering the current registry/controller path, preserved owner hooks, names, admission, stop/reopen and wake retry. `git diff --check` passed.

This establishes text delivery on the tested SDK path, not model comprehension, skill use, compliance or an eight-hour soak. No live model probe was run. Existing frozen runs were not modified; installed payloads and live workers were not reloaded. To give an existing team new guidance requires an explicitly authorized input, not silently rewriting its historical WORKER. Merely changing this source does not activate it in installed sessions.
