"""
Unit tests for FrontOfficeClient.

Tests all front office operations including check-in, check-out,
walk-in processing, and daily reports.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler
from opera_cloud_mcp.clients.api_clients.front_office import (
    ArrivalSummary,
    CheckInRequest,
    CheckOutRequest,
    DepartureSummary,
    FrontOfficeClient,
    WalkInRequest,
)
from opera_cloud_mcp.clients.base_client import APIResponse
from opera_cloud_mcp.config.settings import Settings
from opera_cloud_mcp.models.guest import GuestProfile


class TestFrontOfficeClient:
    """Test suite for FrontOfficeClient functionality."""

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
    def front_office_client(
        self, mock_oauth_handler: Mock, mock_settings: Mock
    ) -> FrontOfficeClient:
        """Create FrontOfficeClient instance for testing."""
        from unittest.mock import AsyncMock

        client = FrontOfficeClient(
            auth_handler=mock_oauth_handler,
            hotel_id="TEST_HOTEL",
            settings=mock_settings,
        )
        # Initialize the session with a mock
        mock_client = AsyncMock()
        mock_client.request = AsyncMock()
        client._session = mock_client
        return client

    @pytest.fixture
    def sample_guest_profile(self) -> GuestProfile:
        """Create sample guest profile for testing."""
        from datetime import datetime

        return GuestProfile(
            guestId="G123456",
            firstName="John",
            lastName="Doe",
            email="john.doe@test.com",
            phone="+1-555-123-4567",
            createdDate=datetime.utcnow(),
            createdBy="test_user",
        )

    @pytest.fixture
    def check_in_data(self) -> dict:
        """Sample check-in data."""
        return {
            "confirmationNumber": "CNF123456",
            "roomNumber": "101",
            "arrivalTime": "2024-12-01T15:00:00",
            "specialRequests": "Late checkout requested",
            "guestSignature": "signature_data",
            "idVerification": True,
            "creditCardAuth": "AUTH123456",
            "keyCardsIssued": 2,
        }

    @pytest.fixture
    def checkout_data(self) -> dict:
        """Sample checkout data."""
        return {
            "confirmationNumber": "CNF123456",
            "roomNumber": "101",
            "departureTime": "2024-12-03T11:00:00",
            "expressCheckout": False,
            "folioSettlement": True,
            "keyCardsReturned": 2,
            "roomDamages": None,
            "guestSatisfaction": 5,
        }

    @pytest.fixture
    def walk_in_data(self, sample_guest_profile: GuestProfile) -> dict:
        """Sample walk-in data."""
        return {
            "guest_profile": sample_guest_profile.model_dump(by_alias=True),
            "roomType": "KING",
            "nights": 2,
            "rateCode": "RACK",
            "specialRequests": "High floor preferred",
            "corporateAccount": None,
            "creditCardRequired": True,
        }

    @pytest.fixture
    def arrivals_report_data(self) -> dict:
        """Sample arrivals report data."""
        return {
            "date": "2024-12-01",
            "total_arrivals": 25,
            "checked_in": 20,
            "pending": 3,
            "no_shows": 2,
            "arrivals": [
                {
                    "confirmationNumber": "CNF123456",
                    "guestName": "John Doe",
                    "roomType": "KING",
                    "assignedRoom": "101",
                    "arrivalTime": "2024-12-01T15:00:00",
                    "nights": 2,
                    "rateCode": "RACK",
                    "rateAmount": 199.99,
                    "status": "confirmed",
                    "vipStatus": "Gold",
                    "specialRequests": "Late checkout",
                }
            ],
        }

    @pytest.fixture
    def departures_report_data(self) -> dict:
        """Sample departures report data."""
        return {
            "date": "2024-12-01",
            "total_departures": 18,
            "checked_out": 15,
            "pending": 3,
            "late_checkouts": 2,
            "departures": [
                {
                    "confirmationNumber": "CNF789012",
                    "guestName": "Jane Smith",
                    "roomNumber": "205",
                    "departureTime": "2024-12-01T11:30:00",
                    "checkoutStatus": "checked_out",
                    "folioBalance": 0.00,
                    "roomCharges": 399.98,
                    "incidentalCharges": 45.50,
                    "paymentMethod": "Credit Card",
                }
            ],
        }

    # Check-In Tests

    @pytest.mark.asyncio
    async def test_check_in_guest_success(
        self, front_office_client: FrontOfficeClient, check_in_data: dict
    ):
        """Test successful guest check-in."""
        from unittest.mock import patch

        # Mock the post method to return a successful response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data={
                    "confirmation_number": "CNF123456",
                    "room_number": "101",
                    "key_cards": ["KEY001", "KEY002"],
                    "checkin_time": "2024-12-01T15:00:00Z",
                },
                status_code=200,
            )

            response = await front_office_client.check_in_guest(check_in_data)

            assert response.success is True
            assert response.data["confirmation_number"] == "CNF123456"
            assert response.data["room_number"] == "101"
            assert len(response.data["key_cards"]) == 2

    @pytest.mark.asyncio
    async def test_check_in_guest_with_request_model(
        self, front_office_client: FrontOfficeClient, check_in_data: dict
    ):
        """Test check-in using CheckInRequest model."""
        from unittest.mock import patch

        check_in_request = CheckInRequest.model_validate(check_in_data)

        # Mock the post method to return a successful response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data={"confirmation_number": "CNF123456"},
                status_code=200,
            )

            response = await front_office_client.check_in_guest(check_in_request)

            assert response.success is True
            # Verify the correct endpoint was called
            expected_endpoint = "fof/v1/reservations/CNF123456/checkin"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert expected_endpoint in call_args[0][0]

    @pytest.mark.asyncio
    async def test_check_in_guest_room_not_ready(
        self, front_office_client: FrontOfficeClient, check_in_data: dict
    ):
        """Test check-in when room is not ready."""
        from unittest.mock import patch

        # Mock the post method to return an error response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=False,
                error="Room not ready for occupancy",
                status_code=409,
            )

            response = await front_office_client.check_in_guest(check_in_data)

            assert response.success is False
            assert "Room not ready" in response.error

    # Check-Out Tests

    @pytest.mark.asyncio
    async def test_check_out_guest_success(
        self, front_office_client: FrontOfficeClient, checkout_data: dict
    ):
        """Test successful guest check-out."""
        from unittest.mock import patch

        # Mock the post method to return a successful response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data={
                    "confirmation_number": "CNF123456",
                    "room_number": "101",
                    "checkout_time": "2024-12-03T11:00:00Z",
                    "final_folio": {
                        "total_charges": 445.48,
                        "payments": 445.48,
                        "balance": 0.00,
                    },
                },
                status_code=200,
            )

            response = await front_office_client.check_out_guest(checkout_data)

            assert response.success is True
            assert response.data["confirmation_number"] == "CNF123456"
            assert response.data["final_folio"]["balance"] == 0.00

    @pytest.mark.asyncio
    async def test_check_out_guest_with_outstanding_balance(
        self, front_office_client: FrontOfficeClient, checkout_data: dict
    ):
        """Test check-out with outstanding folio balance."""
        from unittest.mock import patch

        # Mock the post method to return an error response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=False,
                error="Outstanding balance must be settled",
                status_code=409,
                data={"balance": 125.75},
            )

            response = await front_office_client.check_out_guest(checkout_data)

            assert response.success is False
            assert "Outstanding balance" in response.error

    @pytest.mark.asyncio
    async def test_express_checkout(
        self, front_office_client: FrontOfficeClient, checkout_data: dict
    ):
        """Test express checkout functionality."""
        from unittest.mock import patch

        checkout_data["expressCheckout"] = True
        checkout_data["folioSettlement"] = False

        # Mock the post method to return a successful response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data={
                    "confirmation_number": "CNF123456",
                    "express_checkout": True,
                    "folio_sent_to_email": True,
                },
                status_code=200,
            )

            response = await front_office_client.check_out_guest(checkout_data)

            assert response.success is True
            assert response.data["express_checkout"] is True

    # Walk-In Tests

    @pytest.mark.asyncio
    async def test_process_walk_in_success(
        self, front_office_client: FrontOfficeClient, walk_in_data: dict
    ):
        """Test successful walk-in guest processing."""
        from unittest.mock import patch

        # Mock the post method to return a successful response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data={
                    "confirmation_number": "WLK789012",
                    "guest_id": "G789012",
                    "room_assigned": "305",
                    "rate_quoted": 179.99,
                },
                status_code=201,
            )

            response = await front_office_client.process_walk_in(walk_in_data)

            assert response.success is True
            assert response.data["confirmation_number"] == "WLK789012"
            assert response.data["room_assigned"] == "305"

    @pytest.mark.asyncio
    async def test_process_walk_in_no_availability(
        self, front_office_client: FrontOfficeClient, walk_in_data: dict
    ):
        """Test walk-in when no rooms available."""
        from unittest.mock import patch

        # Mock the post method to return an error response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=False,
                error="No rooms available for requested type",
                status_code=409,
                data={
                    "requested_type": "KING",
                    "alternative_types": ["QUEEN", "DOUBLE"],
                },
            )

            response = await front_office_client.process_walk_in(walk_in_data)

            assert response.success is False
            assert "No rooms available" in response.error

    # Room Assignment Tests

    @pytest.mark.asyncio
    async def test_assign_room_success(self, front_office_client: FrontOfficeClient):
        """Test successful room assignment."""
        from unittest.mock import patch

        # Mock the post method to return a successful response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data={
                    "confirmation_number": "CNF123456",
                    "room_number": "101",
                    "assigned_at": "2024-12-01T10:00:00Z",
                },
                status_code=200,
            )

            response = await front_office_client.assign_room(
                "CNF123456", "101", "Upgrade for VIP guest"
            )

            assert response.success is True
            assert response.data["room_number"] == "101"

    @pytest.mark.asyncio
    async def test_get_room_assignments(self, front_office_client: FrontOfficeClient):
        """Test getting room assignments for a date."""
        from datetime import date
        from unittest.mock import patch

        test_date = date(2024, 12, 1)

        # Mock the get method to return a successful response
        with patch.object(front_office_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data={
                    "date": "2024-12-01",
                    "assignments": [
                        {
                            "confirmation_number": "CNF123456",
                            "room_number": "101",
                            "guest_name": "John Doe",
                        }
                    ],
                },
                status_code=200,
            )

            response = await front_office_client.get_room_assignments(test_date)

            assert response.success is True
            assert response.data["date"] == "2024-12-01"
            assert len(response.data["assignments"]) == 1

    # Report Tests

    @pytest.mark.asyncio
    async def test_get_arrivals_report(
        self, front_office_client: FrontOfficeClient, arrivals_report_data: dict
    ):
        """Test getting arrivals report."""
        from datetime import date
        from unittest.mock import patch

        # Mock the get method to return the arrivals report data
        with patch.object(front_office_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=arrivals_report_data,
                status_code=200,
            )

            response = await front_office_client.get_arrivals_report(
                date(2024, 12, 1), status_filter="confirmed"
            )

            assert response.success is True
            assert response.data["total_arrivals"] == 25
            assert len(response.data["arrivals"]) == 1

    @pytest.mark.asyncio
    async def test_get_departures_report(
        self, front_office_client: FrontOfficeClient, departures_report_data: dict
    ):
        """Test getting departures report."""
        from datetime import date
        from unittest.mock import patch

        # Mock the get method to return the departures report data
        with patch.object(front_office_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=departures_report_data,
                status_code=200,
            )

            response = await front_office_client.get_departures_report(
                date(2024, 12, 1), checkout_status="pending"
            )

            assert response.success is True
            assert response.data["total_departures"] == 18
            assert len(response.data["departures"]) == 1

    @pytest.mark.asyncio
    async def test_get_occupancy_report(self, front_office_client: FrontOfficeClient):
        """Test getting occupancy report."""
        from datetime import date
        from unittest.mock import patch

        occupancy_data = {
            "date": "2024-12-01",
            "total_rooms": 100,
            "occupied_rooms": 85,
            "occupancy_percentage": 85.0,
            "by_room_type": {
                "KING": {"total": 40, "occupied": 35, "percentage": 87.5},
                "QUEEN": {"total": 35, "occupied": 30, "percentage": 85.7},
                "SUITE": {"total": 25, "occupied": 20, "percentage": 80.0},
            },
        }

        # Mock the get method to return the occupancy data
        with patch.object(front_office_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=occupancy_data,
                status_code=200,
            )

            response = await front_office_client.get_occupancy_report(date(2024, 12, 1))

            assert response.success is True
            assert response.data["occupancy_percentage"] == 85.0
            assert "by_room_type" in response.data

    @pytest.mark.asyncio
    async def test_get_no_show_report(self, front_office_client: FrontOfficeClient):
        """Test getting no-show report."""
        from unittest.mock import patch

        no_show_data = {
            "date": "2024-12-01",
            "total_no_shows": 3,
            "no_shows": [
                {
                    "confirmation_number": "CNF999999",
                    "guest_name": "No Show Guest",
                    "room_type": "KING",
                    "expected_arrival": "2024-12-01T15:00:00",
                }
            ],
        }

        # Mock the get method to return the no-show data
        with patch.object(front_office_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=no_show_data,
                status_code=200,
            )

            response = await front_office_client.get_no_show_report()

            assert response.success is True
            assert response.data["total_no_shows"] == 3

    # Folio Operations Tests

    @pytest.mark.asyncio
    async def test_get_guest_folio(self, front_office_client: FrontOfficeClient):
        """Test getting guest folio."""
        from unittest.mock import patch

        folio_data = {
            "confirmation_number": "CNF123456",
            "folio_type": "master",
            "charges": [
                {"date": "2024-12-01", "description": "Room Charge", "amount": 199.99},
                {"date": "2024-12-02", "description": "Restaurant", "amount": 45.50},
            ],
            "payments": [
                {"date": "2024-12-01", "description": "Credit Card", "amount": 245.49}
            ],
            "balance": 0.00,
        }

        # Mock the get method to return the folio data
        with patch.object(front_office_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=folio_data,
                status_code=200,
            )

            response = await front_office_client.get_guest_folio("CNF123456", "master")

            assert response.success is True
            assert response.data["balance"] == 0.00
            assert len(response.data["charges"]) == 2

    @pytest.mark.asyncio
    async def test_post_charge_to_room(self, front_office_client: FrontOfficeClient):
        """Test posting a charge to room folio."""
        from unittest.mock import patch

        charge_data = {
            "amount": 25.99,
            "description": "Mini Bar",
            "department": "F&B",
            "transaction_code": "MINIBAR",
        }

        # Mock the post method to return a successful response
        with patch.object(front_office_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data={
                    "transaction_id": "TXN789012",
                    "amount": 25.99,
                    "posted_at": "2024-12-01T18:30:00Z",
                },
                status_code=201,
            )

            response = await front_office_client.post_charge_to_room(
                "CNF123456", charge_data
            )

            assert response.success is True
            assert response.data["amount"] == 25.99

    # Batch Operations Tests

    @pytest.mark.asyncio
    async def test_batch_check_in_success(
        self, front_office_client: FrontOfficeClient, check_in_data: dict
    ):
        """Test successful batch check-in operation."""
        # Create multiple check-in requests
        check_in_requests = [
            CheckInRequest.model_validate(
                {**check_in_data, "confirmationNumber": f"CNF{i}"}
            )
            for i in range(12345, 12348)
        ]

        # Mock successful responses for all check-ins
        success_response = Mock(
            status_code=200,
            json=lambda: {"success": True, "data": {"confirmation_number": "CNF12345"}},
        )
        front_office_client._session.request.return_value = success_response

        response = await front_office_client.batch_check_in(check_in_requests)

        assert response.success is True
        assert response.data["total_processed"] == 3
        assert response.data["success_count"] == 3
        assert response.data["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_batch_check_in_partial_failure(
        self, front_office_client: FrontOfficeClient, check_in_data: dict
    ):
        """Test batch check-in with some failures."""
        check_in_requests = [
            CheckInRequest.model_validate(
                {**check_in_data, "confirmationNumber": f"CNF{i}"}
            )
            for i in range(12345, 12347)
        ]

        # Mock mixed responses
        responses = [
            Mock(
                status_code=200,
                json=lambda: {
                    "success": True,
                    "data": {"confirmation_number": "CNF12345"},
                },
            ),
            Mock(
                status_code=409,
                json=lambda: {"success": False, "error": "Room not ready"},
            ),
        ]

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            result = responses[call_count % len(responses)]
            call_count += 1
            return result

        front_office_client._session.request.side_effect = side_effect

        response = await front_office_client.batch_check_in(check_in_requests)

        assert response.success is False  # Not all succeeded
        assert response.data["total_processed"] == 2
        assert response.data["success_count"] == 1
        assert response.data["failure_count"] == 1

    # Convenience Methods Tests

    @pytest.mark.asyncio
    async def test_get_front_desk_summary(
        self,
        front_office_client: FrontOfficeClient,
        arrivals_report_data: dict,
        departures_report_data: dict,
    ):
        """Test comprehensive front desk summary."""
        occupancy_data = {"occupancy_percentage": 85.0}
        no_show_data = {"total_no_shows": 2}

        # Mock all report responses
        responses = [
            Mock(status_code=200, json=lambda: arrivals_report_data),
            Mock(status_code=200, json=lambda: departures_report_data),
            Mock(status_code=200, json=lambda: occupancy_data),
            Mock(status_code=200, json=lambda: no_show_data),
        ]

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            result = responses[call_count % len(responses)]
            call_count += 1
            return result

        front_office_client._session.request.side_effect = side_effect

        response = await front_office_client.get_front_desk_summary(date(2024, 12, 1))

        assert response.success is True
        assert response.data["date"] == "2024-12-01"
        assert response.data["arrivals"] is not None
        assert response.data["departures"] is not None
        assert response.data["occupancy"] is not None
        assert response.data["no_shows"] is not None

    @pytest.mark.asyncio
    async def test_search_in_house_guests(self, front_office_client: FrontOfficeClient):
        """Test searching for in-house guests."""
        search_criteria = {"guest_name": "John", "room_number": "101"}

        in_house_data = {
            "guests": [
                {
                    "guest_id": "G123456",
                    "guest_name": "John Doe",
                    "room_number": "101",
                    "checkin_date": "2024-12-01",
                    "checkout_date": "2024-12-03",
                }
            ]
        }

        front_office_client._session.request.return_value = Mock(
            status_code=200, json=lambda: in_house_data
        )

        response = await front_office_client.search_in_house_guests(search_criteria)

        assert response.success is True
        assert len(response.data["guests"]) == 1

        # Verify search criteria were passed correctly
        call_args = front_office_client._session.request.call_args
        params = call_args[1].get("params", {})
        assert params["guest_name"] == "John"
        assert params["room_number"] == "101"

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_network_error_handling(self, front_office_client: FrontOfficeClient):
        """Test handling of network errors."""
        from httpx import RequestError

        front_office_client._session.request.side_effect = RequestError(
            "Network connection failed"
        )

        with pytest.raises(RequestError):
            await front_office_client.get_arrivals_report()

    @pytest.mark.asyncio
    async def test_api_domain_configuration(
        self, front_office_client: FrontOfficeClient
    ):
        """Test that API domain is properly configured."""
        assert front_office_client.api_domain == "fof"

        # Verify domain is used in endpoint construction
        front_office_client._session.request.return_value = Mock(
            status_code=200, json=lambda: {"data": {}}
        )

        await front_office_client.get_arrivals_report()

        call_args = front_office_client._session.request.call_args
        url = call_args[1]["url"]
        assert "fof/v1/reports/arrivals" in url


class TestFrontOfficeModels:
    """Test suite for Front Office data models."""

    def test_checkin_request_model(self):
        """Test CheckInRequest model validation."""
        data = {
            "confirmationNumber": "CNF123456",
            "roomNumber": "101",
            "arrivalTime": "2024-12-01T15:00:00",
            "keyCardsIssued": 2,
        }

        request = CheckInRequest.model_validate(data)

        assert request.confirmation_number == "CNF123456"
        assert request.room_number == "101"
        assert request.key_cards_issued == 2
        assert isinstance(request.arrival_time, datetime)

    def test_checkin_request_defaults(self):
        """Test CheckInRequest model with defaults."""
        data = {"confirmationNumber": "CNF123456"}

        request = CheckInRequest.model_validate(data)

        assert request.confirmation_number == "CNF123456"
        assert request.room_number is None
        assert request.id_verification is True
        assert request.key_cards_issued == 1

    def test_checkout_request_model(self):
        """Test CheckOutRequest model validation."""
        data = {
            "confirmationNumber": "CNF123456",
            "roomNumber": "101",
            "departureTime": "2024-12-03T11:00:00",
            "guestSatisfaction": 5,
        }

        request = CheckOutRequest.model_validate(data)

        assert request.confirmation_number == "CNF123456"
        assert request.room_number == "101"
        assert request.guest_satisfaction == 5
        assert isinstance(request.departure_time, datetime)

    def test_walk_in_request_model(self):
        """Test WalkInRequest model validation."""
        from datetime import datetime

        guest_profile = GuestProfile(
            guestId="G123456",
            firstName="John",
            lastName="Doe",
            email="john.doe@test.com",
            createdDate=datetime.utcnow(),
            createdBy="test_user",
        )

        data = {
            "guest_profile": guest_profile,
            "roomType": "KING",
            "nights": 2,
            "rateCode": "RACK",
        }

        request = WalkInRequest.model_validate(data)

        assert request.guest_profile == guest_profile
        assert request.room_type == "KING"
        assert request.nights == 2
        assert request.credit_card_required is True

    def test_arrival_summary_model(self):
        """Test ArrivalSummary model."""
        data = {
            "confirmationNumber": "CNF123456",
            "guestName": "John Doe",
            "roomType": "KING",
            "nights": 2,
            "rateCode": "RACK",
            "rateAmount": 199.99,
            "status": "confirmed",
        }

        summary = ArrivalSummary.model_validate(data)

        assert summary.confirmation_number == "CNF123456"
        assert summary.guest_name == "John Doe"
        assert summary.rate_amount == 199.99

    def test_departure_summary_model(self):
        """Test DepartureSummary model."""
        data = {
            "confirmationNumber": "CNF789012",
            "guestName": "Jane Smith",
            "roomNumber": "205",
            "checkoutStatus": "checked_out",
            "folioBalance": 0.00,
            "roomCharges": 399.98,
            "incidentalCharges": 45.50,
        }

        summary = DepartureSummary.model_validate(data)

        assert summary.confirmation_number == "CNF789012"
        assert summary.guest_name == "Jane Smith"
        assert summary.folio_balance == 0.00
