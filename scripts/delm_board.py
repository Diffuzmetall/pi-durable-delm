#!/usr/bin/env python3
"""DeLM board: interactive read-only observer, or board server with an observer."""
import argparse
import curses
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import textwrap
import time
import unicodedata
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import Any

from delm_domain import project_events


def clean(value, multiline=False):
    text = ''.join(c for c in str(value) if not unicodedata.category(c).startswith('C')
                   or (multiline and c == '\n'))
    return text if multiline else ' '.join(text.split())


def native_waits(db):
    """Project our version-1 wait document without opening a native storage owner."""
    records = [json.loads(raw) for raw, in db.execute(
        'SELECT record FROM tasks WHERE kind=? AND status!=?', (json.dumps('delm.wait'), 'terminal'))]
    if not records:
        return []
    waits = {}
    for document_id, in db.execute('SELECT id FROM documents WHERE kind=? AND retired_at IS NULL',
                                   (json.dumps('delm.waits'),)):
        base = db.execute("SELECT seq,version,content FROM document_revisions WHERE document_id=? AND kind='base' ORDER BY seq DESC LIMIT 1",
                          (document_id,)).fetchone()
        if not base or base[1] != 1:
            raise ValueError('Unsupported native wait document')
        doc = json.loads(base[2])
        for kind, version, raw in db.execute('SELECT kind,version,content FROM document_revisions WHERE document_id=? AND seq>? ORDER BY seq',
                                              (document_id, base[0])):
            if kind != 'delta' or version != 1:
                raise ValueError('Unsupported native wait revision')
            # delm.waits only sets/deletes object fields; reject unfamiliar codecs.
            for op in json.loads(raw):
                if op[0] not in ('s', 'd') or not isinstance(op[1], list):
                    raise ValueError('Unsupported native wait delta')
                path = op[1]
                if not path:
                    if op[0] != 's':
                        raise ValueError('Unsupported native wait root delta')
                    doc = op[2]
                    continue
                target = doc
                for key in path[:-1]:
                    target = target[key]
                if not isinstance(target, dict):
                    raise ValueError('Unsupported native wait container')
                if op[0] == 's':
                    target[path[-1]] = op[2]
                else:
                    target.pop(path[-1], None)
        waits.update(doc['waits'])
    result = []
    for record in records:
        entry = waits[record['input']['id']]
        if entry['state'] == 'waiting':
            result.append(dict(entry, native_id=record['id']))
    return result


def event_time(note, now_ns=None):
    recorded = note.get('recorded_at_ns')
    if recorded is None:
        return '--.--.--'
    age = max(0, ((time.time_ns() if now_ns is None else now_ns) - recorded) // 1_000_000_000)
    amount, unit = (age, 's') if age < 60 else (age // 60, 'm') if age < 3600 else (age // 3600, 'h') if age < 86400 else (age // 86400, 'd')
    clock = time.strftime('%H.%M.%S', time.localtime(recorded / 1_000_000_000))
    return f"{'~' if note.get('estimated_time') else ''}{clock} · {amount}{unit}"


def task_label(task):
    if task.get('key'):
        return task['key']
    unit = re.search(r'\b(U\d+|REVIEW|QA|ACCEPT)\b', task['subject'])
    return unit[0] if unit else task['id'][:8]


def project_prefix(workspace):
    words = re.findall(r'[A-Za-z0-9]+', Path(workspace).name)
    return (''.join(word[0] for word in words) if len(words) > 1 else ''.join(words)[:4]).upper() or 'PRJ'


def task_title(task):
    subject = task['subject'].removeprefix('iii-native-durable-v2 ')
    # Historic phase codes stay in the record; display their existing explanation.
    if re.fullmatch(r'S\d+-[A-Z0-9-]+', subject) and task.get('detail', '').strip():
        return clean(task['detail'])
    return subject


def task_line(row, width):
    show_wait = width >= 90
    widths = [7, 5, 9, width - (45 if show_wait else 33)]
    values = [row['state'].upper(), row['owner'].upper(), row.get('key', '-'), task_title(row)] if row else ['STATE', 'OWNER', 'KEY', 'TASK']
    if show_wait:
        widths.append(9)
        values.append((f"{len(row['waited_by'])} agents" if len(row['waited_by']) > 1 else
                       ','.join(actor.upper() for actor in row['waited_by']) or '-') if row else 'WAITED BY')
    cells = []
    for value, size in zip(values, widths):
        value = clean(value)
        if len(value) > size:
            value = value[:size - 1] + '…'
        cells.append(value.ljust(size))
    return ' │ '.join(cells)


def load_board(run):
    config = json.loads((run / 'config.json').read_text())
    with closing(sqlite3.connect((run / 'context.sqlite').as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        events = db.execute('SELECT sequence, time_ns, actor, kind, payload FROM events ORDER BY sequence').fetchall()
        projection = project_events((dict(sequence=seq, actor=actor, kind=kind, payload=raw)
                                     for seq, _, actor, kind, raw in events), tuple(config['actors']))
        # Leases share this snapshot; no board owner, receipt/ack, schema or expiry writes.
        try:
            from delm_leases import project as project_leases
        except ModuleNotFoundError as error:
            if error.name != 'delm_leases':
                raise
            leases = []
        else:
            leases = project_leases(db)
    # Legacy events have only monotonic time. File mtime anchors the latest write,
    # approximately; never carry that estimate across a detected clock reset.
    legacy_offset = (run / 'context.sqlite').stat().st_mtime_ns - events[-1][1] if events else 0
    legacy_start = 0
    for i in range(1, len(events)):
        if events[i][1] < events[i - 1][1]:
            legacy_start = i
    data: dict[str, Any] = {
        'actors': list(config['actors']), 'workspace': config.get('workspace', 'isolated'),
        'statuses': {}, 'tasks': [], 'notes': [], 'waits': {},
        'sequence': events[-1][0] if events else 0,
    }
    data.update(blockers=projection.get('blockers', []), leases=leases,
                sessions=projection.get('sessions', []), events=projection.get('events', []))
    times = {}
    for i, (sequence, monotonic_ns, actor, kind, raw) in enumerate(events):
        item = json.loads(raw)
        if kind == 'status':
            data['statuses'][actor] = item['text']
        if i >= legacy_start:
            times[sequence] = monotonic_ns + legacy_offset
    for item in projection['notes']:
        note = dict(item)
        if 'recorded_at_ns' not in note and note['sequence'] in times:
            note.update(recorded_at_ns=times[note['sequence']], estimated_time=True)
        data['notes'].append(note)
    prefix = project_prefix(config.get('workspace', 'isolated'))
    data['tasks'] = [dict(task, owner=task.get('owner') or '-', key=f'{prefix}-{number}',
                          sequence=task.get('sequence', task.get('revision', 0)))
                     for number, task in enumerate(projection['queue'], 1)]
    order = {'claimed': 0, 'blocked': 1, 'open': 2, 'done': 3}
    data['tasks'].sort(key=lambda task: (order.get(task['state'], 2), task['sequence']))
    # Existing run metadata only; never open a second owner or write to native databases.
    manifest = run / 'dcg-reopen-sessions.json'
    if manifest.exists():
        for actor, info in json.loads(manifest.read_text()).items():
            if actor not in data['actors']:
                continue
            try:
                path = Path(info['session']).resolve()
                with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=0.1)) as db:
                    db.execute('BEGIN')
                    data['waits'][actor] = native_waits(db)
            except (OSError, sqlite3.Error, KeyError, ValueError, TypeError, IndexError):
                data['waits'][actor] = None  # unavailable is not evidence of no wait
    for task in data['tasks']:
        task['waited_by'] = [actor for actor in data['actors']
                             if any(task['id'] in wait['items'] for wait in data['waits'].get(actor) or [])]
    return data


def agent_line(data, actor):
    claims = [t for t in data['tasks'] if t['owner'] == actor and t['state'] in ('claimed', 'blocked')]
    waits = data['waits'].get(actor)
    if waits and any(wait.get('mode') == 'work' for wait in waits):
        current = 'WAIT → available work'
    elif waits:
        tasks = {task['id']: task for task in data['tasks']}
        ids = list(dict.fromkeys(item for wait in waits for item in wait['items']))
        pending = []
        for item in ids:
            task = tasks.get(item)
            if task is None:
                pending.append(f'{item[:8]} [MISSING]')
            elif task['state'] != 'done':
                owner = task['owner'].upper() if task['owner'] != '-' else 'OPEN'
                pending.append(f'{task_label(task)} [{owner}]')
        current = f"WAIT → {', '.join(pending) or 'wake pending'} | ready {len(ids) - len(pending)}/{len(ids)}"
    elif actor in data['waits'] and waits is None:
        current = 'WAIT UNKNOWN'
    elif claims:
        current = 'CLAIM ' + '; '.join(f"{task_label(t)} {task_title(t)}" for t in claims)
    else:
        current = 'NO CLAIM'
    lifecycle = next((entry for entry in data.get('sessions', []) if entry.get('actor') == actor), {})
    if lifecycle.get('state') in ('active', 'idle', 'ended', 'blocked'):
        current += f" | {lifecycle['state'].upper()} gen {lifecycle.get('generation', 0)}"
        if lifecycle.get('reason'):
            current += ' ' + lifecycle['reason']
    reported = data['statuses'].get(actor, 'no published status')
    return f'{actor:6} {current} | reported: {reported}'


def snapshot(run):
    data = load_board(run)
    counts = Counter(t['state'] for t in data['tasks'])
    lines = ['DeLM | read-only board', 'Workspace: ' + data['workspace'], '',
             f"CLAIMED {counts['claimed']} | OPEN {counts['open']} | BLOCKED {counts['blocked']} | DONE {counts['done']}",
             f"Unresolved blockers: {len(data['blockers'])} | Leases: {len(data['leases'])} (advisory)", '', 'AGENTS', '']
    lines += ['  ' + clean(agent_line(data, a)) for a in data['actors']]
    task_width = max([100] + [len(clean(task['subject'].removeprefix('iii-native-durable-v2 '))) + 44 for task in data['tasks']])
    lines += ['', f"TASKS ({len(data['tasks'])}; active first)", '', '  ' + task_line(None, task_width)]
    lines += ['  ' + task_line(task, task_width) for task in data['tasks']]
    lines += ['', 'RECENT FACT / FAIL', '']
    lines += [f"  #{n['sequence']} {n['actor']} {n['type']} · {event_time(n)}: {clean(n['text'])}" for n in data['notes'][-10:]]
    lines += ['', 'UNRESOLVED BLOCKERS (all)', '']
    lines += [f"  {clean(json.dumps(blocker, ensure_ascii=False))}" for blocker in data['blockers']]
    lines += ['', 'LEASES (advisory; expiry is not producer death)', '']
    lines += [f"  {clean(json.dumps(lease, ensure_ascii=False))}" for lease in data['leases']]
    lines += [f"Events: {data['sequence']}"]
    return lines


class BoardView:
    """Selection and filters are local UI state, never shared board state."""
    def __init__(self):
        self.tab = 'tasks'
        self.filter = 'active'
        self.note_filter = 'all'
        self.actor = 'all'
        self.query = ''
        self.selected = None
        self.top = 0
        self.detail = False
        self.scroll = 0

    def rows(self, data):
        rows = data['tasks'] if self.tab == 'tasks' else list(reversed(data['notes']))
        result = []
        for row in rows:
            if self.actor != 'all' and row.get('owner', row.get('actor')) != self.actor:
                continue
            if self.tab == 'tasks':
                # An entirely completed team should show its results, not an empty queue.
                if self.filter == 'active' and row['state'] == 'done' and any(
                        task['state'] != 'done' for task in data['tasks']):
                    continue
                if self.filter not in ('active', 'all') and row['state'] != self.filter:
                    continue
            elif self.note_filter != 'all' and row['type'] != self.note_filter:
                continue
            if self.query.casefold() not in ' '.join(str(v) for v in row.values()).casefold():
                continue
            result.append(row)
        return result

    def key(self, row):
        return row['id'] if self.tab == 'tasks' else row['sequence']

    def index(self, rows):
        return next((i for i, row in enumerate(rows) if self.key(row) == self.selected), 0)

    def move(self, rows, delta):
        if rows:
            self.selected = self.key(rows[max(0, min(len(rows) - 1, self.index(rows) + delta))])

    def reset(self):
        self.selected = None
        self.top = self.scroll = 0
        self.detail = False

    def document(self, row, data):
        if self.tab == 'notes':
            return (f"{row['type']} | {row['actor']} | event #{row['sequence']} | {event_time(row)}\nID: {row.get('id', '-')}\n\n{row['text']}\n\nScope: {row.get('scope', '-')}\nBasis: {row.get('basis', '-')}\n\n"
                    + json.dumps({key: row[key] for key in ('task', 'related', 'output', 'readiness', 'limitations', 'resolves')
                                  if key in row}, ensure_ascii=False, indent=2))
        lines = [f"{row.get('key', '-')} · {task_title(row)}", f"Original title: {row['subject']}", f"State: {row['state']} | Owner: {row['owner']}", f"ID: {row['id']}", f"Waited by: {', '.join(row.get('waited_by', [])) or '-'}", '',
                 row.get('detail', ''), '', 'RESULT / HANDOFF', row.get('summary', 'No completion published.'),
                 f"Publication: {row.get('publication_id', '-')}", '', 'TASK PROJECTION']
        lines += [json.dumps({key: row[key] for key in ('generation', 'revision', 'deps', 'criteria', 'parent',
                              'outputs', 'mapping', 'handoff', 'readiness', 'blockers', 'blocked_reason')
                              if key in row}, ensure_ascii=False, indent=2), '', 'TASK LEASES (advisory)']
        lines += [json.dumps(lease, ensure_ascii=False) for lease in data.get('leases', [])
                  if lease.get('task') == row['id']]
        unit = re.search(r'\b(U\d+|REVIEW|QA|ACCEPT)\b', row['subject'])
        related = [note for note in data['notes'] if note.get('task') == row['id']
                   or row['id'] in note.get('related', []) or note.get('output') == row['id']
                   or ('task' not in note and (row['id'] in note['text'] or
                       (unit and re.search(r'\b' + unit[0] + r'\b', note['text']))))]
        lines += ['', 'TASK EVENT HISTORY']
        lines += [json.dumps(event, ensure_ascii=False) for event in data.get('events', [])
                  if event['payload'].get('item') == row['id']
                  or event['payload'].get('id') == row['id']
                  or (isinstance(event['payload'].get('task'), dict)
                      and event['payload']['task'].get('id') == row['id'])]
        lines += ['', 'RELATED FACT / FAIL']
        for note in reversed(related):
            lines += [f"\n#{note['sequence']} {note['actor']} {note['type']} · {event_time(note)}", note['text'],
                      f"Scope: {note.get('scope', '-')} | Basis: {note.get('basis', '-')}"]
        return '\n'.join(lines)


class LogView(BoardView):
    """Pause only while actively navigating older log entries."""
    def __init__(self):
        super().__init__()
        self.tab = 'notes'
        self.last_navigation = None

    def follow(self, rows, focused):
        if (not focused or self.index(rows) == 0 or self.last_navigation is None
                or time.monotonic() >= self.last_navigation + 5):
            self.selected = self.last_navigation = None

    def navigate(self, rows, delta):
        self.move(rows, delta)
        self.last_navigation = time.monotonic()
        self.follow(rows, True)


def wrapped(text, width):
    return [line for paragraph in clean(text, multiline=True).split('\n')
            for line in (textwrap.wrap(paragraph, max(1, width), replace_whitespace=False) or [''])]


def interactive(screen, run, server=None):
    curses.curs_set(0)
    curses.set_escdelay(25)
    screen.timeout(100)
    screen.keypad(True)
    curses.mousemask(0)  # Leave dragging/selection/copy to the terminal.
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        for pair, color in enumerate((curses.COLOR_CYAN, curses.COLOR_YELLOW, curses.COLOR_GREEN, curses.COLOR_RED), 1):
            curses.init_pair(pair, color, -1)
    view, log_view = BoardView(), LogView()
    log_focus = False
    data, error, refresh = None, '', 0
    searching, previous_query = False, ''

    def put(y, x, text, style=0):
        height, width = screen.getmaxyx()
        if 0 <= y < height and 0 <= x < width - 1:
            try:
                # Preserve column padding while still removing terminal control characters.
                screen.addnstr(y, x, clean(text, multiline=True).replace('\n', ' '), width - x - 1, style)
            except curses.error:
                pass  # resize / double-width character at the terminal edge

    while server is None or server.poll() is None:
        if time.monotonic() >= refresh:
            try:
                data = load_board(run)
                error = ''
            except (OSError, sqlite3.Error, ValueError) as exc:
                error = f'Read unavailable (retaining last view): {exc}'
            refresh = time.monotonic() + 1
        log_view.follow(log_view.rows(data) if data else [], log_focus)
        screen.erase()
        height, width = screen.getmaxyx()
        log_height, log_page = 0, 1
        minimum_height = max(14, 12 + len(data['actors'])) if data else 14
        if height < minimum_height or width < 45:
            put(0, 0, f'DeLM: enlarge terminal (45x{minimum_height} minimum); q exits')
        elif data is None:
            put(0, 0, error or 'Reading board...')
        else:
            rows = view.rows(data)
            index = view.index(rows)
            if rows:
                view.selected = view.key(rows[index])
            counts = Counter(t['state'] for t in data['tasks'])
            put(0, 0, 'DeLM BOARD | READ ONLY | no server/agent restart', curses.A_BOLD)
            put(1, 0, f"CLAIMED {counts['claimed']}   OPEN {counts['open']}   BLOCKED {counts['blocked']}   DONE {counts['done']}   events {data['sequence']}")
            put(2, 0, f"{data['workspace']} | blockers {len(data['blockers'])} | leases {len(data['leases'])} advisory", curses.A_DIM)
            put(3, 0, '── AGENTS ' + '─' * width, curses.A_BOLD)
            for i, actor in enumerate(data['actors']):
                summary = agent_line(data, actor).split(' | reported:', 1)[0]
                put(5 + i, 0, summary.replace(actor, actor.upper(), 1))
            start = 9 + len(data['actors'])
            capacity = max(1, height - start - 2 - (view.tab == 'tasks' and not view.detail))
            log_height = min(32, max(0, capacity - min(5, len(rows)))) if view.tab == 'tasks' and not view.detail else 0
            if not log_height:
                log_focus = False
            capacity = max(1, capacity - log_height)
            state_filter = view.filter if view.tab == 'tasks' else view.note_filter
            put(start - 3, 0, f"── {view.tab.upper()} | {state_filter} | actor:{view.actor} | search:{view.query or '-'} | {index + 1 if rows else 0}/{len(rows)} " + '─' * width, curses.A_BOLD)
            if not view.detail:
                put(start - 1, 0, '  ' + task_line(None, width) if view.tab == 'tasks' else
                    '  EVENT   │ AUTHOR │ TYPE │ TIME / AGE │ MESSAGE', curses.A_DIM)
            if view.detail and rows:
                lines = wrapped(view.document(rows[index], data), width - 2)
                view.scroll = max(0, min(view.scroll, max(0, len(lines) - capacity)))
                for i, line in enumerate(lines[view.scroll:view.scroll + capacity]):
                    put(start + i, 0, line)
                put(height - 2, 0, f'DETAIL lines {view.scroll + 1}-{min(view.scroll + capacity, len(lines))}/{len(lines)} | arrows/PgUp/PgDn scroll | Esc back')
            else:
                view.top = max(0, min(view.top, index))
                if index >= view.top + capacity:
                    view.top = index - capacity + 1
                for i, row in enumerate(rows[view.top:view.top + capacity]):
                    pos = view.top + i
                    if view.tab == 'tasks':
                        text = task_line(row, width)
                        color = {'claimed': 2, 'open': 1, 'blocked': 4, 'done': 3}.get(row['state'], 1)
                    else:
                        text = f"#{row['sequence']:<5} {row['actor']:6} {row['type']:4} {event_time(row)} │ {row['text']}"
                        color = 4 if row['type'] == 'FAIL' else 1
                    style = curses.color_pair(color) if curses.has_colors() else 0
                    put(start + i, 0, ('> ' if pos == index else '  ') + text,
                        style | (curses.A_REVERSE if pos == index else 0))
                if not rows:
                    put(start, 0, 'No matches. f changes filter; / searches; Esc clears search.')
                if view.tab == 'tasks' and rows:
                    names = ', '.join(actor.upper() for actor in rows[index]['waited_by']) or '-'
                    put(start + min(capacity, len(rows)), 0, 'Waited by: ' + names)
                if log_height:
                    log_rows = log_view.rows(data)
                    log_index = log_view.index(log_rows)
                    log_top = start + min(capacity, max(1, len(rows))) + 2
                    mode = 'LIVE' if log_view.selected is None else 'PAUSED'
                    focus = 'FOCUSED | l: tasks' if log_focus else 'l: scroll log'
                    put(log_top, 0, f"── RECENT FACT / FAIL | {mode} | {log_index + 1 if log_rows else 0}/{len(log_rows)} | {focus} " + '─' * width, curses.A_BOLD)
                    log_page = max(1, min(10, (height - log_top - 4) // 3))
                    y = log_top + 2
                    for note in log_rows[log_index:log_index + 10]:
                        if y >= height - 3:
                            break
                        color = 4 if note['type'] == 'FAIL' else 1
                        style = curses.color_pair(color) if curses.has_colors() else 0
                        put(y, 0, f"[{note['actor'].upper()}] {note['type']} · event #{note['sequence']} · {event_time(note)}", style | curses.A_BOLD)
                        y += 1
                        for line in wrapped(note['text'], width - 4)[:2]:
                            if y >= height - 2:
                                break
                            put(y, 2, line)
                            y += 1
                put(height - 2, 0, 'LOG | arrows/jk PgUp/PgDn | Home latest | End oldest | Enter detail | l tasks' if log_focus else
                    'l focus log | arrows/jk PgUp/PgDn | Enter detail | Tab tasks/notes | f filter | a actor')
            quit_hint = 'q close VIEW only' if server is None else 'q stops board SERVER'
            put(height - 1, 0, ('/ ' + view.query + '  [Enter apply, Esc cancel]') if searching else
                (error or f'/ search | {quit_hint} | CLAIM is ownership, not proof the model is running'), curses.A_DIM)
        screen.refresh()
        try:
            key = screen.get_wch()
        except curses.error:
            continue
        rows = view.rows(data) if data else []
        if searching:
            if key in ('\n', '\r'):
                searching = False
            elif key == '\x1b':
                view.query, searching = previous_query, False
            elif key in (curses.KEY_BACKSPACE, '\x7f', '\b'):
                view.query = view.query[:-1]
            elif isinstance(key, str) and key.isprintable():
                view.query += key
            view.reset()
            continue
        if key in ('q', '\x03'):
            return
        if key == curses.KEY_RESIZE:
            continue
        if key == 'l' and log_height:
            log_focus = not log_focus
        elif key == '/':
            log_focus = False
            previous_query, searching = view.query, True
        elif key in ('\n', '\r') and log_focus:
            log_rows = log_view.rows(data)
            if not log_rows:
                continue
            view.tab, view.detail = 'notes', True
            view.query, view.actor, view.note_filter = '', 'all', 'all'
            view.selected = log_view.key(log_rows[log_view.index(log_rows)])
            view.scroll, log_focus = 0, False
        elif key in ('\n', '\r') and rows:
            view.detail = not view.detail
            view.scroll = 0
        elif key == '\x1b':
            if log_focus:
                log_focus = False
                continue
            if view.detail:
                view.detail = False
            else:
                view.query = ''
            view.scroll = 0
        elif key == '\t':
            log_focus = False
            view.tab = 'notes' if view.tab == 'tasks' else 'tasks'
            view.query = ''
            view.reset()
        elif key == 'f':
            if view.tab == 'tasks':
                filters = ('active', 'all', 'claimed', 'open', 'blocked', 'done')
                view.filter = filters[(filters.index(view.filter) + 1) % len(filters)]
            else:
                filters = ('all', 'FACT', 'FAIL', 'CORRECTION', 'RESOLUTION')
                view.note_filter = filters[(filters.index(view.note_filter) + 1) % len(filters)]
            view.reset()
        elif key == 'a' and data:
            actors = ['all'] + data['actors']
            view.actor = actors[(actors.index(view.actor) + 1) % len(actors)]
            view.reset()
        else:
            delta = {curses.KEY_UP: -1, 'k': -1, curses.KEY_DOWN: 1, 'j': 1,
                     curses.KEY_PPAGE: -max(1, height - 12), curses.KEY_NPAGE: max(1, height - 12),
                     curses.KEY_HOME: -10**9, curses.KEY_END: 10**9}.get(key, 0)
            if log_focus:
                delta = -log_page if key == curses.KEY_PPAGE else log_page if key == curses.KEY_NPAGE else delta
                if delta:
                    log_view.navigate(log_view.rows(data), delta)
            elif view.detail:
                view.scroll = max(0, view.scroll + delta)
            else:
                view.move(rows, delta)


def show(run, server=None):
    if sys.stdin.isatty() and sys.stdout.isatty():
        curses.wrapper(interactive, run, server)
    else:
        while server is None or server.poll() is None:
            width, height = shutil.get_terminal_size((100, 30))
            print('\033[2J\033[H' + '\n'.join(line[:width - 1] for line in snapshot(run)[:height - 1]), end='', flush=True)
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--once', action='store_true', help='print all tasks once; no server or writes')
    mode.add_argument('--observe', action='store_true', help='attach read-only UI; never start or stop the board server')
    args = parser.parse_args()
    run = args.run.resolve()
    if args.once:
        print('\n'.join(snapshot(run)))
    elif args.observe:
        show(run)
    else:
        with (run / 'server.log').open('a') as log:
            server = subprocess.Popen([sys.executable, str(Path(__file__).with_name('delm_local.py')), 'serve', str(run)], stdout=log, stderr=log)
            try:
                show(run, server)
                if server.poll() is not None:
                    raise SystemExit(f"board server exited {server.returncode}; see {run / 'server.log'}")
            except KeyboardInterrupt:
                pass
            finally:
                if server.poll() is None:
                    server.terminate()
                    server.wait(timeout=5)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (OSError, sqlite3.Error, ValueError, curses.error) as error:
        sys.exit(str(error))
