"""
Unit tests for room MCP tools.

Tests the FastMCP tool registration for room and inventory management functionality.
"""

from fastmcp import FastMCP

from opera_cloud_mcp.tools.room_tools import register_room_tools


class TestRoomTools:
    """Test suite for room MCP tools."""

    async def test_register_room_tools(self):
        """Test that room tools are registered correctly."""
        app = FastMCP("test-app")
        register_room_tools(app)

        # Check that tools were registered using the correct FastMCP API
        tools = await app.get_tools()
        tool_names = list(tools.keys())

        expected_tools = [
            "get_room_status",
            "update_room_status",
            "check_room_availability",
            "get_housekeeping_tasks",
            "create_housekeeping_task",
            "complete_housekeeping_task",
            "get_inventory_levels",
            "update_inventory",
            "get_room_inspection",
            "create_maintenance_request",
            "get_inventory_status",
            "update_inventory_stock",
            "get_cleaning_schedule",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, (
                f"Tool '{tool_name}' not found in registered tools: {tool_names}"
            )

        # Verify we got the expected number of tools
        assert len(tool_names) == len(expected_tools), (
            f"Expected {len(expected_tools)} tools, got {len(tool_names)}: {tool_names}"
        )

    async def test_room_tool_functions_exist(self):
        """Test that room tool functions can be accessed."""
        app = FastMCP("test-app")
        register_room_tools(app)

        tools = await app.get_tools()

        # Test that each tool has the expected attributes
        for tool_name in [
            "get_room_status",
            "update_room_status",
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

    async def test_room_status_tools_parameters(self):
        """Test room status tools have proper parameter structures."""
        app = FastMCP("test-app")
        register_room_tools(app)

        tools = await app.get_tools()

        # Test get_room_status parameters
        get_tool = tools["get_room_status"]
        get_params = get_tool.parameters

        assert "properties" in get_params
        assert "hotel_id" in get_params["properties"]

        # Test update_room_status parameters
        update_tool = tools["update_room_status"]
        update_params = update_tool.parameters

        assert "properties" in update_params
        assert "room_number" in update_params["properties"]
        assert "new_status" in update_params["properties"]
        assert "hotel_id" in update_params["properties"]

        # Check required fields
        required_fields = update_params.get("required", [])
        assert "room_number" in required_fields
        assert "new_status" in required_fields

    async def test_housekeeping_tools_parameters(self):
        """Test housekeeping tools have proper parameter structures."""
        app = FastMCP("test-app")
        register_room_tools(app)

        tools = await app.get_tools()

        # Test get_housekeeping_tasks parameters
        get_tasks_tool = tools["get_housekeeping_tasks"]
        get_tasks_params = get_tasks_tool.parameters

        assert "properties" in get_tasks_params
        assert "hotel_id" in get_tasks_params["properties"]

        # Test create_housekeeping_task parameters
        create_task_tool = tools["create_housekeeping_task"]
        create_task_params = create_task_tool.parameters

        assert "properties" in create_task_params
        assert "task_type" in create_task_params["properties"]
        assert "room_number" in create_task_params["properties"]
        assert "priority" in create_task_params["properties"]

        # Check required fields
        required_fields = create_task_params.get("required", [])
        assert "task_type" in required_fields
        assert "room_number" in required_fields

    async def test_maintenance_tools_parameters(self):
        """Test maintenance tools have proper parameter structures."""
        app = FastMCP("test-app")
        register_room_tools(app)

        tools = await app.get_tools()

        # Test create_maintenance_request parameters
        maintenance_tool = tools["create_maintenance_request"]
        maintenance_params = maintenance_tool.parameters

        assert "properties" in maintenance_params
        assert "room_number" in maintenance_params["properties"]
        assert "issue_description" in maintenance_params["properties"]
        assert "priority" in maintenance_params["properties"]

        # Check required fields
        required_fields = maintenance_params.get("required", [])
        assert "room_number" in required_fields
        assert "issue_description" in required_fields

    async def test_inventory_tools_parameters(self):
        """Test inventory tools have proper parameter structures."""
        app = FastMCP("test-app")
        register_room_tools(app)

        tools = await app.get_tools()

        # Test get_inventory_status parameters
        get_inventory_tool = tools["get_inventory_status"]
        get_inventory_params = get_inventory_tool.parameters

        assert "properties" in get_inventory_params
        assert "hotel_id" in get_inventory_params["properties"]

        # Test update_inventory_stock parameters
        update_stock_tool = tools["update_inventory_stock"]
        update_stock_params = update_stock_tool.parameters

        assert "properties" in update_stock_params
        assert "item_id" in update_stock_params["properties"]
        assert "adjustment_reason" in update_stock_params["properties"]

        # The function has required fields
        required_fields = update_stock_params.get("required", [])
        assert "item_id" in required_fields
        assert "adjustment_reason" in required_fields

    async def test_availability_and_cleaning_tools(self):
        """Test availability and cleaning schedule tools."""
        app = FastMCP("test-app")
        register_room_tools(app)

        tools = await app.get_tools()

        # Test check_room_availability parameters
        availability_tool = tools["check_room_availability"]
        availability_params = availability_tool.parameters

        assert "properties" in availability_params
        assert "arrival_date" in availability_params["properties"]
        assert "departure_date" in availability_params["properties"]

        # Test get_cleaning_schedule parameters
        cleaning_tool = tools["get_cleaning_schedule"]
        cleaning_params = cleaning_tool.parameters

        assert "properties" in cleaning_params
        assert "hotel_id" in cleaning_params["properties"]
        assert "schedule_date" in cleaning_params["properties"]
