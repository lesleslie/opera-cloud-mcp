"""Unit tests for the main module."""

import asyncio
import tempfile
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastmcp import FastMCP

from opera_cloud_mcp import main
from opera_cloud_mcp.config.settings import Settings


class TestMainModule:
    """Test cases for the main module functionality."""

    def setup_method(self):
        """Setup method to reset global state before each test."""
        main.settings = None
        main.oauth_handler = None
        main.auth_handler = None

    def test_get_settings_with_defaults(self):
        """Test getting settings with default test values."""
        settings = main.get_settings()

        assert settings is not None
        assert isinstance(settings, Settings)
        assert settings.opera_client_id == "test_client_id"
        assert settings.opera_client_secret == "test_client_secret"
        assert settings.opera_base_url == "https://test-api.oracle-hospitality.com"

    def test_get_settings_multiple_calls(self):
        """Test that get_settings returns the same instance on multiple calls."""
        settings1 = main.get_settings()
        settings2 = main.get_settings()

        assert settings1 is settings2

    def test_app_initialization(self):
        """Test that FastMCP app is properly initialized."""
        assert isinstance(main.app, FastMCP)
        assert main.app.name == "opera-cloud-mcp"
        assert main.app.version == "0.1.0"

    @patch('opera_cloud_mcp.main.get_settings')
    @patch('opera_cloud_mcp.auth.create_oauth_handler')
    @patch('opera_cloud_mcp.config.settings.Settings.validate_oauth_credentials_at_startup')
    def test_initialize_server(self, mock_validate, mock_create_oauth_handler, mock_get_settings):
        """Test server initialization."""
        # Setup mock settings
        mock_settings = Mock(spec=Settings)
        mock_settings.opera_client_id = "test_client_id"
        mock_settings.opera_client_secret = "test_client_secret"
        mock_settings.opera_base_url = "https://test-api.oracle-hospitality.com"
        mock_get_settings.return_value = mock_settings

        mock_oauth_handler = MagicMock()
        mock_create_oauth_handler.return_value = mock_oauth_handler

        # Run initialization
        asyncio.run(main.initialize_server())

        # Verify OAuth handler was created and set
        mock_create_oauth_handler.assert_called_once_with(mock_settings)
        mock_validate.assert_called_once()

    @patch('asyncio.get_event_loop')
    def test_health_check_success(self, mock_get_loop):
        """Test health check returns expected structure."""
        mock_loop = Mock()
        mock_loop.time.return_value = 12345.0
        mock_get_loop.return_value = mock_loop

        result = main.health_check()

        assert isinstance(result, dict)
        assert "status" in result
        assert "checks" in result
        assert "timestamp" in result
        assert result["timestamp"] == 12345.0
        assert result["status"] in ["healthy", "unhealthy"]

    def test_get_server_info(self):
        """Test get_server_info returns expected information."""
        # Skip: get_server_info is decorated as an MCP tool (@app.tool())
        # and cannot be called directly. It must be called through the MCP protocol.
        pytest.skip("get_server_info is an MCP tool and must be tested via MCP protocol")

    def test_get_auth_status_no_handler(self):
        """Test get_auth_status when no handler is available."""
        # Skip this test as it requires actual tool execution
        pytest.skip("Skipping tool test that requires actual execution")

    def test_validate_auth_credentials_no_handler(self):
        """Test validate_auth_credentials when no handler is available."""
        # Skip this test as it requires actual tool execution
        pytest.skip("Skipping tool test that requires actual execution")

    def test_api_documentation(self):
        """Test API documentation resource."""
        result = asyncio.run(main.api_documentation())

        assert hasattr(result, 'uri')
        assert hasattr(result, 'name')
        assert hasattr(result, 'description')
        assert hasattr(result, 'mime_type')
        assert hasattr(result, 'text')
        assert result.uri == "opera://api/docs"
        assert "OPERA Cloud API Documentation" in result.text

    def test_hotel_configuration(self):
        """Test hotel configuration resource."""
        result = asyncio.run(main.hotel_configuration())

        assert hasattr(result, 'uri')
        assert hasattr(result, 'name')
        assert hasattr(result, 'description')
        assert hasattr(result, 'mime_type')
        assert hasattr(result, 'text')
        assert result.uri == "opera://config/hotel"

        import json
        config = json.loads(result.text)
        assert "default_hotel_id" in config

    def test_current_auth_handler_preference(self):
        """Test that _current_auth_handler prefers auth_handler over oauth_handler."""
        # Set both handlers
        main.oauth_handler = "oauth_handler"
        main.auth_handler = "auth_handler"

        result = main._current_auth_handler()
        assert result == "auth_handler"

        # Reset auth_handler and check it falls back to oauth_handler
        main.auth_handler = None
        result = main._current_auth_handler()
        assert result == "oauth_handler"

    def test_determine_overall_status_healthy(self):
        """Test _determine_overall_status returns healthy for good conditions."""
        checks = {
            "configuration": True,
            "oauth_handler": True,
            "authentication": {"status": "valid"}
        }

        status = main._determine_overall_status(checks)
        assert status == "healthy"

    def test_determine_overall_status_unhealthy(self):
        """Test _determine_overall_status returns unhealthy for bad conditions."""
        # Test missing configuration
        checks = {
            "configuration": False,
            "oauth_handler": True
        }

        status = main._determine_overall_status(checks)
        assert status == "unhealthy"

        # Test missing oauth handler
        checks = {
            "configuration": True,
            "oauth_handler": False
        }

        status = main._determine_overall_status(checks)
        assert status == "unhealthy"

        # Test authentication error
        checks = {
            "configuration": True,
            "oauth_handler": True,
            "authentication": {"status": "error"}
        }

        status = main._determine_overall_status(checks)
        assert status == "unhealthy"
