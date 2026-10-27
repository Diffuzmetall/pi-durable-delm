#!/usr/bin/env python3
"""Run the PRODUCT launcher against an isolated actual existing Native server; deterministic MODEL only."""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import selectors
import select
import pty
import struct
import termios
import time
import signal
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/host"))
from deterministic_provider import DeterministicProvider
from native_process import NativeProcess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True, help="Released disposable PUBLIC Native fixture, never author runtime")
    args = parser.parse_args()
    original = json.loads(args.fixture.read_text())
    sandbox = args.fixture.resolve().parent
    # Native also creates a control-UUID.sock: keep the complete Unix path below 108 bytes.
    area = sandbox / ("cl-" + uuid.uuid4().hex[:6])
    area.mkdir(mode=0o700)
    fixture = dict(original)
    for key, leaf in (("home", "h"), ("project", "p"), ("evidence", "e")):
        fixture[key] = str(sandbox / ("c" + uuid.uuid4().hex[:2])) if key == "home" else str(area / leaf)
        Path(fixture[key]).mkdir(mode=0o700)
    longest_endpoint = Path(fixture["home"]) / ".pi/server" / ("server-" + str(uuid.uuid4()) + "-0123456789ab.sock")
    assert len(os.fsencode(longest_endpoint)) < 108, "Fixture Unix backend socket path is too long"
    fixture["env"] = original["env"] | {"HOME": fixture["home"],
        "PI_CODING_AGENT_DIR": str(Path(fixture["home"]) / ".pi/agent")}
    # Same common sandbox preserves NativeProcess's source-isolation guard. All mutable data is new/actor-local.
    locator = sandbox / (area.name + "-fixture.json")
    locator.write_text(json.dumps(fixture))
    locator.chmod(0o600)
    source = Path(fixture["source"])
    assert source.resolve().is_relative_to(sandbox)
    provenance = json.loads((Path(original["evidence"]) / "public-host-discovery.json").read_text())
    assert provenance["revision"] == "cd32f7725fdbddbaecdff5b1e68491563394e0ca"
    changed = {file for file, expected in provenance["source_hashes"].items()
               if hashlib.sha256((source / file).read_bytes()).hexdigest() != expected}
    assert changed == {"packages/coding-agent/src/experimental/" + file for file in
                       ("session-worker.ts", "services/worker.ts", "plugin.ts")}, changed
    project = Path(fixture["project"])
    for name, body in {"AGENTS.md": "Synthetic launcher project, no publication.\n", "Plan.md": "Verify exact Native sessions only.\n"}.items():
        (project / name).write_text(body)
    global_rules, approved = area / "GlobalAgents.md", area / "approved.txt"
    global_rules.write_text("Read all rules; no live models, publication or extra agents.\n")
    approved.write_text("Synthetic approved launcher task; deterministic provider only.\n")
    run = area / "run"
    script = ROOT / "skills/delm/Tools/Run.py"
    output = ROOT / "tests/launcher/host-evidence/real-native"
    output.mkdir(parents=True, exist_ok=True)
    server_id = str(uuid.uuid4())
    sessions = area / "sessions"
    host = NativeProcess(locator, server_id=server_id, session_directory=sessions, plugins=[ROOT])
    # TEST environment supplies the matching existing PUBLIC client packages; product needs no source flag.
    public_peer_resolver = " --import=" + (source / "packages/coding-agent/src/experimental/source-resolver.ts").as_uri()
    host.env["NODE_OPTIONS"] += public_peer_resolver
    def cli(arguments, label, *, success=True):
        result = subprocess.run([sys.executable, "-B", str(script), *arguments], env=host.env,
            cwd=project, capture_output=True, text=True, timeout=150)
        (output / (label + ".log")).write_text(host.redact(result.stdout + result.stderr))
        assert (result.returncode == 0) == success, label + ": " + host.redact(result.stderr)[-2000:]
        return json.loads(result.stdout) if success else None
    cli(["prepare", "--workspace", str(project), "--global-agents", str(global_rules), "--plan", str(project / "Plan.md"),
        "--prompt-file", str(approved), "--agents", "2", "--run-dir", str(run)], "prepare")
    board = subprocess.Popen([sys.executable, "-B", str(ROOT / "scripts/delm_local.py"), "serve", str(run)],
        cwd=project, env=host.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    selector.register(board.stdout, selectors.EVENT_READ)
    def observe(update=False):
        result = host.probe(Path(__file__).with_name("probe_native_launcher.mjs"),
            {"DELM_LAUNCHER_MANIFEST": str(run / "launch.json"), "DELM_LAUNCHER_EXPECT_UPDATE": "yes" if update else "no",
             "DELM_LAUNCHER_FORBIDDEN_DRAFT": "UNSENT_LAUNCHER_DRAFT_731"})
        (output / ("observe-update.log" if update else "observe-bootstrap.log")).write_text(host.redact(result.stdout + result.stderr))
        assert result.returncode == 0, host.redact(result.stderr)[-2000:]
        return json.loads(result.stdout)
    try:
        assert selector.select(15), "Owned board server did not start"
        board.stdout.readline()
        with DeterministicProvider([{"text": "HOST_FIXTURE_ACK"}, {"text": "HOST_FIXTURE_ACK"},
                                    {"text": "NATIVE_LAUNCHER_NOTIFY_ACK"}]) as provider:
            agent = Path(host.env["PI_CODING_AGENT_DIR"])
            agent.mkdir(parents=True, exist_ok=True)
            (agent / "models.json").write_text(json.dumps(provider.models_config()))
            with host:
                baseline = host.probe(Path(__file__).with_name("probe_native_management.mjs"))
                (output / "same-server-official-client.log").write_text(host.redact(baseline.stdout + baseline.stderr))
                assert baseline.returncode == 0, host.redact(baseline.stderr)[-2000:]
                start = ["start", "--run-dir", str(run), "--socket", str(host.socket)]
                loss = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("lose_native_response.py")), *start],
                    cwd=project, env=host.env, capture_output=True, text=True, timeout=120)
                (output / "actual-accepted-response-loss.log").write_text(host.redact(loss.stdout + loss.stderr))
                assert loss.returncode == 42, host.redact(loss.stderr)[-2000:]
                pending = json.loads((run / "launch.json").read_text())
                assert len(pending["requests"]) == 1 and next(iter(pending["requests"].values()))["status"] == "pending"
                first = cli(start, "start")
                assert first["results"]["alice"]["replay"] is True
                initial = json.loads((run / "launch.json").read_text())
                observed = observe()
                assert provider.requests == 2
                replay = cli(start, "repeat-start")
                assert all(result["replay"] for result in replay["results"].values())
                assert provider.requests == 2
                saved_manifest = (run / "launch.json").read_bytes()
                missing = json.loads(saved_manifest)
                missing_id = str(uuid.uuid4())
                missing["actors"]["alice"]["session"] = missing_id
                missing["actors"]["alice"]["identity"]["sessionId"] = missing_id
                (run / "launch.json").write_text(json.dumps(missing))
                try:
                    cli(start + ["--actor", "alice"], "missing-recorded-session-refused", success=False)
                    directory = host.probe(Path(__file__).with_name("probe_native_management.mjs"))
                    assert directory.returncode == 0 and json.loads(directory.stdout)["existingSessionCount"] == 2
                finally:
                    (run / "launch.json").write_bytes(saved_manifest)
                update = area / "update.txt"
                update.write_text("NATIVE_LAUNCHER_UPDATE approved exact original text\n")
                notify = ["notify", "--run-dir", str(run), "--actor", "alice", "--input-file", str(update), "--request-id", "original-update"]
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 38, 120, 0, 0))
                command = host.base + [str(host.source / "packages/coding-agent/src/experimental/cli.ts"), "client",
                    "--connect", "unix://" + str(host.socket), "--session-id", initial["actors"]["alice"]["session"]]
                terminal = subprocess.Popen(command, cwd=project, env=host.env | {"TERM": "xterm-256color"},
                    stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
                os.close(slave)
                transcript = b""
                def screen_until(predicate):
                    nonlocal transcript
                    deadline = time.monotonic() + 25
                    while time.monotonic() < deadline:
                        assert terminal.poll() is None, "Actual Native editor exited"
                        if not select.select([master], [], [], .2)[0]:
                            continue
                        chunk = os.read(master, 65536)
                        transcript += chunk
                        if b"\x1b[6n" in chunk:
                            os.write(master, b"\x1b[1;1R")
                        screen = subprocess.run(host.base + [str(ROOT / "tests/host/decode_native_screen.mjs")],
                            input=base64.b64encode(transcript).decode(), capture_output=True, text=True,
                            env=host.env | {"DELM_PUBLIC_HOST_SOURCE": str(source)}, timeout=10)
                        assert screen.returncode == 0, host.redact(screen.stderr)
                        text = "\n".join(json.loads(screen.stdout))
                        if predicate(text):
                            return host.redact(text)
                    raise AssertionError("Actual Native editor screen timed out")
                try:
                    screen_until(lambda text: "HOST_FIXTURE_ACK" in text)
                    os.write(master, b"\x1b[200~UNSENT_LAUNCHER_DRAFT_731\x1b[201~")
                    before = screen_until(lambda text: "UNSENT_LAUNCHER_DRAFT_731" in text)
                    (output / "editor-before-notify.txt").write_text(before)
                    assert provider.requests == 2, "Typing draft submitted a model input"
                    cli(notify, "notify")
                    after = screen_until(lambda text: "UNSENT_LAUNCHER_DRAFT_731" in text and "NATIVE_LAUNCHER_NOTIFY_ACK" in text)
                    (output / "editor-after-notify.txt").write_text(after)
                    observe(True)
                    assert provider.requests == 3
                finally:
                    if terminal.poll() is None:
                        os.write(master, b"\x03")
                    try:
                        terminal.wait(timeout=6)
                    except subprocess.TimeoutExpired:
                        terminal.terminate()
                        terminal.wait(timeout=10)
                    os.close(master)
                    (output / "editor-transcript.log").write_text(host.redact(transcript.decode(errors="replace")))
                assert terminal.returncode == 0
                update.write_text("different approved payload under same ID\n")
                cli(notify, "changed-notify-refused", success=False)
                cli(["stop", "--run-dir", str(run)], "stop")
                assert provider.requests == 3
            assert host.process.returncode == 0
            host = NativeProcess(locator, server_id=server_id, session_directory=sessions, plugins=[ROOT], log="restart.log")
            host.env["NODE_OPTIONS"] += public_peer_resolver
            with host:
                cli(["resume", "--run-dir", str(run)], "resume-exact-after-restart")
                status = cli(["status", "--run-dir", str(run)], "status-after-restart")
                assert all(value["stopped"] is False for value in status["native_sessions"].values())
                observe(True)
                after = json.loads((run / "launch.json").read_text())
                assert {a: r["identity"] for a, r in initial["actors"].items()} == {a: r["identity"] for a, r in after["actors"].items()}
                assert provider.requests == 3, "Resume/restart re-enqueued input"
                cli(["stop", "--run-dir", str(run)], "final-stop")
            assert host.process.returncode == 0
            result = dict(actual_existing_native=True, source_variant="explicit three-file public API patch",
                product_launcher=True, public_client_libraries_only=True, product_host_source_flag=False, exact_two_sessions=True,
                duplicate_start_no_extra_input=True, actual_accepted_response_loss_reconciled=True,
                changed_notify_refused=True, missing_recorded_session_not_recreated=True, restart_exact_instances=True,
                resume_without_input=True, stop_confirmed=True, deterministic_http_requests=provider.requests,
                live_model_calls=0, editor_draft="ACTUAL Native CLI OS PTY: unsent draft retained during product notify; absent from both histories; no editor Enter", 
                observed=observed)
            (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result))
    finally:
        selector.close()
        if board.poll() is None:
            board.send_signal(signal.SIGTERM)
        stdout, stderr = board.communicate(timeout=10)
        (output / "board.log").write_text(host.redact((stdout + stderr).decode(errors="replace")))


if __name__ == "__main__":
    main()
