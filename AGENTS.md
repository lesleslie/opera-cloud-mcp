# AGENTS.md

This file describes the tools, resources, and capabilities provided by the **OPERA Cloud MCP Server** for use with AI agents through the Model Context Protocol (MCP).

## Overview

The OPERA Cloud MCP Server provides comprehensive access to Oracle OPERA Cloud hospitality management APIs, enabling AI agents to perform hotel operations, manage reservations, handle guest services, and access financial reporting.

**Server Name:** `opera-cloud-mcp`
**Version:** `0.1.0`
**Protocol:** FastMCP (Model Context Protocol)
**Domain:** Hospitality Management & Hotel Operations

## Authentication

This server requires OAuth2 authentication with Oracle OPERA Cloud. Configure the following environment variables:

- `OPERA_CLIENT_ID` - Your OPERA Cloud application client ID
- `OPERA_CLIENT_SECRET` - Your OPERA Cloud application client secret
- `OPERA_TOKEN_URL` - OAuth token endpoint URL
- `OPERA_BASE_URL` - OPERA Cloud API base URL
- `DEFAULT_HOTEL_ID` - Default hotel identifier for operations

## Tools

The server provides 45+ tools organized into five functional domains:

### 🏨 Reservation Management (9 tools)

Comprehensive booking and reservation operations.

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `search_reservations` | Search existing reservations with filters | `hotel_id`, `arrival_date`, `guest_name`, `confirmation_number` |
| `create_reservation` | Create new room reservation | `hotel_id`, `guest_data`, `arrival_date`, `departure_date`, `room_type` |
| `modify_reservation` | Update existing reservation details | `hotel_id`, `reservation_id`, `modification_data` |
| `cancel_reservation` | Cancel a reservation | `hotel_id`, `reservation_id`, `cancellation_reason` |
| `get_reservation_details` | Retrieve full reservation information | `hotel_id`, `reservation_id` |
| `add_reservation_note` | Add notes to reservation | `hotel_id`, `reservation_id`, `note_text` |
| `check_availability` | Check room availability for dates | `hotel_id`, `arrival_date`, `departure_date`, `room_type` |
| `create_group_reservation` | Create group/block booking | `hotel_id`, `group_data`, `room_requirements` |
| `split_reservation` | Split reservation into multiple bookings | `hotel_id`, `reservation_id`, `split_data` |

### 👤 Guest Services (8 tools)

Guest profile management and customer service operations.

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `search_guest_profiles` | Find guest profiles by criteria | `hotel_id`, `name`, `email`, `phone`, `membership_id` |
| `create_guest_profile` | Create new guest profile | `hotel_id`, `personal_info`, `contact_data`, `preferences` |
| `update_guest_profile` | Modify guest information | `hotel_id`, `profile_id`, `updated_data` |
| `get_guest_history` | Retrieve guest stay history | `hotel_id`, `profile_id`, `date_range` |
| `manage_guest_preferences` | Update guest preferences | `hotel_id`, `profile_id`, `preferences` |
| `handle_guest_complaint` | Record and track complaints | `hotel_id`, `profile_id`, `complaint_details` |
| `update_loyalty_status` | Manage loyalty program status | `hotel_id`, `profile_id`, `loyalty_data` |
| `merge_guest_profiles` | Combine duplicate guest profiles | `hotel_id`, `primary_id`, `duplicate_id` |

### 🏠 Room & Inventory Management (10 tools)

Room status, housekeeping, and inventory operations.

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_room_status` | Check current room status | `hotel_id`, `room_number`, `floor`, `room_type` |
| `update_room_status` | Change room status (clean/dirty/OOO) | `hotel_id`, `room_number`, `new_status`, `reason` |
| `get_housekeeping_tasks` | Retrieve cleaning assignments | `hotel_id`, `date`, `floor`, `housekeeper_id` |
| `assign_housekeeper` | Assign rooms to housekeeping staff | `hotel_id`, `room_list`, `housekeeper_id` |
| `create_maintenance_request` | Report room maintenance needs | `hotel_id`, `room_number`, `issue_description`, `priority` |
| `get_room_inventory` | Check room amenities and supplies | `hotel_id`, `room_number` |
| `manage_room_blocks` | Handle room blocking/unblocking | `hotel_id`, `room_numbers`, `block_reason` |
| `get_floor_summary` | Get status summary by floor | `hotel_id`, `floor_number` |
| `schedule_deep_cleaning` | Schedule special cleaning | `hotel_id`, `room_number`, `cleaning_type`, `date` |
| `track_amenity_usage` | Monitor amenity consumption | `hotel_id`, `amenity_type`, `date_range` |

### 🏢 Operations & Front Desk (12 tools)

Daily operations, check-in/out, and front desk functions.

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `check_in_guest` | Process guest check-in | `hotel_id`, `reservation_id`, `room_assignment`, `special_requests` |
| `check_out_guest` | Process guest check-out | `hotel_id`, `reservation_id`, `final_charges`, `checkout_time` |
| `process_walk_in` | Handle walk-in guests | `hotel_id`, `guest_data`, `room_preferences` |
| `get_arrivals_report` | Daily arrivals report | `hotel_id`, `date`, `status_filter` |
| `get_departures_report` | Daily departures report | `hotel_id`, `date`, `checkout_status` |
| `get_occupancy_report` | Current occupancy statistics | `hotel_id`, `date`, `room_type` |
| `get_no_show_report` | No-show reservations report | `hotel_id`, `date` |
| `assign_room` | Assign specific room to reservation | `hotel_id`, `reservation_id`, `room_number` |
| `get_in_house_guests` | List current in-house guests | `hotel_id`, `floor`, `vip_status` |
| `get_front_desk_summary` | Front desk dashboard data | `hotel_id`, `shift_date` |
| `create_activity_booking` | Book guest activities/tours | `hotel_id`, `guest_id`, `activity_details` |
| `create_dining_reservation` | Restaurant reservation booking | `hotel_id`, `guest_id`, `restaurant_details` |

### 💰 Financial & Cashiering (9 tools)

Payment processing, billing, and financial reporting.

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_guest_folio` | Retrieve guest bill/folio | `hotel_id`, `reservation_id`, `folio_type` |
| `post_charge_to_room` | Add charges to guest folio | `hotel_id`, `reservation_id`, `charge_details` |
| `process_payment` | Process payment transaction | `hotel_id`, `reservation_id`, `payment_data` |
| `generate_folio_report` | Create detailed billing report | `hotel_id`, `date_range`, `report_type` |
| `transfer_charges` | Move charges between folios | `hotel_id`, `from_folio`, `to_folio`, `charges` |
| `void_transaction` | Cancel/void a transaction | `hotel_id`, `transaction_id`, `void_reason` |
| `process_refund` | Issue refund to guest | `hotel_id`, `transaction_id`, `refund_amount` |
| `get_daily_revenue_report` | Daily financial summary | `hotel_id`, `date`, `department` |
| `get_outstanding_balances` | Unpaid balances report | `hotel_id`, `aging_days` |

## Resources

The server exposes two informational resources:

### `opera://api/docs`

**OPERA Cloud API Documentation**
Comprehensive documentation covering all OPERA Cloud REST API domains including authentication, reservations, front office, CRM, inventory, housekeeping, and more.

### `opera://config/hotel`

**Hotel Configuration**
Current hotel configuration settings including default hotel ID, API environment, version, and cache settings.

## Error Handling

All tools implement comprehensive error handling with:

- **Authentication Errors**: Automatic token refresh and retry
- **Rate Limiting**: Built-in backoff and retry logic
- **Validation Errors**: Input parameter validation with descriptive messages
- **API Errors**: Standardized error responses with OPERA Cloud error codes
- **Circuit Breaker**: Automatic failover for degraded API performance

## Observability

The server includes comprehensive monitoring:

- **Structured Logging**: JSON logs with PII masking
- **Metrics Collection**: Performance counters, timers, and gauges
- **Distributed Tracing**: Request correlation across operations
- **Health Endpoints**: `/health`, `/metrics`, `/status` for monitoring

## Usage Examples

### Search and Book Reservation

```python
# Search for availability
availability = await search_tool(
    "check_availability",
    {
        "hotel_id": "HOTEL001",
        "arrival_date": "2024-03-15",
        "departure_date": "2024-03-18",
        "room_type": "DELUXE",
    },
)

# Create reservation if available
if availability["available"]:
    reservation = await search_tool(
        "create_reservation",
        {
            "hotel_id": "HOTEL001",
            "guest_data": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@email.com",
            },
            "arrival_date": "2024-03-15",
            "departure_date": "2024-03-18",
            "room_type": "DELUXE",
        },
    )
```

### Guest Check-in Process

```python
# Check in guest
checkin_result = await search_tool(
    "check_in_guest",
    {
        "hotel_id": "HOTEL001",
        "reservation_id": "RES123456",
        "room_assignment": "101",
        "special_requests": ["Late checkout", "Extra towels"],
    },
)

# Update room status
await search_tool(
    "update_room_status",
    {
        "hotel_id": "HOTEL001",
        "room_number": "101",
        "new_status": "OCCUPIED",
        "reason": "Guest checked in",
    },
)
```

## Configuration

### Environment Variables

- `OPERA_CLIENT_ID` - Required OAuth client ID
- `OPERA_CLIENT_SECRET` - Required OAuth client secret
- `OPERA_TOKEN_URL` - OAuth token endpoint
- `OPERA_BASE_URL` - OPERA Cloud API base URL
- `DEFAULT_HOTEL_ID` - Default hotel for operations
- `ENABLE_CACHE` - Enable response caching (default: true)
- `CACHE_TTL` - Cache time-to-live in seconds (default: 300)
- `LOG_LEVEL` - Logging level (default: INFO)

### Rate Limits

- **Default**: 10 requests/second with 20 request burst capacity
- **Circuit Breaker**: Activates after 5 consecutive failures
- **Retry Logic**: Exponential backoff with maximum 3 retries

## Production Deployment

The server is production-ready with:

- **Docker Support**: Multi-stage Dockerfile with security hardening
- **Health Checks**: Comprehensive health monitoring endpoints
- **Monitoring Stack**: Prometheus metrics and Grafana dashboards
- **Logging**: Structured JSON logs with PII protection
- **Security**: OAuth2 authentication with token management

## Support

For issues or questions:

- Review the logs at `/status` endpoint for diagnostic information
- Check authentication status via `/health` endpoint
- Monitor performance metrics via `/metrics` endpoint
- Verify configuration via the `opera://config/hotel` resource

______________________________________________________________________

*This MCP server enables AI agents to provide comprehensive hospitality management capabilities through Oracle OPERA Cloud APIs, supporting everything from reservation management to financial operations.*
