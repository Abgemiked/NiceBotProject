"""Bot-Konfiguration verwalten (M2).

GET /api/config  — Felder + aktuelle Werte (Secrets maskiert je nach Tier).
PUT /api/config  — validiertes, atomares Schreiben der Whitelist-Keys.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, status

from ..bot_client import BotApiError
from ..authz import current_tier_live
from ..bot_config import BotConfigError, read_config, write_config
from ..config_schema import (
    FIELDS,
    ValidationError,
    apply_updates,
    validate_updates,
)
from ..deps import require_access
from ..rbac import Tier, can_view_secrets, mask_secrets

router = APIRouter(prefix="/api", tags=["config"])


def _field_meta():
    """Statische Feld-Metadaten. Laufzeit-Secrets (Token etc.) werden NICHT hier,
    sondern im dedizierten Secrets-Tab (/api/secrets, .env-basiert) verwaltet."""
    return [dict(f, secret=False, editable=True) for f in FIELDS]


@router.get("/config")
def get_config(user=Depends(require_access)):
    tier = Tier(user.get("tier"))
    try:
        raw = read_config()
    except BotConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    fields = _field_meta()
    # Nur bekannte Felder zurückgeben; Werte für Secrets maskieren wenn nötig.
    values = {f["key"]: raw.get(f["key"]) for f in fields}
    values = mask_secrets(values, tier)
    # WICHTIG: Discord-Snowflake-IDs als STRINGS ausliefern. Als JSON-Zahl
    # verlieren IDs > 2^53 im Browser an Präzision und matchen dann die
    # (exakten String-)Dropdown-Optionen nicht mehr → Felder wirken "nicht gesetzt".
    for f in fields:
        v = values.get(f["key"])
        if f.get("type") == "id" and v is not None:
            values[f["key"]] = str(v)
        elif f.get("type") == "idlist" and isinstance(v, list):
            values[f["key"]] = [str(x) for x in v]
    return {
        "fields": fields,
        "values": values,
        "can_view_secrets": can_view_secrets(tier),
        "restart_required_keys": ["TOKEN"],  # nur bei Bot-Start geladen
    }


@router.put("/config")
async def put_config(payload: dict = Body(...), user=Depends(require_access)):
    # 1) Tier FRISCH gegen die Bot-API prüfen (nicht der Session vertrauen).
    try:
        live_tier = await current_tier_live(user.get("discord_id"))
    except BotApiError as exc:
        raise HTTPException(status_code=502, detail=f"Rollenprüfung fehlgeschlagen: {exc}")
    if live_tier == Tier.NONE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine berechtigte Rolle")

    updates = payload.get("updates", payload)
    # 2) Validieren (Whitelist + Typen; Secret-Write wird hart abgelehnt).
    try:
        clean, errors = validate_updates(updates, can_write=live_tier in (Tier.FULL_ADMIN, Tier.DC_MOD))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail={"validation_errors": errors})
    if not clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Keine Änderungen")

    # 3) Atomar mergen + schreiben (Fremd-/Secret-Keys bleiben erhalten).
    try:
        existing = read_config()
    except BotConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    write_config(apply_updates(existing, clean))
    return {"updated": sorted(clean.keys())}
