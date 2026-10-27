"""Advisory path/resource leases in the board's caller-owned transaction.

TTL revokes permission, not proof that an external writer stopped. These records
cannot prevent arbitrary shell/background writes or filesystem alias races.
"""
import json
import math
from pathlib import Path
import re
import sqlite3
import time
import uuid


class LeaseError(ValueError):
    def __init__(self, message, code="INVALID"):
        super().__init__(message)
        self.code = code


def _schema(db):
    if not db.in_transaction:
        raise LeaseError("leases require caller transaction")
    db.execute("CREATE TABLE IF NOT EXISTS delm_leases (lease_id TEXT PRIMARY KEY, body TEXT NOT NULL)")


def project(db, *, now=None):
    """Read-only, even on an unmigrated DB; never clean up expired leases."""
    now = time.time() if now is None else now
    try:
        rows = db.execute("SELECT body FROM delm_leases ORDER BY rowid").fetchall()
    except sqlite3.OperationalError as error:
        if "no such table: delm_leases" in str(error):
            return []
        raise
    result = []
    for row in rows:
        lease = json.loads(row[0])
        lease["expired"] = lease["state"] == "active" and lease["expires_at"] <= now
        result.append(lease)
    return result


def _paths(workspace, values):
    if not isinstance(values, list) or len(values) > 100:
        raise LeaseError("paths must be a list of at most 100 project paths")
    result = set()
    for value in values:
        if not isinstance(value, str) or not value.strip() or len(value) > 4096 or "\x00" in value:
            raise LeaseError("invalid project path")
        try:
            path = (workspace / value).resolve()
        except (OSError, RuntimeError, ValueError) as error:
            raise LeaseError("cannot canonicalize project path") from error
        if not path.is_relative_to(workspace):
            raise LeaseError("project path escapes workspace")
        if path == workspace:
            raise LeaseError("lease must name a narrow project path, not workspace root")
        result.add(str(path))
    return sorted(result)


def _resources(values):
    if not isinstance(values, list) or len(values) > 100:
        raise LeaseError("resources must be a list of at most 100 keys")
    if any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}", value)
           for value in values):
        raise LeaseError("invalid resource key")
    return sorted(set(values))


def _ttl(args):
    ttl = args.get("ttl", 300)
    if isinstance(ttl, bool) or not isinstance(ttl, (int, float)) or not math.isfinite(ttl) or not 1 <= ttl <= 86400:
        raise LeaseError("ttl must be finite seconds between 1 and 86400")
    return ttl


def _task(tasks, task_id, owner, generation):
    task = tasks.get(task_id) if isinstance(task_id, str) else None
    if not task:
        raise LeaseError("unknown lease task", "UNKNOWN")
    if isinstance(generation, bool) or not isinstance(generation, int):
        raise LeaseError("generation must be integer")
    if task.get("generation") != generation:
        raise LeaseError("stale task generation", "STALE")
    if task.get("state") != "claimed" or task.get("owner") != owner:
        raise LeaseError("lease requires live claimed task owned by actor", "CONFLICT")
    return task


def _overlap(left, right):
    a, b = Path(left), Path(right)
    return a.is_relative_to(b) or b.is_relative_to(a)


def _conflicts(leases, candidate, now, exclude=None):
    for other in leases:
        if other["lease_id"] == exclude or other["state"] != "active" or other["expires_at"] <= now:
            continue
        if set(other["resources"]) & set(candidate["resources"]) or any(
                _overlap(a, b) for a in other["paths"] for b in candidate["paths"]):
            raise LeaseError(f"lease conflict with {other['lease_id']} owned by {other['owner']}", "CONFLICT")


def operate(db, actor, op, args, *, workspace, tasks, append, now=None):
    """Execute acquire/renew/release/handoff; outer domain supplies request replay."""
    if not isinstance(actor, str) or not actor or not isinstance(args, dict):
        raise LeaseError("invalid actor or lease arguments")
    if op not in ("acquire", "renew", "release", "handoff"):
        raise LeaseError("unknown lease operation")
    now = time.time() if now is None else now
    if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
        raise LeaseError("invalid clock")
    workspace = Path(workspace).resolve(strict=True)
    if not workspace.is_dir():
        raise LeaseError("workspace must be a directory")
    _schema(db)
    leases = project(db, now=now)
    if op == "acquire":
        _task(tasks, args.get("task"), actor, args.get("generation"))
        declared = args.get("paths", [])
        lease = dict(lease_id=uuid.uuid4().hex, owner=actor, task=args["task"],
                     generation=args["generation"], workspace=str(workspace),
                     paths=_paths(workspace, declared), declared_paths=declared,
                     resources=_resources(args.get("resources", [])),
                     expires_at=now + _ttl(args), state="active", advisory=True)
        if not lease["paths"] and not lease["resources"]:
            raise LeaseError("acquire needs at least one path or resource")
        _conflicts(leases, lease, now)
    else:
        lease = next((entry for entry in leases if entry["lease_id"] == args.get("lease_id")), None)
        if not lease:
            raise LeaseError("unknown lease", "UNKNOWN")
        lease.pop("expired", None)
        if lease["workspace"] != str(workspace) or lease["owner"] != actor or lease["task"] != args.get("task"):
            raise LeaseError("lease identity/owner/task mismatch", "CONFLICT")
        if op == "handoff":
            recipient = args.get("to")
            if not isinstance(recipient, str) or recipient == actor:
                raise LeaseError("handoff requires a different recipient")
            # Old authenticated lease owner is the capability; new task owner must
            # be exactly the next ownership epoch of that same task.
            _task(tasks, lease["task"], recipient, args.get("generation"))
            if args["generation"] != lease["generation"] + 1:
                raise LeaseError("handoff requires direct next-generation task transfer", "STALE")
        else:
            _task(tasks, lease["task"], actor, args.get("generation"))
            if lease["generation"] != args["generation"]:
                raise LeaseError("stale lease generation", "STALE")
        if lease["state"] != "active" or lease["expires_at"] <= now:
            raise LeaseError("lease permission released or expired; acquire a new lease", "STALE")
        if op != "release":
            if _paths(workspace, lease["declared_paths"]) != lease["paths"]:
                raise LeaseError("project path alias changed since acquisition", "STALE")
            _conflicts(leases, lease, now, exclude=lease["lease_id"])
            lease["expires_at"] = now + _ttl(args)
        if op == "handoff":
            lease.update(owner=args["to"], generation=args["generation"])
        elif op == "release":
            lease["state"] = "released"
    db.execute("INSERT INTO delm_leases(lease_id,body) VALUES (?,?) ON CONFLICT(lease_id) DO UPDATE SET body=excluded.body",
               (lease["lease_id"], json.dumps(lease, ensure_ascii=False)))
    sequence = append(db, actor, "lease", dict(action=op, lease=lease))
    return dict(lease=lease, sequence=sequence, advisory=True)
