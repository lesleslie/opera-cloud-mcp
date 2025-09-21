"""
Custom exceptions for OPERA Cloud MCP server.

Provides a hierarchy of exceptions for different error conditions
that can occur during OPERA Cloud API operations.
"""

from typing import Any


class OperaCloudError(Exception):
    """
    Base exception for all OPERA Cloud MCP errors.

    This is the root exception class that all other custom exceptions
    inherit from. It provides basic error handling and context.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """
        Initialize the exception.

        Args:
            message: Error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class AuthenticationError(OperaCloudError):
    """
    Raised when authentication fails.

    This includes OAuth token acquisition failures, token expiry,
    and authorization errors.
    """

    pass


class SecurityError(OperaCloudError):
    """
    Raised when security validation fails.

    This includes security policy violations, threat detection,
    and security-related configuration errors.
    """

    def __init__(
        self,
        message: str,
        security_level: str | None = None,
        threat_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the security error.

        Args:
            message: Error message
            security_level: Security level of the violation (low, medium, high)
            threat_type: Type of security threat detected
            details: Optional additional error details
        """
        super().__init__(message, details)
        self.security_level = security_level
        self.threat_type = threat_type


class ValidationError(OperaCloudError):
    """
    Raised when request validation fails.

    This includes invalid parameters, missing required fields,
    and data format errors.
    """

    pass


class ResourceNotFoundError(OperaCloudError):
    """
    Raised when a requested resource is not found.

    This includes missing reservations, guest profiles,
    room numbers, and other entity lookups.
    """

    pass


class RateLimitError(OperaCloudError):
    """
    Raised when API rate limits are exceeded.

    This indicates that the client has made too many requests
    and should implement backoff and retry logic.
    """

    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        limit_type: str = "requests",
        current_usage: int | None = None,
        limit_value: int | None = None,
        reset_time: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            limit_type: Type of limit exceeded (requests, bandwidth, etc.)
            current_usage: Current usage count
            limit_value: Maximum allowed limit
            reset_time: Unix timestamp when the limit resets
            details: Optional additional error details
        """
        super().__init__(message, details)
        self.retry_after = retry_after
        self.limit_type = limit_type
        self.current_usage = current_usage
        self.limit_value = limit_value
        self.reset_time = reset_time

    def get_backoff_time(self, default_backoff: int = 60) -> int:
        """Get recommended backoff time in seconds."""
        if self.retry_after is not None:
            return self.retry_after
        return default_backoff


class ConfigurationError(OperaCloudError):
    """
    Raised when configuration is invalid or missing.

    This includes missing environment variables, invalid URLs,
    and configuration validation errors.
    """

    pass


class APIError(OperaCloudError):
    """
    Raised for general API errors.

    This includes server errors, network errors, and other
    API-related issues that don't fit other categories.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
        endpoint: str | None = None,
        method: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response_data: Response data from API
            endpoint: API endpoint that caused the error
            method: HTTP method used
            details: Optional additional error details
        """
        super().__init__(message, details)
        self.status_code = status_code
        self.response_data = response_data or {}
        self.endpoint = endpoint
        self.method = method

    def is_client_error(self) -> bool:
        """Check if this is a client error (4xx status code)."""
        return self.status_code is not None and 400 <= self.status_code < 500

    def is_server_error(self) -> bool:
        """Check if this is a server error (5xx status code)."""
        return self.status_code is not None and self.status_code >= 500

    def is_retryable(self) -> bool:
        """Check if this error is potentially retryable."""
        if self.status_code is None:
            return True  # Network errors are generally retryable

        # Retryable status codes
        retryable_codes = {408, 429, 500, 502, 503, 504}
        return self.status_code in retryable_codes


class TimeoutError(OperaCloudError):
    """
    Raised when operations timeout.

    This includes HTTP request timeouts and operation timeouts.
    """

    def __init__(
        self,
        message: str,
        timeout_duration: float | None = None,
        operation_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the timeout error.

        Args:
            message: Error message
            timeout_duration: The timeout duration that was exceeded
            operation_type: Type of operation that timed out
            details: Optional additional error details
        """
        super().__init__(message, details)
        self.timeout_duration = timeout_duration
        self.operation_type = operation_type


class DataError(OperaCloudError):
    """
    Raised when data processing fails.

    This includes JSON parsing errors, data transformation errors,
    and model validation failures.
    """

    pass


class CachingError(OperaCloudError):
    """
    Raised when caching operations fail.

    This includes cache initialization errors, cache read/write failures,
    and cache invalidation issues.
    """

    pass


class CircuitBreakerError(OperaCloudError):
    """
    Raised when circuit breaker is open.

    This indicates that the service is temporarily unavailable
    due to repeated failures and the circuit breaker pattern
    has been activated for protection.
    """

    def __init__(
        self,
        message: str,
        failure_count: int = 0,
        circuit_state: str = "unknown",
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the circuit breaker error.

        Args:
            message: Error message
            failure_count: Number of failures that triggered the circuit breaker
            circuit_state: Current state of the circuit breaker
            details: Optional additional error details
        """
        super().__init__(message, details)
        self.failure_count = failure_count
        self.circuit_state = circuit_state


# Reservation-specific exceptions


class ReservationError(OperaCloudError):
    """Base exception for reservation-related errors."""

    def __init__(
        self,
        message: str,
        confirmation_number: str | None = None,
        hotel_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        """
        Initialize the reservation error.

        Args:
            message: Error message
            confirmation_number: Reservation confirmation number if applicable
            hotel_id: Hotel identifier if applicable
            details: Optional additional error details
        """
        super().__init__(message, details)
        self.confirmation_number = confirmation_number
        self.hotel_id = hotel_id


class ReservationNotFoundError(ReservationError):
    """Raised when a reservation cannot be found."""

    pass


class ReservationConflictError(ReservationError):
    """
    Raised when a reservation operation conflicts with current state.

    This includes attempts to modify canceled reservations,
    double-booking scenarios, and state transition conflicts.
    """

    def __init__(
        self,
        message: str,
        confirmation_number: str | None = None,
        hotel_id: str | None = None,
        current_status: str | None = None,
        requested_action: str | None = None,
        details: dict | None = None,
    ) -> None:
        """
        Initialize the reservation conflict error.

        Args:
            message: Error message
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier
            current_status: Current reservation status
            requested_action: Action that was attempted
            details: Optional additional error details
        """
        super().__init__(message, confirmation_number, hotel_id, details)
        self.current_status = current_status
        self.requested_action = requested_action


class ReservationValidationError(ReservationError, ValidationError):
    """
    Raised when reservation data validation fails.

    This includes invalid dates, room types, guest information,
    and business rule violations.
    """

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        field_value: str | None = None,
        validation_rule: str | None = None,
        confirmation_number: str | None = None,
        hotel_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        """
        Initialize the reservation validation error.

        Args:
            message: Error message
            field_name: Name of the invalid field
            field_value: Value that failed validation
            validation_rule: Validation rule that was violated
            confirmation_number: Reservation confirmation number if applicable
            hotel_id: Hotel identifier if applicable
            details: Optional additional error details
        """
        super().__init__(message, confirmation_number, hotel_id, details)
        self.field_name = field_name
        self.field_value = field_value
        self.validation_rule = validation_rule


class RoomAvailabilityError(ReservationError):
    """
    Raised when requested rooms are not available.

    This includes no availability for dates, room type not available,
    and rate restrictions.
    """

    def __init__(
        self,
        message: str,
        arrival_date: str | None = None,
        departure_date: str | None = None,
        room_type: str | None = None,
        rate_code: str | None = None,
        available_alternatives: list[dict[str, Any]] | None = None,
        hotel_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the room availability error.

        Args:
            message: Error message
            arrival_date: Requested arrival date
            departure_date: Requested departure date
            room_type: Requested room type
            rate_code: Requested rate code
            available_alternatives: List of alternative room/rate options
            hotel_id: Hotel identifier
            details: Optional additional error details
        """
        super().__init__(message, None, hotel_id, details)
        self.arrival_date = arrival_date
        self.departure_date = departure_date
        self.room_type = room_type
        self.rate_code = rate_code
        self.available_alternatives = available_alternatives or []


class PaymentError(ReservationError):
    """
    Raised when payment processing fails.

    This includes payment authorization failures, invalid payment methods,
    and payment processing timeouts.
    """

    def __init__(
        self,
        message: str,
        payment_type: str | None = None,
        amount: float | None = None,
        currency: str | None = None,
        transaction_id: str | None = None,
        confirmation_number: str | None = None,
        hotel_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        """
        Initialize the payment error.

        Args:
            message: Error message
            payment_type: Type of payment (credit card, deposit, etc.)
            amount: Payment amount
            currency: Payment currency
            transaction_id: Payment transaction identifier
            confirmation_number: Associated reservation confirmation number
            hotel_id: Hotel identifier
            details: Optional additional error details
        """
        super().__init__(message, confirmation_number, hotel_id, details)
        self.payment_type = payment_type
        self.amount = amount
        self.currency = currency
        self.transaction_id = transaction_id


class CancellationError(ReservationError):
    """
    Raised when reservation cancellation fails.

    This includes cancellation policy violations, penalty calculation errors,
    and cancellation processing failures.
    """

    def __init__(
        self,
        message: str,
        cancellation_reason: str | None = None,
        penalty_amount: float | None = None,
        cancellation_allowed: bool = True,
        policy_violation: str | None = None,
        confirmation_number: str | None = None,
        hotel_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        """
        Initialize the cancellation error.

        Args:
            message: Error message
            cancellation_reason: Reason for cancellation
            penalty_amount: Calculated penalty amount
            cancellation_allowed: Whether cancellation is allowed
            policy_violation: Policy that prevents cancellation
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier
            details: Optional additional error details
        """
        super().__init__(message, confirmation_number, hotel_id, details)
        self.cancellation_reason = cancellation_reason
        self.penalty_amount = penalty_amount
        self.cancellation_allowed = cancellation_allowed
        self.policy_violation = policy_violation


class BulkOperationError(OperaCloudError):
    """
    Raised when bulk reservation operations encounter errors.

    This includes partial failures, validation errors across multiple
    reservations, and bulk processing timeouts.
    """

    def __init__(
        self,
        message: str,
        job_id: str | None = None,
        total_count: int = 0,
        processed_count: int = 0,
        error_count: int = 0,
        individual_errors: list[dict[str, Any]] | None = None,
        hotel_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the bulk operation error.

        Args:
            message: Error message
            job_id: Bulk operation job identifier
            total_count: Total number of operations requested
            processed_count: Number of operations processed
            error_count: Number of operations that failed
            individual_errors: List of individual operation errors
            hotel_id: Hotel identifier
            details: Optional additional error details
        """
        super().__init__(message, details)
        self.job_id = job_id
        self.total_count = total_count
        self.processed_count = processed_count
        self.error_count = error_count
        self.individual_errors = individual_errors or []
        self.hotel_id = hotel_id

    def get_success_rate(self) -> float:
        """Calculate the success rate of the bulk operation."""
        if self.total_count == 0:
            return 0.0
        success_count = self.processed_count - self.error_count
        return success_count / self.total_count

    def has_partial_success(self) -> bool:
        """Check if the bulk operation had partial success."""
        return self.processed_count > 0 and self.error_count > 0
