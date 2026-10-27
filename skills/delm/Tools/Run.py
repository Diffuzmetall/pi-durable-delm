#!/usr/bin/env python3
"""Prepare DeLM and control exact team sessions on an existing compatible Native owner."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

PACKAGE_ROOT = Path(__file__).resolve().parents[3]
HOST_GATE = ("BLOCKED: no configured compatible existing Native host. "
             "Requires delm.control protocol 1 and the explicit local DurableSession capability; "
             "this package never installs or starts a Native host.")


def path(value):
    return Path(value).expanduser().resolve()


def configuration(filename=None):
    filename = filename or os.environ.get("DELM_CONFIG")
    config = json.loads(path(filename).read_text()) if filename else {}
    if not isinstance(config, dict) or set(config) - {"runs_root", "global_agents"}:
        raise ValueError("Config accepts only runs_root and global_agents; package root is installation-owned")
    for key in config:
        if not isinstance(config[key], str) or not config[key]:
            raise ValueError(f"{key} must be a nonempty path")
        config[key] = str(path(config[key]))
    config.setdefault("runs_root", str(path("~/.local/state/pi-durable-delm/runs")))
    return config


def required_file(value, label):
    if not value:
        raise ValueError(f"Explicit {label} path required; no personal configuration is inferred")
    filename = path(value)
    if not filename.is_file() or not filename.read_text().strip():
        raise ValueError(f"Required nonempty {label} file missing: {filename}")
    return filename


def save(run, state):
    fd, temporary = tempfile.mkstemp(prefix=".launch-", dir=run)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, run / "launch.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load(run, verify_inputs=True):
    state = json.loads((run / "launch.json").read_text())
    if not isinstance(state, dict) or state.get("schema") != 2 or state.get("run") != str(run):
        raise ValueError("Unknown/moved manifest; inspect exact identities, do not initialize over it")
    if not verify_inputs:
        return state
    inputs = state.get("inputs")
    actors = state.get("actors")
    if not isinstance(inputs, dict) or not isinstance(actors, dict) or not actors:
        raise ValueError("Prepared input and actor bindings are missing; reconcile before control")
    references = inputs.get("references")
    if not isinstance(references, list):
        raise ValueError("Prepared reference bindings are missing; reconcile before control")
    captures = [inputs.get(key) for key in ("prompt", "plan", "global_agents", "project_agents")] + references
    for capture_record in captures:
        if not isinstance(capture_record, dict) or not isinstance(capture_record.get("captured"), str):
            raise ValueError("Invalid approved input record; reconcile before control")
        captured = Path(capture_record["captured"])
        if captured.is_symlink() or captured.resolve().parent != run / "inputs":
            raise ValueError("Approved input escapes the private run inputs directory")
        if hashlib.sha256(captured.read_bytes()).hexdigest() != capture_record.get("sha256"):
            raise ValueError("Approved input fingerprint mismatch; reconcile before control")
    for actor, record in actors.items():
        if not isinstance(actor, str) or not actor or Path(actor).name != actor or actor in (".", "..") or not isinstance(record, dict):
            raise ValueError("Invalid actor binding; reconcile before control")
        bootstrap = run / actor / "records/bootstrap-input.txt"
        if bootstrap.is_symlink() or bootstrap.resolve().parent != run / actor / "records":
            raise ValueError("Bootstrap input escapes its exact actor records directory")
        if hashlib.sha256(bootstrap.read_bytes()).hexdigest() != record.get("bootstrap_sha256"):
            raise ValueError("Bootstrap input fingerprint mismatch; reconcile before control")
    return state


def capture(source, destination, body=None):
    if body is None:
        body = source.read_bytes()
    destination.write_bytes(body)
    destination.chmod(0o600)
    return dict(original=str(source), captured=str(destination), sha256=hashlib.sha256(body).hexdigest())


def prepare(config, args):
    workspace = path(args.workspace)
    if not workspace.is_dir():
        raise ValueError("workspace must be an existing project directory")
    global_agents = required_file(args.global_agents or config.get("global_agents"), "global AGENTS")
    project_agents = required_file(workspace / "AGENTS.md", "project AGENTS")
    plan = required_file(args.plan, "approved plan")
    prompt = required_file(args.prompt_file, "approved original prompt")
    references = [required_file(value, "approved reference") for value in args.reference]
    run = path(args.run_dir) if args.run_dir else path(config["runs_root"]) / f"delm-{uuid.uuid4().hex}"
    if run == workspace or workspace in run.parents:
        raise ValueError("run state must remain outside the project")
    if run.exists():
        raise ValueError("Run target already exists; inspect it instead of reinitializing or duplicating a team")
    prompt_bytes = prompt.read_bytes()
    global_bytes = global_agents.read_bytes()
    project_bytes = project_agents.read_bytes()
    reference_bytes = [source.read_bytes() for source in references]
    task = prompt_bytes.decode("utf-8")
    result = subprocess.run([sys.executable, str(PACKAGE_ROOT / "scripts/delm_local.py"), "init", str(run),
                             "--shared-workspace", str(workspace), "--n", str(args.agents),
                             "--plan", str(plan), "--task", task], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Bundled init failed; no Native launch was attempted")
    inputs = run / "inputs"
    inputs.mkdir(mode=0o700, exist_ok=True)
    # The bundled initializer freezes the plan before generating START. Retain
    # those exact bytes, never recapture a potentially changed original here.
    frozen_plan = inputs / "approved-plan.md"
    plan_record = dict(original=str(plan), captured=str(frozen_plan),
                       sha256=hashlib.sha256(frozen_plan.read_bytes()).hexdigest())
    preserved = dict(prompt=capture(prompt, inputs / "approved-prompt.txt", prompt_bytes),
                     plan=plan_record,
                     global_agents=capture(global_agents, inputs / "global-agents.md", global_bytes),
                     project_agents=capture(project_agents, inputs / "project-agents.md", project_bytes),
                     references=[capture(source, inputs / f"reference-{number:03d}{source.suffix}", body)
                                 for number, (source, body) in enumerate(zip(references, reference_bytes), 1)])
    addendum = (Path(__file__).resolve().parents[1] / "WorkerAddendum.md").read_bytes()
    with (run / "WORKER.md").open("ab") as stream:
        stream.write(b"\n\n" + addendum)
    actors = sorted(p.name for p in run.iterdir() if p.is_dir() and (p / "START.md").is_file())
    if len(actors) != args.agents:
        raise RuntimeError("Generated roster mismatch; retain run for diagnosis, do not retry init")
    state = dict(schema=2, id=uuid.uuid4().hex, run=str(run), workspace=str(workspace),
                 package_root=str(PACKAGE_ROOT), plan=str(frozen_plan), global_agents=str(global_agents),
                 inputs=preserved, actors={actor: dict(prompt="not-sent", session=None) for actor in actors},
                 server_started=False, native_launch="not-started", host_gate=HOST_GATE)
    for actor in actors:
        home = run / actor
        marker = f"[delm-bootstrap:{state['id']}:{actor}]"
        first = (marker + "\nRead COMPLETELY global and project AGENTS plus applicable ancestor/subdirectory rules: "
                 f"{global_agents}, {project_agents}. Continue paged reads to the end.\n"
                 f"Read {home / 'START.md'}, {run / 'WORKER.md'}, {frozen_plan}, and preserved approved inputs "
                 f"{inputs}. The original request, not a task summary, remains authoritative.\n"
                 "Read a fresh actor-bound snapshot, inspect its view, then explicitly ACK. Establish verified DONE, "
                 "owners, unresolved FAIL and remaining acceptance; BOOT is not proof of instruction compliance.\n"
                 "Create/claim complementary authorized outputs; publish useful early contracts; one unfinished claim. "
                 "Use only context and delm_wait, not Mail/Beads/new models.\n")
        (home / "records/bootstrap-input.txt").write_text(first)
        (home / "records/bootstrap-input.txt").chmod(0o600)
        state["actors"][actor]["bootstrap_sha256"] = hashlib.sha256(first.encode()).hexdigest()
        state["actors"][actor]["marker"] = marker
    save(run, state)
    return dict(run=str(run), actors=actors, prepared=True, server_started=False,
                native_launch="not-started", inputs=preserved,
                manual_core_commands=dict(server=[sys.executable, str(PACKAGE_ROOT / "scripts/delm_local.py"), "serve", str(run)],
                                          observer=[sys.executable, str(PACKAGE_ROOT / "scripts/delm_board.py"), str(run), "--observe"]))


@contextmanager
def launch_lock(run):
    fd = os.open(run / ".launch.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another launcher owns this run; reconcile its outcome before retry")
        yield
    finally:
        os.close(fd)


def native_rpc(state, actor, operation, *, create=False, payload=None):
    host = state["native"]
    record = state["actors"][actor]
    request = dict(socket=host["socket"], serverId=host.get("server_id"),
                   sessionId=record["session"], identity=record.get("identity"), action=operation,
                   workspace=state["workspace"], run=state["run"], actor=actor, create=create,
                   payload=payload or {})
    command = ["node"]
    if host.get("source"):
        # Advanced source-backed TEST dependency resolution; never fetch/build/install a host.
        resolver = Path(host["source"]) / "packages/coding-agent/src/experimental/source-resolver.ts"
        if not resolver.is_file():
            raise ValueError("Explicit test dependency resolver is missing")
        command += ["--import", str(resolver)]
    response = subprocess.run(command + [str(Path(__file__).with_name("NativeControl.mjs"))],
                              input=json.dumps(request, ensure_ascii=False), capture_output=True, text=True,
                              cwd=state["workspace"], timeout=60)
    if response.returncode:
        raise RuntimeError(response.stderr.strip() or "Native control failed; outcome may be uncertain, retain exact request/session")
    values = []
    for line in response.stdout.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict) and value.get("delm_control") == 1:
            values.append(value)
    if len(values) != 1:
        raise RuntimeError("Missing/unexpected Native control receipt; reconcile the saved exact request")
    value = values[0]
    if host.get("server_id") and value["serverId"] != host["server_id"]:
        raise ValueError("Recorded Native server identity changed")
    if value["identity"]["sessionId"] != record["session"]:
        raise ValueError("Native returned a different exact session")
    if record.get("identity") and value["identity"] != record["identity"]:
        raise ValueError("Native instance/session identity changed; do not replace it")
    return value


def control(run, args):
    with launch_lock(run):
        # Stop can clean up the exact known Native sessions even if approved inputs were damaged.
        state = load(run, verify_inputs=args.action != "stop")
        host = state.get("native")
        source, socket = getattr(args, "host_source", None), getattr(args, "socket", None)
        if host:
            if not isinstance(host, dict):
                raise ValueError("Invalid Native binding")
            for supplied, key in ((source, "source"), (socket, "socket")):
                if supplied and str(path(supplied)) != host[key]:
                    raise ValueError("Cannot retarget an existing Native run; use its exact recorded host")
        elif args.action == "start" and socket:
            host = dict(source=str(path(source)) if source else None, socket=str(path(socket)))
        else:
            raise RuntimeError(HOST_GATE + " Explicit start --socket SOCKET is required.")
        actors = state.get("actors")
        if not isinstance(actors, dict) or not actors or any(not isinstance(record, dict) for record in actors.values()):
            raise ValueError("Invalid actor/session ledger")
        selected = [args.actor] if getattr(args, "actor", None) else list(actors)
        if any(actor not in actors for actor in selected):
            raise ValueError("Unknown run actor; no sessions controlled")
        sessions = [record.get("session") for record in actors.values() if record.get("session") is not None]
        if len(set(sessions)) != len(sessions):
            raise ValueError("Actor/session collision in launch ledger; reconcile before control")
        if args.action == "notify" and (not args.input_file or not args.request_id):
            raise ValueError("notify requires approved --input-file and stable --request-id")
        notify_text = None
        if args.action == "notify":
            notify_text = required_file(args.input_file, "approved notification input").read_bytes().decode("utf-8")
        if args.action == "start" and not status(run, native=False)["board_reachable"]:
            raise ValueError("Start the prepared run's bundled board server before Native input")
        state["native"] = host
        if args.action == "start":
            for actor, record in actors.items():
                if record.get("session") is None:
                    record["session"] = str(uuid.uuid5(uuid.UUID(state["id"]), actor))
        elif any(not actors[actor].get("identity") for actor in selected):
            raise ValueError("Exact Native session identity is missing; reconcile start, never create a replacement")
        # Reserve all chosen exact session IDs BEFORE the first RPC; every retry reuses them.
        save(run, state)
        results = {}
        for actor in selected:
            record = actors[actor]
            if args.action == "start":
                value = native_rpc(state, actor, "identity", create=True)
                host["server_id"] = value["serverId"]
                record["identity"] = value["identity"]
                save(run, state)  # Identity precedes bind/input, including response-loss recovery.
                native_rpc(state, actor, "bind")
                text = (run / actor / "records/bootstrap-input.txt").read_bytes().decode("utf-8")
                request_id = f"delm-bootstrap:{state['id']}:{actor}"
                operation = "input"
            elif args.action == "notify":
                text = notify_text
                key = hashlib.sha256(args.request_id.encode()).hexdigest()
                request_id = f"delm-notify:{state['id']}:{actor}:{key}"
                operation = "input"
            else:
                operation = args.action
            if operation == "input":
                digest = hashlib.sha256(text.encode()).hexdigest()
                requests = state.setdefault("requests", {})
                if not isinstance(requests, dict):
                    raise ValueError("Invalid saved request ledger")
                previous = requests.get(request_id)
                if previous and (previous.get("sha256") != digest or previous.get("type") != "input" or previous.get("actor") != actor):
                    raise ValueError("Request approval binding changed; use reconciliation, not changed replay")
                saved = run / "inputs" / (hashlib.sha256(request_id.encode()).hexdigest() + ".txt")
                if saved.is_symlink():
                    raise ValueError("Saved approved request must not be a symlink")
                if saved.exists():
                    if hashlib.sha256(saved.read_bytes()).hexdigest() != digest:
                        raise ValueError("Saved approved request bytes changed; reconcile before retry")
                else:
                    saved.write_bytes(text.encode())
                    saved.chmod(0o600)
                requests[request_id] = dict(type="input", sha256=digest, actor=actor, captured=str(saved), status="pending")
                save(run, state)  # Uncertain RPC retains the same identity, bytes and request key.
                receipt = native_rpc(state, actor, operation,
                                     payload=dict(type="input", requestId=request_id, text=text, expectedSha256=digest))
                if receipt["result"].get("accepted") is not True:
                    raise RuntimeError("Native did not confirm input acceptance; retain pending request")
                requests[request_id]["status"] = "accepted"
                if args.action == "start":
                    record["prompt"] = "accepted"
                results[actor] = receipt["result"]
            else:
                results[actor] = native_rpc(state, actor, operation)["result"]
                if operation in ("stop", "resume"):
                    record["stopped"] = operation == "stop"
            state["native_launch"] = "controlled"
            save(run, state)
        return dict(run=str(run), action=args.action, results=results, drafts="not inspected or submitted")


def status(run, native=True):
    state = load(run)
    result = dict(run=str(run), actors=state["actors"], native_launch=state.get("native_launch", "not-started"), board_reachable=False,
                  approved_inputs_verified=True, drafts="not inspected or submitted", host_gate=HOST_GATE)
    actor = next(iter(state["actors"]))
    response = subprocess.run([sys.executable, str(PACKAGE_ROOT / "scripts/delm_local.py"), "context", str(run), actor,
                               "domain", '{"op":"projection"}'], capture_output=True, text=True, timeout=5)
    if response.returncode == 0:
        view = json.loads(response.stdout)
        result.update(board_reachable=True, sequence=view["sequence"], tasks=len(view["queue"]),
                      blockers=len(view["blockers"]))
    if native and state.get("native"):
        result["native_launch"] = state.get("native_launch", "partial")
        result["native_sessions"] = {}
        for actor, record in state["actors"].items():
            if not record.get("identity"):
                result["native_sessions"][actor] = {"state": "unbound-or-uncertain"}
                continue
            try:
                result["native_sessions"][actor] = native_rpc(state, actor, "status")["result"]
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                result["native_sessions"][actor] = {"state": "unavailable-or-unbound", "error": str(error)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Explicit user config or DELM_CONFIG; no installed private config")
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare", help="Freeze approved inputs and 2/4/8 actor instructions; no server/models")
    prep.add_argument("--workspace", required=True)
    prep.add_argument("--plan", required=True)
    prep.add_argument("--prompt-file", required=True)
    prep.add_argument("--reference", action="append", default=[])
    prep.add_argument("--global-agents")
    prep.add_argument("--agents", type=int, choices=(2, 4, 8), required=True)
    prep.add_argument("--run-dir")
    sub.add_parser("capabilities", help="Report installed payload and unverified host-control boundary")
    for name in ("status", "start", "resume", "notify", "stop"):
        action = sub.add_parser(name)
        action.add_argument("--run-dir", required=True)
        if name != "status":
            action.add_argument("--actor", help="One existing actor; omitted means the existing roster")
            action.add_argument("--host-source", help="Advanced source-backed test dependency resolver only; normal public client peers need no source checkout")
            action.add_argument("--socket", help="Existing official Native server Unix socket; no auto-discovery/auto-start")
        if name == "notify":
            action.add_argument("--input-file", help="Approved original notification text")
            action.add_argument("--request-id", help="Stable update identity; reuse unchanged after uncertain response")
    args = parser.parse_args()
    if args.action in ("start", "resume", "notify", "stop"):
        result = control(path(args.run_dir), args)
    elif args.action == "capabilities":
        result = dict(package_root=str(PACKAGE_ROOT), python_core=True, prepare=True,
                      tern_available=shutil.which("tern") is not None, native_launch="requires-existing-compatible-native",
                      native_control_client=True, installs_or_starts_native_host=False, reason=HOST_GATE,
                      sdk_input_component="Tools/NativeInput.mjs uses actual Native owner submit + exact-session binding; extra host policy optional")
    elif args.action == "prepare":
        result = prepare(configuration(args.config), args)
    else:
        result = status(path(args.run_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, KeyError) as error:
        sys.exit(str(error))
