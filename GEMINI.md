# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the OPERA Cloud MCP Server project.

## Project Overview

The `opera-cloud-mcp` project is a Python-based Model Context Protocol (MCP) server that acts as an intermediary between AI agents and the Oracle OPERA Cloud API. It allows AI agents to interact with hospitality management systems for tasks related to reservations, guest management, room operations, and financials.

The project is built using the `FastMCP` framework for high-performance MCP protocol support and is designed for production environments with features like security, monitoring, and rate limiting.

**Key Technologies:**

- **Backend:** Python, FastMCP, `httpx` for asynchronous API requests.
- **Authentication:** OAuth2 for secure communication with the OPERA Cloud API.
- **Dependencies:** Managed with `uv` and defined in `pyproject.toml`.
- **Code Quality:** Enforced using `ruff` for linting and formatting, `mypy` for static type checking, and `pytest` for testing.

**Architecture:**

The server is structured in a modular way:

- `opera_cloud_mcp/server.py`: The main entry point for the FastMCP application. It initializes the server and registers the available tools.
- `opera_cloud_mcp/cli.py`: Implements the command-line interface for managing the server (start, stop, restart, status).
- `opera_cloud_mcp/tools/`: This directory contains modules that define the tools available to the AI agents. Each module corresponds to a specific domain of the OPERA Cloud API (e.g., reservations, guests, rooms).
- `opera_cloud_mcp/clients/`: This directory contains the API clients for interacting with the OPERA Cloud API.
- `opera_cloud_mcp/config/`: Configuration for the application, including settings and security.
- `opera_cloud_mcp/models/`: Pydantic models for data validation and serialization.

## Building and Running

**Installation:**

To set up the development environment and install the required dependencies, run the following command:

```bash
uv sync
```

**Running the Server:**

You can run the MCP server using the following command:

```bash
python -m opera_cloud_mcp --start-mcp-server
```

Or, if you have `uv` installed:

```bash
uv run python -m opera_cloud_mcp --start-mcp-server
```

The server can also be run as a background process:

```bash
python -m opera_cloud_mcp --start-mcp-server -d
```

**Available CLI Commands:**

- `--start-mcp-server`: Starts the MCP server.
- `--stop-mcp-server`: Stops the MCP server.
- `--restart-mcp-server`: Restarts the MCP server.
- `--status`: Shows the current status of the server.
- `--version`: Displays the version of the server.

## Development Conventions

**Code Style:**

The project uses `ruff` for code formatting and linting. Please ensure your contributions adhere to the defined style by running:

```bash
uv run ruff check --fix
```

**Type Checking:**

The project uses `mypy` for static type checking. Before committing your changes, run `mypy` to check for any type errors:

```bash
uv run mypy .
```

**Testing:**

The project uses `pytest` for testing. To run the test suite:

```bash
uv run pytest
```

To run the tests with coverage:

```bash
uv run pytest --cov=opera_cloud_mcp --cov-report=html
```

**Committing Changes:**

Before committing any changes, it's recommended to run all quality checks:

```bash
uv run crackerjack
```
