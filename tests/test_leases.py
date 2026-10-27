import concurrent.futures
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from delm_leases import LeaseError, operate, project


def append(db, actor, kind, payload):
    return db.execute("INSERT INTO events(actor,kind,payload) VALUES (?,?,?)",
                      (actor, kind, json.dumps(payload))).lastrowid


class LeasesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        self.path = self.base / "context.sqlite"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE events(sequence INTEGER PRIMARY KEY, actor, kind, payload)")
        self.db.execute("BEGIN IMMEDIATE")
        self.tasks = {actor: dict(id=actor, state="claimed", owner=actor, generation=1)
                      for actor in ("alice", "bob", "carol", "dave", "erin", "frank", "grace", "heidi")}

    def call(self, actor, op="acquire", **args):
        return operate(self.db, actor, op, dict(task=actor, generation=1, **args),
                       workspace=self.workspace, tasks=self.tasks, append=append, now=100)

    def test_alias_overlap_atomic_multipath_and_resources(self):
        (self.workspace / "source").mkdir()
        (self.workspace / "alias").symlink_to("source", target_is_directory=True)
        first = self.call("alice", paths=["source/new/child"], resources=["build:index"])["lease"]
        for args in (dict(paths=["alias/new"]), dict(paths=["free", "alias/new/child"]),
                     dict(resources=["build:index"])):
            with self.assertRaises(LeaseError):
                self.call("bob", **args)
        self.assertEqual(len(project(self.db, now=100)), 1)
        self.assertEqual(first["paths"], [str(self.workspace / "source/new/child")])
        self.call("bob", paths=["free"])
        self.assertEqual(len(project(self.db, now=100)), 2)

    def test_escape_invalid_inputs_and_retargeted_alias(self):
        (self.workspace / "outside").symlink_to(self.base, target_is_directory=True)
        for paths in (["../escape"], ["outside/missing/child"], ["."], ["\x00"]):
            with self.assertRaises(LeaseError):
                self.call("alice", paths=paths)
        for ttl in (0, -1, float("nan"), float("inf"), True, 86401):
            with self.assertRaises(LeaseError):
                self.call("alice", paths=["file"], ttl=ttl)
        (self.workspace / "one").mkdir()
        (self.workspace / "two").mkdir()
        alias = self.workspace / "alias"
        alias.symlink_to("one", target_is_directory=True)
        lease = self.call("alice", paths=["alias/file"])["lease"]
        alias.unlink()
        alias.symlink_to("two", target_is_directory=True)
        with self.assertRaisesRegex(LeaseError, "alias changed"):
            self.call("alice", "renew", lease_id=lease["lease_id"])

    def test_expiry_stale_writer_renew_release_and_task_handoff(self):
        first = self.call("alice", paths=["file"], ttl=10)["lease"]
        args = dict(task="alice", generation=1, lease_id=first["lease_id"])
        renewed = operate(self.db, "alice", "renew", dict(args, ttl=20),
                          workspace=self.workspace, tasks=self.tasks, append=append, now=105)["lease"]
        self.assertEqual(renewed["expires_at"], 125)
        self.tasks["alice"].update(owner="bob", generation=2)
        with self.assertRaises(LeaseError):
            self.call("alice", "renew", lease_id=first["lease_id"])
        handed = operate(self.db, "alice", "handoff", dict(args, generation=2, to="bob"),
                         workspace=self.workspace, tasks=self.tasks, append=append, now=110)["lease"]
        self.assertEqual((handed["owner"], handed["generation"]), ("bob", 2))
        with self.assertRaises(LeaseError):
            operate(self.db, "alice", "release", args, workspace=self.workspace,
                    tasks=self.tasks, append=append, now=111)
        operate(self.db, "bob", "release", dict(args, generation=2),
                workspace=self.workspace, tasks=self.tasks, append=append, now=111)
        acquired = self.call("carol", paths=["file"], ttl=1)["lease"]
        self.assertTrue(project(self.db, now=102)[-1]["expired"])
        with self.assertRaises(LeaseError):
            operate(self.db, "carol", "renew", dict(task="carol", generation=1, lease_id=acquired["lease_id"]),
                    workspace=self.workspace, tasks=self.tasks, append=append, now=102)
        self.assertEqual(self.tasks["carol"]["state"], "claimed", "expiry must not declare producer dead")

    def test_observer_readonly_absent_table_and_no_cleanup(self):
        self.db.commit()
        self.db.execute("PRAGMA query_only=ON")
        self.assertEqual(project(self.db), [])
        self.db.execute("PRAGMA query_only=OFF")
        self.db.execute("BEGIN IMMEDIATE")
        self.call("alice", paths=["file"], ttl=1)
        self.db.commit()
        self.db.execute("PRAGMA query_only=ON")
        before = self.db.total_changes
        self.assertTrue(project(self.db, now=102)[0]["expired"])
        self.assertEqual(self.db.total_changes, before)

    def test_four_and_eight_actor_conflict_race_has_one_winner(self):
        self.db.commit()
        for count in (4, 8):
            def compete(actor):
                db = sqlite3.connect(self.path, timeout=10)
                try:
                    db.execute("BEGIN IMMEDIATE")
                    try:
                        operate(db, actor, "acquire", dict(task=actor, generation=1, paths=[f"race-{count}"]),
                                workspace=self.workspace, tasks=self.tasks, append=append, now=100)
                    except LeaseError:
                        db.rollback()
                        return False
                    db.commit()
                    return True
                finally:
                    db.close()
            with concurrent.futures.ThreadPoolExecutor(count) as pool:
                self.assertEqual(sum(pool.map(compete, list(self.tasks)[:count])), 1)


if __name__ == "__main__":
    unittest.main()
