---
description: Search Opera Cloud guest profiles by name, email, phone, or loyalty ID, or fetch a single profile with preferences and stay history.
argument-hint: <name|email|phone|loyalty-id> [--hotel-id ID] [--limit N] [--with-history]
allowed-tools: mcp__opera-cloud__search_guests, mcp__opera-cloud__get_guest_profile, mcp__opera-cloud__get_guest_preferences, mcp__opera-cloud__get_guest_stay_history, mcp__opera-cloud__get_guest_loyalty_info
---

# /opera-cloud-guests

Look up Opera Cloud guest profiles via the opera-cloud MCP server. Wraps the read-only guest search path plus the high-frequency profile/preference/stay-history drill-downs front-desk agents reach for during check-in.

## Usage

`/opera-cloud-guests <name|email|phone|loyalty-id> [--hotel-id ID] [--limit N] [--with-history]`

Arguments:

- `<name|email|phone|loyalty-id>`: free-text guest lookup. Email-shaped inputs (`@`) and phone-shaped inputs (digits + `+`) are detected and dispatched as exact matches; otherwise the term is treated as a name substring.
- `--hotel-id ID`: optional OPERA property ID (multi-property deployments).
- `--limit N`: optional cap on result rows (default 25).
- `--with-history`: when present, after the lookup also fetch `mcp__opera-cloud__get_guest_stay_history` and `mcp__opera-cloud__get_guest_loyalty_info` so the front desk sees VIP context in one shot.

## Workflow

1. Classify the argument: email / phone / loyalty-ID vs. name. Loyalty IDs typically start with the chain prefix (e.g. `HG`, `MR`) followed by digits.
2. If a profile ID is found, call `mcp__opera-cloud__get_guest_profile` to pull the canonical record (name, address, contact, ID docs).
3. Always call `mcp__opera-cloud__get_guest_preferences` to surface room-type, smoking, dietary, and communication preferences — front-desk agents need these at check-in.
4. When `--with-history` is set, additionally call `mcp__opera-cloud__get_guest_stay_history` and `mcp__opera-cloud__get_guest_loyalty_info` and append them to the summary.
5. Summarize: full name, primary contact, VIP/loyalty tier, top 3 preferences, last 3 stays.

## Example

`/opera-cloud-guests jane.doe@example.com --with-history`
