# Exported delm skill — local authoring and compatibility evidence

## Authoring workflow

The available CreateSkill body, CreateSkill/ValidateSkill workflows, and active Pi philosophy/skills adapter were read in full and applied to this target only. Type: operations runbook with deterministic input/preparation tools. Structure, routing, gotchas, examples, intent-to-flag mappings, approved-input sufficiency and safety gates are present. No installed skill, personal config or global files were changed. The exported lowercase `skills/delm` name follows the explicit extraction scope and Pi/Agent Skills lowercase name contract rather than a LifeOS-global TitleCase directory convention.

Voice-service calls and global execution logging were not performed: the extraction authorizes only target writes and DeLM team coordination. This local report and `AuthoringExecution.jsonl` record the workflow instead. The active harness exposes skill bodies through file loading, not a callable skill-invocation tool; this is a body-loaded workflow, not a claim of native slash-command expansion.

Canonical `SkillHygieneGate.ts` was actually run against only the target skill. It returned exit 2, `TRACKED_VENDOR_CHECK_UNAVAILABLE: skills root must be inside its Git repository` (`evidence/hygiene.json`). The target was not initialized as a Git repository just to force this gate green. This check is **UNAVAILABLE**, not passed, and its identity-policy coverage is not claimed. Explicit public-content/structure tests and source review are separate checks, not a replacement certificate. No sensitive user identity files/configuration were copied into the export.

## Owning-boundary replay repair

The initial 3-test SDK baseline below did not cover a caller changing both text and its digest under an accepted request ID. Independent review reproduced that false replay acknowledgement (FAIL `70504f2f09b74e59800d099deb99016b`). Two new regressions first failed against the released implementation; no old PASS is presented as covering the defect.

The repair persists request ID → approved text SHA-256/input type atomically in an existing-host conversation-scoped SDK document before admission/submit. It adds no database owner, private host or raw SQL. Matching replay survives actual reopen and lost response; changed text/digest, unbound pre-existing submissions and different submission types refuse explicit reconciliation. Current `evidence/sdk-binding.log`: **5/5 SDK/faux PASS**, including both new regressions. Python preparation inputs/code were unchanged; the 7-test Python baseline was not rerun. Original `evidence/sdk.log` remains historical; the previous candidate hash manifest is superseded by `evidence/binding-candidate.sha256` for changed paths.

## New target tests

- `python3 -B -m unittest discover -s tests/launcher -v`: 7/7 PASS, `evidence/python.log`. Real bundled init for 2/4/8, exact approved prompt/plan/reference/instruction captures, no server/models during preparation, private file modes, existing-run and missing-instruction refusal, root/config isolation, fail-closed unsupported operations and read-only actual HTTP status.
- `node --import ./tests/native/sdk-loader.mjs --test tests/launcher/input-sdk.test.mjs`: 3/3 PASS, `evidence/sdk.log`. Existing installed public SDK 1.4.0 dependencies were resolved by the test-only public-export resolver. Disposable actual SDK SQLite/faux checks first input, stable replay, accepted-response loss followed by reopening the same SDK session, fingerprint/session/refusal guards. No private host implementation, real model, package install or extra production storage owner was used.

Use `DELM_TEST_NODE_MODULES` only when public dependencies are installed elsewhere; no machine path is embedded. The public SDK input helper is not a production host, socket transport or admission implementation. Tests deliberately supply a test admission stub; they cannot certify a real host policy.

## Function status, not silent parity removal

| Function | Status |
|---|---|
| Prepare original approved inputs, plan and 2/4/8 actor instructions | PASS target tests |
| Package-root configuration without author environment | PASS target tests |
| Separate/manual board and read-only observer commands, no Tern core dependency | PASS target tests; no automatic UI claim |
| Explicit protected SDK input helper, request replay, exact-session and digest checks | PASS SDK/faux, requires an existing real host capability |
| Stock Native automatic start/resume/notify/crew-stop | BLOCKED: no verified public production host-control integration |
| Skill discovery in the final assembled/install artifact | Deferred to independent PUB-07; having SKILL.md is not runtime discovery evidence |
| Full real UI draft preservation/reopen | NOT_TESTED in portable package; no draft is accessed by these tools, unsupported control refuses |
| Canonical full hygiene gate | UNAVAILABLE due missing Git tracking context, not a fabricated PASS |

The source launcher's private control/config dependencies were not carried forward or replaced with an allow-all policy. They remain explicit blocked capabilities, with the production integration request in `docs/native-compatibility.md`. The final release must preserve these statuses. Source/live runs/services/sessions and the installed private skill stayed read-only; all test inputs were newly created disposable fixtures.
