"""
OPERA Cloud MCP Server.

A FastMCP-based Model Context Protocol server for Oracle OPERA Cloud APIs,
providing AI agents with seamless access to hospitality management functions.
"""

__version__ = "0.1.0"
__author__ = "Opera Cloud MCP Team"
__description__ = "MCP Server for the Opera Cloud API"

# Import main components for easy access
from opera_cloud_mcp.config.settings import Settings

__all__ = [
    "__version__",
    "__author__",
    "__description__",
    "Settings",
]
