"""
Cashiering API client for OPERA Cloud.

Handles financial operations including payments, billing, refunds,
and folio management through the OPERA Cloud CSH API.
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, validator

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.models.common import OperaBaseModel


class ChargeRequest(OperaBaseModel):
    """Charge posting request model."""

    confirmation_number: str = Field(alias="confirmationNumber")
    amount: Decimal = Field(ge=0)
    description: str
    transaction_code: str = Field(alias="transactionCode")
    department_code: str = Field(alias="departmentCode")
    posting_date: date | None = Field(None, alias="postingDate")
    folio_type: str = Field("master", alias="folioType")  # "master", "individual"
    reference_number: str | None = Field(None, alias="referenceNumber")
    tax_exempt: bool = Field(False, alias="taxExempt")
    package_item: bool = Field(False, alias="packageItem")
    auto_settle: bool = Field(False, alias="autoSettle")


class PaymentRequest(OperaBaseModel):
    """Payment processing request model."""

    confirmation_number: str = Field(alias="confirmationNumber")
    amount: Decimal = Field(ge=0)
    payment_method: str = Field(
        alias="paymentMethod"
    )  # "CASH", "CREDIT", "DEBIT", "CHECK"
    currency: str = "USD"
    folio_type: str = Field("master", alias="folioType")

    # Credit Card Fields
    card_number: str | None = Field(None, alias="cardNumber")
    card_holder_name: str | None = Field(None, alias="cardHolderName")
    expiry_month: int | None = Field(None, alias="expiryMonth", ge=1, le=12)
    expiry_year: int | None = Field(None, alias="expiryYear", ge=2024)
    cvv: str | None = None

    # Check Fields
    check_number: str | None = Field(None, alias="checkNumber")
    bank_name: str | None = Field(None, alias="bankName")
    routing_number: str | None = Field(None, alias="routingNumber")

    # Additional Fields
    authorization_code: str | None = Field(None, alias="authorizationCode")
    reference_number: str | None = Field(None, alias="referenceNumber")
    comments: str | None = None

    @validator("card_number")
    def validate_card_number(self, v, values):
        if values.get("payment_method") in ("CREDIT", "DEBIT") and not v:
            raise ValueError("Card number required for credit/debit payments")
        return v


class RefundRequest(OperaBaseModel):
    """Refund processing request model."""

    confirmation_number: str = Field(alias="confirmationNumber")
    original_payment_id: str = Field(alias="originalPaymentId")
    refund_amount: Decimal = Field(alias="refundAmount", ge=0)
    refund_reason: str = Field(alias="refundReason")
    refund_method: str = Field(alias="refundMethod")  # "ORIGINAL", "CASH", "CHECK"
    partial_refund: bool = Field(False, alias="partialRefund")
    manager_approval: str | None = Field(None, alias="managerApproval")
    comments: str | None = None


class FolioTransfer(OperaBaseModel):
    """Folio transfer request model."""

    confirmation_number: str = Field(alias="confirmationNumber")
    from_folio: str = Field(alias="fromFolio")  # "master", "individual_1", etc.
    to_folio: str = Field(alias="toFolio")
    transfer_amount: Decimal | None = Field(None, alias="transferAmount", ge=0)
    charge_ids: list[str] | None = Field(None, alias="chargeIds")
    transfer_type: str = Field(
        "partial", alias="transferType"
    )  # "all", "partial", "specific"
    reason_code: str = Field(alias="reasonCode")
    comments: str | None = None


class CreditCardAuthorization(OperaBaseModel):
    """Credit card authorization model."""

    card_number: str = Field(alias="cardNumber")
    card_holder_name: str = Field(alias="cardHolderName")
    expiry_month: int = Field(alias="expiryMonth", ge=1, le=12)
    expiry_year: int = Field(alias="expiryYear", ge=2024)
    cvv: str
    authorization_amount: Decimal = Field(alias="authorizationAmount", ge=0)
    authorization_type: str = Field(
        "hold", alias="authorizationType"
    )  # "hold", "charge"
    merchant_id: str | None = Field(None, alias="merchantId")
    terminal_id: str | None = Field(None, alias="terminalId")


class PaymentSummary(OperaBaseModel):
    """Payment summary model."""

    confirmation_number: str = Field(alias="confirmationNumber")
    total_charges: Decimal = Field(alias="totalCharges")
    total_payments: Decimal = Field(alias="totalPayments")
    outstanding_balance: Decimal = Field(alias="outstandingBalance")
    payment_methods: list[str] = Field(default_factory=list, alias="paymentMethods")
    last_payment_date: datetime | None = Field(None, alias="lastPaymentDate")


class CashieringClient(BaseAPIClient):
    """
    Client for OPERA Cloud Cashiering API.

    Provides comprehensive financial operations including charge posting,
    payment processing, refunds, and folio management.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_domain = "csh"

    # Charge Management

    async def post_charge(
        self, charge_data: ChargeRequest | dict[str, Any]
    ) -> APIResponse:
        """
        Post a charge to a guest's folio.

        Args:
            charge_data: Charge details including amount and description

        Returns:
            APIResponse with charge posting confirmation
        """
        if isinstance(charge_data, dict):
            charge_data = ChargeRequest.model_validate(charge_data)

        endpoint = f"{self.api_domain}/v1/charges"

        payload = {
            "confirmationNumber": charge_data.confirmation_number,
            "amount": str(charge_data.amount),
            "description": charge_data.description,
            "transactionCode": charge_data.transaction_code,
            "departmentCode": charge_data.department_code,
            "postingDate": charge_data.posting_date.isoformat()
            if charge_data.posting_date
            else None,
            "folioType": charge_data.folio_type,
            "referenceNumber": charge_data.reference_number,
            "taxExempt": charge_data.tax_exempt,
            "packageItem": charge_data.package_item,
            "autoSettle": charge_data.auto_settle,
        }

        return await self.post(endpoint, json_data=payload)

    async def reverse_charge(
        self, charge_id: str, reason_code: str, comments: str | None = None
    ) -> APIResponse:
        """
        Reverse a previously posted charge.

        Args:
            charge_id: ID of the charge to reverse
            reason_code: Reason for charge reversal
            comments: Optional comments for the reversal

        Returns:
            APIResponse with reversal confirmation
        """
        endpoint = f"{self.api_domain}/v1/charges/{charge_id}/reverse"

        payload = {
            "reasonCode": reason_code,
            "comments": comments,
            "reversalDate": datetime.now().isoformat(),
        }

        return await self.post(endpoint, json_data=payload)

    async def get_charge_history(
        self,
        confirmation_number: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> APIResponse:
        """
        Get charge history for a reservation.

        Args:
            confirmation_number: Reservation confirmation number
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            APIResponse with charge history details
        """
        endpoint = f"{self.api_domain}/v1/reservations/{confirmation_number}/charges"

        params = {}
        if start_date:
            params["startDate"] = start_date.isoformat()
        if end_date:
            params["endDate"] = end_date.isoformat()

        return await self.get(endpoint, params=params)

    # Payment Processing

    async def process_payment(
        self, payment_data: PaymentRequest | dict[str, Any]
    ) -> APIResponse:
        """
        Process a payment for a reservation.

        Args:
            payment_data: Payment details including method and amount

        Returns:
            APIResponse with payment processing results
        """
        if isinstance(payment_data, dict):
            payment_data = PaymentRequest.model_validate(payment_data)

        endpoint = f"{self.api_domain}/v1/payments"

        payload = {
            "confirmationNumber": payment_data.confirmation_number,
            "amount": str(payment_data.amount),
            "paymentMethod": payment_data.payment_method,
            "currency": payment_data.currency,
            "folioType": payment_data.folio_type,
            "authorizationCode": payment_data.authorization_code,
            "referenceNumber": payment_data.reference_number,
            "comments": payment_data.comments,
        }

        # Add payment method specific fields
        if payment_data.payment_method in ("CREDIT", "DEBIT"):
            payload.update(
                {
                    "cardNumber": payment_data.card_number,
                    "cardHolderName": payment_data.card_holder_name,
                    "expiryMonth": str(payment_data.expiry_month)
                    if payment_data.expiry_month
                    else None,
                    "expiryYear": str(payment_data.expiry_year)
                    if payment_data.expiry_year
                    else None,
                    "cvv": payment_data.cvv,
                }
            )
        elif payment_data.payment_method == "CHECK":
            payload.update(
                {
                    "checkNumber": payment_data.check_number,
                    "bankName": payment_data.bank_name,
                    "routingNumber": payment_data.routing_number,
                }
            )

        return await self.post(endpoint, json_data=payload)

    async def authorize_credit_card(
        self, auth_data: CreditCardAuthorization | dict[str, Any]
    ) -> APIResponse:
        """
        Authorize a credit card for payment.

        Args:
            auth_data: Credit card authorization details

        Returns:
            APIResponse with authorization results
        """
        if isinstance(auth_data, dict):
            auth_data = CreditCardAuthorization.model_validate(auth_data)

        endpoint = f"{self.api_domain}/v1/credit-cards/authorize"

        payload = {
            "cardNumber": auth_data.card_number,
            "cardHolderName": auth_data.card_holder_name,
            "expiryMonth": auth_data.expiry_month,
            "expiryYear": auth_data.expiry_year,
            "cvv": auth_data.cvv,
            "authorizationAmount": str(auth_data.authorization_amount),
            "authorizationType": auth_data.authorization_type,
            "merchantId": auth_data.merchant_id,
            "terminalId": auth_data.terminal_id,
        }

        return await self.post(endpoint, json_data=payload)

    async def capture_authorization(
        self, authorization_id: str, capture_amount: Decimal | None = None
    ) -> APIResponse:
        """
        Capture a previously authorized credit card transaction.

        Args:
            authorization_id: Authorization ID to capture
            capture_amount: Amount to capture (defaults to full authorization)

        Returns:
            APIResponse with capture confirmation
        """
        endpoint = (
            f"{self.api_domain}/v1/credit-cards/authorizations/"
            + f"{authorization_id}/capture"
        )

        payload = {}
        if capture_amount:
            payload["captureAmount"] = str(capture_amount)

        return await self.post(endpoint, json_data=payload)

    async def void_authorization(
        self, authorization_id: str, reason: str | None = None
    ) -> APIResponse:
        """
        Void a credit card authorization.

        Args:
            authorization_id: Authorization ID to void
            reason: Reason for voiding

        Returns:
            APIResponse with void confirmation
        """
        endpoint = (
            f"{self.api_domain}/v1/credit-cards/authorizations/{authorization_id}/void"
        )

        payload = {"reason": reason or "Void by request"}

        return await self.post(endpoint, json_data=payload)

    # Refund Processing

    async def process_refund(
        self, refund_data: RefundRequest | dict[str, Any]
    ) -> APIResponse:
        """
        Process a refund for a previous payment.

        Args:
            refund_data: Refund details including amount and reason

        Returns:
            APIResponse with refund processing results
        """
        if isinstance(refund_data, dict):
            refund_data = RefundRequest.model_validate(refund_data)

        endpoint = f"{self.api_domain}/v1/refunds"

        payload = {
            "confirmationNumber": refund_data.confirmation_number,
            "originalPaymentId": refund_data.original_payment_id,
            "refundAmount": str(refund_data.refund_amount),
            "refundReason": refund_data.refund_reason,
            "refundMethod": refund_data.refund_method,
            "partialRefund": refund_data.partial_refund,
            "managerApproval": refund_data.manager_approval,
            "comments": refund_data.comments,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_refund_status(self, refund_id: str) -> APIResponse:
        """
        Get the status of a refund transaction.

        Args:
            refund_id: Refund transaction ID

        Returns:
            APIResponse with refund status details
        """
        endpoint = f"{self.api_domain}/v1/refunds/{refund_id}"

        return await self.get(endpoint)

    # Folio Management

    async def get_folio(
        self, confirmation_number: str, folio_type: str = "master"
    ) -> APIResponse:
        """
        Retrieve a guest folio with all charges and payments.

        Args:
            confirmation_number: Reservation confirmation number
            folio_type: Type of folio to retrieve

        Returns:
            APIResponse with detailed folio information
        """
        endpoint = f"{self.api_domain}/v1/reservations/{confirmation_number}/folio"

        params = {"type": folio_type}

        return await self.get(endpoint, params=params)

    async def split_folio(
        self, confirmation_number: str, split_criteria: dict[str, Any]
    ) -> APIResponse:
        """
        Split a folio into multiple folios.

        Args:
            confirmation_number: Reservation confirmation number
            split_criteria: Criteria for splitting the folio

        Returns:
            APIResponse with split folio details
        """
        endpoint = (
            f"{self.api_domain}/v1/reservations/{confirmation_number}/folio/split"
        )

        return await self.post(endpoint, json_data=split_criteria)

    async def transfer_charges(
        self, transfer_data: FolioTransfer | dict[str, Any]
    ) -> APIResponse:
        """
        Transfer charges between folios.

        Args:
            transfer_data: Transfer details and criteria

        Returns:
            APIResponse with transfer confirmation
        """
        if isinstance(transfer_data, dict):
            transfer_data = FolioTransfer.model_validate(transfer_data)

        endpoint = f"{self.api_domain}/v1/folio-transfers"

        payload = {
            "confirmationNumber": transfer_data.confirmation_number,
            "fromFolio": transfer_data.from_folio,
            "toFolio": transfer_data.to_folio,
            "transferAmount": str(transfer_data.transfer_amount)
            if transfer_data.transfer_amount
            else None,
            "chargeIds": transfer_data.charge_ids,
            "transferType": transfer_data.transfer_type,
            "reasonCode": transfer_data.reason_code,
            "comments": transfer_data.comments,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_payment_summary(self, confirmation_number: str) -> APIResponse:
        """
        Get payment summary for a reservation.

        Args:
            confirmation_number: Reservation confirmation number

        Returns:
            APIResponse with payment summary
        """
        endpoint = (
            f"{self.api_domain}/v1/reservations/{confirmation_number}/payment-summary"
        )

        return await self.get(endpoint)

    # Settlement Operations

    async def settle_folio(
        self,
        confirmation_number: str,
        settlement_method: str,
        folio_type: str = "master",
    ) -> APIResponse:
        """
        Settle a folio with a specific payment method.

        Args:
            confirmation_number: Reservation confirmation number
            settlement_method: Payment method for settlement
            folio_type: Type of folio to settle

        Returns:
            APIResponse with settlement confirmation
        """
        endpoint = f"{self.api_domain}/v1/reservations/{confirmation_number}/settle"

        payload = {
            "settlementMethod": settlement_method,
            "folioType": folio_type,
            "settlementDate": datetime.now().isoformat(),
        }

        return await self.post(endpoint, json_data=payload)

    async def auto_settle(
        self, confirmation_number: str, payment_method_priority: list[str]
    ) -> APIResponse:
        """
        Automatically settle folio using payment method priority.

        Args:
            confirmation_number: Reservation confirmation number
            payment_method_priority: Ordered list of payment methods to try

        Returns:
            APIResponse with auto-settlement results
        """
        endpoint = (
            f"{self.api_domain}/v1/reservations/{confirmation_number}/auto-settle"
        )

        payload = {"paymentMethodPriority": payment_method_priority}

        return await self.post(endpoint, json_data=payload)

    # Batch Operations

    async def batch_post_charges(self, charges: list[ChargeRequest]) -> APIResponse:
        """
        Post multiple charges in a single operation.

        Args:
            charges: List of charges to post

        Returns:
            APIResponse with batch posting results
        """
        endpoint = f"{self.api_domain}/v1/charges/batch"

        payload = {
            "charges": [
                {
                    "confirmationNumber": c.confirmation_number,
                    "amount": str(c.amount),
                    "description": c.description,
                    "transactionCode": c.transaction_code,
                    "departmentCode": c.department_code,
                    "postingDate": c.posting_date.isoformat()
                    if c.posting_date
                    else None,
                    "folioType": c.folio_type,
                    "referenceNumber": c.reference_number,
                    "taxExempt": c.tax_exempt,
                    "packageItem": c.package_item,
                }
                for c in charges
            ]
        }

        return await self.post(endpoint, json_data=payload)

    async def batch_process_payments(
        self, payments: list[PaymentRequest]
    ) -> APIResponse:
        """
        Process multiple payments in a single operation.

        Args:
            payments: List of payments to process

        Returns:
            APIResponse with batch payment results
        """
        # Process payments concurrently for better performance
        tasks = [self.process_payment(payment_data) for payment_data in payments]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        successful = []
        failed = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append(
                    {
                        "confirmation_number": payments[i].confirmation_number,
                        "error": str(result),
                    }
                )
            elif isinstance(result, APIResponse) and result.success:
                successful.append(result.data)
            elif isinstance(result, APIResponse):
                failed.append(
                    {
                        "confirmation_number": payments[i].confirmation_number,
                        "error": result.error or "Payment processing failed",
                    }
                )

        return APIResponse(
            success=len(failed) == 0,
            data={
                "successful_payments": successful,
                "failed_payments": failed,
                "total_processed": len(payments),
                "success_count": len(successful),
                "failure_count": len(failed),
            },
        )

    # Financial Reports

    async def get_daily_revenue_report(
        self, report_date: date | None = None, department_codes: list[str] | None = None
    ) -> APIResponse:
        """
        Get daily revenue report by department.

        Args:
            report_date: Date for the report (defaults to today)
            department_codes: Optional department filter

        Returns:
            APIResponse with revenue breakdown
        """
        if report_date is None:
            report_date = date.today()

        endpoint = f"{self.api_domain}/v1/reports/daily-revenue"

        params = {"date": report_date.isoformat()}
        if department_codes:
            params["departmentCodes"] = ",".join(department_codes)

        return await self.get(endpoint, params=params)

    async def get_payment_method_report(
        self, start_date: date, end_date: date
    ) -> APIResponse:
        """
        Get payment method analysis report.

        Args:
            start_date: Report start date
            end_date: Report end date

        Returns:
            APIResponse with payment method breakdown
        """
        endpoint = f"{self.api_domain}/v1/reports/payment-methods"

        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }

        return await self.get(endpoint, params=params)

    async def get_outstanding_balances_report(
        self, as_of_date: date | None = None
    ) -> APIResponse:
        """
        Get report of outstanding folio balances.

        Args:
            as_of_date: Date for balance calculation (defaults to today)

        Returns:
            APIResponse with outstanding balance details
        """
        if as_of_date is None:
            as_of_date = date.today()

        endpoint = f"{self.api_domain}/v1/reports/outstanding-balances"

        params = {"asOfDate": as_of_date.isoformat()}

        return await self.get(endpoint, params=params)

    # Convenience Methods

    async def quick_cash_payment(
        self, confirmation_number: str, amount: Decimal, comments: str | None = None
    ) -> APIResponse:
        """
        Quick cash payment processing.

        Args:
            confirmation_number: Reservation confirmation number
            amount: Payment amount
            comments: Optional payment comments

        Returns:
            APIResponse with payment confirmation
        """
        payment_data = PaymentRequest(
            confirmationNumber=confirmation_number,
            amount=amount,
            paymentMethod="CASH",
            currency="USD",
            folioType="master",
            cardNumber=None,
            cardHolderName=None,
            expiryMonth=None,
            expiryYear=None,
            cvv=None,
            checkNumber=None,
            bankName=None,
            routingNumber=None,
            authorizationCode=None,
            referenceNumber=None,
            comments=comments,
        )

        return await self.process_payment(payment_data)

    async def is_folio_settled(self, confirmation_number: str) -> APIResponse:
        """
        Check if a folio is fully settled.

        Args:
            confirmation_number: Reservation confirmation number

        Returns:
            APIResponse with settlement status
        """
        summary_response = await self.get_payment_summary(confirmation_number)

        if not summary_response.success:
            return summary_response

        summary_data = summary_response.data
        is_settled = (
            summary_data.get("outstandingBalance", 0) == 0 if summary_data else False
        )

        return APIResponse(
            success=True,
            data={
                "settled": is_settled,
                "outstanding_balance": summary_data.get("outstandingBalance", 0)
                if summary_data
                else 0,
                "total_charges": summary_data.get("totalCharges", 0)
                if summary_data
                else 0,
                "total_payments": summary_data.get("totalPayments", 0)
                if summary_data
                else 0,
            },
        )

    async def get_payment_options(
        self, confirmation_number: str, amount: Decimal | None = None
    ) -> APIResponse:
        """
        Get available payment options for a reservation.

        Args:
            confirmation_number: Reservation confirmation number
            amount: Optional payment amount for validation

        Returns:
            APIResponse with available payment methods and restrictions
        """
        endpoint = (
            f"{self.api_domain}/v1/reservations/{confirmation_number}/payment-options"
        )

        params = {}
        if amount:
            params["amount"] = str(amount)

        return await self.get(endpoint, params=params)
