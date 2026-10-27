#!/usr/bin/env python3
"""Real Native/DeLM input+DONE wake with no tern executable or multiplexer environment."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("native14_driver", ROOT / "tests/native14-host.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def main():
    launcher = Path.home() / ".local/bin/pi-durable"
    paths = driver.installed_paths(launcher)
    antigravity = Path.home() / ".pi/agent/npm/node_modules/pi-antigravity"
    area = Path(tempfile.mkdtemp(prefix="n14-no-tern-"))
    node = shutil.which("node")
    binaries = area / "bin"
    binaries.mkdir()
    (binaries / "node").symlink_to(node)
    # Keep system utilities and the actual current Node; deliberately exclude user-local tern.
    os.environ["PATH"] = str(binaries) + ":/usr/bin:/bin"
    assert shutil.which("tern") is None, "Probe environment still has tern"
    workspace = area / "project"
    workspace.mkdir(mode=0o700)
    plan = area / "plan.md"
    plan.write_text("Disposable no-multiplexer DeLM input/wake proof; faux model only.\n")
    run = area / "run"
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/delm_local.py"), "init", str(run),
                             "--shared-workspace", str(workspace), "--n", "2", "--task", "No terminal manager proof",
                             "--plan", str(plan)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    server_log = (area / "board.log").open("w")
    server = subprocess.Popen([sys.executable, "-B", str(ROOT / "scripts/delm_local.py"), "serve", str(run)],
                              stdout=server_log, stderr=server_log)
    try:
        deadline = time.monotonic() + 10
        while not (run / "endpoint.json").exists():
            assert server.poll() is None, "Board exited"
            assert time.monotonic() < deadline, "Board startup timed out"
            select.select([], [], [], .03)

        def board(actor, payload):
            response = subprocess.run([str(run / actor / "bin/context"), "domain", json.dumps(payload)],
                                      capture_output=True, text=True, timeout=15)
            assert response.returncode == 0, response.stderr + response.stdout
            value = json.loads(response.stdout)
            assert "error" not in value, value
            return value

        board_port = urlsplit(json.loads((run / "endpoint.json").read_text())["url"]).port
        task = board("bob", dict(op="create", request_id="no-tern-task-create", subject="No Tern DONE output",
                                 detail="Synthetic output for actual Native wake proof", deps=[], criteria=["Fixture output"]))["task"]
        socket_directory = area / "private-control"
        socket_directory.mkdir(mode=0o700)
        control = socket_directory / "alice.sock"
        adapter = area / "actor.mjs"
        adapter.write_text("import install from " + json.dumps((ROOT / "extensions/delm/native14.js").as_uri()) +
                           "; export default base => install(base, " + json.dumps(dict(run=str(run), actor="alice", controlSocket=str(control))) + ");\n")
        marker, armed, woke = "NO_TERN_APPROVED_INPUT", "NO_TERN_WAIT_ARMED", "NO_TERN_DONE_WAKE_RECEIVED"
        routes = {marker: [dict(tool="delm_wait", arguments=dict(action="wait", items=[task["id"]], reason="No Tern runtime proof")),
                           dict(text=armed)], "[delm]": [dict(text=woke)]}
        production = [ROOT / "extensions/delm" / name for name in ("native14.js", "native14-owner.js", "index.js", "protocol.js")]
        hashes = {p.relative_to(ROOT).as_posix(): driver.digest(p) for p in production}
        host = driver.Native14Host(paths, area / "native", workspace, extensions=[adapter], routes=routes, antigravity=antigravity)
        host.command[host.command.index("trace=connect")] = "trace=connect,execve"
        assert not any(k.startswith(("TERN_", "HERDR_")) or k == "TMUX" for k in host.env)

        def control_rpc(method, **payload):
            with socket.socket(socket.AF_UNIX) as client:
                client.settimeout(25)
                client.connect(str(control))
                client.sendall((json.dumps(dict(id="no-tern-" + method, method=method, **payload)) + "\n").encode())
                body = b""
                while b"\n" not in body:
                    chunk = client.recv(65536)
                    assert chunk, "Control disconnected"
                    body += chunk
            response = json.loads(body.split(b"\n", 1)[0])
            assert response["ok"], response
            return response["result"]

        with host:
            assert host.request("attach", cwd=str(workspace))["success"]
            identity = control_rpc("identity")["identity"]
            approved = dict(identity=identity, type="input", requestId="no-tern-stable-approved-v1", text=marker,
                            expectedSha256=hashlib.sha256(marker.encode()).hexdigest())
            assert control_rpc("input", **approved)["accepted"]
            host.wait_history(armed)
            assert control_rpc("input", **approved)["accepted"]
            claimed = board("bob", dict(op="claim", request_id="no-tern-task-claim", item=task["id"], expected_revision=task["revision"]))["task"]
            board("bob", dict(op="complete", request_id="no-tern-task-done", item=task["id"], expected_revision=claimed["revision"],
                              generation=claimed["generation"], summary="Synthetic early output complete"))
            host.wait_history(woke)
            events = host.model_events()
            calls = [e for e in events if e["event"] == "model_request"]
            assert len(calls) == 3, calls
            assert all(driver.digest(ROOT / p) == h for p, h in hashes.items()), "Candidate changed during proof"
        assert host.exit_code == 0
        trace = host.trace.read_text()
        executables = re.findall(r'execve\("([^\"]+)"', trace)
        forbidden = [p for p in executables if Path(p).name in ("tern", "tmux", "herdr")]
        assert not forbidden, forbidden
        inet_rows = [line for line in trace.splitlines() if re.search(r"connect\(.*AF_INET6?[, ]", line)]
        unexpected_network = [line for line in inet_rows
                              if f"sin_port=htons({board_port})" not in line or 'inet_addr("127.0.0.1")' not in line]
        assert not unexpected_network, unexpected_network
        report = dict(schema=1, verdict="ACTUAL_NATIVE14_DELM_NO_TERN_PASS", ternDiscoverable=False,
                      multiplexerEnvironment=False, multiplexerExecAttempts=forbidden,
                      actualInstalledNative=True, actualDeLMRegistry=True, realBoard=True,
                      stableApprovedInput=True, sameRequestReplay=True, exactDoneWake=True,
                      nativeCleanExit=True, modelCalls=len(calls), liveModelCalls=0,
                      loopbackBoardConnects=len(inet_rows), unexpectedInetConnects=0,
                      executableBasenames=sorted({Path(p).name for p in executables}), productionHashes=hashes,
                      testDriverSha256=driver.digest(Path(__file__)), personalSessionsChanged=False,
                      finalLauncherEndToEnd="NOT_TESTED_BY_THIS_COMPONENT_PROBE")
        evidence = ROOT / "docs/evidence/native14/packaging/no-tern-runtime.json"
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        server.terminate()
        server.wait(timeout=10)
        server_log.close()


if __name__ == "__main__":
    main()
