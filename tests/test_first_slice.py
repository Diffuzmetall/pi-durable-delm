"""First-slice generated artifacts; fixtures are not real model sessions."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import delm_local as local


class FirstSliceTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.workspace = self.base / "shared"
        self.workspace.mkdir()
        self.run = self.base / "run"

    def initialize(self, run=None):
        with contextlib.redirect_stdout(io.StringIO()):
            local.initialize(run or self.run, None, "Execute docs/DeLM-first-slice-plan.md", 4,
                             self.workspace)

    def test_four_actor_snapshot_identity_and_safety(self):
        self.initialize()
        profile = (ROOT / "prompts/delm-worker.md").read_text()
        self.assertEqual((self.run / "WORKER.md").read_text(), profile)
        self.assertIn("delm-first-slice-v1", profile)
        self.assertIn("No Agent Mail", profile)
        self.assertIn("--no-mcp", profile)
        self.assertIn("ordinary `context read`", profile)
        self.assertEqual(self.run.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.run / "config.json").stat().st_mode & 0o777, 0o600)
        for actor in local.ACTORS:
            home = self.run / actor
            start = (home / "START.md").read_text()
            adapter = (home / "delm-adapter.js").read_text()
            self.assertIn(actor, start)
            self.assertIn(str(self.run / "WORKER.md"), start)
            self.assertIn("docs/DeLM-first-slice-plan.md", start)
            self.assertIn(str(self.workspace), start)
            self.assertNotIn("existing master branch", start)
            self.assertIn(actor, adapter)
            self.assertIn(str(self.run), adapter)
            self.assertIn("extensions/delm/index.js", adapter)
            self.assertNotIn("token", adapter.lower())
            self.assertFalse((home / "workspace").exists())
            self.assertEqual(local.workspace_path(self.run, actor), self.workspace)
            self.assertEqual((home / "bin/context").stat().st_mode & 0o777, 0o700)

    def test_run_inside_workspace_rejected_without_mutation(self):
        nested = self.workspace / "run"
        with self.assertRaisesRegex(ValueError, "outside"):
            self.initialize(nested)
        self.assertFalse(nested.exists())

    def test_early_output_done_releases_producer_for_remaining_work(self):
        self.initialize()
        board = local.board(self.run)
        output = board.reserve("alice", "profile output", "usable contract")["item"]
        board.done("alice", output, "profile ready")
        remainder = board.reserve("alice", "bootstrap remainder", "implementation")["item"]
        consumer = board.reserve("carol", "contract checks", "consume shared profile")["item"]
        from sqlite3 import connect
        with connect(self.run / "context.sqlite") as db:
            import json
            events = [(kind, json.loads(payload)) for kind, payload in
                      db.execute("SELECT kind,payload FROM events ORDER BY sequence")]
        self.assertTrue(any(kind == "done" and payload["item"] == output
                            for kind, payload in events))
        self.assertFalse(any(kind == "done" and payload["item"] in (remainder, consumer)
                             for kind, payload in events))
        self.assertEqual((self.run / "WORKER.md").read_bytes(),
                         (ROOT / "prompts/delm-worker.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
