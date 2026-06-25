"""Signierte, ablaufende Session- und OAuth-State-Cookies.

Nutzt itsdangerous (HMAC-Signatur). Der Session-Inhalt ist NICHT verschlüsselt,
nur signiert — es werden daher bewusst keine Secrets in die Session geschrieben,
nur discord_id, username und die aufgelöste Rollen-Stufe.
"""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .config import settings

_SESSION_SALT = "nicebot-admin-session"
_STATE_SALT = "nicebot-admin-oauth-state"


def _serializer(salt):
    # Fail-closed: ohne gesetztes SESSION_SECRET wäre die Signatur trivial
    # fälschbar (Session-Forgery). Lieber harter Fehler als unsichere Signatur.
    if not settings.SESSION_SECRET:
        raise RuntimeError("SESSION_SECRET ist nicht gesetzt — Sessions deaktiviert")
    return URLSafeTimedSerializer(settings.SESSION_SECRET, salt=salt)


# --- Session ---

def issue_session(discord_id, username, tier_value):
    return _serializer(_SESSION_SALT).dumps({
        "discord_id": str(discord_id),
        "username": username,
        "tier": tier_value,
    })


def read_session(token, max_age=None):
    """Gibt das Session-Dict zurück oder None bei ungültig/abgelaufen."""
    if not token:
        return None
    try:
        return _serializer(_SESSION_SALT).loads(
            token, max_age=max_age or settings.SESSION_MAX_AGE
        )
    except (BadSignature, SignatureExpired):
        return None


# --- OAuth-State (CSRF-Schutz) ---

def issue_state(value):
    return _serializer(_STATE_SALT).dumps({"s": value})


def read_state(token, max_age=600):
    if not token:
        return None
    try:
        return _serializer(_STATE_SALT).loads(token, max_age=max_age).get("s")
    except (BadSignature, SignatureExpired):
        return None
