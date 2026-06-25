"""Tests für die M5-Audit-Log-Logik (gegen Temp-SQLite)."""
import json

import pytest

from app import audit_db
from app.audit_db import normalize_params
from app.config import settings


@pytest.fixture
def adb(tmp_path, monkeypatch):
    path = tmp_path / "audit_log.db"
    monkeypatch.setattr(settings, "AUDIT_DB_PATH", str(path))
    # _connect() legt die Tabelle idempotent an → erst Seed über die API.
    conn = audit_db._connect()
    conn.executemany(
        "INSERT INTO audit_log (ts, event_type, target_name) VALUES (?,?,?)",
        [
            ("2026-06-25T10:00:00+00:00", "message_delete", "alice"),
            ("2026-06-25T10:01:00+00:00", "member_leave", "bob"),
            ("2026-06-25T10:02:00+00:00", "message_delete", "charlie"),
            ("2026-06-25T10:03:00+00:00", "dm_sent", "dave"),
        ],
    )
    conn.commit()
    conn.close()
    return path


def test_normalize_params_filters_unknown_type():
    assert normalize_params(event_type="bogus")[0] is None
    assert normalize_params(event_type="dm_sent")[0] == "dm_sent"
    assert normalize_params(page=-3)[1] == 1
    assert normalize_params(page_size=9999)[2] == 100


def test_list_all_newest_first(adb):
    res = audit_db.list_events()
    assert res["total"] == 4
    # ORDER BY id DESC → zuletzt eingefügt zuerst
    assert res["items"][0]["target_name"] == "dave"


def test_filter_by_type(adb):
    res = audit_db.list_events(event_type="message_delete")
    assert res["total"] == 2
    assert {i["target_name"] for i in res["items"]} == {"alice", "charlie"}


def test_pagination(adb):
    res = audit_db.list_events(page=1, page_size=2)
    assert len(res["items"]) == 2 and res["total"] == 4
    res2 = audit_db.list_events(page=2, page_size=2)
    assert len(res2["items"]) == 2
    # keine Überschneidung
    ids = {i["id"] for i in res["items"]} & {i["id"] for i in res2["items"]}
    assert ids == set()


def test_unknown_filter_returns_all(adb):
    # Unbekannter event_type wird ignoriert → alle Einträge
    assert audit_db.list_events(event_type="DROP TABLE")["total"] == 4


def test_log_admin_override_roundtrip(adb):
    audit_db.log_admin_override(
        actor_id="111", actor_name="admin", target_id="222", target_name="victim",
        meta={"scope": "level", "old": {"level": 5}, "new": {"level": 6}},
    )
    res = audit_db.list_events(event_type="admin_override")
    assert res["total"] == 1
    row = res["items"][0]
    assert row["actor_name"] == "admin" and row["target_id"] == "222"
    assert row["meta"]["new"]["level"] == 6


def test_meta_json_parsed_in_row(adb):
    audit_db.log_admin_override("1", "a", "2", "b", meta={"k": "v"})
    row = audit_db.list_events(event_type="admin_override")["items"][0]
    assert isinstance(row["meta"], dict) and row["meta"]["k"] == "v"
    # Sicherstellen, dass meta wirklich als JSON gespeichert wurde
    assert json.dumps(row["meta"])
