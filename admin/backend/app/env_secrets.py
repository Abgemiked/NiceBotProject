"""Lesen/atomares Schreiben der Laufzeit-Secrets in der gemounteten Bot-.env.

Nur eine Whitelist bekannter Secret-Keys ist sicht-/änderbar. Alle übrigen
.env-Zeilen (andere Keys, Kommentare, Leerzeilen) bleiben beim Schreiben exakt
erhalten. Reine Datei-IO + Parsing → testbar.
"""
import os
import re

from .config import settings

# Verwaltbare Secret-Keys in der Bot-.env (Anzeige-Label fürs UI).
SECRET_ENV_KEYS = {
    "NICEBOT_TOKEN": "Bot-Token",
    "TURNIER_SERVICE_TOKEN": "Turnier-Service-Token",
}

_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


class EnvError(RuntimeError):
    pass


def _parse(text):
    """Liefert {key: value} für alle KEY=VALUE-Zeilen (Werte unverändert)."""
    out = {}
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def read_secrets():
    """Liefert für jeden Whitelist-Key {key, label, value, set}.

    value ist der Klartext (nur an Voll-Admin ausgeliefert; das Frontend
    verbirgt ihn standardmäßig hinter einem Augen-Toggle).
    """
    path = settings.BOT_ENV_PATH
    parsed = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                parsed = _parse(f.read())
        except OSError as exc:
            raise EnvError(f".env nicht lesbar: {exc}") from exc
    result = []
    for key, label in SECRET_ENV_KEYS.items():
        val = parsed.get(key, "")
        result.append({"key": key, "label": label, "value": val, "set": bool(val)})
    return result


def write_secrets(updates):
    """Aktualisiert Whitelist-Keys in der .env (atomar, andere Zeilen erhalten).

    updates: {key: value}. Nicht-Whitelist-Keys → EnvError. Leere Werte → EnvError
    (ein Secret soll nicht versehentlich geleert werden). Gibt Liste der
    geänderten Keys zurück.
    """
    if not isinstance(updates, dict) or not updates:
        raise EnvError("Keine Änderungen")
    for key, value in updates.items():
        if key not in SECRET_ENV_KEYS:
            raise EnvError(f"Unbekannter Secret-Key: {key}")
        if not isinstance(value, str) or not value.strip():
            raise EnvError(f"{key} darf nicht leer sein")
        # Newline-Injection verhindern (sonst ließe sich eine neue .env-Zeile einschleusen).
        if "\n" in value or "\r" in value:
            raise EnvError(f"{key} darf keine Zeilenumbrüche enthalten")

    path = settings.BOT_ENV_PATH
    lines = []
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

    remaining = dict(updates)
    new_lines = []
    for line in lines:
        m = _LINE_RE.match(line)
        if m and m.group(1) in remaining:
            key = m.group(1)
            new_lines.append(f"{key}={remaining.pop(key)}")
        else:
            new_lines.append(line)
    # Noch nicht vorhandene Keys anhängen.
    for key, value in remaining.items():
        new_lines.append(f"{key}={value}")

    # In-Place-Write: Die .env ist ein Single-File-Bind-Mount. os.replace würde
    # die Inode tauschen und den Mount entkoppeln (Schreibvorgänge verpuffen /
    # EBUSY). Daher gesamten Inhalt in einem Rutsch in dieselbe Datei schreiben.
    content = "\n".join(new_lines) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    return sorted(updates.keys())
