"""Lossless board deliveries inside the caller's existing SQLite transaction.

A snapshot is not an acknowledgement. Neither observers nor lost responses move
this cursor, and the legacy read cursor is deliberately unrelated.
"""
import json
import uuid


class DeliveryError(ValueError):
    def __init__(self, message, code="INVALID"):
        super().__init__(message)
        self.code = code


def _schema(db):
    if not db.in_transaction:
        raise DeliveryError("delivery requires caller transaction")
    db.execute("""CREATE TABLE IF NOT EXISTS delm_delivery_cursors (
        actor TEXT PRIMARY KEY, sequence INTEGER NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS delm_deliveries (
        receipt_id TEXT PRIMARY KEY, actor TEXT NOT NULL, request_id TEXT NOT NULL,
        requested_full INTEGER NOT NULL, to_sequence INTEGER NOT NULL,
        receipt TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0,
        UNIQUE(actor,request_id))""")


def _identifier(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise DeliveryError(f"{name} must be a nonempty string of at most 256 characters")


def snapshot(db, actor, request_id, projection, full=False):
    """Persist an immutable response; replay uses its original sequence and body."""
    _identifier(actor, "actor")
    _identifier(request_id, "request_id")
    if not isinstance(full, bool):
        raise DeliveryError("full must be boolean")
    _schema(db)
    previous = db.execute(
        "SELECT requested_full,receipt FROM delm_deliveries WHERE actor=? AND request_id=?",
        (actor, request_id)).fetchone()
    if previous:
        if bool(previous[0]) != full:
            raise DeliveryError("request_id reused with different full flag", "CONFLICT")
        return json.loads(previous[1])
    cursor = db.execute("SELECT sequence FROM delm_delivery_cursors WHERE actor=?", (actor,)).fetchone()
    start = cursor[0] if cursor else 0
    end = projection["sequence"]
    if not isinstance(end, int) or end < start:
        raise DeliveryError("projection sequence precedes acknowledged cursor", "STALE")
    actual_full = full or cursor is None
    # JSON roundtrip separates the frozen receipt from the caller's mutable projection.
    view = json.loads(json.dumps(projection, ensure_ascii=False))
    if not actual_full:
        view["events"] = [event for event in view.get("events", []) if event["sequence"] > start]
        unread_ids = {event["payload"].get("id") for event in view["events"]
                      if event["kind"] in ("note", "publication")}
        view["notes"] = [note for note in view.get("notes", []) if note.get("id") in unread_ids]
    view["full"] = actual_full
    receipt = dict(receipt_id=uuid.uuid4().hex, request_id=request_id, actor=actor,
                   from_sequence=start, to_sequence=end, full=actual_full, view=view)
    db.execute("""INSERT INTO delm_deliveries
        (receipt_id,actor,request_id,requested_full,to_sequence,receipt) VALUES (?,?,?,?,?,?)""",
        (receipt["receipt_id"], actor, request_id, int(full), end,
         json.dumps(receipt, ensure_ascii=False)))
    return receipt


def ack(db, actor, receipt_id):
    """Acknowledge a persisted receipt, never a caller-provided sequence."""
    _identifier(actor, "actor")
    _identifier(receipt_id, "receipt_id")
    _schema(db)
    row = db.execute("SELECT actor,to_sequence FROM delm_deliveries WHERE receipt_id=?",
                     (receipt_id,)).fetchone()
    if not row:
        raise DeliveryError("unknown delivery receipt", "UNKNOWN")
    if row[0] != actor:
        raise DeliveryError("receipt belongs to another actor", "CONFLICT")
    db.execute("""INSERT INTO delm_delivery_cursors(actor,sequence) VALUES (?,?)
        ON CONFLICT(actor) DO UPDATE SET sequence=MAX(sequence,excluded.sequence)""", (actor, row[1]))
    db.execute("UPDATE delm_deliveries SET acknowledged=1 WHERE actor=? AND to_sequence<=?", (actor, row[1]))
    sequence = db.execute("SELECT sequence FROM delm_delivery_cursors WHERE actor=?", (actor,)).fetchone()[0]
    return dict(receipt_id=receipt_id, actor=actor, acked_sequence=sequence)


def pending(db, actor):
    """All unacknowledged receipts, including after process reopen; no window cap."""
    _identifier(actor, "actor")
    _schema(db)
    return [json.loads(row[0]) for row in db.execute(
        "SELECT receipt FROM delm_deliveries WHERE actor=? AND acknowledged=0 ORDER BY rowid", (actor,))]
