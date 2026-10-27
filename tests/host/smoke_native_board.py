#!/usr/bin/env python3
"""Actual existing Native host + DeLM plugin + real board/actor CLI; only the HTTP MODEL is deterministic."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import selectors
import shlex
import signal
import subprocess
import threading
import time
import traceback
import uuid
from deterministic_provider import DeterministicProvider
from native_process import NativeProcess
from smoke_native_draft import NativeTerminal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    sandbox = args.fixture.resolve().parent
    target = Path(__file__).resolve().parents[2]
    policy = sandbox / ("existing-owner-policy-" + uuid.uuid4().hex[:8])
    policy.mkdir()
    (policy / "session.mjs").write_bytes(Path(__file__).with_name("owner-policy-facet.mjs").read_bytes())
    (policy / "package.json").write_text(json.dumps(dict(name="fixture-existing-owner-policy", version="0.0.0", type="module", private=True,
        peerDependencies={p:"1.0.2" for p in ("@earendil-works/chord","@earendil-works/pi-durable","@earendil-works/pi-coding-agent")},
        chord=dict(facets=dict(session="./session.mjs"),external=["@earendil-works/pi-coding-agent/experimental/plugin"]))))
    runtime_files=("package.json","extensions/delm/session-facet.js","extensions/delm/control.js","extensions/delm/index.js","extensions/delm/protocol.js","skills/delm/Tools/NativeInput.mjs")
    runtime_hashes={p:hashlib.sha256((target/p).read_bytes()).hexdigest() for p in runtime_files}
    run = sandbox / ("native-board-run-" + uuid.uuid4().hex[:8])
    host = NativeProcess(args.fixture, plugins=[target,policy], session_directory=sandbox / "native-board-sessions", log="board-e2e/server.log")
    output = host.evidence / "board-e2e"
    output.mkdir(exist_ok=True)
    subprocess.run(["python3", "-B", str(target / "scripts/delm_local.py"), "init", str(run),
                    "--shared-workspace", fixture["project"], "--n", "2", "--task", "Actual Native DeLM integration"],
                   cwd=fixture["project"], env=host.env, check=True, capture_output=True)
    board = subprocess.Popen(["python3", "-B", str(target / "scripts/delm_local.py"), "serve", str(run)],
        env=host.env, cwd=fixture["project"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    selector.register(board.stdout, selectors.EVENT_READ)
    try:
        assert selector.select(15), "Actual board did not become ready"
        board.stdout.readline()  # Own loopback URL, not tokens/config.
        def domain(actor, payload):
            r = subprocess.run([str(run / actor / "bin/context"), "domain", json.dumps(payload)],
                               env=host.env, capture_output=True, text=True)
            if r.returncode:
                message = host.redact(r.stdout + r.stderr)
                (output / "domain-setup-error.log").write_text(message)
                raise RuntimeError(message[-2000:])
            return json.loads(r.stdout)
        tasks = [domain("alice", dict(op="create", request_id=f"native-create-{i}", subject=f"native output {i}", detail="Actual Native integration output"))["task"] for i in range(2)]
        claims = []
        for actor, task in zip(("alice", "bob"), tasks):
            request = dict(op="claim", request_id=f"native-claim-{actor}", item=task["id"], expected_revision=task["revision"])
            claims.append(dict(request=request, result=domain(actor, request)["task"]))
        result_file = Path(fixture["project"]) / (run.name + "-result.txt")
        scenario = dict(run=str(run), workspace=fixture["project"], items=[t["id"] for t in tasks], resultFile=str(result_file),
                        workRecord=str(Path(fixture["project"])/(run.name+"-work.json")))
        sync=sandbox/(run.name+"-ui-sync")
        sync.mkdir()
        scenario.update(uiSession=str(sync/"session.json"),uiDraftReady=str(sync/"draft-ready"),
                        uiWakeVerified=str(sync/"wake-verified"),uiDraft="UNSENT_DELM_EVENT_DRAFT_731",policySource=str(policy/"session.mjs"))
        ui_output=output/"tui"
        ui_output.mkdir(exist_ok=True)
        scenario_path = sandbox / "native-board-scenario.json"
        scenario_path.write_text(json.dumps(scenario))
        def command(actor, phase):
            common = f"""import json,subprocess
from pathlib import Path
cli={str(run / actor / 'bin/context')!r}
def d(p): return json.loads(subprocess.check_output([cli,'domain',json.dumps(p)],text=True))
"""
            if phase in ("first", "second"):
                index = 0 if phase == "first" else 1
                # Replay the fixture's initial stable claim; owners do not change while exact wait is armed.
                body = f"claim=d({claims[index]['request']!r})['task']\n"
                if phase == "first":
                    body += f"Path({str(result_file)!r}).write_text('actual Native producer result\\n')\n"
                body += f"result=d(dict(op='complete',request_id='native-complete-{actor}',item=claim['id'],expected_revision=claim['revision'],generation=claim['generation'],summary='actual Native tool result'))\nprint(json.dumps(dict(completed=result['task']['id'],state=result['task']['state'])))\n"
            elif phase == "new-work":
                body = "r=d(dict(op='create',request_id='native-new-work',subject='available Native work',detail='actual work hint, not assignment'))\n"
                body += f"Path({scenario['workRecord']!r}).write_text(json.dumps(r['task']))\nprint(json.dumps(dict(created=r['task']['id'])))\n"
            elif phase == "after-cancel":
                body = f"t=json.loads(Path({scenario['workRecord']!r}).read_text())\n"
                body += "r=d(dict(op='publish',request_id='native-fact-after-cancel',type='FACT',task=t['id'],text='FACT is not DONE; cancelled wait must not resume'))\nprint(json.dumps(dict(factPublished=True)))\n"
            else:
                body = f"pending=d(dict(op='pending',request_id={('pending-'+phase)!r}))['receipts']\nassert len(pending)==1,pending\nr=pending[0]\ns=d(dict(op='snapshot',request_id=r['request_id']))\nassert s['receipt_id']==r['receipt_id']\n"
                body += f"needed={scenario['items']!r}\nassert all(next(t for t in s['view']['queue'] if t['id']==i)['state']=='done' for i in needed)\n"
                body += f"w=Path({scenario['workRecord']!r})\nif w.exists():\n t=json.loads(w.read_text())\n q=next(x for x in s['view']['queue'] if x['id']==t['id'])\n assert q['state']=='open' and q['owner'] is None\n"
                body += f"a=d(dict(op='ack',request_id=r['request_id']+':ack',receipt_id=r['receipt_id']))\nassert a['acked_sequence']==s['to_sequence']\nassert not d(dict(op='pending',request_id={('pending-after-'+phase)!r}))['receipts']\nprint(json.dumps(dict(actualSnapshotRead=True,actualExplicitAck=True,receipt_id=r['receipt_id'])))\n"
            return "python3 -B -c " + shlex.quote(common + body)
        counts = {}
        def responder(request):
            last_user = next(m for m in reversed(request["messages"]) if m["role"] == "user")
            text = json.dumps(last_user["content"])
            markers=("NATIVE_BOB_WAIT_TWO","NATIVE_ALICE_FIRST","NATIVE_BOB_SECOND","NATIVE_OWNER_GUARD_PROBE",
                     "NATIVE_BOB_WORK","NATIVE_ALICE_NEW_WORK","NATIVE_BOB_CANCEL_ARM","NATIVE_BOB_CANCEL_NOW","NATIVE_ALICE_AFTER_CANCEL")
            key=next((k for k in markers if k in text),None)
            if key is None:
                reference=re.search(r'delm-wake:[0-9]+(?::work:[0-9]+)?',text)
                assert reference, "Unexpected deterministic model input, not an actual wake reference"
                key=("wake-work:" if "WORK AVAILABLE" in text else "wake-exact:")+reference.group()
            count = counts.get(key, 0)
            counts[key] = count + 1
            if key == "NATIVE_BOB_WAIT_TWO":
                return dict(tool="delm_wait", arguments=dict(action="wait", items=scenario["items"], reason="wait for BOTH stable owned outputs")) if count == 0 else dict(text="NATIVE_WAIT_ARMED")
            if key == "NATIVE_OWNER_GUARD_PROBE":
                return dict(tool="delm_wait",arguments=dict(action="work",reason="actual existing owner policy must block this")) if count == 0 else dict(text="NATIVE_OWNER_GUARD_ACK")
            if key == "NATIVE_BOB_WORK":
                return dict(tool="delm_wait",arguments=dict(action="work",reason="actual available work hint")) if count==0 else dict(text="NATIVE_WORK_ARMED")
            if key == "NATIVE_ALICE_NEW_WORK":
                return dict(tool="bash",arguments=dict(command=command("alice","new-work"))) if count==0 else dict(text="NATIVE_NEW_WORK_CREATED")
            if key == "NATIVE_BOB_CANCEL_ARM":
                task=json.loads(Path(scenario["workRecord"]).read_text())
                return dict(tool="delm_wait",arguments=dict(action="wait",items=[task["id"]],reason="cancel this exact wait")) if count==0 else dict(text="NATIVE_CANCEL_ARMED")
            if key == "NATIVE_BOB_CANCEL_NOW":
                wait_id=re.search(r'NATIVE_BOB_CANCEL_NOW ([a-f0-9]{64})',text).group(1)
                return dict(tool="delm_wait",arguments=dict(action="cancel",id=wait_id)) if count==0 else dict(text="NATIVE_CANCELLED")
            if key == "NATIVE_ALICE_AFTER_CANCEL":
                return dict(tool="bash",arguments=dict(command=command("alice","after-cancel"))) if count==0 else dict(text="NATIVE_FACT_AFTER_CANCEL")
            if key in ("NATIVE_ALICE_FIRST", "NATIVE_BOB_SECOND"):
                first = key == "NATIVE_ALICE_FIRST"
                return dict(tool="bash", arguments=dict(command=command("alice" if first else "bob", "first" if first else "second"))) if count == 0 else dict(text="NATIVE_FIRST_DONE" if first else "NATIVE_SECOND_DONE")
            if count == 0:
                return dict(tool="bash", arguments=dict(command=command("bob", "ack-"+key)))
            if count == 1:
                return dict(tool="delm_wait", arguments=dict(action="status"))
            return dict(text="NATIVE_WORK_ACKED" if key.startswith("wake-work:") else "NATIVE_WAKE_ACKED")
        with DeterministicProvider(responder) as provider:
            agent = Path(host.env["PI_CODING_AGENT_DIR"])
            agent.mkdir(parents=True, exist_ok=True)
            (agent / "models.json").write_text(json.dumps(provider.models_config()))
            phases = {}
            for phase in ("arm", "finish"):
                if phase == "finish":
                    host = NativeProcess(args.fixture, server_id=host.server_id, plugins=[target,policy],
                        session_directory=sandbox / "native-board-sessions", log="board-e2e/restarted-server.log")
                with host:
                    errors=[]
                    stopped=threading.Event()
                    def check_editor():
                        try:
                            deadline=time.monotonic()+25
                            while not Path(scenario["uiSession"]).exists():
                                if stopped.wait(.05): return
                                assert time.monotonic()<deadline,"Native UI session checkpoint missing"
                            sid=json.loads(Path(scenario["uiSession"]).read_text())["sessionId"]
                            with NativeTerminal(host,sid,ui_output) as terminal:
                                terminal.wait_screen(lambda s:"NATIVE_WAIT_ARMED" in s)
                                terminal.paste(scenario["uiDraft"])
                                before=terminal.wait_screen(lambda s:scenario["uiDraft"] in s)
                                (ui_output/"before-DeLM-wake.txt").write_text(before)
                                Path(scenario["uiDraftReady"]).write_text("actual editor draft visible; no Enter")
                                after=terminal.wait_screen(lambda s:scenario["uiDraft"] in s and "NATIVE_WAKE_ACKED" in s)
                                (ui_output/"after-DeLM-wake.txt").write_text(after)
                                Path(scenario["uiWakeVerified"]).write_text("actual DeLM wake AND unsent draft visible")
                        except BaseException:
                            errors.append(host.redact(traceback.format_exc()))
                            (ui_output/"failure.log").write_text(errors[-1])
                    thread=threading.Thread(target=check_editor,daemon=True) if phase=="finish" else None
                    if thread: thread.start()
                    try:
                        client = host.probe(Path(__file__).with_name("probe_native_board.mjs"), {
                            "DELM_NATIVE_BOARD_SCENARIO": str(scenario_path), "DELM_NATIVE_BOARD_PHASE": phase})
                        (output / f"{phase}-client.log").write_text(host.redact(client.stdout + client.stderr))
                        assert client.returncode == 0, f"Actual Native bound {phase} failed; see board-e2e/{phase}-client.log"
                        phases[phase] = json.loads(client.stdout)
                    finally:
                        stopped.set()
                        if thread: thread.join(30)
                    assert not errors, errors
                    if thread: assert not thread.is_alive(),"Owned Native TUI fixture did not finish"
                assert host.process.returncode == 0
            result = phases["finish"]
            result["pending_restart_arm"] = phases["arm"]
            assert all(v==2 for k,v in counts.items() if not k.startswith('wake-')), counts
            assert sorted(v for k,v in counts.items() if k.startswith('wake-'))==[3,3],counts
            assert provider.requests == 24, provider.requests
            assert all(hashlib.sha256((target/p).read_bytes()).hexdigest()==h for p,h in runtime_hashes.items()), "Product changed during verification"
            result.update(deterministic_http_requests=provider.requests, model_route_counts=counts, live_model_calls=0,
                          native_sigint_exit=0, dependency_owners_prebound=True, claim_replay_via_actual_native_bash=True,
                          product_sha256=runtime_hashes, policy_fixture_only=True)
            (output / "result.json").write_text(host.redact(json.dumps(result, indent=2)) + "\n")
            print(host.redact(json.dumps(result)))
    finally:
        selector.close()
        if board.poll() is None:
            board.send_signal(signal.SIGTERM)
        stdout, stderr = board.communicate(timeout=10)
        (output / "board.log").write_text(host.redact((stdout + stderr).decode(errors="replace")))


if __name__ == "__main__":
    main()
