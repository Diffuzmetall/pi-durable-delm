"""Current registry bootstrap/preparation only: no Native process, SQL or models."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skills/delm/Tools/Run.py"


class Native14Preparation(unittest.TestCase):
    def test_current_registry_bootstrap_and_exact_approved_bytes(self):
        with tempfile.TemporaryDirectory(prefix="delm-n14-prepare-") as temporary:
            base = Path(temporary)
            project = base / "project"
            project.mkdir()
            (project / "AGENTS.md").write_text("Synthetic project instructions\n")
            global_rules = base / "global.md"
            global_rules.write_text("Synthetic explicit global instructions\n")
            plan = base / "plan.md"
            plan.write_bytes(b"# Approved plan\r\nOriginal bytes\r\n")
            prompt = base / "prompt.txt"
            approved = b"Approved original request\r\nDo not paraphrase.\r\n"
            prompt.write_bytes(approved)
            run = base / "run"
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            env.pop("DELM_CONFIG", None)
            prepared = subprocess.run([sys.executable, str(TOOL), "prepare", "--workspace", str(project),
                "--plan", str(plan), "--prompt-file", str(prompt), "--global-agents", str(global_rules),
                "--agents", "2", "--run-dir", str(run)], capture_output=True, text=True, env=env, timeout=30)
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            value = json.loads(prepared.stdout)
            self.assertTrue(value["prepared"])
            self.assertFalse(value["server_started"])
            self.assertEqual(value["native_launch"], "not-started")
            self.assertEqual(value["manual_core_commands"]["observer"],
                [sys.executable, str(ROOT / "scripts/delm_board.py"), str(run), "--observe"])
            self.assertEqual(value["manual_core_commands"]["server"],
                [sys.executable, str(ROOT / "scripts/delm_local.py"), "serve", str(run)])
            self.assertEqual(Path(value["inputs"]["prompt"]["captured"]).read_bytes(), approved)
            frozen = Path(value["inputs"]["plan"]["captured"])
            self.assertEqual(frozen.read_bytes(), plan.read_bytes())
            for actor in value["actors"]:
                adapter = (run / actor / "delm-adapter.js").read_text()
                self.assertIn(json.dumps(str(ROOT / "extensions/delm/native14.js")), adapter)
                self.assertNotIn("/extensions/delm/index.js", adapter)
                self.assertIn("export default base => install(base,", adapter)
                self.assertIn('actor: ' + json.dumps(actor), adapter)
                self.assertIn('run: ' + json.dumps(str(run)), adapter)
                self.assertIn(str(frozen), (run / actor / "START.md").read_text())
            # Mutating the original source after approval must not replace frozen input.
            prompt.write_text("A later different request")
            inspected = subprocess.run([sys.executable, str(TOOL), "status", "--run-dir", str(run)],
                capture_output=True, text=True, env=env, timeout=10)
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            self.assertTrue(json.loads(inspected.stdout)["approved_inputs_verified"])
            self.assertEqual(Path(value["inputs"]["prompt"]["captured"]).read_bytes(), approved)


if __name__ == "__main__":
    unittest.main()
