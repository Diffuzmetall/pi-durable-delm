"""Run the official Native CLI in a previously provisioned disposable public-source fixture."""
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time
import uuid


class NativeProcess:
    def __init__(self, fixture_path, *, server_id=None, session_directory=None, plugins=None, log="native-process.log"):
        self.fixture_path = Path(fixture_path).resolve()
        self.sandbox = self.fixture_path.parent
        self.fixture = json.loads(self.fixture_path.read_text())
        self.source = Path(self.fixture["source"])
        # Never accidentally launch the author's host through a fixture locator.
        for name in ("source", "home", "project"):
            assert Path(self.fixture[name]).resolve().is_relative_to(self.sandbox), name
        self.evidence = Path(self.fixture["evidence"])
        self.env = self.fixture["env"] | {"PI_EXPERIMENTAL": "1", "PI_OFFLINE": "1", "PI_TELEMETRY": "0",
            "NODE_OPTIONS": "--import=" + Path(__file__).with_name("public-dependencies.mjs").resolve().as_uri()}
        self.server_id = server_id or str(uuid.uuid4())
        self.socket = Path(self.fixture["home"]) / ".pi/server" / (self.server_id + ".sock")
        self.sessions = Path(session_directory or self.sandbox / "native-sessions")
        assert self.sessions.resolve().is_relative_to(self.sandbox), "Only disposable fixture sessions may be opened"
        self.base = ["node", "--import", str(self.source / "packages/coding-agent/src/experimental/source-resolver.ts")]
        self.command = self.base + [str(self.source / "packages/coding-agent/src/experimental/cli.ts"), "server",
            "--server-id", self.server_id, "--session-dir", str(self.sessions), "--provider", "fixture", "--model", "deterministic"]
        for plugin in plugins or [self.source / "packages/coding-agent/examples/plugins/pi-example-plugin"]:
            self.command += ["-e", str(plugin)]
        self.log = log
        self.transcript = b""

    def assert_original_source(self):
        provenance = json.loads((self.evidence / "public-host-discovery.json").read_text())
        assert provenance["revision"] == "cd32f7725fdbddbaecdff5b1e68491563394e0ca"
        for path, expected in provenance["source_hashes"].items():
            assert hashlib.sha256((self.source / path).read_bytes()).hexdigest() == expected, "Not an unmodified Native fixture: " + path

    def redact(self, text):
        for original, replacement in [(str(self.sandbox), "<SANDBOX>"),
                (str(Path(__file__).resolve().parents[2]), "<TARGET>"),
                *[(p, "<PUBLIC_DEPENDENCIES>") for p in self.env["DELM_HOST_DEPENDENCY_ROOTS"].split(os.pathsep)]]:
            text = text.replace(original, replacement)
        return text

    def __enter__(self):
        self.process = subprocess.Popen(self.command, cwd=self.fixture["project"], env=self.env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + 30
        try:
            while b"Socket:" not in self.transcript:
                if time.monotonic() > deadline or self.process.poll() is not None:
                    raise RuntimeError("Native CLI startup failed: " + self.redact(self.transcript.decode(errors="replace")))
                for key, _ in self.selector.select(.2):
                    self.transcript += os.read(key.fileobj.fileno(), 65536)
            return self
        except BaseException:
            self.__exit__()
            raise

    def probe(self, path, extra_env=None):
        env = self.env | {"DELM_PUBLIC_HOST_SOURCE": str(self.source), "DELM_PUBLIC_HOST_SOCKET": str(self.socket)} | (extra_env or {})
        return subprocess.run(self.base + [str(Path(path).resolve())], cwd=self.fixture["project"], env=env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=70)

    def __exit__(self, *_):
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
        try:
            self.transcript += self.process.communicate(timeout=12)[0]
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.transcript += self.process.communicate(timeout=10)[0]
        self.selector.close()
        (self.evidence / self.log).write_text(self.redact(self.transcript.decode(errors="replace")))
