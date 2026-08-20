---
description: Check Opera Cloud room status, housekeeping task state, and room availability for a property — the high-frequency floor ops surface.
argument-hint: "[--hotel-id ID] [--room-number ROOM] [--floor N] [--status STATE] [--available-from YYYY-MM-DD] [--available-to YYYY-MM-DD]"
allowed-tools: mcp__opera-cloud__get_room_status, mcp__opera-cloud__update_room_status, mcp__opera-cloud__get_housekeeping_tasks, mcp__opera-cloud__check_room_availability
---

# /opera-cloud-rooms

Inspect and update Opera Cloud room state via the opera-cloud MCP server. Wraps the room-status and housekeeping-task lookups used by housekeeping supervisors, front-desk agents, and night auditors.

## Usage

`/opera-cloud-rooms [--hotel-id ID] [--room-number ROOM] [--floor N] [--status STATE] [--available-from YYYY-MM-DD] [--available-to YYYY-MM-DD]`

Arguments:

- `--hotel-id ID`: OPERA property ID (required on multi-property deployments).
- `--room-number ROOM`: when set, the call drills down to a single room (`mcp__opera-cloud__get_room_status`); otherwise it returns the floor status rollup.
- `--floor N`: limit the rollup to one floor (e.g. `--floor 12`).
- `--status STATE`: optional filter (`VACANT`, `OCCUPIED`, `OUT_OF_ORDER`, `OUT_OF_SERVICE`, `CLEAN`, `DIRTY`, `INSPECTED`, `PICKUP`).
- `--available-from YYYY-MM-DD` / `--available-to YYYY-MM-DD`: when both are set, the call switches to `mcp__opera-cloud__check_room_availability` for the date window.
- To **update** a room (e.g. mark `DIRTY → CLEAN`), pass `--set-status CLEAN` and `--room-number`.

## Workflow

1. If `--available-from` and `--available-to` are both present, call `mcp__opera-cloud__check_room_availability` with the date window and a default 1-night stay; surface matching room types and rates.
2. Otherwise call `mcp__opera-cloud__get_room_status` (optionally with `--floor` / `--status` filters) to return the live room rollup.
3. If `--set-status` is provided, call `mcp__opera-cloud__update_room_status` for `--room-number`, then re-fetch the room to confirm the change.
4. When the caller asks for housekeeping tasks (e.g. argument contains `tasks` or `housekeeping`), add `mcp__opera-cloud__get_housekeeping_tasks` for the same `--hotel-id` and merge the result.
5. Summarize: counts per status, any `OUT_OF_ORDER` / `OUT_OF_SERVICE` rooms that need follow-up, and availability hits for the date window when relevant.

## Example

`/opera-cloud-rooms --hotel-id HILDX --floor 5 --status DIRTY`
