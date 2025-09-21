#!/usr/bin/env python3
"""OPERA Cloud MCP Server - Module Entry Point.

Allows running the server as: python -m opera_cloud_mcp
"""

import typer

from opera_cloud_mcp.cli import main

if __name__ == "__main__":
    typer.run(main)
