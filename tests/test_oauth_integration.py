"""
Integration tests for OAuth2 authentication system.

Tests the complete OAuth2 implementation including token caching,
refresh logic, error handling, and security features.
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from opera_cloud_mcp.auth import create_oauth_handler
from opera_cloud_mcp.auth.oauth_handler import OAuthHandler, Token, TokenCache
from opera_cloud_mcp.config.settings import Settings
from opera_cloud_mcp.utils.exceptions import AuthenticationError


class TestTokenCache:
    """Test persistent token caching functionality."""

    def test_cache_initialization(self):
        """Test cache directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "test_cache"
            cache = TokenCache(cache_dir)

            assert cache.cache_dir == cache_dir
            assert cache_dir.exists()

    def test_token_encryption_round_trip(self):
        """Test token encryption and decryption."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TokenCache(Path(temp_dir))
            client_id = "test_client"

            # Create test token
            token = Token(
                access_token="test_token_123",
                token_type="Bearer",
                expires_in=3600,
                issued_at=datetime.utcnow(),
            )

            # Save and load token
            cache.save_token(client_id, token)
            loaded_token = cache.load_token(client_id)

            assert loaded_token is not None
            assert loaded_token.access_token == token.access_token
            assert loaded_token.token_type == token.token_type
            assert loaded_token.expires_in == token.expires_in
            assert abs((loaded_token.issued_at - token.issued_at).total_seconds()) < 1

    def test_cache_file_corruption_handling(self):
        """Test handling of corrupted cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TokenCache(Path(temp_dir))
            client_id = "test_client"

            # Create corrupted cache file
            cache_file = cache._get_cache_file(client_id)
            cache_file.write_text("corrupted_data")

            # Should handle corruption gracefully
            loaded_token = cache.load_token(client_id)
            assert loaded_token is None

            # Cache file should be cleaned up
            assert not cache_file.exists()


class TestOAuthHandler:
    """Test OAuth handler functionality."""

    def setup_method(self):
        """Set up test dependencies."""
        self.client_id = "test_client_id"
        self.client_secret = "test_client_secret"
        self.token_url = "https://example.com/oauth/token"

        # Create temporary directory that persists for the test
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir)
        self.handler = OAuthHandler(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_url=self.token_url,
            timeout=30,
            max_retries=2,
            retry_backoff=0.1,  # Fast retries for testing
            enable_persistent_cache=True,
            cache_dir=self.cache_dir,
        )

    def teardown_method(self):
        """Clean up test resources."""
        if hasattr(self, "temp_dir") and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_handler_initialization(self):
        """Test OAuth handler initialization."""
        assert self.handler.client_id == self.client_id
        assert self.handler.client_secret == self.client_secret
        assert self.handler.token_url == self.token_url
        assert self.handler.persistent_cache is not None

    def test_initialization_validation(self):
        """Test initialization with invalid parameters."""
        with pytest.raises(
            AuthenticationError, match="Client ID and client secret are required"
        ):
            OAuthHandler("", "secret", "https://example.com/token")

        with pytest.raises(AuthenticationError, match="Token URL is required"):
            OAuthHandler("client", "secret", "")

    @pytest.mark.asyncio
    async def test_successful_token_refresh(self):
        """Test successful token acquisition."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            token = await self.handler.get_token()

            assert token == "new_access_token"
            assert self.handler._token_cache is not None
            assert self.handler._token_cache.access_token == "new_access_token"
            assert self.handler._token_refresh_count == 1

    @pytest.mark.asyncio
    async def test_token_refresh_retry_logic(self):
        """Test retry logic on temporary failures."""
        # First call fails with 500, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.json.return_value = {"error": "server_error"}
        mock_response_fail.text = "Internal Server Error"

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "access_token": "retry_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient") as mock_client:
            # Configure mock to fail first, then succeed
            mock_post = AsyncMock(
                side_effect=[mock_response_fail, mock_response_success]
            )
            mock_client.return_value.__aenter__.return_value.post = mock_post

            with patch("asyncio.sleep") as mock_sleep:  # Speed up retries
                token = await self.handler.get_token()

                assert token == "retry_token"
                assert mock_post.call_count == 2
                assert mock_sleep.call_count == 1  # One retry

    @pytest.mark.asyncio
    async def test_authentication_error_no_retry(self):
        """Test that authentication errors (401, 403) are not retried."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client credentials",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(AuthenticationError, match="Invalid client credentials"):
                await self.handler.get_token()

    @pytest.mark.asyncio
    async def test_persistent_cache_integration(self):
        """Test persistent cache saves and loads tokens."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "cached_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            # Get token (should save to cache)
            token1 = await self.handler.get_token()
            assert token1 == "cached_token"

            # Create new handler with same cache directory
            handler2 = OAuthHandler(
                client_id=self.client_id,
                client_secret=self.client_secret,
                token_url=self.token_url,
                enable_persistent_cache=True,
                cache_dir=self.cache_dir,
            )

            # Should load from cache without making HTTP request
            token2 = await handler2.get_token()
            assert token2 == "cached_token"

            # HTTP client should only be called once (by first handler)
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 1

    @pytest.mark.asyncio
    async def test_token_expiry_handling(self):
        """Test handling of expired tokens."""
        # Create expired token
        expired_token = Token(
            access_token="expired_token",
            token_type="Bearer",
            expires_in=3600,
            issued_at=datetime.utcnow() - timedelta(seconds=3700),  # Expired
        )

        self.handler._token_cache = expired_token

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            # Should refresh expired token
            token = await self.handler.get_token()
            assert token == "new_token"

    @pytest.mark.asyncio
    async def test_proactive_token_refresh(self):
        """Test proactive token refresh with minimum validity."""
        # Create token expiring soon
        soon_expired_token = Token(
            access_token="soon_expired",
            token_type="Bearer",
            expires_in=3600,
            issued_at=datetime.utcnow() - timedelta(seconds=3400),  # 200 seconds left
        )

        self.handler._token_cache = soon_expired_token

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            # Request token with 300 seconds minimum validity
            token = await self.handler.ensure_valid_token(min_validity_seconds=300)
            assert token == "refreshed_token"

    def test_token_info_status(self):
        """Test token information reporting."""
        # No token
        info = self.handler.get_token_info()
        assert info["has_token"] is False
        assert info["status"] == "no_token"

        # Valid token
        valid_token = Token(
            access_token="valid_token",
            token_type="Bearer",
            expires_in=3600,
            issued_at=datetime.utcnow(),
        )
        self.handler._token_cache = valid_token

        info = self.handler.get_token_info()
        assert info["has_token"] is True
        assert info["status"] == "valid"

        # Expiring soon token
        expiring_token = Token(
            access_token="expiring_token",
            token_type="Bearer",
            expires_in=3600,
            issued_at=datetime.utcnow() - timedelta(seconds=3400),  # 200 seconds left
        )
        self.handler._token_cache = expiring_token

        info = self.handler.get_token_info()
        assert info["status"] == "expiring_soon"

        # Expired token
        expired_token = Token(
            access_token="expired_token",
            token_type="Bearer",
            expires_in=3600,
            issued_at=datetime.utcnow() - timedelta(seconds=3700),
        )
        self.handler._token_cache = expired_token

        info = self.handler.get_token_info()
        assert info["status"] == "expired"


class TestOAuthIntegration:
    """Test integration with settings and factory functions."""

    def test_create_oauth_handler_from_settings(self):
        """Test OAuth handler creation from settings."""
        # Mock settings with valid configuration
        settings = Mock(spec=Settings)
        settings.validate_required_settings.return_value = []
        settings.get_oauth_handler_config.return_value = {
            "client_id": "test_client",
            "client_secret": "test_secret",
            "token_url": "https://example.com/token",
            "timeout": 30,
            "max_retries": 3,
            "retry_backoff": 1.0,
            "enable_persistent_cache": True,
            "cache_dir": None,
        }

        handler = create_oauth_handler(settings)

        assert isinstance(handler, OAuthHandler)
        assert handler.client_id == "test_client"
        assert handler.client_secret == "test_secret"

    def test_create_oauth_handler_missing_settings(self):
        """Test handler creation with missing settings."""
        settings = Mock(spec=Settings)
        settings.validate_required_settings.return_value = [
            "OPERA_CLIENT_ID",
            "OPERA_CLIENT_SECRET",
        ]

        with pytest.raises(AuthenticationError, match="Missing required settings"):
            create_oauth_handler(settings)

    @pytest.mark.asyncio
    async def test_credential_validation(self):
        """Test credential validation functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = OAuthHandler(
                client_id="test_client",
                client_secret="test_secret",
                token_url="https://example.com/token",
                cache_dir=Path(temp_dir),
            )

            # Mock successful validation
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "validation_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                is_valid = await handler.validate_credentials()
                assert is_valid is True

            # Mock failed validation
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "invalid_client"}

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                is_valid = await handler.validate_credentials()
                assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
