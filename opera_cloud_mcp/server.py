"""
OPERA Cloud MCP Server

FastMCP-based Model Context Protocol server for Oracle OPERA Cloud API integration.
Provides AI agents with comprehensive access to hospitality management functions.
"""

import asyncio
import importlib.util
import logging

from fastmcp import FastMCP

from opera_cloud_mcp.tools.financial_tools import register_financial_tools
from opera_cloud_mcp.tools.guest_tools import register_guest_tools
from opera_cloud_mcp.tools.operation_tools import register_operation_tools
from opera_cloud_mcp.tools.reservation_tools import register_reservation_tools
from opera_cloud_mcp.tools.room_tools import register_room_tools

# Check FastMCP rate limiting middleware availability (Phase 3.3 M2: improved pattern)
RATE_LIMITING_AVAILABLE = (
    importlib.util.find_spec("fastmcp.server.middleware.rate_limiting") is not None
)

# Check ServerPanels availability (Phase 3.3 M2: improved pattern)
SERVERPANELS_AVAILABLE = importlib.util.find_spec("mcp_common.ui") is not None

# Import security availability flag (Phase 3 Security Hardening)
SECURITY_AVAILABLE = importlib.util.find_spec("mcp_common.security") is not None

logger = logging.getLogger(__name__)

# Initialize FastMCP app
app = FastMCP("opera-cloud-mcp")

# Add rate limiting middleware (Phase 3 Security Hardening)
if RATE_LIMITING_AVAILABLE:
    from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

    rate_limiter = RateLimitingMiddleware(
        max_requests_per_second=10.0,  # Sustainable rate for hospitality API
        burst_capacity=20,  # Allow brief bursts
        global_limit=True,  # Protect the OPERA Cloud API globally
    )
    app.add_middleware(rate_limiter)
    logger.info("Rate limiting enabled: 10 req/sec, burst 20")

# Register all MCP tools
register_reservation_tools(app)
register_guest_tools(app)
register_room_tools(app)
register_operation_tools(app)
register_financial_tools(app)

# Export ASGI app for uvicorn (standardized startup pattern)
http_app = app.http_app


def main() -> None:
    """Main entry point for running the server."""
    asyncio.run(app.run())  # type: ignore[func-returns-value]


if __name__ == "__main__":
    main()
