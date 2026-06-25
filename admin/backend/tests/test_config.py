"""Tests für die M2-Konfigurationslogik (Whitelist, Validierung, atomares Schreiben)."""
import json

import pytest

from app.config_schema import (
    EDITABLE_KEYS,
    apply_updates,
    validate_updates,
    ValidationError,
)


# --- Whitelist & Validierung ---

def test_valid_id_and_keyword():
    clean, errors = validate_updates(
        {"GIF_ID": "123456789012345678", "SPAM_KEYWORD": "  oof  "}, can_write=True
    )
    assert errors == {}
    assert clean["GIF_ID"] == 123456789012345678
    assert clean["SPAM_KEYWORD"] == "oof"


def test_unknown_key_rejected():
    clean, errors = validate_updates({"EVIL_KEY": "x"}, can_write=True)
    assert "EVIL_KEY" in errors
    assert clean == {}


def test_non_numeric_id_rejected():
    clean, errors = validate_updates({"GIF_ID": "nicht-numerisch"}, can_write=True)
    assert "GIF_ID" in errors and clean == {}


def test_idlist_validation():
    clean, errors = validate_updates(
        {"BLOCKED_CHANNEL_IDS": ["111111", 222222]}, can_write=True
    )
    assert errors == {}
    assert clean["BLOCKED_CHANNEL_IDS"] == [111111, 222222]


def test_hostlist_valid_and_invalid():
    clean, errors = validate_updates(
        {"GIF_ALLOWED_DOMAINS": ["Tenor.com", "klipy.com"]}, can_write=True
    )
    assert clean["GIF_ALLOWED_DOMAINS"] == ["tenor.com", "klipy.com"]
    _, errors2 = validate_updates(
        {"GIF_ALLOWED_DOMAINS": ["not a host"]}, can_write=True
    )
    assert "GIF_ALLOWED_DOMAINS" in errors2


def test_bool_is_not_a_valid_id():
    _, errors = validate_updates({"GIF_ID": True}, can_write=True)
    assert "GIF_ID" in errors


def test_secret_key_write_forbidden():
    with pytest.raises(PermissionError):
        validate_updates({"TOKEN": "abc"}, can_write=True)
    with pytest.raises(PermissionError):
        validate_updates({"TURNIER_SERVICE_TOKEN": "abc"}, can_write=True)


def test_no_write_permission_raises():
    with pytest.raises(PermissionError):
        validate_updates({"GIF_ID": "123456"}, can_write=False)


def test_body_must_be_object():
    with pytest.raises(ValidationError):
        validate_updates(["not", "a", "dict"], can_write=True)


def test_string_too_long_rejected():
    _, errors = validate_updates({"SPAM_KEYWORD": "x" * 201}, can_write=True)
    assert "SPAM_KEYWORD" in errors


def test_empty_string_rejected():
    _, errors = validate_updates({"SPAM_KEYWORD": "   "}, can_write=True)
    assert "SPAM_KEYWORD" in errors


def test_empty_lists_rejected():
    _, e1 = validate_updates({"GIF_ALLOWED_DOMAINS": []}, can_write=True)
    assert "GIF_ALLOWED_DOMAINS" in e1
    # idlist mit Nicht-Listen-Wert (String) wird abgelehnt
    _, e2 = validate_updates({"BLOCKED_CHANNEL_IDS": "111,222"}, can_write=True)
    assert "BLOCKED_CHANNEL_IDS" in e2


def test_token_not_in_editable_whitelist():
    assert "TOKEN" not in EDITABLE_KEYS
    assert "TURNIER_SERVICE_TOKEN" not in EDITABLE_KEYS


# --- Merge erhält Fremd-Keys ---

def test_apply_updates_preserves_foreign_keys():
    existing = {"TOKEN": "geheim", "GIF_ID": 1, "TURNIER_API_URL": "http://x"}
    merged = apply_updates(existing, {"GIF_ID": 999})
    assert merged["GIF_ID"] == 999
    assert merged["TOKEN"] == "geheim"  # Secret bleibt unangetastet
    assert merged["TURNIER_API_URL"] == "http://x"
    assert existing["GIF_ID"] == 1  # Original nicht mutiert


# --- Atomares Schreiben/Lesen ---

def test_atomic_write_roundtrip_preserves_foreign(tmp_path, monkeypatch):
    from app import bot_config
    from app.config import settings

    target = tmp_path / "config.json"
    target.write_text(json.dumps({"TOKEN": "geheim", "GIF_ID": 1}), encoding="utf-8")
    monkeypatch.setattr(settings, "BOT_CONFIG_PATH", str(target))

    existing = bot_config.read_config()
    clean, errors = validate_updates({"GIF_ID": "777777"}, can_write=True)
    assert errors == {}
    bot_config.write_config(apply_updates(existing, clean))

    result = json.loads(target.read_text(encoding="utf-8"))
    assert result["GIF_ID"] == 777777
    assert result["TOKEN"] == "geheim"
    # Keine Temp-Reste im Verzeichnis
    assert [p.name for p in tmp_path.iterdir()] == ["config.json"]
