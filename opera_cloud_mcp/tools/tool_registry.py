"""
Centralized MCP tool registry and organization system.

Provides dynamic tool registration, categorization, and lifecycle management
for OPERA Cloud MCP tools with automatic discovery and validation.
"""

import asyncio
import inspect
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool

from opera_cloud_mcp.utils.exceptions import RateLimitError

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """MCP tool categories for organization."""

    RESERVATION = "reservation"
    GUEST = "guest"
    ROOM = "room"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    REPORTING = "reporting"
    AUTHENTICATION = "authentication"
    SYSTEM = "system"


class ToolPriority(Enum):
    """Tool execution priority levels."""

    CRITICAL = 1  # System/auth tools
    HIGH = 2  # Core business operations
    NORMAL = 3  # Standard hotel operations
    LOW = 4  # Reports and analytics


@dataclass
class ToolMetadata:
    """Metadata for MCP tools."""

    name: str
    category: ToolCategory
    priority: ToolPriority
    description: str
    version: str = "1.0.0"
    dependencies: list[str] = field(default_factory=list)
    rate_limit_per_minute: int | None = None
    requires_auth: bool = True
    hotel_specific: bool = True
    async_execution: bool = True
    timeout_seconds: int = 30
    tags: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolRegistration:
    """Complete tool registration information."""

    metadata: ToolMetadata
    function: Callable
    fastmcp_tool: Any  # The decorated tool function
    registered_at: float = field(
        default_factory=lambda: asyncio.get_event_loop().time()
    )
    call_count: int = 0
    last_called: float | None = None
    average_duration: float = 0.0
    error_count: int = 0


class ToolRegistry:
    """
    Centralized registry for OPERA Cloud MCP tools.

    Features:
    - Automatic tool discovery and registration
    - Category-based organization
    - Performance monitoring and metrics
    - Dependency management
    - Rate limiting and access control
    - Lifecycle management
    """

    def __init__(self, app: FastMCP, hotel_id: str | None = None):
        """
        Initialize tool registry.

        Args:
            app: FastMCP application instance
            hotel_id: Hotel identifier for context
        """
        self.app = app
        self.hotel_id = hotel_id

        # Registry storage
        self.tools: dict[str, ToolRegistration] = {}
        self.categories: dict[ToolCategory, list[str]] = defaultdict(list)
        self.dependencies: dict[str, list[str]] = defaultdict(list)

        # Performance tracking
        self.call_history: list[dict[str, Any]] = []
        self.error_history: list[dict[str, Any]] = []

        # Rate limiting
        self.rate_limits: dict[str, dict[str, Any]] = defaultdict(dict)

        logger.info(
            "Tool registry initialized",
            extra={
                "hotel_id": hotel_id,
                "app_name": app.name if hasattr(app, "name") else "unknown",
            },
        )

    def register_tool(self, metadata: ToolMetadata, function: Callable) -> Tool:
        """
        Register a tool with the registry and FastMCP.

        Args:
            metadata: Tool metadata
            function: Tool function to register

        Returns:
            Decorated function for use with FastMCP
        """
        # Validate function signature
        self._validate_tool_function(function, metadata)

        # Create wrapper for monitoring and rate limiting
        wrapped_function = self._create_tool_wrapper(function, metadata)

        # Register with FastMCP
        decorated_function = Tool.from_function(
            wrapped_function, name=metadata.name, description=metadata.description
        )

        # Store registration
        registration = ToolRegistration(
            metadata=metadata, function=function, fastmcp_tool=decorated_function
        )

        self.tools[metadata.name] = registration
        self.categories[metadata.category].append(metadata.name)

        # Track dependencies
        for dep in metadata.dependencies:
            self.dependencies[dep].append(metadata.name)

        logger.info(
            "Tool registered",
            extra={
                "tool_name": metadata.name,
                "category": metadata.category.value,
                "priority": metadata.priority.value,
                "dependencies": metadata.dependencies,
            },
        )

        return decorated_function

    def _validate_tool_function(
        self, function: Callable, metadata: ToolMetadata
    ) -> None:
        """Validate tool function meets requirements."""
        sig = inspect.signature(function)

        # Check if async when required
        if metadata.async_execution and not asyncio.iscoroutinefunction(function):
            raise ValueError(
                f"Tool {metadata.name} requires async execution "
                + "but function is not async"
            )

        # Check for hotel_id parameter if hotel-specific
        if metadata.hotel_specific:
            params = list(sig.parameters.keys())
            if "hotel_id" not in params:
                logger.warning(
                    f"Hotel-specific tool {metadata.name} doesn't "
                    + "have hotel_id parameter"
                )

        # Validate return type hints
        if sig.return_annotation == inspect.Signature.empty:
            logger.warning(f"Tool {metadata.name} missing return type annotation")

    def _create_tool_wrapper(
        self, function: Callable, metadata: ToolMetadata
    ) -> Callable:
        """Create monitoring and rate limiting wrapper."""

        @wraps(function)
        async def async_wrapper(*args, **kwargs):
            return await self._execute_with_monitoring(function, metadata, args, kwargs)

        @wraps(function)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(
                self._execute_with_monitoring(function, metadata, args, kwargs)
            )

        return async_wrapper if metadata.async_execution else sync_wrapper

    async def _execute_with_monitoring(
        self, function: Callable, metadata: ToolMetadata, args: tuple, kwargs: dict
    ) -> Any:
        """Execute tool with monitoring and error handling."""
        start_time = asyncio.get_event_loop().time()
        registration = self.tools[metadata.name]

        # Check rate limits
        if metadata.rate_limit_per_minute and not self._check_rate_limit(
            metadata.name, metadata.rate_limit_per_minute
        ):
            raise RateLimitError(f"Rate limit exceeded for tool {metadata.name}")

        try:
            # Execute function with timeout
            if metadata.async_execution:
                result = await asyncio.wait_for(
                    function(*args, **kwargs), timeout=metadata.timeout_seconds
                )
            else:
                result = function(*args, **kwargs)

            # Update success metrics
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time

            registration.call_count += 1
            registration.last_called = end_time

            # Update average duration
            if registration.average_duration == 0:
                registration.average_duration = duration
            else:
                registration.average_duration = (
                    registration.average_duration * (registration.call_count - 1)
                    + duration
                ) / registration.call_count

            # Record call history
            self.call_history.append(
                {
                    "tool_name": metadata.name,
                    "timestamp": end_time,
                    "duration": duration,
                    "success": True,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs),
                }
            )

            logger.debug(
                "Tool executed successfully",
                extra={
                    "tool_name": metadata.name,
                    "duration": duration,
                    "call_count": registration.call_count,
                },
            )

            return result

        except Exception as e:
            # Update error metrics
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time

            registration.error_count += 1

            # Record error history
            self.error_history.append(
                {
                    "tool_name": metadata.name,
                    "timestamp": end_time,
                    "duration": duration,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "args_count": len(args),
                    "kwargs_count": len(kwargs),
                }
            )

            logger.error(
                "Tool execution failed",
                extra={
                    "tool_name": metadata.name,
                    "duration": duration,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            raise

    def _check_rate_limit(self, tool_name: str, limit_per_minute: int) -> bool:
        """Check if tool is within rate limits."""
        now = asyncio.get_event_loop().time()
        minute_ago = now - 60.0

        # Initialize tracking if needed
        if tool_name not in self.rate_limits:
            self.rate_limits[tool_name] = {"calls": [], "minute_count": 0}

        rate_data = self.rate_limits[tool_name]

        # Remove old calls
        rate_data["calls"] = [
            call_time for call_time in rate_data["calls"] if call_time > minute_ago
        ]

        # Check limit
        if len(rate_data["calls"]) >= limit_per_minute:
            return False

        # Record this call
        rate_data["calls"].append(now)
        return True

    def get_tools_by_category(self, category: ToolCategory) -> list[ToolRegistration]:
        """Get all tools in a category."""
        tool_names = self.categories.get(category, [])
        return [self.tools[name] for name in tool_names if name in self.tools]

    def get_tool_dependencies(self, tool_name: str) -> list[str]:
        """Get tools that depend on the given tool."""
        return self.dependencies.get(tool_name, [])

    def get_tool_metrics(self, tool_name: str | None = None) -> dict[str, Any]:
        """
        Get tool performance metrics.

        Args:
            tool_name: Specific tool name, or None for all tools

        Returns:
            Dictionary with metrics
        """
        if tool_name and tool_name in self.tools:
            # Single tool metrics
            registration = self.tools[tool_name]
            error_rate = 0.0
            if registration.call_count > 0:
                error_rate = registration.error_count / registration.call_count

            return {
                "tool_name": tool_name,
                "call_count": registration.call_count,
                "error_count": registration.error_count,
                "error_rate": error_rate,
                "average_duration": registration.average_duration,
                "last_called": registration.last_called,
                "category": registration.metadata.category.value,
                "priority": registration.metadata.priority.value,
            }
        else:
            # Overall metrics
            total_calls = sum(reg.call_count for reg in self.tools.values())
            total_errors = sum(reg.error_count for reg in self.tools.values())

            # Category breakdown
            category_stats = {}
            for category, tool_names in self.categories.items():
                cat_calls = sum(
                    self.tools[name].call_count
                    for name in tool_names
                    if name in self.tools
                )
                cat_errors = sum(
                    self.tools[name].error_count
                    for name in tool_names
                    if name in self.tools
                )

                category_stats[category.value] = {
                    "tool_count": len(tool_names),
                    "total_calls": cat_calls,
                    "total_errors": cat_errors,
                    "error_rate": cat_errors / max(cat_calls, 1),
                }

            return {
                "total_tools": len(self.tools),
                "total_calls": total_calls,
                "total_errors": total_errors,
                "overall_error_rate": total_errors / max(total_calls, 1),
                "categories": category_stats,
                "top_tools": self._get_top_tools_by_usage(10),
            }

    def _get_top_tools_by_usage(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get most frequently used tools."""
        sorted_tools = sorted(
            self.tools.values(), key=lambda x: x.call_count, reverse=True
        )

        return [
            {
                "name": reg.metadata.name,
                "call_count": reg.call_count,
                "category": reg.metadata.category.value,
                "average_duration": reg.average_duration,
                "error_rate": reg.error_count / max(reg.call_count, 1),
            }
            for reg in sorted_tools[:limit]
        ]

    def get_health_status(self) -> dict[str, Any]:
        """Get overall tool registry health."""
        now = asyncio.get_event_loop().time()

        # Count tools by status
        active_tools = sum(
            1
            for reg in self.tools.values()
            if reg.last_called and (now - reg.last_called) < 3600
        )
        error_prone_tools = sum(
            1
            for reg in self.tools.values()
            if reg.call_count > 0 and (reg.error_count / reg.call_count) > 0.1
        )

        # Recent errors
        recent_errors = sum(
            1 for error in self.error_history if (now - error["timestamp"]) < 300
        )

        # Determine health status
        total_tools = len(self.tools)
        health_score = 1.0

        if total_tools > 0:
            error_rate = error_prone_tools / total_tools
            health_score = max(0.0, 1.0 - error_rate)

        status = "healthy"
        if health_score < 0.7:
            status = "degraded"
        elif health_score < 0.5:
            status = "unhealthy"

        return {
            "status": status,
            "health_score": health_score,
            "total_tools": total_tools,
            "active_tools": active_tools,
            "error_prone_tools": error_prone_tools,
            "recent_errors": recent_errors,
            "categories": len(self.categories),
            "call_history_size": len(self.call_history),
            "error_history_size": len(self.error_history),
        }

    def list_tools(
        self,
        category: ToolCategory | None = None,
        priority: ToolPriority | None = None,
        include_examples: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List registered tools with optional filtering.

        Args:
            category: Filter by category
            priority: Filter by priority
            include_examples: Include usage examples

        Returns:
            List of tool information
        """
        filtered_tools = []

        for registration in self.tools.values():
            metadata = registration.metadata

            # Apply filters
            if category and metadata.category != category:
                continue
            if priority and metadata.priority != priority:
                continue

            tool_info: dict[str, Any] = {
                "name": metadata.name,
                "description": metadata.description,
                "category": metadata.category.value,
                "priority": metadata.priority.value,
                "version": metadata.version,
                "requires_auth": metadata.requires_auth,
                "hotel_specific": metadata.hotel_specific,
                "rate_limit_per_minute": metadata.rate_limit_per_minute,
                "timeout_seconds": metadata.timeout_seconds,
                "tags": metadata.tags,
                "call_count": registration.call_count,
                "error_count": registration.error_count,
                "average_duration": registration.average_duration,
            }

            if include_examples:
                tool_info["examples"] = metadata.examples

            filtered_tools.append(tool_info)

        # Sort by priority and name
        from operator import itemgetter

        filtered_tools.sort(key=itemgetter("priority", "name"))
        return filtered_tools

    def cleanup_history(self, max_age_hours: float = 24.0) -> int:
        """
        Clean up old call and error history.

        Args:
            max_age_hours: Maximum age to keep in hours

        Returns:
            Number of entries removed
        """
        cutoff_time = asyncio.get_event_loop().time() - (max_age_hours * 3600)

        # Clean call history
        old_call_count = len(self.call_history)
        self.call_history = [
            entry for entry in self.call_history if entry["timestamp"] > cutoff_time
        ]

        # Clean error history
        old_error_count = len(self.error_history)
        self.error_history = [
            entry for entry in self.error_history if entry["timestamp"] > cutoff_time
        ]

        removed = (old_call_count - len(self.call_history)) + (
            old_error_count - len(self.error_history)
        )

        if removed > 0:
            logger.info(f"Cleaned up {removed} old history entries")

        return removed


# Global registry instance (initialized by application)
_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    if _tool_registry is None:
        raise RuntimeError(
            "Tool registry not initialized. Call initialize_tool_registry() first."
        )
    return _tool_registry


def initialize_tool_registry(app: FastMCP, hotel_id: str | None = None) -> ToolRegistry:
    """Initialize the global tool registry."""
    global _tool_registry

    if _tool_registry is not None:
        logger.warning("Tool registry already initialized, replacing existing instance")

    _tool_registry = ToolRegistry(app=app, hotel_id=hotel_id)
    return _tool_registry


def register_opera_tool(
    category: ToolCategory,
    priority: ToolPriority = ToolPriority.NORMAL,
    description: str = "",
    version: str = "1.0.0",
    dependencies: list[str] | None = None,
    rate_limit_per_minute: int | None = None,
    requires_auth: bool = True,
    hotel_specific: bool = True,
    async_execution: bool = True,
    timeout_seconds: int = 30,
    tags: list[str] | None = None,
    examples: list[dict[str, Any]] | None = None,
):
    """
    Decorator for registering OPERA Cloud MCP tools.

    Args:
        category: Tool category
        priority: Execution priority
        description: Tool description
        version: Tool version
        dependencies: List of dependencies
        rate_limit_per_minute: Rate limit per minute
        requires_auth: Whether authentication is required
        hotel_specific: Whether hotel_id is required
        async_execution: Whether tool is async
        timeout_seconds: Execution timeout
        tags: List of tags
        examples: Usage examples

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Tool:
        # Get function name and create metadata
        func_name = func.__name__

        metadata = ToolMetadata(
            name=func_name,
            category=category,
            priority=priority,
            description=description
            or func.__doc__
            or f"OPERA Cloud {category.value} tool",
            version=version,
            dependencies=dependencies or [],
            rate_limit_per_minute=rate_limit_per_minute,
            requires_auth=requires_auth,
            hotel_specific=hotel_specific,
            async_execution=async_execution,
            timeout_seconds=timeout_seconds,
            tags=tags or [],
            examples=examples or [],
        )

        # Register with global registry
        return get_tool_registry().register_tool(metadata, func)

    return decorator
