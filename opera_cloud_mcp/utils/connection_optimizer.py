"""
Connection pooling and HTTP client optimization for production workloads.

Provides advanced connection management, monitoring, and optimization
specifically tuned for OPERA Cloud API patterns.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetrics:
    """Connection pool metrics."""

    total_requests: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    connection_timeouts: int = 0
    avg_response_time: float = 0.0
    peak_connections: int = 0
    last_reset: float = 0.0


@dataclass
class EndpointMetrics:
    """Per-endpoint performance metrics."""

    request_count: int = 0
    avg_response_time: float = 0.0
    error_count: int = 0
    last_error_time: float | None = None
    success_rate: float = 1.0


class ConnectionPoolOptimizer:
    """
    Advanced connection pool optimizer for OPERA Cloud APIs.

    Features:
    - Dynamic pool sizing based on load patterns
    - Per-endpoint connection affinity
    - Health monitoring and automatic recovery
    - Production-optimized timeouts and limits
    """

    def __init__(
        self,
        base_url: str,
        hotel_id: str,
        initial_pool_size: int = 20,
        max_pool_size: int = 100,
        min_pool_size: int = 5,
        monitoring_window_seconds: int = 300,
    ):
        """
        Initialize connection pool optimizer.

        Args:
            base_url: Base API URL
            hotel_id: Hotel identifier
            initial_pool_size: Starting pool size
            max_pool_size: Maximum connections
            min_pool_size: Minimum connections to maintain
            monitoring_window_seconds: Metrics collection window
        """
        self.base_url = base_url
        self.hotel_id = hotel_id
        self.initial_pool_size = initial_pool_size
        self.max_pool_size = max_pool_size
        self.min_pool_size = min_pool_size
        self.monitoring_window = monitoring_window_seconds

        # Connection metrics
        self.metrics = ConnectionMetrics()
        self.endpoint_metrics: dict[str, EndpointMetrics] = defaultdict(EndpointMetrics)

        # Performance tracking
        self._response_times: list[float] = []
        self._request_times: list[float] = []

        # Adaptive settings
        self._current_pool_size = initial_pool_size
        self._last_optimization = time.time()
        self._optimization_interval = 60.0  # Optimize every minute

        # Client instance cache
        self._clients: dict[str, httpx.AsyncClient] = {}
        self._client_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        logger.info(
            "Connection optimizer initialized",
            extra={
                "base_url": base_url,
                "hotel_id": hotel_id,
                "initial_pool_size": initial_pool_size,
                "max_pool_size": max_pool_size,
            },
        )

    def get_optimized_client_config(
        self, endpoint_pattern: str | None = None
    ) -> dict[str, Any]:
        """
        Get optimized HTTP client configuration.

        Args:
            endpoint_pattern: Endpoint pattern for specialized optimization

        Returns:
            Configuration dictionary for httpx.AsyncClient
        """
        # Base configuration optimized for OPERA Cloud
        config = {
            "timeout": httpx.Timeout(
                connect=10.0,  # Fast connection timeout
                read=45.0,  # Generous read for complex queries
                write=15.0,  # Standard write timeout
                pool=60.0,  # Pool management timeout
            ),
            "limits": httpx.Limits(
                max_connections=self._current_pool_size,
                max_keepalive_connections=max(self._current_pool_size // 2, 10),
                keepalive_expiry=30.0,  # Keep connections alive for 30 seconds
            ),
            "http2": True,  # Enable HTTP/2 for performance
            "verify": True,  # Always verify SSL
            "follow_redirects": True,
            "headers": {
                "User-Agent": f"OPERA-Cloud-MCP/{self.hotel_id}",
                "Connection": "keep-alive",
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json",
            },
        }

        # Endpoint-specific optimizations
        if endpoint_pattern:
            if "reservation" in endpoint_pattern.lower():
                # Reservations may return large datasets
                config["timeout"] = httpx.Timeout(
                    connect=10.0,
                    read=60.0,  # Longer read timeout
                    write=20.0,
                    pool=90.0,
                )
            elif "report" in endpoint_pattern.lower():
                # Reports can be very slow
                config["timeout"] = httpx.Timeout(
                    connect=15.0,
                    read=120.0,  # Very long read timeout
                    write=30.0,
                    pool=150.0,
                )
            elif (
                "real-time" in endpoint_pattern.lower()
                or "status" in endpoint_pattern.lower()
            ):
                # Real-time data needs fast responses
                config["timeout"] = httpx.Timeout(
                    connect=5.0,
                    read=15.0,  # Fast read timeout
                    write=10.0,
                    pool=30.0,
                )

        return config

    async def get_optimized_client(
        self, endpoint_pattern: str | None = None, client_id: str | None = None
    ) -> httpx.AsyncClient:
        """
        Get an optimized HTTP client instance.

        Args:
            endpoint_pattern: Pattern for endpoint-specific optimization
            client_id: Unique identifier for client caching

        Returns:
            Optimized httpx.AsyncClient instance
        """
        # Generate client key
        if client_id is None:
            client_id = f"default_{endpoint_pattern or 'general'}"

        # Check if we have a cached client
        async with self._client_locks[client_id]:
            if client_id in self._clients:
                client = self._clients[client_id]
                # Check if client is still healthy
                if not client.is_closed:
                    return client
                else:
                    # Client is closed, remove from cache
                    del self._clients[client_id]

            # Create new optimized client
            config = self.get_optimized_client_config(endpoint_pattern)
            client = httpx.AsyncClient(base_url=self.base_url, **config)

            self._clients[client_id] = client

            logger.debug(
                "Created optimized client",
                extra={
                    "client_id": client_id,
                    "endpoint_pattern": endpoint_pattern,
                    "pool_size": self._current_pool_size,
                },
            )

            return client

    def record_request_metrics(
        self,
        endpoint: str,
        response_time: float,
        success: bool,
        error_type: str | None = None,
    ) -> None:
        """
        Record request metrics for optimization.

        Args:
            endpoint: API endpoint
            response_time: Request response time in seconds
            success: Whether request was successful
            error_type: Type of error if not successful
        """
        now = time.time()

        # Update global metrics
        self.metrics.total_requests += 1
        self._response_times.append(response_time)
        self._request_times.append(now)

        # Keep only recent response times
        cutoff_time = now - self.monitoring_window
        self._response_times = [
            rt
            for rt, t in zip(self._response_times, self._request_times, strict=False)
            if t > cutoff_time
        ]
        self._request_times = [t for t in self._request_times if t > cutoff_time]

        # Update average response time
        if self._response_times:
            self.metrics.avg_response_time = sum(self._response_times) / len(
                self._response_times
            )

        # Update endpoint metrics
        endpoint_key = self._normalize_endpoint(endpoint)
        endpoint_metric = self.endpoint_metrics[endpoint_key]
        endpoint_metric.request_count += 1

        # Update endpoint average response time
        current_avg = endpoint_metric.avg_response_time
        count = endpoint_metric.request_count
        endpoint_metric.avg_response_time = (
            (current_avg * (count - 1)) + response_time
        ) / count

        # Update error metrics
        if not success:
            endpoint_metric.error_count += 1
            endpoint_metric.last_error_time = now

            if error_type == "timeout":
                self.metrics.connection_timeouts += 1
            else:
                self.metrics.failed_connections += 1

        # Update success rate
        endpoint_metric.success_rate = 1.0 - (
            endpoint_metric.error_count / endpoint_metric.request_count
        )

        # Check if we need to optimize
        if now - self._last_optimization > self._optimization_interval:
            asyncio.create_task(self._optimize_pool_size())

    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint for metrics grouping."""
        # Remove query parameters and IDs for grouping
        parts = endpoint.strip("/").split("/")
        normalized_parts = []

        for part in parts:
            # Replace what looks like IDs with placeholder
            if (
                part.isdigit()
                or len(part) > 20  # Long strings likely to be IDs
                or "-" in part
                and len(part) > 10
            ):  # UUID-like patterns
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)

        return "/".join(normalized_parts)

    async def _optimize_pool_size(self) -> None:
        """
        Optimize connection pool size based on current metrics.
        """
        self._last_optimization = time.time()
        current_time = time.time()

        # Calculate recent request rate (requests per second)
        recent_requests = len(
            [t for t in self._request_times if current_time - t <= 60]
        )
        request_rate = recent_requests / 60.0

        # Calculate target pool size based on request rate and response times
        avg_response_time = self.metrics.avg_response_time
        if avg_response_time > 0:
            # Estimate concurrent requests: rate * average response time
            estimated_concurrent = request_rate * avg_response_time

            # Add buffer for peak loads (50% more than estimated)
            target_pool_size = int(estimated_concurrent * 1.5)

            # Apply bounds
            target_pool_size = max(
                self.min_pool_size, min(target_pool_size, self.max_pool_size)
            )

            # Only adjust if significant change (avoid thrashing)
            size_diff = abs(target_pool_size - self._current_pool_size)
            if size_diff > 2:  # At least 2 connections difference
                old_size = self._current_pool_size
                self._current_pool_size = target_pool_size

                logger.info(
                    "Optimized connection pool size",
                    extra={
                        "old_size": old_size,
                        "new_size": target_pool_size,
                        "request_rate": request_rate,
                        "avg_response_time": avg_response_time,
                        "estimated_concurrent": estimated_concurrent,
                    },
                )

                # Update existing clients with new limits
                await self._update_client_limits()

    async def _update_client_limits(self) -> None:
        """Update limits on existing clients."""
        # Implementation would update existing client limits
        pass

    def get_pool_health_status(self) -> dict[str, Any]:
        """
        Get current connection pool health status.

        Returns:
            Dictionary with health metrics
        """
        now = time.time()
        recent_errors = sum(
            1
            for metric in self.endpoint_metrics.values()
            if metric.last_error_time and (now - metric.last_error_time) < 300
        )

        # Calculate overall health
        total_endpoints = len(self.endpoint_metrics)
        unhealthy_endpoints = sum(
            1
            for metric in self.endpoint_metrics.values()
            if metric.success_rate < 0.8  # Less than 80% success rate
        )

        health_score = 1.0
        if total_endpoints > 0:
            health_score = 1.0 - (unhealthy_endpoints / total_endpoints)

        # Determine status
        if health_score >= 0.9:
            status = "healthy"
        elif health_score >= 0.7:
            status = "warning"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "health_score": health_score,
            "current_pool_size": self._current_pool_size,
            "active_clients": len(self._clients),
            "total_requests": self.metrics.total_requests,
            "avg_response_time": self.metrics.avg_response_time,
            "recent_errors": recent_errors,
            "unhealthy_endpoints": unhealthy_endpoints,
            "endpoint_count": total_endpoints,
            "metrics_window": self.monitoring_window,
        }

    def get_endpoint_statistics(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get statistics for top endpoints.

        Args:
            limit: Maximum number of endpoints to return

        Returns:
            List of endpoint statistics
        """
        # Sort endpoints by request count
        sorted_endpoints = sorted(
            self.endpoint_metrics.items(),
            key=lambda x: x[1].request_count,
            reverse=True,
        )

        return [
            {
                "endpoint": endpoint,
                "request_count": metrics.request_count,
                "avg_response_time": metrics.avg_response_time,
                "error_count": metrics.error_count,
                "success_rate": metrics.success_rate,
                "last_error_time": metrics.last_error_time,
            }
            for endpoint, metrics in sorted_endpoints[:limit]
        ]

    async def cleanup(self) -> None:
        """Clean up all clients and resources."""
        logger.info("Cleaning up connection optimizer")

        # Close all cached clients
        for client_id, client in self._clients.items():
            try:
                await client.aclose()
                logger.debug(f"Closed client: {client_id}")
            except Exception as e:
                logger.warning(f"Error closing client {client_id}: {e}")

        self._clients.clear()
        self._client_locks.clear()

        # Clear metrics
        self.endpoint_metrics.clear()
        self._response_times.clear()
        self._request_times.clear()

        logger.info("Connection optimizer cleanup completed")
