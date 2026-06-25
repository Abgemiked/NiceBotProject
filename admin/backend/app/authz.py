"""Frische (live) Rollen-/Tier-Auflösung gegen die Bot-API.

Für sensible Operationen (Schreiben/Secrets) wird das Tier NICHT aus der
Session geglaubt, sondern direkt gegen die Bot-API re-validiert — so wirkt ein
Rollenentzug sofort, nicht erst nach Cookie-Ablauf (M1-Audit-Empfehlung).
"""
from .bot_client import fetch_member_roles
from .config import settings
from .rbac import Tier, resolve_tier


async def current_tier_live(discord_id):
    """Liefert das aktuelle Tier laut Bot-API. BotApiError wird durchgereicht."""
    is_member, role_ids, _ = await fetch_member_roles(discord_id)
    if not is_member:
        return Tier.NONE
    return resolve_tier(role_ids, settings.FULL_ADMIN_ROLE_IDS, settings.MOD_ROLE_IDS)
