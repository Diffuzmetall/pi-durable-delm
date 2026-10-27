"""Supported 2/4/8 rosters are deterministic participants, never model launches."""
import concurrent.futures
import contextlib
import io
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import delm_local as local
from delm_domain import DomainError


class ScaleTest(unittest.TestCase):
    def test_roster_bindings_races_delivery_reopen_and_rejection(self):
        for n in (2, 4, 8):
            with self.subTest(n=n), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp); shared = base / 'shared'; shared.mkdir(); run = base / 'run'
                with contextlib.redirect_stdout(io.StringIO()): local.initialize(run, None, 'fixture only', n, shared)
                actors = local.ROSTER[:n]; board = local.board(run)
                self.assertEqual(board.actors, actors)
                for actor in actors:
                    start = (run / actor / 'START.md').read_text()
                    adapter = (run / actor / 'delm-adapter.js').read_text()
                    self.assertIn(f'# DeLM peer {actor}', start)
                    self.assertIn(f'actor: "{actor}"', adapter)
                    self.assertIn(str(run), adapter)
                task = board.domain('alice', dict(op='create', request_id='create', subject='race', detail='single winner'))['task']
                def claim(actor):
                    try:
                        return board.domain(actor, dict(op='claim', request_id='claim', item=task['id'], expected_revision=task['revision']))
                    except DomainError:
                        return None
                with concurrent.futures.ThreadPoolExecutor(n) as pool: results = list(pool.map(claim, actors))
                self.assertEqual(sum(r is not None for r in results), 1)
                receipts = {a: board.domain(a, dict(op='snapshot', request_id='same-request')) for a in actors}
                self.assertEqual(len({r['receipt_id'] for r in receipts.values()}), n)
                reopened = local.board(run)
                for actor in actors:
                    self.assertEqual(reopened.domain(actor, dict(op='snapshot', request_id='same-request')), receipts[actor])
                    reopened.domain(actor, dict(op='ack', request_id='ack', receipt_id=receipts[actor]['receipt_id']))
                with self.assertRaises(ValueError): reopened.domain('outsider', dict(op='projection'))
                with self.assertRaises(ValueError): local.configure_client(run, 'outsider')
                if n < 8:
                    with self.assertRaises(ValueError): local.workspace_path(run, local.ROSTER[n])

    def test_future_worker_profile_and_offline_help(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); shared = base / 'shared'; shared.mkdir(); run = base / 'run'
            with contextlib.redirect_stdout(io.StringIO()): local.initialize(run, None, 'fixture only', 4, shared)
            # No endpoint/server: help must not need authentication or consume any cursor.
            for arguments in (['--help'], ['domain', '--help']):
                result = subprocess.run([str(run / 'alice/bin/context'), *arguments], text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                for token in ('domain', 'snapshot', 'receipt_id', 'ack', 'pending', 'expected_revision', 'generation', 'RESOLUTION', 'lease-acquire', 'ADVISORY'):
                    self.assertIn(token, result.stdout)
                for action in local.client.ACTIONS:
                    self.assertIn(action, result.stdout)
            profile = (run / 'WORKER.md').read_text()
            self.assertEqual(profile, (ROOT / 'prompts/delm-worker.md').read_text())
            self.assertTrue(profile.startswith('# DeLM worker — delm-remaining-v2'))
            for token in ('context domain', 'receipt_id', 'snapshot', 'pending', 'expected_revision', 'generation', 'CORRECTION', 'RESOLUTION', 'lease-acquire', 'advisory', 'No Agent Mail', '--no-mcp'):
                self.assertIn(token, profile)
            for actor in local.ACTORS:
                self.assertIn('Profile: delm-remaining-v2', (run / actor / 'START.md').read_text())
                self.assertIn('context --help', (run / actor / 'START.md').read_text())
            self.assertFalse((run / 'context.sqlite').exists())

    def test_invalid_counts_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); shared = base / 'shared'; shared.mkdir()
            for n in (0, 3, 9, True):
                with self.assertRaises(ValueError): local.initialize(base / 'run', None, 'no mutation', n, shared)
                self.assertFalse((base / 'run').exists())


if __name__ == '__main__': unittest.main()
