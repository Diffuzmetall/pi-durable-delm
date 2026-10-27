"""Delivery regression without a second board/storage owner."""
import sqlite3
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from delm_delivery import snapshot, ack, pending, DeliveryError


def projection(end):
    return dict(sequence=end, queue=[dict(id=str(i)) for i in range(70)],
                blockers=[dict(id="sticky")],
                events=[dict(sequence=i, kind="publication", payload=dict(id=str(i)))
                        for i in range(1, end + 1)],
                notes=[dict(id=str(i)) for i in range(1, end + 1)])


class DeliveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "context.sqlite"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(lambda: self.db.close())
        self.db.execute("BEGIN IMMEDIATE")

    def test_lost_response_reopen_immutable_replay_and_identity(self):
        first = snapshot(self.db, "carol", "lost", projection(70))
        self.db.commit()
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.db.execute("BEGIN IMMEDIATE")
        self.assertEqual(pending(self.db, "carol"), [first])
        self.assertEqual(snapshot(self.db, "carol", "lost", projection(80)), first)
        self.assertEqual(len(first["view"]["events"]), 70)
        self.assertTrue(first["full"])
        with self.assertRaises(DeliveryError):
            snapshot(self.db, "carol", "lost", projection(80), full=True)
        with self.assertRaises(DeliveryError):
            ack(self.db, "bob", first["receipt_id"])
        self.assertEqual(pending(self.db, "bob"), [])
        self.assertNotEqual(snapshot(self.db, "bob", "lost", projection(80))["receipt_id"],
                            first["receipt_id"])

    def test_delta_sticky_state_monotonic_ack_and_full_recovery(self):
        first = snapshot(self.db, "carol", "first", projection(70))
        ack(self.db, "carol", first["receipt_id"])
        delta = snapshot(self.db, "carol", "delta", projection(80))
        self.assertFalse(delta["full"])
        self.assertEqual(len(delta["view"]["events"]), 10)
        self.assertEqual(len(delta["view"]["notes"]), 10)
        self.assertEqual(len(delta["view"]["queue"]), 70)
        self.assertEqual(delta["view"]["blockers"], [dict(id="sticky")])
        ack(self.db, "carol", delta["receipt_id"])
        self.assertEqual(ack(self.db, "carol", first["receipt_id"])["acked_sequence"], 80)
        self.assertEqual(pending(self.db, "carol"), [])
        recovery = snapshot(self.db, "carol", "recovery", projection(80), full=True)
        self.assertEqual(len(recovery["view"]["events"]), 80)
        with self.assertRaises(DeliveryError):
            snapshot(self.db, "carol", "stale", projection(79))

    def test_transaction_rollback_and_explicit_caller_boundary(self):
        snapshot(self.db, "carol", "lost", projection(70))
        self.db.rollback()
        with self.assertRaises(DeliveryError):
            pending(self.db, "carol")
        self.db.execute("BEGIN IMMEDIATE")
        self.assertEqual(pending(self.db, "carol"), [])
        self.assertEqual(snapshot(self.db, "carol", "lost", projection(80))["to_sequence"], 80)


if __name__ == "__main__":
    unittest.main()
