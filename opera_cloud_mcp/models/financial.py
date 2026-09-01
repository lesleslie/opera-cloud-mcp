"""
Financial data models for OPERA Cloud MCP server.

Provides Pydantic models for billing, payments,
and financial transaction entities.
"""

from datetime import datetime

from pydantic import Field

from opera_cloud_mcp.models.common import Money, OperaBaseModel


class Charge(OperaBaseModel):
    """Charge/billing item model."""

    charge_id: str | None = Field(None, alias="chargeId")
    folio_number: str = Field(alias="folioNumber")
    transaction_code: str = Field(alias="transactionCode")
    description: str
    amount: Money
    post_date: datetime = Field(alias="postDate")
    posted_by: str = Field(alias="postedBy")


class Payment(OperaBaseModel):
    """Payment model."""

    payment_id: str | None = Field(None, alias="paymentId")
    folio_number: str = Field(alias="folioNumber")
    payment_method: str = Field(alias="paymentMethod")
    amount: Money
    payment_date: datetime = Field(alias="paymentDate")
    reference_number: str | None = Field(None, alias="referenceNumber")
    processed_by: str = Field(alias="processedBy")


class Folio(OperaBaseModel):
    """Guest folio model."""

    folio_number: str = Field(alias="folioNumber")
    confirmation_number: str = Field(alias="confirmationNumber")
    guest_name: str = Field(alias="guestName")
    charges: list[Charge] = []
    payments: list[Payment] = []
    balance: Money
    status: str = "OPEN"
