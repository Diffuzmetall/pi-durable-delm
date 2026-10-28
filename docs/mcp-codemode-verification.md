# Scoped MCP/CodeMode review — 2026-10-28

## Result and boundaries

**Scoped source/component checks passed; live smoke is 3/4, not 4/4.** Alice, Bob and Carol each executed the actual builtin `codemode`: arithmetic returned `2`, nested Native `read` returned their own START header, and real local stdio MCP `ctx_stats` returned successfully. The original `ctx_search` failed with `Knowledge base is empty — no content has been indexed yet`; it is not a search PASS. The user approved a different read-only MCP check, and separate RESOLUTION publications closed the smoke blockers without deleting that history.

Dave was excluded at handoff because of an unsent editor draft. Later board notices report that his old UI/process disappeared and that the operator reopened the saved session; those notices do not establish draft restoration. This review did not touch his process, input or panel and certifies only the three directly inspected sessions, not 4/4. Draft restoration remains unverified. The original old team was not migrated. Final installed-artifact acceptance remains **PENDING_N14_ACCEPT**; none of the historical archive hashes or acceptance reports were rewritten. No new release archive or deployment was produced (packaging checks used temporary test payloads only).

- [Policy and startup/reopen instructions](mcp-and-codemode.md)
- [Safe scoped machine evidence](evidence/native14/mcp/scoped-result.json)
- [Safe installed-Native stdio probe result](evidence/native14/mcp/stdio-probe-result.json)

## Review

Reviewed the launcher `open_actor` callers, the Native registry/admission boundary, SDK fixtures, MCP stdio fixture and actual-host driver, documentation, and provenance/parity. Expected scale is one local shared-checkout team with 2/4/8 actors; synthetic four-actor argv checks are not four live models.

The adapter checks the installed host's MCP registry and builtin tool before DeLM setup. The launcher keeps Native's default configuration or forwards an explicit single-server/tool profile, retains it on exact reopen, and rejects incomplete profiles before recording a launch attempt. It does not set model/auth configuration. Native remains responsible for MCP tool permissions. A registry/tool name alone is not transport acceptance: actual nested results were checked separately.

Review found two Python regression failures: worker-policy checks required explicit `No Agent Mail` and `--no-mcp` safety wording. The prompt now explicitly prohibits Mail for team coordination and prohibits `--no-mcp` fallback; this preserves MCP-on rather than restoring the old policy. No tests were weakened. Seven stale provenance `packaged_sha256` values were refreshed; the worker prompt is now `adapted`, retaining its original `source_sha256`.

No remaining blocking finding in this scope. Default Native startup can initialize enabled servers, including Mail: restricted projects must choose their permitted profile **before startup**. This is documented, not bypassed. Independent agents were not launched; this is a local scoped review, not a new independent milestone acceptance.

## Verification

Commands run from the repository root with existing installed dependencies only:

```sh
DELM_TEST_NODE_MODULES="$EXISTING_NATIVE_NODE_MODULES" node --import ./tests/native/sdk-loader.mjs \
  --test tests/native14-mcp-policy.test.mjs tests/native14-adapter.test.mjs \
  tests/native14-adapter-control.test.mjs
python3 -B tests/native14-launch-control.py
python3 -B -m unittest discover -s tests/packaging -v
python3 -B -m unittest discover -s tests/native14-package -p 'test_*.py' -v
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
PYTHONPATH=tests python3 -B -m unittest \
  test_first_slice.FirstSliceTest.test_four_actor_snapshot_identity_and_safety \
  test_scale.ScaleTest.test_future_worker_profile_and_offline_help -v
python3 -B -m unittest discover -s examples/slugify -v
node "$SKILL_HYGIENE_GATE" --skills-root "$PWD/skills" --skill delm --json
```

- Targeted installed SDK 1.4: **8 PASS, 0 FAIL/SKIP**. Launcher bookkeeping: **8 PASS**, including synthetic all-four profile persistence/exact-session checks.
- Packaging: **10 PASS**; Native14 package/docs: **4 PASS**. Runtime provenance hashes and temporary payload installation/removal checks passed. Final prompt hash was checked again after the small prompt correction.
- Python core: initial run **46 PASS / 2 FAIL**; after the prompt correction, both affected tests **PASS**. The other 46 tests were not needlessly repeated. Unicode demo: **1 PASS**.
- Scoped skill hygiene: **0 violations**, no tracked vendored dependencies; `identityScan=unconfigured`, zero identity patterns. This is **not privacy certification**.
- Markdown links and added public evidence were checked locally; no private paths, raw journal content, statistics payload, configs, tokens, SQLite or screenshots were exported.

The operator-provided actual installed-Native probe was inspected, not rerun just to repeat a completed check. It uses the real product `open`, builtin CodeMode/nested read and actual stdio MCP echo; only the model is deterministic/faux (**0 live model calls**). It also records exact reopen/replay, lost-acceptance recovery, changed-replay refusal, stop/resume and a synthetic draft. It is one focused actor, not final installed-package/full-team acceptance.

For the three live sessions, read-only Native journals were correlated directly: model assistant toolCall named `codemode`, matching terminal parent/result, completed nested `read` and `ctx_stats` tasks, and result details reporting both nested calls `ok`. The safe evidence records entry/task locators and hashes, not conversation or account data. Board DONE/self-reports alone were not treated as proof.

The new evidence applies to this MCP change only. Old `current_live_team_build`, model-count and frozen-candidate fields in provenance/parity retain their original historical scope; the new scoped blocks explicitly mark that boundary.
