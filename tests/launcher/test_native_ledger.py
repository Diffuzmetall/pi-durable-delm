"""Launcher bookkeeping UNIT tests with synthetic RPC receipts, NOT real-host acceptance."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_host_preparation as preparation

launcher = preparation.launcher


class NativeLedger(unittest.TestCase):
    def setUp(self):
        preparation.PreparedInputIntegrity.setUp(self)
        self.calls = []
        self.sessions = {}
        self.accepted = {}
        self.lose_response = False
        self.addCleanup(patch.stopall)
        patch.object(launcher, "status", return_value={"board_reachable": True}).start()
        patch.object(launcher, "native_rpc", side_effect=self.rpc).start()

    def options(self, action="start", actor=None):
        return argparse.Namespace(action=action, actor=actor,
            host_source=str(self.base / "public-source") if action == "start" else None,
            socket=str(self.base / "native-server.sock") if action == "start" else None,
            input_file=None, request_id=None)

    def rpc(self, state, actor, operation, *, create=False, payload=None):
        persisted = json.loads((self.run / "launch.json").read_text())
        record = persisted["actors"][actor]
        self.assertEqual(record["session"], state["actors"][actor]["session"])
        session = record["session"]
        self.sessions.setdefault(session, dict(sessionId=session, sessionPath=str(self.base / (session + ".sqlite")),
            workspace=state["workspace"], conversationId=1, instanceId="instance-" + session))
        identity = self.sessions[session]
        self.calls.append((actor, operation, copy.deepcopy(payload), session))
        if operation != "identity":
            self.assertEqual(record["identity"], identity, "Identity must be persisted before bind/input")
        result = {}
        if operation == "input":
            saved = persisted["requests"][payload["requestId"]]
            self.assertEqual(saved["status"], "pending", "Persist uncertain request BEFORE RPC")
            self.assertEqual(saved["sha256"], hashlib.sha256(payload["text"].encode()).hexdigest())
            replay = payload["requestId"] in self.accepted
            self.accepted[payload["requestId"]] = payload["text"]
            if self.lose_response:
                self.lose_response = False
                raise RuntimeError("Synthetic RPC loses accepted response")
            result = {"accepted": True, "replay": replay}
        elif operation == "stop":
            result = {"stopped": True}
        elif operation == "resume":
            result = {"resumed": True}
        return {"delm_control": 1, "serverId": "unit-server", "identity": identity, "result": result}

    def test_start_reserves_all_ids_and_identity_before_input_and_reuses_exact_ids(self):
        first = launcher.control(self.run, self.options())
        before = launcher.load(self.run)
        self.assertEqual(len(self.sessions), 2)
        self.assertTrue(all(reply["accepted"] for reply in first["results"].values()))
        replay = launcher.control(self.run, self.options())
        self.assertEqual(len(self.sessions), 2)
        self.assertTrue(all(reply["replay"] for reply in replay["results"].values()))
        self.assertEqual(before["actors"], launcher.load(self.run)["actors"])

    def test_response_loss_keeps_pending_and_same_request_and_actor_ids(self):
        self.lose_response = True
        with self.assertRaisesRegex(RuntimeError, "loses accepted"):
            launcher.control(self.run, self.options())
        pending = launcher.load(self.run)
        self.assertEqual(len(pending["requests"]), 1)
        self.assertEqual(next(iter(pending["requests"].values()))["status"], "pending")
        ids = {actor: record["session"] for actor, record in pending["actors"].items()}
        reply = launcher.control(self.run, self.options())
        self.assertTrue(reply["results"]["alice"]["replay"])
        self.assertEqual(ids, {actor: record["session"] for actor, record in launcher.load(self.run)["actors"].items()})
        self.assertEqual(len(self.accepted), 2)

    def test_notification_key_cannot_acknowledge_different_approved_payload(self):
        launcher.control(self.run, self.options())
        args = self.options("notify", "alice")
        approved = self.base / "update.txt"
        approved.write_text("approved update A")
        args.input_file, args.request_id = str(approved), "update-1"
        launcher.control(self.run, args)
        count = len(self.calls)
        approved.write_text("different approved update B")
        with self.assertRaisesRegex(ValueError, "binding changed"):
            launcher.control(self.run, args)
        self.assertEqual(len(self.calls), count)

    def test_resume_and_stop_have_no_input_and_stop_can_clean_damaged_captures(self):
        launcher.control(self.run, self.options())
        count = len(self.accepted)
        launcher.control(self.run, self.options("resume"))
        Path(self.state["inputs"]["prompt"]["captured"]).write_text("damaged input")
        reply = launcher.control(self.run, self.options("stop"))
        self.assertTrue(all(item["stopped"] for item in reply["results"].values()))
        self.assertEqual(len(self.accepted), count)

    def test_actor_session_collision_and_retarget_are_refused_before_rpc(self):
        launcher.control(self.run, self.options())
        state = launcher.load(self.run)
        state["actors"]["bob"]["session"] = state["actors"]["alice"]["session"]
        launcher.save(self.run, state)
        count = len(self.calls)
        with self.assertRaisesRegex(ValueError, "collision"):
            launcher.control(self.run, self.options("resume"))
        args = self.options()
        args.socket = str(self.base / "different-server.sock")
        with self.assertRaisesRegex(ValueError, "retarget"):
            launcher.control(self.run, args)
        self.assertEqual(len(self.calls), count)

    def test_concurrent_launch_is_refused_without_rpc_or_manifest_mutation(self):
        before = (self.run / "launch.json").read_bytes()
        with launcher.launch_lock(self.run):
            with self.assertRaisesRegex(RuntimeError, "Another launcher"):
                launcher.control(self.run, self.options())
        self.assertEqual(before, (self.run / "launch.json").read_bytes())
        self.assertEqual(self.calls, [])

    def test_missing_identity_never_creates_replacement_on_resume(self):
        with self.assertRaisesRegex(RuntimeError, "BLOCKED"):
            launcher.control(self.run, self.options("resume"))
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
