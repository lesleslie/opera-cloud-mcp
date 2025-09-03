"""
Financial and billing tools for OPERA Cloud MCP.

Provides MCP tools for managing guest folios, payments, charges,
and financial transactions through the OPERA Cloud Cashiering API.
"""

from decimal import Decimal
from typing import Any

from fastmcp import FastMCP

from opera_cloud_mcp.utils.client_factory import (
    create_cashier_client,
    create_front_office_client,
)
from opera_cloud_mcp.utils.exceptions import ValidationError


def register_financial_tools(app: FastMCP):
    """Register all financial and billing MCP tools."""

    @app.tool()
    async def get_guest_folio(
        confirmation_number: str,
        hotel_id: str | None = None,
        folio_type: str = "master",
        include_details: bool = True,
    ) -> dict[str, Any]:
        """
        Retrieve guest folio with all charges and payments.

        Args:
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier (uses default if not provided)
            folio_type: Type of folio (master, individual, group)
            include_details: Include detailed line items

        Returns:
            Dictionary containing detailed folio information
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        valid_folio_types = ["master", "individual", "group"]
        if folio_type not in valid_folio_types:
            raise ValidationError(
                f"Invalid folio_type. Must be one of: {', '.join(valid_folio_types)}"
            )

        client = create_front_office_client(hotel_id=hotel_id)

        response = await client.get_guest_folio(
            confirmation_number=confirmation_number, folio_type=folio_type
        )

        if response.success:
            return {
                "success": True,
                "folio": response.data,
                "confirmation_number": confirmation_number,
                "folio_type": folio_type,
                "current_balance": response.data.get("currentBalance"),
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def post_charge_to_room(
        confirmation_number: str,
        amount: float,
        description: str,
        department_code: str,
        hotel_id: str | None = None,
        tax_amount: float | None = None,
        reference_number: str | None = None,
        posting_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Post a charge to a guest's room folio.

        Args:
            confirmation_number: Reservation confirmation number
            amount: Charge amount (must be positive)
            description: Charge description
            department_code: Department code (room, restaurant, spa, etc.)
            hotel_id: Hotel identifier (uses default if not provided)
            tax_amount: Tax amount if applicable
            reference_number: Reference number for the charge
            posting_date: Posting date in YYYY-MM-DD format (defaults to today)

        Returns:
            Dictionary containing charge posting confirmation
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if amount <= 0:
            raise ValidationError("amount must be positive")

        # Convert to Decimal for precision
        amount_decimal = Decimal(str(amount))
        if tax_amount is not None:
            tax_amount_decimal = Decimal(str(tax_amount))
        else:
            tax_amount_decimal = None

        client = create_front_office_client(hotel_id=hotel_id)

        charge_data = {
            "amount": float(amount_decimal),
            "description": description,
            "departmentCode": department_code,
            "taxAmount": float(tax_amount_decimal) if tax_amount_decimal else None,
            "referenceNumber": reference_number,
            "postingDate": posting_date,
            "postedBy": "mcp_agent",
        }

        response = await client.post_charge_to_room(confirmation_number, charge_data)

        if response.success:
            return {
                "success": True,
                "charge_details": response.data,
                "confirmation_number": confirmation_number,
                "amount": float(amount_decimal),
                "description": description,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def process_payment(
        confirmation_number: str,
        amount: float,
        payment_method: str,
        hotel_id: str | None = None,
        reference_number: str | None = None,
        notes: str | None = None,
        apply_to_balance: bool = True,
    ) -> dict[str, Any]:
        """
        Process a payment against a guest's folio.

        Args:
            confirmation_number: Reservation confirmation number
            amount: Payment amount (must be positive)
            payment_method: Payment method (cash, credit_card, check, comp)
            hotel_id: Hotel identifier (uses default if not provided)
            reference_number: Payment reference number
            notes: Payment notes or comments
            apply_to_balance: Whether to apply payment to outstanding balance

        Returns:
            Dictionary containing payment processing confirmation
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if amount <= 0:
            raise ValidationError("amount must be positive")

        valid_payment_methods = [
            "cash",
            "credit_card",
            "debit_card",
            "check",
            "comp",
            "transfer",
        ]
        if payment_method not in valid_payment_methods:
            raise ValidationError(
                f"Invalid payment_method. Must be one of: {', '.join(valid_payment_methods)}"
            )

        # Convert to Decimal for precision
        amount_decimal = Decimal(str(amount))

        client = create_cashier_client(hotel_id=hotel_id)

        payment_data = {
            "amount": float(amount_decimal),
            "paymentMethod": payment_method,
            "referenceNumber": reference_number,
            "notes": notes,
            "applyToBalance": apply_to_balance,
            "processedBy": "mcp_agent",
        }

        response = await client.process_payment(confirmation_number, payment_data)

        if response.success:
            return {
                "success": True,
                "payment_details": response.data,
                "confirmation_number": confirmation_number,
                "amount": float(amount_decimal),
                "payment_method": payment_method,
                "remaining_balance": response.data.get("remainingBalance"),
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def generate_folio_report(
        confirmation_number: str,
        hotel_id: str | None = None,
        format_type: str = "detailed",
        include_zero_amounts: bool = False,
    ) -> dict[str, Any]:
        """
        Generate a formatted folio report for printing or email.

        Args:
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier (uses default if not provided)
            format_type: Report format (detailed, summary, itemized)
            include_zero_amounts: Include zero amount line items

        Returns:
            Dictionary containing formatted folio report
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        valid_formats = ["detailed", "summary", "itemized"]
        if format_type not in valid_formats:
            raise ValidationError(
                f"Invalid format_type. Must be one of: {', '.join(valid_formats)}"
            )

        client = create_cashier_client(hotel_id=hotel_id)

        report_params = {
            "format": format_type,
            "includeZeroAmounts": include_zero_amounts,
        }

        response = await client.generate_folio_report(
            confirmation_number, report_params
        )

        if response.success:
            return {
                "success": True,
                "folio_report": response.data,
                "confirmation_number": confirmation_number,
                "format_type": format_type,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def transfer_charges(
        from_confirmation: str,
        to_confirmation: str,
        charges: list[dict[str, Any]],
        hotel_id: str | None = None,
        transfer_reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Transfer charges between guest folios.

        Args:
            from_confirmation: Source reservation confirmation number
            to_confirmation: Destination reservation confirmation number
            charges: List of charge items to transfer with amounts and descriptions
            hotel_id: Hotel identifier (uses default if not provided)
            transfer_reason: Reason for the transfer

        Example charges format:
            [
                {"charge_id": "12345", "amount": 150.00, "description": "Room charge"},
                {"charge_id": "12346", "amount": 25.50, "description": "Restaurant"}
            ]

        Returns:
            Dictionary containing transfer confirmation
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if not charges:
            raise ValidationError("At least one charge must be provided for transfer")

        # Validate charge format
        for charge in charges:
            if not all(key in charge for key in ["charge_id", "amount", "description"]):
                raise ValidationError(
                    "Each charge must have 'charge_id', 'amount', and 'description' fields"
                )
            if charge["amount"] <= 0:
                raise ValidationError("Charge amounts must be positive")

        client = create_cashier_client(hotel_id=hotel_id)

        transfer_data = {
            "fromConfirmation": from_confirmation,
            "toConfirmation": to_confirmation,
            "charges": charges,
            "transferReason": transfer_reason,
            "transferredBy": "mcp_agent",
        }

        response = await client.transfer_charges(transfer_data)

        if response.success:
            return {
                "success": True,
                "transfer_details": response.data,
                "from_confirmation": from_confirmation,
                "to_confirmation": to_confirmation,
                "total_transferred": sum(charge["amount"] for charge in charges),
                "charges_count": len(charges),
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "from_confirmation": from_confirmation,
                "to_confirmation": to_confirmation,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def void_transaction(
        confirmation_number: str,
        transaction_id: str,
        void_reason: str,
        hotel_id: str | None = None,
        manager_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Void a financial transaction on a guest folio.

        Args:
            confirmation_number: Reservation confirmation number
            transaction_id: Transaction ID to void
            void_reason: Reason for voiding the transaction
            hotel_id: Hotel identifier (uses default if not provided)
            manager_override: Manager authorization code if required

        Returns:
            Dictionary containing void transaction confirmation
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_cashier_client(hotel_id=hotel_id)

        void_data = {
            "transactionId": transaction_id,
            "voidReason": void_reason,
            "managerOverride": manager_override,
            "voidedBy": "mcp_agent",
        }

        response = await client.void_transaction(confirmation_number, void_data)

        if response.success:
            return {
                "success": True,
                "void_details": response.data,
                "confirmation_number": confirmation_number,
                "transaction_id": transaction_id,
                "void_reason": void_reason,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_number": confirmation_number,
                "transaction_id": transaction_id,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def process_refund(
        confirmation_number: str,
        amount: float,
        refund_reason: str,
        refund_method: str = "original_payment",
        hotel_id: str | None = None,
        original_transaction_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a refund for a guest.

        Args:
            confirmation_number: Reservation confirmation number
            amount: Refund amount (must be positive)
            refund_reason: Reason for the refund
            refund_method: Refund method (original_payment, cash, check, credit)
            hotel_id: Hotel identifier (uses default if not provided)
            original_transaction_id: Original transaction being refunded
            notes: Additional notes about the refund

        Returns:
            Dictionary containing refund processing confirmation
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if amount <= 0:
            raise ValidationError("refund amount must be positive")

        valid_refund_methods = [
            "original_payment",
            "cash",
            "check",
            "credit",
            "transfer",
        ]
        if refund_method not in valid_refund_methods:
            raise ValidationError(
                f"Invalid refund_method. Must be one of: {', '.join(valid_refund_methods)}"
            )

        # Convert to Decimal for precision
        amount_decimal = Decimal(str(amount))

        client = create_cashier_client(hotel_id=hotel_id)

        refund_data = {
            "amount": float(amount_decimal),
            "refundReason": refund_reason,
            "refundMethod": refund_method,
            "originalTransactionId": original_transaction_id,
            "notes": notes,
            "processedBy": "mcp_agent",
        }

        response = await client.process_refund(confirmation_number, refund_data)

        if response.success:
            return {
                "success": True,
                "refund_details": response.data,
                "confirmation_number": confirmation_number,
                "amount": float(amount_decimal),
                "refund_reason": refund_reason,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_daily_revenue_report(
        report_date: str | None = None,
        hotel_id: str | None = None,
        include_departments: bool = True,
        include_payment_methods: bool = True,
    ) -> dict[str, Any]:
        """
        Get daily revenue report with departmental breakdown.

        Args:
            report_date: Date for report in YYYY-MM-DD format (defaults to today)
            hotel_id: Hotel identifier (uses default if not provided)
            include_departments: Include revenue by department
            include_payment_methods: Include breakdown by payment methods

        Returns:
            Dictionary containing daily revenue statistics
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        from datetime import date as date_module

        if not report_date:
            report_date = date_module.today().isoformat()

        client = create_cashier_client(hotel_id=hotel_id)

        report_params = {
            "date": report_date,
            "includeDepartments": include_departments,
            "includePaymentMethods": include_payment_methods,
        }

        response = await client.get_daily_revenue_report(report_params)

        if response.success:
            return {
                "success": True,
                "revenue_report": response.data,
                "report_date": report_date,
                "total_revenue": response.data.get("totalRevenue"),
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "report_date": report_date,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_outstanding_balances(
        hotel_id: str | None = None,
        balance_threshold: float = 0.01,
        include_departed: bool = True,
        days_back: int = 7,
    ) -> dict[str, Any]:
        """
        Get list of guest folios with outstanding balances.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            balance_threshold: Minimum balance amount to include
            include_departed: Include departed guests with balances
            days_back: How many days back to check for departed guests

        Returns:
            Dictionary containing outstanding balance information
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if balance_threshold < 0:
            raise ValidationError("balance_threshold cannot be negative")

        client = create_cashier_client(hotel_id=hotel_id)

        balance_params = {
            "balanceThreshold": balance_threshold,
            "includeDeparted": include_departed,
            "daysBack": days_back,
        }

        response = await client.get_outstanding_balances(balance_params)

        if response.success:
            return {
                "success": True,
                "outstanding_balances": response.data.get("balances", []),
                "total_outstanding": response.data.get("totalOutstanding"),
                "count": response.data.get("count", 0),
                "balance_threshold": balance_threshold,
                "hotel_id": hotel_id,
            }
        else:
            return {"success": False, "error": response.error, "hotel_id": hotel_id}
