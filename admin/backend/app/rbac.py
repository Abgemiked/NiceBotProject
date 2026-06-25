"""Rollenbasierte Zugriffssteuerung (RBAC) für nicebot-admin.

Reine Logik ohne FastAPI-Abhängigkeiten → vollständig unit-testbar.

Drei Stufen:
- FULL_ADMIN: alles, inkl. Secrets/Keys (.env-Werte).
- DC_MOD: Einstellungen sehen/ändern, KEINE Secrets.
- NONE: kein Zugriff (403).
"""
from enum import Enum


class Tier(str, Enum):
    FULL_ADMIN = "full_admin"
    DC_MOD = "dc_mod"
    NONE = "none"


# Config-/ENV-Schlüssel, die als Secret gelten und nur FULL_ADMIN sehen darf.
SECRET_KEYS = frozenset({
    "TOKEN",
    "TURNIER_SERVICE_TOKEN",
    "BOT_SERVICE_TOKEN",
    "DISCORD_CLIENT_SECRET",
    "SESSION_SECRET",
})

MASK = "••••••••"


def resolve_tier(user_role_ids, full_admin_ids, mod_ids):
    """Bestimmt die höchste Stufe anhand der Discord-Rollen des Users.

    FULL_ADMIN hat Vorrang vor DC_MOD. Akzeptiert beliebige iterierbare
    Rollen-ID-Sammlungen (werden zu int normalisiert).
    """
    user = {int(r) for r in user_role_ids if str(r).isdigit()}
    if user & {int(r) for r in full_admin_ids}:
        return Tier.FULL_ADMIN
    if user & {int(r) for r in mod_ids}:
        return Tier.DC_MOD
    return Tier.NONE


def can_view_secrets(tier):
    return tier == Tier.FULL_ADMIN


def can_edit_settings(tier):
    return tier in (Tier.FULL_ADMIN, Tier.DC_MOD)


def permissions_for(tier):
    """Maschinenlesbare Rechte-Map fürs Frontend."""
    return {
        "tier": tier.value,
        "view_secrets": can_view_secrets(tier),
        "edit_settings": can_edit_settings(tier),
        "edit_secrets": tier == Tier.FULL_ADMIN,
    }


def mask_secrets(data, tier):
    """Maskiert Secret-Felder, wenn die Stufe sie nicht sehen darf.

    Erwartet ein dict {key: value}; nicht-FULL_ADMIN bekommt SECRET_KEYS
    durch MASK ersetzt (sofern überhaupt ein Wert gesetzt ist).
    """
    if can_view_secrets(tier):
        return dict(data)
    out = {}
    for key, value in data.items():
        if key in SECRET_KEYS:
            out[key] = MASK if value not in (None, "") else value
        else:
            out[key] = value
    return out
