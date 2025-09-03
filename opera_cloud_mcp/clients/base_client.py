"""
Base API client for OPERA Cloud services.

Provides common functionality including authentication, retry logic,
error handling, and request/response processing for all API clients.
"""

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel, Field

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler
from opera_cloud_mcp.auth.secure_oauth_handler import SecureOAuthHandler
from opera_cloud_mcp.config.settings import Settings
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
from opera_cloud_mcp.utils.observability import get_observability

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern implementation for API resilience."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Exception | tuple = Exception,
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

    async def call(self, func: Callable, *args, **kwargs) -> Any:
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
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
        self._request_history: deque = deque(maxlen=1000)

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
        self._request_history: deque = deque(maxlen=max_history)
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
        now = datetime.utcnow()
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
            "error_counts": dict(self._error_counts),
            "status_code_counts": dict(self._status_code_counts),
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
            return data

        cleaned = {}
        for key, value in data.items():
            if value is None or value == "":
                continue
            elif isinstance(value, dict):
                cleaned_nested = DataTransformer.sanitize_request_data(value)
                if cleaned_nested:
                    cleaned[key] = cleaned_nested
            elif isinstance(value, list):
                cleaned_list = [
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
    def transform_response_data(
        data: dict[str, Any], transformations: dict[str, Callable] | None = None
    ) -> dict[str, Any]:
        """Transform response data using provided transformation functions."""
        if not transformations or not isinstance(data, dict):
            return data

        transformed = data.copy()
        for field_path, transform_func in transformations.items():
            try:
                # Support nested field paths like "guest.profile.name"
                keys = field_path.split(".")
                current = transformed

                # Navigate to the parent of the target field
                for key in keys[:-1]:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        break
                else:
                    # Apply transformation to the target field
                    final_key = keys[-1]
                    if isinstance(current, dict) and final_key in current:
                        current[final_key] = transform_func(current[final_key])
            except Exception as e:
                logger.warning(f"Failed to transform field {field_path}: {e}")

        return transformed

    @staticmethod
    def mask_sensitive_data(
        data: dict[str, Any], sensitive_fields: set | None = None
    ) -> dict[str, Any]:
        """Mask sensitive data in logs and responses."""
        if sensitive_fields is None:
            sensitive_fields = {
                "password",
                "secret",
                "token",
                "authorization",
                "credit_card",
                "ssn",
                "phone",
                "email",
                "address",
            }

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
            else:
                return obj

        return _mask_recursive(data)


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
        self.settings = settings or Settings()
        self._session: httpx.AsyncClient | None = None
        self._session_lock = asyncio.Lock()

        # Rate limiting
        self.enable_rate_limiting = enable_rate_limiting
        if enable_rate_limiting:
            self._rate_limiter = RateLimiter(
                requests_per_second=requests_per_second, burst_capacity=burst_capacity
            )
        else:
            self._rate_limiter = None

        # Health monitoring
        self.enable_monitoring = enable_monitoring
        if enable_monitoring:
            self._health_monitor = HealthMonitor()
        else:
            self._health_monitor = None

        # Response caching
        self.enable_caching = enable_caching
        if enable_caching:
            self._cache_manager = OperaCacheManager(
                hotel_id=hotel_id,
                enable_persistent=settings.enable_cache if settings else True,
                max_memory_size=settings.cache_max_memory
                if hasattr(settings, "cache_max_memory")
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
                            "keepalive_connections": self._connection_limits.max_keepalive_connections,
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
        return f"{self.settings.opera_base_url.rstrip('/')}/{self.settings.opera_api_version}"

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

    async def _log_request(self, method: str, url: str, **kwargs) -> None:
        """Log outgoing request details."""
        # Calculate request size
        request_size = 0
        if "json" in kwargs and kwargs["json"]:
            request_size = len(json.dumps(kwargs["json"]).encode("utf-8"))
        elif "data" in kwargs and kwargs["data"]:
            request_size = len(str(kwargs["data"]).encode("utf-8"))

        # Mask sensitive data for logging
        safe_params = self._data_transformer.mask_sensitive_data(
            kwargs.get("params", {})
        )
        safe_json = self._data_transformer.mask_sensitive_data(kwargs.get("json", {}))

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

    async def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        enable_caching: bool = False,
        data_transformations: dict[str, Callable] | None = None,
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
        # Start timing for metrics
        start_time = time.time()

        await self._ensure_session()

        # Check cache for GET requests if caching is enabled
        if self._cache_manager and enable_caching and method.upper() == "GET":
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

        # Start tracing span if available
        trace_context = None
        if self._tracer:
            try:
                trace_context = self._tracer.start_span(
                    f"api.{method.lower()}",
                    tags={
                        "http.method": method,
                        "http.url": f"{self.base_url}/{endpoint.lstrip('/')}",
                        "hotel.id": self.hotel_id,
                    },
                )
            except Exception as e:
                logger.debug(f"Failed to start trace span: {e}")

        # Apply rate limiting if enabled
        if self._rate_limiter:
            wait_time = await self._rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.debug(f"Rate limited - waited {wait_time:.2f}s")

        # Build full URL
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Prepare and sanitize request data
        if json_data:
            json_data = self._data_transformer.sanitize_request_data(json_data)

        # Prepare headers
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-hotelid": self.hotel_id,
            "x-request-id": f"{self.hotel_id}-{int(time.time() * 1000)}",  # Unique request ID
        }

        if headers:
            request_headers.update(headers)

        # Custom timeout handling
        request_timeout = timeout or self.settings.request_timeout
        custom_timeout = httpx.Timeout(
            connect=10.0, read=request_timeout, write=10.0, pool=5.0
        )

        # Log request
        await self._log_request(
            method, url, params=params, json=json_data, headers=request_headers
        )

        # Retry loop with enhanced error handling
        last_error: Exception | None = None
        retry_count = 0

        for attempt in range(self.settings.max_retries + 1):
            try:
                # Get fresh auth token
                token = await self.auth.get_token()
                auth_headers = self.auth.get_auth_header(token)
                request_headers.update(auth_headers)

                logger.debug(
                    f"API request: {method} {url} (attempt {attempt + 1})",
                    extra={
                        "method": method,
                        "url": url,
                        "attempt": attempt + 1,
                        "retry_count": retry_count,
                        "hotel_id": self.hotel_id,
                    },
                )

                # Make request with custom timeout
                request_start = time.time()
                response = await self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=request_headers,
                    timeout=custom_timeout,
                )
                request_duration = (time.time() - request_start) * 1000

                # Log response
                await self._log_response(
                    method, url, response, request_duration, retry_count
                )

                # Handle response and apply transformations
                api_response = await self._handle_response(
                    response, data_transformations=data_transformations
                )

                # Record metrics if monitoring is enabled
                if self._health_monitor:
                    total_duration = (time.time() - start_time) * 1000
                    metrics = RequestMetrics(
                        method=method,
                        endpoint=endpoint,
                        status_code=response.status_code,
                        duration_ms=total_duration,
                        request_size_bytes=len(json.dumps(json_data).encode())
                        if json_data
                        else 0,
                        response_size_bytes=len(response.content)
                        if response.content
                        else 0,
                        retry_count=retry_count,
                        hotel_id=self.hotel_id,
                        error_type=None
                        if api_response.success
                        else type(last_error).__name__
                        if last_error
                        else "UnknownError",
                    )
                    await self._health_monitor.record_request(metrics)
                    api_response.metrics = metrics

                # Add response headers to the API response
                api_response.headers = dict(response.headers)

                # Cache successful GET responses if caching is enabled
                if (
                    self._cache_manager
                    and enable_caching
                    and method.upper() == "GET"
                    and api_response.success
                    and response.status_code == 200
                ):
                    cache_key = f"{method}:{endpoint}:{hash(str(params))}"
                    ttl = (
                        self.settings.cache_ttl
                        if hasattr(self.settings, "cache_ttl")
                        else 300
                    )
                    await self._cache_manager.set(
                        "api_response", cache_key, api_response.data, ttl_override=ttl
                    )
                    logger.debug(
                        f"Response cached for {method} {endpoint} with TTL {ttl}s"
                    )

                # Finish tracing span if available
                if self._tracer and "trace_context" in locals():
                    try:
                        self._tracer.finish_span(trace_context)
                    except Exception as e:
                        logger.debug(f"Failed to finish trace span: {e}")

                return api_response

            except AuthenticationError as e:
                last_error = e
                retry_count += 1
                # Invalidate token and retry
                await self.auth.invalidate_token()
                if attempt < self.settings.max_retries:
                    backoff_time = self.settings.retry_backoff * (attempt + 1)
                    logger.warning(
                        f"Authentication failed, retrying in {backoff_time}s... (attempt {attempt + 1})",
                        extra={"error": str(e), "retry_count": retry_count},
                    )
                    await asyncio.sleep(backoff_time)
                    continue
                raise

            except httpx.TimeoutException as e:
                last_error = e
                retry_count += 1
                if attempt < self.settings.max_retries:
                    backoff_time = self.settings.retry_backoff * (2**attempt)
                    logger.warning(
                        f"Request timeout, retrying in {backoff_time}s... (attempt {attempt + 1}): {e}",
                        extra={"timeout": request_timeout, "retry_count": retry_count},
                    )
                    await asyncio.sleep(backoff_time)
                    continue
                break

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_error = e
                retry_count += 1
                if attempt < self.settings.max_retries:
                    backoff_time = self.settings.retry_backoff * (2**attempt)
                    logger.warning(
                        f"Request failed, retrying in {backoff_time}s... (attempt {attempt + 1}): {e}",
                        extra={
                            "error_type": type(e).__name__,
                            "retry_count": retry_count,
                        },
                    )
                    await asyncio.sleep(backoff_time)
                    continue
                break

            except OperaCloudError as e:
                # Re-raise custom OperaCloudError exceptions without wrapping
                last_error = e
                retry_count += 1
                logger.error(
                    f"OperaCloudError during API request (attempt {attempt + 1}): {e}",
                    extra={"error_type": type(e).__name__, "retry_count": retry_count},
                )
                # Don't retry on custom exceptions
                break

            except Exception as e:
                last_error = e
                retry_count += 1
                logger.error(
                    f"Unexpected error during API request (attempt {attempt + 1}): {e}",
                    extra={"error_type": type(e).__name__, "retry_count": retry_count},
                )
                # Don't retry on unexpected errors unless it's the first attempt
                if attempt == 0 and attempt < self.settings.max_retries:
                    backoff_time = self.settings.retry_backoff
                    await asyncio.sleep(backoff_time)
                    continue
                break

        # All retries exhausted - record failure metrics and raise error
        total_duration = (time.time() - start_time) * 1000

        if self._health_monitor and last_error:
            error_metrics = RequestMetrics(
                method=method,
                endpoint=endpoint,
                status_code=None,
                duration_ms=total_duration,
                request_size_bytes=len(json.dumps(json_data).encode())
                if json_data
                else 0,
                response_size_bytes=0,
                retry_count=retry_count,
                hotel_id=self.hotel_id,
                error_type=type(last_error).__name__,
            )
            await self._health_monitor.record_request(error_metrics)

        if last_error:
            error_msg = f"Request failed after {self.settings.max_retries + 1} attempts: {last_error}"
            logger.error(
                error_msg,
                extra={
                    "final_error_type": type(last_error).__name__,
                    "total_duration_ms": total_duration,
                    "total_retries": retry_count,
                    "method": method,
                    "endpoint": endpoint,
                },
            )

            # Raise specific exception type based on the last error
            if isinstance(last_error, httpx.TimeoutException):
                raise TimeoutError(error_msg) from last_error
            elif isinstance(last_error, httpx.ConnectError | httpx.RequestError):
                raise APIError(error_msg) from last_error
            elif isinstance(last_error, OperaCloudError):
                # Re-raise custom OperaCloudError exceptions without wrapping
                raise last_error
            else:
                raise OperaCloudError(error_msg) from last_error

        # Finish tracing span with error if available
        if self._tracer and "trace_context" in locals():
            try:
                self._tracer.finish_span(
                    trace_context,
                    error=last_error if "last_error" in locals() else None,
                )
            except Exception as e:
                logger.debug(f"Failed to finish trace span with error: {e}")

        raise OperaCloudError("Unexpected error in request retry loop")

    async def _handle_response(
        self,
        response: httpx.Response,
        data_transformations: dict[str, Callable] | None = None,
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

        # Success responses
        if 200 <= status_code < 300:
            try:
                data = response.json() if response.content else {}

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

        # Error responses - enhanced error handling with detailed context
        error_msg = f"HTTP {status_code}"
        error_data = None
        retry_after = None

        try:
            if response.content:
                error_data = response.json()
                if isinstance(error_data, dict):
                    # Extract detailed error information
                    error_msg = (
                        error_data.get("error_description")
                        or error_data.get("message")
                        or error_data.get("detail")
                        or error_data.get("error")
                        or error_msg
                    )

                    # Extract retry-after header for rate limiting
                    if status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                retry_after = int(retry_after)
                            except ValueError:
                                retry_after = None
        except json.JSONDecodeError:
            # If JSON parsing fails, use raw text
            error_msg = response.text[:500] or error_msg  # Limit error message length
        except Exception as e:
            logger.warning(f"Failed to parse error response: {e}")
            error_msg = response.text[:500] or error_msg

        # Create detailed error context
        error_details = {
            "status_code": status_code,
            "url": str(response.url),
            "method": response.request.method if response.request else "Unknown",
            "headers": dict(response.headers),
            "hotel_id": self.hotel_id,
        }

        if error_data:
            error_details["response_data"] = error_data

        # Specific error handling with enhanced details
        if status_code == 401:
            raise AuthenticationError(
                f"Authentication failed: {error_msg}", details=error_details
            )
        elif status_code == 403:
            raise AuthenticationError(
                f"Access forbidden: {error_msg}", details=error_details
            )
        elif status_code == 404:
            raise ResourceNotFoundError(
                f"Resource not found: {error_msg}", details=error_details
            )
        elif status_code == 422:
            raise ValidationError(
                f"Validation error: {error_msg}", details=error_details
            )
        elif status_code == 429:
            raise RateLimitError(
                f"Rate limit exceeded: {error_msg}",
                retry_after=retry_after,
                details=error_details,
            )
        elif status_code == 400:
            raise ValidationError(f"Bad request: {error_msg}", details=error_details)
        elif status_code == 409:
            raise ValidationError(f"Conflict: {error_msg}", details=error_details)
        elif 400 <= status_code < 500:
            raise APIError(
                f"Client error {status_code}: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
        elif status_code == 500:
            raise APIError(
                f"Internal server error: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
        elif status_code == 502:
            raise APIError(
                f"Bad gateway: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
        elif status_code == 503:
            raise APIError(
                f"Service unavailable: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
        elif status_code == 504:
            raise TimeoutError(f"Gateway timeout: {error_msg}", details=error_details)
        elif status_code >= 500:
            raise APIError(
                f"Server error {status_code}: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )

        # Generic error for unexpected status codes
        raise APIError(
            f"Unexpected response {status_code}: {error_msg}",
            status_code=status_code,
            response_data=error_data,
            details=error_details,
        )

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        enable_caching: bool = False,
        data_transformations: dict[str, Callable] | None = None,
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
        data_transformations: dict[str, Callable] | None = None,
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
        data_transformations: dict[str, Callable] | None = None,
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
        data_transformations: dict[str, Callable] | None = None,
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
