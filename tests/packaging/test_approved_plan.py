"""Bundled init freezes approved authority independently of mutable source paths."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ApprovedPlanTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.project = self.base / "project"
        self.project.mkdir()
        self.run = self.base / "run"

    def initialize(self, *args):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        environment.pop("PYTHONPATH", None)
        return subprocess.run([sys.executable, "-B", str(ROOT / "scripts/delm_local.py"),
                               "init", str(self.run), "--shared-workspace", str(self.project),
                               "--n", "2", "--task", "Approved fixture only", *map(str, args)],
                              cwd=self.base, env=environment, capture_output=True, text=True, timeout=10)

    def test_actor_authority_points_to_frozen_bytes_not_mutable_source(self):
        plan = self.project / "PLAN.md"
        approved = "# Утверждённый план\nНе запускать модели.\n".encode()
        plan.write_bytes(approved)
        result = self.initialize("--plan", plan)
        self.assertEqual(result.returncode, 0, result.stderr)
        frozen = self.run / "inputs/approved-plan.md"
        self.assertEqual(frozen.read_bytes(), approved)
        self.assertEqual(frozen.stat().st_mode & 0o777, 0o600)
        self.assertEqual(frozen.parent.stat().st_mode & 0o777, 0o700)
        plan.write_text("Unapproved later changes")
        for actor in ("alice", "bob"):
            start = (self.run / actor / "START.md").read_text()
            self.assertIn(f"Authorized plan: {frozen}. Read it completely.", start)
            self.assertNotIn(f"Authorized plan: {plan}.", start)
            self.assertIn(f"Original plan source (provenance only): {plan}.", start)
        self.assertEqual(frozen.read_bytes(), approved)

    def test_missing_plan_refused_before_run_creation(self):
        result = self.initialize("--plan", self.project / "missing.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.run.exists())

    def test_no_plan_keeps_legacy_task_only_behavior(self):
        result = self.initialize()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.run / "inputs").exists())
        self.assertIn("No separate plan supplied", (self.run / "alice/START.md").read_text())


if __name__ == "__main__":
    unittest.main()
