"""Lesen/atomares Schreiben der gemounteten Bot-config.json (M2)."""
import json
import os
import tempfile

from .config import settings


class BotConfigError(RuntimeError):
    pass


def read_config():
    """Liest die config.json. Fehlt sie, leeres dict (UI zeigt dann Defaults).

    Eine vorhandene, aber kaputte Datei führt zu BotConfigError (kein roher
    500/Stacktrace) — und blockt vor allem ein Schreiben, das die kaputte Datei
    sonst weiter verschlimmern könnte.
    """
    path = settings.BOT_CONFIG_PATH
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise BotConfigError(f"config.json nicht lesbar: {exc}") from exc


def write_config(data):
    """Schreibt die config.json atomar (Temp-Datei + os.replace).

    Der parallel lesende Bot sieht dadurch nie eine halb geschriebene Datei.
    Schreibt im selben Verzeichnis, damit os.replace atomar bleibt (gleiches FS).
    """
    path = settings.BOT_CONFIG_PATH
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".config.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        # Aufräumen, falls der Tausch nicht zustande kam.
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
