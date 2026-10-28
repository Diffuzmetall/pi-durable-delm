#!/usr/bin/env python3
"""Focused actual Run.open/Native1.4 probe. Reuses the independently reviewed MODEL-only fixture."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import pty
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native14_fixture", ROOT / "tests/native14-host.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
TOOL = ROOT / "skills/delm/Tools/Run.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--launcher", required=True)
    parser.add_argument("--antigravity-dir", required=True)
    args = parser.parse_args()
    area = Path(tempfile.mkdtemp(prefix="n14l-"))
    workspace = area / "project"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("Synthetic fixture instructions. No live services.\n")
    for name in ("global.md", "plan.md", "prompt.txt"):
        (area / name).write_text("Synthetic approved launcher fixture.\n")
    run = area / "run"
    prepared = subprocess.run([sys.executable, str(TOOL), "prepare", "--workspace", str(workspace),
        "--plan", str(area / "plan.md"), "--prompt-file", str(area / "prompt.txt"),
        "--global-agents", str(area / "global.md"), "--agents", "2", "--run-dir", str(run)],
        capture_output=True, text=True, timeout=30)
    assert prepared.returncode == 0, prepared.stderr
    manifest = json.loads((run / "launch.json").read_text())
    marker = manifest["actors"]["alice"]["marker"]
    paths = fixture.installed_paths(args.launcher)
    proof_file = workspace / "mcp-codemode-proof.txt"
    proof_file.write_text("N14_NATIVE_READ_OK\n")
    code = ("text(await tools.read({path:" + json.dumps(str(proof_file)) + "}));"
            'text(await tools.mcp__fixture__echo({message:"N14_MCP_CODEMODE_OK"}));')
    host = fixture.Native14Host(paths, area / "a", workspace,
        routes={marker: [{"tool": "codemode", "arguments": {"code": code}},
                         {"text": "N14_LAUNCH_BOOT_OK", "expectToolText": "N14_MCP_CODEMODE_OK"}],
                "N14_NOTIFY_APPROVED": [{"text": "N14_LAUNCH_NOTIFY_OK"}]},
        antigravity=args.antigravity_dir,
        mcp_servers={"fixture": {"command": sys.executable, "args": [str(ROOT / "tests/native14-mcp-server.py")]}})
    # Same actual launcher/main, entered THROUGH product open; no modified Native or extra Harness.
    host.command = ["strace", "-f", "-e", "trace=connect", "-o", str(host.trace), sys.executable,
        str(TOOL), "open", "--run-dir", str(run), "--actor", "alice", "--native-executable", str(paths["launcher"])]
    log = (area / "board.log").open("wb")
    board = subprocess.Popen([sys.executable, str(ROOT / "scripts/delm_local.py"), "serve", str(run)],
        stdout=log, stderr=log)
    host.master, slave = pty.openpty()
    host.process = subprocess.Popen(host.command, cwd=workspace, env=host.env,
        stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
    os.close(slave)
    result = {}
    active = [host]
    def cli(action, *extra):
        answer = subprocess.run([sys.executable, str(TOOL), action, "--run-dir", str(run), "--actor", "alice", *extra],
            capture_output=True, text=True, timeout=40)
        if answer.returncode:
            raise RuntimeError(action + " failed: " + answer.stderr)
        return json.loads(answer.stdout)
    try:
        def ready():
            current = json.loads((run / "launch.json").read_text())
            endpoint = current["actors"]["alice"].get("socket")
            return bool(endpoint and Path(endpoint).exists() and b'\x1b[?2004h' in host.raw)
        host.until(ready, "product open / actual registry endpoint and TUI", 45)
        end = time.monotonic() + 10
        while not (run / "endpoint.json").exists():
            if board.poll() is not None or time.monotonic() > end:
                raise RuntimeError("Owned board startup failed")
            host.pump(.03)
        cli("start")
        host.until(lambda: b'N14_LAUNCH_BOOT_OK' in host.raw, "actual approved bootstrap reply")
        identity = json.loads((run / "launch.json").read_text())["actors"]["alice"]["identity"]
        cli("start")  # Same approved request must replay, not another MODEL call.
        draft = "UNSENT_N14_LAUNCH_DRAFT"
        os.write(host.master, draft.encode())
        host.until(lambda: draft.encode() in host.raw, "owned synthetic draft visible")
        update = area / "update.txt"
        update.write_text("N14_NOTIFY_APPROVED\n")
        product_spec = importlib.util.spec_from_file_location("product_launcher", TOOL)
        product = importlib.util.module_from_spec(product_spec)
        product_spec.loader.exec_module(product)
        original_rpc = product.native_rpc
        def lose_launcher_receipt(*values, **options):
            accepted = original_rpc(*values, **options)
            if values[2] == "input":
                assert accepted["accepted"] is True
                raise RuntimeError("Synthetic launcher receipt loss AFTER real Native acceptance")
            return accepted
        with patch.object(product, "native_rpc", side_effect=lose_launcher_receipt):
            try:
                product.control(run, SimpleNamespace(action="notify", actor="alice", input_file=str(update), request_id="same-update"))
            except RuntimeError as failure:
                assert "receipt loss AFTER real Native acceptance" in str(failure)
            else:
                raise AssertionError("Expected injected launcher receipt loss")
        saved_requests = json.loads((run / "launch.json").read_text())["requests"]
        assert any(r["status"] == "pending" for r in saved_requests.values())
        host.until(lambda: b'N14_LAUNCH_NOTIFY_OK' in host.raw, "actual approved notification reply")
        assert draft in host.screen(), "Owned draft no longer visible after external approved input"
        cli("notify", "--input-file", str(update), "--request-id", "same-update")
        update.write_text("Changed N14_NOTIFY_APPROVED\n")
        changed = subprocess.run([sys.executable, str(TOOL), "notify", "--run-dir", str(run), "--actor", "alice",
            "--input-file", str(update), "--request-id", "same-update"], capture_output=True, text=True, timeout=30)
        assert changed.returncode != 0 and 'approval binding changed' in changed.stderr
        assert cli("stop")["results"]["alice"]["stopped"] is True
        assert cli("resume")["results"]["alice"]["resumed"] is True
        requests = [event for event in host.model_events() if event.get("event") == "model_request"]
        assert len(requests) == 3, requests
        assert b'N14_NATIVE_READ_OK' in host.raw and b'N14_MCP_CODEMODE_OK' in host.raw
        result = dict(verdict="ACTUAL_NATIVE14_PRODUCT_OPEN_AND_INPUT_PASS", actualProductOpen=True,
            sdkVersion=identity["sdkVersion"], initialAndNotifyModelCalls=3, liveModelCalls=0,
            actualMcpConnection=True, builtinCodemodeReadAndMcpCall=True,
            replayWithoutExtraModel=True, ambiguousLauncherAcceptanceRecovered=True,
            changedReplayRefused=True, stopResumeWithoutInput=True,
            syntheticDraftVisibleAfterNotify=True, hostConstructedByFixture=False,
            scope="One focused actor; full two-actor wait/readACK/guard/install acceptance remains separate")
        host.close()
        active.remove(host)
        reopened = fixture.Native14Host(paths, area / "r", workspace, routes={}, antigravity=args.antigravity_dir)
        for key in ("HOME", "PI_CODING_AGENT_DIR", "XDG_CONFIG_HOME", "HINDSIGHT_CONFIG"):
            reopened.env[key] = host.env[key]
        reopened.command = ["strace", "-f", "-e", "trace=connect", "-o", str(reopened.trace), sys.executable,
            str(TOOL), "open", "--run-dir", str(run), "--actor", "alice", "--native-executable", str(paths["launcher"])]
        old_socket = json.loads((run / "launch.json").read_text())["actors"]["alice"]["socket"]
        reopened.master, slave = pty.openpty()
        reopened.process = subprocess.Popen(reopened.command, cwd=workspace, env=reopened.env,
            stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        os.close(slave)
        active.append(reopened)
        def reopened_ready():
            record = json.loads((run / "launch.json").read_text())["actors"]["alice"]
            return record.get("socket") != old_socket and Path(record["socket"]).exists() and b'\x1b[?2004h' in reopened.raw
        reopened.until(reopened_ready, "same product open exact-session reopen", 45)
        assert cli("start")["results"]["alice"]["replay"] is True
        assert json.loads((run / "launch.json").read_text())["actors"]["alice"]["identity"] == identity
        assert not [e for e in reopened.model_events() if e.get("event") == "model_request"]
        result.update(exactReopenSameFullIdentity=True, reopenedBootstrapReplayWithoutModel=True)
    finally:
        for owned in reversed(active):
            owned.close()
        board.terminate()
        board.wait(timeout=10)
        log.close()
        (area / "probe-result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"private_owned_area": str(area), **result}))


if __name__ == "__main__":
    main()
