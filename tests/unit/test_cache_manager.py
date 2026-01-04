"""Unit tests for the cache manager module."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from opera_cloud_mcp.utils.cache_manager import (
    CacheConfig,
    CacheEntry,
    InvalidationStrategy,
    OperaCacheManager,
)


class TestCacheManager:
    """Test cases for the cache manager functionality."""

    def setup_method(self):
        """Setup method to reset global state before each test."""
        pass

    def test_cache_config_defaults(self):
        """Test CacheConfig with default values."""
        config = CacheConfig(
            ttl_seconds=300,
            max_size=100,
            invalidation_strategy=InvalidationStrategy.TIME_BASED
        )

        assert config.ttl_seconds == 300
        assert config.max_size == 100
        assert config.invalidation_strategy == InvalidationStrategy.TIME_BASED
        assert config.dependencies is None
        assert config.tags is None
        assert config.compress is False
        assert config.serialize_json is True

    def test_cache_entry_defaults(self):
        """Test CacheEntry with default values."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=5)
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0
        assert entry.last_accessed is None
        assert entry.dependencies is None
        assert entry.tags is None
        assert entry.size_bytes == 0

    def test_cache_manager_initialization(self):
        """Test cache manager initialization."""
        cache_manager = OperaCacheManager(
            hotel_id="HOTEL123",
            enable_persistent=True,
            enable_monitoring=True,
            max_memory_size=5000
        )

        assert cache_manager.hotel_id == "HOTEL123"
        assert cache_manager.enable_persistent is True
        assert cache_manager.enable_monitoring is True
        assert cache_manager.max_memory_size == 5000
        assert cache_manager._memory_cache == {}
        assert cache_manager._dependency_map == {}
        assert cache_manager._stats is not None
        assert cache_manager._stats["hits"] == 0
        assert cache_manager._stats["misses"] == 0

    def test_generate_cache_key(self):
        """Test cache key generation."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        # Test basic key generation
        key = cache_manager._generate_cache_key("guest_profile", "GUEST001")
        expected = "HOTEL123:guest_profile:GUEST001"
        assert key == expected

        # Test with parameters
        params = {"include_history": True, "limit": 10}
        key_with_params = cache_manager._generate_cache_key("guest_profile", "GUEST001", params)

        # Should contain the base key plus a hash of the parameters
        assert key_with_params.startswith("HOTEL123:guest_profile:GUEST001:")
        assert len(key_with_params) > len(expected)  # Hash part added

    def test_calculate_size(self):
        """Test size calculation for different value types."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        # Test string size
        size_str = cache_manager._calculate_size("hello world")
        assert size_str == len("hello world".encode("utf-8"))

        # Test dict size
        size_dict = cache_manager._calculate_size({"key": "value", "num": 123})
        assert size_dict > 0

        # Test list size
        size_list = cache_manager._calculate_size([1, 2, 3, "hello"])
        assert size_list > 0

        # Test other types
        size_int = cache_manager._calculate_size(42)
        assert size_int > 0

    @patch('opera_cloud_mcp.utils.cache_manager.datetime')
    def test_set_and_get_cache(self, mock_datetime):
        """Test setting and getting values from cache."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        # Mock datetime to have consistent time
        mock_now = datetime.now(UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda tz: datetime.now(tz) if tz == UTC else datetime.now()

        # Set a value
        result = asyncio.run(
            cache_manager.set("guest_profile", "GUEST001", {"name": "John Doe"})
        )
        assert result is True

        # Get the value back
        value = asyncio.run(
            cache_manager.get("guest_profile", "GUEST001")
        )
        assert value == {"name": "John Doe"}

        # Verify access count increased
        cache_key = "HOTEL123:guest_profile:GUEST001"
        entry = cache_manager._memory_cache[cache_key]
        assert entry.access_count == 1
        assert entry.last_accessed == mock_now

    @patch('opera_cloud_mcp.utils.cache_manager.datetime')
    def test_cache_expiration(self, mock_datetime):
        """Test cache expiration."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        # Mock datetime to simulate time progression
        mock_now = datetime.now(UTC)
        mock_datetime.now.return_value = mock_now

        # Set a value with short TTL
        asyncio.run(
            cache_manager.set("test_data", "TEST001", {"data": "value"}, ttl_override=1)
        )

        # Advance time beyond expiration
        mock_datetime.now.return_value = mock_now + timedelta(seconds=2)

        # Try to get the value - should return default since it's expired
        value = asyncio.run(
            cache_manager.get("test_data", "TEST001", default="default_value")
        )
        assert value == "default_value"

    @patch('opera_cloud_mcp.utils.cache_manager.datetime')
    def test_cache_invalidation_by_dependency(self, mock_datetime):
        """Test cache invalidation by dependency."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        mock_now = datetime.now(UTC)
        mock_datetime.now.return_value = mock_now

        # Set a value with dependencies
        config = CacheConfig(
            ttl_seconds=300,
            max_size=100,
            invalidation_strategy=InvalidationStrategy.EVENT_BASED,
            dependencies=["guest_updates"]
        )

        # Manually add an entry with dependencies
        cache_key = "HOTEL123:guest_profile:GUEST001"
        entry = CacheEntry(
            key=cache_key,
            value={"name": "John Doe"},
            created_at=mock_now,
            expires_at=mock_now + timedelta(minutes=5),
            dependencies=["guest_updates"]
        )
        cache_manager._memory_cache[cache_key] = entry
        cache_manager._dependency_map["guest_updates"] = [cache_key]

        # Verify entry exists
        assert cache_key in cache_manager._memory_cache

        # Invalidate by dependency
        invalidated_count = asyncio.run(
            cache_manager.invalidate(dependency="guest_updates")
        )

        assert invalidated_count == 1
        assert cache_key not in cache_manager._memory_cache
        assert "guest_updates" not in cache_manager._dependency_map

    @patch('opera_cloud_mcp.utils.cache_manager.datetime')
    def test_cache_invalidation_by_data_type(self, mock_datetime):
        """Test cache invalidation by data type."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        mock_now = datetime.now(UTC)
        mock_datetime.now.return_value = mock_now

        # Add entries of different types
        asyncio.run(
            cache_manager.set("guest_profile", "GUEST001", {"name": "John"})
        )
        asyncio.run(
            cache_manager.set("room_status", "ROOM101", {"status": "clean"})
        )
        asyncio.run(
            cache_manager.set("guest_profile", "GUEST002", {"name": "Jane"})
        )

        # Verify entries exist
        assert len(cache_manager._memory_cache) == 3

        # Invalidate all guest_profile entries
        invalidated_count = asyncio.run(
            cache_manager.invalidate(data_type="guest_profile")
        )

        assert invalidated_count == 2  # GUEST001 and GUEST002
        assert len(cache_manager._memory_cache) == 1  # Only room_status remains

    @patch('opera_cloud_mcp.utils.cache_manager.datetime')
    def test_cache_invalidation_by_tags(self, mock_datetime):
        """Test cache invalidation by tags."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        mock_now = datetime.now(UTC)
        mock_datetime.now.return_value = mock_now

        # Manually add entries with tags
        cache_key1 = "HOTEL123:guest_profile:GUEST001"
        cache_key2 = "HOTEL123:room_status:ROOM101"

        entry1 = CacheEntry(
            key=cache_key1,
            value={"name": "John"},
            created_at=mock_now,
            expires_at=mock_now + timedelta(minutes=5),
            tags=["guest", "profile"]
        )
        entry2 = CacheEntry(
            key=cache_key2,
            value={"status": "clean"},
            created_at=mock_now,
            expires_at=mock_now + timedelta(minutes=5),
            tags=["room", "status"]
        )

        cache_manager._memory_cache[cache_key1] = entry1
        cache_manager._memory_cache[cache_key2] = entry2

        # Invalidate by tag
        invalidated_count = asyncio.run(
            cache_manager.invalidate(tags=["guest"])
        )

        assert invalidated_count == 1  # Only the guest entry
        assert cache_key1 not in cache_manager._memory_cache
        assert cache_key2 in cache_manager._memory_cache

    @patch('opera_cloud_mcp.utils.cache_manager.datetime')
    def test_cache_invalidation_by_identifier(self, mock_datetime):
        """Test cache invalidation by specific identifier."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        mock_now = datetime.now(UTC)
        mock_datetime.now.return_value = mock_now

        # Add entries
        asyncio.run(
            cache_manager.set("guest_profile", "GUEST001", {"name": "John"})
        )
        asyncio.run(
            cache_manager.set("guest_profile", "GUEST002", {"name": "Jane"})
        )

        # Check that both entries exist
        assert len(cache_manager._memory_cache) == 2

        # Invalidate specific identifier
        invalidated_count = asyncio.run(
            cache_manager.invalidate(data_type="guest_profile", identifier="GUEST001")
        )

        # Should have invalidated only 1 entry
        assert invalidated_count == 1
        # Should have 1 entry remaining
        assert len(cache_manager._memory_cache) == 1
        # The remaining entry should be GUEST002
        remaining_key = "HOTEL123:guest_profile:GUEST002"
        assert remaining_key in cache_manager._memory_cache
        cache_key = "HOTEL123:guest_profile:GUEST001"
        assert cache_key not in cache_manager._memory_cache

    def test_cache_capacity_management(self):
        """Test cache capacity management and eviction."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123", max_memory_size=2)

        # Add more entries than the max size
        asyncio.run(
            cache_manager.set("data_type", "ITEM1", {"value": 1})
        )
        asyncio.run(
            cache_manager.set("data_type", "ITEM2", {"value": 2})
        )
        asyncio.run(
            cache_manager.set("data_type", "ITEM3", {"value": 3})
        )

        # Should have evicted some entries to stay within capacity
        assert len(cache_manager._memory_cache) <= 2

    def test_cache_stats(self):
        """Test cache statistics."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        # Initially empty
        stats = cache_manager.get_stats()
        assert stats is not None
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["entries_count"] == 0
        assert stats["hit_rate"] == 0.0

    @patch('opera_cloud_mcp.utils.cache_manager.datetime')
    def test_cache_health_check(self, mock_datetime):
        """Test cache health check."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        mock_now = datetime.now(UTC)
        mock_datetime.now.return_value = mock_now

        # Add some entries
        asyncio.run(
            cache_manager.set("test_data", "TEST001", {"value": "test"})
        )

        # Run health check
        health = asyncio.run(cache_manager.health_check())

        assert "status" in health
        assert "stats" in health
        assert "expired_entries" in health
        assert "capacity_usage" in health
        assert "dependencies_tracked" in health

    @patch('opera_cloud_mcp.utils.cache_manager.datetime')
    def test_cleanup_expired(self, mock_datetime):
        """Test cleanup of expired entries."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        mock_now = datetime.now(UTC)
        mock_datetime.now.return_value = mock_now

        # Add an expired entry
        cache_key = "HOTEL123:expired_data:EXPIRED001"
        expired_entry = CacheEntry(
            key=cache_key,
            value={"data": "expired"},
            created_at=mock_now - timedelta(hours=1),
            expires_at=mock_now - timedelta(minutes=1)  # Already expired
        )
        cache_manager._memory_cache[cache_key] = expired_entry

        # Add a valid entry
        asyncio.run(
            cache_manager.set("valid_data", "VALID001", {"data": "valid"})
        )

        # Clean up expired entries
        cleaned_count = asyncio.run(cache_manager.cleanup_expired())

        assert cleaned_count == 1
        assert cache_key not in cache_manager._memory_cache
        assert len(cache_manager._memory_cache) == 1  # Only valid entry remains

    def test_cache_close(self):
        """Test cache manager cleanup."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        # Add some data
        asyncio.run(
            cache_manager.set("test_data", "TEST001", {"value": "test"})
        )

        # Close the cache manager
        asyncio.run(cache_manager.close())

        # Verify cleanup
        assert cache_manager._memory_cache == {}
        assert cache_manager._dependency_map == {}
        if cache_manager._stats:
            assert cache_manager._stats == {}

    def test_cache_configurations(self):
        """Test predefined cache configurations."""
        cache_manager = OperaCacheManager(hotel_id="HOTEL123")

        # Check that predefined configurations exist
        assert "guest_profile" in cache_manager.CACHE_CONFIGS
        assert "room_status" in cache_manager.CACHE_CONFIGS
        assert "reservation" in cache_manager.CACHE_CONFIGS
        assert "rate_codes" in cache_manager.CACHE_CONFIGS
        assert "room_types" in cache_manager.CACHE_CONFIGS
        assert "daily_reports" in cache_manager.CACHE_CONFIGS
        assert "financial_transactions" in cache_manager.CACHE_CONFIGS

        # Check specific configuration values
        guest_config = cache_manager.CACHE_CONFIGS["guest_profile"]
        assert guest_config.ttl_seconds == 3600  # 1 hour
        assert guest_config.invalidation_strategy == InvalidationStrategy.EVENT_BASED
        assert "guest" in guest_config.tags
