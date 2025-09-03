"""
Unit tests for API client module.

Tests base client functionality, retry logic, and error handling.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.config.settings import Settings
from opera_cloud_mcp.utils.exceptions import (
    RateLimitError,
    ResourceNotFoundError,
    ValidationError,
)


class TestAPIResponse:
    """Tests for APIResponse model."""

    def test_successful_response(self):
        """Test successful API response creation."""
        response = APIResponse(success=True, data={"key": "value"}, status_code=200)

        assert response.success is True
        assert response.data == {"key": "value"}
        assert response.error is None
        assert response.status_code == 200

    def test_error_response(self):
        """Test error API response creation."""
        response = APIResponse(
            success=False, error="Something went wrong", status_code=400
        )

        assert response.success is False
        assert response.data is None
        assert response.error == "Something went wrong"
        assert response.status_code == 400


class TestBaseAPIClient:
    """Tests for BaseAPIClient."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings."""
        return Settings(
            opera_client_id="test_id",
            opera_client_secret="test_secret",
            opera_base_url="https://api.test.com",
            opera_api_version="v1",
            request_timeout=30,
            max_retries=3,
            retry_backoff=1.0,
        )

    @pytest.fixture
    def mock_auth_handler(self) -> Mock:
        """Create mock auth handler."""
        handler = Mock()
        handler.get_token = AsyncMock(return_value="mock_token")
        handler.get_auth_header.return_value = {"Authorization": "Bearer mock_token"}
        handler.invalidate_token = AsyncMock()
        return handler

    @pytest.fixture
    def client(self, mock_auth_handler: Mock, mock_settings: Settings) -> BaseAPIClient:
        """Create API client for testing."""
        return BaseAPIClient(
            auth_handler=mock_auth_handler,
            hotel_id="TEST_HOTEL",
            settings=mock_settings,
        )

    def test_base_url_property(self, client: BaseAPIClient):
        """Test base URL construction."""
        assert client.base_url == "https://api.test.com/v1"

    @pytest.mark.asyncio
    async def test_successful_request(self, client: BaseAPIClient):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.content = b'{"result": "success"}'
        mock_response.url = "https://api.test.com/v1/test"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.request = Mock(method="GET")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            client._session = mock_client

            response = await client.request("GET", "/test")

            assert response.success is True
            assert response.data == {"result": "success"}
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_authentication_error_retry(
        self, client: BaseAPIClient, mock_auth_handler: Mock
    ):
        """Test authentication error with retry."""
        # First call returns 401, second succeeds
        mock_responses = [
            Mock(status_code=401, text="Unauthorized", content=b"Unauthorized"),
            Mock(
                status_code=200,
                json=lambda: {"result": "success"},
                content=b'{"result": "success"}',
            ),
        ]
        mock_responses[0].json.side_effect = ValueError("No JSON")
        mock_responses[0].headers = {}
        mock_responses[0].url = "https://api.test.com/v1/test"
        mock_responses[0].request = Mock(method="GET")
        mock_responses[1].url = "https://api.test.com/v1/test"
        mock_responses[1].headers = {"content-type": "application/json"}
        mock_responses[1].request = Mock(method="GET")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.side_effect = mock_responses

            client._session = mock_client

            # Should succeed on retry after token invalidation
            response = await client.request("GET", "/test")

            # Should have called invalidate_token
            mock_auth_handler.invalidate_token.assert_called()

            # Should have succeeded
            assert response.success is True
            assert response.data == {"result": "success"}

    @pytest.mark.asyncio
    async def test_resource_not_found_error(self, client: BaseAPIClient):
        """Test 404 resource not found handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.content = b"Not found"
        mock_response.url = "https://api.test.com/v1/test"
        mock_response.headers = {}
        mock_response.request = Mock(method="GET")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            client._session = mock_client

            with pytest.raises(ResourceNotFoundError) as exc_info:
                await client.request("GET", "/test")

            assert "Resource not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client: BaseAPIClient):
        """Test 429 rate limit handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.content = b"Rate limit exceeded"
        mock_response.url = "https://api.test.com/v1/test"
        mock_response.headers = {}
        mock_response.request = Mock(method="GET")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            client._session = mock_client

            with pytest.raises(RateLimitError) as exc_info:
                await client.request("GET", "/test")

            assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error(self, client: BaseAPIClient):
        """Test 422 validation error handling."""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"message": "Invalid input"}
        mock_response.content = b'{"message": "Invalid input"}'
        mock_response.url = "https://api.test.com/v1/test"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.request = Mock(method="GET")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            client._session = mock_client

            with pytest.raises(ValidationError) as exc_info:
                await client.request("POST", "/test", json_data={"invalid": "data"})

            assert "Validation error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_convenience_methods(self, client: BaseAPIClient):
        """Test GET, POST, PUT, DELETE convenience methods."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.content = b'{"success": true}'
        mock_response.url = "https://api.test.com/v1/test"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.request = Mock(method="GET")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            client._session = mock_client

            # Test all convenience methods
            await client.get("/test")
            await client.post("/test", json_data={"key": "value"})
            await client.put("/test", json_data={"key": "value"})
            await client.delete("/test")

            # Should have made 4 requests
            assert mock_client.request.call_count == 4

    @pytest.mark.asyncio
    async def test_context_manager(
        self, mock_auth_handler: Mock, mock_settings: Settings
    ):
        """Test async context manager usage."""
        async with BaseAPIClient(
            mock_auth_handler, "TEST_HOTEL", mock_settings
        ) as client:
            assert client._session is not None

        # Session should be closed after exiting context
