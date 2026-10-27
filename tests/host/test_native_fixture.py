"""Unit checks for fixture safety, not mocked Native integration evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from native_process import NativeProcess


class NativeFixtureSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("source", "home", "project", "evidence"):
            (self.root / name).mkdir()
        self.fixture = dict(source=str(self.root / "source"), home=str(self.root / "home"),
            project=str(self.root / "project"), evidence=str(self.root / "evidence"), env={"DELM_HOST_DEPENDENCY_ROOTS": ""})
        self.locator = self.root / "fixture.json"

    def save(self):
        self.locator.write_text(json.dumps(self.fixture))

    def test_never_launches_source_outside_disposable_fixture(self):
        self.fixture["source"] = str(self.root.parent / "not-the-fixture")
        self.save()
        with self.assertRaises(AssertionError):
            NativeProcess(self.locator)

    def test_never_opens_sessions_outside_disposable_fixture(self):
        self.save()
        with self.assertRaises(AssertionError):
            NativeProcess(self.locator, session_directory=self.root.parent / "unrelated-sessions")

    def test_unmodified_baseline_rejects_changed_source(self):
        self.save()
        path = self.root / "source" / "marker.ts"
        path.write_text("original")
        (self.root / "evidence/public-host-discovery.json").write_text(json.dumps(dict(
            revision="cd32f7725fdbddbaecdff5b1e68491563394e0ca",
            source_hashes={"marker.ts": hashlib.sha256(path.read_bytes()).hexdigest()})))
        host = NativeProcess(self.locator)
        host.assert_original_source()
        path.write_text("changed")
        with self.assertRaisesRegex(AssertionError, "Not an unmodified Native fixture"):
            host.assert_original_source()


if __name__ == "__main__":
    unittest.main()
