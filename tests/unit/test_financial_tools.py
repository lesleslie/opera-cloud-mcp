"""
Unit tests for financial MCP tools.

Tests the FastMCP tool registration for financial and cashiering operations.
"""

from fastmcp import FastMCP

from opera_cloud_mcp.tools.financial_tools import register_financial_tools


class TestFinancialTools:
    """Test suite for financial MCP tools."""

    async def test_register_financial_tools(self):
        """Test that financial tools are registered correctly."""
        app = FastMCP("test-app")
        register_financial_tools(app)

        # Check that tools were registered using the correct FastMCP API
        tools = await app.get_tools()
        tool_names = list(tools.keys())

        expected_tools = [
            "get_guest_folio",
            "post_charge_to_room",
            "process_payment",
            "generate_folio_report",
            "transfer_charges",
            "void_transaction",
            "process_refund",
            "get_daily_revenue_report",
            "get_outstanding_balances",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, (
                f"Tool '{tool_name}' not found in registered tools: {tool_names}"
            )

        # Verify we got the expected number of tools
        assert len(tool_names) == len(expected_tools), (
            f"Expected {len(expected_tools)} tools, got {len(tool_names)}: {tool_names}"
        )

    async def test_financial_tool_functions_exist(self):
        """Test that financial tool functions can be accessed."""
        app = FastMCP("test-app")
        register_financial_tools(app)

        tools = await app.get_tools()

        # Test that each tool has the expected attributes
        for tool_name in ["get_guest_folio", "post_charge_to_room", "process_payment"]:
            tool = tools[tool_name]
            assert tool.fn is not None, f"Tool {tool_name} should have a function"
            assert callable(tool.fn), f"Tool {tool_name} function should be callable"
            assert hasattr(tool, "parameters"), (
                f"Tool {tool_name} should have parameters"
            )
            assert tool.parameters is not None, (
                f"Tool {tool_name} parameters should not be None"
            )

    async def test_financial_tools_parameters(self):
        """Test financial tools have proper parameter structures."""
        app = FastMCP("test-app")
        register_financial_tools(app)

        tools = await app.get_tools()

        # Test key financial tools have hotel_id parameter
        key_tools = ["get_guest_folio", "post_charge_to_room", "process_payment"]
        for tool_name in key_tools:
            tool = tools[tool_name]
            assert "properties" in tool.parameters
            assert "hotel_id" in tool.parameters["properties"], (
                f"Tool {tool_name} should have hotel_id parameter"
            )
