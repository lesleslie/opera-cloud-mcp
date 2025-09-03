"""
Unit tests for operation MCP tools.

Tests the FastMCP tool registration for front office operations.
"""

from fastmcp import FastMCP

from opera_cloud_mcp.tools.operation_tools import register_operation_tools


class TestOperationTools:
    """Test suite for operation MCP tools."""

    async def test_register_operation_tools(self):
        """Test that operation tools are registered correctly."""
        app = FastMCP("test-app")
        register_operation_tools(app)

        # Check that tools were registered using the correct FastMCP API
        tools = await app.get_tools()
        tool_names = list(tools.keys())

        expected_tools = [
            "check_in_guest",
            "check_out_guest",
            "process_walk_in",
            "get_arrivals_report",
            "get_departures_report",
            "get_occupancy_report",
            "get_no_show_report",
            "assign_room",
            "get_in_house_guests",
            "get_front_desk_summary",
            "create_activity_booking",
            "create_dining_reservation",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, (
                f"Tool '{tool_name}' not found in registered tools: {tool_names}"
            )

        # Verify we got the expected number of tools
        assert len(tool_names) == len(expected_tools), (
            f"Expected {len(expected_tools)} tools, got {len(tool_names)}: {tool_names}"
        )

    async def test_operation_tool_functions_exist(self):
        """Test that operation tool functions can be accessed."""
        app = FastMCP("test-app")
        register_operation_tools(app)

        tools = await app.get_tools()

        # Test that each tool has the expected attributes
        for tool_name in ["check_in_guest", "check_out_guest", "get_arrivals_report"]:
            tool = tools[tool_name]
            assert tool.fn is not None, f"Tool {tool_name} should have a function"
            assert callable(tool.fn), f"Tool {tool_name} function should be callable"
            assert hasattr(tool, "parameters"), (
                f"Tool {tool_name} should have parameters"
            )
            assert tool.parameters is not None, (
                f"Tool {tool_name} parameters should not be None"
            )

    async def test_checkin_checkout_tools_parameters(self):
        """Test check-in and check-out tools have hotel_id parameters."""
        app = FastMCP("test-app")
        register_operation_tools(app)

        tools = await app.get_tools()

        # Test key operational tools have hotel_id parameter
        key_tools = ["check_in_guest", "check_out_guest", "assign_room"]
        for tool_name in key_tools:
            tool = tools[tool_name]
            assert "properties" in tool.parameters
            assert "hotel_id" in tool.parameters["properties"], (
                f"Tool {tool_name} should have hotel_id parameter"
            )
