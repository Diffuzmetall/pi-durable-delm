"""Launcher bookkeeping units, not real Native/admission execution evidence."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native14_run", ROOT / "skills/delm/Tools/Run.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherUnits(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="delm14-ledger-unit-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.project = self.base / "project"
        self.project.mkdir()
        (self.project / "AGENTS.md").write_text("Synthetic project instructions\n")
        rules = self.base / "rules.md"
        rules.write_text("Synthetic global instructions\n")
        plan = self.base / "plan.md"
        plan.write_text("Synthetic approved plan\n")
        prompt = self.base / "prompt.txt"
        prompt.write_bytes(b"Approved original\r\n")
        self.run = self.base / "run"
        launcher.prepare({}, SimpleNamespace(workspace=str(self.project), global_agents=str(rules),
            plan=str(plan), prompt_file=str(prompt), reference=[], run_dir=str(self.run), agents=2))
        self.state = launcher.load(self.run)
        self.state["native"] = {"protocol": launcher.PROTOCOL}
        self.state["actors"]["alice"]["socket"] = str(self.base / "synthetic.sock")
        folder = self.base / "native" / "synthetic-session"
        folder.mkdir(parents=True)
        session = folder / "session.sqlite"
        session.write_text("Synthetic marker, NOT a Native database")
        self.identity = dict(protocol=launcher.PROTOCOL, sdkVersion="1.4.0", run=str(self.run), actor="alice",
            workspace=str(self.project), sessionPath=str(session), sessionId=folder.name, conversationId=1,
            instanceId="synthetic-persistent-instance")
        launcher.save(self.run, self.state)
        self.args = SimpleNamespace(action="start", actor="alice", request_id=None, input_file=None)

    def test_pending_before_rpc_lost_response_and_changed_notify(self):
        calls, lose = [], [True]
        def rpc(state, actor, method, payload=None):
            if method == "identity":
                return {"identity": self.identity, "stopped": False}
            self.assertEqual(method, "input")
            persisted = launcher.load(self.run)
            self.assertEqual(persisted["actors"][actor]["identity"], self.identity)
            self.assertEqual(persisted["requests"][payload["requestId"]]["status"], "pending")
            calls.append(payload)
            if lose[0]:
                lose[0] = False
                raise RuntimeError("Synthetic response loss after acceptance")
            return dict(accepted=True, replay=True, requestId=payload["requestId"], conversationId=1)
        with patch.object(launcher, "native_rpc", side_effect=rpc), patch.object(launcher, "status", return_value={"board_reachable": True}):
            with self.assertRaisesRegex(RuntimeError, "response loss"):
                launcher.control(self.run, self.args)
            request = calls[0]["requestId"]
            self.assertEqual(launcher.load(self.run)["requests"][request]["status"], "pending")
            launcher.control(self.run, self.args)
            self.assertEqual(calls[0], calls[1])
            self.assertEqual(launcher.load(self.run)["requests"][request]["status"], "accepted")
            update = self.base / "update.txt"
            update.write_bytes(b"Approved update\r\n")
            self.args = SimpleNamespace(action="notify", actor="alice", request_id="same-update", input_file=str(update))
            launcher.control(self.run, self.args)
            count = len(calls)
            update.write_text("Changed update")
            with self.assertRaisesRegex(ValueError, "approval binding changed"):
                launcher.control(self.run, self.args)
            self.assertEqual(len(calls), count)

    def test_wrong_owner_identity_refuses_before_input(self):
        with patch.object(launcher, "native_rpc", return_value={"identity": {**self.identity, "actor": "bob"}}) as rpc, \
                patch.object(launcher, "status", return_value={"board_reachable": True}):
            with self.assertRaisesRegex(ValueError, "mismatch"):
                launcher.control(self.run, self.args)
            self.assertEqual(rpc.call_count, 1)
            self.assertNotIn("requests", launcher.load(self.run))

    def test_plain_terminal_open_persists_attempt_before_exec_and_never_sets_models(self):
        executable = self.base / "existing-native"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o700)
        args = SimpleNamespace(actor="alice", native_executable=str(executable))
        before = os.getcwd()
        def captured_exec(file, argv, env):
            saved = launcher.load(self.run)
            actor = saved["actors"]["alice"]
            self.assertTrue(actor["launch_attempt"])
            self.assertEqual(actor["pid"], os.getpid())
            self.assertEqual(argv, actor["argv"])
            self.assertEqual(file, str(executable))
            self.assertEqual(argv[1], "--no-mcp")
            self.assertNotIn("--model", argv)
            self.assertNotIn("--continue", argv)
            self.assertNotIn("--session", argv)
            self.assertEqual(env.get("HOME"), os.environ.get("HOME"))
            self.assertTrue(env["PATH"].startswith(str(self.run / "alice/bin")))
            socket_root = Path(actor["socket"]).parent
            self.addCleanup(shutil.rmtree, socket_root)
            self.assertEqual(socket_root.stat().st_mode & 0o777, 0o700)
            adapter = (self.run / "alice/delm-adapter.js").read_text()
            self.assertIn("native14.js", adapter)
            self.assertIn(json.dumps(actor["socket"]), adapter)
            raise RuntimeError("Captured exec; no Native started")
        try:
            with patch.object(launcher.sys.stdin, "isatty", return_value=True), \
                    patch.object(launcher.sys.stdout, "isatty", return_value=True), \
                    patch.object(launcher.os, "execve", side_effect=captured_exec):
                with self.assertRaisesRegex(RuntimeError, "Captured exec"):
                    launcher.open_actor(self.run, args)
        finally:
            os.chdir(before)

    def test_stop_remains_input_free_when_approved_bootstrap_is_damaged(self):
        launcher.record_identity(self.state, "alice", self.identity)
        launcher.save(self.run, self.state)
        (self.run / "alice/records/bootstrap-input.txt").write_text("Damaged approved bytes")
        with patch.object(launcher, "native_rpc", return_value={"stopped": True}) as rpc:
            value = launcher.control(self.run, SimpleNamespace(action="stop", actor="alice"))
            self.assertTrue(value["results"]["alice"]["stopped"])
            self.assertEqual(rpc.call_args.args[2], "stop")
            self.assertEqual(rpc.call_count, 1)

    def test_historical_binding_refuses_silent_migration(self):
        self.state["native"] = {"server_id": "historical", "socket": "historical"}
        launcher.save(self.run, self.state)
        with self.assertRaisesRegex(ValueError, "Historical Native binding"):
            launcher.load(self.run)

    def test_missing_recorded_session_refuses_replacement(self):
        launcher.record_identity(self.state, "alice", self.identity)
        launcher.save(self.run, self.state)
        Path(self.identity["sessionPath"]).unlink()
        with patch.object(launcher.sys.stdin, "isatty", return_value=True), \
                patch.object(launcher.sys.stdout, "isatty", return_value=True), \
                patch.object(launcher.os, "execve") as execute:
            with self.assertRaisesRegex(ValueError, "missing"):
                launcher.open_actor(self.run, SimpleNamespace(actor="alice", native_executable=None))
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
