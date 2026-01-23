"""Unit tests for utility validators.

Tests for validation functions in opera_cloud_mcp/utils/validators.py
"""

import pytest
from datetime import date

from opera_cloud_mcp.utils.exceptions import ValidationError
from opera_cloud_mcp.utils.validators import (
    validate_date_string,
    validate_date_format,
    validate_hotel_id,
    validate_confirmation_number,
    validate_room_number,
    validate_email,
    validate_phone,
    validate_pagination_params,
    validate_required_fields,
    ConfirmationNumberValidator,
    EmailValidator,
    PhoneValidator,
    clean_phone_number,
)


class TestDateValidation:
    """Test date validation functions."""

    def test_validate_date_string_valid(self):
        """Test valid date string parsing."""
        result = validate_date_string("2024-12-25")
        assert result == date(2024, 12, 25)

    def test_validate_date_string_leap_year(self):
        """Test leap year date validation."""
        result = validate_date_string("2024-02-29")
        assert result == date(2024, 2, 29)

    def test_validate_date_string_invalid_format(self):
        """Test invalid date format raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date_string("12/25/2024")

    def test_validate_date_string_invalid_date(self):
        """Test invalid date raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date_string("2024-02-30")

    def test_validate_date_string_empty(self):
        """Test empty date string raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_date_string("")

    def test_validate_date_format_valid(self):
        """Test valid date format validation."""
        # Should not raise
        validate_date_format("2024-12-25")

    def test_validate_date_format_invalid(self):
        """Test invalid date format raises ValidationError."""
        with pytest.raises(ValidationError, match="Expected YYYY-MM-DD format"):
            validate_date_format("25-12-2024")


class TestHotelIdValidation:
    """Test hotel ID validation."""

    def test_validate_hotel_id_valid(self):
        """Test valid hotel ID."""
        result = validate_hotel_id("HOTEL123")
        assert result == "HOTEL123"

    def test_validate_hotel_id_lowercase_to_uppercase(self):
        """Test hotel ID is converted to uppercase."""
        result = validate_hotel_id("hotel123")
        assert result == "HOTEL123"

    def test_validate_hotel_id_empty(self):
        """Test empty hotel ID raises ValidationError."""
        with pytest.raises(ValidationError, match="Hotel ID cannot be empty"):
            validate_hotel_id("")

    def test_validate_hotel_id_non_alphanumeric(self):
        """Test non-alphanumeric hotel ID raises ValidationError."""
        with pytest.raises(ValidationError, match="must be alphanumeric"):
            validate_hotel_id("HOTEL-123")

    def test_validate_hotel_id_too_long(self):
        """Test hotel ID exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot exceed 20 characters"):
            validate_hotel_id("A" * 21)


class TestConfirmationNumberValidation:
    """Test confirmation number validation."""

    def test_validate_confirmation_number_valid(self):
        """Test valid confirmation number."""
        result = validate_confirmation_number("ABC123")
        assert result == "ABC123"

    def test_validate_confirmation_number_lowercase(self):
        """Test confirmation number must be uppercase."""
        # The pattern validation requires uppercase, so lowercase will fail
        with pytest.raises(ValidationError, match="Invalid confirmation number"):
            validate_confirmation_number("abc123")

    def test_validate_confirmation_number_empty(self):
        """Test empty confirmation number raises ValidationError."""
        with pytest.raises(ValidationError, match="Confirmation number cannot be empty"):
            validate_confirmation_number("")

    def test_validate_confirmation_number_too_short(self):
        """Test confirmation number too short raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid confirmation number"):
            validate_confirmation_number("AB12")

    def test_validate_confirmation_number_too_long(self):
        """Test confirmation number too long raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid confirmation number"):
            validate_confirmation_number("A" * 21)

    def test_validate_confirmation_number_with_special_chars(self):
        """Test confirmation number with special chars raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid confirmation number"):
            validate_confirmation_number("ABC-123")


class TestRoomNumberValidation:
    """Test room number validation."""

    def test_validate_room_number_valid(self):
        """Test valid room number."""
        result = validate_room_number("101")
        assert result == "101"

    def test_validate_room_number_uppercase(self):
        """Test room number is converted to uppercase."""
        result = validate_room_number("101a")
        assert result == "101A"

    def test_validate_room_number_empty(self):
        """Test empty room number raises ValidationError."""
        with pytest.raises(ValidationError, match="Room number cannot be empty"):
            validate_room_number("")

    def test_validate_room_number_too_long(self):
        """Test room number exceeding max length raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot exceed 10 characters"):
            validate_room_number("A" * 11)


class TestEmailValidation:
    """Test email validation."""

    def test_validate_email_valid(self):
        """Test valid email address."""
        result = validate_email("test@example.com")
        assert result == "test@example.com"

    def test_validate_email_empty(self):
        """Test empty email raises ValidationError."""
        with pytest.raises(ValidationError, match="Email address cannot be empty"):
            validate_email("")

    def test_validate_email_invalid_format(self):
        """Test invalid email format raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid email address format"):
            validate_email("not-an-email")


class TestPhoneValidation:
    """Test phone validation."""

    def test_validate_phone_valid(self):
        """Test valid phone number."""
        result = validate_phone("+1-555-123-4567")
        assert result == "+15551234567"

    def test_validate_phone_simple(self):
        """Test simple phone number."""
        result = validate_phone("5551234567")
        assert result == "5551234567"

    def test_validate_phone_empty(self):
        """Test empty phone raises ValidationError."""
        with pytest.raises(ValidationError, match="Phone number cannot be empty"):
            validate_phone("")

    def test_validate_phone_too_short(self):
        """Test phone number too short raises ValidationError."""
        # Phone validation requires at least 7 digits after cleaning
        with pytest.raises(ValidationError):
            validate_phone("123")

    def test_validate_phone_too_long(self):
        """Test phone number too long raises ValidationError."""
        # Phone validation allows max 15 digits after cleaning
        with pytest.raises(ValidationError):
            validate_phone("1" * 20)

    def test_clean_phone_number(self):
        """Test phone number cleaning."""
        result = clean_phone_number("+1 (555) 123-4567")
        assert result == "+15551234567"


class TestPaginationValidation:
    """Test pagination parameter validation."""

    def test_validate_pagination_params_valid(self):
        """Test valid pagination parameters."""
        result = validate_pagination_params(page=1, page_size=10)
        assert result == (1, 10)

    def test_validate_pagination_params_max_page_size(self):
        """Test maximum allowed page size."""
        result = validate_pagination_params(page=1, page_size=100)
        assert result == (1, 100)

    def test_validate_pagination_params_invalid_page(self):
        """Test invalid page number raises ValidationError."""
        with pytest.raises(ValidationError, match="Page number must be 1 or greater"):
            validate_pagination_params(page=0, page_size=10)

    def test_validate_pagination_params_invalid_page_size(self):
        """Test invalid page size raises ValidationError."""
        with pytest.raises(ValidationError, match="Page size must be 1 or greater"):
            validate_pagination_params(page=1, page_size=0)

    def test_validate_pagination_params_page_size_too_large(self):
        """Test page size exceeds maximum raises ValidationError."""
        with pytest.raises(ValidationError, match="Page size cannot exceed 100"):
            validate_pagination_params(page=1, page_size=101)


class TestRequiredFieldsValidation:
    """Test required fields validation."""

    def test_validate_required_fields_all_present(self):
        """Test all required fields present."""
        data = {"field1": "value1", "field2": "value2"}
        # Should not raise
        validate_required_fields(data, ["field1", "field2"])

    def test_validate_required_fields_missing(self):
        """Test missing required fields raises ValidationError."""
        data = {"field1": "value1"}
        with pytest.raises(ValidationError, match="Missing required fields: field2"):
            validate_required_fields(data, ["field1", "field2"])

    def test_validate_required_fields_empty_string(self):
        """Test empty required field raises ValidationError."""
        data = {"field1": "value1", "field2": ""}
        with pytest.raises(ValidationError, match="Empty required fields: field2"):
            validate_required_fields(data, ["field1", "field2"])

    def test_validate_required_fields_zero_allowed(self):
        """Test zero value is allowed for required fields."""
        data = {"field1": 0, "field2": "value2"}
        # Should not raise
        validate_required_fields(data, ["field1", "field2"])

    def test_validate_required_fields_none_not_allowed(self):
        """Test None value raises ValidationError."""
        data = {"field1": None, "field2": "value2"}
        with pytest.raises(ValidationError, match="Empty required fields: field1"):
            validate_required_fields(data, ["field1", "field2"])


class TestPydanticValidators:
    """Test Pydantic validator models."""

    def test_confirmation_number_validator_valid(self):
        """Test ConfirmationNumberValidator with valid input."""
        validator = ConfirmationNumberValidator(confirmation_number="ABC123")
        assert validator.confirmation_number == "ABC123"

    def test_confirmation_number_validator_uppercase(self):
        """Test ConfirmationNumberValidator requires uppercase."""
        # Pattern validation requires uppercase, lowercase will raise validation error
        with pytest.raises(Exception):
            ConfirmationNumberValidator(confirmation_number="abc123")

    def test_confirmation_number_validator_invalid_pattern(self):
        """Test ConfirmationNumberValidator rejects invalid pattern."""
        with pytest.raises(Exception):
            ConfirmationNumberValidator(confirmation_number="AB12")

    def test_email_validator_valid(self):
        """Test EmailValidator with valid email."""
        validator = EmailValidator(email="test@example.com")
        assert validator.email == "test@example.com"

    def test_email_validator_invalid(self):
        """Test EmailValidator rejects invalid email."""
        with pytest.raises(Exception):
            EmailValidator(email="not-an-email")

    def test_phone_validator_valid(self):
        """Test PhoneValidator with valid phone."""
        validator = PhoneValidator(phone="+1-555-123-4567")
        assert validator.phone == "+15551234567"

    def test_phone_validator_too_short(self):
        """Test PhoneValidator rejects too short phone."""
        with pytest.raises(Exception, match="Invalid phone number length"):
            PhoneValidator(phone="123")

    def test_phone_validator_too_long(self):
        """Test PhoneValidator rejects too long phone."""
        with pytest.raises(Exception, match="Invalid phone number length"):
            PhoneValidator(phone="1" * 16)
