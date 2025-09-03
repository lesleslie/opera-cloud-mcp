"""
Unit tests for guest MCP tools.

Tests the FastMCP tool registration for guest profile management functionality.
"""

from fastmcp import FastMCP

from opera_cloud_mcp.tools.guest_tools import register_guest_tools


class TestGuestTools:
    """Test suite for guest MCP tools."""

    async def test_register_guest_tools(self):
        """Test that guest tools are registered correctly."""
        app = FastMCP("test-app")
        register_guest_tools(app)

        # Check that tools were registered using the correct FastMCP API
        tools = await app.get_tools()
        tool_names = list(tools.keys())

        expected_tools = [
            "search_guests",
            "get_guest_profile",
            "create_guest_profile",
            "update_guest_profile",
            "get_guest_preferences",
            "update_guest_preferences",
            "get_guest_stay_history",
            "merge_guest_profiles",
            "get_guest_loyalty_info",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, (
                f"Tool '{tool_name}' not found in registered tools: {tool_names}"
            )

        # Verify we got the expected number of tools
        assert len(tool_names) == len(expected_tools), (
            f"Expected {len(expected_tools)} tools, got {len(tool_names)}: {tool_names}"
        )

    async def test_guest_tool_functions_exist(self):
        """Test that guest tool functions can be accessed."""
        app = FastMCP("test-app")
        register_guest_tools(app)

        tools = await app.get_tools()

        # Test that each tool has the expected attributes
        for tool_name in [
            "search_guests",
            "get_guest_profile",
            "create_guest_profile",
            "update_guest_profile",
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

    async def test_guest_tool_parameters_structure(self):
        """Test that guest tools have proper parameter structures."""
        app = FastMCP("test-app")
        register_guest_tools(app)

        tools = await app.get_tools()

        # Test search_guests parameters
        search_tool = tools["search_guests"]
        search_params = search_tool.parameters

        assert "properties" in search_params
        assert "hotel_id" in search_params["properties"]

        # Test get_guest_profile parameters
        get_tool = tools["get_guest_profile"]
        get_params = get_tool.parameters

        assert "properties" in get_params
        assert "guest_id" in get_params["properties"]
        assert "hotel_id" in get_params["properties"]

        # Check required fields for get_guest_profile
        assert "guest_id" in get_params.get("required", [])

        # Test create_guest_profile parameters
        create_tool = tools["create_guest_profile"]
        create_params = create_tool.parameters

        assert "properties" in create_params
        assert "first_name" in create_params["properties"]
        assert "last_name" in create_params["properties"]

        # Check required fields for create_guest_profile
        required_fields = create_params.get("required", [])
        assert "first_name" in required_fields
        assert "last_name" in required_fields

    async def test_guest_preference_tools_exist(self):
        """Test that guest preference tools are properly registered."""
        app = FastMCP("test-app")
        register_guest_tools(app)

        tools = await app.get_tools()

        # Test preference-related tools
        pref_tools = ["get_guest_preferences", "update_guest_preferences"]
        for tool_name in pref_tools:
            assert tool_name in tools, f"Preference tool {tool_name} not found"
            tool = tools[tool_name]
            assert "guest_id" in tool.parameters["properties"], (
                f"Tool {tool_name} should have guest_id parameter"
            )

    async def test_guest_loyalty_and_history_tools(self):
        """Test that guest loyalty and history tools are properly registered."""
        app = FastMCP("test-app")
        register_guest_tools(app)

        tools = await app.get_tools()

        # Test loyalty and history tools
        history_tools = ["get_guest_stay_history", "get_guest_loyalty_info"]
        for tool_name in history_tools:
            assert tool_name in tools, f"History/loyalty tool {tool_name} not found"
            tool = tools[tool_name]
            assert "guest_id" in tool.parameters["properties"], (
                f"Tool {tool_name} should have guest_id parameter"
            )

    async def test_merge_guest_profiles_tool(self):
        """Test that merge guest profiles tool is properly configured."""
        app = FastMCP("test-app")
        register_guest_tools(app)

        tools = await app.get_tools()

        merge_tool = tools["merge_guest_profiles"]
        merge_params = merge_tool.parameters

        assert "properties" in merge_params
        assert "primary_guest_id" in merge_params["properties"]
        assert "duplicate_guest_id" in merge_params["properties"]

        # Check required fields
        required_fields = merge_params.get("required", [])
        assert "primary_guest_id" in required_fields
        assert "duplicate_guest_id" in required_fields
