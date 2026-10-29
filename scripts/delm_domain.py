"""Canonical local DeLM events and fenced operations; no storage owner of its own."""
import json
import threading
import uuid
from contextlib import AbstractContextManager, contextmanager
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Protocol, cast


class DomainError(ValueError):
    def __init__(self, message, code="INVALID"):
        super().__init__(message)
        self.code = code


def _decode_json(value: str, source: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise DomainError(f"malformed {source} JSON") from error


def project_events(rows, actors=()) -> dict[str, Any]:
    tasks, notes, sessions, statuses, events, attached = {}, [], {}, {}, [], {}
    sequence = 0
    for row in rows:
        row = dict(row)
        p = _decode_json(row["payload"], "event payload") if isinstance(row["payload"], str) else deepcopy(row["payload"])
        actor, kind, seq = row["actor"], row["kind"], row["sequence"]
        sequence = max(sequence, seq)
        if kind == "read":
            p = {"via": p.get("via")}
        events.append(dict(sequence=seq, actor=actor, kind=kind, payload=p))
        if kind == "item":
            tasks[p["id"]] = dict(p, state="open", owner=None, generation=0, revision=seq,
                                   deps=[], criteria=[], parent=None, outputs=[], mapping={})
        elif kind in ("claim", "done") and p.get("item") in tasks:
            t = tasks[p["item"]]
            t.update(state="claimed" if kind == "claim" else "done", owner=actor, revision=seq)
            if kind == "claim":
                t["generation"] += 1
            else:
                t.update(summary=p["summary"], publication_id=p.get("publication_id", p["item"]))
        elif kind == "task":
            tasks[p["task"]["id"]] = dict(p["task"], revision=seq)
        elif kind in ("note", "publication"):
            notes.append(dict(p, actor=actor, sequence=seq))
        elif kind == "session":
            if sessions.get(p["actor"], {}).get("generation", 0) == 0:
                sessions[p["actor"]] = dict(actor=p["actor"], state=p["state"], generation=0)
        elif kind == "lifecycle":
            sessions[p["actor"]] = dict(p)
        elif kind == "status":
            statuses[actor] = p["text"]
        elif kind == "body":
            attached[p["id"]] = p["files"]
    for task in tasks.values():
        publication_id = task.get("publication_id", task["id"])
        if publication_id in attached:
            task["files"] = attached[publication_id]
    for note in notes:
        if note["id"] in attached:
            note["files"] = attached[note["id"]]
    resolved = {i for n in notes if n.get("type") in ("CORRECTION", "RESOLUTION") for i in n.get("resolves", [])}
    blockers = [n for n in notes if n.get("type") == "FAIL" and n["id"] not in resolved]
    # Reverse edges let each unresolved blocker visit only its affected tasks.
    dependents = {}
    for identity, task in tasks.items():
        task["blockers"] = []
        for dependency in task.get("deps", []) + task.get("outputs", []):
            dependents.setdefault(dependency, []).append(identity)
    for blocker in blockers:
        pending = [blocker.get("task"), blocker.get("output"), *blocker.get("related", [])]
        seen = set()
        while pending:
            identity = pending.pop()
            if identity in seen:
                continue
            seen.add(identity)
            if identity in tasks:
                tasks[identity]["blockers"].append(blocker)
            pending.extend(dependents.get(identity, ()))
    for task in tasks.values():
        task["readiness"] = task["state"] == "open" and not task["blockers"] and all(
            tasks.get(i, {}).get("state") == "done" for i in task.get("deps", []))
    return dict(protocol=2, sequence=sequence, agents=list(actors), queue=list(tasks.values()), notes=notes,
                blockers=blockers, sessions=[sessions.get(a, dict(actor=a, state="starting", generation=0)) for a in actors],
                status=[dict(actor=a, text=s) for a, s in statuses.items()], events=events)


def text(value, field, limit=8192):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise DomainError(f"{field} must be nonempty text <= {limit} characters")
    return value


def strings(value, field):
    if not isinstance(value, list) or len(value) > 256:
        raise DomainError(f"{field} must be an array of at most 256 strings")
    result = [text(v, field, 1024) for v in value]
    if len(result) != len(set(result)):
        raise DomainError(f"{field} contains duplicates")
    return result


def validate_graph(tasks):
    visiting, visited = set(), set()
    for identity in tasks:
        if identity in visited:
            continue
        visiting.add(identity)
        # Completion waits on outputs too; parent is only a metadata back-pointer.
        stack = [(identity, iter(tasks[identity].get("deps", []) + tasks[identity].get("outputs", [])))]
        while stack:
            current, dependencies = stack[-1]
            try:
                dependency = next(dependencies)
            except StopIteration:
                stack.pop()
                visiting.remove(current)
                visited.add(current)
                continue
            if dependency in visiting:
                raise DomainError("dependency cycle")
            if dependency in visited:
                continue
            if dependency not in tasks:
                raise DomainError(f"unknown dependency {dependency}", "UNKNOWN")
            visiting.add(dependency)
            stack.append((dependency, iter(tasks[dependency].get("deps", []) + tasks[dependency].get("outputs", []))))


class _BoardBase(Protocol):
    def connect(self) -> AbstractContextManager[Any]:
        raise NotImplementedError

    def claim(self, actor: str, item_id: str) -> Any:
        raise NotImplementedError

    def reserve(self, actor: str, subject: str, detail: str) -> Any:
        raise NotImplementedError

    def done(self, actor: str, item_id: str, summary: str, files=None, request_id=None) -> Any:
        raise NotImplementedError


class DomainMixin:
    """Methods execute only inside inherited board transactions/auth boundaries."""
    if TYPE_CHECKING:
        actors: Any
        path: Any
        workspace: Any

        @staticmethod
        def append(db: Any, actor: str, kind: str, payload: Any) -> int:
            raise NotImplementedError

        @staticmethod
        def last_read(db: Any, actor: str) -> int | None:
            raise NotImplementedError

        @staticmethod
        def last_sequence(db: Any) -> int:
            raise NotImplementedError

        def check_actor(self, actor: Any) -> None:
            raise NotImplementedError

        @staticmethod
        def fingerprint(args: Any) -> str:
            raise NotImplementedError

    def __init__(self, *args, **kwargs):
        self._transactions = threading.local()
        super().__init__(*args, **kwargs)

    @contextmanager
    def connect(self):
        # Keep legacy validation + inherited mutation in one transaction, not a TOCTOU pair.
        current = getattr(self._transactions, "db", None)
        if current is not None:
            yield current
            return
        with cast(_BoardBase, super()).connect() as db:
            self._transactions.db = db
            try:
                yield db
            finally:
                self._transactions.db = None

    def projection(self, db) -> dict[str, Any]:
        result = project_events(db.execute("SELECT sequence,actor,kind,payload FROM events ORDER BY sequence"), self.actors)
        # Optional module read projections must tolerate legacy DBs without their tables.
        try:
            from delm_leases import project
            result["leases"] = project(db)
        except ImportError:
            result["leases"] = []
        return result

    def queue_state(self, db) -> list[dict[str, Any]]:
        return self.projection(db)["queue"]

    def view(self, db, reader) -> dict[str, Any]:
        result = self.projection(db)
        result["reader"] = reader
        return result

    def served(self, db, actor, via, full=False) -> dict[str, Any]:
        # Compatibility read remains legacy consumption; v2 consumers use snapshot/ack.
        result = self.view(db, actor)
        previous = self.last_read(db, actor)
        result["full"] = full or previous is None
        if not result["full"]:
            result["events"] = [r for r in result["events"] if r["sequence"] > previous]
            result["notes"] = [r for r in result["notes"] if r["sequence"] > previous or r in result["blockers"]]
        self.append(db, actor, "read", dict(view=result, via=via))
        return result

    def _emit_task(self, db, actor, task):
        task = {k: v for k, v in task.items() if k not in ("blockers", "readiness")}
        task["domain"] = True
        task["revision"] = self.last_sequence(db) + 1
        self.append(db, actor, "task", dict(task=task))
        return task

    def _new_task(self, args):
        return dict(id=uuid.uuid4().hex, subject=text(args.get("subject"), "subject", 512),
                    detail=text(args.get("detail"), "detail"), state="open", owner=None,
                    generation=0, revision=0, deps=strings(args.get("deps", []), "deps"),
                    criteria=strings(args.get("criteria", []), "criteria"), parent=args.get("parent"),
                    outputs=[], mapping={}, domain=True)

    def domain(self, actor, args):
        self.check_actor(actor)
        if not isinstance(args, dict):
            raise DomainError("request must be an object")
        if "actor" in args:
            raise DomainError("actor identity comes from authentication")
        op = text(args.get("op"), "op", 64)
        with self.connect() as db:
            if op == "projection":
                return self.projection(db)
            if op == "pending":
                from delm_delivery import pending
                return {"receipts": pending(db, actor)}
            request_id = text(args.get("request_id"), "request_id", 256)
            fingerprint = self.fingerprint(args)
            db.execute("CREATE TABLE IF NOT EXISTS domain_requests (actor TEXT, request_id TEXT, fingerprint TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(actor,request_id))")
            prior = db.execute("SELECT fingerprint,response FROM domain_requests WHERE actor=? AND request_id=?", (actor, request_id)).fetchone()
            if prior:
                if prior[0] != fingerprint:
                    raise DomainError("request_id reused with changed payload", "CONFLICT")
                return _decode_json(prior[1], "cached domain response")
            projection = self.projection(db)
            tasks = {t["id"]: deepcopy(t) for t in projection["queue"]}
            if op == "snapshot":
                from delm_delivery import snapshot
                result = snapshot(db, actor, request_id, projection, args.get("full", False))
            elif op == "ack":
                from delm_delivery import ack
                result = ack(db, actor, args.get("receipt_id"))
            elif op == "publish":
                result = self._publication(db, actor, args, tasks, projection)
            elif op in ("lifecycle", "reclaim", "resume"):
                result = self._lifecycle(db, actor, op, args, tasks, projection)
            elif op.startswith("lease-"):
                from delm_leases import operate
                result = operate(db, actor, op.removeprefix("lease-"), args,
                                 workspace=getattr(self, "workspace", self.path.parent), tasks=tasks, append=self.append)
            else:
                result = self._task_operation(db, actor, op, args, tasks, projection)
            db.execute("INSERT INTO domain_requests VALUES (?,?,?,?)", (actor, request_id, fingerprint, json.dumps(result)))
            return result

    @staticmethod
    def _available(actor, projection):
        if any(s["actor"] == actor and s["state"] in ("ended", "blocked") for s in projection["sessions"]):
            raise DomainError("actor must reconcile lifecycle to active before acquiring work", "BLOCKED")

    def _lifecycle(self, db, actor, op, args, tasks, projection):
        sessions = {s["actor"]: s for s in projection["sessions"]}
        if op == "lifecycle":
            current = sessions[actor]
            if type(args.get("expected_generation")) is not int or args["expected_generation"] != current.get("generation", 0):
                raise DomainError("stale producer generation", "STALE")
            state = args.get("state")
            if state not in ("active", "idle", "ended", "blocked"):
                raise DomainError("invalid lifecycle state")
            reason = text(args.get("reason"), "reason")
            entry = dict(actor=actor, state=state, reason=reason, generation=current.get("generation", 0) + 1)
            self.append(db, actor, "lifecycle", entry)
            affected = []
            if state in ("ended", "blocked"):
                for task in tasks.values():
                    if task["owner"] == actor and task["state"] in ("claimed", "blocked"):
                        task.update(state="blocked", blocked_reason=reason, producer_generation=entry["generation"],
                                    generation=task["generation"] + 1)
                        affected.append(self._emit_task(db, actor, task))
            return dict(lifecycle=entry, tasks=affected)
        task = self._owned(actor, args, tasks, claimed=False)
        if type(args.get("generation")) is not int or args["generation"] != task["generation"]:
            raise DomainError("stale task generation", "STALE")
        if task["state"] != "blocked":
            raise DomainError("only explicitly blocked task can be reconciled", "BLOCKED")
        producer = sessions.get(task["owner"], {})
        summary = text(args.get("summary"), "summary")
        if op == "reclaim":
            if producer.get("state") != "ended" or type(args.get("producer_generation")) is not int or args["producer_generation"] != producer.get("generation"):
                raise DomainError("producer must explicitly be ended at expected generation", "BLOCKED")
            if task["owner"] == actor or args.get("acknowledge_external_writes") is not True:
                raise DomainError("reclaim needs another actor and explicit external-write salvage acknowledgement", "BLOCKED")
            self._available(actor, projection)
            self._free(actor, tasks)
        else:
            if task["owner"] != actor or sessions[actor].get("state") != "active":
                raise DomainError("only active owner may resume its blocked work", "BLOCKED")
            self._free(actor, tasks, task["id"])
        task.update(owner=actor, state="claimed", generation=task["generation"] + 1, handoff=summary)
        task.pop("blocked_reason", None)
        task.pop("producer_generation", None)
        return dict(task=self._emit_task(db, actor, task), advisory=True)

    def _publication(self, db, actor, args, tasks, projection):
        kind = args.get("type")
        if kind not in ("FACT", "FAIL", "CORRECTION", "RESOLUTION"):
            raise DomainError("invalid publication type")
        task = args.get("task")
        related = strings(args.get("related", []), "related")
        output = args.get("output")
        for identity in [task, output, *related]:
            if identity is not None and (not isinstance(identity, str) or identity not in tasks):
                raise DomainError("unknown linked task", "UNKNOWN")
        readiness = args.get("readiness", False)
        if type(readiness) is not bool:
            raise DomainError("readiness must be boolean")
        if readiness and (kind == "FAIL" or not output or tasks[output]["state"] != "done" or tasks[output]["blockers"]):
            raise DomainError("ready publication needs a completed nonblocked output", "BLOCKED")
        resolves = strings(args.get("resolves", []), "resolves")
        if (resolves and kind not in ("CORRECTION", "RESOLUTION")) or (kind == "RESOLUTION" and not resolves):
            raise DomainError("only explicit correction/resolution may resolve publications")
        existing = {n["id"]: n for n in projection["notes"]}
        for identity in resolves:
            prior = existing.get(identity)
            if prior is None:
                raise DomainError("unknown publication to resolve", "UNKNOWN")
            owners = {tasks[i]["owner"] for i in [prior.get("task"), *prior.get("related", [])] if i in tasks}
            if actor != prior["actor"] and actor not in owners:
                raise DomainError("only author or linked task owner may resolve", "CONFLICT")
        limitations = args.get("limitations", "")
        if not isinstance(limitations, str) or len(limitations) > 8192:
            raise DomainError("invalid limitations")
        publication = dict(id=uuid.uuid4().hex, type=kind, text=text(args.get("text"), "text"), task=task,
                           related=related, output=output, readiness=readiness, limitations=limitations, resolves=resolves)
        sequence = self.append(db, actor, "publication", publication)
        return dict(publication=dict(publication, actor=actor, sequence=sequence))

    def _owned(self, actor, args, tasks, claimed=True):
        task = tasks.get(args.get("item"))
        if task is None:
            raise DomainError("unknown task", "UNKNOWN")
        if type(args.get("expected_revision")) is not int or args["expected_revision"] != task["revision"]:
            raise DomainError("stale task revision", "STALE")
        if claimed and (task["owner"] != actor or task["state"] != "claimed"):
            raise DomainError("only claimed task owner may mutate", "CONFLICT")
        if claimed and (type(args.get("generation")) is not int or args["generation"] != task["generation"]):
            raise DomainError("stale ownership generation", "STALE")
        return task

    @staticmethod
    def _free(actor, tasks, except_id=None):
        if any(t["owner"] == actor and t["state"] in ("claimed", "blocked") and t["id"] != except_id for t in tasks.values()):
            raise DomainError("actor already owns unfinished work", "CONFLICT")

    def _task_operation(self, db, actor, op, args, tasks, projection):
        if op == "create":
            task = self._new_task(args)
            if task["parent"] is not None:
                raise DomainError("use owned split to create mapped children")
            tasks[task["id"]] = task
            validate_graph(tasks)
            return dict(task=self._emit_task(db, actor, task))
        if op not in ("claim", "update", "split", "release", "handoff", "complete"):
            raise DomainError("unknown domain operation")
        task = self._owned(actor, args, tasks, claimed=op != "claim")
        if op == "claim":
            self._available(actor, projection)
            if not task.get("readiness"):
                raise DomainError("task is not open and ready", "BLOCKED")
            self._free(actor, tasks)
            task.update(state="claimed", owner=actor, generation=task["generation"] + 1)
        elif op == "update":
            changes = args.get("changes")
            if not isinstance(changes, dict) or not changes or set(changes) - {"subject", "detail", "deps", "criteria"}:
                raise DomainError("invalid changes")
            for k, v in changes.items():
                if k == "criteria" and task["outputs"]:
                    raise DomainError("cannot change mapped parent criteria after split")
                task[k] = strings(v, k) if k in ("deps", "criteria") else text(v, k, 512 if k == "subject" else 8192)
            validate_graph(tasks)
        elif op == "split":
            children = args.get("children")
            if not isinstance(children, list) or not 1 <= len(children) <= 64:
                raise DomainError("split needs 1..64 children")
            created = []
            covered = set()
            for child in children:
                if not isinstance(child, dict):
                    raise DomainError("child must be an object")
                mapping = strings(child.get("mapping", []), "mapping")
                if not mapping or not set(mapping) <= set(task["criteria"]):
                    raise DomainError("child mapping must reference parent criteria")
                covered.update(mapping)
                t = self._new_task(child)
                t["parent"] = task["id"]
                tasks[t["id"]] = t
                task["outputs"].append(t["id"])
                task["mapping"][t["id"]] = mapping
                created.append(t)
            if covered != set(task["criteria"]):
                raise DomainError("split must preserve coverage of every parent criterion")
            validate_graph(tasks)
            created = [self._emit_task(db, actor, c) for c in created]
            return dict(task=self._emit_task(db, actor, task), children=created)
        elif op in ("release", "handoff"):
            task["handoff"] = text(args.get("summary"), "summary")
            task.update(state="open", owner=None, generation=task["generation"] + 1)
            if op == "handoff":
                recipient = args.get("to")
                self.check_actor(recipient)
                self._available(recipient, projection)
                self._free(recipient, tasks, task["id"])
                if recipient == actor:
                    raise DomainError("handoff needs another actor")
                task.update(state="claimed", owner=recipient)
        elif op == "complete":
            if task.get("blockers") or any(tasks[i]["state"] != "done" for i in task["deps"] + task["outputs"]):
                raise DomainError("dependencies, outputs or FAIL unresolved", "BLOCKED")
            task.update(state="done", summary=text(args.get("summary"), "summary"))
        return dict(task=self._emit_task(db, actor, task))

    def claim(self, actor, item_id):
        with self.connect() as db:
            self._available(actor, self.projection(db))
            task = next((t for t in self.queue_state(db) if t["id"] == item_id), None)
            if task and task.get("domain"):
                raise DomainError("use domain claim with expected_revision", "STALE")
            self._free(actor, {t["id"]: t for t in self.queue_state(db)}, item_id)
            return cast(_BoardBase, super()).claim(actor, item_id)

    def reserve(self, actor, subject, detail):
        text(subject, "subject", 512)
        with self.connect() as db:
            self._available(actor, self.projection(db))
            queue = self.queue_state(db)
            matching = next((t for t in queue if " ".join(t["subject"].lower().split()) == " ".join(subject.lower().split())), None)
            if matching and matching.get("domain"):
                raise DomainError("use domain claim with expected_revision", "STALE")
            self._free(actor, {t["id"]: t for t in queue}, matching["id"] if matching else None)
            return cast(_BoardBase, super()).reserve(actor, subject, detail)

    def done(self, actor, item_id, summary, files=None, request_id=None):
        with self.connect() as db:
            task = next((t for t in self.queue_state(db) if t["id"] == item_id), None)
            if task and task.get("domain"):
                raise DomainError("use domain complete with generation and revision", "STALE")
            return cast(_BoardBase, super()).done(actor, item_id, summary, files, request_id)
