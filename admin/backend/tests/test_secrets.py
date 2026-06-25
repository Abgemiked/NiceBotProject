"""Tests für die .env-Secret-Verwaltung (Whitelist, atomares Schreiben)."""
import pytest

from app import env_secrets
from app.config import settings
from app.env_secrets import EnvError, read_secrets, write_secrets


@pytest.fixture
def env(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text(
        "# Bot config\n"
        "NICEBOT_TOKEN=alt_token\n"
        "TURNIER_API_URL=http://turnier-backend:3130\n"
        "TURNIER_SERVICE_TOKEN=svc_geheim\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "BOT_ENV_PATH", str(path))
    return path


def test_read_secrets_returns_whitelist(env):
    secrets = {s["key"]: s for s in read_secrets()}
    assert secrets["NICEBOT_TOKEN"]["value"] == "alt_token"
    assert secrets["NICEBOT_TOKEN"]["set"] is True
    assert secrets["TURNIER_SERVICE_TOKEN"]["value"] == "svc_geheim"
    # Nur Whitelist-Keys, kein TURNIER_API_URL
    assert set(secrets.keys()) == {"NICEBOT_TOKEN", "TURNIER_SERVICE_TOKEN"}


def test_write_updates_and_preserves_other_lines(env):
    changed = write_secrets({"NICEBOT_TOKEN": "neu_token"})
    assert changed == ["NICEBOT_TOKEN"]
    text = env.read_text(encoding="utf-8")
    assert "NICEBOT_TOKEN=neu_token" in text
    assert "TURNIER_SERVICE_TOKEN=svc_geheim" in text  # unangetastet
    assert "TURNIER_API_URL=http://turnier-backend:3130" in text  # Fremd-Key bleibt
    assert text.startswith("# Bot config")  # Kommentar bleibt


def test_write_rejects_non_whitelist(env):
    with pytest.raises(EnvError):
        write_secrets({"TURNIER_API_URL": "http://evil"})


def test_write_rejects_empty(env):
    with pytest.raises(EnvError):
        write_secrets({"NICEBOT_TOKEN": "   "})


def test_write_rejects_newline_injection(env):
    with pytest.raises(EnvError):
        write_secrets({"NICEBOT_TOKEN": "tok\nEVIL=1"})
    # .env darf nicht durch die EVIL-Zeile verseucht sein
    assert "EVIL=1" not in env.read_text(encoding="utf-8")


def test_write_rejects_no_changes(env):
    with pytest.raises(EnvError):
        write_secrets({})


def test_write_appends_missing_key(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("NICEBOT_TOKEN=x\n", encoding="utf-8")
    monkeypatch.setattr(settings, "BOT_ENV_PATH", str(path))
    write_secrets({"TURNIER_SERVICE_TOKEN": "neu_svc"})
    assert "TURNIER_SERVICE_TOKEN=neu_svc" in path.read_text(encoding="utf-8")


def test_read_missing_file_returns_unset(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "BOT_ENV_PATH", str(tmp_path / "nope.env"))
    secrets = {s["key"]: s for s in read_secrets()}
    assert secrets["NICEBOT_TOKEN"]["set"] is False
    assert secrets["NICEBOT_TOKEN"]["value"] == ""
