"""
Common data models for OPERA Cloud MCP server.

Provides base models and common structures used across
different OPERA Cloud API domains.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperaBaseModel(BaseModel):
    """Base model for all OPERA Cloud entities."""

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields from API responses
        use_enum_values=True,
        validate_assignment=True,
    )


class Address(OperaBaseModel):
    """Address model for guest and hotel information."""

    address_line1: str | None = Field(None, alias="addressLine1")
    address_line2: str | None = Field(None, alias="addressLine2")
    city: str | None = None
    state_province: str | None = Field(None, alias="stateProvince")
    postal_code: str | None = Field(None, alias="postalCode")
    country: str | None = None


class Contact(OperaBaseModel):
    """Contact information model."""

    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    fax: str | None = None


class Money(OperaBaseModel):
    """Money/currency model."""

    amount: float
    currency_code: str = Field("USD", alias="currencyCode")


class APIError(OperaBaseModel):
    """Standard API error response model."""

    error_code: str = Field(alias="errorCode")
    error_message: str = Field(alias="errorMessage")
    error_details: dict[str, Any] | None = Field(None, alias="errorDetails")


class PaginationInfo(OperaBaseModel):
    """Pagination information model."""

    page: int = 1
    page_size: int = Field(10, alias="pageSize")
    total_count: int = Field(alias="totalCount")
    total_pages: int = Field(alias="totalPages")
