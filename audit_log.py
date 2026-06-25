"""Persistentes Audit-Log für NiceBot (M5).

Schreibt Moderations-/Bot-Aktionen (gelöschte Nachrichten, Member-Leaves,
gesendete DMs) sowie Admin-Overrides aus dem Web-Tool in eine separate SQLite.

WICHTIG: Audit-Schreibfehler dürfen den Bot NIEMALS beeinträchtigen — alle
Funktionen sind exception-tolerant (sie loggen auf stderr und kehren zurück,
statt zu werfen). Die DB liegt standardmäßig neben der Level-DB im data-Volume,
sodass das Web-Verwaltungstool sie über denselben Mount lesen kann.
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

# Pfad: explizit via AUDIT_DB_PATH, sonst neben DB_PATH (Level-DB), sonst lokal.
_DEFAULT = os.path.join(os.path.dirname(os.environ.get("DB_PATH", "")) or ".",
                        "audit_log.db")
AUDIT_DB_PATH = os.environ.get("AUDIT_DB_PATH", _DEFAULT)

# DSGVO-Härtung: Aufbewahrungsfrist (Speicherbegrenzung Art. 5) + optionale
# Speicherung von Nachrichteninhalten (Datenminimierung). Per ENV steuerbar.
try:
    AUDIT_RETENTION_DAYS = int(os.environ.get("AUDIT_RETENTION_DAYS", "60"))
except (TypeError, ValueError):
    AUDIT_RETENTION_DAYS = 60
AUDIT_STORE_CONTENT = os.environ.get("AUDIT_STORE_CONTENT", "1") not in ("0", "false", "False")

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


def init_db():
    """Legt Tabelle + Indizes an (idempotent, exception-tolerant)."""
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH, timeout=5.0)
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:  # niemals den Bot brechen
        print(f"[audit_log] init fehlgeschlagen: {exc}")


def log_event(event_type, actor_id=None, actor_name=None, target_id=None,
              target_name=None, channel_id=None, content=None, meta=None):
    """Schreibt eine Audit-Zeile. Schluckt alle Fehler (best effort)."""
    try:
        ts = datetime.now(timezone.utc).isoformat()
        # Datenminimierung: Inhalte nur speichern, wenn aktiviert (Default an).
        if not AUDIT_STORE_CONTENT:
            content = None
        else:
            content = (content or "")[:1000] if content is not None else None
        meta_json = json.dumps(meta, ensure_ascii=False) if meta is not None else None
        conn = sqlite3.connect(AUDIT_DB_PATH, timeout=5.0)
        try:
            conn.execute(
                "INSERT INTO audit_log (ts, event_type, actor_id, actor_name, "
                "target_id, target_name, channel_id, content, meta) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (ts, str(event_type),
                 _s(actor_id), _s(actor_name), _s(target_id), _s(target_name),
                 _s(channel_id), content, meta_json),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        print(f"[audit_log] log_event fehlgeschlagen ({event_type}): {exc}")


def purge_old(retention_days=None):
    """Löscht Audit-Einträge älter als die Aufbewahrungsfrist (Art. 5 DSGVO).
    Exception-tolerant; gibt die Zahl gelöschter Zeilen zurück (0 bei Fehler)."""
    days = AUDIT_RETENTION_DAYS if retention_days is None else retention_days
    if not days or days <= 0:
        return 0
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(AUDIT_DB_PATH, timeout=5.0)
        try:
            cur = conn.execute("DELETE FROM audit_log WHERE ts < ?", (cutoff,))
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()
    except Exception as exc:
        print(f"[audit_log] purge fehlgeschlagen: {exc}")
        return 0


def _s(value):
    return str(value) if value is not None else None
