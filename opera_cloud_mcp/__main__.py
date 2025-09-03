#!/usr/bin/env python3
"""OPERA Cloud MCP Server - Module Entry Point.

Allows running the server as: python -m opera_cloud_mcp
"""

import argparse


def main() -> None:
    """Main entry point for the OPERA Cloud MCP server."""
    parser = argparse.ArgumentParser(
        description="OPERA Cloud MCP Server",
        prog="opera-cloud-mcp",
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information",
    )

    args = parser.parse_args()

    if args.version:
        print("OPERA Cloud MCP Server v0.1.0")
        return

    # Import and run the server
    from .server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
