"""
Main entry point for the OPERA Cloud MCP server.

This module sets up the FastMCP server with all necessary tools and configuration
for interfacing with Oracle OPERA Cloud APIs.
"""

import asyncio
import json
import logging
import sys

from fastmcp import FastMCP

from opera_cloud_mcp.auth import create_oauth_handler
from opera_cloud_mcp.config.settings import Settings
from opera_cloud_mcp.tools.guest_tools import register_guest_tools
from opera_cloud_mcp.tools.reservation_tools import register_reservation_tools
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

# Global settings instance (initialized on first use)
settings = None

# Global OAuth handler (initialized on startup)
oauth_handler = None


def get_settings() -> Settings:
    """Get or initialize settings instance."""
    global settings
    if settings is None:
        settings = Settings()
    return settings


@app.tool()
async def health_check() -> dict[str, any]:
    """
    Perform a comprehensive health check of the MCP server and its dependencies.

    Returns:
        Dictionary containing health status information including authentication,
        performance metrics, and system resources
    """
    try:
        current_settings = get_settings()
        # Basic health checks
        checks = {
            "mcp_server": True,
            "configuration": bool(
                current_settings.opera_client_id
                and current_settings.opera_client_secret
            ),
            "oauth_handler": oauth_handler is not None,
            "version": app.version,
        }

        # Test authentication if OAuth handler is available
        if oauth_handler:
            try:
                token_info = oauth_handler.get_token_info()
                checks["authentication"] = {
                    "has_token": token_info["has_token"],
                    "status": token_info["status"],
                    "refresh_count": token_info["refresh_count"],
                    "expires_in": token_info.get("expires_in"),
                }

                # Test token validity if we have one
                if token_info["has_token"] and token_info["status"] in [
                    "valid",
                    "expiring_soon",
                ]:
                    checks["authentication"]["token_valid"] = True
                else:
                    checks["authentication"]["token_valid"] = False

            except Exception as e:
                logger.warning(f"Authentication health check failed: {e}")
                checks["authentication"] = {
                    "error": str(e),
                    "status": "error",
                }
        else:
            checks["authentication"] = {
                "status": "not_initialized",
            }

        # Add observability metrics if available
        try:
            from opera_cloud_mcp.utils.observability import get_observability

            observability = get_observability()
            checks["observability"] = observability.get_health_dashboard()
        except Exception as e:
            logger.debug(f"Observability not available: {e}")
            checks["observability"] = {"status": "not_initialized"}

        # Overall status
        has_errors = False
        if not checks["configuration"] or not checks["oauth_handler"]:
            has_errors = True
        if (
            isinstance(checks.get("authentication"), dict)
            and checks["authentication"].get("status") == "error"
        ):
            has_errors = True

        status = "unhealthy" if has_errors else "healthy"

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


@app.tool()
async def get_auth_status() -> dict[str, any]:
    """
    Get detailed authentication status and token information.

    Returns:
        Dictionary containing authentication status and token metadata
    """
    if not oauth_handler:
        return {
            "status": "not_initialized",
            "error": "OAuth handler not initialized",
        }

    try:
        current_settings = get_settings()
        token_info = oauth_handler.get_token_info()

        return {
            "status": "success",
            "data": {
                "oauth_client_id": current_settings.opera_client_id[:8] + "..."
                if current_settings.opera_client_id
                else None,
                "token_url": current_settings.opera_token_url,
                "persistent_cache_enabled": current_settings.enable_persistent_token_cache,
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
async def validate_auth_credentials() -> dict[str, any]:
    """
    Validate OAuth credentials by attempting to get a fresh token.

    Returns:
        Dictionary containing validation results
    """
    if not oauth_handler:
        return {
            "status": "error",
            "error": "OAuth handler not initialized",
        }

    try:
        logger.info("Validating OAuth credentials")
        is_valid = await oauth_handler.validate_credentials()

        if is_valid:
            token_info = oauth_handler.get_token_info()
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
        "opera_base_url": current_settings.opera_base_url,
        "opera_api_version": current_settings.opera_api_version,
        "opera_environment": current_settings.opera_environment,
    }


async def initialize_server() -> None:
    """Initialize server components."""
    global oauth_handler

    current_settings = get_settings()
    logger.info("Initializing OPERA Cloud MCP server...")
    logger.info("Version: 0.1.0")
    logger.info(f"Environment: {current_settings.opera_environment}")

    # Validate configuration
    missing_settings = current_settings.validate_required_settings()
    if missing_settings:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_settings)}"
        )
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

    logger.info("Configuration validated successfully")

    # Initialize OAuth handler
    try:
        oauth_handler = create_oauth_handler(settings)
        logger.info("OAuth handler initialized successfully")

        # Validate credentials on startup
        logger.info("Validating OAuth credentials...")
        is_valid = await oauth_handler.validate_credentials()

        if is_valid:
            logger.info("OAuth credentials validated successfully")
            token_info = oauth_handler.get_token_info()
            logger.info(
                "Authentication initialized",
                extra={
                    "token_status": token_info["status"],
                    "expires_in": token_info.get("expires_in"),
                    "persistent_cache": current_settings.enable_persistent_token_cache,
                },
            )
        else:
            logger.warning(
                "OAuth credential validation failed - server will start but authentication may fail"
            )

    except AuthenticationError as e:
        logger.error(f"Authentication initialization failed: {e}")
        logger.warning(
            "Server will start without valid authentication - operations may fail"
        )
        # Don't fail startup, but log the issue

    except Exception as e:
        logger.error(f"Unexpected error during OAuth initialization: {e}")
        raise

    # Register MCP tools
    logger.info("Registering MCP tools...")
    try:
        register_reservation_tools(app)
        logger.info("Reservation tools registered successfully")

        register_guest_tools(app)
        logger.info("Guest management tools registered successfully")

        # Register health check resources
        from opera_cloud_mcp.resources import register_health_resources

        register_health_resources(app)
        logger.info("Health check resources registered successfully")
    except Exception as e:
        logger.error(f"Failed to register tools: {e}")
        raise

    logger.info("Server initialization completed successfully")


async def main() -> None:
    """Main entry point for the MCP server."""
    try:
        # Setup logging first
        setup_logging(get_settings())

        # Initialize server components
        await initialize_server()

        # Run the FastMCP server
        logger.info("Starting FastMCP server...")
        await app.run()

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")

        # Cleanup on shutdown
        if oauth_handler and hasattr(oauth_handler, "persistent_cache"):
            logger.info("Performing cleanup...")

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
