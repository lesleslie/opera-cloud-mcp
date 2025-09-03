"""
Unit tests for authentication module.

Tests OAuth2 token handling, caching, and error scenarios.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import httpx
import pytest

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler, Token
from opera_cloud_mcp.utils.exceptions import AuthenticationError


class TestToken:
    """Tests for Token model."""

    def test_token_creation(self):
        """Test token creation and properties."""
        now = datetime.now(UTC)
        token = Token(access_token="test_token", expires_in=3600, issued_at=now)

        assert token.access_token == "test_token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.issued_at == now
        assert token.expires_at == now + timedelta(seconds=3600)

    def test_token_expiry_check(self):
        """Test token expiry detection."""
        # Expired token
        past_time = datetime.now(UTC) - timedelta(hours=2)
        expired_token = Token(
            access_token="expired", expires_in=3600, issued_at=past_time
        )
        assert expired_token.is_expired

        # Valid token
        recent_time = datetime.now(UTC) - timedelta(minutes=5)
        valid_token = Token(
            access_token="valid", expires_in=3600, issued_at=recent_time
        )
        assert not valid_token.is_expired


class TestOAuthHandler:
    """Tests for OAuthHandler."""

    @pytest.fixture
    def oauth_handler(self) -> OAuthHandler:
        """Create OAuth handler for testing."""
        return OAuthHandler(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://api.test.com/oauth/v1/tokens",
        )

    @pytest.mark.asyncio
    async def test_get_token_success(self, oauth_handler: OAuthHandler):
        """Test successful token acquisition."""

        with patch.object(oauth_handler, "_refresh_token") as mock_refresh:
            mock_refresh.return_value = "new_access_token"

            token = await oauth_handler.get_token()

            assert token == "new_access_token"
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_from_cache(self, oauth_handler: OAuthHandler):
        """Test token retrieval from cache."""
        # Set a valid cached token
        oauth_handler._token_cache = Token(
            access_token="cached_token", expires_in=3600, issued_at=datetime.now(UTC)
        )

        with patch.object(oauth_handler, "_refresh_token") as mock_refresh:
            token = await oauth_handler.get_token()

            assert token == "cached_token"
            mock_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, oauth_handler: OAuthHandler):
        """Test successful token refresh."""
        mock_response_data = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data

            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            token = await oauth_handler._refresh_token()

            assert token == "new_token"
            assert oauth_handler._token_cache is not None
            assert oauth_handler._token_cache.access_token == "new_token"

    @pytest.mark.asyncio
    async def test_refresh_token_failure(self, oauth_handler: OAuthHandler):
        """Test token refresh failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Invalid credentials"
            mock_response.json.return_value = {"error": "invalid_client"}

            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            with pytest.raises(AuthenticationError) as exc_info:
                await oauth_handler._refresh_token()

            assert "Token request failed: HTTP 400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_token_network_error(self, oauth_handler: OAuthHandler):
        """Test token refresh network error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = (
                httpx.ConnectTimeout("Connection timeout")
            )

            with pytest.raises(AuthenticationError) as exc_info:
                await oauth_handler._refresh_token()

            assert "Token request timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalidate_token(self, oauth_handler: OAuthHandler):
        """Test token invalidation."""
        # Set a cached token
        oauth_handler._token_cache = Token(
            access_token="cached_token", expires_in=3600, issued_at=datetime.now(UTC)
        )

        await oauth_handler.invalidate_token()

        assert oauth_handler._token_cache is None

    def test_get_auth_header(self, oauth_handler: OAuthHandler):
        """Test authorization header generation."""
        header = oauth_handler.get_auth_header("test_token")

        assert header == {"Authorization": "Bearer test_token"}
