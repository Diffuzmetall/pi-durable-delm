"""Read-only observer conformance against canonical event projection, not a UI reducer."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from delm_board import BoardView, agent_line, load_board, snapshot
from delm_domain import project_events


class ObserverV2Test(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.run = Path(temporary.name)
        (self.run / 'config.json').write_text(json.dumps({'actors': {'alice': 'secret', 'bob': 'other'}}))
        with closing(sqlite3.connect(self.run / 'context.sqlite')) as db, db:
            db.execute('CREATE TABLE events(sequence INTEGER PRIMARY KEY, time_ns INTEGER, actor TEXT, kind TEXT, payload TEXT)')
            # A pre-existing opaque receipt/cursor must be untouched by observation.
            db.execute('CREATE TABLE observer_preservation(value TEXT)')
            db.execute("INSERT INTO observer_preservation VALUES('unacked receipt/cursor')")
        self.rows = []

    def emit(self, kind, payload, actor='alice'):
        sequence = len(self.rows) + 1
        with closing(sqlite3.connect(self.run / 'context.sqlite')) as db, db:
            db.execute('INSERT INTO events VALUES(?,?,?,?,?)', (sequence, sequence, actor, kind, json.dumps(payload)))
        self.rows.append(dict(sequence=sequence, actor=actor, kind=kind, payload=payload))

    def task(self, item, state='open', **fields):
        task = dict(id=item, subject='Output ' + item, detail='full detail', state=state,
                    owner='alice' if state == 'claimed' else None, generation=1, revision=len(self.rows) + 1,
                    deps=[], criteria=['usable'], parent=None, outputs=[], mapping={}, handoff='')
        task.update(fields)
        self.emit('task', {'task': task})

    def test_canonical_transitions_links_blockers_and_read_only(self):
        self.emit('item', {'id': 'legacy', 'subject': 'legacy output'})
        self.emit('claim', {'item': 'legacy'})
        self.task('legacy', 'open', generation=2, handoff='released after useful partial')
        self.task('child', 'done', parent='legacy', summary='shared file ready')
        self.task('consumer', 'blocked', deps=['child'], outputs=[], blocked_reason='explicit gate')
        self.emit('lifecycle', dict(actor='alice', state='ended', reason='explicit operator declaration', generation=3))
        self.emit('publication', dict(id='fail', type='FAIL', text='explicit linked blocker', task='consumer',
                                    related=['legacy'], output=None, readiness=False, limitations='check needed', resolves=[]))
        for number in range(70):
            self.emit('note', dict(id=f'unrelated-{number}', type='FACT', text='unrelated history', scope='', basis='fixture'))
        before = (self.run / 'context.sqlite').read_bytes()
        data = load_board(self.run)
        canonical = project_events(self.rows, ('alice', 'bob'))
        self.assertEqual({task['id']: task['state'] for task in data['tasks']},
                         {task['id']: task['state'] for task in canonical['queue']})
        self.assertEqual(data['blockers'], canonical['blockers'])
        self.assertEqual(len(data['notes']), 71, 'full note history, not recent-window truth')
        legacy = next(task for task in data['tasks'] if task['id'] == 'legacy')
        self.assertEqual(legacy['owner'], '-')
        self.assertEqual(legacy['generation'], 2)
        document = BoardView().document(legacy, data)
        self.assertIn('explicit linked blocker', document)
        self.assertIn('released after useful partial', document)
        self.assertIn('TASK EVENT HISTORY', document)
        self.assertIn('"generation": 2', document)
        self.assertIn('ENDED gen 3', agent_line(data, 'alice'))
        consumer = next(task for task in data['tasks'] if task['id'] == 'consumer')
        detail = BoardView().document(consumer, data)
        self.assertIn('explicit gate', detail)
        self.assertIn('"deps"', detail)
        self.assertIn('child', detail)
        text = '\n'.join(snapshot(self.run))
        self.assertIn('UNRESOLVED BLOCKERS (all)', text)
        self.assertIn('explicit linked blocker', text, 'old sticky failure remains visible outside ten-event preview')
        self.assertNotIn('secret', text)
        self.assertEqual(before, (self.run / 'context.sqlite').read_bytes())
        with closing(sqlite3.connect(self.run / 'context.sqlite')) as db:
            self.assertEqual(db.execute('SELECT value FROM observer_preservation').fetchone()[0], 'unacked receipt/cursor')

    def test_available_work_wait_is_not_reported_as_zero_dependencies_ready(self):
        data = dict(tasks=[], waits={'bob': [{'mode': 'work', 'items': [], 'reason': 'available'}]},
                    sessions=[], statuses={})
        line = agent_line(data, 'bob')
        self.assertIn('WAIT → available work', line)
        self.assertNotIn('ready 0/0', line)
        self.assertNotIn('wake pending', line)

    def test_completed_team_keeps_results_visible_and_resolution_history(self):
        self.task('result', 'done', summary='verified final artifact')
        self.emit('publication', dict(id='failure', type='FAIL', text='old failure', task='result', related=[],
                                    output=None, readiness=False, limitations='', resolves=[]))
        self.emit('publication', dict(id='resolution', type='RESOLUTION', text='resolved with evidence', task='result',
                                    related=[], output=None, readiness=False, limitations='', resolves=['failure']))
        data = load_board(self.run)
        self.assertFalse(data['blockers'])
        rows = BoardView().rows(data)
        self.assertEqual([task['id'] for task in rows], ['result'])
        self.assertIn('verified final artifact', BoardView().document(rows[0], data))
        self.assertIn('old failure', BoardView().document(rows[0], data))
        self.assertIn('resolved with evidence', BoardView().document(rows[0], data))
        notes = BoardView()
        notes.tab, notes.note_filter = 'notes', 'RESOLUTION'
        self.assertEqual(len(notes.rows(data)), 1)


if __name__ == '__main__':
    unittest.main()
