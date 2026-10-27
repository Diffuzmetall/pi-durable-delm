# Early actual current Native1.4 board integration

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/native14-host-integration.py` from this package root.

The successful run uses the same installed launcher/global-runtime/main/SDK1.4 as the independently reviewed frozen N14 baseline. It reuses `Native14Host` and Bob's existing one-line endpoint client, rather than creating a host, Harness, storage owner or substitute admission. A real Python board is served in a new private fixture; Native Bash calls the real bound actor CLI.

Result: **9 faux-model calls, 0 live calls**, two Native owners, real fresh claim and shared result, exact pending-wait reopen, same-ID approved-input replay, actual event wake, saved snapshot/read/explicit ACK, sent/acked status and no remaining receipt. Stop/resume submits no extra input. Only the exact owned board's IPv4 loopback port is allowed by the actual INET-connect trace audit; external INET connects are zero. Unix control is the explicitly approved plugin endpoint inside the original Native process.

The Native execution-environment guard is not disabled. The fixture explicitly selects the operator's existing installed trusted `durable-dcg` addon and `dcg` executable read-only because its new HOME otherwise has no addon. Successful actual Bash results pass through that real boundary. No personal policy, settings, credentials, session, SOURCE code or installed Native file is changed. Both sessions and all owned processes close normally.

Two failed QA probes are retained separately, not recorded as product failures or ignored as successful commands:

1. Blocking on a separate control RPC without draining real PTYs/shared observation streams timed out after the actual wake/readACK workflow. The consumer now drains all live owned terminal/view streams during that reply wait. It changes no production code or policy.
2. After all workflow assertions passed, an over-strict audit expected zero INET connects despite intentionally using a real localhost HTTP board. Retained traces showed only that exact board address/port. The audit now rejects every other INET target, and the corrected complete driver was run successfully from a fresh fixture.

`result.json` records hashes of eight actual product inputs before/after the successful run. `candidate.json` fingerprints the driver, successful result/logs, failures and this explanation. The original baseline's three driver files remain unchanged; Alice's earlier review is not silently extended to this new integration file. Alice can independently review this complementary major output without rerunning Native calls unless needed.

This is an **early target-code fixture**, not acceptance of an installed final archive, current live team build, final terminal-neutral setup instructions or the interactive packaged board. Those remain N14-ACCEPT criteria. The original public1.0.2/HOST05 proof is not used here.
