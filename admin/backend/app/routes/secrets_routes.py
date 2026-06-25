"""Laufzeit-Secrets der Bot-.env verwalten (nur Voll-Admin).

GET /api/secrets — Klartext-Werte der Whitelist-Secrets (Frontend verbirgt sie
                   per Augen-Toggle). Nur FULL_ADMIN (live geprüft).
PUT /api/secrets — Secrets in der .env setzen; Bot-Neustart danach nötig.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, status

from ..audit_db import log_admin_override
from ..authz import current_tier_live
from ..bot_client import BotApiError
from ..deps import require_access
from ..env_secrets import EnvError, read_secrets, write_secrets
from ..rbac import Tier

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


async def _require_full_admin_live(user):
    """Frische FULL_ADMIN-Prüfung gegen die Bot-API (Session nicht vertrauen)."""
    discord_id = user.get("discord_id")
    if not discord_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Identität")
    try:
        tier = await current_tier_live(discord_id)
    except BotApiError as exc:
        raise HTTPException(status_code=502, detail=f"Rollenprüfung fehlgeschlagen: {exc}")
    if tier != Tier.FULL_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nur Voll-Admin")


@router.get("")
async def get_secrets(user=Depends(require_access)):
    await _require_full_admin_live(user)
    try:
        return {"secrets": read_secrets()}
    except EnvError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.put("")
async def put_secrets(payload: dict = Body(...), user=Depends(require_access)):
    await _require_full_admin_live(user)
    updates = payload.get("updates", payload)
    try:
        changed = write_secrets(updates)
    except EnvError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    # Audit (best effort) — Werte NICHT mitloggen, nur welche Keys geändert wurden.
    log_admin_override(
        actor_id=user.get("discord_id"),
        actor_name=user.get("username"),
        target_id=None,
        target_name="bot .env",
        meta={"scope": "secrets", "changed_keys": changed},
    )
    return {"updated": changed, "restart_required": True}
