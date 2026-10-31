"""Bounded, read-only observation of exact SDK Host roots (public HTTP API)."""
import json
import os
import re
import stat
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward the operator's bearer to a different endpoint.


def private_json(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('Noncanonical private file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Unsafe private file')
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Oversized private file')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise TypeError('Expected JSON object')
    return value


def origin(value):
    if not isinstance(value, str):
        raise TypeError('Missing endpoint')
    url = urlsplit(value)
    if (url.scheme != 'http' or url.hostname not in ('127.0.0.1', '::1', 'localhost')
            or url.username is not None or url.password is not None or url.query or url.fragment
            or url.path not in ('', '/')):
        raise ValueError('Expected private loopback origin')
    # Access port to reject invalid ports before making any request.
    return f'http://{url.hostname if url.hostname != "::1" else "[::1]"}:{url.port or 80}'


def observe_sdk(run, actors, workspace, client_file):
    """Hard bound even slow HTTP headers/bodies; keep completed peers on timeout."""
    result = {'waits': dict.fromkeys(actors), 'activity': dict.fromkeys(actors, 'unknown')}
    if client_file is None:
        return result
    request = {'run': str(run), 'actors': list(actors), 'workspace': workspace, 'client': str(client_file)}
    try:
        # Rex's login-style argv[0] (-python3) leaves sys.executable empty.
        # Resolve the running Linux interpreter, not another Python on PATH.
        executable = sys.executable or os.readlink('/proc/self/exe')
        response = subprocess.run([executable, '-B', str(Path(__file__).resolve())],
                                  input=json.dumps(request).encode(), capture_output=True, timeout=3, check=False)
        output = response.stdout
    except subprocess.TimeoutExpired as error:
        output = error.stdout or b''  # subprocess.run kills/reaps the entire network reader.
    except OSError:
        return result
    for line in output.splitlines():
        try:
            entry = json.loads(line)
            actor = entry['actor']
            if actor in result['waits']:
                result['waits'][actor] = entry['waits']
                result['activity'][actor] = entry['activity']
        except (ValueError, KeyError, TypeError):
            continue  # A killed worker can leave an incomplete last frame.
    return result


def _observe_sdk(run, actors, workspace, client_file):
    """Credentials come only from an explicit operator path, never run metadata.

    A missing/unreachable/unbound source is UNKNOWN, not evidence of no wait.
    No tool execution, task abort, receipt read/ACK or Native SQLite access.
    """
    unknown = {'waits': dict.fromkeys(actors), 'activity': dict.fromkeys(actors, 'unknown')}
    if client_file is None:
        return unknown
    try:
        state = json.loads((run / 'sdk-launch.json').read_text())
        if (not isinstance(state, dict) or state.get('version') != 1 or state.get('run') != str(run)
                or state.get('workspace') != workspace or not isinstance(state.get('actors'), dict)
                or set(state['actors']) != set(actors)):
            return unknown
        records = state['actors']
        host_ids = []
        for record in records.values():
            if (not isinstance(record, dict) or type(record.get('rootId')) is not int or record['rootId'] != 1
                    or not isinstance(record.get('hostId'), str)
                    or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,255}', record['hostId'])):
                return unknown
            host_ids.append(record['hostId'])
        if len(set(host_ids)) != len(host_ids):
            return unknown
        auth = private_json(client_file)
        if (set(auth) not in ({'url', 'token'}, {'baseUrl', 'token'})
                or not isinstance(auth.get('token'), str) or not auth['token'].strip()
                or '\n' in auth['token'] or '\r' in auth['token']):
            return unknown
        endpoint = origin(auth.get('url', auth.get('baseUrl')))
        if endpoint != origin(state['endpoint']):
            return unknown
        bindings = private_json(state['bindingsFile'])
        if bindings.get('version') != 1 or not isinstance(bindings.get('sessions'), dict):
            return unknown
    except (OSError, ValueError, KeyError, TypeError):
        return unknown

    def observe(actor):
        try:
            host_id = records[actor]['hostId']
            binding = bindings['sessions'].get(host_id)
            if (not isinstance(binding, dict) or binding.get('run') != str(run)
                    or binding.get('workspace') != workspace or binding.get('actor') != actor
                    or type(binding.get('enabled')) is not bool):
                return None, 'unknown'
            if not binding['enabled']:
                return None, 'disabled'
            # Proxy settings must not send the local bearer through an external proxy.
            opener = build_opener(ProxyHandler({}), NoRedirect())
            deadline = time.monotonic() + 2

            def get(path):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Observation deadline')
                request = Request(endpoint + path, headers={'Authorization': 'Bearer ' + auth['token']})
                with opener.open(request, timeout=remaining) as response:
                    raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise ValueError('Oversized Host response')
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise TypeError('Expected Host object')
                return value

            base = f'/v1/sessions/{host_id}'
            session = get(base)
            if session.get('id') != host_id or session.get('cwd') != workspace:
                return None, 'unknown'
            root = get(base + '/agents/1')
            if (root.get('id') != 1 or root.get('sessionId') != host_id
                    or not isinstance(root.get('config'), dict) or root['config'].get('cwd') != workspace
                    or type(root.get('busy')) is not bool):
                return None, 'unknown'
            doc = get(base + '/agents/1/docs/delm.waits')
            if (doc.get('kind') != 'delm.waits' or not isinstance(doc.get('value'), dict)
                    or not isinstance(doc['value'].get('waits'), dict)):
                return None, 'unknown'
            active = []
            for entry in doc['value']['waits'].values():
                if (not isinstance(entry, dict) or entry.get('state') not in
                        ('waiting', 'failed', 'sent', 'cancelled')):
                    return None, 'unknown'
                if entry['state'] in ('sent', 'cancelled'):
                    continue  # Historical deliveries are not active waits.
                if (not isinstance(entry.get('items'), list)
                        or any(not isinstance(item, str) or not item for item in entry['items'])
                        or entry.get('mode', 'items') not in ('items', 'work')):
                    return None, 'unknown'
                active.append({key: entry[key] for key in ('state', 'items', 'mode', 'taskId') if key in entry})
            return active, 'running' if root['busy'] else 'idle'
        except (OSError, ValueError, KeyError, TypeError, HTTPException, HTTPError, URLError):
            return None, 'unknown'  # Do not expose errors containing headers or private payloads.

    with ThreadPoolExecutor(max_workers=max(1, min(8, len(actors)))) as pool:
        pending = {pool.submit(observe, actor): actor for actor in actors}
        for future in as_completed(pending):
            waits, activity = future.result()
            print(json.dumps({'actor': pending[future], 'waits': waits, 'activity': activity}), flush=True)


if __name__ == '__main__':
    request = json.load(sys.stdin)
    _observe_sdk(Path(request['run']), request['actors'], request['workspace'], request['client'])
