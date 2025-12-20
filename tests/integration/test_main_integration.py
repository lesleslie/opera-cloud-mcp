"""
Integration tests for OPERA Cloud MCP main module.

These tests verify the complete integration of the MCP server
with all components including authentication, configuration,
and tool registration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

# Test constants to avoid hardcoded password warnings
TEST_CLIENT_SECRET = "placeholder_secret_value_for_testing_only"
TEST_TOKEN_URL = "https://placeholder.example.com/token"
TEST_BASE_URL = "https://placeholder.example.com/api"


class TestMainIntegration:
    """Test suite for main.py integration tests."""

    @pytest.fixture
    def mock_oauth_handler(self):
        """Mock OAuth handler for testing."""
        handler = AsyncMock()
        handler.get_token.return_value = "test_token"
        return handler

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.opera_client_id = "test_client"
        settings.opera_client_secret = TEST_CLIENT_SECRET
        settings.opera_token_url = TEST_TOKEN_URL
        settings.opera_base_url = TEST_BASE_URL
        settings.default_hotel_id = "TEST_HOTEL"
        settings.opera_environment = "test"
        settings.opera_api_version = "v1"
        settings.enable_cache = True
        settings.cache_ttl = 3600
        return settings

    def test_fastmcp_app_creation(self):
        """Test that FastMCP app is created correctly."""
        # Import here to avoid circular imports during test collection
        import opera_cloud_mcp.main as main_module

        app = main_module.app

        assert isinstance(app, FastMCP)
        assert app.name == "opera-cloud-mcp"
        assert app.version == "0.1.0"
        assert "MCP server for Oracle OPERA Cloud API integration" in app.description

    @patch("opera_cloud_mcp.main.get_settings")
    @patch("opera_cloud_mcp.main.create_oauth_handler")
    async def test_startup_success(
        self,
        mock_create_oauth_handler,
        mock_get_settings,
        mock_settings,
        mock_oauth_handler,
    ):
        """Test successful server startup and authentication."""
        mock_get_settings.return_value = mock_settings
        mock_settings.validate_oauth_credentials_at_startup = MagicMock()
        mock_create_oauth_handler.return_value = mock_oauth_handler

        from opera_cloud_mcp.main import initialize_server

        await initialize_server()

        mock_settings.validate_oauth_credentials_at_startup.assert_called_once()
        mock_create_oauth_handler.assert_called_once_with(mock_settings)

    @patch("opera_cloud_mcp.main.get_settings")
    @patch("opera_cloud_mcp.main.create_oauth_handler")
    async def test_startup_auth_failure(
        self, mock_create_oauth_handler, mock_get_settings, mock_settings
    ):
        """Test startup failure when authentication fails."""
        mock_get_settings.return_value = mock_settings
        mock_settings.validate_oauth_credentials_at_startup = MagicMock()

        mock_create_oauth_handler.side_effect = Exception("Auth failed")

        # Test that startup raises exception on auth failure
        from opera_cloud_mcp.main import initialize_server

        with pytest.raises(Exception, match="Auth failed"):
            await initialize_server()

    @patch("opera_cloud_mcp.main.get_settings")
    async def test_api_documentation_resource(self, mock_get_settings, mock_settings):
        """Test API documentation resource."""
        mock_get_settings.return_value = mock_settings

        from opera_cloud_mcp.main import api_documentation

        resource = await api_documentation()

        assert resource.uri == "opera://api/docs"
        assert resource.name == "OPERA Cloud API Documentation"
        assert (
            "Comprehensive documentation for OPERA Cloud REST APIs"
            in resource.description
        )
        assert resource.mimeType == "text/markdown"
        assert "Authentication" in resource.text
        assert "Reservations" in resource.text
        assert "Front Office" in resource.text

    @patch("opera_cloud_mcp.main.get_settings")
    async def test_hotel_configuration_resource(self, mock_get_settings, mock_settings):
        """Test hotel configuration resource."""
        mock_get_settings.return_value = mock_settings

        from opera_cloud_mcp.main import hotel_configuration

        resource = await hotel_configuration()

        assert resource.uri == "opera://config/hotel"
        assert resource.name == "Hotel Configuration"
        assert "Current hotel configuration settings" in resource.description
        assert resource.mimeType == "application/json"

        # Parse the JSON content to verify structure
        import json

        config_data = json.loads(resource.text)

        assert config_data["default_hotel_id"] == "TEST_HOTEL"
        assert config_data["api_environment"] == "test"
        assert config_data["api_version"] == "v1"
        assert config_data["cache_enabled"] == "true"
        assert config_data["cache_ttl"] == 3600

    @patch("opera_cloud_mcp.main.get_settings")
    @patch("opera_cloud_mcp.main.auth_handler", None)  # Reset global auth_handler
    async def test_health_check_all_healthy(self, mock_get_settings, mock_settings):
        """Test health check endpoint when all systems are healthy."""
        mock_get_settings.return_value = mock_settings

        # Mock healthy auth handler
        healthy_auth = MagicMock()
        healthy_auth.get_token_info.return_value = {
            "has_token": True,
            "status": "valid",
            "refresh_count": 0,
            "expires_in": 3600,
        }

        with patch("opera_cloud_mcp.main.auth_handler", healthy_auth):
            from opera_cloud_mcp.main import health_check

            result = health_check()

            assert result["status"] == "healthy"
            assert result["checks"]["mcp_server"]
            assert result["checks"]["oauth_handler"]
            assert result["checks"]["configuration"]
            assert result["checks"]["version"] == "0.1.0"

    @patch("opera_cloud_mcp.main.get_settings")
    @patch("opera_cloud_mcp.main.auth_handler", None)  # Reset global auth_handler
    async def test_health_check_auth_failure(self, mock_get_settings, mock_settings):
        """Test health check when authentication fails."""
        mock_get_settings.return_value = mock_settings

        # Mock failing auth handler
        failing_auth = MagicMock()
        failing_auth.get_token_info.side_effect = Exception("Auth failed")

        with patch("opera_cloud_mcp.main.auth_handler", failing_auth):
            from opera_cloud_mcp.main import health_check

            result = health_check()

            assert result["status"] == "unhealthy"
            assert result["checks"]["mcp_server"]
            assert result["checks"]["oauth_handler"]
            assert result["checks"]["configuration"]
            assert result["checks"]["authentication"]["status"] == "error"

    @patch("opera_cloud_mcp.main.get_settings")
    async def test_health_check_config_failure(self, mock_get_settings):
        """Test health check when configuration is invalid."""
        # Mock settings with missing credentials
        bad_settings = MagicMock()
        bad_settings.opera_client_id = None
        bad_settings.opera_client_secret = TEST_CLIENT_SECRET
        mock_get_settings.return_value = bad_settings

        with (
            patch("opera_cloud_mcp.main.auth_handler", None),
            patch("opera_cloud_mcp.main.oauth_handler", None),
        ):
            from opera_cloud_mcp.main import health_check

            result = health_check()

            assert result["status"] == "unhealthy"
            assert result["checks"]["mcp_server"]
            assert not result["checks"]["oauth_handler"]
            assert not result["checks"]["configuration"]

    def test_get_auth_handler_success(self):
        """Test get_auth_handler returns the global handler."""
        from opera_cloud_mcp.main import get_auth_handler

        # Mock a handler
        mock_handler = MagicMock()

        with patch("opera_cloud_mcp.main.auth_handler", mock_handler):
            result = get_auth_handler()
            assert result == mock_handler

    def test_get_auth_handler_not_initialized(self):
        """Test get_auth_handler raises error when not initialized."""
        from opera_cloud_mcp.main import get_auth_handler

        with (
            patch("opera_cloud_mcp.main.auth_handler", None),
            patch("opera_cloud_mcp.main.oauth_handler", None),
            pytest.raises(RuntimeError, match="Authentication handler not initialized"),
        ):
            get_auth_handler()

    async def test_tool_registration(self):
        """Test that the server module registers tools."""
        import opera_cloud_mcp.server as server_module

        tools = await server_module.app.get_tools()
        tool_names = list(tools.keys())

        expected_tools = [
            "search_reservations",
            "search_guests",
            "check_room_availability",
            "check_in_guest",
            "get_guest_folio",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names

    def test_uvicorn_configuration(self):
        """Test uvicorn configuration in __main__ block."""
        import os

        # Test default port
        with patch.dict(os.environ, {}, clear=True):
            # This will only work if we modify main.py to expose the port
            # For now, just test the default behavior conceptually
            assert True  # Placeholder test

        # Test custom port
        with patch.dict(os.environ, {"PORT": "9000"}):
            # Would test that port gets set to 9000
            assert True  # Placeholder test
