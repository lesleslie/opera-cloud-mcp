# OPERA Cloud MCP Server Implementation Plan

## Project Overview

Build a FastMCP-based Model Context Protocol server to interface with Oracle OPERA Cloud APIs, providing AI agents with seamless access to hospitality management functions.

### Key Objectives

- Provide comprehensive access to OPERA Cloud REST APIs
- Implement secure OAuth2 authentication
- Create intuitive MCP tools for common hospitality operations
- Ensure production-ready code quality with Crackerjack standards
- Achieve >80% test coverage

## Oracle OPERA Cloud API Overview

### Available API Domains

Based on the Oracle Hospitality API documentation:

| API Code | Domain | Description |
|----------|--------|-------------|
| `oauth` | Authentication | OAuth2 token management |
| `rsv` | Reservations | Booking management (sync) |
| `rsvasync` | Reservations | Bulk booking operations (async) |
| `fof` | Front Office | Check-in/out, billing, payments |
| `hsk` | Housekeeping | Room status, cleaning schedules |
| `crm` | Customer Relations | Guest profiles, preferences |
| `inv` | Inventory | Room availability, restrictions |
| `blk` | Block Management | Group bookings, events |
| `rtp` | Rate Planning | Pricing, rate codes |
| `csh` | Cashiering | Payment processing |
| `act` | Activities | Guest activities, amenities |

### API Characteristics

- **REST Architecture**: Standard HTTP methods (GET, POST, PUT, DELETE)
- **JSON Format**: Request/response payloads in JSON
- **OAuth2 Authentication**: Bearer token authorization
- **Versioning**: API version in URL path
- **Rate Limiting**: Throttling applies to prevent abuse

## Architecture Design

### 1. Project Structure

```
opera_cloud_mcp/
├── __init__.py
├── main.py                    # FastMCP server entry point
├── auth/
│   ├── __init__.py
│   └── oauth_handler.py       # OAuth2 token management
├── clients/
│   ├── __init__.py
│   ├── base_client.py         # Base HTTP client with auth
│   └── api_clients/           # Specific API clients
│       ├── reservations.py
│       ├── front_office.py
│       ├── housekeeping.py
│       ├── crm.py
│       ├── inventory.py
│       ├── block.py
│       ├── rates.py
│       └── cashiering.py
├── tools/
│   ├── __init__.py
│   ├── reservation_tools.py   # Reservation management tools
│   ├── guest_tools.py          # Guest/CRM tools
│   ├── room_tools.py           # Room/inventory tools
│   ├── operation_tools.py     # Daily operations tools
│   └── financial_tools.py     # Billing/payment tools
├── resources/
│   ├── __init__.py
│   └── api_specs.py           # API spec resources
├── models/
│   ├── __init__.py
│   ├── common.py              # Common data models
│   ├── reservation.py         # Reservation models
│   ├── guest.py               # Guest/profile models
│   ├── room.py                # Room/inventory models
│   └── financial.py           # Financial models
├── config/
│   ├── __init__.py
│   └── settings.py            # Configuration management
├── utils/
│   ├── __init__.py
│   ├── validators.py          # Input validation
│   ├── formatters.py          # Data formatting
│   └── exceptions.py          # Custom exceptions
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   ├── test_auth.py
    │   ├── test_clients.py
    │   └── test_models.py
    ├── integration/
    │   ├── test_tools.py
    │   └── test_workflows.py
    └── fixtures/
        └── mock_responses.py
```

### 2. Core Components

#### Authentication Module (`auth/oauth_handler.py`)

```python
class OAuthHandler:
    """Manages OAuth2 authentication for OPERA Cloud APIs."""

    def __init__(self, client_id: str, client_secret: str, base_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self._token_cache: Optional[Token] = None
        self._token_expiry: Optional[datetime] = None

    async def get_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        if self._is_token_valid():
            return self._token_cache.access_token
        return await self._refresh_token()

    async def _refresh_token(self) -> str:
        """Request new token from OAuth endpoint."""
        # Implementation details
        pass
```

#### Base API Client (`clients/base_client.py`)

```python
class BaseAPIClient:
    """Base client with common functionality for all API clients."""

    def __init__(self, auth_handler: OAuthHandler, hotel_id: str):
        self.auth = auth_handler
        self.hotel_id = hotel_id
        self.session = httpx.AsyncClient()

    async def request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make authenticated API request with retry logic."""
        # Add authentication header
        # Implement retry logic
        # Handle errors
        pass
```

#### MCP Tools Structure

```python
from fastmcp import FastMCP
from fastmcp.tools import tool
from typing import Optional, List, Dict

app = FastMCP(
    name="opera-cloud-mcp",
    version="0.1.0",
    description="MCP server for Oracle OPERA Cloud API integration",
)


@tool(description="Search for hotel reservations by various criteria")
async def search_reservations(
    hotel_id: str,
    arrival_date: Optional[str] = None,
    departure_date: Optional[str] = None,
    guest_name: Optional[str] = None,
    confirmation_number: Optional[str] = None,
    limit: int = 10,
) -> Dict:
    """
    Search for reservations in OPERA Cloud.

    Args:
        hotel_id: Hotel identifier
        arrival_date: Arrival date (YYYY-MM-DD)
        departure_date: Departure date (YYYY-MM-DD)
        guest_name: Guest name (partial match supported)
        confirmation_number: Confirmation number
        limit: Maximum results to return

    Returns:
        Dictionary containing reservation search results
    """
    # Implementation
    pass
```

## Implementation Phases

### Phase 1: Foundation (Days 1-2)

#### Tasks:

1. **Project Setup**

   - Initialize project structure
   - Configure FastMCP server
   - Set up development environment
   - Configure Crackerjack tools

1. **Authentication Implementation**

   - OAuth2 token handler
   - Token caching mechanism
   - Automatic token refresh
   - Credential management

1. **Base Infrastructure**

   - HTTP client with retry logic
   - Error handling framework
   - Logging configuration
   - Configuration management

#### Deliverables:

- Working FastMCP server
- OAuth authentication
- Base client implementation
- Development environment ready

### Phase 2: Core APIs (Days 3-5)

#### Priority 1: Reservation Management

- **Client**: `ReservationClient`
- **Tools**:
  - `search_reservations`
  - `create_reservation`
  - `get_reservation`
  - `modify_reservation`
  - `cancel_reservation`

#### Priority 2: Guest Operations

- **Client**: `CRMClient`
- **Tools**:
  - `search_guests`
  - `get_guest_profile`
  - `update_guest_profile`
  - `get_guest_history`
  - `merge_guest_profiles`

#### Priority 3: Room Management

- **Client**: `InventoryClient`
- **Tools**:
  - `check_room_availability`
  - `get_room_status`
  - `update_room_status`
  - `get_housekeeping_tasks`

### Phase 3: Extended Operations (Days 6-7)

#### Front Office Operations

- **Client**: `FrontOfficeClient`
- **Tools**:
  - `check_in_guest`
  - `check_out_guest`
  - `get_arrivals_report`
  - `get_departures_report`
  - `process_walk_in`

#### Financial Operations

- **Client**: `CashieringClient`
- **Tools**:
  - `post_charge`
  - `process_payment`
  - `generate_folio`
  - `transfer_charges`

### Phase 4: Testing & Documentation (Days 8-9)

#### Testing Strategy

1. **Unit Tests** (>80% coverage)

   - Auth module tests
   - Client tests with mocked responses
   - Model validation tests
   - Utility function tests

1. **Integration Tests**

   - Tool execution tests
   - End-to-end workflows
   - Error handling scenarios
   - Rate limiting tests

1. **Contract Tests**

   - Validate against OpenAPI specs
   - Response format validation
   - Required field checks

#### Documentation

- README with quick start
- API reference documentation
- Tool usage examples
- Troubleshooting guide
- Deployment instructions

### Phase 5: Production Readiness (Days 10)

#### Performance Optimization

- Response caching strategy
- Connection pooling
- Async operation optimization
- Rate limiting implementation

#### Monitoring & Observability

- Structured logging
- Metrics collection
- Health check endpoint
- Error tracking

## Technical Specifications

### Configuration Management

```python
# config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # OAuth Configuration
    opera_client_id: str
    opera_client_secret: str
    opera_token_url: str = "https://api.oracle-hospitality.com/oauth/v1/tokens"

    # API Configuration
    opera_base_url: str = "https://api.oracle-hospitality.com"
    opera_api_version: str = "v1"
    opera_environment: str = "production"

    # Default Hotel Configuration
    default_hotel_id: Optional[str] = None

    # Client Configuration
    request_timeout: int = 30
    max_retries: int = 3
    retry_backoff: float = 1.0

    # Caching
    enable_cache: bool = True
    cache_ttl: int = 300  # 5 minutes

    class Config:
        env_file = ".env"
        env_prefix = "OPERA_"
```

### Error Handling

```python
# utils/exceptions.py
class OperaCloudError(Exception):
    """Base exception for OPERA Cloud MCP."""

    pass


class AuthenticationError(OperaCloudError):
    """Authentication failed."""

    pass


class RateLimitError(OperaCloudError):
    """Rate limit exceeded."""

    pass


class ResourceNotFoundError(OperaCloudError):
    """Requested resource not found."""

    pass


class ValidationError(OperaCloudError):
    """Request validation failed."""

    pass
```

### Data Models (Pydantic)

```python
# models/reservation.py
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List


class Guest(BaseModel):
    """Guest information model."""

    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    loyalty_number: Optional[str] = None


class Reservation(BaseModel):
    """Reservation model."""

    confirmation_number: str
    hotel_id: str
    guest: Guest
    arrival_date: date
    departure_date: date
    room_type: str
    rate_code: str
    total_amount: float
    status: str
    created_at: datetime
    modified_at: Optional[datetime] = None
```

## MCP Tools Catalog

### Reservation Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `search_reservations` | Search reservations by criteria | hotel_id, dates, guest_name |
| `create_reservation` | Create new reservation | guest_info, dates, room_type |
| `get_reservation` | Get reservation details | confirmation_number |
| `modify_reservation` | Update reservation | confirmation_number, changes |
| `cancel_reservation` | Cancel reservation | confirmation_number, reason |

### Guest Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `search_guests` | Search guest profiles | name, email, phone |
| `get_guest_profile` | Get guest details | guest_id |
| `update_guest_profile` | Update guest info | guest_id, updates |
| `get_guest_history` | Get stay history | guest_id, date_range |
| `get_guest_preferences` | Get preferences | guest_id |

### Room Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `check_room_availability` | Check available rooms | dates, room_type |
| `get_room_status` | Get room status | room_number |
| `update_room_status` | Update status | room_number, status |
| `get_housekeeping_schedule` | Get cleaning schedule | date |
| `assign_room` | Assign room to reservation | confirmation_number, room |

### Operational Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `get_arrivals_report` | Today's arrivals | date, status |
| `get_departures_report` | Today's departures | date, status |
| `get_occupancy_report` | Occupancy statistics | date_range |
| `get_revenue_report` | Revenue summary | date_range |
| `get_no_show_report` | No-show guests | date |

## Development Guidelines

### Code Quality Standards (Crackerjack)

1. **Type Hints**: All functions must have type hints
1. **Docstrings**: Comprehensive docstrings for all public functions
1. **Testing**: Minimum 80% code coverage
1. **Linting**: Pass all ruff checks
1. **Security**: Pass bandit security scans
1. **Formatting**: Follow black/ruff formatting

### Async Best Practices

```python
# Use async context managers
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# Concurrent operations
import asyncio

results = await asyncio.gather(
    fetch_reservation(id1), fetch_reservation(id2), fetch_reservation(id3)
)
```

### Security Considerations

1. **No hardcoded credentials** - Use environment variables
1. **Input validation** - Validate all user inputs
1. **SQL injection prevention** - Use parameterized queries
1. **Rate limiting** - Implement client-side rate limiting
1. **Audit logging** - Log all operations
1. **Data encryption** - Encrypt sensitive data at rest

## Testing Strategy

### Unit Test Example

```python
# tests/unit/test_auth.py
import pytest
from unittest.mock import AsyncMock, patch
from opera_cloud_mcp.auth import OAuthHandler


@pytest.mark.asyncio
async def test_token_refresh():
    """Test OAuth token refresh."""
    handler = OAuthHandler(
        client_id="test", client_secret="secret", base_url="https://api.test.com"
    )

    with patch.object(handler, "_request_token") as mock_request:
        mock_request.return_value = AsyncMock(
            return_value={"access_token": "new_token", "expires_in": 3600}
        )

        token = await handler.get_token()
        assert token == "new_token"
```

### Integration Test Example

```python
# tests/integration/test_tools.py
import pytest
from fastmcp.testing import TestClient
from opera_cloud_mcp.main import app


@pytest.mark.asyncio
async def test_search_reservations_tool():
    """Test reservation search tool."""
    async with TestClient(app) as client:
        result = await client.call_tool(
            "search_reservations", hotel_id="HOTEL123", arrival_date="2024-12-01"
        )

        assert result["success"] is True
        assert "reservations" in result["data"]
```

## Deployment Configuration

### Docker Setup

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

COPY . .

CMD ["uv", "run", "python", "-m", "opera_cloud_mcp.main"]
```

### Environment Variables

```bash
# .env.example
# OAuth Configuration
OPERA_CLIENT_ID=your_client_id
OPERA_CLIENT_SECRET=your_client_secret
OPERA_TOKEN_URL=https://api.oracle-hospitality.com/oauth/v1/tokens

# API Configuration
OPERA_BASE_URL=https://api.oracle-hospitality.com
OPERA_API_VERSION=v1
OPERA_ENVIRONMENT=production

# Default Configuration
OPERA_DEFAULT_HOTEL_ID=HOTEL123

# Performance Settings
OPERA_REQUEST_TIMEOUT=30
OPERA_MAX_RETRIES=3
OPERA_ENABLE_CACHE=true
OPERA_CACHE_TTL=300
```

## Monitoring & Observability

### Logging Configuration

```python
import structlog

logger = structlog.get_logger()

# Log API requests
logger.info(
    "api_request",
    method=method,
    endpoint=endpoint,
    hotel_id=hotel_id,
    duration=duration,
)

# Log errors
logger.error(
    "api_error", error_type=type(e).__name__, error_message=str(e), endpoint=endpoint
)
```

### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    checks = {
        "api": await check_api_connectivity(),
        "auth": await check_auth_status(),
        "cache": check_cache_health(),
    }

    return {
        "status": "healthy" if all(checks.values()) else "degraded",
        "checks": checks,
        "version": app.version,
    }
```

## Success Metrics

### Functional Requirements

- ✅ OAuth2 authentication working
- ✅ All major OPERA Cloud APIs integrated
- ✅ Core MCP tools implemented
- ✅ Error handling for all edge cases
- ✅ Comprehensive logging

### Performance Requirements

- ✅ Response time < 2 seconds for all operations
- ✅ Support for concurrent requests
- ✅ Efficient token caching
- ✅ Connection pooling implemented

### Quality Requirements

- ✅ >80% test coverage
- ✅ All Crackerjack checks passing
- ✅ Type hints on all functions
- ✅ Comprehensive documentation
- ✅ Security scanning passed

## Crackerjack Agents Usage

### Development Workflow

1. **python-pro**: Core implementation

   - FastMCP server setup
   - Async/await patterns
   - Error handling

1. **backend-architect**: Architecture design

   - API client structure
   - Caching strategy
   - Performance optimization

1. **authentication-specialist**: OAuth implementation

   - Token management
   - Security best practices
   - Credential handling

1. **api-documenter**: Documentation

   - OpenAPI integration
   - Tool descriptions
   - Usage examples

1. **test-specialist**: Testing strategy

   - Unit test design
   - Integration testing
   - Mock strategies

1. **crackerjack-test-specialist**: Quality assurance

   - Coverage requirements
   - Linting compliance
   - Security validation

## Next Steps

1. **Immediate Actions**

   - Set up OAuth credentials with Oracle
   - Create development environment
   - Initialize FastMCP server

1. **Development Priorities**

   - Implement authentication first
   - Build reservation tools (highest value)
   - Add guest management
   - Expand to other domains

1. **Testing & Validation**

   - Set up sandbox environment
   - Create test data fixtures
   - Validate against real API

1. **Documentation**

   - Create user guide
   - Document all tools
   - Provide code examples

## Resources & References

- [Oracle Hospitality Integration Platform](https://www.oracle.com/hospitality/integration-platform/)
- Oracle Hospitality API Documentation
- [OPERA Cloud API Documentation](https://docs.oracle.com/en/industries/hospitality/integration-platform/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- Crackerjack Standards

______________________________________________________________________

*This implementation plan provides a comprehensive roadmap for building a production-ready MCP server for OPERA Cloud integration. Follow the phases sequentially for best results.*
