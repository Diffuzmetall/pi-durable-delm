#!/usr/bin/env python3
"""Portable DeLM preparation/inspection; unsupported Native control fails closed."""
import argparse
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
HOST_GATE = ("BLOCKED: no verified public Native host launch/control capability. "
             "Do not substitute private RPC, a faux host or unguarded submit. "
             "See docs/native-compatibility.md; preparation and Python CLI remain usable.")


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


def load(run):
    state = json.loads((run / "launch.json").read_text())
    if state.get("schema") != 2 or state.get("run") != str(run):
        raise ValueError("Unknown/moved manifest; inspect exact identities, do not initialize over it")
    return state


def capture(source, destination):
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
    task = prompt.read_text()
    result = subprocess.run([sys.executable, str(PACKAGE_ROOT / "scripts/delm_local.py"), "init", str(run),
                             "--shared-workspace", str(workspace), "--n", str(args.agents),
                             "--plan", str(plan), "--task", task], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Bundled init failed; no Native launch was attempted")
    inputs = run / "inputs"
    inputs.mkdir(mode=0o700)
    preserved = dict(prompt=capture(prompt, inputs / "approved-prompt.txt"),
                     plan=capture(plan, inputs / "approved-plan.md"),
                     global_agents=capture(global_agents, inputs / "global-agents.md"),
                     project_agents=capture(project_agents, inputs / "project-agents.md"),
                     references=[capture(source, inputs / f"reference-{number:03d}{source.suffix}")
                                 for number, source in enumerate(references, 1)])
    addendum = (Path(__file__).resolve().parents[1] / "WorkerAddendum.md").read_bytes()
    with (run / "WORKER.md").open("ab") as stream:
        stream.write(b"\n\n" + addendum)
    actors = sorted(p.name for p in run.iterdir() if p.is_dir() and (p / "START.md").is_file())
    if len(actors) != args.agents:
        raise RuntimeError("Generated roster mismatch; retain run for diagnosis, do not retry init")
    state = dict(schema=2, id=uuid.uuid4().hex, run=str(run), workspace=str(workspace),
                 package_root=str(PACKAGE_ROOT), plan=str(plan), global_agents=str(global_agents),
                 inputs=preserved, actors={actor: dict(prompt="not-sent", session=None) for actor in actors},
                 server_started=False, native_launch="BLOCKED", host_gate=HOST_GATE)
    for actor in actors:
        home = run / actor
        marker = f"[delm-bootstrap:{state['id']}:{actor}]"
        first = (marker + "\nRead COMPLETELY global and project AGENTS plus applicable ancestor/subdirectory rules: "
                 f"{global_agents}, {project_agents}. Continue paged reads to the end.\n"
                 f"Read {home / 'START.md'}, {run / 'WORKER.md'}, {plan}, and preserved approved inputs "
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
                native_launch="BLOCKED", inputs=preserved,
                manual_core_commands=dict(server=[sys.executable, str(PACKAGE_ROOT / "scripts/delm_local.py"), "serve", str(run)],
                                          observer=[sys.executable, str(PACKAGE_ROOT / "scripts/delm_board.py"), str(run), "--observe"]))


def status(run):
    state = load(run)
    result = dict(run=str(run), actors=state["actors"], native_launch="BLOCKED", board_reachable=False,
                  drafts="not inspected or submitted", host_gate=HOST_GATE)
    actor = next(iter(state["actors"]))
    response = subprocess.run([sys.executable, str(PACKAGE_ROOT / "scripts/delm_local.py"), "context", str(run), actor,
                               "domain", '{"op":"projection"}'], capture_output=True, text=True, timeout=5)
    if response.returncode == 0:
        view = json.loads(response.stdout)
        result.update(board_reachable=True, sequence=view["sequence"], tasks=len(view["queue"]),
                      blockers=len(view["blockers"]))
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
    args = parser.parse_args()
    if args.action in ("start", "resume", "notify", "stop"):
        # Refuse before probing configs, sockets, sessions or spawning a process.
        raise RuntimeError(HOST_GATE)
    if args.action == "capabilities":
        result = dict(package_root=str(PACKAGE_ROOT), python_core=True, prepare=True,
                      tern_available=shutil.which("tern") is not None, native_launch="BLOCKED", reason=HOST_GATE,
                      sdk_input_component="Tools/NativeInput.mjs requires real host admission and exact-session binding")
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
