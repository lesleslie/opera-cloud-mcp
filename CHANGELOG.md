# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-08-20

### Added

- opera-cloud-mcp: Adopt apply_tool_profile() with OPERA_CLOUD_TOOL_PROFILE
- opera-cloud: Bodai plugin conversion (manifest, mcp.json, slash commands)

### Fixed

- opera-cloud-mcp: Broaden PROFILE_REGISTRATIONS type and drop unused ty:ignore
- opera-cloud-mcp: In-progress WIP commit before dep refresh
- opera-cloud-mcp: Shorten E501 line in __main__.py
- opera-cloud-mcp: Sync __init__.py version to pyproject.toml
- opera-cloud-mcp: Untrack .pyscn/reports/ artifacts

### Documentation

- opera-cloud-mcp: Inline mermaid diagrams + fix OPFRA typo + update tool counts
- opera-cloud-mcp: Reconcile audit findings across README, AGENTS, example config

### Internal

- Gitignore runtime artifacts + untrack user-authorized cache files (bodai cleanup 2026-08-17)
- gitignore: Untrack .pyscn/ (bodai 2026-08-20)
- opera-cloud-mcp: Annotate [tool.crackerjack] baseline + uv sync upgrade
- opera-cloud-mcp: Gitignore .lycheecache (file, not just dir)
- opera-cloud-mcp: Gitignore .lycheecache + .hypothesis
- opera-cloud-mcp: Refresh oneiric + mcp-common deps
- opera-cloud-mcp: Untrack .lycheecache (final)
- Untrack backup files (.backup, .backup.json, .bak)

## [0.4.0] - 2026-08-12

### Fixed

- Address ruff E501 + E402

### Internal

- Adopt register_http_health_route from mcp-common
- Bump oneiric dep to >=0.16.0
- Fix FastMCP 3.x test drift surfaced by pin bump
- Fix pre-existing test failures surfaced by FastMCP 3.x bump
- Migrate MCPBaseSettings → OneiricMCPConfig, bump fastmcp to >=3.4.0,\<4
- Normalize LICENSE attribution to Robert Leslie and Wedgwood Web Works, 2026
- opera-cloud-mcp: Migrate # type: ignore stragglers to ty syntax or fix
- Use __version__ instead of hardcoded version literal

## [0.3.7] - 2026-06-20

### Internal

- Add .cache dir for gitleaks quality tooling
- gitignore: Add backup file patterns to silence checkpoint tool artifacts
- Untrack and delete 9 historical *.backup/*.bak files

## [0.3.5] - 2026-05-10

### Changed

- Opera-cloud-mcp (quality: 75/100) - 2026-02-22 02:29:42

### Fixed

- Add health endpoints for Claude Code compatibility
- Catch APIKeyFormatError in OAuth credential validation

## [0.3.4] - 2026-01-24

### Changed

- Increase refurb timeout to prevent hook failures

### Documentation

- Fix broken mermaid gallery link

### Internal

- Add .skylos/ to gitignore and remove from tracking
- Remove cache files from git tracking

## [0.3.3] - 2026-01-22

### Changed

- Update config, core, deps, docs, tests

## [0.3.2] - 2026-01-08

### Changed

- Update config, core, deps

## [0.3.1] - 2026-01-05

### Changed

- Update config, core, deps

## [0.3.0] - 2026-01-04

### Changed

- Migrate to mcp-common v0.4.4 server module
- Opera-cloud-mcp (quality: 66/100) - 2026-01-04 02:43:52
- Update config, core, deps, tests

## [0.2.2] - 2025-12-20

### Changed

- Opera-cloud-mcp (quality: 58/100) - 2025-12-20 03:51:55
- Update config, core, deps, docs, tests

### Testing

- config: Update CHANGELOG, coverage, pyproject

## [0.2.1] - 2025-09-21

### Changed

- Opera-cloud-mcp (quality: 76/100) - 2025-09-21 02:12:38

### Fixed

- test: Update 82 files
