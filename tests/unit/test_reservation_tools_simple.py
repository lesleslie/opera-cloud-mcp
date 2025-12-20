"""
Simplified unit tests for reservation MCP tools.

Tests the FastMCP tool registration without complex mocking.
"""

from fastmcp import FastMCP

from opera_cloud_mcp.tools.reservation_tools import register_reservation_tools


class TestReservationToolsSimple:
    """Simplified test suite for reservation MCP tools."""

    async def test_register_reservation_tools(self):
        """Test that reservation tools are registered correctly."""
        app = FastMCP("test-app")
        register_reservation_tools(app)

        # Check that tools were registered using the correct FastMCP API
        tools = await app.get_tools()
        tool_names = list(tools.keys())

        expected_tools = [
            "search_reservations",
            "get_reservation",
            "create_reservation",
            "modify_reservation",
            "cancel_reservation",
            "check_room_availability",
            "get_reservation_history",
            "bulk_create_reservations",
            "get_bulk_operation_status",
            "get_reservation_client_metrics",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, (
                f"Tool '{tool_name}' not found in registered tools: {tool_names}"
            )

        # Verify we got the expected number of tools
        assert len(tool_names) == len(expected_tools), (
            f"Expected {len(expected_tools)} tools, got {len(tool_names)}: {tool_names}"
        )

    async def test_tool_function_exists(self):
        """Test that tool functions can be accessed."""
        app = FastMCP("test-app")
        register_reservation_tools(app)

        tools = await app.get_tools()

        # Test that each tool has the expected attributes
        for tool_name in [
            "search_reservations",
            "get_reservation",
            "check_room_availability",
        ]:
            tool = tools[tool_name]
            assert tool.fn is not None, f"Tool {tool_name} should have a function"
            assert callable(tool.fn), f"Tool {tool_name} function should be callable"
            assert hasattr(tool, "parameters"), (
                f"Tool {tool_name} should have parameters"
            )
            assert tool.parameters is not None, (
                f"Tool {tool_name} parameters should not be None"
            )

    async def test_tool_parameters_structure(self):
        """Test that tools have proper parameter structures."""
        app = FastMCP("test-app")
        register_reservation_tools(app)

        tools = await app.get_tools()

        # Test search_reservations parameters
        search_tool = tools["search_reservations"]
        search_params = search_tool.parameters

        assert "properties" in search_params
        assert "hotel_id" in search_params["properties"]
        assert "arrival_date" in search_params["properties"]
        assert "departure_date" in search_params["properties"]
        assert "guest_name" in search_params["properties"]
        assert "limit" in search_params["properties"]

        # Test get_reservation parameters
        get_tool = tools["get_reservation"]
        get_params = get_tool.parameters

        assert "properties" in get_params
        assert "confirmation_number" in get_params["properties"]
        assert "hotel_id" in get_params["properties"]
        assert "include_folios" in get_params["properties"]
        assert "include_history" in get_params["properties"]

        # Check required fields
        assert "confirmation_number" in get_params.get("required", [])
