#!/usr/bin/env python3
"""Real Native CLI PTY checks; shared by plain Native and actual DeLM-event integration."""
import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import termios
import time
from deterministic_provider import DeterministicProvider
from native_process import NativeProcess


class NativeTerminal:
    def __init__(self, host, session_id, output):
        self.host, self.session_id, self.output = host, session_id, Path(output)
        self.transcript, self.screen = b"", ""

    def __enter__(self):
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 38, 120, 0, 0))
        command = self.host.base + [str(self.host.source / "packages/coding-agent/src/experimental/cli.ts"), "client",
            "--connect", "unix://" + str(self.host.socket), "--session-id", self.session_id]
        self.process = subprocess.Popen(command, cwd=self.host.fixture["project"], env=self.host.env | {"TERM": "xterm-256color"},
            stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        os.close(slave)
        return self

    def paste(self, text):
        assert "\n" not in text and "\r" not in text, "This fixture never sends editor Enter"
        os.write(self.master, b"\x1b[200~" + text.encode() + b"\x1b[201~")

    def wait_screen(self, predicate):
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if self.screen and predicate(self.screen):
                return self.host.redact(self.screen)
            assert self.process.poll() is None, "Actual Native TUI exited unexpectedly"
            if not select.select([self.master], [], [], .2)[0]:
                continue
            chunk = os.read(self.master, 65536)
            self.transcript += chunk
            if b"\x1b[6n" in chunk:
                os.write(self.master, b"\x1b[1;1R")
            decoded = subprocess.run(self.host.base + [str(Path(__file__).with_name("decode_native_screen.mjs"))],
                input=base64.b64encode(self.transcript).decode(), text=True, capture_output=True,
                env=self.host.env | {"DELM_PUBLIC_HOST_SOURCE": str(self.host.source)}, timeout=10)
            assert decoded.returncode == 0, self.host.redact(decoded.stderr)
            self.screen = "\n".join(json.loads(decoded.stdout))
        raise AssertionError("Actual Native screen condition timed out; see tui-transcript.log")

    def __exit__(self, error_type, *_):
        if self.process.poll() is None:
            os.write(self.master, b"\x03")
        try:
            self.process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)
        os.close(self.master)
        (self.output / "tui-transcript.log").write_text(self.host.redact(self.transcript.decode(errors="replace")))
        if error_type is None:
            assert self.process.returncode == 0, self.process.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    host = NativeProcess(args.fixture, session_directory=args.fixture.resolve().parent / "native-draft-sessions", log="native-draft/server.log")
    host.assert_original_source()
    output = host.evidence / "native-draft"
    output.mkdir(exist_ok=True)
    state = host.sandbox / "native-draft-state.json"
    draft = "UNSENT_NATIVE_EDITOR_DRAFT_731"
    phases = []
    with DeterministicProvider([{"text":"HOST_FIXTURE_ACK"},{"text":"HOST_FIXTURE_ACK"},{"text":"NATIVE_DRAFT_WAKE_ACK"}]) as provider:
        agent = Path(host.env["PI_CODING_AGENT_DIR"])
        agent.mkdir(parents=True, exist_ok=True)
        (agent / "models.json").write_text(json.dumps(provider.models_config()))
        with host:
            def probe(phase):
                client = host.probe(Path(__file__).with_name("probe_native_lifecycle.mjs"), {
                    "DELM_NATIVE_LIFECYCLE_PHASE":phase,"DELM_NATIVE_LIFECYCLE_STATE":str(state),"DELM_NATIVE_FORBIDDEN_DRAFT":draft})
                (output / f"{phase}-client.log").write_text(host.redact(client.stdout + client.stderr))
                assert client.returncode == 0, f"Actual Native {phase} failed; see logs"
                phases.append(json.loads(client.stdout))
            probe("create")
            session_id = json.loads(state.read_text())[0]["sessionId"]
            with NativeTerminal(host, session_id, output) as terminal:
                terminal.wait_screen(lambda s:"HOST_FIXTURE_ACK" in s)
                terminal.paste(draft)
                (output / "before-wake-screen.txt").write_text(terminal.wait_screen(lambda s:draft in s))
                assert provider.requests == 2
                probe("wake")
                (output / "after-wake-screen.txt").write_text(terminal.wait_screen(lambda s:draft in s and "NATIVE_DRAFT_WAKE_ACK" in s))
                probe("resume")
                assert provider.requests == 3
        assert host.process.returncode == 0
        result = dict(schema=1,host="Actual public Native CLI server AND client TUI",version="1.0.2",
            revision="cd32f7725fdbddbaecdff5b1e68491563394e0ca",source_modified=False,
            terminal="real OS PTY; upstream VirtualTerminal/xterm decodes actual bytes",draft_visible_before=True,
            actual_external_prompt_completed=True,draft_visible_after=True,draft_absent_from_both_real_histories=True,
            editor_enter_sent=False,deterministic_model_http_requests=provider.requests,live_model_calls=0,
            native_server_exit=0,native_tui_exit=0,delm_plugin="NOT_YET_TESTED",phases=phases)
        (output / "result.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result))


if __name__ == "__main__":
    main()
