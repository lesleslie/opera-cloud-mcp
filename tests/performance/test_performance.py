"""
Performance and load testing for OPERA Cloud MCP server.

These tests verify that the server maintains optimal performance
under various load conditions and caching scenarios.
"""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler
from opera_cloud_mcp.clients.api_clients.reservations import APIResponse
from opera_cloud_mcp.clients.base_client import BaseAPIClient
from opera_cloud_mcp.config.settings import Settings


class TestPerformance:
    """Performance tests for the OPERA Cloud MCP server."""

    @pytest.fixture
    def mock_auth_handler(self) -> OAuthHandler:
        """Create a mock OAuth handler for testing."""
        handler = Mock(spec=OAuthHandler)
        handler.get_token = AsyncMock(return_value="test_token")
        handler.get_auth_header.return_value = {"Authorization": "Bearer test_token"}
        handler.get_token_info.return_value = {
            "has_token": True,
            "status": "valid",
            "expires_in": 3600,
        }
        return handler

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings for testing."""
        settings = Mock(spec=Settings)
        settings.opera_base_url = "https://placeholder.example.com/api"
        settings.opera_api_version = "v1"
        settings.request_timeout = 30
        settings.max_retries = 3
        settings.retry_backoff = 1.0
        settings.enable_cache = True
        settings.cache_ttl = 300
        settings.cache_max_memory = 10000
        return settings

    @pytest.fixture
    def api_client(self, mock_auth_handler, mock_settings) -> BaseAPIClient:
        """Create an API client for testing."""
        return BaseAPIClient(
            auth_handler=mock_auth_handler,
            hotel_id="TEST_HOTEL",
            settings=mock_settings,
            enable_rate_limiting=True,
            enable_monitoring=True,
            enable_caching=True,
            requests_per_second=100,  # High rate for testing
            burst_capacity=200,
        )

    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self, api_client: BaseAPIClient):
        """Test performance under concurrent requests."""
        # Mock successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test_response"}
        mock_response.content = b'{"data": "test_response"}'
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_http_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.request = AsyncMock(return_value=mock_response)
            mock_http_client.return_value = mock_client_instance

            # Test concurrent requests
            start_time = time.time()
            tasks = []

            # Create 50 concurrent requests
            for i in range(50):
                task = api_client.get(f"/test/endpoint/{i}")
                tasks.append(task)

            responses = await asyncio.gather(*tasks)
            end_time = time.time()

            # Validate all requests completed successfully
            assert len(responses) == 50
            for response in responses:
                assert isinstance(response, APIResponse)
                assert response.success is True
                assert response.status_code == 200

            # Check performance - should complete within reasonable time
            total_time = end_time - start_time
            assert total_time < 5.0  # Should complete within 5 seconds

            # Check that we're using connection pooling efficiently
            # All requests should share the same client instance
            assert mock_client_instance.request.call_count == 50

    @pytest.mark.asyncio
    async def test_caching_performance(self, api_client: BaseAPIClient):
        """Test caching performance improvements."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "cached_response"}
        mock_response.content = b'{"data": "cached_response"}'
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_http_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.request = AsyncMock(return_value=mock_response)
            mock_http_client.return_value = mock_client_instance

            # Measure cache hit performance
            response1 = await api_client.get(
                "/test/cached-endpoint", enable_caching=True
            )

            # Second request - should be served from cache
            response2 = await api_client.get(
                "/test/cached-endpoint", enable_caching=True
            )

        # Validate responses
        assert response1.success is True
        assert response2.success is True
        assert response1.data == response2.data

        # Cache hit should be significantly faster
        # We can't assert exact times in tests, but we can check call counts
        assert mock_client_instance.request.call_count == 1  # Only one actual API call

    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, api_client: BaseAPIClient):
        """Test rate limiting behavior under high load."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test_response"}
        mock_response.content = b'{"data": "test_response"}'
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_http_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.request = AsyncMock(return_value=mock_response)
            mock_http_client.return_value = mock_client_instance

            # Test burst of requests that should trigger rate limiting
            start_time = time.time()
            tasks = []

            # Create more requests than burst capacity
            for i in range(250):  # More than burst_capacity of 200
                task = api_client.get(f"/test/rate-limit/{i}")
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Validate all requests completed (possibly with delays)
            successful_responses = [
                r for r in responses if not isinstance(r, Exception)
            ]
            assert len(successful_responses) == 250

            # Check that rate limiting was applied (requests took longer due to waiting)
            total_time = end_time - start_time
            # Even with rate limiting, should complete within reasonable time
            assert total_time < 10.0

    @pytest.mark.asyncio
    async def test_error_handling_performance(self, api_client: BaseAPIClient):
        """Test performance of error handling and retry logic."""
        # Mock error response that will trigger retries
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_error_response.json.return_value = {"error": "internal_server_error"}
        mock_error_response.text = "Internal Server Error"
        mock_error_response.headers = {}

        # Mock successful response for retry
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"data": "success_after_retry"}
        mock_success_response.content = b'{"data": "success_after_retry"}'
        mock_success_response.headers = {}

        with patch("httpx.AsyncClient") as mock_http_client:
            mock_client_instance = AsyncMock()
            # First call fails, second succeeds
            mock_client_instance.request = AsyncMock(
                side_effect=[
                    mock_error_response,
                    mock_success_response,
                ]
            )
            mock_http_client.return_value = mock_client_instance

            start_time = time.time()
            response = await api_client.get("/test/retry-endpoint")
            end_time = time.time()

            # Validate successful response after retry
            assert response.success is True
            assert response.status_code == 200
            assert response.data == {"data": "success_after_retry"}

            # Check that retry was attempted
            assert mock_client_instance.request.call_count == 2

            # Check performance - even with retry, should be reasonable
            total_time = end_time - start_time
            assert total_time < 3.0  # Should complete within 3 seconds

    @pytest.mark.asyncio
    async def test_health_check_performance(self, api_client: BaseAPIClient):
        """Test performance of health check functionality."""
        start_time = time.time()
        health_status = await api_client.health_check()
        end_time = time.time()

        # Validate health check response
        assert isinstance(health_status, dict)
        assert "client_initialized" in health_status
        assert "rate_limiting_enabled" in health_status
        assert "monitoring_enabled" in health_status

        # Health check should be very fast
        health_check_time = end_time - start_time
        assert health_check_time < 0.1  # Should complete within 100ms

    def test_connection_pooling_configuration(self, api_client: BaseAPIClient):
        """Test that connection pooling is properly configured."""
        # Check connection limits
        assert api_client._connection_limits.max_connections == 50
        assert api_client._connection_limits.max_keepalive_connections == 20
        assert api_client._connection_limits.keepalive_expiry == 30.0

        # Check timeout configuration
        assert api_client._timeout_config.connect == 10.0
        assert api_client._timeout_config.read == 30  # From mock settings
        assert api_client._timeout_config.write == 10.0
        assert api_client._timeout_config.pool == 5.0

    @pytest.mark.asyncio
    async def test_concurrent_client_sessions(self):
        """Test performance with multiple concurrent client sessions."""
        mock_auth_handler = Mock()
        mock_auth_handler.get_token = AsyncMock(return_value="test_token")
        mock_auth_handler.get_auth_header.return_value = {
            "Authorization": "Bearer test_token"
        }

        mock_settings = Mock()
        mock_settings.opera_base_url = "https://placeholder.example.com/api"
        mock_settings.opera_api_version = "v1"
        mock_settings.request_timeout = 30
        mock_settings.max_retries = 3
        mock_settings.retry_backoff = 1.0
        mock_settings.enable_cache = True
        mock_settings.cache_ttl = 300
        mock_settings.cache_max_memory = 10000

        # Create multiple clients
        clients = []
        for i in range(10):
            client = BaseAPIClient(
                auth_handler=mock_auth_handler,
                hotel_id=f"TEST_HOTEL_{i}",
                settings=mock_settings,
                enable_rate_limiting=True,
                enable_monitoring=True,
                enable_caching=True,
            )
            clients.append(client)

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test_response"}
        mock_response.content = b'{"data": "test_response"}'
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_http_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.request = AsyncMock(return_value=mock_response)
            mock_http_client.return_value = mock_client_instance

            # Run concurrent requests across all clients
            start_time = time.time()
            all_tasks = []

            for client in clients:
                for i in range(5):  # 5 requests per client
                    task = client.get(f"/test/multi-client/{i}")
                    all_tasks.append(task)

            responses = await asyncio.gather(*all_tasks)
            end_time = time.time()

            # Validate all requests completed
            assert len(responses) == 50  # 10 clients * 5 requests each
            for response in responses:
                assert isinstance(response, APIResponse)
                assert response.success is True

            # Check performance
            total_time = end_time - start_time
            assert total_time < 5.0  # Should complete within 5 seconds

            # Clean up clients
            close_tasks = [client.close() for client in clients]
            await asyncio.gather(*close_tasks)
