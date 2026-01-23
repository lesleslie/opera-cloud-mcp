"""Unit tests for client factory utilities.

Tests for opera_cloud_mcp/utils/client_factory.py
"""

from unittest.mock import MagicMock, patch
import pytest

from opera_cloud_mcp.utils.client_factory import (
    get_oauth_handler,
    create_reservations_client,
    create_crm_client,
)


class TestGetOAuthHandler:
    """Test get_oauth_handler function."""

    @patch('opera_cloud_mcp.utils.client_factory.get_settings')
    @patch('opera_cloud_mcp.utils.client_factory.OAuthHandler')
    def test_get_oauth_handler_creates_new_instance(self, mock_oauth_cls, mock_get_settings):
        """Test that get_oauth_handler creates new instance on first call."""
        mock_settings = MagicMock()
        mock_settings.opera_client_id = "test_client"
        mock_settings.opera_client_secret = "test_secret"
        mock_settings.opera_token_url = "https://api.example.com/token"
        mock_get_settings.return_value = mock_settings

        mock_handler_instance = MagicMock()
        mock_oauth_cls.return_value = mock_handler_instance

        result = get_oauth_handler()

        assert result == mock_handler_instance
        mock_oauth_cls.assert_called_once_with(
            client_id="test_client",
            client_secret="test_secret",
            token_url="https://api.example.com/token"
        )

    @patch('opera_cloud_mcp.utils.client_factory._oauth_handler', None)
    @patch('opera_cloud_mcp.utils.client_factory._settings', None)
    @patch('opera_cloud_mcp.utils.client_factory.get_settings')
    @patch('opera_cloud_mcp.utils.client_factory.OAuthHandler')
    def test_get_oauth_handler_cached(self, mock_oauth_cls, mock_get_settings):
        """Test that get_oauth_handler returns cached instance on subsequent calls."""
        mock_settings = MagicMock()
        mock_settings.opera_client_id = "test_client"
        mock_settings.opera_client_secret = "test_secret"
        mock_settings.opera_token_url = "https://api.example.com/token"
        mock_get_settings.return_value = mock_settings

        mock_handler_instance = MagicMock()
        mock_oauth_cls.return_value = mock_handler_instance

        # First call should create instance
        result1 = get_oauth_handler()
        # Second call should return cached instance
        result2 = get_oauth_handler()

        assert result1 is result2
        # OAuthHandler should only be created once
        mock_oauth_cls.assert_called_once()


class TestCreateReservationsClient:
    """Test create_reservations_client function."""

    @patch('opera_cloud_mcp.utils.client_factory.get_oauth_handler')
    @patch('opera_cloud_mcp.utils.client_factory.get_settings')
    @patch('opera_cloud_mcp.utils.client_factory.ReservationsClient')
    def test_create_reservations_client_with_hotel_id(self, mock_client_cls, mock_get_settings, mock_get_oauth):
        """Test creating ReservationsClient with explicit hotel_id."""
        mock_settings = MagicMock()
        mock_settings.default_hotel_id = "DEFAULT_HOTEL"
        mock_get_settings.return_value = mock_settings

        mock_oauth = MagicMock()
        mock_get_oauth.return_value = mock_oauth

        mock_client_instance = MagicMock()
        mock_client_cls.return_value = mock_client_instance

        result = create_reservations_client(hotel_id="HOTEL123")

        assert result == mock_client_instance
        mock_client_cls.assert_called_once_with(
            auth_handler=mock_oauth,
            hotel_id="HOTEL123",
            settings=mock_settings
        )

    @patch('opera_cloud_mcp.utils.client_factory.get_oauth_handler')
    @patch('opera_cloud_mcp.utils.client_factory.get_settings')
    @patch('opera_cloud_mcp.utils.client_factory.ReservationsClient')
    def test_create_reservations_client_default_hotel_id(self, mock_client_cls, mock_get_settings, mock_get_oauth):
        """Test creating ReservationsClient with default hotel_id."""
        mock_settings = MagicMock()
        mock_settings.default_hotel_id = "DEFAULT_HOTEL"
        mock_get_settings.return_value = mock_settings

        mock_oauth = MagicMock()
        mock_get_oauth.return_value = mock_oauth

        mock_client_instance = MagicMock()
        mock_client_cls.return_value = mock_client_instance

        result = create_reservations_client(hotel_id=None)

        assert result == mock_client_instance
        mock_client_cls.assert_called_once_with(
            auth_handler=mock_oauth,
            hotel_id="DEFAULT_HOTEL",
            settings=mock_settings
        )

    @patch('opera_cloud_mcp.utils.client_factory.get_oauth_handler')
    @patch('opera_cloud_mcp.utils.client_factory.get_settings')
    def test_create_reservations_client_no_hotel_id_error(self, mock_get_settings, mock_get_oauth):
        """Test error when hotel_id not provided and no default set."""
        mock_settings = MagicMock()
        mock_settings.default_hotel_id = None
        mock_get_settings.return_value = mock_settings

        mock_oauth = MagicMock()
        mock_get_oauth.return_value = mock_oauth

        with pytest.raises(ValueError, match="Hotel ID must be provided"):
            create_reservations_client(hotel_id=None)


class TestCreateCRMClient:
    """Test create_crm_client function."""

    @patch('opera_cloud_mcp.utils.client_factory.get_oauth_handler')
    @patch('opera_cloud_mcp.utils.client_factory.get_settings')
    @patch('opera_cloud_mcp.utils.client_factory.CRMClient')
    def test_create_crm_client_with_hotel_id(self, mock_client_cls, mock_get_settings, mock_get_oauth):
        """Test creating CRMClient with explicit hotel_id."""
        mock_settings = MagicMock()
        mock_settings.default_hotel_id = "DEFAULT_HOTEL"
        mock_get_settings.return_value = mock_settings

        mock_oauth = MagicMock()
        mock_get_oauth.return_value = mock_oauth

        mock_client_instance = MagicMock()
        mock_client_cls.return_value = mock_client_instance

        result = create_crm_client(hotel_id="HOTEL456")

        assert result == mock_client_instance
        mock_client_cls.assert_called_once_with(
            auth_handler=mock_oauth,
            hotel_id="HOTEL456",
            settings=mock_settings
        )
