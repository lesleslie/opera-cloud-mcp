"""Unit tests for the tool registry module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from opera_cloud_mcp.tools import tool_registry
from opera_cloud_mcp.tools.tool_registry import (
    ToolCategory,
    ToolMetadata,
    ToolPriority,
    ToolRegistry,
    get_tool_registry,
    initialize_tool_registry,
    register_opera_tool,
)


class TestToolRegistry:
    """Test cases for the tool registry functionality."""

    def setup_method(self):
        """Setup method to reset global state before each test."""
        # Reset global registry
        tool_registry._tool_registry = None

    def test_tool_category_enum(self):
        """Test ToolCategory enum values."""
        assert ToolCategory.RESERVATION.value == "reservation"
        assert ToolCategory.GUEST.value == "guest"
        assert ToolCategory.ROOM.value == "room"
        assert ToolCategory.FINANCIAL.value == "financial"
        assert ToolCategory.OPERATIONAL.value == "operational"
        assert ToolCategory.REPORTING.value == "reporting"
        assert ToolCategory.AUTHENTICATION.value == "authentication"
        assert ToolCategory.SYSTEM.value == "system"

    def test_tool_priority_enum(self):
        """Test ToolPriority enum values."""
        assert ToolPriority.CRITICAL.value == 1
        assert ToolPriority.HIGH.value == 2
        assert ToolPriority.NORMAL.value == 3
        assert ToolPriority.LOW.value == 4

    def test_tool_metadata_defaults(self):
        """Test ToolMetadata with default values."""
        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool"
        )

        assert metadata.name == "test_tool"
        assert metadata.category == ToolCategory.RESERVATION
        assert metadata.priority == ToolPriority.NORMAL
        assert metadata.description == "Test tool"
        assert metadata.version == "1.0.0"
        assert metadata.dependencies == []
        assert metadata.rate_limit_per_minute is None
        assert metadata.requires_auth is True
        assert metadata.hotel_specific is True
        assert metadata.async_execution is True
        assert metadata.timeout_seconds == 30
        assert metadata.tags == []
        assert metadata.examples == []

    def test_tool_registry_initialization(self):
        """Test ToolRegistry initialization."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        assert registry.app == app
        assert registry.hotel_id == "HOTEL123"
        assert registry.tools == {}
        assert registry.categories == {}
        assert registry.dependencies == {}
        assert registry.call_history == []
        assert registry.error_history == []
        assert registry.rate_limits == {}

    def test_register_tool_success(self):
        """Test successful tool registration."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        async def test_tool():
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool"
        )

        # Register the tool
        decorated_tool = registry.register_tool(metadata, test_tool)

        # Verify tool was registered
        assert "test_tool" in registry.tools
        assert registry.tools["test_tool"].metadata == metadata
        assert registry.tools["test_tool"].function == test_tool
        assert "test_tool" in registry.categories[ToolCategory.RESERVATION]

        # Verify decorated tool is a FastMCP Tool
        from fastmcp.tools.tool import Tool
        assert isinstance(decorated_tool, Tool)

    def test_validate_tool_function_async_required(self):
        """Test validation when async function is required but not provided."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        def sync_tool():  # Not async
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool",
            async_execution=True  # Requires async
        )

        with pytest.raises(ValueError, match="requires async execution but function is not async"):
            registry._validate_tool_function(sync_tool, metadata)

    def test_validate_tool_function_missing_hotel_id(self):
        """Test validation when hotel-specific tool is missing hotel_id parameter."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        async def tool_without_hotel_id():
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool",
            hotel_specific=True  # Requires hotel_id
        )

        # Should log a warning but not raise an exception
        with patch('opera_cloud_mcp.tools.tool_registry.logger') as mock_logger:
            registry._validate_tool_function(tool_without_hotel_id, metadata)
            mock_logger.warning.assert_called_once()

    def test_create_tool_wrapper_async(self):
        """Test creating async tool wrapper."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        async def test_tool():
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool",
            async_execution=True
        )

        wrapper = registry._create_tool_wrapper(test_tool, metadata)

        # Verify it's an async function
        assert asyncio.iscoroutinefunction(wrapper)

    def test_create_tool_wrapper_sync(self):
        """Test creating sync tool wrapper."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        def test_tool():
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool",
            async_execution=False
        )

        wrapper = registry._create_tool_wrapper(test_tool, metadata)

        # Verify it's not an async function
        assert not asyncio.iscoroutinefunction(wrapper)

    @patch('asyncio.get_event_loop')
    def test_execute_with_monitoring_success(self, mock_get_loop):
        """Test _execute_with_monitoring for successful execution."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        async def test_tool():
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool"
        )

        # Register the tool to create registration
        registry.register_tool(metadata, test_tool)

        # Execute the tool
        result = asyncio.run(
            registry._execute_with_monitoring(test_tool, metadata, (), {})
        )

        assert result == "success"
        assert registry.tools["test_tool"].call_count == 1
        assert len(registry.call_history) == 1
        assert registry.call_history[0]["success"] is True

    @patch('asyncio.get_event_loop')
    def test_execute_with_monitoring_error(self, mock_get_loop):
        """Test _execute_with_monitoring for error execution."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        async def failing_tool():
            raise ValueError("Test error")

        metadata = ToolMetadata(
            name="failing_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Failing tool"
        )

        # Register the tool to create registration
        registry.register_tool(metadata, failing_tool)

        # Execute the tool and expect the error to be raised
        with pytest.raises(ValueError, match="Test error"):
            asyncio.run(
                registry._execute_with_monitoring(failing_tool, metadata, (), {})
            )

        assert registry.tools["failing_tool"].error_count == 1
        assert len(registry.error_history) == 1
        assert registry.error_history[0]["error_message"] == "Test error"

    def test_check_rate_limit(self):
        """Test rate limiting functionality."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        # Initially should allow calls
        assert registry._check_rate_limit("test_tool", 5) is True

        # Add 4 more calls (total 5) - should still allow
        for i in range(4):
            registry._check_rate_limit("test_tool", 5)

        # Next call should be blocked
        assert registry._check_rate_limit("test_tool", 5) is False

    @patch('asyncio.get_event_loop')
    def test_get_tools_by_category(self, mock_get_loop):
        """Test getting tools by category."""
        from fastmcp import FastMCP

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        async def test_tool():
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool"
        )

        # Register the tool
        registry.register_tool(metadata, test_tool)

        # Get tools by category
        tools = registry.get_tools_by_category(ToolCategory.RESERVATION)

        assert len(tools) == 1
        assert tools[0].metadata.name == "test_tool"

    @patch('asyncio.get_event_loop')
    def test_get_tool_dependencies(self, mock_get_loop):
        """Test getting tool dependencies."""
        from fastmcp import FastMCP

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        async def dependent_tool():
            return "success"

        metadata = ToolMetadata(
            name="dependent_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Dependent tool",
            dependencies=["base_tool"]
        )

        # Register the tool
        registry.register_tool(metadata, dependent_tool)

        # Get dependencies
        deps = registry.get_tool_dependencies("base_tool")

        assert "dependent_tool" in deps

    @patch('asyncio.get_event_loop')
    def test_get_tool_metrics_single_tool(self, mock_get_loop):
        """Test getting metrics for a single tool."""
        from fastmcp import FastMCP

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        async def test_tool():
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool"
        )

        # Register the tool
        registry.register_tool(metadata, test_tool)

        # Execute the tool once to increment call count
        asyncio.run(
            registry._execute_with_monitoring(test_tool, metadata, (), {})
        )

        # Get metrics for the tool
        metrics = registry.get_tool_metrics("test_tool")

        assert metrics["tool_name"] == "test_tool"
        assert metrics["call_count"] == 1
        assert metrics["error_count"] == 0
        assert metrics["error_rate"] == 0.0
        assert metrics["category"] == "reservation"

    @patch('asyncio.get_event_loop')
    def test_get_tool_metrics_all_tools(self, mock_get_loop):
        """Test getting metrics for all tools."""
        from fastmcp import FastMCP

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        async def test_tool():
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool"
        )

        # Register the tool
        registry.register_tool(metadata, test_tool)

        # Get overall metrics
        metrics = registry.get_tool_metrics()

        assert "total_tools" in metrics
        assert "total_calls" in metrics
        assert "total_errors" in metrics
        assert "overall_error_rate" in metrics
        assert "categories" in metrics
        assert "top_tools" in metrics

    @patch('asyncio.get_event_loop')
    def test_get_health_status(self, mock_get_loop):
        """Test getting health status."""
        from fastmcp import FastMCP

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        health = registry.get_health_status()

        assert "status" in health
        assert "health_score" in health
        assert "total_tools" in health
        assert "active_tools" in health
        assert "error_prone_tools" in health
        assert "recent_errors" in health
        assert "categories" in health
        assert "call_history_size" in health
        assert "error_history_size" in health

    @patch('asyncio.get_event_loop')
    def test_list_tools(self, mock_get_loop):
        """Test listing tools with filtering."""
        from fastmcp import FastMCP

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        async def test_tool():
            return "success"

        metadata = ToolMetadata(
            name="test_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Test tool"
        )

        # Register the tool
        registry.register_tool(metadata, test_tool)

        # List tools
        tools = registry.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"
        assert tools[0]["category"] == "reservation"

    @patch('asyncio.get_event_loop')
    def test_list_tools_with_filtering(self, mock_get_loop):
        """Test listing tools with category filtering."""
        from fastmcp import FastMCP

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        async def reservation_tool():
            return "reservation"

        async def guest_tool():
            return "guest"

        reservation_metadata = ToolMetadata(
            name="reservation_tool",
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.NORMAL,
            description="Reservation tool"
        )

        guest_metadata = ToolMetadata(
            name="guest_tool",
            category=ToolCategory.GUEST,
            priority=ToolPriority.NORMAL,
            description="Guest tool"
        )

        # Register both tools
        registry.register_tool(reservation_metadata, reservation_tool)
        registry.register_tool(guest_metadata, guest_tool)

        # List tools with category filter
        tools = registry.list_tools(category=ToolCategory.RESERVATION)

        assert len(tools) == 1
        assert tools[0]["name"] == "reservation_tool"

    @patch('asyncio.get_event_loop')
    def test_cleanup_history(self, mock_get_loop):
        """Test cleaning up old history entries."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")
        registry = ToolRegistry(app, hotel_id="HOTEL123")

        # Mock the event loop to return a time in the past
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0  # Old time
        mock_get_loop.return_value = mock_loop

        # Add some history entries
        registry.call_history.append({"timestamp": 50.0})  # Very old
        registry.error_history.append({"timestamp": 60.0})  # Very old

        # Mock current time to be much later
        mock_loop.time.return_value = 100000.0  # Current time (much later)

        # Clean up history (keep last 24 hours = 86400 seconds)
        removed = registry.cleanup_history(max_age_hours=24.0)

        # All entries should be removed since they're older than 24 hours
        assert removed == 2  # 1 call + 1 error
        assert len(registry.call_history) == 0
        assert len(registry.error_history) == 0


class TestGlobalRegistry:
    """Test global registry functions."""

    def setup_method(self):
        """Setup method to reset global state before each test."""
        tool_registry._tool_registry = None

    def test_get_tool_registry_not_initialized(self):
        """Test getting registry when not initialized."""
        with pytest.raises(RuntimeError, match="Tool registry not initialized"):
            get_tool_registry()

    def test_initialize_tool_registry(self):
        """Test initializing the global tool registry."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")

        registry = initialize_tool_registry(app, hotel_id="HOTEL123")

        assert isinstance(registry, ToolRegistry)
        assert registry.hotel_id == "HOTEL123"

        # Verify it's accessible via get_tool_registry
        retrieved_registry = get_tool_registry()
        assert retrieved_registry == registry

    def test_initialize_tool_registry_warning(self):
        """Test initializing registry when already initialized."""
        from fastmcp import FastMCP

        app = FastMCP(name="test_app", version="1.0.0")

        # Initialize first time
        registry1 = initialize_tool_registry(app, hotel_id="HOTEL123")

        with patch('opera_cloud_mcp.tools.tool_registry.logger') as mock_logger:
            # Initialize second time - should log warning
            registry2 = initialize_tool_registry(app, hotel_id="HOTEL456")

            mock_logger.warning.assert_called_once()
            assert registry2.hotel_id == "HOTEL456"  # New instance should be used


class TestRegisterOperaToolDecorator:
    """Test the register_opera_tool decorator."""

    def setup_method(self):
        """Setup method to reset global state before each test."""
        tool_registry._tool_registry = None

    @patch('asyncio.get_event_loop')
    def test_register_opera_tool_decorator(self, mock_get_loop):
        """Test the register_opera_tool decorator."""
        from fastmcp import FastMCP

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        app = FastMCP(name="test_app", version="1.0.0")
        initialize_tool_registry(app, hotel_id="HOTEL123")

        @register_opera_tool(
            category=ToolCategory.RESERVATION,
            priority=ToolPriority.HIGH,
            description="Test decorated tool"
        )
        async def decorated_tool():
            return "decorated"

        # Verify the tool was registered
        registry = get_tool_registry()
        assert "decorated_tool" in registry.tools

        tool_registration = registry.tools["decorated_tool"]
        assert tool_registration.metadata.category == ToolCategory.RESERVATION
        assert tool_registration.metadata.priority == ToolPriority.HIGH
        assert tool_registration.metadata.description == "Test decorated tool"

        # Verify it's a FastMCP Tool
        from fastmcp.tools.tool import Tool
        assert isinstance(decorated_tool, Tool)

    @patch('asyncio.get_event_loop')
    def test_register_opera_tool_decorator_with_defaults(self, mock_get_loop):
        """Test the register_opera_tool decorator with default values."""
        from fastmcp import FastMCP

        # Mock the event loop
        mock_loop = Mock()
        mock_loop.time.return_value = 100.0
        mock_get_loop.return_value = mock_loop

        app = FastMCP(name="test_app", version="1.0.0")
        initialize_tool_registry(app, hotel_id="HOTEL123")

        @register_opera_tool(category=ToolCategory.GUEST)
        async def simple_tool():
            """Simple tool docstring."""
            return "simple"

        # Verify the tool was registered with defaults
        registry = get_tool_registry()
        tool_registration = registry.tools["simple_tool"]

        assert tool_registration.metadata.category == ToolCategory.GUEST
        assert tool_registration.metadata.priority == ToolPriority.NORMAL  # Default
        assert tool_registration.metadata.description == "Simple tool docstring."  # From docstring
        assert tool_registration.metadata.requires_auth is True  # Default
        assert tool_registration.metadata.hotel_specific is True  # Default
