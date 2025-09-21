"""
OPERA Cloud MCP Server

FastMCP-based Model Context Protocol server for Oracle OPERA Cloud API integration.
Provides AI agents with comprehensive access to hospitality management functions.
"""

import asyncio

from fastmcp import FastMCP

from opera_cloud_mcp.tools.financial_tools import register_financial_tools
from opera_cloud_mcp.tools.guest_tools import register_guest_tools
from opera_cloud_mcp.tools.operation_tools import register_operation_tools
from opera_cloud_mcp.tools.reservation_tools import register_reservation_tools
from opera_cloud_mcp.tools.room_tools import register_room_tools

# Initialize FastMCP app
app = FastMCP("opera-cloud-mcp")

# Register all MCP tools
register_reservation_tools(app)
register_guest_tools(app)
register_room_tools(app)
register_operation_tools(app)
register_financial_tools(app)


def main() -> None:
    """Main entry point for running the server."""
    asyncio.run(app.run())  # type: ignore[func-returns-value]


if __name__ == "__main__":
    main()
