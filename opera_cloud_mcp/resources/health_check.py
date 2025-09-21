"""
Health check resources for OPERA Cloud MCP server.

Provides HTTP endpoints for monitoring and health checking
the MCP server and its dependencies.
"""

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

from opera_cloud_mcp.main import app, get_settings, oauth_handler

logger = logging.getLogger(__name__)


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


@app.resource("health://status/{component}")
async def health_status(component: str = "all"):
    """
    Health check resource that provides detailed status information.

    Returns:
        Dictionary containing health status and detailed checks
    """
    try:
        current_settings = get_settings()
        # Basic health checks
        checks = {
            "mcp_server": True,
            "configuration": bool(
                current_settings
                and current_settings.opera_client_id
                and current_settings.opera_client_secret
            ),
            "oauth_handler": oauth_handler is not None,
            "version": getattr(app, "version", "unknown"),
        }

        # Test authentication if OAuth handler is available
        checks["authentication"] = _check_authentication(oauth_handler)

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


@app.resource("health://ready/{component}")
async def readiness_check(component: str = "server"):
    """
    Readiness check resource that indicates if the service is ready to serve requests.

    Returns:
        Dictionary indicating readiness status
    """
    try:
        # Check if OAuth handler is initialized
        if oauth_handler is None:
            return {"status": "not_ready", "reason": "OAuth handler not initialized"}

        # Check if configuration is valid
        current_settings = get_settings()
        if not (
            current_settings
            and current_settings.opera_client_id
            and current_settings.opera_client_secret
        ):
            return {"status": "not_ready", "reason": "Missing required configuration"}

        # Check authentication status
        token_info = oauth_handler.get_token_info()
        if not token_info["has_token"] or token_info["status"] == "error":
            return {"status": "not_ready", "reason": "Authentication not available"}

        return {
            "status": "ready",
            "details": {
                "authentication": token_info["status"],
                "version": getattr(app, "version", "unknown"),
            },
        }

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not_ready", "error": str(e)}


@app.resource("health://live/{component}")
async def liveness_check(component: str = "server"):
    """
    Liveness check resource that indicates if the service is alive.

    Returns:
        Dictionary indicating liveness status
    """
    return {
        "status": "alive",
        "timestamp": asyncio.get_event_loop().time(),
        "version": getattr(app, "version", "unknown"),
    }


def register_health_resources(app: FastMCP):
    """
    Register all health check resources with the FastMCP app.

    Args:
        app: FastMCP application instance
    """
    # Resources are automatically registered via decorators
    logger.info("Health check resources registered")
