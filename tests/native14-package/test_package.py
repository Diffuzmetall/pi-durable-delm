"""Current-host packaging/docs checks, not Native runtime acceptance."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("native14_payload", ROOT / "packaging/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Native14PackageTest(unittest.TestCase):
    def test_explicit_registry_export_not_ordinary_pi_extension(self):
        metadata = json.loads((ROOT / "package.json").read_text())
        self.assertEqual(metadata["exports"]["./native14"], "./extensions/delm/native14.js")
        self.assertTrue((ROOT / metadata["exports"]["./native14"]).is_file())
        self.assertEqual(metadata["pi"]["extensions"], [])
        self.assertIn("1.4.0", metadata["peerDependencies"]["@earendil-works/pi-durable"])
        self.assertNotIn("host API patch", metadata["description"])

    def test_agent_reading_map_and_reusable_prompt(self):
        for relative in ("README.md", "docs/agent-setup.md", "prompts/setup-delm.md"):
            path = ROOT / relative
            text = path.read_text()
            for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                if "://" in link or link.startswith("#"):
                    continue
                target = (path.parent / link.split("#", 1)[0]).resolve()
                self.assertTrue(target.is_relative_to(ROOT), (relative, link))
                self.assertTrue(target.is_file(), (relative, link))
        for relative in ("docs/agent-setup.md", "prompts/setup-delm.md"):
            text = (ROOT / relative).read_text()
            self.assertNotIn("/home/ubuntu/", text)
            for contract in ("--observe", "--once", "request", "admission", "1.0.2", "1.4"):
                self.assertIn(contract, text)
        readme = (ROOT / "README.md").read_text()
        self.assertIn("## Настройка агентом по ссылке на GitHub", readme)
        self.assertIn("prompts/setup-delm.md", readme)
        self.assertIn("TUI входит", readme)

    def test_user_setup_is_terminal_neutral(self):
        for relative in ("README.md", "docs/agent-setup.md", "prompts/setup-delm.md"):
            with self.subTest(path=relative):
                text = (ROOT / relative).read_text()
                self.assertNotRegex(text.lower(), r"\b(?:tern|tmux|herdr)\b")
                self.assertIn("терминал", text)
        guide = (ROOT / "docs/agent-setup.md").read_text()
        self.assertIn("--session", guide)
        self.assertIn("lock", guide)
        self.assertIn("фоновую работу", guide)

    def test_visible_board_and_theme_startup_contract_is_shipped(self):
        for relative in ("prompts/setup-delm.md", "docs/agent-setup.md", "docs/user-guide.md"):
            with self.subTest(path=relative):
                self.assertIn("terminal-layout.md", (ROOT / relative).read_text())
        guide = (ROOT / "docs/terminal-layout.md").read_text()
        for contract in ("2×2", "постоянно видимой", "до запуска", "--session", "--continue", "--ansi"):
            self.assertIn(contract, guide)
        self.assertNotIn("/home/ubuntu/", guide)
        evidence = json.loads((ROOT / "evidence/native14/live-theme-reopen-2026-10-29.json").read_text())
        self.assertTrue(evidence["same_full_identities"])
        self.assertTrue(evidence["board_alongside_four_actors"])
        self.assertEqual(evidence["actors_reopened"], 4)
        self.assertFalse(evidence["bootstrap_replayed"])

    def test_real_archive_installs_same_tui_and_setup_prompt_without_runtime(self):
        with tempfile.TemporaryDirectory(prefix="delm-native14-package-") as temporary:
            directory = Path(temporary)
            for name in ("user.npmrc", "global.npmrc"):
                (directory / name).write_text("")
            result = subprocess.run(
                ["npm", "--offline", "--userconfig", str(directory / "user.npmrc"),
                 "--globalconfig", str(directory / "global.npmrc"), "pack", "--ignore-scripts", "--json",
                 "--pack-destination", str(directory), "--cache", str(directory / "npm-cache")],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
                env=dict(os.environ, HOME=str(directory), NPM_CONFIG_UPDATE_NOTIFIER="false"),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            archive = directory / json.loads(result.stdout)[0]["filename"]
            with tarfile.open(archive, "r:gz") as payload:
                for private_document in ("Pi-Durable-1.4-current-host-plan.md",
                                         "pi-durable-host-session-retrospective-2026-10-29.md"):
                    self.assertNotIn("package/docs/" + private_document, payload.getnames())
                for relative in ("scripts/delm_board.py", "prompts/setup-delm.md", "docs/agent-setup.md",
                                 "docs/terminal-layout.md", "evidence/native14/live-theme-reopen-2026-10-29.json",
                                 "extensions/delm/native14.js"):
                    self.assertEqual(payload.extractfile("package/" + relative).read(), (ROOT / relative).read_bytes())
                self.assertIn(b"DeLM BOARD | READ ONLY", payload.extractfile("package/scripts/delm_board.py").read())
            prefix = directory / "payload"
            installed = installer.install(archive, prefix)
            self.assertFalse(installed["native_registered"])
            root = Path(installed["root"])
            observer = subprocess.run(["python3", "-B", str(root / "scripts/delm_board.py"), "--help"],
                                      capture_output=True, text=True, timeout=10)
            self.assertEqual(observer.returncode, 0, observer.stderr)
            self.assertIn("--observe", observer.stdout)
            self.assertEqual(installer.install(archive, prefix)["status"], "unchanged")
            user_data = prefix / "my-run"
            user_data.mkdir()
            (user_data / "history").write_bytes(b"preserve")
            removed = installer.uninstall(prefix)
            self.assertEqual(removed["retained"], [])
            self.assertEqual((user_data / "history").read_bytes(), b"preserve")
            print("TUI_SHA256=" + hashlib.sha256((ROOT / "scripts/delm_board.py").read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
