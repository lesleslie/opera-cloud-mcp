"""opera-cloud-mcp tool profile registration.

3-tier profile system that controls which tool groups are registered at
startup, reducing context-token cost for daily-driver use cases.

Profiles:
    MINIMAL:  0 tools — server still up, ``discover_tools`` meta available.
    STANDARD: 2 tools — ``search_reservations`` + ``search_guests`` (read-only
              lookups; the daily-driver surface for front-desk agents).
    FULL:     All 53 tools (default — backward-compatible behavior).

Configured via ``OPERA_CLOUD_TOOL_PROFILE`` env var. See
``docs/architecture/tool-profile-rationale.md`` for bucket mapping and
the per-tier behavioral contract.

This module imports the canonical ``register_*_tools`` aggregators from
each domain tool module — no tool bodies are duplicated. The W0 helper
in ``mcp-common`` (0.18.0+) dispatches by looking up these group names
in ``REGISTRATION_MAP`` at server startup.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastmcp import FastMCP
from mcp_common.tools.dispatch import ALL_TOOLS
from mcp_common.tools.profiles import MANDATORY_GROUPS, MANDATORY_TOOLS, ToolProfile

# Public top-level domain aggregators (one per module) — used at FULL profile.
from opera_cloud_mcp.tools.financial_tools import register_financial_tools
from opera_cloud_mcp.tools.guest_tools import (
    _register_search_guests_tool,
    register_guest_tools,
)
from opera_cloud_mcp.tools.operation_tools import register_operation_tools
from opera_cloud_mcp.tools.reservation_tools import (
    _register_search_reservations_tool,
    register_reservation_tools,
)
from opera_cloud_mcp.tools.room_tools import register_room_tools

# ``RegisterFn`` = ``Callable[[FastMCP], Awaitable[None] | None]``.
# Sync register functions return ``None``; async register functions return
# a coroutine. The W0 helper awaits coroutines internally via
# ``_maybe_await``; we don't need to differentiate here.
RegisterFn = Callable[[FastMCP], Awaitable[None] | None]

# REGISTRATION_MAP: every register_* function keyed by group name.
# Used by ``apply_tool_profile()`` to look up groups named in
# ``PROFILE_REGISTRATIONS``. Keep this list aligned with the actual
# ``def register_*`` functions in ``opera_cloud_mcp/tools/*.py`` —
# the W0 helper raises ``ValueError`` if a group is named in
# ``PROFILE_REGISTRATIONS`` but missing from this map.
REGISTRATION_MAP: dict[str, RegisterFn] = {
    # Full-domain aggregators (FULL profile = "everything")
    "operation_tools": register_operation_tools,
    "room_tools": register_room_tools,
    "reservation_tools": register_reservation_tools,
    "guest_tools": register_guest_tools,
    "financial_tools": register_financial_tools,
    # Per-tool sub-registers (STANDARD profile = "read-only lookups").
    # These bypass the full domain aggregator so MINIMAL/STANDARD get
    # only the read-only search tools, not the write side.
    "search_reservations": _register_search_reservations_tool,
    "search_guests": _register_search_guests_tool,
}


# PROFILE_REGISTRATIONS: which groups each profile activates.
# Values: list of group names (resolved via REGISTRATION_MAP), or
# ``ALL_TOOLS`` sentinel for "register every group via
# ``register_all_tool_groups``".
PROFILE_REGISTRATIONS: dict[ToolProfile, list[str] | type[ALL_TOOLS]] = {
    ToolProfile.MINIMAL: list(MANDATORY_TOOLS),  # empty — no business tools
    ToolProfile.STANDARD: [
        # Daily-driver read-only lookups for front-desk / concierge agents.
        "search_reservations",
        "search_guests",
    ],
    ToolProfile.FULL: ALL_TOOLS,
}


def register_all_tool_groups(server: FastMCP) -> None:
    """Register all 53 opera-cloud-mcp tools (called at FULL profile).

    Invoked by the W0 helper when ``PROFILE_REGISTRATIONS[FULL]`` is
    ``ALL_TOOLS``. Each call delegates to the public top-level aggregator
    in the corresponding tool module — no tool body is reimplemented here.
    """
    register_operation_tools(server)
    register_room_tools(server)
    register_reservation_tools(server)
    register_guest_tools(server)
    register_financial_tools(server)


# Mandatory groups: registration_map keys that are always registered at every
# profile (in addition to the per-profile list). opera-cloud-mcp does not
# expose the canonical ``get_liveness`` / ``get_readiness`` / ``get_health``
# MCP tool names (it exposes ``/healthz`` as an HTTP route, not an MCP tool),
# so the subset check is opted out via the default empty
# ``MANDATORY_GROUPS`` / ``MANDATORY_TOOLS`` from ``mcp_common``.
async def apply_opera_cloud_tool_profile(server: FastMCP) -> None:
    """Apply the OPERA_CLOUD_TOOL_PROFILE dispatch to ``server`` at startup.

    Async wrapper around the W0 helper. Called from the server module
    (``opera_cloud_mcp.server``) at import time, and from the test suite
    for profile-specific behavior verification.

    Note: the sync ``apply_tool_profile()`` from mcp-common raises
    ``RuntimeError`` when called from within a running event loop. Use this
    async variant from async contexts (FastMCP startup hooks, async
    tests, lifespan handlers).
    """
    # Lazy import to avoid loading the mcp_common dispatcher at module
    # import time; keeps ``opera_cloud_mcp.tools.profiles`` importable
    # without triggering FastMCP server creation.
    from mcp_common.tools.dispatch import _apply_tool_profile

    await _apply_tool_profile(
        server,
        profile_env_var="OPERA_CLOUD_TOOL_PROFILE",
        registrations=PROFILE_REGISTRATIONS,
        registration_map=REGISTRATION_MAP,
        register_all_fn=register_all_tool_groups,
    )


__all__ = [
    "ALL_TOOLS",
    "MANDATORY_GROUPS",
    "MANDATORY_TOOLS",
    "PROFILE_REGISTRATIONS",
    "REGISTRATION_MAP",
    "RegisterFn",
    "ToolProfile",
    "apply_opera_cloud_tool_profile",
    "register_all_tool_groups",
]
