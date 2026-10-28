# Current Native 1.4 — packaging and onboarding evidence

Status: **Final installed Native1.4 acceptance completed, with two independent reviews and the post-removal correction.** See [current status](project-status.md), [plan/task report](delivery-plan.md) and [authoritative final index](../evidence/native14/acceptance/final-review-index.json). Component check counts below are historical scoped results, not new runs. This report does not supersede historical HOST05 evidence or imply the current live team loaded these new bytes.

## Current usable output

- `package.json` describes the existing Native1.4 registry adapter, not an obligatory public-host API patch. Explicit export `./native14` selects `extensions/delm/native14.js`; ordinary Pi extension autodiscovery remains disabled. Generic SDK and historical Chord facet assets remain separately present for existing consumers; that metadata is not evidence that the current host uses the old facet.
- README has a dedicated **«Настройка агентом по ссылке на GitHub»** section, a copyable request, explicit current-host status and links to the separate complete prompt and reading map. Old facet/API1 instructions and HOST05 numbers are explicitly historical, not the current1.4 recipe.
- `prompts/setup-delm.md` is the reusable setup prompt. `docs/agent-setup.md` maps source files, real CLI discovery, package install/connection, activation, verification, preservation and removal. It needs no author paths, account tokens or mandatory template variables. Missing task/model spending approval is not inferred from a GitHub URL.
- The **same shipped interactive TUI** is `scripts/delm_board.py`, not an author-only component or screenshot. SHA256: `9c5bfc5f545be7eb8a63df14d68892a03a780c7e45dd03c4fa4be604a22382be`. `--observe` opens the read-only interface without starting/restarting backend or workers; Only an ordinary interactive terminal is required. Interactive runtime/cursor verification belongs to final QA, not the help check below.

## Fresh verification

Command:

```bash
python3 -B -m unittest discover -s tests/native14-package -v
```

Result: **4 tests PASS** (latest run: 2.082s). These test:

1. Explicit actual registry export, existing entry file, permitted1.4 peer range and absence of ordinary Pi extension autoload.
2. Relative links in README/reading map/prompt resolve to actual repository files; portable setup files contain no author home path and include input/admission/old-vs-current/TUI evidence boundaries. This is deterministic structural validation, not a claim that an LLM executed the prompt successfully.
3. A real `npm pack --ignore-scripts` archive includes the **exact same bytes** for TUI, setup prompt, reading map and Native14 entry. It installs through the real local payload installer; installed TUI help exposes `--observe`; repeat installation is unchanged and removal preserves independent run data. `native_registered:false` is expected: installing a payload does not load a Native extension.

4. User-facing README, reading map and setup prompt are terminal-neutral: no named multiplexer, ordinary terminal instructions, exact session/process-lock and background-lifetime boundaries.

No dependency installation, host alteration, model/API call, existing Native session/SQL/auth/config access or publication was performed by these four packaging/docs checks. The temporary archive is a packaging smoke during concurrent implementation, **not a frozen final accepted artifact**.

## Actual no-multiplexer runtime proof

User specifically requested a runtime check, not a documentation assertion. Command:

```bash
python3 -B tests/native14-package/check_no_tern.py
```

**PASS: actual installed Native1.4 + current DeLM registry/control + real Python board.** [Correlated result and production hashes](evidence/native14/packaging/no-tern-runtime.json).

The child environment has no `tern` executable in PATH and no multiplexer environment. Native is opened directly through its real executable/PTY, not through a terminal manager. `strace` records no attempt to execute `tern`, `tmux` or `herdr`; only bash/context/dirname/node/pi-durable/python3 ran.

A real approved stable input was accepted through the extension-owned private socket; replay of the same request did not duplicate work. The actual Native tool armed an exact-DONE wait. The real actor CLI completed the board task; the same Native conversation received the READY wake and continued. Final successful run: **3 faux model calls, 0 live model calls**, one allowed localhost HTTP connection to the actual board, no unexpected INET connections, clean Native exit. Current personal sessions/configuration were not used or changed. Production file hashes remained unchanged during this probe.

Two preliminary fixture assertions were corrected, not production guards: first the test placed the socket under a non0700 actor directory and was correctly refused; then a blanket zeroINET expectation incorrectly rejected the legitimate localhost board HTTP call after input/replay/wake had succeeded. The final driver creates a dedicated0700 socket directory and permits only that actual board port. Admission and real private-directory checks remain intact; no guard was weakened.

This proves the core Native/DeLM/control/board/wake path does not need a multiplexer. It does **not** replace final testing of Carol's complete launcher, installed interactive observer or whole-team acceptance.

## Frozen source and final gate

Bob ADAPTER DONE834 and Carol LAUNCH DONE839 release their final bytes. README now documents the actual ordinary-terminal `prepare → serve → open(actor) → start → status/notify/stop/resume` interfaces, not the historical `--socket` route. `start` connects already opened actors; process reopen is separate from input-free resume.

`provenance.json` records all **37 current runtime assets**, including the Native14 entry/owner and user setup prompt; `parity.json` separates current Native1.4 component proofs from historical HOST05. Root `evidence/native14/` is included in the payload so referenced current protocol/launcher reports are available from the installed package. Historical accepted manifests remain unchanged. The local execution plan with author run/pane locations is excluded by `docs/.npmignore` while its source remains untouched. The public ABI introduction links product setup instead, with only its documentation hash updated by explicit Bob→Alice handoff; no runtime/protocol/evidence content changed.

Fresh source checks: packaging **10 PASS**; current package/docs **4 PASS**. Core ran48 with47PASS and one stale generated-entry assertion; after explicit Dave→Alice file handoff only `tests/test_first_slice.py:49` was updated from `index.js` to `native14.js`. Its focused3 tests then PASS. Together these cover all48 current core tests; this is not represented as one fresh all-green48 run. Failure d137940... was explicitly resolved and the file returned to Dave. No production runtime bytes changed for the repair.

Final archive/privacy/runtime-hash checks and exact candidate handoff are recorded externally with the archive hash, avoiding self-reference. Final installed interactive TUI, two-actor launcher/skill/guard behavior, payload lifecycle and offline setup map subsequently passed Dave's N14-ACCEPT gate with independent Alice/Carol review. Fresh-machine agent setup remains NOT_TESTED. A static prompt check, help output, existing team pane or old1.0.2 PASS is not that proof.

The user explicitly approved only the minimal private Unix extension control endpoint **inside the existing Native process**, with actual admission/exact identity/request-ID/type/SHA/guards retained. No standalone Native host, extra Harness, SQL owner, global configuration change or implicit publication follows from that approval.
