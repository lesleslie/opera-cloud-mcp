"""
MCP Resources for OPERA Cloud API.

This module contains resource definitions that provide documentation
and specifications for the OPERA Cloud APIs.
"""

from .health_check import register_health_resources

__all__ = [
    "register_health_resources",
]
