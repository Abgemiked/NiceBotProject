"""Schema, Validierung und Merge-Logik für die Bot-Konfiguration (M2).

Reine Logik ohne FastAPI/IO → vollständig unit-testbar. Definiert, welche
config.json-Keys über das Web editierbar sind (Whitelist), wie sie typisiert
und validiert werden, und wie Updates sicher in die bestehende Config gemischt
werden (Fremd-Keys bleiben erhalten).
"""
import re

from .rbac import SECRET_KEYS

# Plausibler Discord-Snowflake: 5–25 Ziffern.
_ID_RE = re.compile(r"^\d{5,25}$")
# Konservativer Hostname (Buchstaben/Ziffern/Punkt/Bindestrich, mind. ein Punkt).
_HOST_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9](-?[a-z0-9])*\.)+[a-z]{2,}$")


# Feld-Definitionen: key, group, type (Validierung), kind (UI-Rendering), label.
# type ∈ {id, idlist, string, hostlist}; kind ∈ {channel, voice, category, role,
# keyword, hostlist, idlist} steuert, ob das Frontend ein Auswahl-Dropdown
# (aus echten Guild-Daten) oder ein Textfeld zeigt.
FIELDS = [
    {"key": "ALLGEMEIN_ID", "group": "Channels", "type": "id", "kind": "channel", "label": "Allgemein-Channel"},
    {"key": "SPAM_CHANNEL_ID", "group": "Channels", "type": "id", "kind": "channel", "label": "Spam-Channel"},
    {"key": "GIF_ID", "group": "Channels", "type": "id", "kind": "channel", "label": "GIF-Channel"},
    {"key": "LOG_CHANNEL_ID", "group": "Channels", "type": "id", "kind": "channel", "label": "Log-Channel"},
    {"key": "LEAVE_CHANNEL_ID", "group": "Channels", "type": "id", "kind": "channel", "label": "Leave-Channel"},
    {"key": "MUSIC_CHANNEL_ID", "group": "Channels", "type": "id", "kind": "channel", "label": "Musik-Channel"},
    {"key": "PICTURE_CHANNEL_ID", "group": "Channels", "type": "id", "kind": "channel", "label": "Bilder-Channel"},
    {"key": "TEMP_CHANNEL_ID", "group": "Channels", "type": "id", "kind": "voice", "label": "Temp-Voice-Channel"},
    {"key": "TEMP_CATEGORY_ID", "group": "Channels", "type": "id", "kind": "category", "label": "Temp-Kategorie"},
    {"key": "BOT_CHANNEL_ID", "group": "Channels", "type": "id", "kind": "channel", "label": "Bot-Channel"},
    {"key": "SPAM_KEYWORD", "group": "Filter", "type": "string", "kind": "keyword", "label": "Spam-Keyword"},
    {"key": "GIF_ALLOWED_DOMAINS", "group": "Filter", "type": "hostlist", "kind": "hostlist", "label": "Erlaubte GIF-Domains"},
    {"key": "BLOCKED_CHANNEL_IDS", "group": "Filter", "type": "idlist", "kind": "idlist", "label": "Blockierte Channels"},
    {"key": "ALLOWED_ROLE_IDS", "group": "Rollen", "type": "idlist", "kind": "rolelist", "label": "Admin-Rollen"},
    {"key": "DC_MOD_ROLE_IDS", "group": "Rollen", "type": "idlist", "kind": "rolelist", "label": "DC-Mod-Rolle(n)"},
    {"key": "IGNORED_ROLE_ID", "group": "Rollen", "type": "id", "kind": "role", "label": "Ignorierte Rolle (Statistik)"},
]

# Schreib-Whitelist: nur diese Keys dürfen über das Web geändert werden.
EDITABLE_KEYS = frozenset(f["key"] for f in FIELDS)
_FIELD_BY_KEY = {f["key"]: f for f in FIELDS}

# In M2 nur lesbar (maskiert für nicht-FULL_ADMIN), nicht editierbar.
READONLY_SECRET_KEYS = frozenset({"TOKEN", "TURNIER_SERVICE_TOKEN"})


class ValidationError(ValueError):
    pass


def _validate_id(value):
    if isinstance(value, bool):
        raise ValidationError("muss eine Discord-ID sein")
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str) or not _ID_RE.match(value.strip()):
        raise ValidationError("muss eine numerische Discord-ID (5–25 Ziffern) sein")
    return int(value.strip())


def _validate_idlist(value):
    if not isinstance(value, list):
        raise ValidationError("muss eine Liste von IDs sein")
    return [_validate_id(v) for v in value]


def _validate_string(value):
    if not isinstance(value, str):
        raise ValidationError("muss Text sein")
    value = value.strip()
    if not value:
        raise ValidationError("darf nicht leer sein")
    if len(value) > 200:
        raise ValidationError("ist zu lang (max. 200 Zeichen)")
    return value


def _validate_hostlist(value):
    if not isinstance(value, list):
        raise ValidationError("muss eine Liste von Hostnamen sein")
    out = []
    for v in value:
        if not isinstance(v, str):
            raise ValidationError("Hostname muss Text sein")
        host = v.strip().lower()
        if not _HOST_RE.match(host):
            raise ValidationError(f"ungültiger Hostname: {v!r}")
        out.append(host)
    if not out:
        raise ValidationError("mindestens ein Hostname erforderlich")
    return out


_VALIDATORS = {
    "id": _validate_id,
    "idlist": _validate_idlist,
    "string": _validate_string,
    "hostlist": _validate_hostlist,
}


def validate_updates(updates, can_write):
    """Validiert ein {key: value}-Update gegen Whitelist + Typen.

    `can_write` ist True, wenn der (frisch geprüfte) Aufrufer schreiben darf.
    Liefert (clean: dict, errors: dict[key->msg]). Wirft PermissionError bei
    Versuch, Secret-Keys zu schreiben (in M2 generell verboten).
    """
    if not isinstance(updates, dict):
        raise ValidationError("Body muss ein Objekt sein")
    if not can_write:
        raise PermissionError("keine Schreibberechtigung")

    clean, errors = {}, {}
    for key, value in updates.items():
        if key in SECRET_KEYS or key in READONLY_SECRET_KEYS:
            # Secrets sind in M2 nicht über das Web änderbar.
            raise PermissionError(f"Secret-Key '{key}' ist nicht editierbar")
        if key not in EDITABLE_KEYS:
            errors[key] = "unbekannter oder nicht editierbarer Schlüssel"
            continue
        try:
            clean[key] = _VALIDATORS[_FIELD_BY_KEY[key]["type"]](value)
        except ValidationError as exc:
            errors[key] = str(exc)
    return clean, errors


def apply_updates(existing, clean):
    """Mischt validierte Updates in die bestehende Config.

    Erhält ALLE nicht betroffenen Keys unverändert (auch Fremd-/Secret-Keys).
    Gibt ein neues dict zurück (mutiert das Original nicht).
    """
    merged = dict(existing)
    merged.update(clean)
    return merged
