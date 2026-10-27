"""Installed DeLM CLI must not dirty immutable payload trees during normal use."""
import importlib.util
import os
import shlex
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("runtime_payload", ROOT / "packaging/install.py")
payload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(payload)


class RuntimeCleanTest(unittest.TestCase):
    def test_plain_python_and_bound_cli_allow_safe_update_and_removal(self):
        with tempfile.TemporaryDirectory(prefix="delm-runtime-clean-") as temporary:
            base = Path(temporary)
            archive, prefix, project, run = base / "core.tgz", base / "install", base / "project", base / "run"
            project.mkdir()
            # A real bundled CORE subset, not a mocked CLI or a Native host fixture.
            files = [ROOT / "package.json", ROOT / "bin/delm", ROOT / "prompts/delm-worker.md",
                     ROOT / "vendor/DeLM/LICENSE", *sorted((ROOT / "scripts").glob("*.py")),
                     *sorted((ROOT / "vendor/DeLM").rglob("*.py"))]
            with tarfile.open(archive, "w:gz") as target:
                for source in files:
                    target.add(source, arcname="package/" + source.relative_to(ROOT).as_posix())
            payload.install(archive, prefix)
            installed, record = payload.state(prefix)
            environment = dict(os.environ, HOME=str(base / "home"))
            environment.pop("PYTHONPATH", None)
            environment.pop("PYTHONDONTWRITEBYTECODE", None)
            for command in ([str(installed / "bin/delm"), "--help"],
                            [str(installed / "bin/delm"), "init", str(run), "--shared-workspace", str(project),
                             "--n", "2", "--task", "Core regression only; no models"],
                            [str(run / "alice/bin/context"), "domain", "--help"]):
                result = subprocess.run(command, cwd=base, env=environment, capture_output=True,
                                        text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                if "init" in command:
                    hint = shlex.split(result.stdout.split("; start: ", 1)[1].strip())
                    self.assertEqual(hint, [sys.executable, str(installed / "scripts/delm_local.py"), "serve", str(run)])
                    probe = subprocess.run(hint + ["--help"], cwd=base, env=environment,
                                           capture_output=True, text=True, timeout=10)
                    self.assertEqual(probe.returncode, 0, probe.stderr)
            self.assertEqual(list(installed.rglob("__pycache__")), [])
            self.assertEqual(payload.files(installed), record["files"])
            self.assertEqual(payload.install(archive, prefix)["status"], "unchanged")
            self.assertEqual(payload.uninstall(prefix)["retained"], [])
            self.assertTrue((run / "WORKER.md").exists())


if __name__ == "__main__":
    unittest.main()
