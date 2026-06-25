"""Tests für die sicherheitskritische RBAC-Logik (M1)."""
from app.rbac import (
    Tier,
    resolve_tier,
    can_view_secrets,
    can_edit_settings,
    permissions_for,
    mask_secrets,
    MASK,
)

FULL = {669879940296081420, 1130018862990098463}
MOD = {1078399961496039515}


def test_full_admin_match():
    assert resolve_tier([669879940296081420], FULL, MOD) == Tier.FULL_ADMIN
    assert resolve_tier([1130018862990098463], FULL, MOD) == Tier.FULL_ADMIN


def test_mod_match():
    assert resolve_tier([1078399961496039515], FULL, MOD) == Tier.DC_MOD


def test_full_admin_takes_precedence_over_mod():
    # User mit beiden Rollen → FULL_ADMIN gewinnt.
    assert resolve_tier(
        [1078399961496039515, 669879940296081420], FULL, MOD
    ) == Tier.FULL_ADMIN


def test_no_match_is_none():
    assert resolve_tier([111, 222], FULL, MOD) == Tier.NONE
    assert resolve_tier([], FULL, MOD) == Tier.NONE


def test_string_ids_are_normalized():
    assert resolve_tier(["669879940296081420"], FULL, MOD) == Tier.FULL_ADMIN
    assert resolve_tier(["nonsense", "1078399961496039515"], FULL, MOD) == Tier.DC_MOD


def test_permission_helpers():
    assert can_view_secrets(Tier.FULL_ADMIN) is True
    assert can_view_secrets(Tier.DC_MOD) is False
    assert can_view_secrets(Tier.NONE) is False
    assert can_edit_settings(Tier.DC_MOD) is True
    assert can_edit_settings(Tier.NONE) is False


def test_permissions_for_map():
    p = permissions_for(Tier.DC_MOD)
    assert p == {
        "tier": "dc_mod",
        "view_secrets": False,
        "edit_settings": True,
        "edit_secrets": False,
    }


def test_mask_secrets_hides_for_mod():
    data = {"TOKEN": "abc123", "GIF_ID": 42, "SPAM_KEYWORD": "oof"}
    masked = mask_secrets(data, Tier.DC_MOD)
    assert masked["TOKEN"] == MASK
    assert masked["GIF_ID"] == 42
    assert masked["SPAM_KEYWORD"] == "oof"


def test_mask_secrets_visible_for_full_admin():
    data = {"TOKEN": "abc123", "GIF_ID": 42}
    assert mask_secrets(data, Tier.FULL_ADMIN) == data


def test_mask_secrets_keeps_empty_unmasked():
    # Leeres Secret bleibt leer (kein irreführendes MASK-Symbol).
    data = {"TOKEN": "", "TURNIER_SERVICE_TOKEN": None}
    masked = mask_secrets(data, Tier.DC_MOD)
    assert masked["TOKEN"] == ""
    assert masked["TURNIER_SERVICE_TOKEN"] is None
