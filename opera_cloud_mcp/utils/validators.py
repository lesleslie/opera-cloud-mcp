"""
Input validation utilities for OPERA Cloud MCP server.

Provides common validation functions for API inputs, dates,
and data formats used throughout the application.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from opera_cloud_mcp.utils.exceptions import ValidationError


def validate_date_string(date_str: str) -> date:
    """
    Validate and parse date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate

    Returns:
        Parsed date object

    Raises:
        ValidationError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValidationError(f"Invalid date format '{date_str}': {e}") from e


def validate_date_format(date_str: str) -> None:
    """
    Validate date format without returning parsed date.

    Args:
        date_str: Date string to validate

    Raises:
        ValidationError: If date format is invalid
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValidationError(
            f"Invalid date format '{date_str}': Expected YYYY-MM-DD format"
        ) from e


def validate_hotel_id(hotel_id: str) -> str:
    """
    Validate hotel ID format.

    Args:
        hotel_id: Hotel ID to validate

    Returns:
        Validated hotel ID

    Raises:
        ValidationError: If hotel ID format is invalid
    """
    if not hotel_id:
        raise ValidationError("Hotel ID cannot be empty")

    if not hotel_id.isalnum():
        raise ValidationError(f"Hotel ID '{hotel_id}' must be alphanumeric")

    if len(hotel_id) > 20:
        raise ValidationError(f"Hotel ID '{hotel_id}' cannot exceed 20 characters")

    return hotel_id.upper()


def validate_confirmation_number(confirmation_number: str) -> str:
    """
    Validate reservation confirmation number format.

    Args:
        confirmation_number: Confirmation number to validate

    Returns:
        Validated confirmation number

    Raises:
        ValidationError: If confirmation number format is invalid
    """
    if not confirmation_number:
        raise ValidationError("Confirmation number cannot be empty")

    # Basic alphanumeric validation (can be enhanced based on actual format)
    try:
        confirmation_validator = ConfirmationNumberValidator(
            confirmation_number=confirmation_number
        )
        return confirmation_validator.confirmation_number
    except Exception as e:
        # Catch any validation errors and convert to our custom ValidationError
        raise ValidationError(
            f"Invalid confirmation number format: {confirmation_number}"
        ) from e


def validate_room_number(room_number: str) -> str:
    """
    Validate room number format.

    Args:
        room_number: Room number to validate

    Returns:
        Validated room number

    Raises:
        ValidationError: If room number format is invalid
    """
    if not room_number:
        raise ValidationError("Room number cannot be empty")

    if len(room_number) > 10:
        raise ValidationError(
            f"Room number '{room_number}' cannot exceed 10 characters"
        )

    return room_number.upper()


def validate_email(email: str) -> str:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        Validated email address

    Raises:
        ValidationError: If email format is invalid
    """
    if not email:
        raise ValidationError("Email address cannot be empty")

    try:
        email_validator = EmailValidator(email=email)
        return email_validator.email
    except Exception as e:
        raise ValidationError(f"Invalid email address format '{email}'") from e


def validate_phone(phone: str) -> str:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        Validated phone number

    Raises:
        ValidationError: If phone format is invalid
    """
    if not phone:
        raise ValidationError("Phone number cannot be empty")

    try:
        phone_validator = PhoneValidator(phone=phone)
        return phone_validator.phone
    except Exception as e:
        raise ValidationError(f"Invalid phone number format '{phone}'") from e


def validate_pagination_params(page: int, page_size: int) -> tuple[int, int]:
    """
    Validate pagination parameters.

    Args:
        page: Page number
        page_size: Items per page

    Returns:
        Tuple of validated (page, page_size)

    Raises:
        ValidationError: If pagination parameters are invalid
    """
    if page < 1:
        raise ValidationError("Page number must be 1 or greater")

    if page_size < 1:
        raise ValidationError("Page size must be 1 or greater")

    if page_size > 100:
        raise ValidationError("Page size cannot exceed 100")

    return page, page_size


def validate_required_fields(data: dict[str, Any], required_fields: list[str]) -> None:
    """
    Validate that required fields are present in data.

    Args:
        data: Data dictionary to validate
        required_fields: List of required field names

    Raises:
        ValidationError: If any required fields are missing
    """
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    # Check for empty values
    empty_fields = [
        field
        for field in required_fields
        if not data.get(field) and data.get(field) != 0
    ]

    if empty_fields:
        raise ValidationError(f"Empty required fields: {', '.join(empty_fields)}")


# Pydantic models for validation
class ConfirmationNumberValidator(BaseModel):
    confirmation_number: str = Field(..., pattern=r"^[A-Z0-9]{6,20}$")

    @field_validator("confirmation_number")
    @classmethod
    def validate_and_upper(cls, v: str) -> str:
        return v.upper()


class EmailValidator(BaseModel):
    email: EmailStr


def clean_phone_number(phone: str) -> str:
    """Clean phone number by removing non-digit characters except +"""
    return "".join(c for c in phone if c.isdigit() or c == "+")


class PhoneValidator(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        cleaned = clean_phone_number(v)
        if len(cleaned) < 7 or len(cleaned) > 15:
            raise ValueError(f"Invalid phone number length: {len(cleaned)}")
        return cleaned
