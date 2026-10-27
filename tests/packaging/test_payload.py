"""Local payload manager uses genuine tgz files; no Native registration claimed."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("payload_install", ROOT / "packaging/install.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


class PayloadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prefix = self.root / "user"

    def archive(self, version, extras=None):
        archive = self.root / (version + ".tgz")
        content = {"package/package.json": json.dumps(dict(name="pi-durable-delm", version=version)),
                   "package/bin/delm": "#!/usr/bin/env python3\nprint('" + version + "')\n"}
        content.update(extras or {})
        with tarfile.open(archive, "w:gz") as target:
            for name, value in content.items():
                data = value.encode()
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o755 if name.endswith("bin/delm") else 0o644
                target.addfile(info, io.BytesIO(data))
        return archive

    def test_manifest_and_runtime_provenance_are_complete(self):
        metadata = json.loads((ROOT / "package.json").read_text())
        self.assertEqual(metadata["pi"], dict(extensions=[], skills=["./skills/delm"], prompts=[], themes=[]))
        self.assertTrue(metadata["private"])
        self.assertEqual(metadata["license"], "MIT")
        self.assertTrue((ROOT / "LICENSE").read_text().startswith("MIT License\n"))
        inventory = json.loads((ROOT / "provenance.json").read_text())["files"]
        recorded = {entry["target"] for entry in inventory}
        for entry in inventory:
            with self.subTest(path=entry["target"]):
                self.assertEqual(manager.digest((ROOT / entry["target"]).read_bytes()), entry["packaged_sha256"])
        runtime = {"package.json", "bin/delm", "packaging/install.py"}
        for directory in ("scripts", "vendor/DeLM", "prompts", "extensions/delm", "skills/delm"):
            runtime.update(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob("*")
                           if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
        self.assertEqual(recorded, runtime)

    def test_repeat_update_rollback_and_default_data_preservation(self):
        old, new = self.archive("0.1.0"), self.archive("0.2.0")
        first = manager.install(old, self.prefix)
        self.assertFalse(first["native_registered"])
        self.assertEqual(manager.install(old, self.prefix)["status"], "unchanged")
        (self.prefix / "my-run").mkdir()
        (self.prefix / "my-run/history.sqlite").write_bytes(b"user data, not managed")
        previous = manager.state(self.prefix)[0]
        manager.install(new, self.prefix)
        self.assertNotEqual(manager.state(self.prefix)[0], previous)
        manager.rollback(self.prefix)
        self.assertEqual(manager.state(self.prefix)[0], previous)
        self.assertEqual(manager.state(self.prefix)[1]["version"], "0.1.0")
        result = manager.uninstall(self.prefix)
        self.assertEqual(len(result["removed"]), 2)
        self.assertFalse((self.prefix / "current").exists())
        self.assertEqual((self.prefix / "my-run/history.sqlite").read_bytes(), b"user data, not managed")

    def test_modified_and_untracked_files_are_not_overwritten_or_deleted(self):
        old, new = self.archive("0.1.0"), self.archive("0.2.0")
        manager.install(old, self.prefix)
        root = manager.state(self.prefix)[0]
        script = root / "bin/delm"
        script.write_text("user edit\n")
        extra = root / "user-notes.txt"
        extra.write_text("keep me")
        with self.assertRaisesRegex(ValueError, "modified"):
            manager.install(new, self.prefix)
        self.assertEqual(manager.state(self.prefix)[0], root)
        result = manager.uninstall(self.prefix)
        self.assertEqual(result["retained"], [str(root)])
        self.assertEqual(script.read_text(), "user edit\n")
        self.assertEqual(extra.read_text(), "keep me")

    def test_unrelated_current_and_versions_symlink_refused(self):
        self.prefix.mkdir()
        (self.prefix / "current").write_text("user file")
        archive = self.archive("0.1.0")
        with self.assertRaises(ValueError):
            manager.install(archive, self.prefix)
        self.assertEqual((self.prefix / "current").read_text(), "user file")
        (self.prefix / "current").unlink()
        external = self.root / "external"
        external.mkdir()
        (self.prefix / "versions").symlink_to(external, target_is_directory=True)
        with self.assertRaises(ValueError):
            manager.install(archive, self.prefix)
        self.assertEqual(list(external.iterdir()), [])

    def test_untrusted_archive_traversal_and_links_refused_without_activation(self):
        for name in ("../escape", "package/../../escape", "/absolute"):
            with self.subTest(name=name):
                archive = self.archive("0.1.0", {name: "not allowed"})
                with self.assertRaises(ValueError):
                    manager.install(archive, self.prefix)
                self.assertIsNone(manager.state(self.prefix))
        archive = self.root / "link.tgz"
        with tarfile.open(archive, "w:gz") as target:
            info = tarfile.TarInfo("package/link")
            info.type = tarfile.SYMTYPE
            info.linkname = "../../outside"
            target.addfile(info)
        with self.assertRaises(ValueError):
            manager.install(archive, self.prefix)
        self.assertIsNone(manager.state(self.prefix))


if __name__ == "__main__":
    unittest.main()
