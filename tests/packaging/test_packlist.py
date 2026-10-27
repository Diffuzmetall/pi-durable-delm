"""Actual npm pack filtering; does not install or contact any package registry."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PacklistTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("npm"), "npm prerequisite unavailable; artifact build not verified")
    def test_python_caches_excluded_under_explicit_files_directories(self):
        rules=[ROOT / parent / ".npmignore" for parent in ("scripts","packaging","tests","examples","skills","vendor")]
        if not any(path.exists() for path in rules):
            self.skipTest("Source-build rules intentionally absent from npm payload; archive cache scan is a separate check")
        self.assertTrue(all(path.is_file() for path in rules), "Partial source checkout is missing build rules")
        with tempfile.TemporaryDirectory(prefix="delm-packlist-") as temporary:
            root = Path(temporary)
            files = json.loads((ROOT / "package.json").read_text())["files"]
            (root / "package.json").write_text(json.dumps(dict(name="delm-packlist-fixture", version="0.0.0", files=files)))
            expected = []
            for parent, content in (("scripts", "scripts"), ("packaging", "packaging"),
                                    ("tests", "tests/host"), ("examples", "examples/slugify"),
                                    ("skills", "skills/delm/Tools"), ("vendor", "vendor/DeLM/board")):
                (root / parent).mkdir(parents=True, exist_ok=True)
                (root / parent / ".npmignore").write_bytes((ROOT / parent / ".npmignore").read_bytes())
                destination = root / content
                (destination / "__pycache__").mkdir(parents=True)
                (destination / "__pycache__/private-cache.pyc").write_bytes(b"generated cache fixture")
                (destination / "stray.pyc").write_bytes(b"generated cache fixture")
                (destination / "kept.py").write_text("# legitimate source fixture\n")
                expected.append(content + "/kept.py")
            for name in ("user.npmrc", "global.npmrc"):
                (root / name).write_text("")
            environment = dict(os.environ, HOME=str(root), NPM_CONFIG_UPDATE_NOTIFIER="false")
            environment.pop("NODE_OPTIONS", None)
            result = subprocess.run(["npm", "--offline", "--cache", str(root / "npm-cache"),
                                     "--userconfig", str(root / "user.npmrc"),
                                     "--globalconfig", str(root / "global.npmrc"),
                                     "pack", "--ignore-scripts", "--json"], cwd=root, env=environment,
                                    capture_output=True, text=True, timeout=40)
            self.assertEqual(result.returncode, 0, result.stderr)
            packaged = [entry["path"] for entry in json.loads(result.stdout)[0]["files"]]
            self.assertTrue(all(name in packaged for name in expected), packaged)
            self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in packaged), packaged)
            self.assertFalse(any(name.endswith(".npmignore") for name in packaged), packaged)


if __name__ == "__main__":
    unittest.main()
