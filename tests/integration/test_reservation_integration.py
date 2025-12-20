"""
Integration tests for reservation management system.

Tests the complete integration between MCP tools, ReservationsClient,
and OPERA Cloud API mocking.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import FastMCP

from opera_cloud_mcp.clients.base_client import APIResponse
from opera_cloud_mcp.tools.reservation_tools import register_reservation_tools


@pytest.fixture
def mock_opera_cloud_api():
    """Mock OPERA Cloud API responses."""

    class MockOperaAPI:
        def __init__(self):
            self.reservations = {}
            self.search_results = []
            self.availability_data = {}

        def add_reservation(self, confirmation_number: str, reservation_data: dict):
            """Add a reservation to mock storage."""
            self.reservations[confirmation_number] = reservation_data

        def set_search_results(self, results: list):
            """Set search results for testing."""
            self.search_results = results

        def set_availability(self, room_type: str, available_rooms: int):
            """Set availability data."""
            if "roomTypes" not in self.availability_data:
                self.availability_data["roomTypes"] = []

            self.availability_data["roomTypes"].append(
                {"roomType": room_type, "availableRooms": available_rooms}
            )

    return MockOperaAPI()


@pytest.fixture
async def integrated_app(mock_opera_cloud_api):
    """Create FastMCP app with registered reservation tools."""
    app = FastMCP("test-reservation-app")

    # Mock the client creation to use our mock API
    def mock_client_context():
        client = AsyncMock()

        # Mock search operations
        client.search_reservations = AsyncMock(
            return_value=APIResponse(
                success=True,
                data={
                    "reservations": mock_opera_cloud_api.search_results,
                    "totalCount": len(mock_opera_cloud_api.search_results),
                },
                status_code=200,
            )
        )

        # Mock get operations
        def get_reservation_side_effect(confirmation_number, **kwargs):
            if confirmation_number in mock_opera_cloud_api.reservations:
                return APIResponse(
                    success=True,
                    data=mock_opera_cloud_api.reservations[confirmation_number],
                    status_code=200,
                )
            else:
                return APIResponse(
                    success=False, error="Reservation not found", status_code=404
                )

        client.get_reservation = AsyncMock(side_effect=get_reservation_side_effect)

        # Mock create operations
        def create_reservation_side_effect(request):
            confirmation_number = f"NEW{len(mock_opera_cloud_api.reservations) + 1:06d}"
            guest_profile = request.get("guestProfile", {})
            reservation_data = {
                "confirmationNumber": confirmation_number,
                "status": "CONFIRMED",
                "primaryGuest": {
                    "firstName": guest_profile.get("firstName"),
                    "lastName": guest_profile.get("lastName"),
                },
                "stayDetails": {
                    "arrivalDate": request.get("arrivalDate"),
                    "departureDate": request.get("departureDate"),
                    "roomType": request.get("roomType"),
                    "adults": request.get("adults"),
                },
            }

            # Add to mock storage
            mock_opera_cloud_api.add_reservation(confirmation_number, reservation_data)

            return APIResponse(success=True, data=reservation_data, status_code=201)

        client.create_reservation = AsyncMock(
            side_effect=create_reservation_side_effect
        )

        # Mock modify operations
        def modify_reservation_side_effect(confirmation_number, modifications):
            if confirmation_number in mock_opera_cloud_api.reservations:
                # Update reservation data
                reservation_data = mock_opera_cloud_api.reservations[
                    confirmation_number
                ].copy()
                reservation_data["status"] = "MODIFIED"
                mock_opera_cloud_api.reservations[confirmation_number] = (
                    reservation_data
                )

                return APIResponse(
                    success=True,
                    data={"reservation": reservation_data},
                    status_code=200,
                )
            else:
                return APIResponse(
                    success=False, error="Reservation not found", status_code=404
                )

        client.modify_reservation = AsyncMock(
            side_effect=modify_reservation_side_effect
        )

        # Mock cancel operations
        def cancel_reservation_side_effect(confirmation_number, cancellation):
            if confirmation_number in mock_opera_cloud_api.reservations:
                # Update reservation status
                reservation_data = mock_opera_cloud_api.reservations[
                    confirmation_number
                ].copy()
                reservation_data["status"] = "CANCELED"
                mock_opera_cloud_api.reservations[confirmation_number] = (
                    reservation_data
                )

                return APIResponse(
                    success=True,
                    data={"reservation": reservation_data, "charges": []},
                    status_code=200,
                )
            else:
                return APIResponse(
                    success=False, error="Reservation not found", status_code=404
                )

        client.cancel_reservation = AsyncMock(
            side_effect=cancel_reservation_side_effect
        )

        # Mock availability operations
        client.check_availability = AsyncMock(
            return_value=APIResponse(
                success=True,
                data=mock_opera_cloud_api.availability_data,
                status_code=200,
            )
        )

        client.__aenter__.return_value = client
        client.__aexit__.return_value = None

        return client

    with patch(
        "opera_cloud_mcp.tools.reservation_tools._get_reservations_client",
        side_effect=lambda hotel_id: mock_client_context(),
    ):
        register_reservation_tools(app)
        yield app


class TestReservationIntegration:
    """Integration test suite for reservation management."""

    async def test_complete_reservation_lifecycle(
        self, integrated_app, mock_opera_cloud_api
    ):
        """Test complete reservation lifecycle from creation to cancellation."""
        app = integrated_app
        tools = await app.get_tools()

        # Set up availability
        mock_opera_cloud_api.set_availability("DELUXE", 3)

        # Step 1: Check availability
        availability_tool = tools["check_room_availability"]
        availability_result = await availability_tool.fn(
            hotel_id="INTEGRATION_HOTEL",
            arrival_date="2024-12-15",
            departure_date="2024-12-18",
            adults=2,
            room_type="DELUXE",
        )

        assert availability_result["success"] is True
        assert (
            availability_result["availability"]["roomTypes"][0]["availableRooms"] == 3
        )

        # Step 2: Create reservation
        create_tool = tools["create_reservation"]
        create_result = await create_tool.fn(
            hotel_id="INTEGRATION_HOTEL",
            guest_profile={
                "firstName": "Jane",
                "lastName": "Smith",
                "email": "jane.smith@corp.com",
                "phoneNumber": "+1-555-0123",
            },
            arrival_date="2024-12-15",
            departure_date="2024-12-18",
            room_type="DELUXE",
            rate_code="CORPORATE",
            adults=2,
            children=0,
            special_requests="Late checkout requested",
        )

        assert create_result["success"] is True
        confirmation_number = create_result["reservation"]["confirmationNumber"]
        assert confirmation_number.startswith("NEW")

        # Step 3: Retrieve the created reservation
        get_tool = tools["get_reservation"]
        get_result = await get_tool.fn(
            hotel_id="INTEGRATION_HOTEL", confirmation_number=confirmation_number
        )

        assert get_result["success"] is True
        retrieved_reservation = get_result["reservation"]
        assert retrieved_reservation["confirmationNumber"] == confirmation_number
        assert retrieved_reservation["status"] == "CONFIRMED"
        assert retrieved_reservation["primaryGuest"]["firstName"] == "Jane"
        assert retrieved_reservation["primaryGuest"]["lastName"] == "Smith"

        # Step 4: Search for the reservation
        search_tool = tools["search_reservations"]

        # Add reservation to search results
        mock_opera_cloud_api.set_search_results([retrieved_reservation])

        search_result = await search_tool.fn(
            hotel_id="INTEGRATION_HOTEL", guest_name="Jane Smith"
        )

        assert search_result["success"] is True
        assert len(search_result["reservations"]) == 1
        found_reservation = search_result["reservations"][0]
        assert found_reservation["confirmationNumber"] == confirmation_number

        # Step 5: Modify the reservation
        modify_tool = tools["modify_reservation"]
        modify_result = await modify_tool.fn(
            hotel_id="INTEGRATION_HOTEL",
            confirmation_number=confirmation_number,
            adults=3,
            special_requests="Late checkout requested",
        )

        assert modify_result["success"] is True

        # Step 6: Cancel the reservation
        cancel_tool = tools["cancel_reservation"]
        cancel_result = await cancel_tool.fn(
            hotel_id="INTEGRATION_HOTEL",
            confirmation_number=confirmation_number,
            cancellation_reason="Travel plans changed",
        )

        assert cancel_result["success"] is True
        assert (
            cancel_result["cancellation_details"]["reservation"]["status"] == "CANCELED"
        )

        # Verify final status
        final_get_result = await get_tool.fn(
            hotel_id="INTEGRATION_HOTEL", confirmation_number=confirmation_number
        )

        assert final_get_result["success"] is True
        final_reservation = final_get_result["reservation"]
        assert final_reservation["status"] == "CANCELED"

    async def test_bulk_reservation_workflow(self, integrated_app):
        """Test bulk reservation creation workflow."""
        app = integrated_app
        tools = await app.get_tools()

        # Prepare bulk reservation data
        reservations_data = [
            {
                "guest_first_name": "Alice",
                "guest_last_name": "Johnson",
                "arrival_date": "2024-12-15",
                "departure_date": "2024-12-17",
                "room_type": "STANDARD",
                "rate_code": "RACK",
                "adults": 1,
                "children": 0,
            },
            {
                "guest_first_name": "Bob",
                "guest_last_name": "Wilson",
                "arrival_date": "2024-12-16",
                "departure_date": "2024-12-19",
                "room_type": "DELUXE",
                "rate_code": "CORPORATE",
                "adults": 2,
                "children": 1,
            },
        ]

        # Mock bulk operations
        bulk_create_tool = tools["bulk_create_reservations"]

        # Mock the bulk client operations
        mock_client = AsyncMock()
        mock_client.bulk_create_reservations.return_value = APIResponse(
            success=True,
            data={"jobId": "BULK12345", "status": "PENDING"},
            status_code=202,
        )
        mock_client.get_bulk_operation_status.return_value = APIResponse(
            success=True,
            data={
                "jobId": "BULK12345",
                "status": "COMPLETED",
                "totalReservations": 2,
                "processedCount": 2,
                "successCount": 2,
                "errorCount": 0,
            },
            status_code=200,
        )
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch(
            "opera_cloud_mcp.tools.reservation_tools._get_reservations_client",
            return_value=mock_client,
        ):
            # Start bulk creation
            bulk_result = await bulk_create_tool.fn(
                hotel_id="INTEGRATION_HOTEL", reservations_data=reservations_data
            )

            assert bulk_result["success"] is True
            assert "BULK12345" in bulk_result["message"]

            # Check bulk operation status
            status_tool = tools["get_bulk_operation_status"]
            status_result = await status_tool.fn(
                hotel_id="INTEGRATION_HOTEL", job_id="BULK12345"
            )

            assert status_result["success"] is True
            assert "COMPLETED" in status_result["message"]
            assert "(2/2 processed)" in status_result["message"]

    async def test_error_handling_integration(self, integrated_app):
        """Test error handling across the integrated system."""
        tools = await integrated_app.get_tools()

        # Test getting non-existent reservation
        get_tool = tools["get_reservation"]
        get_result = await get_tool.fn(
            hotel_id="INTEGRATION_HOTEL", confirmation_number="NONEXISTENT"
        )

        assert get_result["success"] is False
        assert "Reservation not found" in get_result["error"]

        # Test modifying non-existent reservation
        modify_tool = tools["modify_reservation"]
        modify_result = await modify_tool.fn(
            hotel_id="INTEGRATION_HOTEL", confirmation_number="NONEXISTENT", adults=2
        )

        assert modify_result["success"] is False
        assert "Reservation not found" in modify_result["error"]

        # Test canceling non-existent reservation
        cancel_tool = tools["cancel_reservation"]
        cancel_result = await cancel_tool.fn(
            hotel_id="INTEGRATION_HOTEL", confirmation_number="NONEXISTENT"
        )

        assert cancel_result["success"] is False
        assert "Reservation not found" in cancel_result["error"]

    async def test_validation_integration(self, integrated_app):
        """Test validation errors in the integrated system."""
        tools = await integrated_app.get_tools()
        from opera_cloud_mcp.utils.exceptions import ValidationError

        # Test create reservation with invalid date
        create_tool = tools["create_reservation"]
        with pytest.raises(ValidationError):
            await create_tool.fn(
                hotel_id="INTEGRATION_HOTEL",
                guest_profile={
                    "firstName": "John",
                    "lastName": "Doe",
                    "email": "john.doe@example.com",
                    "phoneNumber": "+1-555-0124",
                },
                arrival_date="invalid-date",
                departure_date="2024-12-18",
                room_type="STANDARD",
                rate_code="RACK",
            )

        # Test search with invalid confirmation number format
        search_tool = tools["search_reservations"]
        with pytest.raises(ValidationError):
            await search_tool.fn(
                hotel_id="INTEGRATION_HOTEL", confirmation_number="invalid"
            )

    async def test_client_metrics_integration(self, integrated_app):
        """Test client metrics collection in integrated environment."""
        tools = await integrated_app.get_tools()
        mock_client = AsyncMock()
        mock_client.get_metrics.return_value = {
            "operation_metrics": {
                "searches": 5,
                "creates": 3,
                "retrievals": 8,
                "modifications": 2,
                "cancellations": 1,
            },
            "health_status": "healthy",
            "last_operation": "2024-12-01T15:30:00Z",
        }

        with patch(
            "opera_cloud_mcp.tools.reservation_tools._get_reservations_client",
            return_value=mock_client,
        ):
            metrics_tool = tools["get_reservation_client_metrics"]
            metrics_result = await metrics_tool.fn(hotel_id="INTEGRATION_HOTEL")

            assert metrics_result["success"] is True
            assert metrics_result["data"]["hotel_id"] == "INTEGRATION_HOTEL"
            assert "operation_metrics" in metrics_result["data"]["metrics"]
            assert (
                metrics_result["data"]["metrics"]["operation_metrics"]["searches"] == 5
            )
