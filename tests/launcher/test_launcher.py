"""Portable installed-root preparation and fail-closed public-host boundary."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/delm/Tools/Run.py"
spec = importlib.util.spec_from_file_location("delm_launcher", SCRIPT)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.workspace = self.base / "project"
        self.workspace.mkdir()
        self.global_agents = self.base / "GlobalAgents.md"
        self.global_agents.write_text("Read full instructions; do not weaken admission.\n")
        (self.workspace / "AGENTS.md").write_text("Preserve peer/user work.\n")
        self.plan = self.workspace / "Plan.md"
        self.plan.write_text("Build a verified useful output; do not create extra models.\n")
        self.prompt = self.base / "approved.txt"
        self.prompt.write_text("Исходное поручение: preserve every constraint, do not publish.\n")
        self.reference = self.base / "reference.txt"
        self.reference.write_text("Explicitly authorized input, not conversation history.\n")
        self.config = dict(runs_root=str(self.base / "runs"), global_agents=str(self.global_agents))

    def prepare(self, count=2, name="run"):
        args = argparse.Namespace(workspace=str(self.workspace), plan=str(self.plan), prompt_file=str(self.prompt),
                                  reference=[str(self.reference)], global_agents=None, agents=count,
                                  run_dir=str(self.base / name))
        return launcher.prepare(self.config, args)

    def test_prepare_2_4_8_exact_inputs_and_no_launch(self):
        for count in (2, 4, 8):
            result = self.prepare(count, f"run-{count}")
            run = Path(result["run"])
            self.assertEqual(len(result["actors"]), count)
            self.assertFalse(result["server_started"])
            self.assertEqual(result["native_launch"], "not-started")
            self.assertFalse((run / "endpoint.json").exists())
            self.assertEqual((run / "launch.json").stat().st_mode & 0o777, 0o600)
            state = launcher.load(run)
            for key in ("prompt", "plan", "global_agents", "project_agents"):
                saved = state["inputs"][key]
                self.assertEqual(Path(saved["captured"]).read_bytes(), Path(saved["original"]).read_bytes())
                self.assertEqual(hashlib.sha256(Path(saved["captured"]).read_bytes()).hexdigest(), saved["sha256"])
            self.assertEqual(Path(state["inputs"]["references"][0]["captured"]).read_text(), self.reference.read_text())
            for actor, record in state["actors"].items():
                bootstrap = (run / actor / "records/bootstrap-input.txt").read_text()
                self.assertTrue(bootstrap.startswith(record["marker"]))
                self.assertIn("COMPLETELY", bootstrap)
                self.assertIn(str(self.global_agents), bootstrap)
                self.assertIn(str(run / "inputs/approved-plan.md"), bootstrap)
                self.assertIn(f"Authorized plan: {run / 'inputs/approved-plan.md'}.", (run / actor / "START.md").read_text())
                self.assertEqual(record["prompt"], "not-sent")
                self.assertIsNone(record["session"])
            self.assertIn("The original task remains authoritative", (run / "WORKER.md").read_text())
            self.assertEqual(result["manual_core_commands"]["observer"][-1], "--observe")

    def test_required_instructions_and_existing_run_preserved(self):
        self.global_agents.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.prepare()
        self.assertFalse((self.base / "run").exists())
        self.global_agents.write_text("restored fixture rules")
        self.prepare()
        before = (self.base / "run/launch.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.prepare()
        self.assertEqual((self.base / "run/launch.json").read_bytes(), before)

    def test_no_private_config_or_root_override(self):
        config = self.base / "user.json"
        config.write_text(json.dumps({"adapter_root": "/not-a-supported-override"}))
        with self.assertRaisesRegex(ValueError, "only runs_root"):
            launcher.configuration(str(config))
        config.write_text(json.dumps(self.config))
        self.assertEqual(launcher.configuration(str(config)), self.config)
        self.assertEqual(launcher.PACKAGE_ROOT, ROOT)

    def test_blocked_native_commands_spawn_nothing_preserve_state(self):
        self.prepare()
        manifest = self.base / "run/launch.json"
        before = manifest.read_bytes()
        for action in ("start", "resume", "notify", "stop"):
            result = subprocess.run([sys.executable, str(SCRIPT), "--config", str(self.base / "missing-config"),
                                     action, "--run-dir", str(self.base / "run")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("BLOCKED: no configured compatible existing Native", result.stderr)
            self.assertEqual(manifest.read_bytes(), before)
            self.assertFalse((self.base / "run/endpoint.json").exists())

    def test_capabilities_help_and_missing_manifest_without_service(self):
        for arguments in (["--help"], ["capabilities"]):
            result = subprocess.run([sys.executable, str(SCRIPT), *arguments], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        caps = json.loads(result.stdout)
        self.assertTrue(caps["python_core"])
        self.assertEqual(caps["native_launch"], "requires-existing-compatible-native")
        self.assertFalse(caps["installs_or_starts_native_host"])
        result = subprocess.run([sys.executable, str(SCRIPT), "status", "--run-dir", str(self.base / "absent")],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.base / "absent").exists())

    def test_readonly_status_with_real_board_http(self):
        self.prepare()
        run = self.base / "run"
        server = subprocess.Popen([sys.executable, str(ROOT / "scripts/delm_local.py"), "serve", str(run)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            while not (run / "endpoint.json").exists():
                if server.poll() is not None or time.monotonic() > deadline:
                    self.fail("owned fixture server did not start")
                time.sleep(0.01)
            before = (run / "context.sqlite").read_bytes()
            value = launcher.status(run)
            self.assertTrue(value["board_reachable"])
            self.assertEqual(value["tasks"], 0)
            self.assertEqual((run / "context.sqlite").read_bytes(), before)
            self.assertFalse(any(record["prompt"] != "not-sent" for record in value["actors"].values()))
        finally:
            server.terminate()
            server.wait(timeout=5)

    def test_portable_skill_structure_and_workflows(self):
        skill = ROOT / "skills/delm"
        body = (skill / "SKILL.md").read_text()
        for field in ("name: delm", "USE WHEN", "NOT FOR", "## Workflow Routing", "## Gotchas", "## Examples"):
            self.assertIn(field, body)
        self.assertLess(len(body.splitlines()), 500)
        for workflow in ("Prepare", "Launch", "Resume", "Recover"):
            content = (skill / "Workflows" / f"{workflow}.md").read_text()
            self.assertIn(f"Workflows/{workflow}.md", body)
            self.assertIn("Intent-to-Flag Mapping", content)
        self.assertFalse((skill / "Config.json").exists())
        self.assertFalse((skill / "Tools/FauxHost.mjs").exists())
        for file in skill.rglob("*"):
            if file.is_file() and "__pycache__" not in file.parts:
                text = file.read_text()
                self.assertNotIn("/home/ubuntu/", text)
                self.assertNotIn("HINDSIGHT_CONTROLLER", text)
                self.assertNotIn("USER/CUSTOMIZATIONS", text)


if __name__ == "__main__":
    unittest.main()
