"""
Data formatting utilities for OPERA Cloud MCP server.

Provides common formatting functions for dates, currency,
and data transformation used throughout the application.
"""

from datetime import UTC, date, datetime
from typing import Any

from opera_cloud_mcp.models.common import Money


def format_date_for_api(date_obj: date) -> str:
    """
    Format date object for API requests.

    Args:
        date_obj: Date object to format

    Returns:
        Date string in YYYY-MM-DD format
    """
    return date_obj.strftime("%Y-%m-%d")


def format_datetime_for_api(datetime_obj: datetime) -> str:
    """
    Format datetime object for API requests.

    Args:
        datetime_obj: Datetime object to format

    Returns:
        Datetime string in ISO format
    """
    return datetime_obj.isoformat()


def format_money(amount: float, currency_code: str = "USD") -> Money:
    """
    Format money amount into Money model.

    Args:
        amount: Money amount
        currency_code: Currency code (default: USD)

    Returns:
        Money model instance
    """
    return Money(amount=amount, currencyCode=currency_code)


def format_guest_name(
    first_name: str, last_name: str, middle_name: str | None = None
) -> str:
    """
    Format guest name for display.

    Args:
        first_name: Guest first name
        last_name: Guest last name
        middle_name: Optional middle name

    Returns:
        Formatted full name
    """
    if middle_name:
        return f"{first_name} {middle_name} {last_name}"
    return f"{first_name} {last_name}"


def format_phone_display(phone: str) -> str:
    """
    Format phone number for display.

    Args:
        phone: Phone number string

    Returns:
        Formatted phone number
    """
    # Remove all non-digits
    digits = "".join(c for c in phone if c.isdigit())

    # Format US numbers
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    # Return original for international or non-standard formats
    return phone


def format_api_response(
    success: bool,
    data: dict[str, Any] | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Format standardized API response.

    Args:
        success: Whether operation was successful
        data: Response data
        error: Error message if unsuccessful
        metadata: Optional metadata

    Returns:
        Formatted response dictionary
    """
    response = {
        "success": success,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }

    if success:
        response["data"] = data or {}
    else:
        response["error"] = error

    if metadata:
        response["metadata"] = metadata

    return response


def format_search_params(**kwargs: Any) -> dict[str, str]:
    """
    Format search parameters for API requests.

    Args:
        **kwargs: Search parameters

    Returns:
        Formatted parameters dictionary
    """
    params = {}

    for key, value in kwargs.items():
        if value is not None:
            # Convert dates to string format
            if isinstance(value, date):
                params[key] = format_date_for_api(value)
            elif isinstance(value, datetime):
                params[key] = format_datetime_for_api(value)
            else:
                params[key] = str(value)

    return params


def camel_to_snake_case(camel_str: str) -> str:
    """
    Convert camelCase to snake_case.

    Args:
        camel_str: String in camelCase

    Returns:
        String in snake_case
    """
    # Convert camelCase to snake_case without regex
    result = []
    for i, char in enumerate(camel_str):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


def snake_to_camel_case(snake_str: str) -> str:
    """
    Convert snake_case to camelCase.

    Args:
        snake_str: String in snake_case

    Returns:
        String in camelCase
    """
    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


def _clean_dict_value(value: dict[str, Any]) -> dict[str, Any]:
    """Clean a dictionary value recursively."""
    return clean_api_data(value)


def _clean_list_value(value: list[Any]) -> list[Any]:
    """Clean a list value recursively."""
    cleaned_items = []
    for item in value:
        if item is not None and item != "":
            if isinstance(item, dict):
                cleaned_item = clean_api_data(item)
                if cleaned_item:  # Only include non-empty dicts
                    cleaned_items.append(cleaned_item)
            else:
                cleaned_items.append(item)
    return cleaned_items


def _should_include_value(value: Any) -> bool:
    """Check if a value should be included in cleaned data."""
    return value is not None and value != ""


def _process_dict_value(value: dict[str, Any]) -> dict[str, Any] | None:
    """Process a dictionary value."""
    cleaned_value = clean_api_data(value)
    if cleaned_value:
        return cleaned_value
    return None  # Return None if empty


def _process_list_value(value: list[Any]) -> list[Any] | None:
    """Process a list value."""
    cleaned_value = _clean_list_value(value)
    if cleaned_value:
        return cleaned_value
    return None  # Return None if empty


def _process_value(value: Any) -> Any:
    """Process a single value based on its type."""
    if isinstance(value, dict):
        return _process_dict_value(value)
    elif isinstance(value, list):
        return _process_list_value(value)
    return value


def clean_api_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Clean API data by removing None values and empty strings.

    Args:
        data: Data dictionary to clean

    Returns:
        Cleaned data dictionary
    """
    cleaned: dict[str, Any] = {}

    for key, value in data.items():
        if _should_include_value(value):
            processed_value = _process_value(value)
            if processed_value is not None:
                cleaned[key] = processed_value

    return cleaned
