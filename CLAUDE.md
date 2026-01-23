# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server for Oracle OPERA Cloud API integration. It provides AI agents with comprehensive access to hospitality management functions through 45+ tools across 5 domains: reservations, guests, rooms, operations, and financial management.

## Development Commands

### Core Commands

- `python -m opera_cloud_mcp` - Start the MCP server
- `uv run python -m opera_cloud_mcp` - Alternative server startup with UV
- `uv sync` - Install/sync dependencies

### Testing

- `uv run pytest` - Run all tests
- `uv run pytest tests/unit/` - Run unit tests only
- `uv run pytest tests/integration/` - Run integration tests only
- `uv run pytest --cov=opera_cloud_mcp --cov-report=html` - Test with coverage report
- `uv run pytest tests/unit/test_reservation_tools.py::TestReservationTools::test_search_reservations` - Run single test

### Code Quality

- `uv run crackerjack` - Run all quality checks (recommended)
- `uv run ruff check --fix` - Lint and auto-fix code
- `uv run mypy .` - Type checking
- `uv run bandit -r opera_cloud_mcp/` - Security scanning

### Production

- `docker build -t opera-cloud-mcp .` - Build Docker image
- `docker-compose up -d` - Run full stack with monitoring

## Architecture Overview

### Core Components

**FastMCP Server (`opera_cloud_mcp/server.py`)**

- Main MCP server using FastMCP framework
- Registers all tool modules and handles MCP protocol

**Base Client (`opera_cloud_mcp/clients/base_client.py`)**

- Foundation for all OPERA Cloud API interactions
- Handles OAuth2 authentication, rate limiting, circuit breaker
- Provides retry logic, error handling, and observability

**Tool Modules (`opera_cloud_mcp/tools/`)**

- `reservation_tools.py` - Booking and reservation management
- `guest_tools.py` - Guest profiles and loyalty programs
- `room_tools.py` - Room inventory and housekeeping
- `operation_tools.py` - Daily operations and reporting
- `financial_tools.py` - Billing and revenue management

**Authentication (`opera_cloud_mcp/auth/`)**

- OAuth2 handler with automatic token refresh
- Security middleware and audit logging
- Production-grade security enhancements

**API Clients (`opera_cloud_mcp/clients/api_clients/`)**

- Specialized clients for each OPERA Cloud module
- Handle endpoint-specific logic and data transformation

### Key Patterns

**Tool Registration**: Each tool module exports a `register_*_tools(app)` function that registers FastMCP tools

**Error Handling**: Custom exception hierarchy with specific error types for different failure modes

**Observability**: Structured logging, metrics, and distributed tracing through `utils/observability.py`

**Configuration**: Pydantic settings with environment variable support and security validation

## Testing Architecture

### Test Structure

- `tests/unit/` - Fast unit tests with mocking
- `tests/integration/` - Full API integration tests
- `tests/performance/` - Load and performance testing
- `tests/fixtures/` - Shared test data and mock responses

### Mock Strategy

Use `tests/fixtures/mock_responses.py` for consistent API mocking. Always mock external OPERA Cloud API calls in unit tests.

## Configuration

### Environment Setup

Copy `.env.example` to `.env` and configure:

```env
OPERA_CLOUD_BASE_URL=https://your-instance.com/api/v1
OPERA_CLOUD_CLIENT_ID=your_client_id
OPERA_CLOUD_CLIENT_SECRET=your_secret
OPERA_CLOUD_USERNAME=your_username
OPERA_CLOUD_PASSWORD=your_password
```

### MCP Client Integration

See `example.mcp.json` for production config and `example.mcp.dev.json` for development setup.

## Security Considerations

The `opera_cloud_mcp/config/security_settings.py` provides enterprise-grade security configuration including:

- Rate limiting and circuit breakers
- Audit logging and security monitoring
- Token binding and credential rotation
- Network restrictions and compliance features

Always use the security settings in production and never commit credentials to the repository.

<!-- CRACKERJACK_START -->

## Crackerjack Integration

This project uses Crackerjack for automated code quality and best practices.

### Quality Standards

- **Code Coverage**: Minimum 80% test coverage required
- **Type Safety**: All functions must have proper type hints
- **Security**: Bandit security scanning enabled
- **Style**: Ruff formatting and linting enforced
- **Dependencies**: Safety checks for known vulnerabilities

### Quality Checks

The following quality checks are enforced:

1. **Formatting**: Ruff auto-formatting
1. **Linting**: Ruff linting with auto-fixes
1. **Type Checking**: MyPy static analysis
1. **Security**: Bandit security scanning
1. **Dependencies**: UV dependency validation
1. **Safety**: Known vulnerability scanning

### Running Quality Checks

```bash
# Run all quality checks
uv run crackerjack

# Run specific tools
uv run ruff check --fix
uv run mypy .
uv run bandit -r .
uv run pytest --cov=.
```

### CI/CD Integration

Quality gates are enforced in CI/CD:

- All tests must pass
- Coverage threshold must be met
- No security vulnerabilities allowed
- All type checks must pass

### Configuration Files

- `pyproject.toml` - Tool configurations (ruff, mypy, pytest, bandit)
- Quality standards are automatically enforced

For more information, see the Crackerjack repository.

<!-- CRACKERJACK_END -->

<!-- CRACKERJACK INTEGRATION START -->

This project uses crackerjack for Python project management and quality assurance.

For optimal development experience with this crackerjack - enabled project, use these specialized agents:

- **🏗️ crackerjack-architect**: Expert in crackerjack's modular architecture and Python project management patterns. **Use PROACTIVELY** for all feature development, architectural decisions, and ensuring code follows crackerjack standards from the start.

- **🐍 python-pro**: Modern Python development with type hints, async/await patterns, and clean architecture

- **🧪 pytest-hypothesis-specialist**: Advanced testing patterns, property-based testing, and test optimization

- **🧪 crackerjack-test-specialist**: Advanced testing specialist for complex testing scenarios and coverage optimization

- **🏗️ backend-architect**: System design, API architecture, and service integration patterns

- **🔒 security-auditor**: Security analysis, vulnerability detection, and secure coding practices

```bash

Task tool with subagent_type ="crackerjack-architect" for feature planning


Task tool with subagent_type ="python-pro" for code implementation


Task tool with subagent_type ="pytest-hypothesis-specialist" for test development


Task tool with subagent_type ="security-auditor" for security analysis
```

**💡 Pro Tip**: The crackerjack-architect agent automatically ensures code follows crackerjack patterns from the start, eliminating the need for retrofitting and quality fixes.

This project follows crackerjack's clean code philosophy:

- **EVERY LINE OF CODE IS A LIABILITY**: The best code is no code

- **DRY (Don't Repeat Yourself)**: If you write it twice, you're doing it wrong

- **YAGNI (You Ain't Gonna Need It)**: Build only what's needed NOW

- **KISS (Keep It Simple, Stupid)**: Complexity is the enemy of maintainability

- \*\*Cognitive complexity ≤15 \*\*per function (automatically enforced)

- **Coverage ratchet system**: Never decrease coverage, always improve toward 100%

- **Type annotations required**: All functions must have return type hints

- **Security patterns**: No hardcoded paths, proper temp file handling

- **Python 3.13+ modern patterns**: Use `|` unions, pathlib over os.path

```bash

python -m crackerjack


python -m crackerjack - t


python -m crackerjack - - ai - agent - t


python -m crackerjack - a patch
```

1. **Plan with crackerjack-architect**: Ensure proper architecture from the start
1. **Implement with python-pro**: Follow modern Python patterns
1. **Test comprehensively**: Use pytest-hypothesis-specialist for robust testing
1. **Run quality checks**: `python -m crackerjack -t` before committing
1. **Security review**: Use security-auditor for final validation

- **Use crackerjack-architect agent proactively** for all significant code changes
- **Never reduce test coverage** - the ratchet system only allows improvements
- **Follow crackerjack patterns** - the tools will enforce quality automatically
- **Leverage AI agent auto-fixing** - `python -m crackerjack --ai-agent -t` for autonomous quality fixes

______________________________________________________________________

- This project is enhanced by crackerjack's intelligent Python project management.\*

<!-- CRACKERJACK INTEGRATION END -->
