"""HOST-03 preparation integrity; not a real-host lifecycle/discovery claim."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("host_preparation_launcher", ROOT / "skills/delm/Tools/Run.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class PreparedInputIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        project = self.base / "project"
        project.mkdir()
        self.originals = {}
        for key, name, body in (
            ("global_agents", "GlobalAgents.md", "Read real rules and preserve current drafts.\n"),
            ("prompt", "approved-prompt.txt", "Original approved task, no live models or publication.\n"),
            ("reference", "reference.md", "Only this reference is authorized.\n"),
        ):
            source = self.base / name
            source.write_text(body)
            self.originals[key] = source
        for key, name in (("project_agents", "AGENTS.md"), ("plan", "Plan.md")):
            source = project / name
            source.write_text("Approved frozen " + key + "\n")
            self.originals[key] = source
        self.run = self.base / "run"
        self.args = argparse.Namespace(workspace=str(project),
            global_agents=str(self.originals["global_agents"]), plan=str(self.originals["plan"]),
            prompt_file=str(self.originals["prompt"]), reference=[str(self.originals["reference"])],
            agents=2, run_dir=str(self.run))
        launcher.prepare({}, self.args)
        self.state = json.loads((self.run / "launch.json").read_text())

    def test_all_approved_captures_and_bootstraps_are_verified_without_original_reads(self):
        for original in self.originals.values():
            original.unlink()
        self.assertEqual(launcher.load(self.run), self.state)

    def test_init_frozen_plan_and_preinit_input_bytes_survive_original_changes(self):
        before = {key: source.read_bytes() for key, source in self.originals.items()}
        args = copy.copy(self.args)
        args.run_dir = str(self.base / "run-mutating-originals")
        real_run = launcher.subprocess.run
        def initialize_then_change_sources(*positional, **keywords):
            result = real_run(*positional, **keywords)
            for source in self.originals.values():
                source.write_text("unapproved source edit after init")
            return result
        with patch.object(launcher.subprocess, "run", side_effect=initialize_then_change_sources):
            launcher.prepare({}, args)
        run = Path(args.run_dir)
        state = launcher.load(run)
        for key in ("prompt", "plan", "global_agents", "project_agents"):
            self.assertEqual(Path(state["inputs"][key]["captured"]).read_bytes(), before[key])
        self.assertEqual(Path(state["inputs"]["references"][0]["captured"]).read_bytes(), before["reference"])
        self.assertEqual(state["plan"], str(run / "inputs/approved-plan.md"))
        self.assertIn(f"Authorized plan: {state['plan']}.", (run / "alice/START.md").read_text())
        self.assertNotIn(str(self.originals["plan"]), (run / "alice/records/bootstrap-input.txt").read_text())

    def test_original_prompt_crlf_bytes_are_not_normalized_between_init_and_capture(self):
        original = b"First approved line\r\nSecond approved line\r\n"
        self.originals["prompt"].write_bytes(original)
        args = copy.copy(self.args)
        args.run_dir = str(self.base / "run-crlf")
        launcher.prepare({}, args)
        run = Path(args.run_dir)
        self.assertEqual((run / "inputs/approved-prompt.txt").read_bytes(), original)
        self.assertEqual((run / "alice/records/prompt.txt").read_bytes(), original)

    def test_each_changed_capture_and_reference_refuses_control_reconciliation(self):
        records = [self.state["inputs"][key] for key in ("prompt", "plan", "global_agents", "project_agents")]
        records += self.state["inputs"]["references"]
        for record in records:
            with self.subTest(input=Path(record["captured"]).name):
                file = Path(record["captured"])
                before = file.read_bytes()
                file.write_bytes(before + b"changed after approval")
                with self.assertRaisesRegex(ValueError, "Approved input fingerprint"):
                    launcher.load(self.run)
                file.write_bytes(before)

    def test_changed_actual_bootstrap_is_not_certified_as_prepared(self):
        file = self.run / "alice/records/bootstrap-input.txt"
        file.write_text("different input, same launch record")
        with self.assertRaisesRegex(ValueError, "Bootstrap input fingerprint"):
            launcher.load(self.run)

    def test_capture_symlink_is_refused_even_for_identical_bytes(self):
        record = self.state["inputs"]["prompt"]
        captured = Path(record["captured"])
        captured.unlink()
        captured.symlink_to(self.originals["prompt"])
        with self.assertRaisesRegex(ValueError, "escapes"):
            launcher.load(self.run)

    def test_manifest_path_escape_and_malformed_bindings_fail_closed(self):
        mutations = (
            lambda state: state["inputs"]["prompt"].update(captured=str(self.originals["prompt"])),
            lambda state: state.update(actors={"../other": state["actors"]["alice"]}),
            lambda state: state.update(actors={"": state["actors"]["alice"]}),
            lambda state: state.update(inputs=[]),
            lambda state: state["inputs"].update(references=None),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                state = copy.deepcopy(self.state)
                mutate(state)
                (self.run / "launch.json").write_text(json.dumps(state))
                with self.assertRaises(ValueError):
                    launcher.load(self.run)


if __name__ == "__main__":
    unittest.main()
