"""
Advanced caching system for OPERA Cloud API responses.

Provides multi-layer caching with intelligent invalidation strategies
optimized for hotel operations data patterns.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level enumeration."""

    MEMORY = "memory"
    PERSISTENT = "persistent"
    DISTRIBUTED = "distributed"


class InvalidationStrategy(Enum):
    """Cache invalidation strategy."""

    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    DEPENDENCY_BASED = "dependency_based"
    MANUAL = "manual"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime | None = None
    dependencies: list[str] | None = None
    tags: list[str] | None = None
    size_bytes: int = 0


@dataclass
class CacheConfig:
    """Cache configuration for different data types."""

    ttl_seconds: int
    max_size: int
    invalidation_strategy: InvalidationStrategy
    dependencies: list[str] | None = None
    tags: list[str] | None = None
    compress: bool = False
    serialize_json: bool = True


class OperaCacheManager:
    """
    Advanced caching manager optimized for OPERA Cloud API responses.

    Features:
    - Multi-layer caching (memory, persistent)
    - Intelligent TTL based on data type
    - Dependency-based invalidation
    - Hotel-specific cache isolation
    - Performance monitoring
    """

    # Predefined cache configurations for different data types
    CACHE_CONFIGS = {
        # Guest profiles change infrequently
        "guest_profile": CacheConfig(
            ttl_seconds=3600,  # 1 hour
            max_size=1000,
            invalidation_strategy=InvalidationStrategy.EVENT_BASED,
            dependencies=["guest_updates", "profile_merges"],
            tags=["guest", "profile", "crm"],
        ),
        # Room status changes frequently
        "room_status": CacheConfig(
            ttl_seconds=300,  # 5 minutes
            max_size=500,
            invalidation_strategy=InvalidationStrategy.TIME_BASED,
            dependencies=["housekeeping_updates", "maintenance"],
            tags=["rooms", "housekeeping", "inventory"],
        ),
        # Reservations can change but not as frequently as room status
        "reservation": CacheConfig(
            ttl_seconds=900,  # 15 minutes
            max_size=2000,
            invalidation_strategy=InvalidationStrategy.DEPENDENCY_BASED,
            dependencies=["reservation_updates", "cancellations", "modifications"],
            tags=["reservations", "bookings"],
        ),
        # Rate codes are relatively static
        "rate_codes": CacheConfig(
            ttl_seconds=7200,  # 2 hours
            max_size=200,
            invalidation_strategy=InvalidationStrategy.TIME_BASED,
            tags=["rates", "pricing", "revenue"],
        ),
        # Room types are very static
        "room_types": CacheConfig(
            ttl_seconds=14400,  # 4 hours
            max_size=100,
            invalidation_strategy=InvalidationStrategy.MANUAL,
            tags=["inventory", "room_types", "configuration"],
        ),
        # Daily operational reports - short cache
        "daily_reports": CacheConfig(
            ttl_seconds=600,  # 10 minutes
            max_size=50,
            invalidation_strategy=InvalidationStrategy.TIME_BASED,
            tags=["reports", "operations", "analytics"],
        ),
        # Financial transactions - event-based invalidation
        "financial_transactions": CacheConfig(
            ttl_seconds=1800,  # 30 minutes
            max_size=1000,
            invalidation_strategy=InvalidationStrategy.EVENT_BASED,
            dependencies=["payment_processing", "folio_updates", "charges"],
            tags=["financial", "transactions", "billing"],
        ),
    }

    def __init__(
        self,
        hotel_id: str,
        enable_persistent: bool = True,
        enable_monitoring: bool = True,
        max_memory_size: int = 10000,
    ):
        """
        Initialize cache manager.

        Args:
            hotel_id: Hotel identifier for cache isolation
            enable_persistent: Enable persistent caching
            enable_monitoring: Enable cache performance monitoring
            max_memory_size: Maximum number of entries in memory cache
        """
        self.hotel_id = hotel_id
        self.enable_persistent = enable_persistent
        self.enable_monitoring = enable_monitoring
        self.max_memory_size = max_memory_size

        # Memory cache storage
        self._memory_cache: dict[str, CacheEntry] = {}

        # Performance monitoring
        self._stats = (
            {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "invalidations": 0,
                "size_bytes": 0,
            }
            if enable_monitoring
            else None
        )

        # Dependency tracking
        self._dependency_map: dict[str, list[str]] = {}

        # Background cleanup task
        self._cleanup_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

        logger.info(
            "Cache manager initialized",
            extra={
                "hotel_id": hotel_id,
                "persistent_enabled": enable_persistent,
                "monitoring_enabled": enable_monitoring,
                "max_memory_size": max_memory_size,
            },
        )

    def _generate_cache_key(
        self, data_type: str, identifier: str, params: dict[str, Any] | None = None
    ) -> str:
        """
        Generate a consistent cache key.

        Args:
            data_type: Type of data being cached
            identifier: Unique identifier for the data
            params: Additional parameters that affect the data

        Returns:
            Generated cache key
        """
        key_parts = [self.hotel_id, data_type, identifier]

        if params:
            # Sort parameters for consistent key generation
            param_str = json.dumps(params, sort_keys=True, default=str)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_parts.append(param_hash)

        return ":".join(key_parts)

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of cached value in bytes."""
        try:
            if isinstance(value, str):
                return len(value.encode("utf-8"))
            elif isinstance(value, (dict, list)):
                return len(json.dumps(value, default=str).encode("utf-8"))
            else:
                return len(str(value).encode("utf-8"))
        except Exception:
            return 0

    async def get(
        self,
        data_type: str,
        identifier: str,
        params: dict[str, Any] | None = None,
        default: Any = None,
    ) -> Any:
        """
        Get value from cache.

        Args:
            data_type: Type of data
            identifier: Data identifier
            params: Additional parameters
            default: Default value if not found

        Returns:
            Cached value or default
        """
        cache_key = self._generate_cache_key(data_type, identifier, params)

        # Check memory cache first
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]

            # Check expiration
            if entry.expires_at > datetime.utcnow():
                # Update access statistics
                entry.access_count += 1
                entry.last_accessed = datetime.utcnow()

                if self._stats:
                    self._stats["hits"] += 1

                logger.debug(
                    "Cache hit",
                    extra={
                        "cache_key": cache_key,
                        "data_type": data_type,
                        "access_count": entry.access_count,
                    },
                )

                return entry.value
            else:
                # Expired entry
                await self._remove_entry(cache_key, "expired")

        if self._stats:
            self._stats["misses"] += 1

        logger.debug(
            "Cache miss", extra={"cache_key": cache_key, "data_type": data_type}
        )

        return default

    async def set(
        self,
        data_type: str,
        identifier: str,
        value: Any,
        params: dict[str, Any] | None = None,
        ttl_override: int | None = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            data_type: Type of data
            identifier: Data identifier
            value: Value to cache
            params: Additional parameters
            ttl_override: Override default TTL

        Returns:
            True if successfully cached
        """
        cache_key = self._generate_cache_key(data_type, identifier, params)

        # Get cache configuration
        config = self.CACHE_CONFIGS.get(
            data_type,
            CacheConfig(
                ttl_seconds=600,  # Default 10 minutes
                max_size=100,
                invalidation_strategy=InvalidationStrategy.TIME_BASED,
            ),
        )

        # Calculate expiration
        ttl = ttl_override or config.ttl_seconds
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        # Calculate size
        size_bytes = self._calculate_size(value)

        # Create cache entry
        entry = CacheEntry(
            key=cache_key,
            value=value,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            dependencies=config.dependencies,
            tags=config.tags,
            size_bytes=size_bytes,
        )

        # Check if we need to evict entries
        await self._ensure_capacity()

        # Store in memory cache
        self._memory_cache[cache_key] = entry

        # Update dependency tracking
        if config.dependencies:
            for dep in config.dependencies:
                if dep not in self._dependency_map:
                    self._dependency_map[dep] = []
                if cache_key not in self._dependency_map[dep]:
                    self._dependency_map[dep].append(cache_key)

        # Update statistics
        if self._stats:
            self._stats["size_bytes"] += size_bytes

        logger.debug(
            "Cache set",
            extra={
                "cache_key": cache_key,
                "data_type": data_type,
                "ttl_seconds": ttl,
                "size_bytes": size_bytes,
            },
        )

        return True

    async def invalidate(
        self,
        data_type: str | None = None,
        identifier: str | None = None,
        dependency: str | None = None,
        tags: list[str] | None = None,
    ) -> int:
        """
        Invalidate cache entries.

        Args:
            data_type: Invalidate specific data type
            identifier: Invalidate specific identifier
            dependency: Invalidate by dependency
            tags: Invalidate by tags

        Returns:
            Number of entries invalidated
        """
        invalidated_count = 0
        keys_to_remove = []

        # Invalidate by dependency
        if dependency and dependency in self._dependency_map:
            keys_to_remove.extend(self._dependency_map[dependency])
            del self._dependency_map[dependency]

        # Invalidate by tags or data type
        if data_type or tags:
            for cache_key, entry in self._memory_cache.items():
                should_invalidate = False

                # Check data type
                if data_type and cache_key.split(":")[1] == data_type:
                    should_invalidate = True

                # Check tags
                if tags and entry.tags:
                    if any(tag in entry.tags for tag in tags):
                        should_invalidate = True

                if should_invalidate:
                    keys_to_remove.append(cache_key)

        # Remove specific key
        if identifier:
            cache_key = self._generate_cache_key(data_type or "", identifier)
            if cache_key in self._memory_cache:
                keys_to_remove.append(cache_key)

        # Remove all identified keys
        for cache_key in set(keys_to_remove):  # Remove duplicates
            if cache_key in self._memory_cache:
                await self._remove_entry(cache_key, "invalidated")
                invalidated_count += 1

        if self._stats:
            self._stats["invalidations"] += invalidated_count

        logger.info(
            "Cache invalidation completed",
            extra={
                "invalidated_count": invalidated_count,
                "data_type": data_type,
                "dependency": dependency,
                "tags": tags,
            },
        )

        return invalidated_count

    async def _remove_entry(self, cache_key: str, reason: str) -> None:
        """Remove cache entry and update statistics."""
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]

            # Update statistics
            if self._stats:
                self._stats["size_bytes"] -= entry.size_bytes
                if reason == "evicted":
                    self._stats["evictions"] += 1

            # Remove from dependency map
            if entry.dependencies:
                for dep in entry.dependencies:
                    if (
                        dep in self._dependency_map
                        and cache_key in self._dependency_map[dep]
                    ):
                        self._dependency_map[dep].remove(cache_key)
                        if not self._dependency_map[dep]:
                            del self._dependency_map[dep]

            del self._memory_cache[cache_key]

    async def _ensure_capacity(self) -> None:
        """Ensure cache doesn't exceed maximum capacity."""
        if len(self._memory_cache) < self.max_memory_size:
            return

        # Find entries to evict (LRU-style)
        now = datetime.utcnow()
        entries_with_score = []

        for cache_key, entry in self._memory_cache.items():
            # Score based on age, access count, and last access
            age_score = (now - entry.created_at).total_seconds()
            access_score = 1.0 / max(entry.access_count, 1)
            last_access_score = 0

            if entry.last_accessed:
                last_access_score = (now - entry.last_accessed).total_seconds()

            # Combined score (higher = more likely to evict)
            score = age_score + access_score + last_access_score
            entries_with_score.append((cache_key, score))

        # Sort by score and evict oldest/least used entries
        entries_with_score.sort(key=lambda x: x[1], reverse=True)
        entries_to_evict = len(self._memory_cache) - (self.max_memory_size // 2)

        for cache_key, _ in entries_with_score[:entries_to_evict]:
            await self._remove_entry(cache_key, "evicted")

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        now = datetime.utcnow()
        expired_keys = []

        for cache_key, entry in self._memory_cache.items():
            if entry.expires_at <= now:
                expired_keys.append(cache_key)

        for cache_key in expired_keys:
            await self._remove_entry(cache_key, "expired")

        return len(expired_keys)

    def get_stats(self) -> dict[str, Any] | None:
        """Get cache statistics."""
        if not self._stats:
            return None

        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests) if total_requests > 0 else 0.0

        return {
            **self._stats,
            "entries_count": len(self._memory_cache),
            "hit_rate": hit_rate,
            "dependencies_count": len(self._dependency_map),
            "hotel_id": self.hotel_id,
        }

    async def health_check(self) -> dict[str, Any]:
        """Perform cache health check."""
        stats = self.get_stats() or {}
        now = datetime.utcnow()
        expired_count = 0

        # Count expired entries
        for entry in self._memory_cache.values():
            if entry.expires_at <= now:
                expired_count += 1

        # Determine health status
        hit_rate = stats.get("hit_rate", 0.0)
        entries_count = len(self._memory_cache)

        status = "healthy"
        if hit_rate < 0.3:
            status = "low_hit_rate"
        elif entries_count > self.max_memory_size * 0.9:
            status = "near_capacity"
        elif expired_count > entries_count * 0.2:
            status = "many_expired"

        return {
            "status": status,
            "stats": stats,
            "expired_entries": expired_count,
            "capacity_usage": entries_count / self.max_memory_size,
            "dependencies_tracked": len(self._dependency_map),
        }

    async def start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._background_cleanup())

    async def _background_cleanup(self) -> None:
        """Background task for cache cleanup."""
        logger.info("Started cache background cleanup task")

        while not self._shutdown_event.is_set():
            try:
                # Cleanup expired entries every 5 minutes
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=300.0)
            except TimeoutError:
                expired_count = await self.cleanup_expired()
                if expired_count > 0:
                    logger.debug(f"Cleaned up {expired_count} expired cache entries")

        logger.info("Cache background cleanup task stopped")

    async def close(self) -> None:
        """Clean up cache manager."""
        logger.info("Closing cache manager")

        # Stop background tasks
        self._shutdown_event.set()
        if self._cleanup_task:
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=5.0)
            except TimeoutError:
                self._cleanup_task.cancel()

        # Clear cache
        self._memory_cache.clear()
        self._dependency_map.clear()

        if self._stats:
            self._stats.clear()

        logger.info("Cache manager closed")
