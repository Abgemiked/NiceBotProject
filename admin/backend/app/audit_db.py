"""Zugriff auf das Audit-Log (M5).

Liest die vom Bot geschriebene audit_log-Tabelle (gemeinsames data-Volume) und
schreibt zusätzlich Admin-Overrides (Level/Config-Änderungen aus dem Web-Tool).
Schema identisch zur Bot-Seite (audit_log.py). Tabelle wird idempotent angelegt,
falls der Bot sie noch nicht erzeugt hat.
"""
import json
import sqlite3
from datetime import datetime, timezone

from .config import settings

EVENT_TYPES = ("message_delete", "member_leave", "dm_sent", "admin_override")
PAGE_SIZE_MAX = 100

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    actor_id    TEXT,
    actor_name  TEXT,
    target_id   TEXT,
    target_name TEXT,
    channel_id  TEXT,
    content     TEXT,
    meta        TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type);
"""


def _connect():
    conn = sqlite3.connect(settings.AUDIT_DB_PATH, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _row(r):
    meta = None
    if r["meta"]:
        try:
            meta = json.loads(r["meta"])
        except (ValueError, TypeError):
            meta = r["meta"]
    return {
        "id": r["id"], "ts": r["ts"], "event_type": r["event_type"],
        "actor_id": r["actor_id"], "actor_name": r["actor_name"],
        "target_id": r["target_id"], "target_name": r["target_name"],
        "channel_id": r["channel_id"], "content": r["content"], "meta": meta,
    }


def normalize_params(event_type=None, page=1, page_size=25):
    et = event_type if event_type in EVENT_TYPES else None
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = 25
    page_size = min(PAGE_SIZE_MAX, max(1, page_size))
    return et, page, page_size


def list_events(event_type=None, page=1, page_size=25):
    et, page, page_size = normalize_params(event_type, page, page_size)
    where, params = ("WHERE event_type = ?", [et]) if et else ("", [])
    offset = (page - 1) * page_size
    conn = _connect()
    try:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM audit_log {where}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT * FROM audit_log {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
    finally:
        conn.close()
    return {"items": [_row(r) for r in rows], "total": total,
            "page": page, "page_size": page_size}


def log_admin_override(actor_id, actor_name, target_id, target_name, meta):
    """Schreibt einen Admin-Override-Eintrag (best effort, schluckt Fehler)."""
    try:
        ts = datetime.now(timezone.utc).isoformat()
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO audit_log (ts, event_type, actor_id, actor_name, "
                "target_id, target_name, content, meta) VALUES (?,?,?,?,?,?,?,?)",
                (ts, "admin_override", _s(actor_id), _s(actor_name),
                 _s(target_id), _s(target_name), None,
                 json.dumps(meta, ensure_ascii=False) if meta is not None else None),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:  # Audit darf die eigentliche Aktion nie scheitern lassen
        print(f"[audit_db] override-log fehlgeschlagen: {exc}")


def _s(value):
    return str(value) if value is not None else None
