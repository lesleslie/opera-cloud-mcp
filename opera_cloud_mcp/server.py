"""
from __future__ import annotations
OPERA Cloud MCP Server

FastMCP-based Model Context Protocol server for Oracle OPERA Cloud API integration.
Provides AI agents with comprehensive access to hospitality management functions.
"""

import importlib.util
import logging
from typing import Any

from mcp_common.fastmcp import FastMCP
from mcp_common.health import register_http_health_route
from mcp_common.tools.dispatch import apply_tool_profile

from opera_cloud_mcp import __version__
from opera_cloud_mcp.tools.profiles import (
    PROFILE_REGISTRATIONS,
    REGISTRATION_MAP,
    register_all_tool_groups,
)

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


# HTTP health endpoint for Claude Code compatibility
register_http_health_route(
    app,
    service_name="opera-cloud",
    version=__version__,
)


@app.custom_route("/healthz", methods=["GET"])
async def healthz_check(request: Any) -> Any:
    """Kubernetes-style health check endpoint."""
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok"})


# Add rate limiting middleware (Phase 3 Security Hardening)
if RATE_LIMITING_AVAILABLE:
    from mcp_common.fastmcp import RateLimitingMiddleware

    rate_limiter = RateLimitingMiddleware(
        max_requests_per_second=10.0,  # Sustainable rate for hospitality API
        burst_capacity=20,  # Allow brief bursts
        global_limit=True,  # Protect the OPERA Cloud API globally
    )
    app.add_middleware(rate_limiter)
    logger.info("Rate limiting enabled: 10 req/sec, burst 20")

# Apply the tool profile (reads OPERA_CLOUD_TOOL_PROFILE env var).
#
# This replaces the previous direct register_*_tools(app) calls. The W0
# helper from mcp-common 0.18.0+ dispatches by group name and always
# registers the `discover_tools` meta-tool. The default (no env var)
# remains FULL = all 52 unique tool names (53 decorators, but
# check_room_availability is registered in two modules and FastMCP
# dedups to 1) — the previous behavior is preserved.
#
# The sync ``apply_tool_profile`` wrapper from mcp-common handles the
# no-running-loop case via ``asyncio.run``; it raises ``RuntimeError``
# when called from within a running event loop (forcing async callers
# to use ``_apply_tool_profile_async`` instead). At module import time
# of server.py no event loop is running, so this works in normal CLI
# / HTTP-server startup paths.
apply_tool_profile(
    app,
    profile_env_var="OPERA_CLOUD_TOOL_PROFILE",
    registrations=PROFILE_REGISTRATIONS,
    registration_map=REGISTRATION_MAP,
    register_all_fn=register_all_tool_groups,
)

http_app = app.http_app


def main() -> None:
    """Main entry point for running the server."""
    app.run()


if __name__ == "__main__":
    main()
