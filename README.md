# OPERA Cloud MCP Server

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13%2B-green)](https://www.python.org/downloads/)
![Coverage](https://img.shields.io/badge/coverage-38.6%25-red)

Unofficial Model Context Protocol (MCP) server for Oracle OPERA Cloud API integration, enabling AI agents to interact with hospitality management systems.

## Features

- **Complete OPERA Cloud Integration**: Access to reservations, guests, rooms, operations, and financial data
- **FastMCP Framework**: Built on FastMCP for high-performance MCP protocol support
- **Production Ready**: Security, monitoring, rate limiting, and Docker deployment
- **45+ Tools**: Comprehensive API coverage across 5 core domains
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
OPERA_CLOUD_BASE_URL=https://your-opera-instance.com/api/v1
OPERA_CLOUD_CLIENT_ID=your_client_id
OPERA_CLOUD_CLIENT_SECRET=your_client_secret
OPERA_CLOUD_USERNAME=your_username
OPERA_CLOUD_PASSWORD=your_password
```

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
        "OPERA_CLOUD_BASE_URL": "https://your-opera-instance.com/api/v1",
        "OPERA_CLOUD_CLIENT_ID": "your_client_id",
        "OPERA_CLOUD_CLIENT_SECRET": "your_client_secret",
        "OPERA_CLOUD_USERNAME": "your_username",
        "OPERA_CLOUD_PASSWORD": "your_password"
      }
    }
  }
}
```

### Other MCP Clients

See `example.mcp.json` and `example.mcp.dev.json` for configuration templates.

## Available Tools

The server provides 45+ tools across 5 domains:

### Reservation Management (15 tools)

- Search reservations by date, guest, or status
- Create, modify, and cancel reservations
- Handle check-in/check-out operations
- Manage group bookings and waitlists

### Guest Management (12 tools)

- Guest profile creation and updates
- Loyalty program management
- Communication preferences
- Guest history and analytics

### Room Management (8 tools)

- Room availability and inventory
- Housekeeping status updates
- Room assignments and moves
- Maintenance coordination

### Operations Management (6 tools)

- Daily operations reporting
- Occupancy forecasting
- Revenue management
- Event coordination

### Financial Management (4 tools)

- Billing and invoicing
- Payment processing
- Revenue reporting
- Financial analytics

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
```

## Production Deployment

### Docker

```bash
# Build image
docker build -t opera-cloud-mcp .

# Run container
docker run -d \
  --name opera-cloud-mcp \
  -p 8000:8000 \
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

| Variable | Description | Required |
|----------|-------------|----------|
| `OPERA_CLOUD_BASE_URL` | OPERA Cloud API base URL | Yes |
| `OPERA_CLOUD_CLIENT_ID` | OAuth2 client ID | Yes |
| `OPERA_CLOUD_CLIENT_SECRET` | OAuth2 client secret | Yes |
| `OPERA_CLOUD_USERNAME` | OPERA Cloud username | Yes |
| `OPERA_CLOUD_PASSWORD` | OPERA Cloud password | Yes |
| `OPERA_CLOUD_TIMEOUT` | Request timeout (seconds) | No (default: 30) |
| `OPERA_CLOUD_MAX_CONNECTIONS` | Max HTTP connections | No (default: 50) |
| `OPERA_CLOUD_RATE_LIMIT` | Rate limit (requests/second) | No (default: 10) |

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
