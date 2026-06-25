"""Streamer-Verwaltung (M6).

GET    /api/streamers — bestehende Streamer (DC-Mod + Voll-Admin)
POST   /api/streamers — Streamer anlegen (Kategorie+Channels+Rollen) — NUR Voll-Admin
DELETE /api/streamers — Streamer löschen — NUR Voll-Admin

Anlegen/Löschen sind destruktive Discord-Operationen → nur live-geprüftes
FULL_ADMIN, jede Aktion wird im Audit-Log protokolliert.
"""
from fastapi import APIRouter, Body, Depends, HTTPException

from ..audit_db import log_admin_override
from ..bot_client import BotApiError, create_streamer, delete_streamer, fetch_streamers
from ..deps import require_access, require_full_admin_live

router = APIRouter(prefix="/api/streamers", tags=["streamers"])


@router.get("")
async def get_streamers(user=Depends(require_access)):
    try:
        return {"streamers": await fetch_streamers()}
    except BotApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("")
async def post_streamer(payload: dict = Body(...), user=Depends(require_full_admin_live)):
    name = (payload or {}).get("name", "")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="Streamer-Name erforderlich")
    name = name.strip()
    status_code, data = await create_streamer(name)
    if status_code == 200:
        log_admin_override(
            actor_id=user.get("discord_id"), actor_name=user.get("username"),
            target_id=None, target_name=name,
            meta={"scope": "streamer", "action": "create"},
        )
        return {"ok": True, "name": data.get("name", name)}
    if status_code == 409:
        raise HTTPException(status_code=409, detail="Streamer existiert bereits")
    if status_code == 400:
        raise HTTPException(status_code=400, detail=data.get("error", "Ungültige Anfrage"))
    raise HTTPException(status_code=502, detail=data.get("error", "Anlegen fehlgeschlagen"))


@router.delete("")
async def del_streamer(payload: dict = Body(...), user=Depends(require_full_admin_live)):
    name = (payload or {}).get("name", "")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="Streamer-Name erforderlich")
    name = name.strip()
    status_code, data = await delete_streamer(name)
    if status_code == 200:
        log_admin_override(
            actor_id=user.get("discord_id"), actor_name=user.get("username"),
            target_id=None, target_name=name,
            meta={"scope": "streamer", "action": "delete"},
        )
        return {"ok": True}
    if status_code == 404:
        raise HTTPException(status_code=404, detail="Streamer nicht gefunden")
    raise HTTPException(status_code=502, detail=data.get("error", "Löschen fehlgeschlagen"))
