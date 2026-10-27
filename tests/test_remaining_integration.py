"""Shared-checkout user flow via real authenticated actor-local CLI and HTTP."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/delm_local.py"


class RemainingIntegrationTest(unittest.TestCase):
    def test_four_and_eight_actor_delivery_handoff_and_recovery(self):
        for count in (4, 8):
            with self.subTest(actors=count), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                workspace = base / "shared"
                workspace.mkdir()
                run = base / "run"
                initialized = subprocess.run([sys.executable, str(SCRIPT), "init", str(run),
                                              "--shared-workspace", str(workspace), "--n", str(count),
                                              "--task", "integration fixture"], capture_output=True, text=True)
                self.assertEqual(initialized.returncode, 0, initialized.stderr)
                server = None
                counter = 0

                def stop():
                    if server is not None and server.poll() is None:
                        server.terminate()
                        server.wait(timeout=5)

                def start():
                    nonlocal server
                    (run / "endpoint.json").unlink(missing_ok=True)
                    server = subprocess.Popen([sys.executable, str(SCRIPT), "serve", str(run)],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    deadline = time.monotonic() + 5
                    while not (run / "endpoint.json").exists():
                        if server.poll() is not None or time.monotonic() > deadline:
                            self.fail("fixture server did not start")
                        time.sleep(0.01)

                def call(actor, op, expected=0, **args):
                    nonlocal counter
                    counter += 1
                    payload = {"request_id": f"integration-{counter}", **args, "op": op}
                    result = subprocess.run([str(run / actor / "bin/context"), "domain", json.dumps(payload)],
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                    return json.loads(result.stdout) if expected == 0 else result

                def create(subject, **args):
                    return call("alice", "create", subject=subject, detail="verified shared artifact", **args)["task"]

                def claim(actor, task):
                    return call(actor, "claim", item=task["id"], expected_revision=task["revision"])["task"]

                def owned(actor, op, task, **args):
                    return call(actor, op, item=task["id"], expected_revision=task["revision"],
                                generation=task["generation"], **args)

                start()
                try:
                    output = claim("alice", create("early output"))
                    artifact = workspace / "contract.txt"
                    artifact.write_text("usable shared contract\n")
                    output = owned("alice", "complete", output, summary="contract verified")["task"]
                    remainder = claim("alice", create("producer remainder"))
                    consumer = claim("bob", create("consume early output", deps=[output["id"]]))
                    self.assertEqual(artifact.read_text(), "usable shared contract\n")
                    lease = call("bob", "lease-acquire", task=consumer["id"], generation=consumer["generation"],
                                 paths=["contract.txt"], resources=["build:index"], ttl=300)["lease"]
                    call("alice", "lease-acquire", expected=1, task=remainder["id"], generation=remainder["generation"],
                         paths=["free-file", "contract.txt"], ttl=300)
                    projection = call("dave", "projection")
                    self.assertEqual(len(projection["leases"]), 1)
                    self.assertEqual(next(t for t in projection["queue"] if t["id"] == remainder["id"])["state"], "claimed")
                    transferred = owned("bob", "handoff", consumer, to="carol", summary="reuse shared result")["task"]
                    call("bob", "lease-handoff", task=consumer["id"], generation=transferred["generation"],
                         lease_id=lease["lease_id"], to="carol", ttl=300)
                    call("bob", "lease-renew", expected=1, task=consumer["id"], generation=consumer["generation"],
                         lease_id=lease["lease_id"], ttl=300)
                    failure = call("dave", "publish", type="FAIL", text="output requires correction", task=output["id"])["publication"]
                    for number in range(70):
                        call("dave", "publish", type="FACT", text=f"unrelated history {number}")
                    lost_request = "lost-snapshot"
                    receipt = call("carol", "snapshot", request_id=lost_request)
                    self.assertIn(failure["id"], [blocker["id"] for blocker in receipt["view"]["blockers"]])
                    self.assertGreaterEqual(len(receipt["view"]["events"]), 70)
                    stop()
                    start()
                    self.assertEqual(call("carol", "snapshot", request_id=lost_request), receipt)
                    self.assertEqual(call("carol", "pending")["receipts"][0]["receipt_id"], receipt["receipt_id"])
                    call("bob", "ack", expected=1, receipt_id=receipt["receipt_id"])
                    call("carol", "ack", receipt_id=receipt["receipt_id"])
                    call("alice", "publish", type="CORRECTION", text="producer fixed root cause", task=output["id"],
                         resolves=[failure["id"]])
                    delta = call("carol", "snapshot")
                    self.assertFalse(delta["full"])
                    self.assertFalse(delta["view"]["blockers"])
                    self.assertTrue(any(event["kind"] == "publication" and event["payload"]["type"] == "CORRECTION"
                                        for event in delta["view"]["events"]))
                    call("carol", "lease-release", task=transferred["id"], generation=transferred["generation"], lease_id=lease["lease_id"])
                    owned("carol", "complete", transferred, summary="consumer checks passed")
                    owned("alice", "release", remainder, summary="safe checkpoint, not falsely DONE")
                    with closing(sqlite3.connect(run / "context.sqlite")) as db:
                        before = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                    observed = subprocess.run([sys.executable, str(ROOT / "scripts/delm_board.py"), str(run), "--once"],
                                              capture_output=True, text=True, timeout=10)
                    self.assertEqual(observed.returncode, 0, observed.stderr)
                    self.assertIn("consume early output", observed.stdout)
                    final = call("dave", "projection")
                    self.assertEqual(next(t for t in final["queue"] if t["id"] == transferred["id"])["summary"],
                                     "consumer checks passed")
                    with closing(sqlite3.connect(run / "context.sqlite")) as db:
                        self.assertEqual(db.execute("SELECT COUNT(*) FROM events").fetchone()[0], before)
                    self.assertEqual(artifact.read_text(), "usable shared contract\n")
                    self.assertTrue(call("carol", "pending")["receipts"], "unacked delta remains replayable")
                finally:
                    stop()


if __name__ == "__main__":
    unittest.main()
