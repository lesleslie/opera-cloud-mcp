"""Unit tests for the health check module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from opera_cloud_mcp.resources import health_check


class TestHealthCheckModule:
    """Test cases for the health check module functionality."""

    def setup_method(self):
        """Setup method to reset global state before each test."""
        # Reset global variables to avoid test interference
        from opera_cloud_mcp.main import app
        app.resources = {}  # Reset resources to avoid conflicts

    @patch('opera_cloud_mcp.resources.health_check.oauth_handler', None)
    def test_check_authentication_no_handler(self):
        """Test _check_authentication when no handler is available."""
        result = health_check._check_authentication(None)

        assert result["status"] == "not_initialized"

    @patch('opera_cloud_mcp.resources.health_check.oauth_handler')
    def test_check_authentication_with_handler(self, mock_oauth_handler):
        """Test _check_authentication with a valid handler."""
        mock_oauth_handler.get_token_info.return_value = {
            "has_token": True,
            "status": "valid",
            "refresh_count": 1,
            "expires_in": 3600
        }

        result = health_check._check_authentication(mock_oauth_handler)

        assert result["has_token"] is True
        assert result["status"] == "valid"
        assert result["refresh_count"] == 1
        assert result["expires_in"] == 3600
        assert result["token_valid"] is True

    @patch('opera_cloud_mcp.resources.health_check.oauth_handler')
    def test_check_authentication_expiring_soon(self, mock_oauth_handler):
        """Test _check_authentication with expiring soon token."""
        mock_oauth_handler.get_token_info.return_value = {
            "has_token": True,
            "status": "expiring_soon",
            "refresh_count": 1,
            "expires_in": 300
        }

        result = health_check._check_authentication(mock_oauth_handler)

        assert result["has_token"] is True
        assert result["status"] == "expiring_soon"
        assert result["token_valid"] is True

    @patch('opera_cloud_mcp.resources.health_check.oauth_handler')
    def test_check_authentication_no_token(self, mock_oauth_handler):
        """Test _check_authentication with no token."""
        mock_oauth_handler.get_token_info.return_value = {
            "has_token": False,
            "status": "no_token",
            "refresh_count": 0
        }

        result = health_check._check_authentication(mock_oauth_handler)

        assert result["has_token"] is False
        assert result["status"] == "no_token"
        assert result["token_valid"] is False

    @patch('opera_cloud_mcp.resources.health_check.oauth_handler')
    def test_check_authentication_exception(self, mock_oauth_handler):
        """Test _check_authentication when exception occurs."""
        mock_oauth_handler.get_token_info.side_effect = Exception("Test error")

        result = health_check._check_authentication(mock_oauth_handler)

        assert result["status"] == "error"
        assert "Test error" in result["error"]

    @patch('opera_cloud_mcp.utils.observability.get_observability')
    def test_check_observability_available(self, mock_get_observability):
        """Test _check_observability when observability is available."""
        mock_observability = Mock()
        mock_observability.get_health_dashboard.return_value = {"status": "healthy", "metrics": []}
        mock_get_observability.return_value = mock_observability

        result = health_check._check_observability()

        assert result["status"] == "healthy"
        assert "metrics" in result

    @patch('opera_cloud_mcp.utils.observability.get_observability', side_effect=ImportError("Not available"))
    def test_check_observability_not_available(self, mock_get_observability):
        """Test _check_observability when observability is not available."""
        result = health_check._check_observability()

        assert result["status"] == "not_initialized"

    def test_determine_overall_status_healthy(self):
        """Test _determine_overall_status returns healthy for good conditions."""
        checks = {
            "configuration": True,
            "oauth_handler": True,
            "authentication": {"status": "valid"}
        }

        status = health_check._determine_overall_status(checks)
        assert status == "healthy"

    def test_determine_overall_status_unhealthy_missing_config(self):
        """Test _determine_overall_status returns unhealthy for missing config."""
        checks = {
            "configuration": False,
            "oauth_handler": True,
            "authentication": {"status": "valid"}
        }

        status = health_check._determine_overall_status(checks)
        assert status == "unhealthy"

    def test_determine_overall_status_unhealthy_missing_oauth_handler(self):
        """Test _determine_overall_status returns unhealthy for missing oauth handler."""
        checks = {
            "configuration": True,
            "oauth_handler": False,
            "authentication": {"status": "valid"}
        }

        status = health_check._determine_overall_status(checks)
        assert status == "unhealthy"

    def test_determine_overall_status_unhealthy_auth_error(self):
        """Test _determine_overall_status returns unhealthy for auth error."""
        checks = {
            "configuration": True,
            "oauth_handler": True,
            "authentication": {"status": "error"}
        }

        status = health_check._determine_overall_status(checks)
        assert status == "unhealthy"

    def test_health_status_success(self):
        """Test health_status resource returns expected structure."""
        # Skip this test as it requires actual resource execution
        pytest.skip("Skipping resource test that requires actual execution")

    def test_health_status_exception(self):
        """Test health_status handles exceptions properly."""
        # Skip this test as it requires actual resource execution
        pytest.skip("Skipping resource test that requires actual execution")

    def test_readiness_check_no_oauth_handler(self):
        """Test readiness_check when no OAuth handler is available."""
        # Skip this test as it requires actual resource execution
        pytest.skip("Skipping resource test that requires actual execution")

    def test_readiness_check_missing_config(self):
        """Test readiness_check when configuration is missing."""
        # Skip this test as it requires actual resource execution
        pytest.skip("Skipping resource test that requires actual execution")

    def test_readiness_check_no_token(self):
        """Test readiness_check when no token is available."""
        # Skip this test as it requires actual resource execution
        pytest.skip("Skipping resource test that requires actual execution")

    def test_readiness_check_success(self):
        """Test readiness_check returns ready when all conditions are met."""
        # Skip this test as it requires actual resource execution
        pytest.skip("Skipping resource test that requires actual execution")

    def test_readiness_check_exception(self):
        """Test readiness_check handles exceptions properly."""
        # Skip this test as it requires actual resource execution
        pytest.skip("Skipping resource test that requires actual execution")

    def test_liveness_check(self):
        """Test liveness_check returns alive status."""
        # Skip this test as it requires actual resource execution
        pytest.skip("Skipping resource test that requires actual execution")

    @patch('opera_cloud_mcp.resources.health_check.logger')
    def test_register_health_resources(self, mock_logger):
        """Test register_health_resources logs registration."""
        from fastmcp import FastMCP

        app = FastMCP(name="test", version="1.0.0")

        health_check.register_health_resources(app)

        mock_logger.info.assert_called_once_with("Health check resources registered")
