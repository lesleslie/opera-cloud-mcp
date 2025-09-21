"""
Test configuration and global fixtures.

This module provides test configuration and fixtures used across all test files.
"""

import sys
from unittest.mock import Mock, patch

import pytest


# Mock the audit logger at import time to prevent encryption issues
@pytest.fixture(autouse=True, scope="session")
def mock_global_audit_logger():
    """Mock the global audit logger for all tests."""
    mock_logger = Mock()
    mock_logger.log_authentication_event.return_value = True
    mock_logger.get_audit_trail.return_value = []
    mock_logger.get_security_report.return_value = {}

    with (
        patch("opera_cloud_mcp.auth.audit_logger.audit_logger", mock_logger),
        patch("opera_cloud_mcp.auth.audit_logger.AuditLogger") as mock_class,
    ):
        mock_class.return_value = mock_logger
        yield mock_logger


# Ensure clean test environment
@pytest.fixture(autouse=True)
def clean_test_environment():
    """Ensure clean test environment for each test."""
    # Clear any cached modules that might interfere with testing
    modules_to_clear = [
        mod
        for mod in sys.modules
        if mod.startswith("opera_cloud_mcp.auth") and "audit" in mod
    ]
    for mod in modules_to_clear:
        if hasattr(sys.modules[mod], "_cached_instances"):
            sys.modules[mod]._cached_instances = {}

    yield

    # Cleanup after test
    for mod in modules_to_clear:
        if hasattr(sys.modules[mod], "_cached_instances"):
            sys.modules[mod]._cached_instances = {}
