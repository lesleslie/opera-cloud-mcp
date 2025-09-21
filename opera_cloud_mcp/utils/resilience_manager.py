"""
Advanced resilience and error handling for OPERA Cloud API operations.

Provides circuit breakers, bulkhead isolation, retry strategies,
and failure recovery patterns optimized for hotel operations.
"""

import asyncio
import logging
import secrets
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class FailureType(Enum):
    """Types of failures for different handling strategies."""

    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    RESOURCE_NOT_FOUND = "resource_not_found"


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_failures: list[FailureType] = field(
        default_factory=lambda: [
            FailureType.TIMEOUT,
            FailureType.NETWORK_ERROR,
            FailureType.SERVER_ERROR,
        ]
    )


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout_duration: float = 30.0
    failure_rate_threshold: float = 0.5  # 50% failure rate


@dataclass
class BulkheadConfig:
    """Bulkhead isolation configuration."""

    max_concurrent_requests: int = 20
    queue_size: int = 100
    timeout: float = 30.0


class CircuitBreaker:
    """
    Production-grade circuit breaker for OPERA Cloud APIs.

    Implements the circuit breaker pattern with failure rate monitoring,
    automatic recovery, and bulkhead isolation.
    """

    def __init__(
        self, name: str, config: CircuitBreakerConfig, hotel_id: str | None = None
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name
            config: Configuration settings
            hotel_id: Hotel identifier for logging context
        """
        self.name = name
        self.config = config
        self.hotel_id = hotel_id

        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self.last_attempt_time: float | None = None

        # Metrics
        self.total_requests = 0
        self.total_failures = 0
        self.state_change_times: list[datetime] = []

        # Sliding window for failure rate calculation
        self.request_window: deque[tuple[datetime, bool]] = deque(
            maxlen=100
        )  # Last 100 requests

        logger.info(
            "Circuit breaker initialized",
            extra={
                "name": name,
                "hotel_id": hotel_id,
                "failure_threshold": config.failure_threshold,
                "recovery_timeout": config.recovery_timeout,
            },
        )

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset from open state."""
        if self.state != CircuitState.OPEN:
            return False

        if self.last_failure_time is None:
            return True

        return time.time() - self.last_failure_time >= self.config.recovery_timeout

    def _calculate_failure_rate(self) -> float:
        """Calculate current failure rate from sliding window."""
        if len(self.request_window) < 5:  # Need minimum requests
            return 0.0

        failures = sum(1 for success in self.request_window if not success)
        return failures / len(self.request_window)

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails
        """
        self.total_requests += 1
        self.last_attempt_time = time.time()

        # Check if circuit should reset
        if self._should_attempt_reset():
            self.state = CircuitState.HALF_OPEN
            self.success_count = 0
            logger.info(f"Circuit breaker {self.name} attempting reset (half-open)")

        # Handle open circuit
        if self.state == CircuitState.OPEN:
            from opera_cloud_mcp.utils.exceptions import CircuitBreakerError

            raise CircuitBreakerError(f"Circuit breaker {self.name} is open")

        try:
            # Execute the function
            result = (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )

            # Record success
            self._record_success()
            return result

        except Exception:
            # Record failure
            self._record_failure()
            raise

    def _record_success(self) -> None:
        """Record a successful request."""
        self.request_window.append((datetime.now(), True))

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.state_change_times.append(datetime.now())
                logger.info(f"Circuit breaker {self.name} closed (recovered)")
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _record_failure(self) -> None:
        """Record a failed request."""
        self.request_window.append((datetime.now(), False))
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        # Check if we should open the circuit
        failure_rate = self._calculate_failure_rate()

        if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN) and (
            self.failure_count >= self.config.failure_threshold
            or failure_rate >= self.config.failure_rate_threshold
        ):
            self.state = CircuitState.OPEN
            self.state_change_times.append(datetime.now())
            logger.warning(
                f"Circuit breaker {self.name} opened",
                extra={
                    "failure_count": self.failure_count,
                    "failure_rate": failure_rate,
                    "threshold": self.config.failure_threshold,
                },
            )

    def get_metrics(self) -> dict[str, Any]:
        """Get circuit breaker metrics."""
        failure_rate = self._calculate_failure_rate()

        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "current_failure_rate": failure_rate,
            "last_failure_time": self.last_failure_time,
            "last_attempt_time": self.last_attempt_time,
            "state_changes": len(self.state_change_times),
        }


class BulkheadIsolator:
    """
    Bulkhead isolation for protecting resources.

    Limits concurrent operations to prevent resource exhaustion
    and provides queue management.
    """

    def __init__(self, name: str, config: BulkheadConfig):
        """
        Initialize bulkhead isolator.

        Args:
            name: Isolator name
            config: Configuration settings
        """
        self.name = name
        self.config = config

        # Semaphore for limiting concurrent operations
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)

        # Queue for pending requests
        self.request_queue: asyncio.Queue = asyncio.Queue(maxsize=config.queue_size)

        # Metrics
        self.active_requests = 0
        self.queued_requests = 0
        self.total_requests = 0
        self.rejected_requests = 0

        logger.info(
            "Bulkhead isolator initialized",
            extra={
                "name": name,
                "max_concurrent": config.max_concurrent_requests,
                "queue_size": config.queue_size,
            },
        )

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with bulkhead protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            ResourceExhaustedError: If resources are exhausted
        """
        self.total_requests += 1

        try:
            # Try to acquire semaphore with timeout
            await asyncio.wait_for(
                self.semaphore.acquire(), timeout=self.config.timeout
            )

            self.active_requests += 1

            try:
                # Execute the function
                result = (
                    await func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                )
                return result
            finally:
                self.active_requests -= 1
                self.semaphore.release()

        except TimeoutError:
            self.rejected_requests += 1
            from opera_cloud_mcp.utils.exceptions import CircuitBreakerError

            raise CircuitBreakerError(
                f"Bulkhead {self.name} resource exhausted"
            ) from None

    def get_metrics(self) -> dict[str, Any]:
        """Get bulkhead metrics."""
        return {
            "name": self.name,
            "active_requests": self.active_requests,
            "available_slots": self.semaphore._value,
            "max_concurrent": self.config.max_concurrent_requests,
            "total_requests": self.total_requests,
            "rejected_requests": self.rejected_requests,
            "rejection_rate": self.rejected_requests / max(self.total_requests, 1),
        }


class RetryManager:
    """
    Intelligent retry manager with adaptive strategies.

    Provides exponential backoff, jitter, and failure-type-specific
    retry policies for different OPERA Cloud API scenarios.
    """

    def __init__(self, default_policy: RetryPolicy | None = None):
        """
        Initialize retry manager.

        Args:
            default_policy: Default retry policy
        """
        self.default_policy = default_policy or RetryPolicy()
        self.failure_specific_policies: dict[FailureType, RetryPolicy] = {
            # Authentication errors need immediate retry after token refresh
            FailureType.AUTHENTICATION: RetryPolicy(
                max_attempts=2,
                base_delay=0.1,
                max_delay=1.0,
                backoff_multiplier=1.5,
                retryable_failures=[FailureType.AUTHENTICATION],
            ),
            # Rate limits need longer delays
            FailureType.RATE_LIMIT: RetryPolicy(
                max_attempts=3,
                base_delay=5.0,
                max_delay=300.0,
                backoff_multiplier=3.0,
                retryable_failures=[FailureType.RATE_LIMIT],
            ),
            # Network errors are aggressively retried
            FailureType.NETWORK_ERROR: RetryPolicy(
                max_attempts=5,
                base_delay=1.0,
                max_delay=30.0,
                backoff_multiplier=2.0,
                jitter=True,
                retryable_failures=[FailureType.NETWORK_ERROR, FailureType.TIMEOUT],
            ),
            # Validation errors should not be retried
            FailureType.VALIDATION_ERROR: RetryPolicy(
                max_attempts=1, retryable_failures=[]
            ),
        }

        # Metrics
        self.retry_attempts: dict[FailureType, int] = defaultdict(int)
        self.successful_retries: dict[FailureType, int] = defaultdict(int)

        logger.info("Retry manager initialized")

    def _classify_failure(self, exception: Exception) -> FailureType:
        """
        Classify exception into failure type.

        Args:
            exception: Exception to classify

        Returns:
            FailureType classification
        """
        exception_name = type(exception).__name__.lower()

        if "timeout" in exception_name:
            return FailureType.TIMEOUT
        elif "auth" in exception_name:
            return FailureType.AUTHENTICATION
        elif "rate" in exception_name or "limit" in exception_name:
            return FailureType.RATE_LIMIT
        elif "server" in exception_name or "500" in str(exception):
            return FailureType.SERVER_ERROR
        elif "network" in exception_name or "connection" in exception_name:
            return FailureType.NETWORK_ERROR
        elif "validation" in exception_name or "400" in str(exception):
            return FailureType.VALIDATION_ERROR
        elif "404" in str(exception) or "not found" in str(exception).lower():
            return FailureType.RESOURCE_NOT_FOUND
        return FailureType.SERVER_ERROR  # Default to retryable

    def _calculate_delay(self, attempt: int, policy: RetryPolicy) -> float:
        """
        Calculate delay for retry attempt.

        Args:
            attempt: Attempt number (0-based)
            policy: Retry policy

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = policy.base_delay * (policy.backoff_multiplier**attempt)
        delay = min(delay, policy.max_delay)

        # Add jitter to prevent thundering herd
        if policy.jitter:
            # Generate cryptographically secure jitter between 0.1 and 0.3
            jitter = (secrets.randbelow(200000) / 1000000.0 + 0.1) * delay
            delay += jitter

        return delay

    def _should_retry(
        self, failure_type: FailureType, effective_policy: RetryPolicy
    ) -> bool:
        """Check if a failure should be retried."""
        return failure_type in effective_policy.retryable_failures

    def _is_last_attempt(self, attempt: int, effective_policy: RetryPolicy) -> bool:
        """Check if this is the last attempt."""
        return attempt >= effective_policy.max_attempts - 1

    async def _handle_retry_success(
        self, attempt: int, last_exception: Exception | None
    ) -> None:
        """Handle successful retry after previous failures."""
        if attempt > 0 and last_exception is not None:
            failure_type = self._classify_failure(last_exception)
            self.successful_retries[failure_type] += 1
            logger.info(
                "Retry succeeded",
                extra={
                    "attempt": attempt + 1,
                    "failure_type": failure_type.value,
                    "total_attempts": self.default_policy.max_attempts,
                },
            )

    def _handle_non_retryable_failure(
        self, failure_type: FailureType, e: Exception
    ) -> None:
        """Handle non-retryable failure."""
        logger.info(
            "Non-retryable failure",
            extra={"failure_type": failure_type.value, "exception": str(e)},
        )
        raise e

    def _handle_exhausted_attempts(
        self, attempt: int, failure_type: FailureType, e: Exception
    ) -> None:
        """Handle case when all retry attempts are exhausted."""
        logger.warning(
            "All retry attempts exhausted",
            extra={
                "attempts": attempt + 1,
                "failure_type": failure_type.value,
                "final_exception": str(e),
            },
        )
        raise e

    def _log_retry_attempt(
        self, attempt: int, failure_type: FailureType, delay: float, e: Exception
    ) -> None:
        """Log retry attempt."""
        logger.info(
            "Retrying after failure",
            extra={
                "attempt": attempt + 1,
                "max_attempts": self.default_policy.max_attempts,
                "failure_type": failure_type.value,
                "delay_seconds": delay,
                "exception": str(e),
            },
        )

    async def execute_with_retry(
        self, func: Callable, *args, policy: RetryPolicy | None = None, **kwargs
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Function arguments
            policy: Override retry policy
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries exhausted
        """
        effective_policy = policy or self.default_policy
        last_exception = None

        for attempt in range(effective_policy.max_attempts):
            try:
                result = (
                    await func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                )

                # Handle successful retry
                await self._handle_retry_success(attempt, last_exception)

                return result

            except Exception as e:
                last_exception = e
                failure_type = self._classify_failure(e)

                # Check if this failure type is retryable
                if not self._should_retry(failure_type, effective_policy):
                    self._handle_non_retryable_failure(failure_type, e)

                # Check if we have more attempts
                if self._is_last_attempt(attempt, effective_policy):
                    self._handle_exhausted_attempts(attempt, failure_type, e)

                # Record retry attempt
                self.retry_attempts[failure_type] += 1

                # Calculate delay and wait
                delay = self._calculate_delay(attempt, effective_policy)

                # Log retry attempt
                self._log_retry_attempt(attempt, failure_type, delay, e)

                await asyncio.sleep(delay)

        # This should never be reached
        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError("Retry failed without a specific exception")

    def get_retry_statistics(self) -> dict[str, Any]:
        """Get retry statistics."""
        total_attempts = sum(self.retry_attempts.values())
        total_successes = sum(self.successful_retries.values())

        stats: dict[str, Any] = {
            "total_retry_attempts": total_attempts,
            "successful_retries": total_successes,
            "success_rate": total_successes / max(total_attempts, 1),
            "by_failure_type": {},
        }

        for failure_type in FailureType:
            attempts = self.retry_attempts[failure_type]
            successes = self.successful_retries[failure_type]

            if attempts > 0:
                stats["by_failure_type"][failure_type.value] = {
                    "attempts": attempts,
                    "successes": successes,
                    "success_rate": successes / attempts,
                }

        return stats


class ResilienceManager:
    """
    Comprehensive resilience manager combining all patterns.

    Orchestrates circuit breakers, bulkheads, and retry logic
    for OPERA Cloud API resilience.
    """

    def __init__(self, hotel_id: str | None = None):
        """
        Initialize resilience manager.

        Args:
            hotel_id: Hotel identifier for context
        """
        self.hotel_id = hotel_id

        # Component managers
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.bulkheads: dict[str, BulkheadIsolator] = {}
        self.retry_manager = RetryManager()

        # Default configurations
        self.default_circuit_config = CircuitBreakerConfig()
        self.default_bulkhead_config = BulkheadConfig()

        logger.info("Resilience manager initialized", extra={"hotel_id": hotel_id})

    def get_or_create_circuit_breaker(
        self, name: str, config: CircuitBreakerConfig | None = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.circuit_breakers:
            effective_config = config or self.default_circuit_config
            self.circuit_breakers[name] = CircuitBreaker(
                name=name, config=effective_config, hotel_id=self.hotel_id
            )

        return self.circuit_breakers[name]

    def get_or_create_bulkhead(
        self, name: str, config: BulkheadConfig | None = None
    ) -> BulkheadIsolator:
        """Get or create a bulkhead isolator."""
        if name not in self.bulkheads:
            effective_config = config or self.default_bulkhead_config
            self.bulkheads[name] = BulkheadIsolator(name=name, config=effective_config)

        return self.bulkheads[name]

    async def execute_with_resilience(
        self,
        func: Callable,
        *args,
        circuit_breaker_name: str | None = None,
        bulkhead_name: str | None = None,
        retry_policy: RetryPolicy | None = None,
        **kwargs,
    ) -> Any:
        """
        Execute function with full resilience patterns.

        Args:
            func: Function to execute
            *args: Function arguments
            circuit_breaker_name: Circuit breaker to use
            bulkhead_name: Bulkhead isolator to use
            retry_policy: Retry policy to use
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """

        async def resilient_execution():
            # Apply bulkhead isolation if specified
            if bulkhead_name:
                bulkhead = self.get_or_create_bulkhead(bulkhead_name)
                return await bulkhead.execute(func, *args, **kwargs)
            return (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )

        # Apply circuit breaker if specified
        if circuit_breaker_name:
            circuit_breaker = self.get_or_create_circuit_breaker(circuit_breaker_name)

            # Combine circuit breaker with retry
            return await self.retry_manager.execute_with_retry(
                circuit_breaker.call, resilient_execution, policy=retry_policy
            )
        # Just apply retry
        return await self.retry_manager.execute_with_retry(
            resilient_execution, policy=retry_policy
        )

    def get_overall_health(self) -> dict[str, Any]:
        """Get overall resilience health status."""
        circuit_health = []
        bulkhead_health = []

        # Collect circuit breaker health
        for name, cb in self.circuit_breakers.items():
            metrics = cb.get_metrics()
            circuit_health.append(
                {
                    "name": name,
                    "state": metrics["state"],
                    "health_score": 1.0 if metrics["state"] == "closed" else 0.0,
                }
            )

        # Collect bulkhead health
        for name, bh in self.bulkheads.items():
            metrics = bh.get_metrics()
            rejection_rate = metrics["rejection_rate"]
            health_score = 1.0 - min(rejection_rate, 1.0)
            bulkhead_health.append(
                {
                    "name": name,
                    "rejection_rate": rejection_rate,
                    "health_score": health_score,
                }
            )

        # Calculate overall health
        all_scores = [cb["health_score"] for cb in circuit_health] + [
            bh["health_score"] for bh in bulkhead_health
        ]
        overall_health = sum(all_scores) / len(all_scores) if all_scores else 1.0

        return {
            "overall_health_score": overall_health,
            "status": "healthy"
            if overall_health > 0.8
            else "degraded"
            if overall_health > 0.5
            else "unhealthy",
            "circuit_breakers": circuit_health,
            "bulkheads": bulkhead_health,
            "retry_stats": self.retry_manager.get_retry_statistics(),
        }
