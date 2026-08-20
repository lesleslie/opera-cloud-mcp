# OPERA Cloud MCP Server

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)
[![Runtime: oneiric](https://img.shields.io/badge/runtime-oneiric-6e5494)](https://github.com/lesleslie/oneiric)
[![Framework: FastMCP](https://img.shields.io/badge/framework-FastMCP-0ea5e9)](https://github.com/jlowin/fastmcp)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13%2B-green)](https://www.python.org/downloads/)

Unofficial Model Context Protocol (MCP) server for Oracle OPERA Cloud API integration, enabling AI agents to interact with hospitality management systems.

## Features

- **Complete OPERA Cloud Integration**: Access to reservations, guests, rooms, operations, and financial data
- **FastMCP Framework**: Built on FastMCP for high-performance MCP protocol support
- **Production Ready**: Security, monitoring, rate limiting, and Docker deployment
- **56 Tools**: Comprehensive API coverage across 5 core domains (plus 3 server/auth tools)
- **Enterprise Security**: OAuth2 authentication, token refresh, and audit logging

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/lesleslie/opera-cloud-mcp.git
cd opera-cloud-mcp

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
```

### Configuration

Edit `.env` with your OPERA Cloud credentials:

```env
OPERA_BASE_URL=https://api.oracle-hospitality.com
OPERA_TOKEN_URL=https://api.oracle-hospitality.com/oauth/v1/tokens
OPERA_API_VERSION=v1
OPERA_CLIENT_ID=your_client_id
OPERA_CLIENT_SECRET=your_client_secret
OPERA_ENVIRONMENT=production
```

Authentication uses OAuth2 client credentials only — there are no `OPERA_CLOUD_USERNAME` / `OPERA_CLOUD_PASSWORD` variables. See `.env.example` for the full list including optional `OPERA_SECURITY_*` knobs.

### Running the Server

```bash
# Development
python -m opera_cloud_mcp

# Or with uv
uv run python -m opera_cloud_mcp
```

## MCP Integration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "opera-cloud-mcp": {
      "command": "python",
      "args": ["-m", "opera_cloud_mcp"],
      "cwd": "/path/to/opera-cloud-mcp",
      "env": {
        "OPERA_BASE_URL": "https://api.oracle-hospitality.com",
        "OPERA_TOKEN_URL": "https://api.oracle-hospitality.com/oauth/v1/tokens",
        "OPERA_API_VERSION": "v1",
        "OPERA_CLIENT_ID": "your_client_id",
        "OPERA_CLIENT_SECRET": "your_client_secret",
        "OPERA_ENVIRONMENT": "production"
      }
    }
  }
}
```

### Other MCP Clients

See `example.mcp.json` and `example.mcp.dev.json` for configuration templates.

## Available Tools

The server provides 56 tools across 5 domains (plus 3 server/auth tools in `main.py`):

### Reservation Management (10 tools)

- `search_reservations`, `get_reservation`, `create_reservation`, `modify_reservation`, `cancel_reservation`
- `check_room_availability`, `get_reservation_history`
- `bulk_create_reservations`, `get_bulk_operation_status`
- `get_reservation_client_metrics`

### Guest Management (9 tools)

- `search_guests`, `get_guest_profile`, `create_guest_profile`, `update_guest_profile`
- `get_guest_preferences`, `update_guest_preferences`
- `get_guest_stay_history`
- `merge_guest_profiles`
- `get_guest_loyalty_info`

### Room Management (13 tools)

- `get_room_status`, `update_room_status`, `check_room_availability`
- `get_housekeeping_tasks`, `create_housekeeping_task`, `complete_housekeeping_task`
- `get_inventory_levels`, `update_inventory`, `get_inventory_status`, `update_inventory_stock`
- `get_room_inspection`, `create_maintenance_request`
- `get_cleaning_schedule`

### Operations Management (12 tools)

- `check_in_guest`, `check_out_guest`, `process_walk_in`
- `get_arrivals_report`, `get_departures_report`, `get_occupancy_report`, `get_no_show_report`, `get_front_desk_summary`
- `assign_room`, `get_in_house_guests`
- `create_activity_booking`, `create_dining_reservation`

### Financial Management (9 tools)

- `get_guest_folio`, `post_charge_to_room`
- `process_payment`, `process_refund`
- `generate_folio_report`, `get_daily_revenue_report`, `get_outstanding_balances`
- `transfer_charges`, `void_transaction`

### Server / Auth (3 tools, in `main.py`)

- `get_auth_status`, `validate_auth_credentials`
- `get_server_info`

For full input/output schemas see [`AGENTS.md`](AGENTS.md) or query the live server with `opera-cloud-mcp mcp list-tools`.

## Development

### Code Quality

```bash
# Run all quality checks
uv run crackerjack

# Individual tools
uv run ruff check --fix
uv run mypy .
uv run pytest --cov=opera_cloud_mcp
```

### Testing

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=opera_cloud_mcp --cov-report=html

# The `--cov-fail-under` threshold (currently 39%) is set in `pyproject.toml` under
# `[tool.pytest.ini_options].addopts`. Raise it as you add tests.
```

## Production Deployment

### Docker

```bash
# Build image
docker build -t opera-cloud-mcp .

# Run container
docker run -d \
  --name opera-cloud-mcp \
  -p 3037:3037 \
  --env-file .env \
  opera-cloud-mcp
```

### Docker Compose

For full stack with monitoring:

```bash
docker-compose up -d
```

Includes:

- OPERA Cloud MCP Server
- Redis (optional caching)
- Prometheus (metrics)
- Grafana (monitoring dashboards)

### Environment Variables

All variables use the `OPERA_` env_prefix defined in `opera_cloud_mcp/config/settings.py`.
See `.env.example` for the authoritative list. The most-used ones:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPERA_BASE_URL` | OPERA Cloud API base URL | Yes |
| `OPERA_TOKEN_URL` | OAuth2 token endpoint URL | Yes |
| `OPERA_API_VERSION` | OPERA Cloud API version (e.g. `v1`) | Yes |
| `OPERA_CLIENT_ID` | OAuth2 client ID | Yes |
| `OPERA_CLIENT_SECRET` | OAuth2 client secret | Yes |
| `OPERA_ENVIRONMENT` | `production`, `staging`, or `development` | Yes |
| `OPERA_DEFAULT_HOTEL_ID` | Default hotel identifier when none is supplied | No |
| `OPERA_REQUEST_TIMEOUT` | HTTP request timeout (seconds) | No (default: 30) |
| `OPERA_MAX_RETRIES` | Retry attempts for transient HTTP errors | No (default: 3) |
| `OPERA_OAUTH_MAX_RETRIES` | Retry attempts for OAuth token fetches | No (default: 3) |
| `OPERA_OAUTH_RETRY_BACKOFF` | OAuth retry backoff (seconds) | No (default: 1.0) |
| `OPERA_ENABLE_CACHE` | Enable in-memory response caching | No (default: true) |
| `OPERA_CACHE_TTL` | Cache TTL (seconds) | No (default: 300) |
| `OPERA_ENABLE_PERSISTENT_TOKEN_CACHE` | Persist OAuth tokens across restarts | No (default: true) |
| `OPERA_LOG_LEVEL` | Log level (`DEBUG`/`INFO`/`WARNING`/`ERROR`) | No (default: `INFO`) |
| `OPERA_LOG_FORMAT` | Log record format string | No |
| `OPERA_ENABLE_STRUCTURED_LOGGING` | Emit JSON logs | No (default: true) |
| `OPERA_SECURITY_*` | Production security knobs (rate limiting, audit, anomaly detection, etc.) — see `.env.example` | No |

Authentication is OAuth2 client-credentials only. There is no `OPERA_USERNAME` / `OPERA_PASSWORD` pair.

## Monitoring

### Health Checks

- **Health**: `GET /health` - Basic health status
- **Ready**: `GET /ready` - Readiness probe for K8s
- **Metrics**: `GET /metrics` - Prometheus metrics

### Observability

- **Structured Logging**: JSON logs with correlation IDs
- **Metrics**: Request rates, latencies, error rates
- **Tracing**: Distributed tracing support
- **Alerting**: Prometheus alerting rules

## Security

### Authentication

- OAuth2 with automatic token refresh
- Secure credential storage
- Token binding for enhanced security

### Security Features

- Rate limiting with token bucket algorithm
- Circuit breaker for service resilience
- Input validation and sanitization
- Audit logging for compliance

### Production Security

See `docs/security-implementation.md` for detailed security configuration.

## Installation via Bodai Marketplace

This repo ships a Bodai Claude Code plugin. The plugin manifest (`.claude-plugin/plugin.json`) registers the local MCP server (`.mcp.json`, default `http://localhost:3037/mcp`) under the `opera-cloud` namespace and exposes three slash commands: `/opera-cloud-reservations`, `/opera-cloud-guests`, `/opera-cloud-rooms`. To install, add the Bodai marketplace once and then install the plugin: `claude plugin marketplace add /Users/les/Projects/bodai-plugins` followed by `claude plugin install opera-cloud --marketplace bodai-plugins`. Once installed, start the server with `opera-cloud-mcp` (HTTP on port 3037) and the slash commands will see the live `mcp__opera-cloud__*` tools.

## Documentation

- [Implementation Plan](docs/implementation-plan.md) - Development roadmap
- [Production Monitoring](docs/production-monitoring.md) - Monitoring setup
- [Security Implementation](docs/security-implementation.md) - Security configuration
- [AGENTS.md](AGENTS.md) - Complete tool reference for AI agents

## Contributing

1. Fork the repository
1. Create a feature branch
1. Make your changes
1. Run quality checks: `uv run crackerjack`
1. Submit a pull request

## License

BSD 3-Clause License - see [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/lesleslie/opera-cloud-mcp/issues)
- **Documentation**: See `/docs` directory
- **Examples**: See `/examples` directory

______________________________________________________________________

Built for the hospitality industry using [FastMCP](https://github.com/jlowin/fastmcp) and Oracle OPERA Cloud.
