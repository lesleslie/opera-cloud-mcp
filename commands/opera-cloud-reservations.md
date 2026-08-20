---
description: Search Opera Cloud reservations by guest name, confirmation number, arrival date, or hotel ID, or fetch a single reservation by ID.
argument-hint: <guest-name-or-conf-number> [--hotel-id ID] [--limit N] [--from YYYY-MM-DD] [--to YYYY-MM-DD]
allowed-tools: mcp__opera-cloud__search_reservations, mcp__opera-cloud__get_reservation, mcp__opera-cloud__get_reservation_history
---

# /opera-cloud-reservations

Look up Opera Cloud reservations via the opera-cloud MCP server. Wraps the standard read-only reservation search path exposed by the `STANDARD` tool profile.

## Usage

`/opera-cloud-reservations <guest-name-or-conf-number> [--hotel-id ID] [--limit N] [--from YYYY-MM-DD] [--to YYYY-MM-DD]`

Arguments:

- `<guest-name-or-conf-number>`: a guest surname / given name, full name, or Opera confirmation / reservation ID. If the value matches `^[A-Z0-9]{6,}$` it is treated as a reservation ID and dispatched to `mcp__opera-cloud__get_reservation`; otherwise it is sent as a free-text search to `mcp__opera-cloud__search_reservations`.
- `--hotel-id ID`: optional OPERA hotel / property ID. Required when the deployment spans multiple hotels.
- `--limit N`: optional cap on search-result rows (default 25).
- `--from YYYY-MM-DD`: optional arrival-window lower bound.
- `--to YYYY-MM-DD`: optional arrival-window upper bound.

## Workflow

1. Detect whether the supplied argument is a reservation ID (uppercase alphanumeric, ≥6 chars). If yes, call `mcp__opera-cloud__get_reservation` with `(hotel_id, confirmation_id)` and surface the single record.
2. Otherwise call `mcp__opera-cloud__search_reservations` with the provided criteria and `--limit`.
3. If the caller asks for history (e.g. argument ends with `--history`), follow up with `mcp__opera-cloud__get_reservation_history`.
4. Summarize the matches: confirmation number, guest name, arrival/departure, room type, status.

## Example

`/opera-cloud-reservations "Lee" --hotel-id HILDX --limit 10`
