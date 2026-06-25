"""Tests für die M3-Level-DB-Logik (gegen Temp-SQLite mit users-Schema)."""
import sqlite3

import pytest

from app import level_db
from app.config import settings
from app.level_db import (
    LevelValidationError,
    normalize_list_params,
    validate_update,
)


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "level_system.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE users (user_id INTEGER PRIMARY KEY, exp INTEGER DEFAULT 0, "
        "level INTEGER DEFAULT 1, username TEXT)"
    )
    conn.executemany(
        "INSERT INTO users (user_id, exp, level, username) VALUES (?,?,?,?)",
        [
            (1, 50, 2, "alice"),
            (2, 300, 5, "bob"),
            (3, 10, 1, "charlie"),
            (4, 999, 9, "dave_50%"),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(settings, "LEVEL_DB_PATH", str(path))
    return path


# --- normalize_list_params (rein) ---

def test_normalize_defaults_and_whitelist():
    assert normalize_list_params(sort="level", direction="desc")[:2] == ("level", "DESC")
    # Nicht-Whitelist-Sort fällt auf level zurück (SQL-Injection-Schutz)
    assert normalize_list_params(sort="level; DROP TABLE users")[0] == "level"
    assert normalize_list_params(direction="asc")[1] == "ASC"


def test_normalize_page_clamping():
    assert normalize_list_params(page=-5)[2] == 1
    assert normalize_list_params(page="abc")[2] == 1
    assert normalize_list_params(page_size=9999)[3] == 100
    assert normalize_list_params(page_size=0)[3] == 1


# --- list_users ---

def test_list_sort_and_pagination(db):
    res = level_db.list_users(sort="level", direction="desc", page=1, page_size=2)
    assert res["total"] == 4
    assert [u["username"] for u in res["items"]] == ["dave_50%", "bob"]
    res2 = level_db.list_users(sort="level", direction="desc", page=2, page_size=2)
    assert [u["username"] for u in res2["items"]] == ["alice", "charlie"]


def test_search_by_username(db):
    res = level_db.list_users(search="bob")
    assert res["total"] == 1 and res["items"][0]["username"] == "bob"


def test_search_by_user_id(db):
    res = level_db.list_users(search="3")
    assert res["total"] == 1 and res["items"][0]["username"] == "charlie"


def test_search_like_wildcards_are_escaped(db):
    # '%' darf nicht als Wildcard wirken — nur dave_50% enthält es wörtlich.
    res = level_db.list_users(search="50%")
    assert res["total"] == 1 and res["items"][0]["username"] == "dave_50%"


def test_injection_sort_does_not_break(db):
    # Bösartiger sort-Wert wird ignoriert, Query läuft normal.
    res = level_db.list_users(sort="username); DROP TABLE users;--")
    assert res["total"] == 4


def test_user_id_returned_as_string(db):
    res = level_db.list_users(search="1")
    assert isinstance(res["items"][0]["user_id"], str)


# --- get_user / update_user ---

def test_get_user(db):
    assert level_db.get_user(2)["username"] == "bob"
    assert level_db.get_user(999) is None


def test_update_user_hit_and_miss(db):
    assert level_db.update_user(1, level=7, exp=123) == 1
    assert level_db.get_user(1)["level"] == 7
    assert level_db.get_user(1)["exp"] == 123
    assert level_db.update_user(999, level=1, exp=0) == 0


# --- validate_update ---

def test_validate_bounds():
    assert validate_update(1, 0) == (1, 0)
    with pytest.raises(LevelValidationError):
        validate_update(0, 0)  # level < 1
    with pytest.raises(LevelValidationError):
        validate_update(1001, 0)  # level > max
    with pytest.raises(LevelValidationError):
        validate_update(1, -1)  # exp < 0
    with pytest.raises(LevelValidationError):
        validate_update(1, 10_000_001)  # exp > max


def test_validate_rejects_bool_and_nonint():
    with pytest.raises(LevelValidationError):
        validate_update(True, 0)
    with pytest.raises(LevelValidationError):
        validate_update(1, "5")
    with pytest.raises(LevelValidationError):
        validate_update(1, None)
