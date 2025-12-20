"""
Refactored Base API client with reduced complexity.

This is a new version of base_client.py with complexity reduced by extracting
methods and simplifying control flow.
"""

import asyncio
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

    def _get_nested_field_value(
        self, data: dict[str, Any], keys: list[str]
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Get the parent dict and final key for a nested field path."""
        current: dict[str, Any] | Any = data

        # Navigate to the parent of the target field
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None, None

        final_key = keys[-1]
        return current if isinstance(current, dict) else None, final_key

    def _apply_field_transformation(
        self,
        data: dict[str, Any],
        field_path: str,
        transform_func: Callable[[Any], Any],
    ) -> None:
        """Apply a single field transformation."""
        try:
            # Support nested field paths like "guest.profile.name"
            keys = field_path.split(".")
            parent_dict, final_key = self._get_nested_field_value(data, keys)

            if (
                parent_dict
                and final_key
                and isinstance(parent_dict, dict)
                and final_key in parent_dict
            ):
                parent_dict[final_key] = transform_func(parent_dict[final_key])
        except Exception as e:
            logger.warning(f"Failed to transform field {field_path}: {e}")

    def transform_response_data(
        self,
        data: dict[str, Any],
        transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> dict[str, Any]:
        """Transform response data using provided transformation functions."""
        if not transformations or not isinstance(data, dict):
            return data if isinstance(data, dict) else {}

        transformed = data.copy()
        for field_path, transform_func in transformations.items():
            self._apply_field_transformation(transformed, field_path, transform_func)

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


class RequestHandler:
    """Handles individual request execution with reduced complexity."""

    def __init__(self, client: "BaseAPIClient"):
        self.client = client

    async def check_cache(
        self, method: str, endpoint: str, params: dict[str, Any] | None = None
    ) -> APIResponse | None:
        """Check cache for GET requests."""
        if not self.client._cache_manager or method.upper() != "GET":
            return None

        cache_key = f"{method}:{endpoint}:{hash(str(params))}"
        cached_response = await self.client._cache_manager.get(
            "api_response", cache_key
        )

        if cached_response is None:
            return None

        logger.debug(f"Cache hit for {method} {endpoint}")

        # Record cache hit metrics
        if self.client._health_monitor:
            metrics = RequestMetrics(
                method=method,
                endpoint=endpoint,
                status_code=200,
                duration_ms=0.1,
                request_size_bytes=0,
                response_size_bytes=len(str(cached_response).encode()),
                retry_count=0,
                hotel_id=self.client.hotel_id,
                error_type=None,
            )
            await self.client._health_monitor.record_request(metrics)

        return APIResponse(success=True, data=cached_response, status_code=200)

    async def save_to_cache(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None,
        response_data: dict[str, Any],
    ) -> None:
        """Save successful GET response to cache."""
        if not self.client._cache_manager or method.upper() != "GET":
            return

        cache_key = f"{method}:{endpoint}:{hash(str(params))}"
        ttl = getattr(self.client.settings, "cache_ttl", 300)

        await self.client._cache_manager.set(
            "api_response", cache_key, response_data, ttl_override=ttl
        )
        logger.debug(f"Response cached for {method} {endpoint} with TTL {ttl}s")

    def prepare_headers(self, headers: dict[str, str] | None = None) -> dict[str, str]:
        """Prepare request headers."""
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-hotelid": self.client.hotel_id,
            "x-request-id": f"{self.client.hotel_id}-{int(time.time() * 1000)}",
        }

        if headers:
            request_headers.update(headers)

        return request_headers

    async def execute_request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        json_data: dict[str, Any] | None,
        headers: dict[str, str],
        timeout: httpx.Timeout,
    ) -> httpx.Response:
        """Execute the HTTP request with authentication."""
        # Get fresh auth token
        token = await self.client.auth.get_token()
        auth_headers = self.client.auth.get_auth_header(token)
        headers.update(auth_headers)

        # Ensure session is available
        if self.client._session is None:
            raise RuntimeError("HTTP session not initialized")

        return await self.client._session.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=headers,
            timeout=timeout,
        )


class RetryHandler:
    """Handles retry logic with reduced complexity."""

    def __init__(self, client: "BaseAPIClient"):
        self.client = client

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if request should be retried."""
        # Don't retry on certain error types
        if isinstance(error, OperaCloudError | KeyError | ValueError):
            return False

        # Check attempt limit
        return attempt < self.client.settings.max_retries

    def calculate_backoff(self, error: Exception, attempt: int) -> float:
        """Calculate backoff time based on error type and attempt."""
        if isinstance(error, AuthenticationError):
            return self.client.settings.retry_backoff * (attempt + 1)
        return self.client.settings.retry_backoff * (2**attempt)

    async def handle_retry(self, error: Exception, attempt: int) -> bool:
        """Handle retry with backoff."""
        if not self.should_retry(error, attempt):
            return False

        backoff_time = self.calculate_backoff(error, attempt)

        # Special handling for auth errors
        if isinstance(error, AuthenticationError):
            await self.client.auth.invalidate_token()

        logger.warning(
            f"Request failed, retrying in {backoff_time}s... "
            f"(attempt {attempt + 1}): {error}"
        )
        await asyncio.sleep(backoff_time)
        return True


class ResponseHandler:
    """Handles response processing with reduced complexity."""

    # Status code to exception mapping
    STATUS_EXCEPTIONS = {
        401: (AuthenticationError, "Authentication failed"),
        403: (AuthenticationError, "Access forbidden"),
        404: (ResourceNotFoundError, "Resource not found"),
        422: (ValidationError, "Validation error"),
        429: (RateLimitError, "Rate limit exceeded"),
        400: (ValidationError, "Bad request"),
        409: (ValidationError, "Conflict"),
        500: (APIError, "Internal server error"),
        502: (APIError, "Bad gateway"),
        503: (APIError, "Service unavailable"),
        504: (TimeoutError, "Gateway timeout"),
    }

    def __init__(self, client: "BaseAPIClient"):
        self.client = client

    async def handle_response(
        self,
        response: httpx.Response,
        data_transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> APIResponse:
        """Handle API response with reduced complexity."""
        status_code = response.status_code

        # Handle success responses
        if 200 <= status_code < 300:
            return self._handle_success_response(response, data_transformations)

        # Handle error responses - this will raise an exception
        self._handle_error_response(response)
        # This line should never be reached due to exception above
        raise OperaCloudError("Unexpected error in response handling")

    def _handle_success_response(
        self,
        response: httpx.Response,
        data_transformations: dict[str, Callable[[Any], Any]] | None = None,
    ) -> APIResponse:
        """Handle successful response."""
        try:
            data: dict[str, Any] = response.json() if response.content else {}

            # Apply transformations
            if data_transformations and isinstance(data, dict):
                data = self.client._data_transformer.transform_response_data(
                    data, data_transformations
                )

            return APIResponse(
                success=True,
                data=data,
                status_code=response.status_code,
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse successful response JSON: {e}")
            return APIResponse(
                success=True,
                data={
                    "raw_content": response.text,
                    "content_type": response.headers.get("content-type"),
                },
                status_code=response.status_code,
            )
        except Exception as e:
            logger.error(f"Unexpected error processing successful response: {e}")
            raise DataError(f"Failed to process response data: {e}") from e

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error response with simplified logic."""
        status_code = response.status_code
        error_msg = f"HTTP {status_code}"
        error_data = None
        retry_after = None

        # Parse error response
        try:
            if response.content:
                error_data = response.json()
                if isinstance(error_data, dict):
                    error_msg = self._extract_error_message(error_data, error_msg)

                    if status_code == 429:
                        retry_after = self._extract_retry_after(response)
        except json.JSONDecodeError:
            error_msg = response.text[:500] or error_msg
        except Exception as e:
            logger.warning(f"Failed to parse error response: {e}")
            error_msg = response.text[:500] or error_msg

        # Build error details
        error_details = self._build_error_details(response, error_data)

        # Raise appropriate exception
        self._raise_exception(
            status_code, error_msg, error_details, retry_after, error_data
        )

    def _extract_error_message(
        self, error_data: dict[str, Any], default_msg: str
    ) -> str:
        """Extract error message from error data."""
        return (
            error_data.get("error_description")
            or error_data.get("message")
            or error_data.get("detail")
            or error_data.get("error")
            or default_msg
        )

    def _extract_retry_after(self, response: httpx.Response) -> int | None:
        """Extract retry-after header value."""
        retry_after_header = response.headers.get("Retry-After")
        if retry_after_header:
            from contextlib import suppress

            with suppress(ValueError):
                return int(retry_after_header)
        return None

    def _build_error_details(
        self, response: httpx.Response, error_data: Any
    ) -> dict[str, Any]:
        """Build error details dictionary."""
        error_details = {
            "status_code": response.status_code,
            "url": str(response.url),
            "method": response.request.method if response.request else "Unknown",
            "headers": dict(response.headers),
            "hotel_id": self.client.hotel_id,
        }

        if error_data:
            error_details["response_data"] = error_data

        return error_details

    def _raise_exception(
        self,
        status_code: int,
        error_msg: str,
        error_details: dict[str, Any],
        retry_after: int | None = None,
        error_data: Any = None,
    ) -> None:
        """Raise appropriate exception based on status code."""
        # Check specific status codes
        if status_code in self.STATUS_EXCEPTIONS:
            exc_class, msg_prefix = self.STATUS_EXCEPTIONS[status_code]

            if status_code == 429 and retry_after is not None:
                raise RateLimitError(
                    f"{msg_prefix}: {error_msg}",
                    retry_after=retry_after,
                    details=error_details,
                )
            else:
                raise exc_class(f"{msg_prefix}: {error_msg}", details=error_details)

        # Handle generic client/server errors
        if 400 <= status_code < 500:
            raise APIError(
                f"Client error {status_code}: {error_msg}",
                status_code=status_code,
                response_data=error_data,
                details=error_details,
            )
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


class BaseAPIClient:
    """
    Refactored production-ready base client for all OPERA Cloud API clients.

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

    Complexity reduced by:
    - Extracting request, retry, and response handling into separate classes
    - Using strategy pattern for error handling
    - Simplifying control flow with early returns
    - Breaking down large methods into focused helpers
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

        # Initialize handlers
        self._request_handler = RequestHandler(self)
        self._retry_handler = RetryHandler(self)
        self._response_handler = ResponseHandler(self)

        # Rate limiter (can be None if disabled)
        self._rate_limiter: RateLimiter | None = None
        if enable_rate_limiting:
            self._rate_limiter = RateLimiter(
                requests_per_second=requests_per_second,
                burst_capacity=burst_capacity,
            )

        # Health monitor (can be None if disabled)
        self._health_monitor: HealthMonitor | None = None
        if enable_monitoring:
            self._health_monitor = HealthMonitor()

        # Cache manager (can be None if disabled)
        self._cache_manager: OperaCacheManager | None = None
        if enable_caching:
            self._cache_manager = OperaCacheManager(
                hotel_id=hotel_id,
                enable_persistent=settings.enable_cache if settings else True,
                max_memory_size=getattr(settings, "cache_max_memory", 10000),
            )

        # Data transformer for request/response processing
        self._data_transformer = DataTransformer()

        # Connection limits for HTTP client pooling
        self._connection_limits = httpx.Limits(
            max_connections=50,
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        )

        # Timeout configuration for HTTP requests
        self._timeout_config = httpx.Timeout(
            connect=10.0,
            read=self.settings.request_timeout,
            write=10.0,
            pool=5.0,
        )

        # Distributed tracer (can be None if tracing is disabled)
        self._tracer: DistributedTracer | None = None
        try:
            self._tracer = get_observability().tracer
        except Exception:
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
                        http2=True,
                        verify=True,
                        follow_redirects=True,
                        headers={
                            "User-Agent": "OPERA-Cloud-MCP/1.0 (httpx)",
                            "Accept-Encoding": "gzip, deflate",
                            "Connection": "keep-alive",
                        },
                    )
                    logger.debug("HTTP session initialized")

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
            "rate_limiting_enabled": self._rate_limiter is not None,
            "monitoring_enabled": self._health_monitor is not None,
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

    async def _record_metrics(
        self,
        method: str,
        endpoint: str,
        start_time: float,
        response: httpx.Response | None,
        json_data: dict[str, Any] | None,
        retry_count: int,
        error: Exception | None = None,
    ) -> RequestMetrics | None:
        """Record request metrics if monitoring is enabled."""
        if not self._health_monitor:
            return None

        total_duration = (time.time() - start_time) * 1000
        metrics = RequestMetrics(
            method=method,
            endpoint=endpoint,
            status_code=response.status_code if response else None,
            duration_ms=total_duration,
            request_size_bytes=len(json.dumps(json_data).encode()) if json_data else 0,
            response_size_bytes=len(response.content)
            if response and response.content
            else 0,
            retry_count=retry_count,
            hotel_id=self.hotel_id,
            error_type=type(error).__name__ if error else None,
        )
        await self._health_monitor.record_request(metrics)
        return metrics

    async def _execute_with_retry(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        json_data: dict[str, Any] | None,
        headers: dict[str, str],
        timeout: httpx.Timeout,
        data_transformations: dict[str, Callable[[Any], Any]] | None,
    ) -> tuple[APIResponse, int]:
        """Execute request with retry logic."""
        retry_count = 0
        last_error: Exception | None = None

        for attempt in range(self.settings.max_retries + 1):
            try:
                logger.debug(
                    f"API request: {method} {url} (attempt {attempt + 1})",
                    extra={
                        "method": method,
                        "url": url,
                        "attempt": attempt + 1,
                        "hotel_id": self.hotel_id,
                    },
                )

                # Execute the request
                request_start = time.time()
                response = await self._request_handler.execute_request(
                    method, url, params, json_data, headers, timeout
                )
                request_duration = (time.time() - request_start) * 1000

                # Log response
                await self._log_response(
                    method, url, response, request_duration, retry_count
                )

                # Handle response
                api_response = await self._response_handler.handle_response(
                    response, data_transformations
                )

                return api_response, retry_count

            except (
                AuthenticationError,
                httpx.TimeoutException,
                httpx.RequestError,
                httpx.HTTPStatusError,
            ) as e:
                last_error = e
                retry_count += 1

                # Check if we should retry
                if not await self._retry_handler.handle_retry(e, attempt):
                    break

            except OperaCloudError as e:
                # Re-raise custom exceptions without retrying
                last_error = e
                retry_count += 1
                logger.error(
                    f"OperaCloudError during API request (attempt {attempt + 1}): {e}"
                )
                break

            except Exception as e:
                last_error = e
                retry_count += 1
                logger.error(
                    f"Unexpected error during API request (attempt {attempt + 1}): {e}"
                )
                # Only retry unexpected errors on first attempt
                if attempt == 0 and attempt < self.settings.max_retries:
                    await asyncio.sleep(self.settings.retry_backoff)
                    continue
                break

        # All retries exhausted - raise final error
        if last_error:
            self._raise_final_error(last_error, retry_count)

        raise OperaCloudError("Unexpected error in request retry loop")

    def _raise_final_error(self, last_error: Exception, retry_count: int) -> None:
        """Raise final error after all retries exhausted."""
        error_msg = (
            f"Request failed after {self.settings.max_retries + 1} "
            f"attempts: {last_error}"
        )

        logger.error(
            error_msg,
            extra={
                "final_error_type": type(last_error).__name__,
                "total_retries": retry_count,
            },
        )

        # Raise specific exception type based on the last error
        if isinstance(last_error, httpx.TimeoutException):
            raise TimeoutError(error_msg) from last_error
        elif isinstance(last_error, httpx.ConnectError | httpx.RequestError):
            raise APIError(error_msg) from last_error
        elif isinstance(last_error, OperaCloudError):
            raise last_error
        else:
            raise OperaCloudError(error_msg) from last_error

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

        Refactored with reduced complexity through:
        - Extracted cache checking
        - Extracted retry logic
        - Extracted metrics recording
        - Simplified control flow

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

        # Check cache for GET requests
        if enable_caching:
            cached_response = await self._request_handler.check_cache(
                method, endpoint, params
            )
            if cached_response:
                return cached_response

        # Start tracing span if available
        trace_context = self._start_trace_span(method, endpoint)

        # Apply rate limiting
        if self._rate_limiter:
            wait_time = await self._rate_limiter.wait_if_needed()
            if wait_time > 0:
                logger.debug(f"Rate limited - waited {wait_time:.2f}s")

        # Build request parameters
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        if json_data:
            json_data = self._data_transformer.sanitize_request_data(json_data)

        request_headers = self._request_handler.prepare_headers(headers)

        request_timeout = httpx.Timeout(
            connect=10.0,
            read=timeout or self.settings.request_timeout,
            write=10.0,
            pool=5.0,
        )

        # Log request
        await self._log_request(
            method, url, params=params, json=json_data, headers=request_headers
        )

        try:
            # Execute request with retry
            api_response, retry_count = await self._execute_with_retry(
                method,
                url,
                params,
                json_data,
                request_headers,
                request_timeout,
                data_transformations,
            )

            # Record metrics
            if self._health_monitor:
                metrics = await self._record_metrics(
                    method,
                    endpoint,
                    start_time,
                    None,  # Response is handled in retry logic
                    json_data,
                    retry_count,
                )
                api_response.metrics = metrics

            # Cache successful GET responses
            if enable_caching and api_response.success and api_response.data:
                await self._request_handler.save_to_cache(
                    method, endpoint, params, api_response.data
                )

            return api_response

        finally:
            # Finish tracing span
            self._finish_trace_span(trace_context)

    def _start_trace_span(self, method: str, endpoint: str) -> Any:
        """Start distributed tracing span if available."""
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

    def _finish_trace_span(
        self, trace_context: Any, error: Exception | None = None
    ) -> None:
        """Finish distributed tracing span if available."""
        if not self._tracer or not trace_context:
            return

        try:
            self._tracer.finish_span(trace_context, error=error)
        except Exception as e:
            logger.debug(f"Failed to finish trace span: {e}")

    # Convenience methods remain unchanged
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
            token_info = self.auth.get_token_info()
            health_status["api_connectivity"] = "unknown"
            health_status["authentication_test"] = token_info["status"]
        except Exception as e:
            health_status["api_connectivity"] = "error"
            health_status["connectivity_error"] = str(e)

        return health_status
