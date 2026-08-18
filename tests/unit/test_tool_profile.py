"""opera-cloud-mcp tool profile tests.

Wires up the W0 helper from mcp-common 0.18.0+ and verifies:

1. The PROFILE_REGISTRATIONS / REGISTRATION_MAP / register_all_tool_groups
   trio is well-formed (3-tier, AST-only checks).
2. The server module wires through ``OPERA_CLOUD_TOOL_PROFILE``.
3. MANDATORY_TOOLS is a subset of REGISTRATION_MAP.keys() at every profile
   (the W0 helper raises ``ValueError`` if not).
4. Behavioral parity: every tool registered by the legacy direct
   ``register_*_tools(app)`` path is also registered at FULL profile via
   the W0 path. The pre-refactor tool surface (52 tools; brief said 53
   but a duplicate name shadows one) is captured inline as
   ``EXPECTED_FULL_TOOL_NAMES`` — NOT from a golden fixture, which would
   be self-validating if captured POST-refactor.
5. STANDARD profile registers exactly the 2 read-only lookups
   (search_reservations, search_guests) plus the ``discover_tools`` meta.
6. MINIMAL profile registers only the ``discover_tools`` meta.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

from mcp_common.fastmcp import FastMCP
from mcp_common.tools.dispatch import ALL_TOOLS
from mcp_common.tools.profiles import MANDATORY_GROUPS, MANDATORY_TOOLS, ToolProfile

from opera_cloud_mcp.tools import profiles as profiles_mod
from opera_cloud_mcp.tools.profiles import (
    PROFILE_REGISTRATIONS,
    REGISTRATION_MAP,
    apply_opera_cloud_tool_profile,
)

if TYPE_CHECKING:
    import pytest

# All 52 opera-cloud-mcp tool names — the legacy direct register_*_tools()
# surface. Captured from the existing per-module test_expected_tools lists
# (test_operation_tools.py, test_room_tools.py, test_financial_tools.py,
# test_guest_tools.py, test_reservation_tools_simple.py) AND verified by
# direct introspection of FastMCP.list_tools() after the legacy
# register_*_tools(app) call sequence. Used by the behavioral parity
# test below.
#
# Note: the brief reported 53 tools, but the actual unique name count is
# 52 — ``check_room_availability`` is registered in BOTH
# room_tools.py and reservation_tools.py, and FastMCP emits
# "Component already exists" warnings and keeps the second registration
# (reservation_tools). Pre-refactor behavior had 1 shadow warning +
# 52 unique tool names; the W0 path produces the same 52 unique names
# with no shadow warning (it only calls each register function once).
EXPECTED_FULL_TOOL_NAMES: set[str] = {
    # operation_tools (12)
    "check_in_guest",
    "check_out_guest",
    "process_walk_in",
    "get_arrivals_report",
    "get_departures_report",
    "get_occupancy_report",
    "get_no_show_report",
    "assign_room",
    "get_in_house_guests",
    "get_front_desk_summary",
    "create_activity_booking",
    "create_dining_reservation",
    # room_tools (13)
    "get_room_status",
    "update_room_status",
    "check_room_availability",
    "get_housekeeping_tasks",
    "create_housekeeping_task",
    "complete_housekeeping_task",
    "get_inventory_levels",
    "update_inventory",
    "get_room_inspection",
    "create_maintenance_request",
    "get_inventory_status",
    "update_inventory_stock",
    "get_cleaning_schedule",
    # reservation_tools (10)
    "search_reservations",
    "get_reservation",
    "create_reservation",
    "modify_reservation",
    "cancel_reservation",
    "get_reservation_history",
    "bulk_create_reservations",
    "get_bulk_operation_status",
    "get_reservation_client_metrics",
    # guest_tools (9)
    "search_guests",
    "get_guest_profile",
    "create_guest_profile",
    "update_guest_profile",
    "get_guest_preferences",
    "update_guest_preferences",
    "get_guest_stay_history",
    "merge_guest_profiles",
    "get_guest_loyalty_info",
    # financial_tools (9)
    "get_guest_folio",
    "post_charge_to_room",
    "process_payment",
    "generate_folio_report",
    "transfer_charges",
    "void_transaction",
    "process_refund",
    "get_daily_revenue_report",
    "get_outstanding_balances",
}
assert len(EXPECTED_FULL_TOOL_NAMES) == 52, (
    f"Expected 52 unique tool names, got {len(EXPECTED_FULL_TOOL_NAMES)}. "
    "Update EXPECTED_FULL_TOOL_NAMES if the tool inventory changed. "
    "Note: the brief reported 53 — the actual count is 52 because "
    "check_room_availability is registered by two modules and the "
    "second registration shadows the first."
)


# --- AST-only / static checks (8 tests) ---------------------------------


def test_profiles_module_exists():
    assert Path("opera_cloud_mcp/tools/profiles.py").exists()


def test_server_module_uses_opera_cloud_tool_profile_env_var():
    """``opera_cloud_mcp/server.py`` must reference the canonical env var name."""
    server = Path("opera_cloud_mcp/server.py")
    tree = ast.parse(server.read_text())
    found = any(
        isinstance(node, ast.Constant) and node.value == "OPERA_CLOUD_TOOL_PROFILE"
        for node in ast.walk(tree)
    )
    assert found, (
        "OPERA_CLOUD_TOOL_PROFILE not referenced in server.py. "
        "Verify the env var name matches the convention."
    )


def test_profile_registrations_cover_all_three_tiers():
    """All 3 profile tiers must be present in PROFILE_REGISTRATIONS."""
    assert set(PROFILE_REGISTRATIONS.keys()) == {
        ToolProfile.MINIMAL,
        ToolProfile.STANDARD,
        ToolProfile.FULL,
    }


def test_full_profile_uses_all_tools_sentinel():
    """FULL profile must use the ALL_TOOLS sentinel (not a hardcoded list of all 52)."""
    assert PROFILE_REGISTRATIONS[ToolProfile.FULL] is ALL_TOOLS


def test_standard_profile_registers_only_lookups():
    """STANDARD must include search_reservations + search_guests only (read-only)."""
    std = PROFILE_REGISTRATIONS[ToolProfile.STANDARD]
    assert std == ["search_reservations", "search_guests"]


def test_minimal_profile_has_no_business_tools():
    """MINIMAL must be an empty list (or list(MANDATORY_TOOLS) which is empty)."""
    minimal = PROFILE_REGISTRATIONS[ToolProfile.MINIMAL]
    assert list(minimal) == []


def test_registration_map_has_required_keys():
    """REGISTRATION_MAP must contain at least the 5 public + 2 lookup groups."""
    required = {
        "operation_tools",
        "room_tools",
        "reservation_tools",
        "guest_tools",
        "financial_tools",
        "search_reservations",
        "search_guests",
    }
    assert required.issubset(REGISTRATION_MAP.keys()), (
        f"REGISTRATION_MAP missing: {required - set(REGISTRATION_MAP.keys())}"
    )


def test_mandatory_tools_subset_of_registration_map_at_every_profile():
    """MANDATORY_TOOLS ∩ profile-list ⊆ REGISTRATION_MAP.keys() at all 3 levels.

    The W0 helper's ``_apply_tool_profile_async`` raises ``ValueError`` if a
    group named in PROFILE_REGISTRATIONS is not in REGISTRATION_MAP. Mirror
    that check here so a misconfiguration fails fast at unit-test time, not
    at server startup.
    """
    for profile, groups in PROFILE_REGISTRATIONS.items():
        if groups is ALL_TOOLS:
            continue  # FULL delegates to register_all_tool_groups
        for name in groups:
            assert name in REGISTRATION_MAP, (
                f"Profile {profile!r} names {name!r} but REGISTRATION_MAP lacks it. "
                f"Add it or remove the reference."
            )
        # MANDATORY_GROUPS / MANDATORY_TOOLS subset check
        for mandatory_group in MANDATORY_GROUPS:
            assert mandatory_group in REGISTRATION_MAP, (
                f"MANDATORY_GROUPS contains {mandatory_group!r} not in REGISTRATION_MAP"
            )
        for mandatory_tool in MANDATORY_TOOLS:
            assert mandatory_tool in REGISTRATION_MAP, (
                f"MANDATORY_TOOLS contains {mandatory_tool!r} not in REGISTRATION_MAP"
            )


def test_w0_helper_exposes_both_sync_and_async_entrypoints():
    """The W0 helper in mcp-common 0.18.0+ exposes both ``apply_tool_profile``
    (sync) and ``_apply_tool_profile`` (async). opera-cloud-mcp uses the sync
    entrypoint in ``server.py`` (no running loop at module import) and the
    async wrapper (``apply_opera_cloud_tool_profile``) in test contexts and
    the profiles module. Both must be importable.
    """
    import mcp_common.tools.dispatch as dispatch

    assert hasattr(dispatch, "apply_tool_profile"), (
        "mcp_common.tools.dispatch.apply_tool_profile missing — sync entrypoint required by server.py"
    )
    assert hasattr(dispatch, "_apply_tool_profile"), (
        "mcp_common.tools.dispatch._apply_tool_profile missing — async entrypoint required by profiles.py"
    )
    assert callable(dispatch.apply_tool_profile)
    assert callable(dispatch._apply_tool_profile)


# --- Runtime profile tests (5 tests) ------------------------------------


async def test_full_profile_registers_all_52_tools(monkeypatch: pytest.MonkeyPatch):
    """FULL profile must register all 52 legacy tools + discover_tools.

    Behavioral parity check against the pre-refactor direct
    ``register_*_tools(app)`` path. This is the load-bearing test for
    "did the refactor drop any tools?".
    """
    monkeypatch.setenv("OPERA_CLOUD_TOOL_PROFILE", "full")
    app = FastMCP("test-opera-cloud-full")
    await apply_opera_cloud_tool_profile(app)

    tools = await app.list_tools()
    registered = {t.name for t in tools}
    # The W0 helper adds a `discover_tools` meta-tool on top of the 52.
    expected = EXPECTED_FULL_TOOL_NAMES | {"discover_tools"}
    missing = EXPECTED_FULL_TOOL_NAMES - registered
    assert not missing, f"FULL profile missing legacy tools: {sorted(missing)}"
    assert registered == expected, (
        f"FULL profile registered {len(registered)} tools; expected {len(expected)}.\n"
        f"  Extra: {sorted(registered - expected)}\n"
        f"  Missing: {sorted(expected - registered)}"
    )


async def test_full_profile_registered_tool_count_matches_inventory(
    monkeypatch: pytest.MonkeyPatch,
):
    """Sanity check: 52 + discover_tools = 53 tools at FULL profile."""
    monkeypatch.setenv("OPERA_CLOUD_TOOL_PROFILE", "full")
    app = FastMCP("test-opera-cloud-count")
    await apply_opera_cloud_tool_profile(app)

    tools = await app.list_tools()
    assert len(tools) == 53, (
        f"Expected 53 tools (52 + discover_tools), got {len(tools)}: "
        f"{sorted(t.name for t in tools)}"
    )


async def test_standard_profile_registers_two_lookups_plus_discover(
    monkeypatch: pytest.MonkeyPatch,
):
    """STANDARD profile registers search_reservations + search_guests."""
    monkeypatch.setenv("OPERA_CLOUD_TOOL_PROFILE", "standard")
    app = FastMCP("test-std")
    await apply_opera_cloud_tool_profile(app)

    tools = await app.list_tools()
    registered = {t.name for t in tools}
    # Discover_tools is added by the W0 helper at every profile.
    expected = {"search_reservations", "search_guests", "discover_tools"}
    assert registered == expected, (
        f"STANDARD registered {sorted(registered)}; expected {sorted(expected)}"
    )


async def test_minimal_profile_registers_only_discover_tools(
    monkeypatch: pytest.MonkeyPatch,
):
    """MINIMAL profile registers only the discover_tools meta — no business tools."""
    monkeypatch.setenv("OPERA_CLOUD_TOOL_PROFILE", "minimal")
    app = FastMCP("test-min")
    await apply_opera_cloud_tool_profile(app)

    tools = await app.list_tools()
    registered = {t.name for t in tools}
    assert registered == {"discover_tools"}, (
        f"MINIMAL registered {sorted(registered)}; expected only discover_tools"
    )


async def test_legacy_register_call_surface_matches_full_profile():
    """The pre-refactor direct register_*_tools() path must produce the same
    52 tool names as the FULL profile (minus the W0 helper's discover_tools
    meta). This is the load-bearing behavioral parity check.
    """
    # 1) Pre-refactor: call each public aggregator directly.
    legacy_app = FastMCP("legacy")
    from opera_cloud_mcp.tools.financial_tools import register_financial_tools
    from opera_cloud_mcp.tools.guest_tools import register_guest_tools
    from opera_cloud_mcp.tools.operation_tools import register_operation_tools
    from opera_cloud_mcp.tools.reservation_tools import register_reservation_tools
    from opera_cloud_mcp.tools.room_tools import register_room_tools

    register_operation_tools(legacy_app)
    register_room_tools(legacy_app)
    register_reservation_tools(legacy_app)
    register_guest_tools(legacy_app)
    register_financial_tools(legacy_app)
    legacy_names = {t.name for t in await legacy_app.list_tools()}

    # 2) W0 path: apply FULL profile via the helper.
    import os

    os.environ["OPERA_CLOUD_TOOL_PROFILE"] = "full"
    try:
        w0_app = FastMCP("w0")
        await apply_opera_cloud_tool_profile(w0_app)
        w0_names = {t.name for t in await w0_app.list_tools()}
    finally:
        os.environ.pop("OPERA_CLOUD_TOOL_PROFILE", None)
    w0_business = w0_names - {"discover_tools"}

    # 3) The 52 legacy tool names must equal the W0 path's business tool set.
    assert legacy_names == w0_business, (
        f"Behavioral parity broken.\n"
        f"  Only in legacy: {sorted(legacy_names - w0_business)}\n"
        f"  Only in W0:     {sorted(w0_business - legacy_names)}"
    )


# --- Misc sanity (2 tests) -----------------------------------------------


def test_no_legacy_direct_register_calls_remain_in_server():
    """The server must not contain stale direct calls to register_*_tools.

    This is the [docs-audit-removed-but-referenced] pattern: after
    refactoring server.py to use apply_opera_cloud_tool_profile, any
    leftover ``register_reservation_tools(app)`` style calls would
    double-register or shadow the W0 dispatch.
    """
    server = Path("opera_cloud_mcp/server.py")
    text = server.read_text()
    # The legacy pattern is: register_<domain>_tools(app) on a bare line.
    legacy_calls = [
        "register_reservation_tools(app)",
        "register_guest_tools(app)",
        "register_room_tools(app)",
        "register_operation_tools(app)",
        "register_financial_tools(app)",
    ]
    for legacy in legacy_calls:
        assert legacy not in text, (
            f"Legacy direct call {legacy!r} still in server.py. "
            "Remove it — apply_opera_cloud_tool_profile handles dispatch."
        )


def test_profiles_module_exposes_required_symbols():
    """The W0 helper imports these symbols by name from profiles.py."""
    for name in (
        "PROFILE_REGISTRATIONS",
        "REGISTRATION_MAP",
        "register_all_tool_groups",
        "apply_opera_cloud_tool_profile",
    ):
        assert hasattr(profiles_mod, name), (
            f"profiles.py missing required symbol: {name}"
        )
