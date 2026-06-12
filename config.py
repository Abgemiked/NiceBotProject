"""Zentrale Konfiguration für NiceBot.

Werte werden in dieser Reihenfolge aufgelöst:
1. Umgebungsvariable ``NICEBOT_<KEY>`` (z.B. NICEBOT_TOKEN)
2. Umgebungsvariable ``<KEY>`` (z.B. TOKEN)
3. config.json (Pfad via CONFIG_PATH überschreibbar, Default ./config.json)

Eine optionale .env-Datei wird geladen, wenn python-dotenv installiert ist.
"""
import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config.json")

# Alle bekannten Konfig-Schlüssel (siehe config.example.json)
KNOWN_KEYS = [
    "TOKEN",
    "ALLGEMEIN_ID",
    "SPAM_CHANNEL_ID",
    "SPAM_KEYWORD",
    "GIF_ID",
    "LOG_CHANNEL_ID",
    "LEAVE_CHANNEL_ID",
    "MUSIC_CHANNEL_ID",
    "PICTURE_CHANNEL_ID",
    "TEMP_CHANNEL_ID",
    "TEMP_CATEGORY_ID",
    "BOT_CHANNEL_ID",
    "BLOCKED_CHANNEL_IDS",
    "ALLOWED_ROLE_IDS",
    "IGNORED_ROLE_ID",
    "GUILD_ID",
    "APPLICATION_ID",
    # Turnier-Schnittstelle (/verknüpfen) — Token gehört in die .env, nicht in config.json
    "TURNIER_API_URL",
    "TURNIER_SERVICE_TOKEN",
    # Interner Service-Endpoint (Guild-Rollen fürs Turnier-Backend, Phase 4)
    "SERVICE_API_PORT",
]


def load_file_config():
    """Liest die config.json. Fehlt sie, wird ein leeres Dict geliefert."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_file_config(data):
    """Schreibt die config.json (genutzt von /einstellungen)."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _coerce(value):
    """ENV-Strings nach Möglichkeit in int/list/bool umwandeln."""
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


def load_config():
    """Liefert die zusammengeführte Konfiguration (ENV überschreibt Datei)."""
    cfg = load_file_config()
    for key in set(KNOWN_KEYS) | set(cfg):
        env_value = os.environ.get(f"NICEBOT_{key}")
        if env_value is None:
            env_value = os.environ.get(key)
        if env_value is not None:
            cfg[key] = _coerce(env_value)
    return cfg
