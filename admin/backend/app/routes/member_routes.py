"""Member-Übersicht (M7) — paginierte Mitgliederliste via Bot-API (read-only)."""
from fastapi import APIRouter, Depends, HTTPException, Query

from ..bot_client import BotApiError, fetch_members
from ..deps import require_access

router = APIRouter(prefix="/api", tags=["members"])


@router.get("/members")
async def get_members(
    user=Depends(require_access),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    try:
        return await fetch_members(search=search, page=page, page_size=page_size)
    except BotApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
