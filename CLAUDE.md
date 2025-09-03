# CLAUDE.md

This file provides guidance to Claude Code when working with this opera-cloud-mcp project.

## Project Overview

This is an MCP (Model Context Protocol) server for the Opera Cloud API. It enables AI agents to interact with Opera Cloud services and infrastructure.

## Development Guidelines

### Code Quality

- Follow PEP 8 style guidelines
- Use type hints for all functions and methods
- Write comprehensive docstrings
- Maintain test coverage above 80%

### Testing

- Write unit tests for all new functionality
- Use pytest for testing framework
- Mock external API calls in tests
- Test both success and error scenarios

### Security

- Never commit API keys or sensitive credentials
- Use environment variables for configuration
- Validate all inputs from external sources
- Follow security best practices for API integrations

### Documentation

- Keep README.md updated with setup and usage instructions
- Document all public APIs
- Include example usage in docstrings
- Update this CLAUDE.md file when project structure changes

## Project Structure

- `main.py` - Main MCP server entry point
- `pyproject.toml` - Project configuration and dependencies
- `.pre-commit-config.yaml` - Code quality hooks
- `.mcp.json` - MCP server configuration

## Development Commands

- `uv run main.py` - Start the MCP server
- `uv run pytest` - Run tests
- `uv run ruff check` - Lint code
- `uv run mypy` - Type checking

## MCP Integration

This server is designed to work with Claude Code and other MCP-compatible clients. Ensure all MCP protocol requirements are met when making changes.

<!-- CRACKERJACK_START -->

## Crackerjack Integration

This project uses [Crackerjack](https://github.com/lesliepython/crackerjack) for automated code quality and best practices.

### Quality Standards

- **Code Coverage**: Minimum 80% test coverage required
- **Type Safety**: All functions must have proper type hints
- **Security**: Bandit security scanning enabled
- **Style**: Ruff formatting and linting enforced
- **Dependencies**: Safety checks for known vulnerabilities

### Pre-commit Hooks

The following quality checks run automatically on every commit:

1. **Formatting**: Ruff auto-formatting
1. **Linting**: Ruff linting with auto-fixes
1. **Type Checking**: MyPy static analysis
1. **Security**: Bandit security scanning
1. **Dependencies**: Poetry/UV dependency validation
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

- `.pre-commit-config.yaml` - Pre-commit hook configuration
- `pyproject.toml` - Tool configurations (ruff, mypy, pytest, bandit)
- Quality standards are automatically enforced

For more information, see: https://github.com/lesliepython/crackerjack

<!-- CRACKERJACK_END -->
