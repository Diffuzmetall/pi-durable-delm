# Independent Alice review of Dave's N14-FIXTURE

What this change does: it drives the actual installed Native1.4 executable through its real main, registry loader, PTY and private shared socket. It replaces only the model boundary in new disposable processes, so it can check real runtime behavior without paid model calls or personal session/config changes.

## Verdict

**Ship the baseline fixture as a reusable test driver. No blocking finding in the reviewed scope.** This is not final DeLM package/runtime acceptance.

Reviewed full files: `tests/native14-host.py`, `tests/native14-host-model.mjs`, `tests/native14-host-observer.mjs`, `docs/native14-fixture.md`, `docs/evidence/native14/fixture/result.json`, `candidate.json`. Traced actual installed launcher/main/shared commands in the preceding ABI investigation. Expected load: one local operator with two deterministic fixture roots, not a production load test.

The driver uses a fresh private directory, HOME and workspace; main creates the actual owner. It does not open Native SQL, construct a Harness, patch host source or touch current team panes. Owner admission is retained and observed through SDK snapshot in the actual registry hook. Model routing refuses unplanned/duplicate requests; the real read-tool result is checked. Shutdown clears only the fixture's synthetic draft and uses its own `/quit`, with bounded termination only for its owned process group.

## Fresh evidence correlation, without rerunning Native

- All **20 frozen fixture files** matched `candidate.json`; all **12 installed launcher/loader/runtime/controller source inputs** matched result hashes.
- All **12 resolved SDK entries** across four process logs matched actual installed entry and package-manifest hashes and version1.4.0.
- Model logs: Alice2 + Bob1 calls; both exact reopens0. Real SDK admission witnesses: Alice2 + Bob1. Four traces show **0 INET connects**.
- Both recorded actual PTY screens contain the expected answer and synthetic unsent draft. Driver asserts the draft is absent from Native history, the wrong workspace/foreign conversation are rejected and reopen returns the same session identity/history.
- Metadata distinguishes current live build NOT_TESTED, final DeLM integration NOT_TESTED and ordinary shared prompt stable-ID NOT_PROVIDED. It does not relabel the old1.0.2 host or turn correlation IDs into delivery IDs.

The earlier unsupported custom-document view assumption is disclosed and its failed probe retained; the final read-only observer uses actual SDK `snapshot`. Memory networking and Codex default behavior are disabled only in the new fixture profile; the original admission capability remains in use. These are test conditions, not live-policy coverage.

Not checked: final extension-owned stable-input/control seam, integrated board/wake/readACK/cancel/stop/resume, final installed interactive observer and agent setup, or current live team activation. Those require the final candidate gate. No duplicate Native/model run was needed for this independent source/evidence review.
