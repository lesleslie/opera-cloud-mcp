"""
Unit tests for enhanced OAuth2 security component integration.

Tests the integration of SecureOAuthHandler, SecurityMiddleware, and related
security components to ensure they work together properly.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from opera_cloud_mcp.auth import create_enhanced_oauth_security
from opera_cloud_mcp.auth.audit_logger import AuditLogger
from opera_cloud_mcp.auth.secure_oauth_handler import SecureOAuthHandler
from opera_cloud_mcp.auth.security_middleware import SecurityMiddleware
from opera_cloud_mcp.clients.client_factory import ClientFactory
from opera_cloud_mcp.config.settings import Settings


class TestEnhancedOAuthIntegration:
    """Test enhanced OAuth2 security integration."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings for testing."""
        return Settings(
            opera_client_id="test_client_id",
            opera_client_secret="test_client_secret",
            opera_base_url="https://api.test.com",
            opera_api_version="v1",
            request_timeout=30,
            max_retries=3,
            retry_backoff=1.0,
        )

    @pytest.fixture
    def temp_cache_dir(self, tmp_path) -> Path:
        """Create temporary cache directory."""
        return tmp_path / "oauth_cache"

    def test_create_enhanced_oauth_security_components(self, temp_cache_dir):
        """Test creation of enhanced OAuth2 security components."""
        # Test with all security features enabled
        oauth_handler, security_middleware, audit_logger = (
            create_enhanced_oauth_security(
                client_id="test_client_id",
                client_secret="test_client_secret",
                token_url="https://auth.test.com/oauth/token",
                enable_security_monitoring=True,
                enable_rate_limiting=True,
                enable_token_binding=True,
                enable_audit_logging=True,
                cache_dir=temp_cache_dir,
            )
        )

        # Verify all components are created and are correct types
        assert isinstance(oauth_handler, SecureOAuthHandler)
        assert isinstance(security_middleware, SecurityMiddleware)
        assert isinstance(audit_logger, AuditLogger)

        # Verify OAuth handler has security features enabled
        assert oauth_handler.enable_security_monitoring is True
        assert oauth_handler.enable_rate_limiting is True
        assert oauth_handler.enable_token_binding is True

    def test_create_enhanced_oauth_security_minimal(self):
        """Test creation with minimal security features."""
        # Test with security features disabled
        oauth_handler, security_middleware, audit_logger = (
            create_enhanced_oauth_security(
                client_id="test_client_id",
                client_secret="test_client_secret",
                token_url="https://auth.test.com/oauth/token",
                enable_security_monitoring=False,
                enable_rate_limiting=False,
                enable_token_binding=False,
                enable_audit_logging=False,
            )
        )

        # Verify components are still created
        assert isinstance(oauth_handler, SecureOAuthHandler)
        assert isinstance(security_middleware, SecurityMiddleware)
        assert isinstance(audit_logger, AuditLogger)

        # Verify OAuth handler has security features configured as requested
        assert oauth_handler.enable_security_monitoring is False
        assert oauth_handler.enable_rate_limiting is False
        assert oauth_handler.enable_token_binding is False

    def test_secure_client_factory_creation(self, mock_settings, temp_cache_dir):
        """Test creation of secure client factory with enhanced OAuth2."""
        # Create secure client factory
        factory = ClientFactory.create_secure_factory(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_url="https://auth.test.com/oauth/token",
            settings=mock_settings,
            hotel_id="TEST_HOTEL",
            enable_security_monitoring=True,
            enable_rate_limiting=True,
            enable_token_binding=True,
            cache_dir=temp_cache_dir,
        )

        # Verify factory is created with secure OAuth handler
        assert isinstance(factory, ClientFactory)
        assert isinstance(factory.auth_handler, SecureOAuthHandler)
        assert factory.default_hotel_id == "TEST_HOTEL"

        # Verify OAuth handler has security features enabled
        assert factory.auth_handler.enable_security_monitoring is True
        assert factory.auth_handler.enable_rate_limiting is True
        assert factory.auth_handler.enable_token_binding is True

    def test_basic_client_factory_creation(self, mock_settings, temp_cache_dir):
        """Test creation of basic client factory for comparison."""
        from opera_cloud_mcp.auth.oauth_handler import OAuthHandler

        # Create basic client factory
        factory = ClientFactory.create_basic_factory(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_url="https://auth.test.com/oauth/token",
            settings=mock_settings,
            hotel_id="TEST_HOTEL",
            cache_dir=temp_cache_dir,
        )

        # Verify factory is created with basic OAuth handler
        assert isinstance(factory, ClientFactory)
        assert isinstance(factory.auth_handler, OAuthHandler)
        assert not isinstance(factory.auth_handler, SecureOAuthHandler)
        assert factory.default_hotel_id == "TEST_HOTEL"

    def test_oauth_handler_compatibility(self, mock_settings):
        """Test that both OAuth handlers are compatible with base client."""
        from opera_cloud_mcp.auth.oauth_handler import OAuthHandler
        from opera_cloud_mcp.clients.base_client import BaseAPIClient

        # Test basic OAuth handler
        basic_handler = OAuthHandler(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_url="https://auth.test.com/oauth/token",
        )

        # Should be able to create base client with basic handler
        basic_client = BaseAPIClient(
            auth_handler=basic_handler,
            hotel_id="TEST_HOTEL",
            settings=mock_settings,
        )
        assert basic_client.auth == basic_handler

        # Test secure OAuth handler
        secure_handler = SecureOAuthHandler(
            client_id="test_client_id",
            client_secret="test_client_secret",
            token_url="https://auth.test.com/oauth/token",
        )

        # Should be able to create base client with secure handler
        secure_client = BaseAPIClient(
            auth_handler=secure_handler,
            hotel_id="TEST_HOTEL",
            settings=mock_settings,
        )
        assert secure_client.auth == secure_handler

    def test_security_component_integration(self, temp_cache_dir):
        """Test that security components work together properly."""
        # Create enhanced security components
        oauth_handler, security_middleware, audit_logger = (
            create_enhanced_oauth_security(
                client_id="test_client_id",
                client_secret="test_client_secret",
                token_url="https://auth.test.com/oauth/token",
                enable_security_monitoring=True,
                cache_dir=temp_cache_dir,
            )
        )

        # Verify security middleware is properly configured
        from opera_cloud_mcp.config.security_settings import SecuritySettings

        assert isinstance(security_middleware.settings, SecuritySettings)

        # Verify cache directory is properly configured
        # The path should be configured (whether file exists depends on usage)
        assert temp_cache_dir.exists()

    @patch("opera_cloud_mcp.auth.AuditLogger")
    @patch("opera_cloud_mcp.auth.SecurityMiddleware")
    def test_enhanced_oauth_security_creation_with_mocks(
        self, mock_security_middleware, mock_audit_logger
    ):
        """Test enhanced OAuth security creation with mocked dependencies."""
        # Setup mocks
        mock_middleware_instance = Mock()
        mock_security_middleware.return_value = mock_middleware_instance
        mock_audit_instance = Mock()
        mock_audit_logger.return_value = mock_audit_instance

        # Create enhanced security components
        oauth_handler, security_middleware, audit_logger = (
            create_enhanced_oauth_security(
                client_id="test_client_id",
                client_secret="test_client_secret",
                token_url="https://auth.test.com/oauth/token",
            )
        )

        # Verify components are created
        assert isinstance(oauth_handler, SecureOAuthHandler)
        assert security_middleware == mock_middleware_instance
        assert audit_logger == mock_audit_instance

        # Verify mocks were called appropriately
        mock_security_middleware.assert_called_once()
        mock_audit_logger.assert_called_once()

    def test_security_settings_integration(self, temp_cache_dir):
        """Test integration with custom security settings."""
        from opera_cloud_mcp.config.security_settings import SecuritySettings

        # Create custom security settings
        custom_settings = SecuritySettings(
            enable_security_monitoring=True,
            enable_rate_limiting=True,
            enable_token_binding=True,
            max_failed_attempts=3,
            token_max_lifetime_hours=12,
        )

        # Create enhanced security with custom settings
        oauth_handler, security_middleware, audit_logger = (
            create_enhanced_oauth_security(
                client_id="test_client_id",
                client_secret="test_client_secret",
                token_url="https://auth.test.com/oauth/token",
                security_settings=custom_settings,
                cache_dir=temp_cache_dir,
            )
        )

        # Verify security settings are applied
        assert security_middleware.settings == custom_settings
        assert security_middleware.settings.max_failed_attempts == 3
        assert security_middleware.settings.token_max_lifetime_hours == 12
