# Repository Guidelines

## Project Structure & Module Organization

- `opera_cloud_mcp/` holds FastMCP server core (tool definitions, OAuth clients, CLI entry at `cli.py`).
- `tests/` mirrors package modules with async integration stubs; put new fixtures in `tests/conftest.py`.
- `docs/` collects reference material shared with MCP agents; keep diagrams and user-facing notes there.
- `examples/` contains sample MCP configurations; use it for runnable snippets.
- Build artefacts (`dist/`, `htmlcov/`, `coverage.json`) are generated; leave them out of commits.

## Build, Test & Development Commands

- `uv sync` installs production + dev dependencies pinned by `uv.lock`.
- `uv run python -m opera_cloud_mcp` starts the local MCP server.
- `uv run pytest` runs the default test suite.
- `uv run pytest --cov=opera_cloud_mcp --cov-report=html` enforces 80% coverage and emits `htmlcov/`.
- `uv run crackerjack` executes the full quality gate (ruff, mypy, bandit, pytest).
- `docker build -t opera-cloud-mcp .` produces the hardened container image.

## Coding Style & Naming Conventions

- Target Python 3.13 with type hints everywhere; `mypy` is configured in strict mode.
- Format with `ruff format`; lint with `ruff check` (line length 88, fixes allowed).
- Use `snake_case` for modules/functions, `PascalCase` classes, `UPPER_SNAKE` constants, and keep MCP tool IDs kebab-cased.
- Prefer dataclasses/pydantic models for payloads; document public functions with concise docstrings.

## Testing Guidelines

- Tests live under `tests/` and follow `test_<module>.py` filenames with `Test*` classes and `test_*` functions.
- Use `pytest.mark.asyncio` for coroutine scenarios.
- Keep coverage ≥80%; add regression tests alongside new tools (e.g., `tests/test_reservations.py::TestReservationFlows::test_create_reservation`).
- Run `uv run pytest -k your_feature` before pushing incremental updates.

## Commit & Pull Request Guidelines

- Follow conventional commit headers (`feat(api): add reservation splitter`, `fix(test): adjust flaky check`) to aid release tooling.
- Describe intent and validation steps in PRs; link GitHub issues or MCP ticket IDs.
- Include screenshots or sample terminal output when behavior changes, especially for monitoring dashboards or CLI flows.

## Security & Configuration Tips

- Store secrets in `.env`; never commit values for `OPERA_CLIENT_ID`, `OPERA_CLIENT_SECRET`, or token URLs.
- Confirm `/health` and `/metrics` respond locally before sharing MCP endpoints.
- Rotate credentials used in examples and scrub PII in log attachments.
