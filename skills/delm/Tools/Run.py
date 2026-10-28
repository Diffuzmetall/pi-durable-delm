#!/usr/bin/env python3
"""Prepare DeLM and connect exact actor conversations on the existing Native 1.4."""
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
PROTOCOL = "delm.native14.control.v1"
HOST_GATE = "Requires the existing Native1.4 executable, registry adapter and genuine host admission; no bundled host or model/settings replacement."


def path(value):
    return Path(value).expanduser().resolve()


def configuration(filename=None):
    filename = filename or os.environ.get("DELM_CONFIG")
    config = json.loads(path(filename).read_text()) if filename else {}
    if not isinstance(config, dict) or set(config) - {"runs_root", "global_agents"}:
        raise ValueError("Config accepts only runs_root and global_agents")
    for key in config:
        if not isinstance(config[key], str) or not config[key]:
            raise ValueError(f"{key} must be a nonempty path")
        config[key] = str(path(config[key]))
    config.setdefault("runs_root", str(path("~/.local/state/pi-durable-delm/runs")))
    return config


def required_file(value, label):
    if not value:
        raise ValueError(f"Explicit {label} path required")
    filename = path(value)
    if not filename.is_file() or not filename.read_text().strip():
        raise ValueError(f"Required nonempty {label} file missing")
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
        raise ValueError("Unknown/moved manifest; reconcile instead of creating another team")
    if state.get("native") and (not isinstance(state["native"], dict) or state["native"].get("protocol") != PROTOCOL):
        raise ValueError("Historical Native binding is not Native14; no automatic migration")
    actors = state.get("actors")
    if not isinstance(actors, dict) or not actors:
        raise ValueError("Actor bindings missing")
    for actor, record in actors.items():
        if not isinstance(actor, str) or Path(actor).name != actor or actor in ("", ".", "..") or not isinstance(record, dict):
            raise ValueError("Invalid actor binding")
    if not verify_inputs:
        return state
    inputs = state.get("inputs")
    if not isinstance(inputs, dict) or not isinstance(inputs.get("references"), list):
        raise ValueError("Prepared input bindings missing")
    captures = [inputs.get(k) for k in ("prompt", "plan", "global_agents", "project_agents")] + inputs["references"]
    for record in captures:
        if not isinstance(record, dict) or not isinstance(record.get("captured"), str):
            raise ValueError("Invalid approved input record")
        captured = Path(record["captured"])
        if captured.is_symlink() or captured.resolve().parent != run / "inputs":
            raise ValueError("Approved input escapes private inputs directory")
        if hashlib.sha256(captured.read_bytes()).hexdigest() != record.get("sha256"):
            raise ValueError("Approved input fingerprint mismatch")
    for actor, record in actors.items():
        bootstrap = run / actor / "records/bootstrap-input.txt"
        if bootstrap.is_symlink() or bootstrap.resolve().parent != run / actor / "records":
            raise ValueError("Bootstrap escapes exact actor records")
        if hashlib.sha256(bootstrap.read_bytes()).hexdigest() != record.get("bootstrap_sha256"):
            raise ValueError("Bootstrap input fingerprint mismatch")
    return state


def capture(source, destination, body=None):
    if body is None:
        body = source.read_bytes()
    destination.write_bytes(body)
    destination.chmod(0o600)
    return dict(original=str(source), captured=str(destination), sha256=hashlib.sha256(body).hexdigest())


def open_commands(run, actors):
    return {actor: [sys.executable, str(Path(__file__).resolve()), "open", "--run-dir", str(run), "--actor", actor]
            for actor in actors}


def prepare(config, args):
    workspace = path(args.workspace)
    if not workspace.is_dir():
        raise ValueError("workspace must be an existing project")
    global_agents = required_file(args.global_agents or config.get("global_agents"), "global AGENTS")
    project_agents = required_file(workspace / "AGENTS.md", "project AGENTS")
    plan = required_file(args.plan, "approved plan")
    prompt = required_file(args.prompt_file, "approved original prompt")
    references = [required_file(value, "approved reference") for value in args.reference]
    run = path(args.run_dir) if args.run_dir else path(config["runs_root"]) / f"delm-{uuid.uuid4().hex}"
    if run == workspace or workspace in run.parents or run.exists():
        raise ValueError("New run must be outside project and must not already exist")
    prompt_bytes, global_bytes, project_bytes = prompt.read_bytes(), global_agents.read_bytes(), project_agents.read_bytes()
    reference_bytes = [source.read_bytes() for source in references]
    result = subprocess.run([sys.executable, str(PACKAGE_ROOT / "scripts/delm_local.py"), "init", str(run),
        "--shared-workspace", str(workspace), "--n", str(args.agents), "--plan", str(plan),
        "--task", prompt_bytes.decode("utf-8")], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Bundled init failed; no Native launch attempted")
    inputs = run / "inputs"
    inputs.mkdir(mode=0o700, exist_ok=True)
    frozen_plan = inputs / "approved-plan.md"
    preserved = dict(prompt=capture(prompt, inputs / "approved-prompt.txt", prompt_bytes),
        plan=dict(original=str(plan), captured=str(frozen_plan), sha256=hashlib.sha256(frozen_plan.read_bytes()).hexdigest()),
        global_agents=capture(global_agents, inputs / "global-agents.md", global_bytes),
        project_agents=capture(project_agents, inputs / "project-agents.md", project_bytes),
        references=[capture(source, inputs / f"reference-{n:03d}{source.suffix}", body)
            for n, (source, body) in enumerate(zip(references, reference_bytes), 1)])
    with (run / "WORKER.md").open("ab") as stream:
        stream.write(b"\n\n" + (Path(__file__).resolve().parents[1] / "WorkerAddendum.md").read_bytes())
    actors = sorted(p.name for p in run.iterdir() if p.is_dir() and (p / "START.md").is_file())
    if len(actors) != args.agents:
        raise RuntimeError("Generated roster mismatch; retain run for diagnosis")
    state = dict(schema=2, id=uuid.uuid4().hex, run=str(run), workspace=str(workspace), package_root=str(PACKAGE_ROOT),
        plan=str(frozen_plan), global_agents=str(global_agents), inputs=preserved,
        actors={a: dict(prompt="not-sent", session=None) for a in actors}, server_started=False,
        native_launch="not-started", host_gate=HOST_GATE)
    for actor in actors:
        home = run / actor
        marker = f"[delm-bootstrap:{state['id']}:{actor}]"
        first = (f"{marker}\nRead COMPLETELY global/project AGENTS and applicable ancestor/subdirectory rules: {global_agents}, {project_agents}. "
            f"Continue paged reads to the end. Read {home / 'START.md'}, {run / 'WORKER.md'}, {frozen_plan} and preserved approved inputs {inputs}. "
            "The original request remains authoritative. Read a fresh actor-bound snapshot, inspect it and explicitly ACK. "
            "Establish DONE/claims/owners/FAIL/remaining acceptance; BOOT is not instruction compliance. "
            "Claim complementary authorized outputs before writing; publish useful early contracts. One unfinished claim. "
            "Only context/delm_wait; no Mail/Beads/new agents/models or polling.\n")
        bootstrap = home / "records/bootstrap-input.txt"
        bootstrap.write_bytes(first.encode())
        bootstrap.chmod(0o600)
        state["actors"][actor].update(bootstrap_sha256=hashlib.sha256(first.encode()).hexdigest(), marker=marker)
    save(run, state)
    return dict(run=str(run), actors=actors, prepared=True, server_started=False, native_launch="not-started", inputs=preserved,
        native_open_commands=open_commands(run, actors), manual_core_commands=dict(
            server=[sys.executable, str(PACKAGE_ROOT / "scripts/delm_local.py"), "serve", str(run)],
            observer=[sys.executable, str(PACKAGE_ROOT / "scripts/delm_board.py"), str(run), "--observe"]))


@contextmanager
def launch_lock(run):
    fd = os.open(run / ".launch.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another launcher owns this run")
        yield
    finally:
        os.close(fd)


def native_rpc(state, actor, method, payload=None):
    record = state["actors"][actor]
    if not record.get("socket"):
        raise ValueError(f"{actor}: open the emitted foreground Native command in an ordinary terminal first")
    request = dict(socket=record["socket"], method=method, payload=payload or {})
    if method != "identity":
        if not record.get("identity"):
            raise ValueError("Exact Native identity missing; reconcile start before control")
        request["identity"] = record["identity"]
    result = subprocess.run(["node", str(Path(__file__).with_name("NativeControl.mjs"))], input=json.dumps(request),
        capture_output=True, text=True, timeout=30, cwd=state["workspace"])
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Native response uncertain; retain exact request")
    value = json.loads(result.stdout)
    if value.get("delm_control") != 14:
        raise ValueError("Unexpected Native control receipt")
    return value["result"]


def record_identity(state, actor, identity):
    if not isinstance(identity, dict) or identity.get("protocol") != PROTOCOL or identity.get("sdkVersion") != "1.4.0":
        raise ValueError("Unsupported current Native control ABI/version")
    if (identity.get("run"), identity.get("actor"), identity.get("workspace"), identity.get("conversationId")) != (
            state["run"], actor, state["workspace"], 1):
        raise ValueError("Native run/actor/workspace/root mismatch")
    session = identity.get("sessionPath")
    if not isinstance(session, str) or not Path(session).is_file() or str(path(session)) != session:
        raise ValueError("Native physical session missing or noncanonical")
    if identity.get("sessionId") != Path(session).parent.name or not isinstance(identity.get("instanceId"), str) or not identity["instanceId"]:
        raise ValueError("Native instance/session identity missing")
    record = state["actors"][actor]
    if record.get("identity") and record["identity"] != identity:
        raise ValueError("Recorded Native identity changed; never replace a session")
    if any(a != actor and r.get("session") == session for a, r in state["actors"].items()):
        raise ValueError("Actor session collision")
    record.update(identity=identity, session=session)


def open_actor(run, args):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError("Open must run in an ordinary foreground terminal; no terminal manager is required")
    with launch_lock(run):
        state = load(run)
        if args.actor not in state["actors"]:
            raise ValueError("Unknown actor")
        record = state["actors"][args.actor]
        if record.get("pid"):
            try:
                os.kill(record["pid"], 0)
            except ProcessLookupError:
                pass
            else:
                raise ValueError("Recorded Native process still exists; use its existing terminal/control endpoint")
        session = record.get("session")
        if session and not Path(session).is_file():
            raise ValueError("Recorded Native session missing; no replacement created")
        if record.get("launch_attempt") and not session:
            raise ValueError("Previous launch outcome unrecorded; reconcile its exact owner before opening again")
        executable = args.native_executable or shutil.which("pi-durable")
        if not executable or not path(executable).is_file() or not os.access(path(executable), os.X_OK):
            raise ValueError("Existing executable pi-durable required; nothing is installed automatically")
        executable = str(path(executable))
        if state.get("native", {}).get("executable", executable) != executable:
            raise ValueError("Existing Native executable changed; reconcile before reopening")
        profile = record.get("mcp_profile")
        if args.mcp_server is not None or args.mcp_tools is not None:
            profile = dict(server=args.mcp_server, tools=args.mcp_tools)
        if profile is not None and (not isinstance(profile, dict) or set(profile) != {"server", "tools"}
                or any(not isinstance(value, str) or not value.strip() for value in profile.values())):
            raise ValueError("An explicit Native MCP profile requires both --mcp-server and --mcp-tools")
        socket_root = str(Path(tempfile.mkdtemp(prefix="delm14-")).resolve())
        endpoint = str(Path(socket_root) / "control.sock")
        options = dict(run=str(run), actor=args.actor, controlSocket=endpoint)
        adapter = run / args.actor / "delm-adapter.js"
        body = (f"import install from {json.dumps(str(PACKAGE_ROOT / 'extensions/delm/native14.js'))};\n"
                f"export default base => install(base, {json.dumps(options)});\n")
        fd = os.open(adapter, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(body)
        state["native"] = dict(protocol=PROTOCOL, executable=executable)
        record.update(socket=endpoint, pid=os.getpid(), launch_attempt=uuid.uuid4().hex,
            adapter_sha256=hashlib.sha256(body.encode()).hexdigest())
        command = [executable, "--extension", str(adapter)]
        if profile is not None:
            command += ["--mcp-server", profile["server"], "--mcp-tools", profile["tools"]]
        record["mcp_profile"] = profile
        if session:
            command += ["--session", session]
        record["argv"] = command
        save(run, state)  # The exact attempt precedes exec; uncertain launch never creates another owner.
        environment = dict(os.environ)
        environment["PATH"] = str(run / args.actor / "bin") + os.pathsep + environment.get("PATH", "")
    os.chdir(state["workspace"])
    os.execve(executable, command, environment)


def control(run, args):
    with launch_lock(run):
        state = load(run, verify_inputs=args.action != "stop")
        selected = [args.actor] if args.actor else list(state["actors"])
        if any(a not in state["actors"] for a in selected):
            raise ValueError("Unknown actor")
        text = None
        if args.action == "notify":
            if not args.request_id:
                raise ValueError("notify requires stable --request-id")
            text = required_file(args.input_file, "approved notification").read_bytes().decode("utf-8")
        if args.action == "start" and not status(run, native=False)["board_reachable"]:
            raise ValueError("Start the emitted bundled board server before Native input")
        results = {}
        for actor in selected:
            record = state["actors"][actor]
            if args.action == "start":
                actual = native_rpc(state, actor, "identity")
                record_identity(state, actor, actual["identity"])
                save(run, state)  # Actual owner identity precedes approved input, including lost-response recovery.
                body = (run / actor / "records/bootstrap-input.txt").read_bytes().decode("utf-8")
                request_id = f"delm-bootstrap:{state['id']}:{actor}"
            elif args.action == "notify":
                body = text
                request_id = f"delm-notify:{state['id']}:{actor}:{hashlib.sha256(args.request_id.encode()).hexdigest()}"
            else:
                results[actor] = native_rpc(state, actor, args.action)
                if args.action in ("stop", "resume"):
                    record["stopped"] = args.action == "stop"
                save(run, state)
                continue
            digest = hashlib.sha256(body.encode()).hexdigest()
            requests = state.setdefault("requests", {})
            if not isinstance(requests, dict):
                raise ValueError("Invalid saved request ledger")
            previous = requests.get(request_id)
            if previous and (previous.get("sha256"), previous.get("type"), previous.get("actor")) != (digest, "input", actor):
                raise ValueError("Request approval binding changed; do not change replay")
            saved = run / "inputs" / (hashlib.sha256(request_id.encode()).hexdigest() + ".txt")
            if saved.is_symlink() or (saved.exists() and hashlib.sha256(saved.read_bytes()).hexdigest() != digest):
                raise ValueError("Saved approved request bytes changed")
            if not saved.exists():
                saved.write_bytes(body.encode())
                saved.chmod(0o600)
            requests[request_id] = dict(type="input", sha256=digest, actor=actor, captured=str(saved), status="pending")
            save(run, state)
            result = native_rpc(state, actor, "input", dict(type="input", requestId=request_id, text=body, expectedSha256=digest))
            if result.get("accepted") is not True or result.get("requestId") != request_id:
                raise RuntimeError("Input acceptance unconfirmed; retain pending exact request")
            requests[request_id]["status"] = "accepted"
            if args.action == "start":
                record["prompt"] = "accepted"
            state["native_launch"] = "controlled"
            results[actor] = result
            save(run, state)
        return dict(run=str(run), action=args.action, results=results, drafts="not inspected or submitted")


def status(run, native=True):
    state = load(run)
    result = dict(run=str(run), actors=state["actors"], native_launch=state.get("native_launch", "not-started"),
        board_reachable=False, approved_inputs_verified=True, drafts="not inspected or submitted",
        native_open_commands=open_commands(run, state["actors"]))
    actor = next(iter(state["actors"]))
    response = subprocess.run([sys.executable, str(PACKAGE_ROOT / "scripts/delm_local.py"), "context", str(run), actor,
        "domain", '{"op":"projection"}'], capture_output=True, text=True, timeout=5)
    if response.returncode == 0:
        view = json.loads(response.stdout)
        result.update(board_reachable=True, sequence=view["sequence"], tasks=len(view["queue"]), blockers=len(view["blockers"]))
    if native and state.get("native"):
        result["native_sessions"] = {}
        for actor, record in state["actors"].items():
            if not record.get("identity"):
                result["native_sessions"][actor] = dict(state="unbound-or-uncertain")
                continue
            try:
                result["native_sessions"][actor] = native_rpc(state, actor, "status")
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                result["native_sessions"][actor] = dict(state="unavailable-or-unbound", error=str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Explicit config or DELM_CONFIG; no private config inferred")
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare", help="Freeze approved inputs; emit ordinary-terminal actor/board commands")
    for name in ("workspace", "plan", "prompt-file"):
        prep.add_argument("--" + name, required=True)
    prep.add_argument("--reference", action="append", default=[])
    prep.add_argument("--global-agents")
    prep.add_argument("--agents", type=int, choices=(2, 4, 8), required=True)
    prep.add_argument("--run-dir")
    sub.add_parser("capabilities")
    opening = sub.add_parser("open", help="Foreground existing Native in this ordinary terminal; exact recorded reopen")
    opening.add_argument("--run-dir", required=True)
    opening.add_argument("--actor", required=True)
    opening.add_argument("--native-executable", help="Existing executable; default PATH pi-durable")
    opening.add_argument("--mcp-server", help="Optional existing Native single-server MCP profile; preserved on reopen")
    opening.add_argument("--mcp-tools", help="Comma-separated tools for --mcp-server; default uses Native configured MCP")
    for name in ("status", "start", "resume", "notify", "stop"):
        action = sub.add_parser(name)
        action.add_argument("--run-dir", required=True)
        if name != "status":
            action.add_argument("--actor")
        if name == "notify":
            action.add_argument("--input-file", required=True)
            action.add_argument("--request-id", required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        result = prepare(configuration(args.config), args)
    elif args.action == "open":
        return open_actor(path(args.run_dir), args)
    elif args.action == "capabilities":
        result = dict(protocol=PROTOCOL, python_core=True, prepare=True, terminal="ordinary foreground terminal",
            existing_native_available=shutil.which("pi-durable") is not None, installs_native=False,
            constructs_harness=False, changes_models_auth_settings=False, reason=HOST_GATE)
    elif args.action == "status":
        result = status(path(args.run_dir))
    else:
        result = control(path(args.run_dir), args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, KeyError) as error:
        sys.exit(str(error))
