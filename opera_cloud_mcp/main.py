"""
Main entry point for the OPERA Cloud MCP server.

This module sets up the FastMCP server with all necessary tools and configuration
for interfacing with Oracle OPERA Cloud APIs.
"""

import asyncio
import json
import logging
import sys
import tempfile
from dataclasses import dataclass
from typing import Any

from fastmcp import FastMCP

from opera_cloud_mcp.auth import create_oauth_handler
from opera_cloud_mcp.config.settings import Settings
from opera_cloud_mcp.server import (
    RATE_LIMITING_AVAILABLE,
    SECURITY_AVAILABLE,
    SERVERPANELS_AVAILABLE,
)
from opera_cloud_mcp.utils.exceptions import (
    AuthenticationError,
    ConfigurationError,
)


def setup_logging(settings: Settings) -> None:
    """Setup logging configuration."""
    if settings.enable_structured_logging:
        # Structured JSON logging
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                # Add extra fields if present
                if hasattr(record, "extra"):
                    log_entry.update(record.extra)

                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)

                return json.dumps(log_entry)

        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logging.root.handlers = [handler]
    else:
        # Standard logging
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format=settings.log_format,
        )

    logging.getLogger().setLevel(getattr(logging, settings.log_level.upper()))

    # Initialize observability
    try:
        from opera_cloud_mcp.utils.observability import initialize_observability

        initialize_observability(
            service_name="opera-cloud-mcp",
            hotel_id=settings.default_hotel_id,
            enable_console_logging=True,
            log_file_path=None,  # Use default
        )
        logger.info("Observability system initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize observability system: {e}")


logger = logging.getLogger(__name__)

# Initialize FastMCP app
app = FastMCP(
    name="opera-cloud-mcp",
    version="0.1.0",
)
app.description = "MCP server for Oracle OPERA Cloud API integration"


@dataclass(frozen=True)
class ResourceDescriptor:
    """Simple resource descriptor for documentation-style responses."""

    uri: str
    name: str
    description: str
    mimeType: str
    text: str


# Global settings instance (initialized on first use)
settings = None

# Global OAuth handler (initialized on startup)
oauth_handler = None
auth_handler = None


def _current_auth_handler():
    """Return the active authentication handler, if any."""
    return auth_handler if auth_handler is not None else oauth_handler


def get_settings() -> Settings | None:
    """Get or initialize settings instance."""
    global settings
    if settings is None:
        # Try to create settings with default values
        try:
            # These are intentionally non-sensitive test values
            test_client_id = "test_client_id"  # noqa: S105 - Test credential, not a real secret
            test_client_secret = "test_client_secret"  # noqa: S105 - Test credential, not a real secret

            settings = Settings(
                opera_client_id=test_client_id,
                opera_client_secret=test_client_secret,
                opera_token_url="https://test-api.oracle-hospitality.com/oauth/v1/tokens",  # noqa: S106 - Test URL, not a password
                opera_base_url="https://test-api.oracle-hospitality.com",
                opera_api_version="v1",
                opera_environment="testing",
                default_hotel_id="TEST001",
                request_timeout=30,
                max_retries=3,
                retry_backoff=1.0,
                enable_cache=True,
                cache_ttl=300,
                cache_max_memory=10000,
                oauth_max_retries=3,
                oauth_retry_backoff=1.0,
                enable_persistent_token_cache=False,
                token_cache_dir=tempfile.gettempdir(),  # noqa: S108 - Temporary directory for testing
                log_level="INFO",
                log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                enable_structured_logging=True,
            )
        except Exception:
            # If we can't create settings, return None
            settings = None
    return settings


def _check_authentication(oauth_handler) -> dict[str, Any]:
    """Check authentication status."""
    if not oauth_handler:
        return {
            "status": "not_initialized",
        }

    try:
        token_info = oauth_handler.get_token_info()
        auth_check = {
            "has_token": token_info["has_token"],
            "status": token_info["status"],
            "refresh_count": token_info["refresh_count"],
            "expires_in": token_info.get("expires_in"),
        }

        # Test token validity if we have one
        if token_info["has_token"] and token_info["status"] in (
            "valid",
            "expiring_soon",
        ):
            auth_check["token_valid"] = True
        else:
            auth_check["token_valid"] = False

        return auth_check

    except Exception as e:
        logger.warning(f"Authentication health check failed: {e}")
        return {
            "error": str(e),
            "status": "error",
        }


def _check_observability() -> dict[str, Any]:
    """Check observability status."""
    try:
        from opera_cloud_mcp.utils.observability import get_observability

        observability = get_observability()
        return observability.get_health_dashboard()
    except Exception as e:
        logger.debug(f"Observability not available: {e}")
        return {"status": "not_initialized"}


def _determine_overall_status(checks: dict[str, Any]) -> str:
    """Determine overall health status."""
    has_errors = False
    if not checks["configuration"] or not checks["oauth_handler"]:
        has_errors = True
    if (
        isinstance(checks.get("authentication"), dict)
        and checks["authentication"].get("status") == "error"
    ):
        has_errors = True

    return "unhealthy" if has_errors else "healthy"


def health_check() -> dict[str, Any]:
    """
    Perform a comprehensive health check of the MCP server and its dependencies.

    Returns:
        Dictionary containing health status information including authentication,
        performance metrics, and system resources
    """
    try:
        current_settings = get_settings()
        handler = _current_auth_handler()
        # Basic health checks
        checks: dict[str, Any] = {
            "mcp_server": True,
            "configuration": bool(
                current_settings
                and current_settings.opera_client_id
                and current_settings.opera_client_secret
            ),
            "oauth_handler": handler is not None,
            "version": app.version,
        }

        # Test authentication if OAuth handler is available
        checks["authentication"] = _check_authentication(handler)

        # Add observability metrics if available
        checks["observability"] = _check_observability()

        # Overall status
        status = _determine_overall_status(checks)

        return {
            "status": status,
            "checks": checks,
            "timestamp": asyncio.get_event_loop().time(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time(),
        }


async def api_documentation() -> ResourceDescriptor:
    """Return documentation resource metadata and contents."""
    text = "\n".join(
        [
            "# OPERA Cloud API Documentation",
            "",
            "## Authentication",
            "OAuth2 client credentials are required for all API requests.",
            "",
            "## Reservations",
            "Reservation search, create, modify, and cancel workflows.",
            "",
            "## Front Office",
            "Check-in, check-out, room assignment, and reporting operations.",
        ]
    )
    return ResourceDescriptor(
        uri="opera://api/docs",
        name="OPERA Cloud API Documentation",
        description="Comprehensive documentation for OPERA Cloud REST APIs.",
        mimeType="text/markdown",
        text=text,
    )


async def hotel_configuration() -> ResourceDescriptor:
    """Return hotel configuration resource metadata and contents."""
    current_settings = get_settings()
    config = {
        "default_hotel_id": current_settings.default_hotel_id
        if current_settings
        else None,
        "api_environment": current_settings.opera_environment
        if current_settings
        else None,
        "api_version": current_settings.opera_api_version if current_settings else None,
        "cache_enabled": "true"
        if current_settings and current_settings.enable_cache
        else "false",
        "cache_ttl": current_settings.cache_ttl if current_settings else None,
    }
    return ResourceDescriptor(
        uri="opera://config/hotel",
        name="Hotel Configuration",
        description="Current hotel configuration settings for the MCP server.",
        mimeType="application/json",
        text=json.dumps(config),
    )


def get_auth_handler():
    """Return the active OAuth handler or raise if unavailable."""
    handler = _current_auth_handler()
    if handler is None:
        raise RuntimeError("Authentication handler not initialized")
    return handler


@app.tool()
async def get_auth_status() -> dict[str, Any]:
    """
    Get detailed authentication status and token information.

    Returns:
        Dictionary containing authentication status and token metadata
    """
    handler = _current_auth_handler()
    if not handler:
        return {
            "status": "not_initialized",
            "error": "OAuth handler not initialized",
        }

    try:
        current_settings = get_settings()
        if current_settings is None:
            return {
                "status": "error",
                "error": "Settings not initialized",
            }

        token_info = handler.get_token_info()

        return {
            "status": "success",
            "data": {
                "oauth_client_id": current_settings.opera_client_id[:8] + "..."
                if current_settings.opera_client_id
                else None,
                "token_url": current_settings.opera_token_url,
                "persistent_cache_enabled": (
                    current_settings.enable_persistent_token_cache
                ),
                "token_info": token_info,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get auth status: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@app.tool()
async def validate_auth_credentials() -> dict[str, Any]:
    """
    Validate OAuth credentials by attempting to get a fresh token.

    Returns:
        Dictionary containing validation results
    """
    handler = _current_auth_handler()
    if not handler:
        return {
            "status": "error",
            "error": "OAuth handler not initialized",
        }

    try:
        logger.info("Validating OAuth credentials")
        is_valid = await handler.validate_credentials()

        if is_valid:
            token_info = handler.get_token_info()
            return {
                "status": "success",
                "valid": True,
                "message": "OAuth credentials are valid",
                "token_info": token_info,
            }
        else:
            return {
                "status": "success",
                "valid": False,
                "message": "OAuth credentials are invalid",
            }

    except Exception as e:
        logger.error(f"Credential validation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@app.tool()
async def get_server_info() -> dict[str, str]:
    """
    Get server information and configuration details.

    Returns:
        Dictionary containing server information
    """
    current_settings = get_settings()
    return {
        "name": app.name,
        "version": "0.1.0",
        "description": "MCP server for Oracle OPERA Cloud API integration",
        "opera_base_url": current_settings.opera_base_url if current_settings else "",
        "opera_api_version": current_settings.opera_api_version
        if current_settings
        else "",
        "opera_environment": current_settings.opera_environment
        if current_settings
        else "",
    }


async def initialize_server() -> None:
    """Initialize server components."""
    global oauth_handler, auth_handler

    current_settings = get_settings()
    if current_settings is None:
        logger.error("Failed to initialize settings")
        return

    # Validate OAuth credentials at startup (Phase 3 Security Hardening)
    # Phase 3.2 H2 fix: Remove suppress wrapper to ensure validation failures
    # are visible
    current_settings.validate_oauth_credentials_at_startup()

    # Create OAuth handler
    oauth_handler = create_oauth_handler(current_settings)
    auth_handler = oauth_handler


def _build_startup_features() -> list[str]:
    """Build the list of startup features to display."""
    features = [
        "🏨 Hospitality Management",
        "🔐 OAuth2 Authentication",
        "💰 Financial Operations",
        "🛏️  Room Management",
    ]
    if SECURITY_AVAILABLE:
        features.append("🔒 OAuth Credential Validation (32+ chars)")
    if RATE_LIMITING_AVAILABLE:
        features.append("⚡ Rate Limiting (10 req/sec, burst 20)")
    return features


def _display_startup_message() -> None:
    """Display the startup message using ServerPanels or fallback."""
    if SERVERPANELS_AVAILABLE:
        features = _build_startup_features()
        from mcp_common.ui import ServerPanels

        ServerPanels.startup_success(
            server_name="OPERA Cloud MCP",
            version="0.1.0",
            features=features,
            transport="STDIO",
            mode="Claude Desktop",
        )
    else:
        # Fallback to plain text
        logger.info("Starting FastMCP server...")


def _perform_shutdown_cleanup() -> None:
    """Perform cleanup during shutdown."""
    handler = _current_auth_handler()
    if handler and hasattr(handler, "persistent_cache"):
        logger.info("Performing cleanup...")


async def main() -> None:
    """Main entry point for the MCP server."""
    try:
        # Setup logging first
        settings = get_settings()
        if settings is not None:
            setup_logging(settings)

        # Initialize server components
        await initialize_server()

        # Display startup message
        _display_startup_message()

        # Run the FastMCP server
        await app.run()  # type: ignore[func-returns-value]

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        _perform_shutdown_cleanup()

    except (ConfigurationError, AuthenticationError) as e:
        logger.error(f"Server startup failed: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected server error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
