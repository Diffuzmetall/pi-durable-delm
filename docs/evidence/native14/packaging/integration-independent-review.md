# Alice independent review: actual Native14 board integration

What this change does: Dave's driver runs two actual installed Native1.4 owners against one real Python board. Their real tools claim/complete an early output, preserve a pending wait across exact reopen, deliver a wake, read the saved snapshot and explicitly ACK it.

**Looks good. Ship this component fixture.** No blocking finding at the intended two-local-root workload. This is not final installed package/launcher/TUI acceptance.

## Reviewed sources and actual flow

Read the complete `tests/native14-host-integration.py`, its imported `tests/native14-adapter-host.py` RPC client, the independently reviewed frozen baseline `tests/native14-host.py`, and result/candidate evidence. The reused RPC helper checks transport request identity and returns the real private-socket response; it does not fabricate owner state. Current helper SHA256: `2ad558a3f3a9584da2cd93f7ffd1996f5be87c30a0ef3678882a305dcc045838`. Final artifact freeze must retain the actual imported helpers as well as this driver's own files.

Only the model replies are substituted. Native executes the actual Bash commands through the selected existing DCG boundary. The producer writes a real shared file and completes the exact claimed generation/revision. The consumer's wait is armed before its process exits; reopen uses the same HOME/session and full persistent identity. Replaying the accepted input does not add a model request. The event wake then runs real actor CLI pending/snapshot/read/ACK and verifies no receipt remains. Status observes sent+ACKed; stop/resume add no input.

The driver creates only disposable workspaces/homes/board/processes, not another Harness or direct Native SQL owner. PTY/view streams are drained while a bounded real socket request waits, avoiding the earlier fixture deadlock. Cleanup addresses only its own processes. The actual local board port is the only admitted INET destination; there is no network fallback or guard disable.

## Fresh evidence checks

- **15 frozen source/evidence files** match `candidate.json` exactly.
- **8 product/runtime inputs** still match the hashes recorded during the successful run; no stale runtime evidence detected.
- Model logs contain Alice4, Bob-initial2 and Bob-reopen3 requests: **9 faux, 0 live**.
- All **9 INET connects** target one own127.0.0.1 board port. No external address/second port appears.
- Result explicitly reports pending wait persistence, same Native instance/wait, approved input replay, actual board event, snapshot/read/ACK, sent+ACKed status, shared result and stop/resume without extra input.
- Both initial fixture failures (blocked PTY/RPC and overstrict zeroINET expectation) are disclosed and retained. The successful later run is not presented as a production fix or a replay of old1.0.2 host evidence.

No second Native/model run was needed for this source/evidence review. The current controller-source correction in event831 changes neither this wire protocol nor these runtime hashes: shared `prompt` still fails to forward the approved stable ID, while this endpoint uses genuine selected admission and same-ID SDK submit.

Not checked: final installed complete launcher/skill/observer/one-URL setup, current team's loaded build and live models. Those remain the final N14-ACCEPT gate, not this early output.

Verdict: Ship the reviewed integration fixture.
