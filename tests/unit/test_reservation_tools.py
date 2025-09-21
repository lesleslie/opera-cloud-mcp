"""
Unit tests for reservation MCP tools.

Tests the FastMCP tool decorators and integration with ReservationsClient.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import FastMCP

from opera_cloud_mcp.clients.base_client import APIResponse
from opera_cloud_mcp.tools.reservation_tools import register_reservation_tools


@pytest.fixture
def mock_app():
    """Mock FastMCP app for testing."""
    app = FastMCP("test-app")
    return app


@pytest.fixture
def mock_reservations_client():
    """Mock ReservationsClient with common responses."""
    client = AsyncMock()

    # Mock successful search response
    client.search_reservations = AsyncMock(
        return_value=APIResponse(
            success=True,
            data={
                "reservations": [
                    {
                        "confirmationNumber": "TEST123",
                        "hotelId": "TEST_HOTEL",
                        "status": "CONFIRMED",
                    }
                ],
                "total_count": 1,
            },
            status_code=200,
        )
    )

    # Mock successful get response
    client.get_reservation = AsyncMock(
        return_value=APIResponse(
            success=True,
            data={"confirmationNumber": "TEST123", "status": "CONFIRMED"},
            status_code=200,
        )
    )

    # Mock successful create response
    client.create_reservation = AsyncMock(
        return_value=APIResponse(
            success=True,
            data={"confirmationNumber": "NEW123", "status": "CONFIRMED"},
            status_code=201,
        )
    )

    # Mock successful modify response
    client.modify_reservation = AsyncMock(
        return_value=APIResponse(
            success=True,
            data={"confirmationNumber": "MOD123", "status": "CONFIRMED"},
            status_code=200,
        )
    )

    # Mock successful cancel response
    client.cancel_reservation = AsyncMock(
        return_value=APIResponse(
            success=True,
            data={"confirmationNumber": "CAN123", "status": "CANCELED"},
            status_code=200,
        )
    )

    # Mock successful availability response
    client.check_availability = AsyncMock(
        return_value=APIResponse(
            success=True,
            data={"rooms": [{"roomType": "STANDARD", "available": 5}]},
            status_code=200,
        )
    )

    # Mock guest history response
    client.get_guest_reservation_history = AsyncMock(
        return_value=APIResponse(
            success=True,
            data={
                "reservations": [{"confirmationNumber": "HIST123"}],
                "total_count": 1,
            },
            status_code=200,
        )
    )

    return client


class TestReservationTools:
    """Test suite for reservation MCP tools."""

    async def test_register_reservation_tools(self, mock_app):
        """Test that reservation tools are registered correctly."""
        register_reservation_tools(mock_app)

        # Check that tools were registered using the correct FastMCP API
        tools = await mock_app.get_tools()
        tool_names = list(tools.keys())

        expected_tools = [
            "search_reservations",
            "get_reservation",
            "create_reservation",
            "modify_reservation",
            "cancel_reservation",
            "check_room_availability",
            "get_reservation_history",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names

    @patch("opera_cloud_mcp.tools.reservation_tools.create_reservations_client")
    @patch("opera_cloud_mcp.utils.client_factory.get_oauth_handler")
    async def test_search_reservations_tool(
        self,
        mock_get_oauth_handler,
        mock_create_client,
        mock_app,
        mock_reservations_client,
    ):
        """Test search_reservations MCP tool by calling it directly."""
        # Mock the OAuth handler to avoid real network calls
        from unittest.mock import Mock

        mock_oauth_handler = Mock()
        mock_oauth_handler.get_token = AsyncMock(return_value="mock_token")
        mock_oauth_handler.get_auth_header.return_value = {
            "Authorization": "Bearer mock_token"
        }
        mock_get_oauth_handler.return_value = mock_oauth_handler

        mock_create_client.return_value = mock_reservations_client

        # Import and call the function directly
        from opera_cloud_mcp.tools.reservation_tools import register_reservation_tools

        # Create a test app to register tools
        test_app = FastMCP("test")
        register_reservation_tools(test_app)

        # Get the tool function
        tools = await test_app.get_tools()
        search_tool = tools["search_reservations"]

        # Call the function directly
        result = await search_tool.fn(
            hotel_id="TEST_HOTEL",
            arrival_date="2024-12-15",
            departure_date="2024-12-18",
            guest_name="John Doe",
            limit=10,
        )

        assert result["success"] is True
        assert "reservations" in result
        assert len(result["reservations"]) == 1
        assert result["reservations"][0]["confirmationNumber"] == "TEST123"
        assert result["hotel_id"] == "TEST_HOTEL"

        # Verify client was called
        mock_reservations_client.search_reservations.assert_called_once()

    @patch("opera_cloud_mcp.tools.reservation_tools.create_reservations_client")
    @patch("opera_cloud_mcp.utils.client_factory.get_oauth_handler")
    async def test_get_reservation_tool(
        self,
        mock_get_oauth_handler,
        mock_create_client,
        mock_app,
        mock_reservations_client,
    ):
        """Test get_reservation MCP tool."""
        # Mock the OAuth handler to avoid real network calls
        from unittest.mock import Mock

        mock_oauth_handler = Mock()
        mock_oauth_handler.get_token = AsyncMock(return_value="mock_token")
        mock_oauth_handler.get_auth_header.return_value = {
            "Authorization": "Bearer mock_token"
        }
        mock_get_oauth_handler.return_value = mock_oauth_handler

        mock_create_client.return_value = mock_reservations_client

        test_app = FastMCP("test")
        register_reservation_tools(test_app)

        tools = await test_app.get_tools()
        get_tool = tools["get_reservation"]

        result = await get_tool.fn(
            confirmation_number="TEST123",
            hotel_id="TEST_HOTEL",
            include_history=True,
        )

        assert result["success"] is True
        assert result["reservation"]["confirmationNumber"] == "TEST123"

        # Verify client was called correctly
        mock_reservations_client.get_reservation.assert_called_once_with(
            confirmation_number="TEST123", include_charges=False, include_history=True
        )

    @patch("opera_cloud_mcp.tools.reservation_tools.create_reservations_client")
    @patch("opera_cloud_mcp.utils.client_factory.get_oauth_handler")
    async def test_check_room_availability_tool(
        self,
        mock_get_oauth_handler,
        mock_create_client,
        mock_app,
        mock_reservations_client,
    ):
        """Test check_room_availability MCP tool."""
        # Mock the OAuth handler to avoid real network calls
        from unittest.mock import Mock

        mock_oauth_handler = Mock()
        mock_oauth_handler.get_token = AsyncMock(return_value="mock_token")
        mock_oauth_handler.get_auth_header.return_value = {
            "Authorization": "Bearer mock_token"
        }
        mock_get_oauth_handler.return_value = mock_oauth_handler

        mock_create_client.return_value = mock_reservations_client

        test_app = FastMCP("test")
        register_reservation_tools(test_app)

        tools = await test_app.get_tools()
        availability_tool = tools["check_room_availability"]

        result = await availability_tool.fn(
            arrival_date="2024-12-15",
            departure_date="2024-12-18",
            hotel_id="TEST_HOTEL",
        )

        assert result["success"] is True
        assert "availability" in result
        assert len(result["availability"]["rooms"]) == 1
        assert result["availability"]["rooms"][0]["roomType"] == "STANDARD"

        # Verify client was called correctly
        mock_reservations_client.check_availability.assert_called_once()

    @patch("opera_cloud_mcp.tools.reservation_tools.create_reservations_client")
    @patch("opera_cloud_mcp.utils.client_factory.get_oauth_handler")
    async def test_get_reservation_history_tool(
        self,
        mock_get_oauth_handler,
        mock_create_client,
        mock_app,
        mock_reservations_client,
    ):
        """Test get_reservation_history MCP tool."""
        # Mock the OAuth handler to avoid real network calls
        from unittest.mock import Mock

        mock_oauth_handler = Mock()
        mock_oauth_handler.get_token = AsyncMock(return_value="mock_token")
        mock_oauth_handler.get_auth_header.return_value = {
            "Authorization": "Bearer mock_token"
        }
        mock_get_oauth_handler.return_value = mock_oauth_handler

        mock_create_client.return_value = mock_reservations_client

        test_app = FastMCP("test")
        register_reservation_tools(test_app)

        tools = await test_app.get_tools()
        history_tool = tools["get_reservation_history"]

        result = await history_tool.fn(
            guest_email="test@example.com",
            hotel_id="TEST_HOTEL",
            limit=5,
        )

        assert result["success"] is True
        assert "history" in result
        assert len(result["history"]) == 1
        assert result["history"][0]["confirmationNumber"] == "HIST123"
        assert result["hotel_id"] == "TEST_HOTEL"

        # Verify client was called correctly
        mock_reservations_client.get_guest_reservation_history.assert_called_once()

    @patch("opera_cloud_mcp.utils.client_factory.create_reservations_client")
    async def test_search_reservations_validation_error(
        self, mock_create_client, mock_app
    ):
        """Test search_reservations with validation error."""
        from opera_cloud_mcp.utils.exceptions import ValidationError

        test_app = FastMCP("test")
        register_reservation_tools(test_app)

        tools = await test_app.get_tools()
        search_tool = tools["search_reservations"]

        # Test with invalid hotel_id (empty string)
        with pytest.raises(ValidationError, match="hotel_id cannot be empty string"):
            await search_tool.fn(hotel_id="")

        # Test with invalid limit
        with pytest.raises(ValidationError, match="limit must be between 1 and 100"):
            await search_tool.fn(limit=0)

    @patch("opera_cloud_mcp.tools.reservation_tools.create_reservations_client")
    @patch("opera_cloud_mcp.utils.client_factory.get_oauth_handler")
    async def test_tool_error_handling(
        self, mock_get_oauth_handler, mock_create_client, mock_app
    ):
        """Test error handling in MCP tools."""
        # Mock the OAuth handler to avoid real network calls
        from unittest.mock import Mock

        mock_oauth_handler = Mock()
        mock_oauth_handler.get_token = AsyncMock(return_value="mock_token")
        mock_oauth_handler.get_auth_header.return_value = {
            "Authorization": "Bearer mock_token"
        }
        mock_get_oauth_handler.return_value = mock_oauth_handler
        # Mock client that returns failure responses
        failure_client = AsyncMock()
        failure_client.search_reservations.return_value = APIResponse(
            success=False, error="Hotel not found", status_code=404
        )
        mock_create_client.return_value = failure_client

        test_app = FastMCP("test")
        register_reservation_tools(test_app)

        tools = await test_app.get_tools()
        search_tool = tools["search_reservations"]

        result = await search_tool.fn(hotel_id="INVALID_HOTEL")

        assert result["success"] is False
        assert result["error"] == "Hotel not found"
        assert result["hotel_id"] == "INVALID_HOTEL"
