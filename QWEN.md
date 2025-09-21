# OPERA Cloud MCP Server - Developer Guide

## Project Overview

The OPERA Cloud MCP Server is a Python-based Model Context Protocol (MCP) server that provides AI agents with seamless access to Oracle OPERA Cloud hospitality management APIs. It enables integration with reservation management, guest services, room operations, and financial systems through 45+ specialized tools.

### Key Technologies

- **Framework**: Built on FastMCP for high-performance MCP protocol support
- **Language**: Python 3.13+
- **Dependencies**:
  - FastMCP, HTTPX, Pydantic for core functionality
  - OAuth2 authentication and security features
  - Comprehensive testing with pytest
- **Architecture**: Modular design with separate API clients, models, tools, and utilities

### Core Components

1. **API Clients** (`opera_cloud_mcp/clients/api_clients/`): Specialized clients for different OPERA Cloud domains
1. **Models** (`opera_cloud_mcp/models/`): Pydantic models for data validation and serialization
1. **Tools** (`opera_cloud_mcp/tools/`): MCP tools organized by business domain
1. **Authentication** (`opera_cloud_mcp/auth/`): OAuth2 and security handling
1. **Configuration** (`opera_cloud_mcp/config/`): Settings and configuration management

## Building and Running

### Prerequisites

- Python 3.13+
- uv package manager (recommended) or pip

### Installation

```bash
# Clone the repository
git clone https://github.com/lesleslie/opera-cloud-mcp.git
cd opera-cloud-mcp

# Install dependencies using uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

### Configuration

Copy and configure environment variables:

```bash
cp .env.example .env
# Edit .env with your OPERA Cloud credentials
```

### Running the Server

```bash
# Development mode
python -m opera_cloud_mcp

# Or with uv
uv run python -m opera_cloud_mcp
```

### Testing

```bash
# Run all unit tests
pytest tests/unit/

# Run tests with coverage
pytest tests/unit/ --cov=opera_cloud_mcp --cov-report=html

# Run specific test file
pytest tests/unit/test_front_office_client.py
```

## Development Conventions

### Code Structure

- **Modular Organization**: Each business domain has dedicated modules (clients, models, tools)
- **API Client Pattern**: All clients inherit from BaseAPIClient with common functionality
- **Pydantic Models**: Strongly typed data validation using Pydantic v2
- **Async/Await**: Fully asynchronous implementation for high performance

### Testing Practices

- **Unit Tests**: Comprehensive test coverage for all API clients and models
- **Mocking Strategy**: Use `unittest.mock.patch.object()` to mock specific client methods
- **Test Fixtures**: Extensive use of pytest fixtures for reusable test data
- **Integration Tests**: Separate integration tests for end-to-end scenarios

### Naming Conventions

- **Files**: snake_case for module names
- **Classes**: PascalCase for class names
- **Functions**: snake_case for function names
- **Variables**: snake_case for variable names
- **Constants**: UPPER_SNAKE_CASE for constants

### Error Handling

- **Custom Exceptions**: Domain-specific exceptions inheriting from OperaCloudError
- **HTTP Status Mapping**: Proper mapping of HTTP status codes to exception types
- **Retry Logic**: Automatic retry with exponential backoff for transient failures
- **Circuit Breaker**: Protection against cascading failures

## Module Structure

### Main Modules

- `opera_cloud_mcp/`: Root package
  - `clients/`: API clients for OPERA Cloud services
    - `api_clients/`: Domain-specific client implementations
    - `base_client.py`: Base client with common functionality
    - `client_factory.py`: Factory for creating client instances
  - `models/`: Pydantic data models
  - `auth/`: Authentication and security modules
  - `tools/`: MCP tools organized by business domain
  - `utils/`: Utility functions and helpers
  - `config/`: Configuration management
  - `resources/`: Static resources and specifications

### Testing Structure

- `tests/`: Root test directory
  - `unit/`: Unit tests for individual modules
  - `integration/`: Integration tests for combined functionality
  - `performance/`: Performance and load tests
  - `fixtures/`: Shared test data and fixtures

## Contributing

### Development Workflow

1. Create feature branch from main
1. Implement changes with accompanying tests
1. Run full test suite to ensure no regressions
1. Update documentation if needed
1. Submit pull request with clear description

### Code Quality Standards

- **Linting**: Ruff for code formatting and linting
- **Type Checking**: Mypy for static type analysis
- **Security Scanning**: Bandit for security vulnerability detection
- **Test Coverage**: Minimum 80% code coverage required

### Branch Naming

- `feature/feature-name` for new features
- `fix/issue-description` for bug fixes
- `hotfix/critical-issue` for urgent production fixes
- `docs/documentation-update` for documentation changes

### Commit Messages

Follow conventional commit format:

- `feat: Add new feature`
- `fix: Resolve bug issue`
- `docs: Update documentation`
- `test: Add test cases`
- `refactor: Restructure code`
- `chore: Maintenance tasks`
