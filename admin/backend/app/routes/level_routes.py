"""Level-System & Ranglisten (M3).

GET  /api/levels            — paginierte Rangliste (DC-Mod + Voll-Admin)
GET  /api/levels/{user_id}  — Einzeluser
PUT  /api/levels/{user_id}  — exp/level setzen (NUR Voll-Admin, live geprüft)
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from ..authz import current_tier_live
from ..bot_client import BotApiError
from ..deps import require_access
from ..level_db import (
    LevelValidationError,
    get_user,
    list_users,
    update_user,
    validate_update,
)
from ..rbac import Tier

router = APIRouter(prefix="/api/levels", tags=["levels"])


@router.get("")
def get_levels(
    user=Depends(require_access),
    search: str | None = Query(default=None, max_length=100),
    sort: str = Query(default="level"),
    direction: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    return list_users(search=search, sort=sort, direction=direction,
                      page=page, page_size=page_size)


@router.get("/{user_id}")
def get_level(user_id: str, user=Depends(require_access)):
    if not user_id.isdigit():
        raise HTTPException(status_code=400, detail="Ungültige user_id")
    found = get_user(user_id)
    if not found:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    return found


@router.put("/{user_id}")
async def put_level(user_id: str, payload: dict = Body(...), user=Depends(require_access)):
    if not user_id.isdigit():
        raise HTTPException(status_code=400, detail="Ungültige user_id")

    # Schreiben nur für FULL_ADMIN — Tier FRISCH gegen die Bot-API prüfen.
    discord_id = user.get("discord_id")
    if not discord_id:  # defensiv: ohne Identität kein Schreibrecht (fail-closed)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Identität in der Session")
    try:
        live_tier = await current_tier_live(discord_id)
    except BotApiError as exc:
        raise HTTPException(status_code=502, detail=f"Rollenprüfung fehlgeschlagen: {exc}")
    if live_tier != Tier.FULL_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Nur Voll-Admin darf Level bearbeiten")

    try:
        level, exp = validate_update(payload.get("level"), payload.get("exp"))
    except LevelValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if update_user(user_id, level, exp) == 0:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    return {"user_id": user_id, "level": level, "exp": exp}
