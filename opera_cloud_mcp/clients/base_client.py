"""
Base API client for OPERA Cloud services.

Provides common functionality including authentication, retry logic,
error handling, and request/response processing for all API clients.
"""

import asyncio
import contextlib
import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel, Field

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler
from opera_cloud_mcp.auth.secure_oauth_handler import SecureOAuthHandler
from opera_cloud_mcp.config.settings import Settings, get_settings
from opera_cloud_mcp.utils.cache_manager import OperaCacheManager
from opera_cloud_mcp.utils.exceptions import (
    APIError,
    AuthenticationError,
    DataError,
    OperaCloudError,
    RateLimitError,
    ResourceNotFoundError,
    TimeoutError,
    ValidationError,
)
from opera_cloud_mcp.utils.observability import DistributedTracer, get_observability

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern implementation for API resilience."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception types that trigger circuit breaking
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        # State management
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self._state == "open":
                if self._should_attempt_reset():
                    self._state = "half-open"
                else:
                    raise OperaCloudError("Circuit breaker is open")

            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except self.expected_exception:
                await self._on_failure()
                raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self._last_failure_time is not None
            and time.time() - self._last_failure_time >= self.recovery_timeout
        )

    async def _on_success(self) -> None:
        """Handle successful operation."""
        self._failure_count = 0
        self._state = "closed"

    async def _on_failure(self) -> None:
        """Handle failed operation."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self._last_failure_time,
            "recovery_timeout": self.recovery_timeout,
        }


class RequestMetrics(BaseModel):
    """Metrics for API request monitoring."""

    method: str
    endpoint: str
    status_code: int | None = None
    duration_ms: float
    request_size_bytes: int = 0
    response_size_bytes: int = 0
    retry_count: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    hotel_id: str | None = None
    error_type: str | None = None


class APIResponse(BaseModel):
    """Standard API response model."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    status_code: int | None = None
    metrics: RequestMetrics | None = None
    headers: dict[str, str] | None = None


class RateLimiter:
    """Token bucket rate limiter for API requests."""

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_capacity: int = 20,
        time_window: int = 60,
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
            burst_capacity: Maximum burst capacity
            time_window: Time window for rate limiting in seconds
        """
        self.requests_per_second = requests_per_second
        self.burst_capacity = burst_capacity
        self.time_window = time_window
        self._tokens = float(burst_capacity)
        self._last_update = time.time()
        self._lock = asyncio.Lock()

        # Track request history for detailed rate limiting
        self._request_history: deque[float] = deque(maxlen=1000)

    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket."""
        async with self._lock:
            now = time.time()

            # Add tokens based on time elapsed
            elapsed = now - self._last_update
            tokens_to_add = elapsed * self.requests_per_second
            self._tokens = min(self.burst_capacity, self._tokens + tokens_to_add)
            self._last_update = now

            # Check if we have enough tokens
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._request_history.append(now)
                return True

            return False

    async def wait_if_needed(self, tokens: int = 1) -> float:
        """Wait if rate limit would be exceeded."""
        if await self.acquire(tokens):
            return 0.0

        # Calculate wait time
        wait_time = tokens / self.requests_per_second
        await asyncio.sleep(wait_time)
        return wait_time

    def get_stats(self) -> dict[str, Any]:
        """Get rate limiter statistics."""
        now = time.time()
        recent_requests = sum(
            1 for t in self._request_history if now - t <= self.time_window
        )

        return {
            "current_tokens": self._tokens,
            "max_tokens": self.burst_capacity,
            "requests_per_second": self.requests_per_second,
            "recent_requests": recent_requests,
            "time_window": self.time_window,
        }


class HealthMonitor:
    """Monitor API client health and collect metrics."""

    def __init__(self, max_history: int = 1000) -> None:
        """
        Initialize health monitor.

        Args:
            max_history: Maximum number of requests to track
        """
        self.max_history = max_history
        self._request_history: deque[RequestMetrics] = deque(maxlen=max_history)
        self._error_counts: dict[str, int] = defaultdict(int)
        self._status_code_counts: dict[int, int] = defaultdict(int)
        self._endpoint_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_duration": 0.0,
                "error_count": 0,
                "avg_duration": 0.0,
            }
        )
        self._lock = asyncio.Lock()

    async def record_request(self, metrics: RequestMetrics) -> None:
        """Record request metrics."""
        async with self._lock:
            self._request_history.append(metrics)

            # Update error counts
            if metrics.error_type:
                self._error_counts[metrics.error_type] += 1

            # Update status code counts
            if metrics.status_code:
                self._status_code_counts[metrics.status_code] += 1

            # Update endpoint stats
            endpoint_key = f"{metrics.method} {metrics.endpoint}"
            stats = self._endpoint_stats[endpoint_key]
            stats["count"] += 1
            stats["total_duration"] += metrics.duration_ms
            if metrics.error_type:
                stats["error_count"] += 1
            stats["avg_duration"] = stats["total_duration"] / stats["count"]

    def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive health status."""
        now = datetime.now(tz=UTC)
        recent_window = now - timedelta(minutes=5)

        recent_requests = [
            req for req in self._request_history if req.timestamp >= recent_window
        ]

        total_requests = len(self._request_history)
        recent_request_count = len(recent_requests)

        # Calculate error rates
        recent_errors = sum(1 for req in recent_requests if req.error_type)
        error_rate = (
            (recent_errors / recent_request_count) if recent_request_count > 0 else 0
        )

        # Calculate average response time
        if recent_requests:
            avg_response_time = sum(req.duration_ms for req in recent_requests) / len(
                recent_requests
            )
        else:
            avg_response_time = 0

        # Determine health status
        health_status = "healthy"
        if error_rate > 0.1:  # More than 10% errors
            health_status = "degraded"
        elif error_rate > 0.05:  # More than 5% errors
            health_status = "warning"

        return {
            "status": health_status,
            "total_requests": total_requests,
            "recent_requests": recent_request_count,
            "error_rate": error_rate,
            "avg_response_time_ms": avg_response_time,
            "error_counts": self._error_counts.copy(),
            "status_code_counts": self._status_code_counts.copy(),
            "top_endpoints": dict(
                sorted(
                    self._endpoint_stats.items(),
                    key=lambda x: x[1]["count"],
                    reverse=True,
                )[:10]
            ),
            "timestamp": now.isoformat(),
        }


class DataTransformer:
    """Utility class for request/response data transformation."""

    @staticmethod
    def sanitize_request_data(data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize request data by removing None values and empty strings."""
        if not isinstance(data, dict):
            # This shouldn't happen based on the type annotation, but just in case
            return {}

        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if value is None or value == "":
                continue
            elif isinstance(value, dict):
                cleaned_nested = DataTransformer.sanitize_request_data(value)
                if cleaned_nested:
                    cleaned[key] = cleaned_nested
            elif isinstance(value, list):
                cleaned_list: list[Any] = [
                    DataTransformer.sanitize_request_data(item)
                    if isinstance(item, dict)
                    else item
                    for item in value
                    if item is not None
                ]
                if cleaned_list:
                    cleaned[key] = cleaned_list
            else:
                cleaned[key] = value

        return cleaned

    @staticmethod
    def _get_nested_field_parent(
        data: dict[str, Any], keys: list[str]
    ) -> dict[str, Any] | None:
        """Get the parent dictionary of a nested field path."""
        current = data
        # Navigate to the parent of the target field
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current if isinstance(current, dict) else None

    @staticmethod
    def _apply_field_transformation(
        parent_dict: dict[str, Any],
        final_key: str,
        transform_func: Callable[[Any], Any],
    ) -> None:
        """Apply transformation to a field."""
        if final_key in parent_dict:
            parent_dict[final_key] = transform_func(parent_dict[final_key])

    @staticmethod
    def transform_response_data(
        data: dict[str, Any],
        transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> dict[str, Any]:
        """Transform response data using provided transformation functions."""
        if not transformations or not isinstance(data, dict):
            return data if isinstance(data, dict) else {}

        transformed = data.copy()
        for field_path, transform_func in transformations.items():
            try:
                # Support nested field paths like "guest.profile.name"
                keys = field_path.split(".")

                # Get parent dictionary
                parent_dict = DataTransformer._get_nested_field_parent(
                    transformed, keys
                )
                if parent_dict is not None:
                    # Apply transformation to the target field
                    final_key = keys[-1]
                    DataTransformer._apply_field_transformation(
                        parent_dict, final_key, transform_func
                    )

            except Exception as e:
                logger.warning(f"Failed to transform field {field_path}: {e}")

        return transformed

    def _mask_sensitive_data(
        self, data: dict[str, Any], sensitive_fields: set[str] | None = None
    ) -> dict[str, Any]:
        """Mask sensitive data in logs and responses."""
        if sensitive_fields is None:
            sensitive_fields = set[str]()

        def _mask_recursive(obj: Any) -> Any:
            if isinstance(obj, dict):
                masked = {}
                for key, value in obj.items():
                    key_lower = key.lower()
                    if any(
                        sensitive_field in key_lower
                        for sensitive_field in sensitive_fields
                    ):
                        masked[key] = "***MASKED***"
                    else:
                        masked[key] = _mask_recursive(value)
                return masked
            elif isinstance(obj, list):
                return [_mask_recursive(item) for item in obj]
            return obj

        return _mask_recursive(data)  # type: ignore


class BaseAPIClient:
    """
    Production-ready base client for all OPERA Cloud API clients.

    Features:
    - OAuth2 authentication with token caching and refresh
    - Exponential backoff retry logic with jitter
    - Comprehensive error handling and custom exceptions
    - Request/response logging and monitoring
    - Rate limiting with token bucket algorithm
    - Connection pooling and timeout management
    - Data transformation and sanitization utilities
    - Health monitoring and metrics collection
    - Circuit breaker pattern for resilience
    - Async context management for proper resource cleanup
    """

    def __init__(
        self,
        auth_handler: OAuthHandler | SecureOAuthHandler,
        hotel_id: str,
        settings: Settings | None = None,
        enable_rate_limiting: bool = True,
        enable_monitoring: bool = True,
        enable_caching: bool = True,
        requests_per_second: float = 10.0,
        burst_capacity: int = 20,
    ) -> None:
        """
        Initialize base API client.

        Args:
            auth_handler: OAuth2 authentication handler
            hotel_id: Hotel identifier for API requests
            settings: Optional settings instance
            enable_rate_limiting: Enable request rate limiting
            enable_monitoring: Enable health monitoring and metrics
            enable_caching: Enable response caching
            requests_per_second: Maximum requests per second (if rate limiting enabled)
            burst_capacity: Maximum burst capacity (if rate limiting enabled)
        """
        self.auth = auth_handler
        self.hotel_id = hotel_id
        self.settings = settings or get_settings()
        self._session: httpx.AsyncClient | None = None
        self._session_lock = asyncio.Lock()

        # Rate limiter (can be None if disabled)
        self._rate_limiter: RateLimiter | None = None

        # Health monitor (can be None if disabled)
        self._health_monitor: HealthMonitor | None = None

        # Cache manager (can be None if disabled)
        self._cache_manager: OperaCacheManager | None = None

        # Distributed tracer (can be None if tracing is disabled)
        self._tracer: DistributedTracer | None = None

        # Data transformer for request/response processing
        self._data_transformer: DataTransformer

        # Connection limits for HTTP client pooling
        self._connection_limits: httpx.Limits

        # Timeout configuration for HTTP requests
        self._timeout_config: httpx.Timeout

        # Rate limiting
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_monitoring = enable_monitoring

        # Response caching
        self.enable_caching = enable_caching
        if enable_caching:
            self._cache_manager = OperaCacheManager(
                hotel_id=hotel_id,
                enable_persistent=settings.enable_cache if settings else True,
                max_memory_size=settings.cache_max_memory
                if settings and hasattr(settings, "cache_max_memory")
                else 10000,
            )
        else:
            self._cache_manager = None

        # Data transformer
        self._data_transformer = DataTransformer()

        # Connection pool configuration
        self._connection_limits = httpx.Limits(
            max_connections=50,  # Increased for better concurrency
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        )

        # Request timeout configuration
        self._timeout_config = httpx.Timeout(
            connect=10.0,  # Connection timeout
            read=self.settings.request_timeout,  # Read timeout
            write=10.0,  # Write timeout
            pool=5.0,  # Pool timeout
        )

        # Tracing
        try:
            self._tracer = get_observability().tracer
        except Exception:
            self._tracer = None
            logger.warning("Tracing not available - observability not initialized")

    async def __aenter__(self) -> "BaseAPIClient":
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is initialized with proper configuration."""
        if self._session is None:
            async with self._session_lock:
                if self._session is None:  # Double-check pattern
                    self._session = httpx.AsyncClient(
                        timeout=self._timeout_config,
                        limits=self._connection_limits,
                        http2=True,  # Enable HTTP/2
                        verify=True,  # SSL verification
                        follow_redirects=True,
                        headers={
                            "User-Agent": "OPERA-Cloud-MCP/1.0 (httpx)",
                            "Accept-Encoding": "gzip, deflate",
                            "Connection": "keep-alive",
                        },
                    )
                    logger.debug(
                        "HTTP session initialized",
                        extra={
                            "timeout_connect": self._timeout_config.connect,
                            "timeout_read": self._timeout_config.read,
                            "max_connections": self._connection_limits.max_connections,
                            "keepalive_connections": (
                                self._connection_limits.max_keepalive_connections
                            ),
                        },
                    )

    async def close(self) -> None:
        """Close HTTP session and cleanup resources."""
        if self._session:
            try:
                await self._session.aclose()
                logger.debug("HTTP session closed successfully")
            except Exception as e:
                logger.warning(f"Error closing HTTP session: {e}")
            finally:
                self._session = None

    @property
    def base_url(self) -> str:
        """Get base API URL."""
        base_url = self.settings.opera_base_url.rstrip("/")
        api_version = self.settings.opera_api_version
        return f"{base_url}/{api_version}"

    def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive client health status."""
        status = {
            "client_initialized": self._session is not None,
            "rate_limiting_enabled": self.enable_rate_limiting,
            "monitoring_enabled": self.enable_monitoring,
            "hotel_id": self.hotel_id,
            "base_url": self.base_url,
        }

        if self._rate_limiter:
            status["rate_limiter"] = self._rate_limiter.get_stats()

        if self._health_monitor:
            status.update(self._health_monitor.get_health_status())

        # Add authentication status
        auth_info = self.auth.get_token_info()
        status["authentication"] = {
            "has_token": auth_info["has_token"],
            "token_status": auth_info["status"],
            "expires_in": auth_info.get("expires_in", 0),
        }

        return status

    async def _log_request(self, method: str, url: str, **kwargs: Any) -> None:
        """Log outgoing request details."""
        # Calculate request size
        request_size = 0
        if "json" in kwargs and kwargs["json"]:
            request_size = len(json.dumps(kwargs["json"]).encode("utf-8"))
        elif "data" in kwargs and kwargs["data"]:
            request_size = len(str(kwargs["data"]).encode("utf-8"))

        # Mask sensitive data for logging
        safe_params = self._data_transformer._mask_sensitive_data(
            kwargs.get("params", {})
        )
        safe_json = self._data_transformer._mask_sensitive_data(kwargs.get("json", {}))

        logger.info(
            f"API Request: {method} {url}",
            extra={
                "method": method,
                "url": url,
                "hotel_id": self.hotel_id,
                "request_size_bytes": request_size,
                "params": safe_params,
                "json_data": safe_json,
                "headers_count": len(kwargs.get("headers", {})),
            },
        )

    async def _log_response(
        self,
        method: str,
        url: str,
        response: httpx.Response,
        duration_ms: float,
        retry_count: int = 0,
    ) -> None:
        """Log response details."""
        response_size = len(response.content) if response.content else 0

        log_data = {
            "method": method,
            "url": url,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "response_size_bytes": response_size,
            "retry_count": retry_count,
            "hotel_id": self.hotel_id,
        }

        if response.status_code >= 400:
            logger.warning(
                f"API Error Response: {method} {url} - {response.status_code}",
                extra=log_data,
            )
        else:
            logger.info(
                f"API Response: {method} {url} - {response.status_code}", extra=log_data
            )

    async def _check_cache(
        self, method: str, endpoint: str, params: dict[str, Any] | None
    ) -> APIResponse | None:
        """Check cache for cached response.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Cached APIResponse if found, None otherwise
        """
        if not self._cache_manager or method.upper() != "GET":
            return None

        cache_key = f"{method}:{endpoint}:{hash(str(params))}"
        cached_response = await self._cache_manager.get("api_response", cache_key)

        if cached_response is not None:
            logger.debug(f"Cache hit for {method} {endpoint}")

            # Record cache hit metrics
            if self._health_monitor:
                metrics = RequestMetrics(
                    method=method,
                    endpoint=endpoint,
                    status_code=200,
                    duration_ms=0.1,  # Negligible time for cache hit
                    request_size_bytes=0,
                    response_size_bytes=len(str(cached_response).encode()),
                    retry_count=0,
                    hotel_id=self.hotel_id,
                    error_type=None,
                )
                await self._health_monitor.record_request(metrics)

            return APIResponse(
                success=True,
                data=cached_response,
                status_code=200,
            )
        return None

    async def _store_cache(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None,
        response_data: Any,
        status_code: int,
    ) -> None:
        """Store successful response in cache.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            response_data: Response data to cache
            status_code: HTTP status code
        """
        if not self._cache_manager or method.upper() != "GET" or status_code != 200:
            return

        cache_key = f"{method}:{endpoint}:{hash(str(params))}"
        ttl = self.settings.cache_ttl if hasattr(self.settings, "cache_ttl") else 300
        await self._cache_manager.set(
            "api_response", cache_key, response_data, ttl_override=ttl
        )
        logger.debug(f"Response cached for {method} {endpoint} with TTL {ttl}s")

    async def _start_tracing(self, method: str, endpoint: str) -> Any:
        """Start distributed tracing span.

        Args:
            method: HTTP method
            endpoint: API endpoint

        Returns:
            Trace context or None
        """
        if not self._tracer:
            return None

        try:
            return self._tracer.start_span(
                f"api.{method.lower()}",
                tags={
                    "http.method": method,
                    "http.url": f"{self.base_url}/{endpoint.lstrip('/')}",
                    "hotel.id": self.hotel_id,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to start trace span: {e}")
            return None

    async def _finish_tracing(
        self, trace_context: Any, error: Exception | None = None
    ) -> None:
        """Finish distributed tracing span.

        Args:
            trace_context: Trace context from _start_tracing
            error: Optional error to attach to span
        """
        if not self._tracer or not trace_context:
            return

        try:
            if error:
                self._tracer.finish_span(trace_context, error=error)
            else:
                self._tracer.finish_span(trace_context)
        except Exception as e:
            logger.debug(f"Failed to finish trace span: {e}")

    async def _apply_rate_limiting(self) -> float:
        """Apply rate limiting if enabled.

        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        if not self._rate_limiter:
            return 0.0

        wait_time = await self._rate_limiter.wait_if_needed()
        if wait_time > 0:
            logger.debug(f"Rate limited - waited {wait_time:.2f}s")
        return wait_time

    def _prepare_request_headers(
        self, headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Prepare request headers.

        Args:
            headers: Additional headers to include

        Returns:
            Complete headers dictionary
        """
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-hotelid": self.hotel_id,
            "x-request-id": (
                f"{self.hotel_id}-" + str(int(time.time() * 1000))
            ),  # Unique request ID
        }

        if headers:
            request_headers.update(headers)

        return request_headers

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff time.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Backoff time in seconds
        """
        return self.settings.retry_backoff * (2**attempt)

    async def _record_request_metrics(
        self,
        method: str,
        endpoint: str,
        start_time: float,
        status_code: int | None = None,
        retry_count: int = 0,
        error: Exception | None = None,
        request_size: int = 0,
        response_size: int = 0,
    ) -> RequestMetrics | None:
        """Record request metrics.

        Args:
            method: HTTP method
            endpoint: API endpoint
            start_time: Request start time
            status_code: HTTP status code
            retry_count: Number of retries
            error: Optional error that occurred
            request_size: Request body size in bytes
            response_size: Response body size in bytes

        Returns:
            RequestMetrics object or None
        """
        if not self._health_monitor:
            return None

        duration_ms = (time.time() - start_time) * 1000
        metrics = RequestMetrics(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            request_size_bytes=request_size,
            response_size_bytes=response_size,
            retry_count=retry_count,
            hotel_id=self.hotel_id,
            error_type=type(error).__name__ if error else None,
        )

        await self._health_monitor.record_request(metrics)
        return metrics

    async def _execute_single_request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        json_data: dict[str, Any] | None,
        headers: dict[str, str],
        timeout: httpx.Timeout,
    ) -> httpx.Response:
        """Execute a single HTTP request.

        Args:
            method: HTTP method
            url: Full URL
            params: Query parameters
            json_data: JSON request body
            headers: Request headers
            timeout: Request timeout configuration

        Returns:
            HTTP response

        Raises:
            RuntimeError: If session is not initialized
            httpx exceptions: For various HTTP errors
        """
        if self._session is None:
            raise RuntimeError("HTTP session not initialized")

        # Get fresh auth token and update headers
        token = await self.auth.get_token()
        auth_headers = self.auth.get_auth_header(token)
        headers.update(auth_headers)

        return await self._session.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=headers,
            timeout=timeout,
        )

    def _should_retry(self, error: Exception, attempt: int) -> tuple[bool, float]:
        """Determine if request should be retried.

        Args:
            error: Exception that occurred
            attempt: Current attempt number (0-based)

        Returns:
            Tuple of (should_retry, backoff_time)
        """
        if attempt >= self.settings.max_retries:
            return False, 0.0

        # Retry on authentication errors
        if isinstance(error, AuthenticationError):
            backoff = self.settings.retry_backoff * (attempt + 1)
            return True, backoff

        # Retry on timeout errors with exponential backoff
        if isinstance(error, httpx.TimeoutException):
            backoff = self._calculate_backoff(attempt)
            return True, backoff

        # Retry on connection/HTTP errors with exponential backoff
        if isinstance(error, httpx.RequestError | httpx.HTTPStatusError):
            backoff = self._calculate_backoff(attempt)
            return True, backoff

        # Don't retry on custom OperaCloudError exceptions
        if isinstance(error, OperaCloudError):
            return False, 0.0

        # Retry once on unexpected errors (only on first attempt)
        if attempt == 0:
            return True, self.settings.retry_backoff

        return False, 0.0

    def _convert_to_opera_error(
        self, error: Exception, error_msg: str
    ) -> OperaCloudError:
        """Convert exception to appropriate OperaCloudError subclass.

        Args:
            error: Original exception
            error_msg: Error message to use

        Returns:
            Appropriate OperaCloudError subclass
        """
        if isinstance(error, httpx.TimeoutException):
            return TimeoutError(error_msg)
        elif isinstance(error, httpx.ConnectError | httpx.RequestError):
            return APIError(error_msg)
        elif isinstance(error, OperaCloudError):
            return error  # Return as-is, don't wrap
        return OperaCloudError(error_msg)

    async def _handle_retry_error(
        self, error: Exception, attempt: int, retry_count: int, timeout: httpx.Timeout
    ) -> tuple[bool, float]:
        """Handle retry logic for different error types.

        Returns:
            Tuple of (should_continue_loop, backoff_time)
        """
        should_retry, backoff = self._should_retry(error, attempt)

        if isinstance(error, AuthenticationError):
            await self.auth.invalidate_token()
            if should_retry:
                logger.warning(
                    f"Authentication failed, retrying in {backoff}s... "
                    f"(attempt {attempt + 1})",
                    extra={"error": str(error), "retry_count": retry_count},
                )
                return True, backoff
        elif isinstance(error, httpx.TimeoutException):
            if should_retry:
                logger.warning(
                    f"Request timeout, retrying in {backoff}s... "
                    f"(attempt {attempt + 1}): {error}",
                    extra={"timeout": timeout.read, "retry_count": retry_count},
                )
                return True, backoff
        elif isinstance(error, httpx.RequestError | httpx.HTTPStatusError):
            if should_retry:
                logger.warning(
                    f"Request failed, retrying in {backoff}s... "
                    f"(attempt {attempt + 1}): {error}",
                    extra={
                        "error_type": type(error).__name__,
                        "retry_count": retry_count,
                    },
                )
                return True, backoff
        elif isinstance(error, OperaCloudError):
            logger.error(
                f"OperaCloudError during API request (attempt {attempt + 1}): {error}",
                extra={"error_type": type(error).__name__, "retry_count": retry_count},
            )
        else:
            logger.error(
                f"Unexpected error during API request (attempt {attempt + 1}): {error}",
                extra={"error_type": type(error).__name__, "retry_count": retry_count},
            )
            if should_retry:
                return True, backoff

        return False, 0.0

    async def _process_successful_response(
        self,
        response: httpx.Response,
        method: str,
        url: str,
        start_time: float,
        retry_count: int,
        json_data: dict[str, Any] | None,
        data_transformations: dict[str, Callable[[Any], Any]] | None,
    ) -> APIResponse:
        """Process a successful HTTP response."""
        # Log response
        request_duration = (time.time() - start_time) * 1000
        await self._log_response(method, url, response, request_duration, retry_count)

        # Handle response and apply transformations
        api_response = await self._handle_response(
            response, data_transformations=data_transformations
        )

        # Add response headers
        api_response.headers = dict(response.headers)

        # Record success metrics
        if self._health_monitor:
            metrics = await self._record_request_metrics(
                method=method,
                endpoint=url.split("/")[-1],  # Extract endpoint from URL
                start_time=start_time,
                status_code=response.status_code,
                retry_count=retry_count,
                request_size=len(json.dumps(json_data).encode()) if json_data else 0,
                response_size=len(response.content) if response.content else 0,
            )
            api_response.metrics = metrics

        return api_response

    async def _execute_with_retry(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        json_data: dict[str, Any] | None,
        headers: dict[str, str],
        timeout: httpx.Timeout,
        data_transformations: dict[str, Callable[[Any], Any]] | None,
        start_time: float,
    ) -> tuple[APIResponse | None, Exception | None, int]:
        """Execute request with retry logic.

        Args:
            method: HTTP method
            url: Full URL
            params: Query parameters
            json_data: JSON request body
            headers: Request headers
            timeout: Request timeout configuration
            data_transformations: Optional data transformations
            start_time: Request start time for metrics

        Returns:
            Tuple of (response, last_error, retry_count)
        """
        last_error: Exception | None = None
        retry_count = 0

        for attempt in range(self.settings.max_retries + 1):
            try:
                response = await self._execute_single_request(
                    method, url, params, json_data, headers, timeout
                )

                api_response = await self._process_successful_response(
                    response,
                    method,
                    url,
                    start_time,
                    retry_count,
                    json_data,
                    data_transformations,
                )

                return api_response, None, retry_count

            except Exception as e:
                last_error = e
                retry_count += 1

                should_continue, backoff = await self._handle_retry_error(
                    e, attempt, retry_count, timeout
                )

                if should_continue:
                    await asyncio.sleep(backoff)
                    continue
                break

        return None, last_error, retry_count

    async def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        enable_caching: bool = False,
        data_transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> APIResponse:
        """
        Make authenticated API request with comprehensive features.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON request body
            headers: Additional headers
            timeout: Custom timeout for this request
            enable_caching: Enable response caching for this request
            data_transformations: Custom data transformations to apply

        Returns:
            APIResponse with success status, data/error, and metrics

        Raises:
            OperaCloudError: For various API error conditions
        """
        start_time = time.time()
        await self._ensure_session()

        # Check cache if enabled
        if enable_caching:
            cached_response = await self._check_cache(method, endpoint, params)
            if cached_response:
                return cached_response

        # Start distributed tracing
        trace_context = await self._start_tracing(method, endpoint)

        # Apply rate limiting
        await self._apply_rate_limiting()

        # Prepare request
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        if json_data:
            json_data = self._data_transformer.sanitize_request_data(json_data)

        request_headers = self._prepare_request_headers(headers)

        request_timeout = timeout or self.settings.request_timeout
        custom_timeout = httpx.Timeout(
            connect=10.0, read=request_timeout, write=10.0, pool=5.0
        )

        # Log request
        await self._log_request(
            method, url, params=params, json=json_data, headers=request_headers
        )

        # Execute request with retry logic
        api_response, last_error, retry_count = await self._execute_with_retry(
            method=method,
            url=url,
            params=params,
            json_data=json_data,
            headers=request_headers,
            timeout=custom_timeout,
            data_transformations=data_transformations,
            start_time=start_time,
        )

        # Handle successful response
        if api_response:
            # Cache successful GET responses
            if enable_caching and api_response.success:
                await self._store_cache(
                    method,
                    endpoint,
                    params,
                    api_response.data,
                    api_response.status_code or 200,
                )

            # Finish tracing
            await self._finish_tracing(trace_context)
            return api_response

        # Handle failure - record metrics and raise error
        if self._health_monitor and last_error:
            await self._record_request_metrics(
                method=method,
                endpoint=endpoint,
                start_time=start_time,
                retry_count=retry_count,
                error=last_error,
                request_size=len(json.dumps(json_data).encode()) if json_data else 0,
            )

        # Finish tracing with error
        await self._finish_tracing(trace_context, last_error)

        # Raise appropriate error
        if last_error:
            error_msg = (
                f"Request failed after {self.settings.max_retries + 1} "
                + f"attempts: {last_error}"
            )
            logger.error(
                error_msg,
                extra={
                    "final_error_type": type(last_error).__name__,
                    "total_duration_ms": (time.time() - start_time) * 1000,
                    "total_retries": retry_count,
                    "method": method,
                    "endpoint": endpoint,
                },
            )

            raise self._convert_to_opera_error(last_error, error_msg) from last_error

        raise OperaCloudError("Unexpected error in request retry loop")

    def _handle_success_response(
        self,
        response: httpx.Response,
        data_transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> APIResponse:
        """Handle successful response (2xx status codes).

        Args:
            response: HTTP response object
            data_transformations: Optional data transformations to apply

        Returns:
            APIResponse with processed data

        Raises:
            DataError: If response data cannot be processed
        """
        status_code = response.status_code

        try:
            data: dict[str, Any] = response.json() if response.content else {}

            # Apply data transformations if provided
            if data_transformations and isinstance(data, dict):
                data = self._data_transformer.transform_response_data(
                    data, data_transformations
                )

            return APIResponse(
                success=True,
                data=data,
                status_code=status_code,
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse successful response JSON: {e}")
            # Try to return raw text if JSON parsing fails
            return APIResponse(
                success=True,
                data={
                    "raw_content": response.text,
                    "content_type": response.headers.get("content-type"),
                },
                status_code=status_code,
            )
        except Exception as e:
            logger.error(f"Unexpected error processing successful response: {e}")
            raise DataError(f"Failed to process response data: {e}") from e

    def _extract_error_message(self, error_data: dict[str, Any]) -> str:
        """Extract error message from error data."""
        error_msg = (
            error_data.get("error_description")
            or error_data.get("message")
            or error_data.get("detail")
            or error_data.get("error")
            or "Unknown error"
        )
        return str(error_msg) if error_msg is not None else "Unknown error"

    def _extract_retry_after(self, response: httpx.Response) -> int | None:
        """Extract retry-after value from response for rate limiting."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            with contextlib.suppress(ValueError):
                return int(retry_after)
        return None

    def _parse_error_json(
        self, response: httpx.Response
    ) -> tuple[str, dict[str, Any] | None, int | None]:
        """Parse error response JSON to extract error message and data."""
        error_data = response.json()
        if isinstance(error_data, dict):
            # Extract detailed error information
            error_msg = (
                self._extract_error_message(error_data)
                or f"HTTP {response.status_code}"
            )

            # Extract retry-after header for rate limiting
            retry_after = None
            if response.status_code == 429:
                retry_after = self._extract_retry_after(response)

            return error_msg, error_data, retry_after
        return f"HTTP {response.status_code}", error_data, None

    def _handle_json_decode_error(
        self, response: httpx.Response
    ) -> tuple[str, dict[str, Any] | None, int | None]:
        """Handle JSON decode errors."""
        # If JSON parsing fails, use raw text
        error_msg = response.text[:500] or f"HTTP {response.status_code}"
        return error_msg, None, None

    def _handle_unexpected_error(
        self, response: httpx.Response, e: Exception
    ) -> tuple[str, dict[str, Any] | None, int | None]:
        """Handle unexpected errors during error parsing."""
        logger.warning(f"Failed to parse error response: {e}")
        error_msg = response.text[:500] or f"HTTP {response.status_code}"
        return error_msg, None, None

    def _parse_error_response(
        self, response: httpx.Response
    ) -> tuple[str, dict[str, Any] | None, int | None]:
        """Parse error response to extract error message and data.

        Args:
            response: HTTP response object

        Returns:
            Tuple of (error_msg, error_data, retry_after)
        """
        status_code = response.status_code
        error_msg = f"HTTP {status_code}"
        error_data = None
        retry_after = None

        try:
            if response.content:
                return self._parse_error_json(response)
        except json.JSONDecodeError:
            return self._handle_json_decode_error(response)
        except Exception as e:
            return self._handle_unexpected_error(response, e)

        return error_msg, error_data, retry_after

    def _build_error_details(
        self, response: httpx.Response, error_data: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Build detailed error context.

        Args:
            response: HTTP response object
            error_data: Parsed error data

        Returns:
            Dictionary with error details
        """
        error_details = {
            "status_code": response.status_code,
            "url": str(response.url),
            "method": response.request.method if response.request else "Unknown",
            "headers": dict(response.headers),
            "hotel_id": self.hotel_id,
        }

        if error_data:
            error_details["response_data"] = error_data

        return error_details

    def _create_authentication_error(
        self, status_code: int, error_msg: str, error_details: dict[str, Any]
    ) -> AuthenticationError:
        """Create authentication error."""
        if status_code == 401:
            return AuthenticationError(
                f"Authentication failed: {error_msg}", details=error_details
            )
        # status_code == 403
        return AuthenticationError(
            f"Access forbidden: {error_msg}", details=error_details
        )

    def _create_resource_error(
        self, error_msg: str, error_details: dict[str, Any]
    ) -> ResourceNotFoundError:
        """Create resource not found error."""
        return ResourceNotFoundError(
            f"Resource not found: {error_msg}", details=error_details
        )

    def _create_validation_error(
        self, status_code: int, error_msg: str, error_details: dict[str, Any]
    ) -> ValidationError:
        """Create validation error."""
        if status_code == 422:
            return ValidationError(
                f"Validation error: {error_msg}", details=error_details
            )
        elif status_code == 400:
            return ValidationError(f"Bad request: {error_msg}", details=error_details)
        # status_code == 409
        return ValidationError(f"Conflict: {error_msg}", details=error_details)

    def _create_rate_limit_error(
        self, error_msg: str, retry_after: int | None, error_details: dict[str, Any]
    ) -> RateLimitError:
        """Create rate limit error."""
        return RateLimitError(
            f"Rate limit exceeded: {error_msg}",
            retry_after=retry_after,
            details=error_details,
        )

    def _create_server_error(
        self,
        status_code: int,
        error_msg: str,
        error_data: dict[str, Any] | None,
        error_details: dict[str, Any],
    ) -> APIError:
        """Create server error."""
        if status_code == 500:
            return APIError(
                f"Internal server error: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
        elif status_code == 502:
            return APIError(
                f"Bad gateway: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
        elif status_code == 503:
            return APIError(
                f"Service unavailable: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
        elif status_code == 504:
            return APIError(
                f"Gateway timeout: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
        # Other server errors
        return APIError(
            f"Server error {status_code}: {error_msg}",
            status_code=status_code,
            response_data=error_data,
            details=error_details,
        )

    def _create_client_error(
        self,
        status_code: int,
        error_msg: str,
        error_data: dict[str, Any] | None,
        error_details: dict[str, Any],
    ) -> APIError:
        """Create client error."""
        if 400 <= status_code < 500:
            return APIError(
                f"Client error {status_code}: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
        # Unexpected status codes
        return APIError(
            f"Unexpected response {status_code}: {error_msg}",
            status_code=status_code,
            response_data=error_data,
            details=error_details,
        )

    def _map_status_to_exception(
        self,
        status_code: int,
        error_msg: str,
        error_data: dict[str, Any] | None,
        error_details: dict[str, Any],
        retry_after: int | None = None,
    ) -> OperaCloudError:
        """Map HTTP status code to appropriate exception.

        Args:
            status_code: HTTP status code
            error_msg: Error message
            error_data: Parsed error data
            error_details: Detailed error context
            retry_after: Retry-after value for rate limiting

        Returns:
            Appropriate OperaCloudError subclass
        """
        # Authentication errors
        if status_code in (401, 403):
            return self._create_authentication_error(
                status_code, error_msg, error_details
            )

        # Resource errors
        elif status_code == 404:
            return self._create_resource_error(error_msg, error_details)

        # Validation errors
        elif status_code in (422, 400, 409):
            return self._create_validation_error(status_code, error_msg, error_details)

        # Rate limiting
        elif status_code == 429:
            return self._create_rate_limit_error(error_msg, retry_after, error_details)

        # Server errors
        elif status_code in (500, 502, 503, 504):
            return self._create_server_error(
                status_code, error_msg, error_data, error_details
            )

        # Generic client errors
        elif 400 <= status_code < 500:
            return self._create_client_error(
                status_code, error_msg, error_data, error_details
            )

        # Generic server errors
        elif status_code >= 500:
            return self._create_server_error(
                status_code, error_msg, error_data, error_details
            )

        # Unexpected status codes
        return self._create_client_error(
            status_code, error_msg, error_data, error_details
        )

    async def _handle_response(
        self,
        response: httpx.Response,
        data_transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> APIResponse:
        """
        Handle API response and convert to standard format.

        Args:
            response: HTTP response object
            data_transformations: Optional data transformations to apply

        Returns:
            APIResponse with processed data and applied transformations

        Raises:
            Various OperaCloudError subclasses based on response
        """
        status_code = response.status_code

        logger.debug(
            f"API response: {status_code}",
            extra={
                "status_code": status_code,
                "url": str(response.url),
            },
        )

        # Handle successful responses (2xx)
        if 200 <= status_code < 300:
            return self._handle_success_response(response, data_transformations)

        # Handle error responses
        error_msg, error_data, retry_after = self._parse_error_response(response)
        error_details = self._build_error_details(response, error_data)

        # Map status code to appropriate exception and raise it
        exception = self._map_status_to_exception(
            status_code, error_msg, error_data, error_details, retry_after
        )
        raise exception

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        enable_caching: bool = False,
        data_transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> APIResponse:
        """Make GET request with enhanced options."""
        return await self.request(
            "GET",
            endpoint,
            params=params,
            headers=headers,
            timeout=timeout,
            enable_caching=enable_caching,
            data_transformations=data_transformations,
        )

    async def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data_transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> APIResponse:
        """Make POST request with enhanced options."""
        return await self.request(
            "POST",
            endpoint,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
            data_transformations=data_transformations,
        )

    async def put(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data_transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> APIResponse:
        """Make PUT request with enhanced options."""
        return await self.request(
            "PUT",
            endpoint,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
            data_transformations=data_transformations,
        )

    async def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Make DELETE request with enhanced options."""
        return await self.request(
            "DELETE", endpoint, params=params, headers=headers, timeout=timeout
        )

    async def patch(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        data_transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> APIResponse:
        """Make PATCH request with enhanced options."""
        return await self.request(
            "PATCH",
            endpoint,
            params=params,
            json_data=json_data,
            headers=headers,
            timeout=timeout,
            data_transformations=data_transformations,
        )

    async def head(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Make HEAD request for metadata checking."""
        return await self.request(
            "HEAD", endpoint, params=params, headers=headers, timeout=timeout
        )

    async def options(
        self,
        endpoint: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """Make OPTIONS request to discover allowed methods."""
        return await self.request("OPTIONS", endpoint, headers=headers, timeout=timeout)

    async def health_check(self) -> dict[str, Any]:
        """Perform a comprehensive health check of the API client."""
        health_status = self.get_health_status()

        # Test connectivity with a simple API call if possible
        try:
            # This would be a lightweight endpoint like /health or /ping
            # For now, we'll just check if we can get a token
            token_info = self.auth.get_token_info()
            health_status["api_connectivity"] = (
                "unknown"  # Would need actual test endpoint
            )
            health_status["authentication_test"] = token_info["status"]
        except Exception as e:
            health_status["api_connectivity"] = "error"
            health_status["connectivity_error"] = str(e)

        return health_status
