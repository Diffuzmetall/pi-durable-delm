import curses
import fcntl
import json
import os
import pty
import re
import select
import signal
import sqlite3
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from contextlib import closing
from importlib import import_module
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from unittest.mock import patch

board_module: Any = import_module('delm_board')
local_module: Any = import_module('delm_local')
BoardView = board_module.BoardView
LogView = board_module.LogView
agent_line = board_module.agent_line
clean = board_module.clean
event_time = board_module.event_time
interactive = board_module.interactive
load_board = board_module.load_board
snapshot = board_module.snapshot
task_line = board_module.task_line
board = local_module.board


class Screen:
    def __init__(self, width=160, keys=()):
        self.width, self.lines = width, {}
        self.keys, self.frames = iter([*keys, 'q']), []

    def getmaxyx(self): return 60, self.width
    def addnstr(self, y, x, text, count, style): self.lines[y] = text[:count]
    def get_wch(self): return next(self.keys)
    def timeout(self, value): pass
    def keypad(self, value): pass
    def erase(self): self.lines.clear()
    def refresh(self): self.frames.append(dict(self.lines))


class BoardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run_dir = Path(self.temp.name)
        (self.run_dir / 'config.json').write_text(json.dumps({'actors': {'alice': 'PRIVATE-TOKEN', 'dave': 'OTHER-TOKEN'}}))
        with closing(sqlite3.connect(self.run_dir / 'context.sqlite')) as db, db:
            db.execute('CREATE TABLE events(sequence INTEGER PRIMARY KEY, time_ns INTEGER, actor TEXT, kind TEXT, payload TEXT)')
        self.emit('alice', 'item', {'id': 'active-id', 'subject': 'U4 active first', 'detail': 'detail ' * 400 + 'DETAIL_TAIL'})
        self.emit('alice', 'claim', {'item': 'active-id'})
        for i in range(20):
            self.emit('alice', 'item', {'id': str(i), 'subject': f'old completed {i}'})
            self.emit('alice', 'done', {'item': str(i), 'summary': 'verified result', 'publication_id': 'pub-id'})
        self.emit('alice', 'note', {'id': 'fact-id', 'type': 'FACT', 'text': 'U4 scope evidence\n' + 'full note ' * 60 + 'FACT_TAIL', 'scope': 'scope-path', 'basis': 'test'})
        self.emit('dave', 'status', {'text': 'done: old prep'})
        native = self.run_dir / 'native.sqlite'
        with closing(sqlite3.connect(native)) as db, db:
            db.execute('CREATE TABLE tasks(kind TEXT, status TEXT, record TEXT)')
            db.execute('INSERT INTO tasks VALUES(?,?,?)', (json.dumps('delm.wait'), 'sleeping', json.dumps({'id': 267, 'input': {'id': 'wait-id'}})))
            db.execute('CREATE TABLE documents(id INTEGER, kind TEXT, retired_at INTEGER)')
            db.execute('CREATE TABLE document_revisions(document_id INTEGER, seq INTEGER, kind TEXT, version INTEGER, content TEXT)')
            db.execute('INSERT INTO documents VALUES(1,?,NULL)', (json.dumps('delm.waits'),))
            doc = {'waits': {'wait-id': {'state': 'waiting', 'items': ['active-id', '0'], 'reason': 'Need both tasks', 'taskId': 267}}}
            db.execute('INSERT INTO document_revisions VALUES(1,1,\'base\',1,?)', (json.dumps(doc),))
        (self.run_dir / 'dcg-reopen-sessions.json').write_text(json.dumps({'dave': {'session': str(native)}}))

    def emit(self, actor, kind, payload):
        with closing(sqlite3.connect(self.run_dir / 'context.sqlite')) as db, db:
            db.execute('INSERT INTO events(time_ns,actor,kind,payload) VALUES(?,?,?,?)', (time.monotonic_ns(), actor, kind, json.dumps(payload)))

    def test_active_first_full_results_wait_and_read_only(self):
        before = (self.run_dir / 'context.sqlite').read_bytes()
        data = load_board(self.run_dir)
        self.assertEqual(data['tasks'][0]['id'], 'active-id')
        self.assertEqual(data['tasks'][1]['summary'], 'verified result')
        self.assertIn('WAIT → ISOL-1 [ALICE] | ready 1/2', agent_line(data, 'dave'))
        self.assertEqual(data['tasks'][0]['waited_by'], ['dave'])
        self.assertIn('Waited by: dave', BoardView().document(data['tasks'][0], data))
        self.assertIn('reported: done: old prep', agent_line(data, 'dave'))
        text = '\n'.join(snapshot(self.run_dir))
        self.assertIn('U4 active first', text)
        self.assertIn('old completed 19', text)
        self.assertNotIn('PRIVATE-TOKEN', text)
        self.assertEqual(before, (self.run_dir / 'context.sqlite').read_bytes())

    def native14_manifest(self):
        actors = {}
        for actor in ('alice', 'dave'):
            actors[actor] = {'socket': f'/private/{actor}/control.sock', 'identity': {
                'protocol': 'delm.native14.control.v1', 'run': str(self.run_dir),
                'workspace': str(self.run_dir), 'actor': actor, 'conversationId': 1,
            }}
        (self.run_dir / 'launch.json').write_text(json.dumps({
            'schema': 2, 'run': str(self.run_dir), 'workspace': str(self.run_dir),
            'native': {'protocol': 'delm.native14.control.v1'}, 'actors': actors,
        }))

    def native14_status(self, argv, **kwargs):
        request = json.loads(kwargs['input'])
        self.assertEqual(request['method'], 'status')
        self.assertEqual(argv[0], 'node')
        self.assertEqual(Path(argv[1]).name, 'NativeControl.mjs')
        self.assertLessEqual(kwargs['timeout'], 2)
        waits = [] if request['identity']['actor'] == 'alice' else [
            {'state': 'waiting', 'items': ['active-id', '0'], 'taskId': 267},
            {'state': 'sent', 'items': ['19'], 'taskId': 268},
        ]
        return subprocess.CompletedProcess(argv, 0, json.dumps({
            'delm_control': 14, 'result': {'waits': waits},
        }), '')

    def test_native14_ledger_waits_without_legacy_manifest_or_native_sql(self):
        self.native14_manifest()
        (self.run_dir / 'dcg-reopen-sessions.json').unlink()
        paths = [self.run_dir / name for name in ('launch.json', 'context.sqlite', 'native.sqlite')]
        before = [p.read_bytes() for p in paths]
        with patch('delm_board.subprocess.run', side_effect=self.native14_status), \
             patch('delm_board.native_waits', side_effect=AssertionError('Native SQL is not the new protocol')):
            data = load_board(self.run_dir)
        self.assertIn('WAIT → ISOL-1 [ALICE] | ready 1/2', agent_line(data, 'dave'))
        self.assertEqual(data['tasks'][0]['waited_by'], ['dave'])
        self.assertEqual(len(data['waits']['dave']), 1)
        self.assertEqual(before, [p.read_bytes() for p in paths])

    def test_sdk_manifest_takes_precedence_over_legacy_native_metadata(self):
        self.native14_manifest()
        (self.run_dir / 'sdk-launch.json').write_text('{}')
        observed = {'waits': {'alice': [], 'dave': [
            {'state': 'waiting', 'items': ['active-id', '0']}]},
            'activity': {'alice': 'running', 'dave': 'idle'}}
        client = self.run_dir / 'operator-client.json'
        with patch('delm_board.observe_sdk', return_value=observed) as observer, \
             patch('delm_board.native14_waits', side_effect=AssertionError('No SDK to Native fallback')):
            data = load_board(self.run_dir, host_client=client)
        observer.assert_called_once_with(self.run_dir, data['actors'], 'isolated', client)
        self.assertIn('WAIT → ISOL-1 [ALICE] | ready 1/2', agent_line(data, 'dave'))
        self.assertIn('CLAIM ISOL-1', agent_line(data, 'alice'))
        self.assertIn('RUNNING', agent_line(data, 'alice'))
        self.assertEqual(data['tasks'][0]['waited_by'], ['dave'])

    def test_sdk_without_operator_client_is_unknown_never_no_wait(self):
        (self.run_dir / 'sdk-launch.json').write_text('{}')
        with patch('delm_board.native14_waits', side_effect=AssertionError('No legacy fallback')):
            data = load_board(self.run_dir)
        self.assertIn('WAIT UNKNOWN', agent_line(data, 'alice'))
        self.assertIn('CLAIM ISOL-1', agent_line(data, 'alice'))
        self.assertIn('WAIT UNKNOWN', agent_line(data, 'dave'))
        self.assertEqual(data['tasks'][0]['waited_by'], [])

    def test_failed_wait_is_visible_and_claim_preserved(self):
        data = load_board(self.run_dir)
        data['waits']['alice'] = [{'state': 'failed', 'items': ['active-id']}]
        self.assertIn('WAIT FAILED', agent_line(data, 'alice'))
        self.assertIn('CLAIM ISOL-1', agent_line(data, 'alice'))

    def test_mixed_work_and_named_waits_keep_named_dependencies(self):
        data = load_board(self.run_dir)
        data['waits']['dave'].append({'state': 'waiting', 'mode': 'work', 'items': []})
        text = agent_line(data, 'dave')
        self.assertIn('available work', text)
        self.assertIn('ISOL-1 [ALICE]', text)
        self.assertIn('ready 1/2', text)

    def test_native14_failed_wait_is_not_hidden_as_a_claim(self):
        self.native14_manifest()
        response = {'delm_control': 14, 'result': {'waits': [
            {'state': 'failed', 'items': ['active-id'], 'taskId': 267}]}}
        with patch('delm_board.subprocess.run', return_value=
                   subprocess.CompletedProcess([], 0, json.dumps(response), '')):
            data = load_board(self.run_dir)
        self.assertIn('WAIT FAILED', agent_line(data, 'alice'))
        self.assertIn('CLAIM ISOL-1', agent_line(data, 'alice'))

    def test_malformed_native14_envelopes_are_unknown_not_crashes(self):
        self.native14_manifest()
        for frame in ([], None, {'delm_control': 14, 'result': None},
                      {'delm_control': 14, 'result': []}):
            with self.subTest(frame=frame), patch('delm_board.subprocess.run', return_value=
                    subprocess.CompletedProcess([], 0, json.dumps(frame), '')):
                data = load_board(self.run_dir)
            self.assertIn('WAIT UNKNOWN', agent_line(data, 'dave'))

    def test_native14_failure_is_unknown_not_legacy_or_no_claim(self):
        self.native14_manifest()
        def unavailable(argv, **kwargs):
            if json.loads(kwargs['input'])['identity']['actor'] == 'dave':
                raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
            return self.native14_status(argv, **kwargs)
        with patch('delm_board.subprocess.run', side_effect=unavailable), \
             patch('delm_board.native_waits', side_effect=AssertionError('No legacy fallback')):
            data = load_board(self.run_dir)
        self.assertIn('WAIT UNKNOWN', agent_line(data, 'dave'))
        self.assertIn('CLAIM ISOL-1', agent_line(data, 'alice'))
        self.assertEqual(data['tasks'][0]['waited_by'], [])

    def test_native14_work_wait_and_invalid_response(self):
        self.native14_manifest()
        for result in ({'waits': [{'state': 'waiting', 'items': [], 'mode': 'work'}]},
                       {'waits': None}, {'waits': [{'state': 'waiting', 'items': 'bad'}]},
                       {'waits': [{'state': 'future-state', 'items': []}]}):
            with self.subTest(result=result), patch('delm_board.subprocess.run', return_value=
                    subprocess.CompletedProcess([], 0, json.dumps({'delm_control': 14, 'result': result}), '')):
                data = load_board(self.run_dir)
            expected = 'WAIT → available work' if result.get('waits') == [{'state': 'waiting', 'items': [], 'mode': 'work'}] else 'WAIT UNKNOWN'
            self.assertIn(expected, agent_line(data, 'dave'))

    def test_native14_bad_ledger_and_actor_identity_fail_closed(self):
        self.native14_manifest()
        path = self.run_dir / 'launch.json'
        original = path.read_text()
        for bad in ('{', json.dumps({'schema': 1}), original.replace('delm.native14.control.v1', 'old')):
            path.write_text(bad)
            with patch('delm_board.subprocess.run') as rpc:
                data = load_board(self.run_dir)
            rpc.assert_not_called()
            self.assertTrue(all(data['waits'].get(a) is None for a in data['actors']))
        state = json.loads(original)
        state['actors']['dave']['identity']['actor'] = 'alice'
        path.write_text(json.dumps(state))
        with patch('delm_board.subprocess.run', side_effect=self.native14_status) as rpc:
            data = load_board(self.run_dir)
        self.assertEqual(rpc.call_count, 1)
        self.assertIn('WAIT UNKNOWN', agent_line(data, 'dave'))

    def test_filters_selection_refresh_and_full_details(self):
        data = load_board(self.run_dir)
        view = BoardView()
        self.assertEqual([t['id'] for t in view.rows(data)], ['active-id'])
        view.filter = 'all'
        view.move(view.rows(data), 10**9)
        selected = view.selected
        self.emit('alice', 'item', {'id': 'new-open', 'subject': 'new task'})
        data = load_board(self.run_dir)
        self.assertEqual(view.rows(data)[view.index(view.rows(data))]['id'], selected)
        view.query = 'U4'
        rows = view.rows(data)
        self.assertEqual(len(rows), 1)
        details = view.document(rows[0], data)
        self.assertIn('DETAIL_TAIL', details)
        self.assertIn('FACT_TAIL', details)
        view.tab, view.query, view.actor = 'notes', 'FACT_TAIL', 'alice'
        self.assertEqual(len(view.rows(data)), 1)
        self.assertIn('scope-path', view.document(view.rows(data)[0], data))
        view.note_filter = 'FAIL'
        self.assertFalse(view.rows(data))
        self.assertNotIn('\x1b', clean('\x1b[31munsafe\x07'))

    def test_native_deltas_terminal_and_unavailable_are_distinct(self):
        native = self.run_dir / 'native.sqlite'
        before = native.read_bytes()
        data = load_board(self.run_dir)
        self.assertEqual(before, native.read_bytes())
        self.assertEqual(data['waits']['dave'][0]['reason'], 'Need both tasks')
        with closing(sqlite3.connect(native)) as db, db:
            delta = [['s', ['waits', 'wait-id', 'items'], ['active-id']],
                     ['s', ['waits', 'wait-id', 'reason'], 'Only active now']]
            db.execute("INSERT INTO document_revisions VALUES(1,2,'delta',1,?)", (json.dumps(delta),))
        data = load_board(self.run_dir)
        self.assertIn('ready 0/1', agent_line(data, 'dave'))
        self.assertEqual(data['waits']['dave'][0]['reason'], 'Only active now')
        with closing(sqlite3.connect(native)) as db, db:
            db.execute("INSERT INTO document_revisions VALUES(1,3,'delta',1,?)", (json.dumps([['s', ['waits', 'wait-id', 'state'], 'cancelled']]),))
        self.assertEqual(load_board(self.run_dir)['waits']['dave'], [])
        with closing(sqlite3.connect(native)) as db, db:
            db.execute("UPDATE tasks SET status='terminal'")
        self.assertEqual(load_board(self.run_dir)['waits']['dave'], [])
        with closing(sqlite3.connect(native)) as db, db:
            db.execute("UPDATE tasks SET status='sleeping'")
            db.execute('DROP TABLE document_revisions')
        data = load_board(self.run_dir)
        self.assertIn('WAIT UNKNOWN', agent_line(data, 'dave'))
        self.assertEqual(data['tasks'][0]['waited_by'], [])

    def test_time_exact_legacy_and_clock_reset(self):
        now = time.time_ns()
        stamp = now - 185_000_000_000
        clock = time.strftime('%H.%M.%S', time.localtime(stamp / 1e9))
        self.assertEqual(event_time({'recorded_at_ns': stamp}, now), clock + ' · 3m')
        for seconds, suffix in [(0, '0s'), (59, '59s'), (60, '1m'), (3600, '1h'), (86400, '1d')]:
            self.assertTrue(event_time({'recorded_at_ns': now - seconds * 10**9}, now).endswith(suffix))
        self.emit('alice', 'note', {'id': 'timed', 'type': 'FACT', 'text': 'exact', 'recorded_at_ns': stamp})
        notes = load_board(self.run_dir)['notes']
        self.assertTrue(event_time(notes[0]).startswith('~'))
        self.assertFalse(event_time(notes[-1], now).startswith('~'))
        self.assertEqual(event_time({}), '--.--.--')
        with closing(sqlite3.connect(self.run_dir / 'context.sqlite')) as db, db:
            db.execute('UPDATE events SET time_ns=1 WHERE sequence=(SELECT MAX(sequence) FROM events)')
        self.assertEqual(event_time(load_board(self.run_dir)['notes'][0]), '--.--.--')

    def test_local_writer_records_wall_time(self):
        local = board(self.run_dir)
        before = time.time_ns()
        local.note('alice', 'FACT', 'timestamped', 'test', 'test')
        note = load_board(self.run_dir)['notes'][-1]
        self.assertGreaterEqual(note['recorded_at_ns'], before)
        self.assertLessEqual(note['recorded_at_ns'], time.time_ns())
        self.assertNotIn('estimated_time', note)

    def test_ten_event_preview_and_section_spacing(self):
        for i in range(12):
            self.emit('alice', 'note', {'id': f'preview-{i}', 'type': 'FACT', 'text': f'preview event {i}'})
        screen = Screen()
        with patch('delm_board.curses.curs_set'), patch('delm_board.curses.set_escdelay'), \
             patch('delm_board.curses.mousemask'), patch('delm_board.curses.has_colors', return_value=False), \
             patch('delm_board.curses.color_pair', return_value=0):
            interactive(screen, self.run_dir)
        lines = screen.lines
        events = [s for s in lines.values() if s.startswith('[ALICE] FACT')]
        self.assertEqual(len(events), 10)
        self.assertTrue(any('preview event 11' in s for s in lines.values()))
        self.assertTrue(any('preview event 2' in s for s in lines.values()))
        self.assertFalse(any('preview event 1' == s for s in lines.values()))
        for y, text in lines.items():
            if text.startswith('── '):
                self.assertNotIn(y + 1, lines)
        self.assertTrue(any('WAITED BY' in s for s in lines.values()))
        self.assertFalse(any(re.search('[А-Яа-я]', s) for s in lines.values()))
        preview = '\n'.join(snapshot(self.run_dir)).split('RECENT FACT / FAIL', 1)[1]
        self.assertEqual(preview.count('alice FACT'), 10)

    def test_rendered_table_columns_align_for_all_rows_and_widths(self):
        self.emit('alice', 'item', {'id': 'open', 'subject': 'Open task'})
        self.emit('alice', 'item', {'id': 'long', 'subject': 'Long owner task'})
        self.emit('long-owner-name', 'claim', {'item': 'long'})
        for width in (45, 85, 100, 160):
            with self.subTest(width=width):
                screen = Screen(width)
                with patch('delm_board.curses.curs_set'), patch('delm_board.curses.set_escdelay'), \
                     patch('delm_board.curses.mousemask'), patch('delm_board.curses.has_colors', return_value=False), \
                     patch('delm_board.curses.color_pair', return_value=0):
                    interactive(screen, self.run_dir)
                header_y = next(y for y, text in screen.lines.items() if 'KEY' in text and 'TASK' in text)
                header = screen.lines[header_y]
                columns = [m.start() for m in re.finditer('│', header)]
                rows = [screen.lines[header_y + i] for i in (1, 2, 3)]
                self.assertTrue(columns)
                for row in rows:
                    self.assertEqual([m.start() for m in re.finditer('│', row)], columns)
                self.assertTrue(all(len(row) <= width - 1 for row in rows))
                self.assertIn('Open task', rows[-1])
        details = BoardView().document(next(t for t in load_board(self.run_dir)['tasks'] if t['id'] == 'long'), load_board(self.run_dir))
        self.assertIn('long-owner-name', details)

    def test_readable_key_is_always_visible_and_task_name_keeps_space(self):
        row = {'id': 'abcdef123456', 'key': 'DT-42', 'state': 'claimed', 'owner': 'carol',
               'waited_by': ['alice', 'carol', 'dave'], 'subject': 'Task description ' * 20}
        for width in (45, 85, 100, 160):
            header = task_line(None, width)
            line = task_line(row, width)
            self.assertEqual([cell.strip() for cell in header.split('│')],
                             ['STATE', 'OWNER', 'KEY', 'TASK'] + (['WAITED BY'] if width >= 90 else []))
            self.assertEqual(len(line), width - 3)
            self.assertEqual(line.split('│')[2].strip(), 'DT-42')
            self.assertGreaterEqual(len(line.split('│')[3].strip()), width - (45 if width >= 90 else 33))
            self.assertIn('…', line.split('│')[3])
            self.assertNotIn('abcdef12', line)

    def test_repo_keys_survive_updates_sorting_and_new_tasks_without_rewriting_history(self):
        config = json.loads((self.run_dir / 'config.json').read_text())
        config['workspace'] = '/example/delm-test'
        (self.run_dir / 'config.json').write_text(json.dumps(config))
        self.emit('alice', 'item', {'id': 'coded', 'subject': 'S1-PROFILE', 'detail': 'Prepare the shared worker instructions'})
        before = (self.run_dir / 'context.sqlite').read_bytes()
        first = load_board(self.run_dir)
        keys = {t['id']: t['key'] for t in first['tasks']}
        coded = next(t for t in first['tasks'] if t['id'] == 'coded')
        rendered = task_line(coded, 100)
        self.assertIn('DT-22', rendered)
        self.assertIn('Prepare the shared worker instructions', rendered)
        self.assertNotIn('S1-PROFILE', rendered)
        self.assertIn('Original title: S1-PROFILE', BoardView().document(coded, first))
        self.assertEqual(before, (self.run_dir / 'context.sqlite').read_bytes())
        self.emit('alice', 'done', {'item': 'active-id', 'summary': 'checked'})
        self.emit('alice', 'item', {'id': 'later', 'subject': 'Add independent output'})
        second = load_board(self.run_dir)
        self.assertTrue(all(t['key'] == keys[t['id']] for t in second['tasks'] if t['id'] in keys))
        self.assertEqual(next(t for t in second['tasks'] if t['id'] == 'later')['key'], 'DT-23')

    def test_bottom_log_scroll_and_full_waiter_names(self):
        native = self.run_dir / 'native.sqlite'
        config = json.loads((self.run_dir / 'config.json').read_text())
        config['actors']['carol'] = 'CAROL-TOKEN'
        (self.run_dir / 'config.json').write_text(json.dumps(config))
        (self.run_dir / 'dcg-reopen-sessions.json').write_text(json.dumps({actor: {'session': str(native)} for actor in ('carol', 'dave')}))
        for i in range(12):
            self.emit('alice', 'note', {'id': f'scroll-{i}', 'type': 'FACT', 'text': f'scroll event {i}'})
        notes = list(reversed(load_board(self.run_dir)['notes']))
        screen = Screen(keys=['l', curses.KEY_DOWN, curses.KEY_NPAGE, curses.KEY_HOME, curses.KEY_END, '\r'])
        with patch('delm_board.curses.curs_set'), patch('delm_board.curses.set_escdelay'), \
             patch('delm_board.curses.mousemask'), patch('delm_board.curses.has_colors', return_value=False), \
             patch('delm_board.curses.color_pair', return_value=0):
            interactive(screen, self.run_dir)
        frames = ['\n'.join(frame.values()) for frame in screen.frames]
        self.assertIn('Waited by: DAVE, CAROL', frames[0])
        self.assertIn('2 agents', frames[0])
        self.assertIn('FOCUSED', frames[1])
        self.assertIn(f"event #{notes[1]['sequence']}", frames[2])
        self.assertNotIn(f"event #{notes[0]['sequence']}", frames[2])
        self.assertIn(f"event #{notes[0]['sequence']}", frames[4])
        self.assertIn('LIVE', frames[4])
        self.assertIn(f"event #{notes[-1]['sequence']}", frames[5])
        self.assertIn('DETAIL lines', frames[6])
        self.assertIn(f"event #{notes[-1]['sequence']}", frames[6])
        for frame in frames[:6]:
            self.assertIn('> CLAIMED', frame)

    def test_log_newest_and_focus_exit_resume_live_immediately(self):
        rows = [dict(sequence=i) for i in (3, 2, 1)]
        log = LogView()
        with patch('delm_board.time.monotonic', return_value=10):
            log.navigate(rows, 1)
            self.assertEqual(log.selected, 2)
            log.navigate(rows, -1)
            self.assertIsNone(log.selected, 'newest must be LIVE, not PAUSED at 1/N')
            log.navigate(rows, 1)
            log.follow(rows, False)
            self.assertIsNone(log.selected, 'leaving focus immediately resumes following')
            self.assertIsNone(log.last_navigation)
            log.follow([dict(sequence=4), *rows], True)
            self.assertEqual(log.index([dict(sequence=4), *rows]), 0)

    def test_log_five_second_monotonic_inactivity_and_navigation_reset(self):
        rows = [dict(sequence=i) for i in (3, 2, 1)]
        log = LogView()
        with patch('delm_board.time.monotonic') as clock:
            clock.return_value = 10
            log.navigate(rows, 1)
            clock.return_value = 14.9
            log.follow(rows, True)
            self.assertEqual(log.selected, 2)
            log.navigate(rows, 1)  # Active browsing postpones expiry to 19.9.
            clock.return_value = 15
            log.follow(rows, True)
            self.assertEqual(log.selected, 1, 'must not jump on the original deadline')
            clock.return_value = 19.8
            log.follow([dict(sequence=4), *rows], True)
            self.assertEqual(log.selected, 1, 'refresh/new events must not interrupt active browsing')
            clock.return_value = 19.9
            log.follow(rows, True)
            self.assertIsNone(log.selected)
            self.assertIsNone(log.last_navigation)

    def test_log_focus_exit_keys_resume_live_without_mouse_capture(self):
        for i in range(3):
            self.emit('alice', 'note', {'id': f'follow-{i}', 'type': 'FACT', 'text': f'event {i}'})
        for exit_key in ('l', '\x1b', '/', '\t', '\r'):
            with self.subTest(exit_key=repr(exit_key)):
                screen = Screen(keys=['l', curses.KEY_DOWN, exit_key] + (['\x1b'] if exit_key == '/' else []))
                with patch('delm_board.curses.curs_set'), patch('delm_board.curses.set_escdelay'), \
                     patch('delm_board.curses.mousemask') as mousemask, \
                     patch('delm_board.curses.has_colors', return_value=False), \
                     patch('delm_board.curses.color_pair', return_value=0), \
                     patch('delm_board.time.monotonic', return_value=10):
                    interactive(screen, self.run_dir)
                mousemask.assert_called_once_with(0)
                frames = ['\n'.join(frame.values()) for frame in screen.frames]
                self.assertIn('PAUSED', frames[2])
                if exit_key in ('l', '\x1b', '/'):
                    self.assertIn('LIVE', frames[3])
                    self.assertNotIn('PAUSED', frames[3])

    def test_actual_terminal_keys_scroll_search_notes_resize_and_quit(self):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 28, 100, 0, 0))
        proc = subprocess.Popen([sys.executable, str(ROOT / 'scripts/delm_board.py'), str(self.run_dir), '--observe'],
                                stdin=slave, stdout=slave, stderr=slave, env=dict(os.environ, TERM='xterm-256color'))
        os.close(slave)
        captured = bytearray()

        def until(pattern):
            chunk = bytearray()
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        part = os.read(master, 65536)
                    except OSError:
                        break
                    captured.extend(part)
                    chunk.extend(part)
                    if pattern in chunk:
                        return
                if proc.poll() is not None:
                    break
            self.fail(f'missing terminal pattern {pattern!r}: {bytes(captured)[-2500:]!r}')

        try:
            until(b'[ALICE] FACT')
            self.assertIn(b'RECENT FACT / FAIL', captured)
            self.assertIn(b'OWNER', captured)
            self.assertIn(b'U4 active first', captured)
            self.assertNotRegex(bytes(captured), br'\x1b\[\?(?:1000|1002|1003)(?:;[0-9]+)*h')
            os.write(master, b'\r')
            until(b'DETAIL lines')
            os.write(master, b'\x1bOF')  # xterm End: scroll to full description/note tail
            until(b'FACT_TAIL')
            os.write(master, b'\x1b')
            until(b'Enter detail')
            os.write(master, b'\t')
            until(b'NOTES')
            os.write(master, b'/absent-filter\r')
            until(b'No matches')
            os.write(master, b'\x1b')
            until(b'FACT')
            fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack('HHHH', 8, 30, 0, 0))
            proc.send_signal(signal.SIGWINCH)
            until(b'enlarge terminal')
            os.write(master, b'q')
            self.assertEqual(proc.wait(timeout=5), 0)
            self.assertFalse((self.run_dir / 'server.log').exists())
            self.assertFalse((self.run_dir / 'endpoint.json').exists())
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
            os.close(master)
