"""Fenced domain operations on real local board transactions and HTTP/CLI."""
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import delm_local as local
from delm_domain import DomainError, project_events


class DomainTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.board = local.LocalBoard(self.base / 'context.sqlite', ('alice', 'bob', 'carol', 'dave'))
        self.counter = 0

    def call(self, actor, op, **args):
        self.counter += 1
        return self.board.domain(actor, dict(op=op, request_id=f'r{self.counter}', **args))

    def create(self, **args):
        return self.call('alice', 'create', subject='job', detail='real useful work', **args)['task']

    def claim(self, actor, task):
        return self.call(actor, 'claim', item=task['id'], expected_revision=task['revision'])['task']

    def owned(self, actor, op, task, **args):
        return self.call(actor, op, item=task['id'], expected_revision=task['revision'], generation=task['generation'], **args)

    def test_race_replay_and_generation_fences(self):
        t = self.create()
        def claim(actor):
            try:
                return self.board.domain(actor, dict(op='claim', item=t['id'], expected_revision=t['revision'], request_id='race'))
            except DomainError:
                return None
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(claim, ('alice', 'bob')))
        self.assertEqual(sum(r is not None for r in results), 1)
        winning = next(r for r in results if r)['task']; actor = winning['owner']
        self.assertEqual(self.board.domain(actor, dict(op='claim', item=t['id'], expected_revision=t['revision'], request_id='race'))['task'], winning)
        with self.assertRaises(DomainError):
            self.board.domain(actor, dict(op='release', request_id='race'))
        released = self.owned(actor, 'release', winning, summary='checkpoint')['task']
        reclaimed = self.claim(actor, released)
        with self.assertRaises(DomainError):
            self.owned(actor, 'complete', winning, summary='stale result')
        done = self.owned(actor, 'complete', reclaimed, summary='verified')['task']
        self.assertEqual(done['state'], 'done')
        reopened = local.LocalBoard(self.base / 'context.sqlite', self.board.actors)
        self.assertEqual(reopened.domain(actor, dict(op='projection'))['queue'][0]['state'], 'done')

    def test_dependency_cycle_parent_mapping_and_partial_not_done(self):
        parent = self.create(criteria=['one', 'two'])
        parent = self.claim('alice', parent)
        with self.assertRaises(DomainError):
            self.owned('alice', 'split', parent, children=[dict(subject='one', detail='x', mapping=['one'])])
        split = self.owned('alice', 'split', parent, children=[dict(subject='output', detail='usable', mapping=['one', 'two'])])
        parent, child = split['task'], split['children'][0]
        with self.assertRaises(DomainError):
            self.owned('alice', 'complete', parent, summary='partial')
        child = self.claim('bob', child)
        self.owned('bob', 'complete', child, summary='output usable')
        view = self.call('alice', 'projection')
        self.assertEqual(next(t for t in view['queue'] if t['id'] == parent['id'])['state'], 'claimed')
        self.owned('alice', 'complete', parent, summary='all criteria verified')
        a = self.create(); b = self.create(deps=[a['id']])
        with self.assertRaises(DomainError): self.claim('bob', b)
        a = self.claim('alice', a)
        with self.assertRaises(DomainError): self.owned('alice', 'update', a, changes={'deps': [b['id']]})
        with self.assertRaises(DomainError): self.create(deps=['missing'])

    def test_split_rejects_child_completion_cycle_atomically(self):
        parent = self.claim('alice', self.create(criteria=['usable result']))
        before = self.call('alice', 'projection')
        request = dict(op='split', request_id='split-cycle-retry', item=parent['id'],
                       expected_revision=parent['revision'], generation=parent['generation'],
                       children=[dict(subject='valid sibling', detail='must not leak', mapping=['usable result']),
                                 dict(subject='cyclic output', detail='needs parent', deps=[parent['id']],
                                      criteria=['child'], mapping=['usable result'])])
        with self.assertRaisesRegex(DomainError, 'cycle'):
            self.board.domain('alice', request)
        self.assertEqual(self.call('alice', 'projection'), before)
        # A rejected command must not reserve its replay ID or leave partial children.
        request['children'] = [dict(subject='usable output', detail='no completion cycle',
                                    criteria=['child'], mapping=['usable result'])]
        split = self.board.domain('alice', request)
        parent, child = split['task'], split['children'][0]
        self.assertEqual(parent['criteria'], ['usable result'])
        self.assertEqual(parent['mapping'], {child['id']: ['usable result']})
        self.assertEqual(child['parent'], parent['id'])
        self.assertEqual(len(self.call('alice', 'projection')['queue']), 2)
        child = self.claim('bob', child)
        self.owned('bob', 'complete', child, summary='usable result verified')
        self.owned('alice', 'complete', parent, summary='mapped result delivered')

    def test_split_rejects_transitive_ancestor_completion_cycles(self):
        parent = self.claim('alice', self.create(criteria=['usable result']))
        bridge = self.create(deps=[parent['id']])
        before = self.call('alice', 'projection')
        with self.assertRaisesRegex(DomainError, 'cycle'):
            self.owned('alice', 'split', parent, children=[dict(
                subject='transitive output', detail='indirect parent prerequisite',
                deps=[bridge['id']], criteria=['child'], mapping=['usable result'])])
        self.assertEqual(self.call('alice', 'projection'), before)
        split = self.owned('alice', 'split', parent, children=[dict(
            subject='valid child', detail='can split further', criteria=['child'], mapping=['usable result'])])
        child = self.claim('bob', split['children'][0])
        before = self.call('alice', 'projection')
        with self.assertRaisesRegex(DomainError, 'cycle'):
            self.owned('bob', 'split', child, children=[dict(
                subject='grandchild', detail='needs ancestor', deps=[parent['id']], mapping=['child'])])
        self.assertEqual(self.call('alice', 'projection'), before)
        self.owned('bob', 'complete', child, summary='valid child remains usable')
        self.owned('alice', 'complete', split['task'], summary='no leaked grandchild/output')

    def test_update_after_split_rejects_completion_cycles_atomically(self):
        parent = self.claim('alice', self.create(criteria=['usable result']))
        split = self.owned('alice', 'split', parent, children=[dict(
            subject='child', detail='valid nested split', criteria=['child'], mapping=['usable result'])])
        parent, child = split['task'], self.claim('bob', split['children'][0])
        nested = self.owned('bob', 'split', child, children=[dict(
            subject='grandchild', detail='independent output', mapping=['child'])])
        child, grandchild = nested['task'], self.claim('carol', nested['children'][0])
        bridge = self.create(deps=[parent['id']])
        for owner, task, dependency in [('bob', child, parent['id']),
                                         ('carol', grandchild, parent['id']),
                                         ('carol', grandchild, bridge['id'])]:
            with self.subTest(owner=owner, task=task['id'], dependency=dependency):
                before = self.call('alice', 'projection')
                with self.assertRaisesRegex(DomainError, 'cycle'):
                    self.owned(owner, 'update', task, changes={'deps': [dependency]})
                self.assertEqual(self.call('alice', 'projection'), before)
        # Reusing a forward prerequisite is acyclic, unlike a child->ancestor edge.
        parent = self.owned('alice', 'update', parent, changes={'deps': [grandchild['id']]})['task']
        self.owned('carol', 'complete', grandchild, summary='nested output usable')
        self.owned('bob', 'complete', child, summary='nested criterion met')
        self.owned('alice', 'complete', parent, summary='parent mapping preserved')

    def test_handoff_legacy_and_single_claim(self):
        a = self.create(); a = self.claim('alice', a)
        b = self.create()
        with self.assertRaises(DomainError): self.claim('alice', b)
        transferred = self.owned('alice', 'handoff', a, to='bob', summary='checkpoint')['task']
        self.assertEqual(transferred['owner'], 'bob')
        with self.assertRaises(DomainError): self.owned('alice', 'complete', a, summary='no')
        with self.assertRaises(DomainError): self.board.claim('carol', transferred['id'])
        with self.assertRaises(DomainError): self.board.reserve('carol', transferred['subject'], 'legacy bypass')
        self.board.publish('carol', [dict(subject='legacy', detail='keep old records')])
        v = self.call('carol', 'projection')
        legacy = next(t for t in v['queue'] if t['subject'] == 'legacy')
        self.assertTrue(self.board.claim('carol', legacy['id'])['won'])
        self.board.done('carol', legacy['id'], 'legacy done')
        self.assertEqual(next(t for t in self.call('alice', 'projection')['queue'] if t['id'] == legacy['id'])['state'], 'done')

    def test_migrated_legacy_task_cannot_bypass_fences(self):
        identity = self.board.reserve('alice', 'migrate old task', 'legacy history')['item']
        task = next(t for t in self.call('alice', 'projection')['queue'] if t['id'] == identity)
        released = self.owned('alice', 'release', task, summary='v2 checkpoint')['task']
        with self.assertRaises(DomainError): self.board.reserve('bob', released['subject'], 'bypass')
        task = self.claim('bob', released)
        with self.assertRaises(DomainError): self.board.done('bob', identity, 'bypass')
        self.owned('bob', 'complete', task, summary='fenced complete')

    def test_snapshot_replay_and_observer_nonconsumption(self):
        a = self.create()
        receipt = self.call('bob', 'snapshot')
        self.create()
        with self.board.connect() as db:
            before = self.board.last_sequence(db)
            self.board.projection(db)
            self.assertEqual(before, self.board.last_sequence(db))
        self.assertEqual(self.call('bob', 'pending')['receipts'][0]['receipt_id'], receipt['receipt_id'])
        with self.assertRaises(ValueError): self.call('carol', 'ack', receipt_id=receipt['receipt_id'])
        self.call('bob', 'ack', receipt_id=receipt['receipt_id'])
        delta = self.call('bob', 'snapshot')
        self.assertFalse(delta['full'])
        self.assertGreater(len(delta['view']['queue']), 1)

    def test_structured_publications_and_sticky_fail(self):
        output = self.create(); output = self.claim('alice', output)
        output = self.owned('alice', 'complete', output, summary='usable')['task']
        consumer = self.create(deps=[output['id']])
        self.call('alice', 'publish', type='FACT', text='ready', output=output['id'], readiness=True)
        failure = self.call('bob', 'publish', type='FAIL', text='output invalid', task=output['id'])['publication']
        for _ in range(70): self.call('bob', 'publish', type='FACT', text='unrelated progress')
        view = self.call('carol', 'projection')
        projected = next(t for t in view['queue'] if t['id'] == consumer['id'])
        self.assertFalse(projected['readiness'])
        self.assertEqual(projected['blockers'][0]['id'], failure['id'])
        with self.assertRaises(DomainError): self.claim('carol', consumer)
        with self.assertRaises(DomainError): self.call('carol', 'publish', type='RESOLUTION', text='unauthorized', resolves=[failure['id']])
        with self.assertRaises(DomainError): self.call('alice', 'publish', type='FACT', text='not readiness', output=consumer['id'], readiness=True)
        self.call('alice', 'publish', type='CORRECTION', text='owner fixed root cause', resolves=[failure['id']], task=output['id'])
        self.assertFalse(self.call('carol', 'projection')['blockers'])
        self.claim('carol', consumer)
        with self.assertRaises(DomainError): self.call('bob', 'publish', type='FAIL', text='bad link', related=['missing'])
        with self.assertRaises(DomainError): self.call('bob', 'publish', type='FACT', text='implicit resolve', resolves=[failure['id']])

    def test_lifecycle_idle_ended_fences_salvage_and_human_gate(self):
        task = self.claim('alice', self.create())
        idle = self.call('alice', 'lifecycle', state='idle', reason='turn ended not producer', expected_generation=0)
        current = next(t for t in self.call('bob', 'projection')['queue'] if t['id'] == task['id'])
        self.assertEqual(current['state'], 'claimed')
        with self.assertRaises(DomainError):
            self.call('bob', 'reclaim', item=task['id'], expected_revision=current['revision'], generation=current['generation'], producer_generation=1, acknowledge_external_writes=True, summary='TTL not proof')
        ended = self.call('alice', 'lifecycle', state='ended', reason='explicit execution ended; checkpoints preserved', expected_generation=1)
        blocked = ended['tasks'][0]
        self.assertEqual(blocked['state'], 'blocked')
        # Reopen/session noise must not erase explicit lifecycle epoch fencing.
        with self.board.connect() as db:
            self.board.append(db, 'alice', 'session', dict(actor='alice', state='starting'))
        self.assertEqual(next(s for s in self.call('bob', 'projection')['sessions'] if s['actor'] == 'alice')['generation'], 2)
        with self.assertRaises(DomainError): self.owned('alice', 'complete', task, summary='stale background writer')
        with self.assertRaises(DomainError): self.board.reserve('alice', 'another legacy', 'must not bypass blocked')
        with self.assertRaises(DomainError): self.call('alice', 'lifecycle', state='active', reason='stale', expected_generation=1)
        args = dict(item=blocked['id'], expected_revision=blocked['revision'], generation=blocked['generation'], producer_generation=2, summary='inspect checkpoints; no overwrite of external work')
        with self.assertRaises(DomainError): self.call('bob', 'reclaim', **args)
        salvaged = self.call('bob', 'reclaim', **args, acknowledge_external_writes=True)['task']
        self.assertEqual(salvaged['owner'], 'bob')
        with self.assertRaises(DomainError): self.owned('alice', 'complete', blocked, summary='old epoch')
        gate = self.call('bob', 'lifecycle', state='blocked', reason='human permission required; retain owned checkpoint', expected_generation=0)
        gated = gate['tasks'][0]
        self.assertEqual(gated['blocked_reason'], 'human permission required; retain owned checkpoint')
        with self.assertRaises(DomainError): self.owned('bob', 'complete', salvaged, summary='false done')
        self.call('bob', 'lifecycle', state='active', reason='human gate satisfied externally', expected_generation=1)
        resumed = self.owned('bob', 'resume', gated, summary='reconciled exact checkpoint')['task']
        self.owned('bob', 'complete', resumed, summary='verified completed')

    def test_real_authenticated_http_and_cli(self):
        run = self.base / 'run'; workspace = self.base / 'workspace'; workspace.mkdir()
        local.initialize(run, None, 'test only', 4, workspace)
        board = local.board(run)
        # Credential fixtures are never logged; exercise actual token authentication.
        config = json.loads((run / 'config.json').read_text())
        identities = {token: actor for actor, token in config['actors'].items()}
        with ThreadingHTTPServer(('127.0.0.1', 0), local.local_handler(board, identities)) as server:
            thread = threading.Thread(target=server.serve_forever); thread.start()
            try:
                (run / 'endpoint.json').write_text(json.dumps({'url': f'http://127.0.0.1:{server.server_port}'}))
                payload = dict(op='create', request_id='http-create', subject='via CLI', detail='real transport')
                command = [sys.executable, str(ROOT / 'scripts/delm_local.py'), 'context', str(run), 'alice', 'domain', json.dumps(payload)]
                first = subprocess.run(command, text=True, capture_output=True, timeout=10)
                self.assertEqual(first.returncode, 0, first.stderr)
                second = subprocess.run(command, text=True, capture_output=True, timeout=10)
                self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))
                self.assertEqual(len(board.domain('bob', {'op': 'projection'})['queue']), 1)
            finally:
                server.shutdown(); thread.join()


if __name__ == '__main__': unittest.main()
