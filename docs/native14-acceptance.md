# Current Native Pi Durable 1.4 — installed candidate acceptance

## Verdict

**Local installed checks: PASS.** Independent milestone review is recorded separately in `evidence/native14/acceptance/final-review-index.json`; until that record contains accepted peer verdicts, these local checks are not whole-task acceptance. Candidate: `dist/pi-durable-delm-0.1.0-native14-candidate-v2.tgz`, SHA-256 `830e43da3e6119fad22507d29db7da0de94fa80817442b26ce4298ca323e7480`.

The final clean three-command pipeline exited zero. It used the actual installed executable, `durable/main.ts`, global registry loader, selected trusted Hindsight admission controller, and Durable/AI/Chord SDK **1.4.0**. It did not clone or patch Native, construct another Harness, inspect Native SQL, change personal skills/global settings/auth, or run a live model. The public 1.0.2 HOST05 proof is historical and is not used as current-host acceptance.

## Exact candidate and bounds

- The archive and all **449 extracted and installed file hashes** matched `dist/N14-candidate-v2-manifest.json`. All **37 runtime hashes** still match the frozen producer files; their exact values are in `evidence/native14/acceptance/correlation-result.json`.
- The execution-only plan with operator paths/pane IDs is absent from the package. Its source remains unchanged. MIT/upstream/Native notices remain in the archive; the producer manifest records the package privacy/provenance checks.
- The actual installed launcher/entrypoint/controller and other 12 file hashes match the independently accepted current-1.4 baseline. Each model-process log records resolved SDK entry/module hashes and version 1.4.0.
- The clean final run made **17 deterministic faux model requests**, zero live/paid calls, and zero external INET connections. Eleven INET connects were to the single exact private fixture board loopback port. No Tern/tmux/herdr executable ran; Tern was absent from the scoped PATH.
- An earlier attempt made 17 faux requests and exposed QA-probe errors. Its logs and successful continuations are retained under `evidence/native14/acceptance/attempt1/`. Total in this acceptance work: **34 faux, zero live**. The final result is a fresh, wholly green pipeline after those test files changed, not a claim that an interrupted old command passed.

## Criterion evidence

| Criterion | Result | Fresh evidence |
|---|---|---|
| Installed package enters the existing current Native, without another host | PASS | `final-pipeline.log`, per-process connect/exec/model logs, `correlation-result.json` |
| Two ordinary-terminal actors and exact approved bootstrap replay | PASS | `installed-flow-result.json`; real `prepare`, `open`, `start`, repeated `start` |
| Packaged skill discovered in the actual Native model prompt | PASS | Actual registry `GenerationTask.beforeRequest` observations for every generation; exact project/installed skill location, not an ordinary-Pi parser mock |
| Native Bash fresh claim, shared result and DONE | PASS | Actual advertised `bash` tool/results and final assistant result, not board mutations substituted for the producer |
| Real event wake, snapshot/read/explicit ACK | PASS | Consumer invokes actual Native `bash` for pending/snapshot/ACK, then actual `delm_wait status`; sent/acked and no pending wake receipt |
| Exact pending wait reopen with the same session/instance, no dummy input | PASS | Quit/reopen through product `open`; full stored identity equality, same wait ID and zero requests before output DONE |
| Tool cancellation followed by actual dependency DONE | PASS | Actual advertised `delm_wait cancel`, then DONE; wait stays cancelled and consumer model count does not increase |
| Denial and stop/resume boundary | PASS | Type/changed-payload/instance fences; actual trusted admission completes, a test scheduling barrier delays its return, real stop occurs, and the second active-state check denies late submit. Resume does not generate a dummy input; the same approved ID retries successfully |
| Draft/message preservation | PASS | Both synthetic unsent drafts remain visible through asynchronous traffic. Prompt witness rejects any draft in actual non-system model history. Exact post-removal Native reopening retains prior producer/assistant/tool output |
| Same shipped interactive BOARD | PASS | Genuine curses PTY: detail, End scroll across 120 note lines, escape, notes, no-match search, clear, small-terminal resize warning, quit. `interactive-board-terminal.txt` contains actual paints, not `--once` |
| Observer is read-only and does not own backend lifecycle | PASS | Both Python board-file hashes and the deliberately unread receipt remain unchanged. Backend and both Native owners are alive after observer quit; only subsequent explicit product stop/fixture cleanup ends them |
| Repeat install, update, rollback, removal | PASS | `lifecycle-result.json`: repeat unchanged, metadata-only successor with the same 37 runtime hashes, exact rollback, managed removal only |
| Original Native still works after package removal | PASS | Same session/conversation reopens with no DeLM extension/skill, prior actual messages remain, one new faux reply succeeds, original Native/SDK file hashes unchanged |
| User settings/auth and unrelated data | PASS, scoped | No actual user auth/settings or personal skills were changed. Synthetic supplied settings/rules and external fixture board/project files stay byte-identical through installer operations and post-removal Native use |
| One GitHub URL onboarding | PASS, offline scope | Packaged README → prompt/setup map → current contract/operations/skill/help paths exist; actual installed CLI help and the documented ordinary-terminal flow run. No second host or terminal-manager requirement |
| Live public GitHub retrieval/publication | NOT_TESTED | No commit/push/publication was authorized. Offline packaged-map verification is not a remote E2E claim |
| Current four-actor live build reload or live-model quality | NOT_TESTED | Disposable sessions use the same installed real application. The running team is not reloaded; faux model behavior does not prove model quality |
| Independent review of this final fixture/UI evidence | Separate gate | See `final-review-index.json` when present; existing peers only, no extra agents or micro-review fan-out |

## Model boundary and test instrumentation

`model.mjs` is the accepted MODEL-only fixture with a small deterministic cancellation-ID extraction from the explicitly approved user text. It replaces only `ModelRuntime.create` and advertises only actual Native tools. `preload.mjs` adds an explicitly identified test registry adapter through the real Native loader; it does not replace the loader or host.

`observer.mjs` observes real request prompts. For the stop race, it calls and awaits the **original trusted admission with the original arguments**, then delays returning at one named test request. It never changes an allow/deny result, policy, signature or stable request ID. That scheduling fault injection makes the real post-admission stopped-state check deterministic; the exact plugin and Native bytes remain unchanged.

All fixtures use fresh restricted HOME/config/rules, memory disabled, MCP off, the existing installed DCG extension/binary explicitly selected, and an ordinary PTY. The only deliberately cleared drafts are the fixture's own recorded synthetic drafts during normal `/quit` cleanup. No real conversation or user draft is touched.

## Reproduction

With the exact archive and external manifest present, from this checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B evidence/native14/acceptance/prepare-area.py \
  --archive dist/pi-durable-delm-0.1.0-native14-candidate-v2.tgz \
  --manifest dist/N14-candidate-v2-manifest.json
PYTHONDONTWRITEBYTECODE=1 python3 -B evidence/native14/acceptance/run-installed.py
PYTHONDONTWRITEBYTECODE=1 python3 -B evidence/native14/acceptance/lifecycle.py
```

`prepare-area.py` creates only a fresh disposable prefix and private locator. The next two commands use that same fixture; do not run concurrent acceptance drivers against the shared locator. They use the already installed current Native and dependencies; there is no package installation, auth setup, network model call, or new agent. Actual private locator/session paths are retained locally, not published in these artifacts.

## Disclosed QA failures

The first runtime probe expected `READONLY` while the unchanged actual board header is `READ ONLY`. Its corrected independent UI continuation passed on the same fixture with zero extra model requests. Two post-removal probe assertions then used unsupported shared-RPC field names (`workspacePath`/`prompt`) and a nonexistent `conversation.id` view field. The corrected probe uses actual `cwd`/`message` and the shared server's ROOT conversation attachment; its continuation passed with one faux request.

Those failures were test errors, not product fixes. The final corrected driver then ran from a fresh exact archive installation through the entire runtime/UI/lifecycle path, all three commands exiting zero. Failed evidence remains separate; product/runtime hashes did not change to make tests green.
