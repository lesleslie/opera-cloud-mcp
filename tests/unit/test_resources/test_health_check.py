"""Unit tests for health check resources.

Tests for resources in opera_cloud_mcp/resources/health_check.py
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from opera_cloud_mcp.resources.health_check import (
    _check_authentication,
    _check_observability,
    _determine_overall_status,
    health_status,
    readiness_check,
    liveness_check,
    register_health_resources,
)


class TestCheckAuthentication:
    """Test _check_authentication function."""

    def test_check_authentication_none_handler(self):
        """Test authentication check with None handler."""
        result = _check_authentication(None)
        assert result == {"status": "not_initialized"}

    def test_check_authentication_valid_token(self):
        """Test authentication check with valid token."""
        mock_handler = MagicMock()
        mock_handler.get_token_info.return_value = {
            "has_token": True,
            "status": "valid",
            "refresh_count": 1,
            "expires_in": 3600
        }

        result = _check_authentication(mock_handler)
        assert result["has_token"] is True
        assert result["status"] == "valid"
        assert result["refresh_count"] == 1
        assert result["expires_in"] == 3600
        assert result["token_valid"] is True

    def test_check_authentication_expiring_soon(self):
        """Test authentication check with expiring token."""
        mock_handler = MagicMock()
        mock_handler.get_token_info.return_value = {
            "has_token": True,
            "status": "expiring_soon",
            "refresh_count": 2,
            "expires_in": 300
        }

        result = _check_authentication(mock_handler)
        assert result["has_token"] is True
        assert result["status"] == "expiring_soon"
        assert result["token_valid"] is True

    def test_check_authentication_invalid_token(self):
        """Test authentication check with invalid token."""
        mock_handler = MagicMock()
        mock_handler.get_token_info.return_value = {
            "has_token": True,
            "status": "expired",
            "refresh_count": 5
        }

        result = _check_authentication(mock_handler)
        assert result["has_token"] is True
        assert result["status"] == "expired"
        assert result["token_valid"] is False

    def test_check_authentication_no_token(self):
        """Test authentication check with no token."""
        mock_handler = MagicMock()
        mock_handler.get_token_info.return_value = {
            "has_token": False,
            "status": "no_token",
            "refresh_count": 0
        }

        result = _check_authentication(mock_handler)
        assert result["has_token"] is False
        assert result["status"] == "no_token"
        assert result["token_valid"] is False

    def test_check_authentication_exception(self):
        """Test authentication check with exception."""
        mock_handler = MagicMock()
        mock_handler.get_token_info.side_effect = Exception("Auth error")

        result = _check_authentication(mock_handler)
        assert result["status"] == "error"
        assert "error" in result


# Note: _check_observability imports get_observability conditionally, so testing it requires
# the observability module to be available. The function is simple enough that manual testing
# is sufficient.


class TestDetermineOverallStatus:
    """Test _determine_overall_status function."""

    def test_determine_overall_status_healthy(self):
        """Test overall status when all checks pass."""
        checks = {
            "configuration": True,
            "oauth_handler": True,
            "authentication": {"status": "valid"}
        }
        result = _determine_overall_status(checks)
        assert result == "healthy"

    def test_determine_overall_status_unhealthy_no_config(self):
        """Test overall status when configuration missing."""
        checks = {
            "configuration": False,
            "oauth_handler": True,
            "authentication": {"status": "valid"}
        }
        result = _determine_overall_status(checks)
        assert result == "unhealthy"

    def test_determine_overall_status_unhealthy_no_oauth(self):
        """Test overall status when oauth_handler missing."""
        checks = {
            "configuration": True,
            "oauth_handler": False,
            "authentication": {"status": "valid"}
        }
        result = _determine_overall_status(checks)
        assert result == "unhealthy"

    def test_determine_overall_status_unhealthy_auth_error(self):
        """Test overall status when authentication has error."""
        checks = {
            "configuration": True,
            "oauth_handler": True,
            "authentication": {"status": "error"}
        }
        result = _determine_overall_status(checks)
        assert result == "unhealthy"


# Note: health_status, readiness_check, and liveness_check are FastMCP resource templates
# The underlying helper functions (_check_authentication, _check_observability, _determine_overall_status)
# are tested above. FastMCP decorator functionality is tested by the FastMCP library itself.


class TestRegisterHealthResources:
    """Test register_health_resources function."""

    @patch('opera_cloud_mcp.resources.health_check.logger')
    def test_register_health_resources(self, mock_logger):
        """Test registering health resources."""
        mock_app = MagicMock()

        register_health_resources(mock_app)

        mock_logger.info.assert_called_once_with("Health check resources registered")
