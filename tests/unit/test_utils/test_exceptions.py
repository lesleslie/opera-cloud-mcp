"""Unit tests for custom exceptions.

Tests for exception classes in opera_cloud_mcp/utils/exceptions.py
"""

import pytest

from opera_cloud_mcp.utils.exceptions import (
    OperaCloudError,
    AuthenticationError,
    SecurityError,
    ValidationError,
    ResourceNotFoundError,
    RateLimitError,
    ConfigurationError,
    APIError,
    TimeoutError,
    DataError,
    CachingError,
    CircuitBreakerError,
    ReservationError,
    ReservationNotFoundError,
    ReservationConflictError,
    ReservationValidationError,
    RoomAvailabilityError,
    PaymentError,
    CancellationError,
    BulkOperationError,
)


class TestBaseExceptions:
    """Test base exception classes."""

    def test_opera_cloud_error_basic(self):
        """Test basic OperaCloudError creation."""
        error = OperaCloudError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_opera_cloud_error_with_details(self):
        """Test OperaCloudError with details."""
        details = {"field": "value", "code": 123}
        error = OperaCloudError("Test error", details=details)
        assert "Details:" in str(error)
        assert error.details == details

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Auth failed")
        assert isinstance(error, OperaCloudError)
        assert "Auth failed" in str(error)

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Validation failed")
        assert isinstance(error, OperaCloudError)
        assert "Validation failed" in str(error)

    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError."""
        error = ResourceNotFoundError("Resource not found")
        assert isinstance(error, OperaCloudError)

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Config invalid")
        assert isinstance(error, OperaCloudError)

    def test_data_error(self):
        """Test DataError."""
        error = DataError("Data processing failed")
        assert isinstance(error, OperaCloudError)

    def test_caching_error(self):
        """Test CachingError."""
        error = CachingError("Cache operation failed")
        assert isinstance(error, OperaCloudError)


class TestSecurityError:
    """Test SecurityError specific features."""

    def test_security_error_basic(self):
        """Test basic SecurityError."""
        error = SecurityError("Security violation")
        assert error.security_level is None
        assert error.threat_type is None

    def test_security_error_with_level(self):
        """Test SecurityError with security level."""
        error = SecurityError("Security violation", security_level="high")
        assert error.security_level == "high"

    def test_security_error_full(self):
        """Test SecurityError with all parameters."""
        error = SecurityError(
            "Threat detected",
            security_level="high",
            threat_type="sql_injection",
            details={"ip": "192.168.1.1"}
        )
        assert error.security_level == "high"
        assert error.threat_type == "sql_injection"
        assert error.details["ip"] == "192.168.1.1"


class TestRateLimitError:
    """Test RateLimitError specific features."""

    def test_rate_limit_error_basic(self):
        """Test basic RateLimitError."""
        error = RateLimitError("Rate limit exceeded")
        assert error.retry_after is None
        assert error.limit_type == "requests"

    def test_rate_limit_error_with_retry_after(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        assert error.retry_after == 60

    def test_rate_limit_error_full(self):
        """Test RateLimitError with all parameters."""
        error = RateLimitError(
            "Rate limit exceeded",
            retry_after=120,
            limit_type="bandwidth",
            current_usage=1000,
            limit_value=2000,
            reset_time=1234567890,
            details={"endpoint": "/api/reservations"}
        )
        assert error.retry_after == 120
        assert error.limit_type == "bandwidth"
        assert error.current_usage == 1000
        assert error.limit_value == 2000
        assert error.reset_time == 1234567890

    def test_get_backoff_time_with_retry_after(self):
        """Test get_backoff_time returns retry_after when set."""
        error = RateLimitError("Rate limit exceeded", retry_after=60)
        assert error.get_backoff_time() == 60

    def test_get_backoff_time_default(self):
        """Test get_backoff_time returns default when retry_after not set."""
        error = RateLimitError("Rate limit exceeded")
        assert error.get_backoff_time() == 60

    def test_get_backoff_time_custom_default(self):
        """Test get_backoff_time with custom default."""
        error = RateLimitError("Rate limit exceeded")
        assert error.get_backoff_time(default_backoff=120) == 120


class TestAPIError:
    """Test APIError specific features."""

    def test_api_error_basic(self):
        """Test basic APIError."""
        error = APIError("API request failed")
        assert error.status_code is None
        assert error.response_data == {}
        assert error.endpoint is None
        assert error.method is None

    def test_api_error_full(self):
        """Test APIError with all parameters."""
        response_data = {"error": "details"}
        error = APIError(
            "API request failed",
            status_code=500,
            response_data=response_data,
            endpoint="/api/reservations",
            method="GET",
            details={"timeout": 30}
        )
        assert error.status_code == 500
        assert error.response_data == response_data
        assert error.endpoint == "/api/reservations"
        assert error.method == "GET"

    def test_is_client_error_4xx(self):
        """Test is_client_error with 4xx status."""
        error = APIError("Not found", status_code=404)
        assert error.is_client_error() is True
        assert error.is_server_error() is False

    def test_is_server_error_5xx(self):
        """Test is_server_error with 5xx status."""
        error = APIError("Server error", status_code=500)
        assert error.is_server_error() is True
        assert error.is_client_error() is False

    def test_is_retryable_network_error(self):
        """Test is_retryable with no status code (network error)."""
        error = APIError("Network error")
        assert error.is_retryable() is True

    def test_is_retryable_408(self):
        """Test is_retryable with 408 Request Timeout."""
        error = APIError("Timeout", status_code=408)
        assert error.is_retryable() is True

    def test_is_retryable_429(self):
        """Test is_retryable with 429 Too Many Requests."""
        error = APIError("Rate limited", status_code=429)
        assert error.is_retryable() is True

    def test_is_retryable_500(self):
        """Test is_retryable with 500 Internal Server Error."""
        error = APIError("Server error", status_code=500)
        assert error.is_retryable() is True

    def test_is_retryable_502(self):
        """Test is_retryable with 502 Bad Gateway."""
        error = APIError("Bad gateway", status_code=502)
        assert error.is_retryable() is True

    def test_is_retryable_503(self):
        """Test is_retryable with 503 Service Unavailable."""
        error = APIError("Service unavailable", status_code=503)
        assert error.is_retryable() is True

    def test_is_retryable_504(self):
        """Test is_retryable with 504 Gateway Timeout."""
        error = APIError("Gateway timeout", status_code=504)
        assert error.is_retryable() is True

    def test_is_not_retryable_404(self):
        """Test is_retryable with 404 Not Found."""
        error = APIError("Not found", status_code=404)
        assert error.is_retryable() is False

    def test_is_not_retryable_400(self):
        """Test is_retryable with 400 Bad Request."""
        error = APIError("Bad request", status_code=400)
        assert error.is_retryable() is False


class TestTimeoutError:
    """Test TimeoutError specific features."""

    def test_timeout_error_basic(self):
        """Test basic TimeoutError."""
        error = TimeoutError("Operation timed out")
        assert error.timeout_duration is None
        assert error.operation_type is None

    def test_timeout_error_full(self):
        """Test TimeoutError with all parameters."""
        error = TimeoutError(
            "Operation timed out",
            timeout_duration=30.5,
            operation_type="api_request",
            details={"endpoint": "/api/reservations"}
        )
        assert error.timeout_duration == 30.5
        assert error.operation_type == "api_request"


class TestCircuitBreakerError:
    """Test CircuitBreakerError specific features."""

    def test_circuit_breaker_error_basic(self):
        """Test basic CircuitBreakerError."""
        error = CircuitBreakerError("Circuit breaker open")
        assert error.failure_count == 0
        assert error.circuit_state == "unknown"

    def test_circuit_breaker_error_full(self):
        """Test CircuitBreakerError with all parameters."""
        error = CircuitBreakerError(
            "Circuit breaker open",
            failure_count=5,
            circuit_state="open",
            details={"service": "reservations"}
        )
        assert error.failure_count == 5
        assert error.circuit_state == "open"


class TestReservationErrors:
    """Test reservation-specific error classes."""

    def test_reservation_error_basic(self):
        """Test basic ReservationError."""
        error = ReservationError("Reservation error")
        assert error.confirmation_number is None
        assert error.hotel_id is None

    def test_reservation_error_full(self):
        """Test ReservationError with all parameters."""
        error = ReservationError(
            "Reservation error",
            confirmation_number="ABC123",
            hotel_id="HOTEL1",
            details={"guest": "John Doe"}
        )
        assert error.confirmation_number == "ABC123"
        assert error.hotel_id == "HOTEL1"

    def test_reservation_not_found_error(self):
        """Test ReservationNotFoundError."""
        error = ReservationNotFoundError("Reservation not found")
        assert isinstance(error, ReservationError)

    def test_reservation_conflict_error(self):
        """Test ReservationConflictError."""
        error = ReservationConflictError(
            "Reservation conflict",
            confirmation_number="ABC123",
            hotel_id="HOTEL1",
            current_status="checked_in",
            requested_action="cancel"
        )
        assert error.current_status == "checked_in"
        assert error.requested_action == "cancel"

    def test_reservation_validation_error(self):
        """Test ReservationValidationError."""
        error = ReservationValidationError(
            "Validation failed",
            field_name="arrival_date",
            field_value="2024-02-30",
            validation_rule="valid_date",
            confirmation_number="ABC123",
            hotel_id="HOTEL1"
        )
        assert error.field_name == "arrival_date"
        assert error.field_value == "2024-02-30"
        assert error.validation_rule == "valid_date"

    def test_room_availability_error(self):
        """Test RoomAvailabilityError."""
        alternatives = [{"room_type": "DELUXE", "rate": 200}]
        error = RoomAvailabilityError(
            "No availability",
            arrival_date="2024-12-25",
            departure_date="2024-12-26",
            room_type="STANDARD",
            rate_code="RACK",
            available_alternatives=alternatives,
            hotel_id="HOTEL1"
        )
        assert error.arrival_date == "2024-12-25"
        assert error.departure_date == "2024-12-26"
        assert error.room_type == "STANDARD"
        assert error.rate_code == "RACK"
        assert error.available_alternatives == alternatives

    def test_payment_error(self):
        """Test PaymentError."""
        error = PaymentError(
            "Payment failed",
            payment_type="credit_card",
            amount=100.50,
            currency="USD",
            transaction_id="TX12345",
            confirmation_number="ABC123",
            hotel_id="HOTEL1"
        )
        assert error.payment_type == "credit_card"
        assert error.amount == 100.50
        assert error.currency == "USD"
        assert error.transaction_id == "TX12345"

    def test_cancellation_error(self):
        """Test CancellationError."""
        error = CancellationError(
            "Cancellation failed",
            cancellation_reason="guest_request",
            penalty_amount=50.0,
            cancellation_allowed=True,
            policy_violation=None,
            confirmation_number="ABC123",
            hotel_id="HOTEL1"
        )
        assert error.cancellation_reason == "guest_request"
        assert error.penalty_amount == 50.0
        assert error.cancellation_allowed is True


class TestBulkOperationError:
    """Test BulkOperationError specific features."""

    def test_bulk_operation_error_basic(self):
        """Test basic BulkOperationError."""
        error = BulkOperationError("Bulk operation failed")
        assert error.job_id is None
        assert error.total_count == 0
        assert error.processed_count == 0
        assert error.error_count == 0
        assert error.individual_errors == []

    def test_bulk_operation_error_full(self):
        """Test BulkOperationError with all parameters."""
        individual_errors = [
            {"index": 0, "error": "Invalid data"},
            {"index": 2, "error": "Not found"}
        ]
        error = BulkOperationError(
            "Bulk operation partial failure",
            job_id="JOB123",
            total_count=10,
            processed_count=10,
            error_count=2,
            individual_errors=individual_errors,
            hotel_id="HOTEL1",
            details={"endpoint": "/api/reservations/bulk"}
        )
        assert error.job_id == "JOB123"
        assert error.total_count == 10
        assert error.processed_count == 10
        assert error.error_count == 2
        assert error.individual_errors == individual_errors
        assert error.hotel_id == "HOTEL1"

    def test_get_success_rate_full_success(self):
        """Test get_success_rate with 100% success."""
        error = BulkOperationError(
            "Bulk operation",
            total_count=10,
            processed_count=10,
            error_count=0
        )
        assert error.get_success_rate() == 1.0

    def test_get_success_rate_partial_success(self):
        """Test get_success_rate with partial success."""
        error = BulkOperationError(
            "Bulk operation",
            total_count=10,
            processed_count=10,
            error_count=3
        )
        assert error.get_success_rate() == 0.7

    def test_get_success_rate_no_success(self):
        """Test get_success_rate with 0% success."""
        error = BulkOperationError(
            "Bulk operation",
            total_count=10,
            processed_count=10,
            error_count=10
        )
        assert error.get_success_rate() == 0.0

    def test_get_success_rate_zero_total(self):
        """Test get_success_rate with zero total count."""
        error = BulkOperationError("Bulk operation")
        assert error.get_success_rate() == 0.0

    def test_has_partial_success_true(self):
        """Test has_partial_success returns True when partial."""
        error = BulkOperationError(
            "Bulk operation",
            processed_count=10,
            error_count=3
        )
        assert error.has_partial_success() is True

    def test_has_partial_success_false_all_success(self):
        """Test has_partial_success returns False when all success."""
        error = BulkOperationError(
            "Bulk operation",
            processed_count=10,
            error_count=0
        )
        assert error.has_partial_success() is False

    def test_has_partial_success_false_all_failure(self):
        """Test has_partial_success returns False when all failure."""
        error = BulkOperationError(
            "Bulk operation",
            processed_count=0,
            error_count=10
        )
        assert error.has_partial_success() is False
