# Post-removal prompt evidence correction — independent finding 4876b0ee

This append-only supplement supersedes the unsupported negative-prompt inference in the original frozen 66-file input (`a8ffbcc6abeeba2834bc4cedff0b037e0a26a0c8275bbf1b693dc3fd25cd167f`). All original reviewed files remain byte-identical. Neither the 449-file archive nor any of its 37 runtime files changed.

## Confirmed defect in the measurement

Carol correctly found that the original lifecycle result set `removedSkillAbsentActualNativePrompt: true` without requiring a post-removal observer record. The private observer record did not exist. The terminal showed `Removed DeLM skill still advertised by Native`, but the generation hook's error was reported softly and the actual Native assistant still replied. Therefore assistant success was not evidence that the measurement succeeded. That inference is retracted, not silently rewritten in the old result.

The old observer searched `JSON.stringify` of **every historical system message**. Native/AI 1.4 uses a system-delta transcript: the leading system message contains the original catalogue, and later messages replace or remove named sections and tools. Preserving the old skill declaration in history is required message preservation, not evidence that the extension or skill is currently active.

## Actual bounded repair

The existing final fixture, session and conversation were reopened after removal, with no product extension, skill link, package reinstall, Native patch, policy substitution, or repeat of the 16 actor/UI cases. Two additional faux requests were used:

1. A preliminary content-only inspection established two real system-message records but was insufficient because catalogue data is in `sections`, not `content`. It is labelled preliminary and is not the negative proof.
2. The corrected observer used the **installed SDK 1.4** functions `getCurrentSystemPrompt` and `getCurrentTools` from `@earendil-works/pi-ai/utils/transcript`. It recorded its result before any harness assertion.

The actual final request has:

- Two system messages; the historical first `skills` section contains `<name>delm</name>`.
- A later update with **`skills: null` and `delm: null`**.
- SDK-replayed current prompt: **no DeLM skill**.
- SDK-replayed current tools: **no `delm_wait`**.
- Exactly **one actual measurement for one actual model request**. No live model was called.

See `postremove-current-prompt-result.json`, `postremove-measurement.json` and the final measurement process logs. This establishes removal of the **effective current catalogue/tool**, not deletion of historical messages.

## Hard failure propagation

`postremove_witness.validate` is a Python harness gate, not a soft Native hook. It requires the actual record, the exact request/record count, a successful measurement, preserved historical catalogue, absent effective skill and absent effective wait tool **before** returning or writing PASS.

The actual captured request passes this gate. Five deterministic bad-record cases — missing record, count mismatch, hook error, active skill, active wait tool — all raise hard assertion failures. See `postremove-hard-gate-result.json`. No Native/model rerun was used for those five checks.

## Scope

The clean original pipeline still has 17 faux requests; this bounded correction adds 2, making 19 for final proof plus correction, and **36 total including the disclosed earlier 17-request attempt**. There are zero live/paid requests. Supplementary process traces have zero INET connections. Original frozen evidence, actual installed Native/global settings/auth, running team and publication scope remain unchanged.

Independent reviewers must consume this correction and explicitly decide whether finding `4876b0eea5f84a0fb474b29e427101ab` is closed. The original unsupported flag alone remains insufficient.
