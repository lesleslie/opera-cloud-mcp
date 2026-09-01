"""
Common data models for OPERA Cloud MCP server.

Provides base models and common structures used across
different OPERA Cloud API domains.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from sqlmodel import Field as SQLModelField
from sqlmodel import SQLModel


class OperaBaseModel(BaseModel):
    """Base model for all OPERA Cloud entities."""

    model_config = ConfigDict(
        extra="allow",  # Allow extra fields from API responses
        use_enum_values=True,
        validate_assignment=True,
        populate_by_name=True,  # Allow population by both alias and field name
    )


class OperaSQLModel(SQLModel):
    """Base SQLModel for all OPERA Cloud database entities."""

    pass


class Address(OperaBaseModel):
    """Address model for guest and hotel information."""

    address_line1: str | None = PydanticField(default=None, alias="addressLine1")
    address_line2: str | None = PydanticField(default=None, alias="addressLine2")
    city: str | None = None
    state_province: str | None = PydanticField(default=None, alias="stateProvince")
    postal_code: str | None = PydanticField(default=None, alias="postalCode")
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
    currency_code: str = PydanticField(default="USD", alias="currencyCode")


class APIError(OperaBaseModel):
    """Standard API error response model."""

    error_code: str = PydanticField(alias="errorCode")
    error_message: str = PydanticField(alias="errorMessage")
    error_details: dict[str, Any] | None = PydanticField(
        default=None, alias="errorDetails"
    )


class PaginationInfo(OperaBaseModel):
    """Pagination information model."""

    page: int = 1
    page_size: int = PydanticField(default=10, alias="pageSize")
    total_count: int = PydanticField(alias="totalCount")
    total_pages: int = PydanticField(alias="totalPages")


class AuditRecordDB(OperaSQLModel, table={"extend_existing": True}):
    """SQLModel for audit records stored in database."""

    id: str = SQLModelField(primary_key=True)
    timestamp: datetime
    event_type: str
    client_id_hash: str
    ip_address: str | None = None
    user_agent_hash: str | None = None
    success: bool
    risk_score: int = 0
    session_id: str | None = None
    encrypted_details: bytes | None = None
    checksum: str
    created_at: datetime | None = None
