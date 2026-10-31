"""Real loopback HTTP regression coverage; no models or live sessions."""
import copy
import importlib
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class SdkObserverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)
        self.requests = []
        self.responses = {}
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                outer.requests.append((self.command, self.path, self.headers.get('Authorization')))
                status, body = outer.responses.get(self.path, (404, {}))
                self.send_response(status)
                if body == 'truncated-chunk':
                    self.send_header('Transfer-Encoding', 'chunked')
                    self.end_headers()
                    self.wfile.write(b'10\r\nshort')
                    self.close_connection = True
                    return
                if body == 'slow-body':
                    self.send_header('Content-Length', '100')
                    self.end_headers()
                    for _ in range(100):
                        try:
                            self.wfile.write(b' ')
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            break
                        time.sleep(0.05)
                    return
                if status == 302:
                    self.send_header('Location', outer.endpoint + '/redirect-target')
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join)
        self.addCleanup(self.server.shutdown)
        self.endpoint = f'http://127.0.0.1:{self.server.server_port}'
        self.client = self.run / 'client.json'
        self.bindings_file = self.run / 'bindings.json'
        self.bindings = {'version': 1, 'sessions': {}}
        self.state = {'version': 1, 'run': str(self.run), 'workspace': str(self.run),
                      'endpoint': self.endpoint, 'bindingsFile': str(self.bindings_file), 'actors': {}}
        for actor in ('alice', 'bob'):
            host = f'host-{actor}'
            self.state['actors'][actor] = {'hostId': host, 'rootId': 1}
            self.bindings['sessions'][host] = {'run': str(self.run), 'workspace': str(self.run),
                                               'actor': actor, 'enabled': True}
            base = f'/v1/sessions/{host}'
            self.responses[base] = (200, {'id': host, 'cwd': str(self.run)})
            self.responses[base + '/agents/1'] = (200, {'id': 1, 'sessionId': host,
                'busy': actor == 'alice', 'config': {'cwd': str(self.run)}})
            waits = {} if actor == 'alice' else {'wait-1': {
                'id': 'wait-1', 'state': 'waiting', 'items': ['task-1'], 'taskId': 164,
                'reason': 'Needs Alice output'}}
            self.responses[base + '/agents/1/docs/delm.waits'] = (200, {
                'kind': 'delm.waits', 'value': {'waits': waits}})
        self.save(self.client, {'url': self.endpoint, 'token': 'private-test-token'})
        self.save_state()

    def save(self, path, value):
        path.write_text(json.dumps(value))
        path.chmod(0o600)

    def save_state(self):
        self.save(self.run / 'sdk-launch.json', self.state)
        self.save(self.bindings_file, self.bindings)

    def observe(self):
        module = importlib.import_module('delm_sdk_observer')
        return module.observe_sdk(self.run, ['alice', 'bob'], str(self.run), self.client)

    def bob_doc(self):
        return self.responses['/v1/sessions/host-bob/agents/1/docs/delm.waits'][1]['value']['waits']

    def test_real_http_waits_activity_and_no_mutations(self):
        before = {p: p.read_bytes() for p in self.run.iterdir()}
        result = self.observe()
        self.assertEqual(result['waits']['alice'], [])
        self.assertEqual(result['waits']['bob'][0]['items'], ['task-1'])
        self.assertEqual(result['activity'], {'alice': 'running', 'bob': 'idle'})
        self.assertEqual(before, {p: p.read_bytes() for p in self.run.iterdir()})
        self.assertEqual(len(self.requests), 6)
        self.assertTrue(all(method == 'GET' and auth == 'Bearer private-test-token'
                            for method, _, auth in self.requests))
        self.assertNotIn('private-test-token', repr(result))

    @unittest.skipUnless(Path('/proc/self/exe').exists(), 'Linux Rex interpreter resolution')
    def test_rex_login_argv0_with_empty_python_executable(self):
        # Rex starts shell:none terminals with argv[0] = -python3; CPython then
        # has an empty sys.executable. Exercise the real child and HTTP reader.
        code = ('import json, sys; from pathlib import Path; '
                'assert not sys.executable; '
                f'sys.path.insert(0, {str(Path(__file__).resolve().parents[1] / "scripts")!r}); '
                'from delm_sdk_observer import observe_sdk; '
                'q = json.load(sys.stdin); '
                'print(json.dumps(observe_sdk(Path(q["run"]), ["alice", "bob"], q["run"], q["client"])))')
        response = subprocess.run(['-python3', '-B', '-c', code], executable=sys.executable,
            input=json.dumps({'run': str(self.run), 'client': str(self.client)}),
            capture_output=True, text=True, timeout=5, check=True)
        result = json.loads(response.stdout)
        self.assertEqual(result['waits']['bob'][0]['items'], ['task-1'])
        self.assertEqual(result['activity'], {'alice': 'running', 'bob': 'idle'})

    def test_work_failed_and_terminal_waits(self):
        original = copy.deepcopy(self.bob_doc()['wait-1'])
        for state in ('waiting', 'failed', 'sent', 'cancelled'):
            with self.subTest(state=state):
                self.bob_doc()['wait-1'] = dict(original, state=state, mode='work', items=[])
                waits = self.observe()['waits']['bob']
                self.assertEqual(len(waits), int(state in ('waiting', 'failed')))
                if waits:
                    self.assertEqual(waits[0]['mode'], 'work')

    def test_manifest_and_client_fences_never_request(self):
        original = copy.deepcopy(self.state)
        cases = [lambda: self.state.update(run='/wrong'),
                 lambda: self.state.update(workspace='/wrong'),
                 lambda: self.state.update(endpoint='http://example.com'),
                 lambda: self.state['actors']['bob'].update(rootId=2),
                 lambda: self.state['actors']['bob'].update(hostId='host-alice'),
                 lambda: self.state['actors'].pop('bob')]
        for mutate in cases:
            with self.subTest(mutate=mutate):
                self.state = copy.deepcopy(original)
                mutate()
                self.save_state()
                self.requests.clear()
                self.assertEqual(self.observe()['waits'], {'alice': None, 'bob': None})
                self.assertEqual(self.requests, [])
        self.state = original
        self.save_state()
        for url in ('http://example.com', self.endpoint + '/path',
                    self.endpoint.replace('http://', 'http://user:pass@'), self.endpoint + '?token=x'):
            self.save(self.client, {'url': url, 'token': 'private-test-token'})
            self.requests.clear()
            self.assertEqual(self.observe()['waits'], {'alice': None, 'bob': None})
            self.assertEqual(self.requests, [])

    def test_bad_or_disabled_binding_is_actor_local(self):
        for patch in ({'actor': 'alice'}, {'workspace': '/wrong'}, {'enabled': False}):
            with self.subTest(patch=patch):
                original = copy.deepcopy(self.bindings)
                self.bindings['sessions']['host-bob'].update(patch)
                self.save_state()
                self.requests.clear()
                result = self.observe()
                self.assertIsNone(result['waits']['bob'])
                self.assertEqual(result['waits']['alice'], [])
                self.assertFalse(any('host-bob' in path for _, path, _ in self.requests))
                self.bindings = original

    def test_wrong_live_identity_does_not_read_document(self):
        for path, field, value in (
                ('/v1/sessions/host-bob', 'cwd', '/wrong'),
                ('/v1/sessions/host-bob', 'id', 'other'),
                ('/v1/sessions/host-bob/agents/1', 'sessionId', 'other'),
                ('/v1/sessions/host-bob/agents/1', 'id', 2),
                ('/v1/sessions/host-bob/agents/1', 'config', {'cwd': '/wrong'})):
            with self.subTest(path=path, field=field):
                original = copy.deepcopy(self.responses[path])
                self.responses[path][1][field] = value
                self.requests.clear()
                result = self.observe()
                self.assertIsNone(result['waits']['bob'])
                self.assertFalse(any('host-bob/agents/1/docs' in p for _, p, _ in self.requests))
                self.responses[path] = original

    def test_malformed_documents_and_offline_are_unknown(self):
        path = '/v1/sessions/host-bob/agents/1/docs/delm.waits'
        valid = copy.deepcopy(self.responses[path])
        for body in ([], None, {'kind': 'other', 'value': {'waits': {}}},
                     {'kind': 'delm.waits', 'value': {'waits': []}},
                     {'kind': 'delm.waits', 'value': {'waits': {'x': {'state': 'future'}}}},
                     {'kind': 'delm.waits', 'value': {'waits': {'x': {'state': 'waiting', 'items': 'wrong'}}}}):
            with self.subTest(body=body):
                self.responses[path] = (200, body)
                result = self.observe()
                self.assertIsNone(result['waits']['bob'])
                self.assertEqual(result['activity']['bob'], 'unknown')
                self.assertEqual(result['waits']['alice'], [])
        for status in (401, 403, 404, 500, 302):
            self.responses[path] = (status, {})
            self.requests.clear()
            self.assertIsNone(self.observe()['waits']['bob'])
            self.assertFalse(any(p == '/redirect-target' for _, p, _ in self.requests))
        self.responses[path] = valid

    def test_interrupted_http_framing_is_actor_local_unknown(self):
        self.responses['/v1/sessions/host-bob/agents/1/docs/delm.waits'] = (200, 'truncated-chunk')
        result = self.observe()
        self.assertIsNone(result['waits']['bob'])
        self.assertEqual(result['waits']['alice'], [])
        self.assertEqual(result['activity']['alice'], 'running')

    def test_slow_progress_has_hard_wall_clock_limit_and_retains_healthy_actor(self):
        self.responses['/v1/sessions/host-bob/agents/1/docs/delm.waits'] = (200, 'slow-body')
        started = time.monotonic()
        result = self.observe()
        self.assertLess(time.monotonic() - started, 4.5)
        self.assertIsNone(result['waits']['bob'])
        self.assertEqual(result['waits']['alice'], [])
        self.assertEqual(result['activity']['alice'], 'running')

    def test_credentials_must_be_private_and_no_symlink(self):
        self.client.chmod(0o644)
        self.assertEqual(self.observe()['waits'], {'alice': None, 'bob': None})
        self.assertEqual(self.requests, [])
        self.client.chmod(0o600)
        linked = self.run / 'linked.json'
        linked.symlink_to(self.client)
        self.client = linked
        self.assertEqual(self.observe()['waits'], {'alice': None, 'bob': None})
        self.assertEqual(self.requests, [])


if __name__ == '__main__':
    unittest.main()
