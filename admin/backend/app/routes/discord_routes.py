"""Discord-Guild-Stammdaten für Auswahl-Dropdowns im Web-Tool.

GET /api/discord/channels — Guild-Channels (id, name, type) für Channel-Auswahl
GET /api/discord/roles    — Guild-Rollen (id, name) für Rollen-Auswahl
"""
from fastapi import APIRouter, Depends, HTTPException

from ..bot_client import BotApiError, fetch_channels, fetch_roles
from ..deps import require_access

router = APIRouter(prefix="/api/discord", tags=["discord"])


@router.get("/channels")
async def get_channels(user=Depends(require_access)):
    try:
        return {"channels": await fetch_channels()}
    except BotApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/roles")
async def get_roles(user=Depends(require_access)):
    try:
        return {"roles": await fetch_roles()}
    except BotApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
