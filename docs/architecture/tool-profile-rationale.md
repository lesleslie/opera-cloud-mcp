# Tool Profile Rationale — opera-cloud-mcp

## Context

opera-cloud-mcp exposes 53 FastMCP tool decorators (across 5 domain
modules) but ships all of them at every startup. Daily-driver agents
(front-desk lookup, concierge) only need a small read-only subset;
shipping the full surface costs context tokens and increases the
blast radius of any single tool's runtime error.

The 2026-08-18 MCP tool-profile adoption spec (W2b.2) introduces a
3-tier profile system via `mcp-common` 0.18.0+. This document records
the bucket mapping for opera-cloud-mcp and the per-tier behavioral
contract.

## Profile mapping

| Profile | Tools | Use case |
|---|---|---|
| `MINIMAL` | 0 + `discover_tools` | Health probes; CLI introspection; minimal-footprint container |
| `STANDARD` | `search_reservations`, `search_guests` + `discover_tools` | Front-desk / concierge read-only lookups |
| `FULL` (default) | All 52 unique tools + `discover_tools` | Full property-management workflows; back-office agents |

### Why STANDARD is the 2-tool read-only subset

- `search_reservations` covers "find an existing booking" — the
  front-desk agent's #1 task. 90% of "is this guest arriving
  tonight?" / "which room is John Smith in?" requests resolve here.
- `search_guests` covers "find a guest profile" — the concierge's
  #1 task. Loyalty lookup, contact info, stay history.

Both are *read-only* — no write-side side effects. Neither triggers an
OPERA Cloud API mutation, neither requires the agent to be on a
specific hotel. They're the two tools a stateless agent can safely
call in a loop without a human-in-the-loop.

Write-side tools (`create_reservation`, `post_charge_to_room`,
`check_in_guest`, etc.) live in FULL only. Putting them in STANDARD
would let a daily-driver agent accidentally double-charge a guest or
check someone in to the wrong room.

### Why MINIMAL is empty

opera-cloud-mcp does not expose the canonical
`get_liveness` / `get_readiness` / `get_health` MCP tool names — it
exposes `/healthz` as an HTTP route (not an MCP tool). The MANDATORY
groups subset check is therefore opted out via the default empty
`MANDATORY_GROUPS` / `MANDATORY_TOOLS` from `mcp_common`.

The W0 helper still registers the `discover_tools` meta-tool at
MINIMAL, so a minimal container can still introspect its own surface.

## Behavioral contract

### Per-tier tool count

| Profile | Opera tools | `discover_tools` | Total |
|---|---|---|---|
| `MINIMAL` | 0 | 1 | 1 |
| `STANDARD` | 2 | 1 | 3 |
| `FULL` | 52 | 1 | 53 |

### Note on the "53 → 52" tool count

The brief reported 53 tools, but the actual unique-name count is 52.
`check_room_availability` is registered by BOTH
`opera_cloud_mcp/tools/room_tools.py` (via
`register_check_room_availability_tool`) and
`opera_cloud_mcp/tools/reservation_tools.py` (via
`_register_check_room_availability_tool`). FastMCP emits
`"Component already exists"` warnings and keeps the second
registration (reservation_tools).

This is a pre-existing design quirk, not introduced by the W0
adoption. The W0 path produces the same 52 unique names as the
pre-refactor direct `register_*_tools(app)` path; both have
one duplicate name, both end up with the same 52-name surface.
`test_legacy_register_call_surface_matches_full_profile` enforces
this parity.

### FULL is the default

No env var → `ToolProfile.FULL` → all 52 tools registered. Backward
compatible with the pre-W0 behavior. The pre-refactor
`register_*_tools(app)` sequence also produced 52 unique tools (with
the same shadow warning), so no agent is surprised by the change.

## Implementation

- `opera_cloud_mcp/tools/profiles.py` — `PROFILE_REGISTRATIONS`,
  `REGISTRATION_MAP`, `register_all_tool_groups`,
  `apply_opera_cloud_tool_profile` (async wrapper).
- `opera_cloud_mcp/server.py` — replaces the 5 direct
  `register_*_tools(app)` calls with a single
  `apply_tool_profile(app, profile_env_var="OPERA_CLOUD_TOOL_PROFILE", ...)`.
- `pyproject.toml` — `mcp-common>=0.18.0` (was `>=0.17.0`).
- `tests/unit/test_tool_profile.py` — 15 wiring + behavioral parity
  tests.
- `docs/architecture/tool-profile-rationale.md` — this file.

## Configuration

```bash
# Default — all 52 tools
OPERA_CLOUD_TOOL_PROFILE=full python -m opera_cloud_mcp

# Daily-driver front-desk (read-only lookups)
OPERA_CLOUD_TOOL_PROFILE=standard python -m opera_cloud_mcp

# Minimal / health-only
OPERA_CLOUD_TOOL_PROFILE=minimal python -m opera_cloud_mcp
```

The W0 helper's `_resolve_profile` raises `InvalidProfileError` if
the env var is SET-BUT-INVALID (e.g. `OPERA_CLOUD_TOOL_PROFILE=` empty
or `OPERA_CLOUD_TOOL_PROFILE=foo`). UNSET falls through to FULL per
spec.

## Cross-reference

- `mcp_common.tools.profiles` — `ToolProfile`, `MANDATORY_GROUPS`,
  `MANDATORY_TOOLS`.
- `mcp_common.tools.dispatch` — `apply_tool_profile` (sync),
  `_apply_tool_profile` (async), `_apply_tool_profile_async`
  (internal), `ALL_TOOLS` sentinel, `InvalidProfileError`.
- W2b.1 mailgun-mcp precedent: `docs/architecture/tool-profile-rationale.md`
  in `mailgun-mcp` (same shape; mailgun used MAILGUN_TOOL_PROFILE).
- W2a Crackerjack retrofit: same dispatch surface, different env var
  (`CRACKERJACK_TOOL_PROFILE`).
