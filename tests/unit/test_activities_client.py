"""
Unit tests for Activities API client.

Tests activities management functionality including CRUD operations,
booking management, and schedule handling.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler
from opera_cloud_mcp.clients.api_clients.activities import (
    ActivitiesClient,
)
from opera_cloud_mcp.config.settings import Settings


class TestActivitiesClient:
    """Tests for ActivitiesClient."""

    @pytest.fixture
    def mock_oauth_handler(self) -> Mock:
        """Create mock OAuth handler."""
        handler = Mock(spec=OAuthHandler)
        handler.get_token = AsyncMock(return_value="mock_token")
        handler.get_auth_header.return_value = {"Authorization": "Bearer mock_token"}
        handler.invalidate_token = AsyncMock()
        return handler

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.opera_base_url = "https://api.test.com"
        settings.opera_api_version = "v1"
        settings.request_timeout = 30
        settings.max_retries = 3
        settings.retry_backoff = 1.0
        settings.enable_cache = True
        settings.cache_ttl = 300
        settings.cache_max_memory = 10000
        return settings

    @pytest.fixture
    def activities_client(
        self, mock_oauth_handler: Mock, mock_settings: Mock
    ) -> ActivitiesClient:
        """Create ActivitiesClient instance for testing."""
        return ActivitiesClient(
            auth_handler=mock_oauth_handler,
            hotel_id="TEST_HOTEL",
            settings=mock_settings,
        )

    def test_activities_client_initialization(
        self, activities_client: ActivitiesClient
    ):
        """Test ActivitiesClient initialization."""
        assert activities_client.hotel_id == "TEST_HOTEL"
        assert activities_client.base_url == "https://api.test.com/v1"

    @pytest.mark.asyncio
    async def test_search_activities_success(self, activities_client: ActivitiesClient):
        """Test successful activities search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "activities": [
                {
                    "activityId": "ACT123",
                    "activityCode": "SPA001",
                    "activityName": "Spa Treatment",
                    "category": "spa",
                    "description": "Relaxing spa treatment",
                    "capacity": 10,
                    "durationMinutes": 60,
                    "price": "150.00",
                    "currencyCode": "USD",
                }
            ],
            "totalCount": 1,
        }
        content_data = {
            "activities": [
                {
                    "activityId": "ACT123",
                    "activityCode": "SPA001",
                    "activityName": "Spa Treatment",
                    "category": "spa",
                    "description": "Relaxing spa treatment",
                    "capacity": 10,
                    "durationMinutes": 60,
                    "price": "150.00",
                    "currencyCode": "USD",
                }
            ],
            "totalCount": 1,
        }
        mock_response.content = json.dumps(content_data).encode()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = (
            "https://api.test.com/v1/act/v1/hotels/TEST_HOTEL/activities"
        )
        mock_response.request = Mock(method="GET")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            activities_client._session = mock_client

            response = await activities_client.get_activities(category="spa")

            assert response.success is True
            assert len(response.data["activities"]) == 1
            assert response.data["activities"][0]["activityName"] == "Spa Treatment"

    @pytest.mark.asyncio
    async def test_get_activity_success(self, activities_client: ActivitiesClient):
        """Test successful activity retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "activityId": "ACT123",
            "activityCode": "SPA001",
            "activityName": "Spa Treatment",
            "category": "spa",
            "description": "Relaxing spa treatment",
            "capacity": 10,
            "durationMinutes": 60,
            "price": "150.00",
            "currencyCode": "USD",
        }
        content_data = {
            "activityId": "ACT123",
            "activityCode": "SPA001",
            "activityName": "Spa Treatment",
            "category": "spa",
            "description": "Relaxing spa treatment",
            "capacity": 10,
            "durationMinutes": 60,
            "price": "150.00",
            "currencyCode": "USD",
        }
        mock_response.content = json.dumps(content_data).encode()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = (
            "https://api.test.com/v1/act/v1/hotels/TEST_HOTEL/activities/ACT123"
        )
        mock_response.request = Mock(method="GET")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            activities_client._session = mock_client

            response = await activities_client.get_activity_details("ACT123")

            assert response.success is True
            assert response.data["activityName"] == "Spa Treatment"

    @pytest.mark.asyncio
    async def test_create_activity_booking_success(
        self, activities_client: ActivitiesClient
    ):
        """Test successful activity booking creation."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "bookingId": "BK123456",
            "activityId": "ACT123",
            "guestName": "John Doe",
            "bookingDate": "2024-12-15",
            "bookingTime": "14:00:00",
            "partySize": 2,
            "totalPrice": "300.00",
            "status": "confirmed",
            "paymentStatus": "pending",
            "createdBy": "test_user",
        }
        content_data = {
            "bookingId": "BK123456",
            "activityId": "ACT123",
            "guestName": "John Doe",
            "bookingDate": "2024-12-15",
            "bookingTime": "14:00:00",
            "partySize": 2,
            "totalPrice": "300.00",
            "status": "confirmed",
            "paymentStatus": "pending",
            "createdBy": "test_user",
        }
        mock_response.content = json.dumps(content_data).encode()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.test.com/v1/act/v1/hotels/TEST_HOTEL/bookings"
        mock_response.request = Mock(method="POST")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            activities_client._session = mock_client

            booking_data = {
                "bookingId": "BK123456",
                "activityId": "ACT123",
                "guestName": "John Doe",
                "bookingDate": "2024-12-15",
                "bookingTime": "14:00:00",
                "partySize": 2,
                "totalPrice": "300.00",
                "createdBy": "test_user",
            }

            response = await activities_client.create_activity_booking(booking_data)

            assert response.success is True
            assert response.data["bookingId"] == "BK123456"
            assert response.data["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_get_activity_schedule_success(
        self, activities_client: ActivitiesClient
    ):
        """Test successful activity schedule retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "scheduleId": "SCH123",
            "activityId": "ACT123",
            "scheduleDate": "2024-12-15",
            "timeSlots": [
                {"time": "10:00", "available": 5},
                {"time": "11:00", "available": 3},
                {"time": "14:00", "available": 8},
            ],
            "operatingHours": {"start": "09:00", "end": "18:00"},
            "closed": False,
            "maximumBookings": 20,
            "currentBookings": 5,
        }
        content_data = {
            "scheduleId": "SCH123",
            "activityId": "ACT123",
            "scheduleDate": "2024-12-15",
            "timeSlots": [
                {"time": "10:00", "available": 5},
                {"time": "11:00", "available": 3},
                {"time": "14:00", "available": 8},
            ],
            "operatingHours": {"start": "09:00", "end": "18:00"},
            "closed": False,
            "maximumBookings": 20,
            "currentBookings": 5,
        }
        mock_response.content = json.dumps(content_data).encode()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.test.com/v1/act/v1/hotels/TEST_HOTEL/activities/ACT123/schedule/2024-12-15"
        mock_response.request = Mock(method="GET")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            activities_client._session = mock_client

            from datetime import date

            response = await activities_client.get_activity_schedule(
                "ACT123", date(2024, 12, 15)
            )

            assert response.success is True
            assert response.data["scheduleId"] == "SCH123"
            assert len(response.data["timeSlots"]) == 3

    @pytest.mark.asyncio
    async def test_cancel_activity_booking_success(
        self, activities_client: ActivitiesClient
    ):
        """Test successful activity booking cancellation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bookingId": "BK123456",
            "status": "cancelled",
            "cancellationDate": "2024-12-10T10:30:00Z",
        }
        content_data = {
            "bookingId": "BK123456",
            "status": "cancelled",
            "cancellationDate": "2024-12-10T10:30:00Z",
        }
        mock_response.content = json.dumps(content_data).encode()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = (
            "https://api.test.com/v1/act/v1/hotels/TEST_HOTEL/bookings/BK123456/cancel"
        )
        mock_response.request = Mock(method="POST")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.request.return_value = mock_response

            activities_client._session = mock_client

            response = await activities_client.cancel_activity_booking("BK123456")

            assert response.success is True
            assert response.data["status"] == "cancelled"
