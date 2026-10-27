# Independent N14 shipped BOARD / terminal-neutral review

Reviewer: existing Carol; claim 879, generation 1, task `aef4046f38b846a5a75e8ea35c34a036`.

## Verdict

**ACCEPTED for the supplied UI/read-only/terminal-neutral onboarding criteria, with the post-removal evidence correction independently accepted.** This is not whole N14 acceptance or permission to publish before the parent gate closes. FAIL `4876b0eea5f84a0fb474b29e427101ab` was a real measurement/enforcement gap and is now supported for resolution by the appended SDK-replayed witness described below; no production bug or history deletion was required.

This review was source/evidence-only. No Native/model/UI probe was repeated, no frozen source/report/manifest was edited, and no live conversation, Native SQL, auth/config or personal draft was accessed. This new report is outside the 66 frozen review inputs.

## Exact correlation

- Archive: `dist/pi-durable-delm-0.1.0-native14-candidate-v2.tgz`, SHA256 `830e43da3e6119fad22507d29db7da0de94fa80817442b26ce4298ca323e7480`.
- Frozen review input: `evidence/native14/acceptance/candidate.json`, SHA256 `a8ffbcc6abeeba2834bc4cedff0b037e0a26a0c8275bbf1b693dc3fd25cd167f`.
- Independently recomputed all **66** review-input fingerprints, all **449** regular archive members against the external manifest, and all **37** current runtime fingerprints against both manifest and correlation result. All matched. No tar links, duplicate members or traversal; execution-only operator plan absent.
- The reviewed README, setup guide, standalone prompt, current contract/operations and shipped BOARD match the exact archive, not a different mutable tree.

Key reviewed source SHA256:

| Source | SHA256 |
| --- | --- |
| `scripts/delm_board.py` | `9c5bfc5f545be7eb8a63df14d68892a03a780c7e45dd03c4fa4be604a22382be` |
| `evidence/native14/acceptance/run-installed.py` | `6f71caa7abf13b8fadde43947c082dac16da7df8397b79e75db2c53a277e12ec` |
| `evidence/native14/acceptance/observer.mjs` | `bfe1c2813e3812699f6f891b808fd14ac8d31eac60f1567fb3b29020c0423d9c` |
| `README.md` | `a6a6024588e84c728020e454c4d164e064a3774d9b58deba7bfb22130167a32b` |
| `docs/agent-setup.md` | `257f1708f4f60c9d9b3c97713dd29af7e85d00dcf56298b65ffd210144ed40c1` |
| `prompts/setup-delm.md` | `2f6bdc925f77e3ecfbe068f60755227f5c97713698cfb656754785a08f3414cd` |

## Criterion-to-evidence assessment

| Supplied criterion | Verdict and direct evidence |
| --- | --- |
| Actual shipped interactive curses BOARD | PASS. Full `run-installed.py` and actual `interactive-board-terminal.txt` reviewed: correct `READ ONLY` header; real owner/tasks/fact paints; Enter detail, End reaches `SCROLL_FINAL_TAIL` after 120 note lines, escape, NOTES, no-match search, small-terminal resize warning and quit. These are real ANSI paints following PTY keys, not a static screenshot or `--once`. |
| Observer read-only and backend/owners survive quit | PASS. The script hashes both board databases before/after the observer, verifies the same deliberately unread receipt remains pending, verifies backend and both Native processes live, then successfully queries pending through the actual backend and explicitly stops both through their Native endpoints. Source `load_board` uses SQLite `mode=ro` plus `query_only`, and the observer has no actor read/ACK or service-restart operation. |
| No Native SQL legacy artifact in current test flow | PASS, scoped. Fresh product preparation and all scripted tool actions create no `dcg-reopen-sessions.json`; the optional historical manifest branch therefore is not entered by this N14 flow. That legacy observer mode still exists in source. This review does not certify historical manifest mode as SDK-only, and no artifact should be fabricated to populate native-wait badges. |
| Genuine current Native packaged skill and drafts | PASS before removal. Actual GenerationTask prompt witnesses are 6 Alice +3 Bob +7 reopened Bob, matching 16 model requests. All record packaged/project-local skill discovery and absence of synthetic drafts from non-system model context. The observer checks genuine requests without injecting a skill prompt; its scheduling barrier delegates the original admission before delaying return. |
| Ordinary-terminal operation without required manager | PASS. Product `open` is used through real PTYs, not pane/session RPC. Actual logs resolve SDK1.4.0. Scoped PATH excludes the named manager; all four process traces contain no manager exec. Native plain-terminal commands and the same read-only observer are explicit in the packaged help/setup documents. No terminal manager installation is required. |
| One GitHub URL onboarding scope | PASS offline. Full README, guide and separate prompt reviewed; links map to actual current contract/operations/skill/help, installation/bootstrap and real CLI flow. Historical run plans are explicitly not operator authority; unsupported hosts are not replaced. Agent may not infer model budget/roster or touch private settings. Public GitHub fetch and autonomous fresh-machine setup were not executed by this acceptance. |

The source-correlated final three-command log exits zero. Independently counted model records: Alice6/Bob3/reopenedBob7/post-remove1 =17; resolved versions are1.4.0. INET lines use one fixture loopback port, no manager exec or external destination. The retained initial QA failures are disclosed; they are not silently promoted to a clean run. No repeated 17-model execution was necessary for this review.

## Parent-blocking evidence gap outside the accepted UI scope

`lifecycle-result.json` claims `removedSkillAbsentActualNativePrompt:true`. However, none of the 66 frozen inputs is an `after-remove-actual-prompt.jsonl.txt` witness, and that file is absent from the supplied evidence directory. The actual after-removal model log contains one model request. `lifecycle.py` sets the true flag without reading/asserting an observation count or negative skill witness; `observer.mjs` logs only after its skill guards. Therefore a successful plain Native reply does not establish that the negative prompt assertion actually ran and passed.

Dave should first recover/hash the private observation if it exists. Otherwise fix only the measurement and require an explicit actual post-removal negative-skill observation, with witness count matched to the genuine model request; a bounded same-session continuation is sufficient. Do not rerun the 16 already supported main/UI cases or alter production bytes merely to satisfy a probe. The after-removal model log's historical union of `toolsAdded` contains `delm_wait`, but that union alone does **not** prove an active package extension remains; this review makes no such product-bug claim.

### Producer confirmation (board883)

Dave confirmed that the private after-removal observation file is absent and the actual terminal contains `Removed DeLM skill still advertised by Native`. The generation-hook exception is soft, so the green plain reply did not enforce the negative guard. The producer retracted the unsupported true flag while preserving the frozen66 history. This rules out my earlier tentative install-return/mutability lead: the hook did execute; the remaining question is active resource availability versus retained historical system/catalog/tool declarations. No request-history deletion or production patch is justified by the current evidence.

### Independently accepted append-only correction

Supplement manifest `postremove-supplement-candidate.json` SHA256 `1d1f0867646f4c0c28fb6690d536333b56f7bbd6bc350d93c7ef2bedfb98a885` freezes 15 new files. All15 fingerprints match; original66 fingerprints and all37 runtime files remain unchanged. Full supplement, `measure-postremove.py`, actual observer, Python hard validator, measurement/result and five negative cases were reviewed without another probe.

The actual same-session witness uses installed SDK1.4 `getCurrentSystemPrompt` / `getCurrentTools`, not ad-hoc string exclusions. It records two system messages: preserved historical catalogue, followed by actual `skills:null` and `delm:null` deltas. SDK replay correctly reports no **effective current** DeLM skill or wait tool, while retaining history. One measurement matches one actual model request. The external Python validator refuses missing/error/duplicate or mismatched records and active skill/tool before returning PASS. The five reported bad-record cases correspond directly to its hard assertions.

Both new process logs resolve SDK1.4 and contain one faux request each; both traces have zero INET. The preliminary content-only inspection is honestly insufficient, not counted as negative proof. The correction adds2faux/0live, yielding19 for clean proof plus correction,36 including the disclosed earlier17. No16-case main/UI rerun, production change, old66 overwrite or model-history deletion occurred. This closes the factual gap by retracting the unsupported old flag and proving the effective current catalogue instead of falsely demanding absent historical text.

A local read-only correlation command initially misclassified the numeric `negativeCasesHardRejected:5` as a boolean field; the corrected explicit five-field check passed. No producer data or Native execution changed for that reviewer check.

## Bounds

The accepted verdict covers the non-empty UI/read-only/terminal-neutral criteria and the concrete supplemental witness correction. Whole-task acceptance still requires the independent full-source reviewer and parent gate. The live four-actor SOURCE build was not reloaded, live model quality and arbitrary host/migration support were not tested, and unconfigured identity policy is not a privacy certificate. The user's later conditional commit/push authorization is tracked separately and becomes executable only after final acceptance; the offline QA's publication-not-performed label is not remote delivery proof.
