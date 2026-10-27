# Actual installed Pi Durable 1.4 fixture — N14-FIXTURE

## Result and exact scope

**PASS: usable isolated baseline driver for the actual installed Native1.4 entrypoint.** This is NOT a clone, an API-patched public1.0.2 host, a replacement main, or a fixture-created Harness. The historical HOST05 result is not evidence for this stage.

The driver launches the same executable as this team: user-local `pi-durable` → installed `host-lane/pi-durable` → Node with the installed `global-runtime.mjs` → installed `experimental/durable/main.ts`, including its actual global local-host composition and Jiti registry loader. The installed code and published SDK1.4 files are read-only. Only `ModelRuntime.create` is substituted inside each disposable test process, using the installed public `fauxProvider` and model collection. No actual user model/auth/configuration is loaded by that substitute.

Evidence: [fixture/result.json](evidence/native14/fixture/result.json). The result records exact SHA-256 for 12 launcher/loader/main/runtime/controller inputs and all three driver files; per-process model logs record actual resolved published Durable/AI/Chord1.4.0 module URLs, entry/manifest hashes and Node version. Hashes are verified unchanged after execution. Paths in public evidence are normalized; the private locator retains actual paths outside the package.

## Fresh checks

| Criterion | Result |
|---|---|
| Actual installed launcher, main, global runtime and real registry loader | PASS |
| Published Durable/AI/Chord physically resolved to installed1.4.0, no source-SDK fallback | PASS |
| Two distinct real owner-created Native sessions in one synthetic workspace | PASS |
| Existing real Hindsight `admit`/`submit` controller present | PASS |
| SDK-only read-only observer sees persisted real admission before model request | PASS |
| Shared socket requires attach; wrong cwd and unattached foreign conversation rejected | PASS |
| Owned socket mode0600, parent private directory | PASS |
| Two actual root inputs, including a real Native read tool and verified tool result | PASS: 3 model calls, 0 live model calls |
| Actual Native PTY retains unsent draft through external input/response | PASS; draft absent from real Native view history |
| Same launcher `--session` reopens exact session directory/id/cwd and old answer | PASS, no dummy prompt/model calls |
| Clean `/quit` closes all four actual host instances | PASS |
| `strace -f -e trace=connect` for all startup/input/reopen instances | PASS: no AF_INET/AF_INET6 connects |
| Current running team's loaded build, real private policies/provider configuration | NOT_TESTED / unchanged |
| Final N14 DeLM adapter/launcher install/E2E | NOT_TESTED by this early baseline |
| Caller-stable input ID through ordinary Native shared `prompt` | NOT_PROVIDED; transport ID is only correlation |

The real main creates each Harness and SQLite owner itself. The fixture never imports/constructs a Harness, opens Native SQLite or fabricates admission. The observer is an actual trusted `--extension` adapter which retains the registry and original controller, adds only a read-only SDK hook and returns the same registry. It queries `hindsight.context` through `api.snapshot`, not SQL and not a forged view.

The first probe wrongly assumed a custom SDK document appears in ordinary Native `ConversationView.docs`. The actual view does not promise that mount. Its successful startup/model/draft observations were not relabelled a complete PASS: the probe failed. The final driver observes the existing document through the supported SDK hook, preserving real admission. The initial failure is retained in `fixture/initial-custom-document-view-assumption.log`.

## Run the baseline

From this package root, with the same already-installed Native and public plugin dependencies:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/native14-host.py \
  --launcher "$HOME/.local/bin/pi-durable" \
  --antigravity-dir "$HOME/.pi/agent/npm/node_modules/pi-antigravity" \
  --evidence-dir docs/evidence/native14/fixture
```

Prerequisites are Python3 stdlib, Node supported by that existing installation, existing `strace`, and existing installed activity-panel terminal emulator dependency. No dependency installation, shell/host patch, copied source or new runtime is performed. Do not point the driver at personal sessions/configuration. Its own private `/tmp/n14-*` area, homes, settings, policies, sessions, logs and workspace are new synthetic test data. It prints that area's private `fixture-locator.json` after success.

The driver uses clean child environments and **creates** a restrictive fixture-only native-defaults policy (`codexDefault:false`), disabled memory configuration and faux default-model settings in those new homes. It does not read/copy/edit the operator's policy/auth/settings. MCP is disabled with the actual `--no-mcp`. The owner Hindsight controller remains real and persists its actual admissions even with memory networking disabled. This profile differs intentionally from the live operator profile; the result is a fixture PASS, not live activation or a test of a remote memory service.

A network trace is observational, not an authorization override. Faux routes reject unplanned or duplicate model requests. No provider fallback is allowed. The real default global adapter resolves the already-existing public Antigravity source tree read-only so it can load normally; its API/credentials are not called by this baseline.

## Reuse for final actual N14 candidate

`tests/native14-host.py` exports `installed_paths(launcher)` and `Native14Host(paths, owned_area, workspace, session=None, extensions=(), routes={}, antigravity=...)`. The fixture's test model routes map an exact marker substring to an ordered list of `{text:...}` or `{tool:..., arguments:{...}}` responses. Tool responses require an actual Native model declaration. `expectToolText` can assert that the subsequent model request contains the actual preceding Native tool result; the baseline exercises this with a real read of a synthetic workspace file. This changes only the model reply, not tool execution or policy.

The object exposes the actual subprocess command/environment, `request(type, **values)` for the host's existing shared observation/control socket, `latest_view()`, `wait_history(marker)`, `screen()`, and `model_events()`. `extensions` are forwarded to the actual main's trusted registry loader. Final Bob/Carol candidate testing can reuse this driver; it must use their approved stable-delivery seam rather than treating `request('prompt')` correlation IDs as durable IDs.

For exact reopen, reuse the original fixture's `HOME`, `PI_CODING_AGENT_DIR`, `XDG_CONFIG_HOME` and disabled-memory paths; pass its actual owner-created `session.sqlite` to `--session`. The baseline demonstrates this explicitly. A draft is recorded before cleanup; only the fixture's own synthetic editor draft is cleared for the real `/quit` command. No actual user pane/session/draft is touched and no synthetic draft is submitted.

The native socket is the already-supported `--listen`, not a new DeLM listener. No hot stable-input/control server is introduced. The bounded missing stable-input seam in [native14-contract.md](native14-contract.md) remains a separate Bob/Carol implementation/permission boundary. Shared prompt is used only for this non-retried synthetic baseline input, not as a claim of exactly-once delivery.

## Freeze and next gate

The three driver files and baseline evidence are frozen after N14-FIXTURE DONE for Alice's independent driver review. A final package acceptance must correlate its own final adapter/launcher bytes, actual SDK1.4 identity, real CLI/board/wait/read-ACK, initial stable input, denial/replay/reopen/stop/cancel and retained guards. It must separately report fixture PASS, current live build status, and no paid/live-model E2E. No historical result or version number substitutes for those checks.
