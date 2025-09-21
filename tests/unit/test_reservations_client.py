"""
Unit tests for ReservationsClient.

Tests the reservation client functionality with mocked OPERA Cloud API responses.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opera_cloud_mcp.clients.api_clients.reservations import (
    ReservationCancelRequest,
    ReservationCreateRequest,
    ReservationModifyRequest,
    ReservationsClient,
    ReservationSearchCriteria,
)
from opera_cloud_mcp.clients.base_client import APIResponse
from opera_cloud_mcp.models.common import Contact
from opera_cloud_mcp.models.reservation import (
    GuestProfile,
    RoomStayDetails,
)
from opera_cloud_mcp.utils.exceptions import (
    ValidationError,
)


@pytest.fixture
def mock_auth_handler():
    """Mock authentication handler."""
    handler = AsyncMock()
    handler.get_token.return_value = "mock_access_token"
    return handler


@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = MagicMock()
    settings.opera_base_url = "https://api.opera.cloud"
    settings.opera_api_version = "v1"
    settings.opera_environment = "test"
    return settings


@pytest.fixture
def reservations_client(mock_auth_handler, mock_settings):
    """Create a ReservationsClient instance with mocked dependencies."""
    return ReservationsClient(
        auth_handler=mock_auth_handler, hotel_id="TEST_HOTEL", settings=mock_settings
    )


@pytest.fixture
def sample_guest():
    """Sample guest profile for testing."""
    return GuestProfile(
        firstName="John",
        lastName="Doe",
        contact=Contact(email="john.doe@example.com", phone="+1-555-123-4567"),
    )


@pytest.fixture
def sample_room_stay():
    """Sample room stay for testing."""
    return RoomStayDetails(
        arrivalDate=date(2024, 12, 15),
        departureDate=date(2024, 12, 18),
        roomType="STANDARD",
        rateCode="RACK",
        adults=2,
        children=0,
    )


@pytest.fixture
def sample_reservation_data():
    """Sample reservation response data."""
    return {
        "reservation": {
            "confirmationNumber": "ABC123456",
            "hotelId": "TEST_HOTEL",
            "status": "CONFIRMED",
            "primaryGuest": {
                "firstName": "John",
                "lastName": "Doe",
                "contact": {
                    "email": "john.doe@example.com",
                    "phone": "+1-555-123-4567",
                },
            },
            "stayDetails": {
                "arrivalDate": "2024-12-15",
                "departureDate": "2024-12-18",
                "roomType": "STANDARD",
                "rateCode": "RACK",
                "adults": 2,
                "children": 0,
            },
            "createdDate": "2024-12-01T10:00:00Z",
            "modifiedDate": "2024-12-01T10:00:00Z",
        }
    }


class TestReservationsClient:
    """Test suite for ReservationsClient."""

    async def test_init_with_metrics(self, reservations_client):
        """Test client initialization includes metrics tracking."""
        assert reservations_client._operation_metrics is not None
        assert reservations_client._operation_metrics["searches"] == 0
        assert reservations_client._operation_metrics["creates"] == 0
        assert reservations_client._operation_metrics["retrievals"] == 0
        assert reservations_client._operation_metrics["modifications"] == 0
        assert reservations_client._operation_metrics["cancellations"] == 0

    async def test_get_metrics(self, reservations_client):
        """Test metrics retrieval."""
        with patch.object(
            reservations_client, "get_health_status", return_value={"healthy": True}
        ):
            metrics = reservations_client.get_metrics()

            assert "operation_metrics" in metrics
            assert metrics["operation_metrics"]["searches"] == 0

    async def test_search_reservations_with_criteria_object(self, reservations_client):
        """Test search with ReservationSearchCriteria object."""
        criteria = ReservationSearchCriteria(
            arrival_date="2024-12-15",
            departure_date="2024-12-18",
            guest_name="John Doe",
            limit=20,
        )

        mock_response = APIResponse(
            success=True, data={"reservations": [], "totalCount": 0}, status_code=200
        )

        with patch.object(
            reservations_client, "get", return_value=mock_response
        ) as mock_get:
            response = await reservations_client.search_reservations(criteria)

            assert response.success
            assert mock_get.called

            # Check that the correct endpoint was called
            call_args = mock_get.call_args
            assert call_args[0][0] == "rsv/v1/hotels/TEST_HOTEL/reservations"

            # Check parameters were built correctly
            params = call_args[1]["params"]
            assert params["arrivalDate"] == "2024-12-15"
            assert params["departureDate"] == "2024-12-18"
            assert params["guestName"] == "John Doe"
            assert params["limit"] == 20

    async def test_search_reservations_with_kwargs(self, reservations_client):
        """Test search with keyword arguments."""
        mock_response = APIResponse(
            success=True, data={"reservations": [], "totalCount": 0}, status_code=200
        )

        with patch.object(reservations_client, "get", return_value=mock_response):
            response = await reservations_client.search_reservations(
                arrival_date="2024-12-15", guest_name="Jane Smith", limit=5
            )

            assert response.success
            # Operation metric should be incremented
            assert reservations_client._operation_metrics["searches"] == 1

    async def test_search_reservations_validation_error(self, reservations_client):
        """Test search with invalid criteria raises ValidationError."""
        with pytest.raises(ValidationError):
            await reservations_client.search_reservations(arrival_date="invalid-date")

    async def test_get_reservation_success(
        self, reservations_client, sample_reservation_data
    ):
        """Test successful reservation retrieval."""
        mock_response = APIResponse(
            success=True, data=sample_reservation_data, status_code=200
        )

        with patch.object(
            reservations_client, "get", return_value=mock_response
        ) as mock_get:
            response = await reservations_client.get_reservation(
                "ABC123456", include_history=True, include_charges=False
            )

            assert response.success
            assert response.data == sample_reservation_data

            # Check correct endpoint and parameters
            call_args = mock_get.call_args
            assert call_args[0][0] == "rsv/v1/hotels/TEST_HOTEL/reservations/ABC123456"
            assert call_args[1]["params"]["includeHistory"] == "true"
            assert "includeCharges" not in call_args[1]["params"]

            # Operation metric should be incremented
            assert reservations_client._operation_metrics["retrievals"] == 1

    async def test_get_reservation_invalid_confirmation_number(
        self, reservations_client
    ):
        """Test get reservation with invalid confirmation number."""
        with pytest.raises(ValidationError):
            await reservations_client.get_reservation("invalid")

    async def test_create_reservation_success(
        self, reservations_client, sample_guest, sample_room_stay
    ):
        """Test successful reservation creation."""
        request = ReservationCreateRequest(
            guest=sample_guest,
            room_stay=sample_room_stay,
            special_requests="Late checkout",
            guarantee_code="CC",
        )

        mock_response = APIResponse(
            success=True,
            data={"reservation": {"confirmationNumber": "NEW123456"}},
            status_code=201,
        )

        with patch.object(
            reservations_client, "post", return_value=mock_response
        ) as mock_post:
            response = await reservations_client.create_reservation(request)

            assert response.success
            assert mock_post.called

            # Check endpoint and data transformation
            call_args = mock_post.call_args
            assert call_args[0][0] == "rsv/v1/hotels/TEST_HOTEL/reservations"

            # Check transformed data
            json_data = call_args[1]["json_data"]
            assert json_data["reservationType"] == "INDIVIDUAL"
            assert json_data["primaryGuest"]["firstName"] == "John"
            assert json_data["primaryGuest"]["lastName"] == "Doe"
            assert json_data["stayDetails"]["roomType"] == "STANDARD"
            assert json_data["specialRequests"] == "Late checkout"

            # Operation metric should be incremented
            assert reservations_client._operation_metrics["creates"] == 1

    async def test_create_reservation_with_dict_input(
        self, reservations_client, sample_guest, sample_room_stay
    ):
        """Test reservation creation with dictionary input."""
        request_dict = {
            "guest": sample_guest,
            "room_stay": sample_room_stay,
            "comments": "VIP guest",
        }

        mock_response = APIResponse(
            success=True,
            data={"reservation": {"confirmationNumber": "DICT123456"}},
            status_code=201,
        )

        with patch.object(reservations_client, "post", return_value=mock_response):
            response = await reservations_client.create_reservation(request_dict)

            assert response.success
            assert reservations_client._operation_metrics["creates"] == 1

    async def test_modify_reservation_success(
        self, reservations_client, sample_room_stay
    ):
        """Test successful reservation modification."""
        modification = ReservationModifyRequest(
            room_stay=sample_room_stay, special_requests="Updated requests"
        )

        mock_response = APIResponse(
            success=True,
            data={"reservation": {"confirmationNumber": "MOD123456"}},
            status_code=200,
        )

        with patch.object(
            reservations_client, "put", return_value=mock_response
        ) as mock_put:
            response = await reservations_client.modify_reservation(
                "MOD123456", modification
            )

            assert response.success
            assert mock_put.called

            # Check endpoint
            call_args = mock_put.call_args
            assert call_args[0][0] == "rsv/v1/hotels/TEST_HOTEL/reservations/MOD123456"

            # Check data transformation
            json_data = call_args[1]["json_data"]
            assert json_data["specialRequests"] == "Updated requests"
            assert "stayDetails" in json_data

            # Operation metric should be incremented
            assert reservations_client._operation_metrics["modifications"] == 1

    async def test_cancel_reservation_success(self, reservations_client):
        """Test successful reservation cancellation."""
        cancellation = ReservationCancelRequest(
            reason="Guest illness", charge_penalty=True, notify_guest=True
        )

        mock_response = APIResponse(
            success=True,
            data={
                "reservation": {
                    "confirmationNumber": "CAN123456",
                    "status": "CANCELED",
                },
                "charges": [{"amount": 50.0, "description": "Cancellation fee"}],
            },
            status_code=200,
        )

        with patch.object(
            reservations_client, "post", return_value=mock_response
        ) as mock_post:
            response = await reservations_client.cancel_reservation(
                "CAN123456", cancellation
            )

            assert response.success
            assert mock_post.called

            # Check endpoint
            call_args = mock_post.call_args
            assert (
                call_args[0][0]
                == "rsv/v1/hotels/TEST_HOTEL/reservations/CAN123456/cancel"
            )

            # Check data transformation
            json_data = call_args[1]["json_data"]
            assert json_data["reason"] == "Guest illness"
            assert json_data["chargePenalty"]
            assert json_data["notifyGuest"]

            # Operation metric should be incremented
            assert reservations_client._operation_metrics["cancellations"] == 1

    async def test_cancel_reservation_with_string_reason(self, reservations_client):
        """Test cancellation with string reason input."""
        mock_response = APIResponse(
            success=True,
            data={
                "reservation": {"confirmationNumber": "STR123456", "status": "CANCELED"}
            },
            status_code=200,
        )

        with patch.object(
            reservations_client, "post", return_value=mock_response
        ) as mock_post:
            response = await reservations_client.cancel_reservation(
                "STR123456", "Personal reasons"
            )

            assert response.success

            # Check that string was converted to proper request
            json_data = mock_post.call_args[1]["json_data"]
            assert json_data["reason"] == "Personal reasons"
            assert not json_data["chargePenalty"]  # Default value
            assert json_data["notifyGuest"]  # Default value

    async def test_get_availability_success(self, reservations_client):
        """Test successful availability check."""
        mock_response = APIResponse(
            success=True,
            data={
                "roomTypes": [
                    {"roomType": "STANDARD", "availableRooms": 5},
                    {"roomType": "DELUXE", "availableRooms": 2},
                ]
            },
            status_code=200,
        )

        with patch.object(
            reservations_client, "get", return_value=mock_response
        ) as mock_get:
            response = await reservations_client.get_availability(
                arrival_date="2024-12-15",
                departure_date="2024-12-18",
                adults=2,
                children=1,
                room_type="STANDARD",
            )

            assert response.success

            # Check endpoint and parameters
            call_args = mock_get.call_args
            assert call_args[0][0] == "rsv/v1/hotels/TEST_HOTEL/availability"

            params = call_args[1]["params"]
            assert params["arrivalDate"] == "2024-12-15"
            assert params["departureDate"] == "2024-12-18"
            assert params["adults"] == 2
            assert params["children"] == 1
            assert params["roomType"] == "STANDARD"

    async def test_get_availability_with_date_objects(self, reservations_client):
        """Test availability check with date objects."""
        mock_response = APIResponse(
            success=True, data={"roomTypes": []}, status_code=200
        )

        with patch.object(
            reservations_client, "get", return_value=mock_response
        ) as mock_get:
            response = await reservations_client.get_availability(
                arrival_date=date(2024, 12, 15), departure_date=date(2024, 12, 18)
            )

            assert response.success

            # Check that dates were converted to strings
            params = mock_get.call_args[1]["params"]
            assert params["arrivalDate"] == "2024-12-15"
            assert params["departureDate"] == "2024-12-18"

    async def test_bulk_create_reservations_success(
        self, reservations_client, sample_guest, sample_room_stay
    ):
        """Test successful bulk reservation creation."""
        reservations = [
            ReservationCreateRequest(guest=sample_guest, room_stay=sample_room_stay)
        ]

        mock_response = APIResponse(
            success=True,
            data={"jobId": "BULK123", "status": "PENDING"},
            status_code=202,
        )

        with patch.object(
            reservations_client, "post", return_value=mock_response
        ) as mock_post:
            response = await reservations_client.bulk_create_reservations(reservations)

            assert response.success

            # Check endpoint
            call_args = mock_post.call_args
            assert call_args[0][0] == "rsvasync/v1/hotels/TEST_HOTEL/reservations/bulk"

            # Check data structure
            json_data = call_args[1]["json_data"]
            assert "reservations" in json_data
            assert len(json_data["reservations"]) == 1

    async def test_get_bulk_operation_status_success(self, reservations_client):
        """Test successful bulk operation status retrieval."""
        mock_response = APIResponse(
            success=True,
            data={
                "jobId": "BULK123",
                "status": "COMPLETED",
                "processedCount": 10,
                "totalReservations": 10,
                "successCount": 9,
                "errorCount": 1,
            },
            status_code=200,
        )

        with patch.object(
            reservations_client, "get", return_value=mock_response
        ) as mock_get:
            response = await reservations_client.get_bulk_operation_status("BULK123")

            assert response.success

            # Check endpoint
            call_args = mock_get.call_args
            assert call_args[0][0] == "rsvasync/v1/hotels/TEST_HOTEL/jobs/BULK123"

    async def test_data_transformations(self, reservations_client):
        """Test that data transformations are applied correctly."""
        # Test reservation list transformation
        raw_data = [{"confirmationId": "123", "hotelCode": "HTL"}]
        transformed = reservations_client._transform_reservation_list(raw_data)

        assert len(transformed) == 1
        assert transformed[0]["confirmationNumber"] == "123"
        assert transformed[0]["hotelId"] == "HTL"

    async def test_build_search_params(self, reservations_client):
        """Test search parameter building."""
        criteria = ReservationSearchCriteria(
            arrival_date="2024-12-15", guest_name="John Doe", limit=25, offset=10
        )

        params = reservations_client._build_search_params(criteria)

        assert params["arrivalDate"] == "2024-12-15"
        assert params["guestName"] == "John Doe"
        assert params["limit"] == 25
        assert params["offset"] == 10
        assert "departureDate" not in params  # Should not include None values

    async def test_error_handling_api_failure(self, reservations_client):
        """Test error handling when API calls fail."""
        mock_response = APIResponse(success=False, error="API Error", status_code=500)

        with patch.object(reservations_client, "get", return_value=mock_response):
            response = await reservations_client.search_reservations()

            assert not response.success
            assert response.error == "API Error"

    async def test_context_manager_support(self, reservations_client):
        """Test that client can be used as async context manager."""
        async with reservations_client as client:
            assert client is reservations_client
            # Context manager should handle resource cleanup
