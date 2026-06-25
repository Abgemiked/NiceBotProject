"""Audit-Log & Statistiken (M5 + M4).

GET /api/audit   — paginiertes, filterbares Audit-Log (DC-Mod + Voll-Admin)
GET /api/stats   — Mitglieder-Statistik (Membercount) live via Bot-API
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from ..audit_db import EVENT_TYPES, list_events
from ..bot_client import BotApiError, fetch_stats
from ..deps import require_access

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
def get_audit(
    user=Depends(require_access),
    event_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    return {
        "event_types": list(EVENT_TYPES),
        **list_events(event_type=event_type, page=page, page_size=page_size),
    }


@router.get("/stats")
async def get_stats(user=Depends(require_access)):
    try:
        return await fetch_stats()
    except BotApiError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
