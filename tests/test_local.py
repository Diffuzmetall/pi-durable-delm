import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "delm_local.py"


class LocalBoardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.source.mkdir()
        (self.source / "solution.txt").write_text("original\n")
        self.run = self.base / "run"
        self.invoke("init", str(self.run), "--source", str(self.source), "--task", "Test coordination")
        self.start_server()

    def invoke(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), *args], text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout

    def start_server(self):
        endpoint = self.run / "endpoint.json"
        endpoint.unlink(missing_ok=True)
        self.log = tempfile.TemporaryFile(mode="w+")
        self.addCleanup(self.log.close)
        self.server = subprocess.Popen([sys.executable, str(SCRIPT), "serve", str(self.run)],
                                       stdout=self.log, stderr=self.log)
        self.addCleanup(self.stop_server)
        for _ in range(100):
            if endpoint.exists():
                return
            if self.server.poll() is not None:
                self.log.seek(0)
                self.fail(self.log.read())
            time.sleep(0.03)
        self.fail("server did not start")

    def stop_server(self):
        if self.server.poll() is None:
            self.server.terminate()
            self.server.wait(timeout=5)

    def cli(self, actor, *args, expected=0):
        return json.loads(self.invoke("context", str(self.run), actor, *args, expected=expected))

    def test_coordination_files_conflict_and_restart(self):
        reservation = self.cli("alice", "reserve", "--subject", "fix", "--detail", "repair solution")
        item = reservation["item"]
        refused = self.cli("bob", "claim", "--item", item)
        self.assertFalse(refused["won"])
        self.cli("bob", "done", "--item", item, "--summary", "not mine", expected=1)
        alice = self.run / "alice" / "workspace" / "solution.txt"
        bob = self.run / "bob" / "workspace" / "solution.txt"
        alice.write_text("fixed\n")
        done = self.cli("alice", "done", "--item", item, "--summary", "fixed", "--attach", "solution.txt")
        replay = self.cli("alice", "done", "--item", item, "--summary", "fixed", "--attach", "solution.txt")
        self.assertEqual(done["publication_id"], replay["publication_id"])
        bob.write_text("local edit\n")
        conflict = self.cli("bob", "apply", "--id", done["publication_id"], expected=1)
        self.assertFalse(conflict["applied"])
        self.assertEqual(bob.read_text(), "local edit\n")
        bob.write_text("original\n")
        applied = self.cli("bob", "apply", "--id", done["publication_id"])
        self.assertTrue(applied["applied"])
        self.assertEqual(bob.read_text(), "fixed\n")
        self.stop_server()
        self.start_server()
        view = self.cli("bob", "read", "--all")
        self.assertEqual(view["queue"][0]["state"], "done")
        self.assertEqual(view["queue"][0]["owner"], "alice")

    def test_simultaneous_claim_single_winner(self):
        published = self.cli("alice", "publish", "--items", json.dumps([
            {"subject": "one job", "detail": "only one owner"}]))
        item = published["items"][0]["id"]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda actor: self.cli(actor, "claim", "--item", item), ("alice", "bob")))
        self.assertEqual(sum(result["won"] for result in results), 1)

    def test_worker_launcher_environment(self):
        binary_dir = self.base / "bin"
        binary_dir.mkdir()
        binary = binary_dir / "pi-durable"
        binary.write_text('#!/bin/sh\nprintf "cwd=%s\\nargs=%s\\n" "$PWD" "$*"\ncommand -v context\n')
        binary.chmod(0o700)
        env = dict(os.environ, PATH=str(binary_dir) + os.pathsep + os.environ["PATH"])
        result = subprocess.run([sys.executable, str(SCRIPT), "worker", str(self.run), "alice", "--continue"],
                                env=env, text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"cwd={self.run / 'alice' / 'workspace'}", result.stdout)
        self.assertIn("args=--no-mcp --continue", result.stdout)
        self.assertIn(str(self.run / "alice" / "bin" / "context"), result.stdout)
        adapter = self.run / "alice" / "delm-adapter.mjs"
        adapter.write_text("export default registry => registry;\n")
        reopened = subprocess.run([sys.executable, str(SCRIPT), "worker", str(self.run), "alice", "--continue"],
                                  env=env, text=True, capture_output=True, timeout=5)
        self.assertEqual(reopened.returncode, 0, reopened.stderr)
        self.assertIn(f"args=--no-mcp --extension {adapter} --continue", reopened.stdout)
        js_adapter = self.run / "alice" / "delm-adapter.js"
        js_adapter.write_text("export default registry => registry;\n")
        fresh = subprocess.run([sys.executable, str(SCRIPT), "worker", str(self.run), "alice", "--continue"],
                               env=env, text=True, capture_output=True, timeout=5)
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        self.assertIn(f"args=--no-mcp --extension {js_adapter} --continue", fresh.stdout)

    def test_four_peers_shared_workspace_and_observer(self):
        self.stop_server()
        self.run = self.base / "shared-run"
        self.invoke("init", str(self.run), "--shared-workspace", str(self.source),
                    "--n", "4", "--task", "Wait for plan")
        self.start_server()
        actors = ("alice", "bob", "carol", "dave")
        for actor in actors:
            self.assertFalse((self.run / actor / "workspace").exists())
            self.assertEqual(self.cli(actor, "read", "--all")["agents"], list(actors))
        binary_dir = self.base / "shared-bin"
        binary_dir.mkdir()
        binary = binary_dir / "pi-durable"
        binary.write_text('#!/bin/sh\npwd\n')
        binary.chmod(0o700)
        for actor in actors:
            env = dict(os.environ, PATH=str(binary_dir) + os.pathsep + os.environ["PATH"])
            result = subprocess.run([sys.executable, str(SCRIPT), "worker", str(self.run), actor],
                                    env=env, text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines()[-1], str(self.source))
        published = self.cli("alice", "publish", "--items", json.dumps([
            {"subject": "shared job", "detail": "one owner only"}]))
        item = published["items"][0]["id"]
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            results = list(pool.map(lambda actor: self.cli(actor, "claim", "--item", item), actors))
        self.assertEqual(sum(result["won"] for result in results), 1)
        refusal = self.invoke("context", str(self.run), "carol", "apply", "--id", item, expected=1)
        with sqlite3.connect(self.run / "context.sqlite") as db:
            before = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        observed = subprocess.run([sys.executable, str(ROOT / "scripts" / "delm_board.py"),
                                   str(self.run), "--once"], text=True, capture_output=True, timeout=5)
        self.assertEqual(observed.returncode, 0, observed.stderr)
        self.assertIn("carol", observed.stdout)
        self.assertIn("shared job", observed.stdout)
        with sqlite3.connect(self.run / "context.sqlite") as db:
            self.assertEqual(before, db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        self.assertEqual((self.source / "solution.txt").read_text(), "original\n")

    def test_local_auth_and_source_safety(self):
        url = json.loads((self.run / "endpoint.json").read_text())["url"]
        req = urllib.request.Request(url + "/wrong-token", data=b'{"action":"read"}',
                                     headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req, timeout=3)
        self.assertEqual(error.exception.code, 403)
        self.invoke("init", str(self.run), "--source", str(self.source), "--task", "no overwrite", expected=1)
        (self.source / ".env").write_text("fake-secret")
        self.invoke("init", str(self.base / "unsafe"), "--source", str(self.source), "--task", "reject", expected=1)
        self.assertFalse((self.base / "unsafe").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
