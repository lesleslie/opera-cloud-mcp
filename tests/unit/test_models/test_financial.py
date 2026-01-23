"""Unit tests for financial models.

Tests for models in opera_cloud_mcp/models/financial.py
"""

from datetime import datetime
import pytest

from opera_cloud_mcp.models.financial import Charge, Payment, Folio
from opera_cloud_mcp.models.common import Money


class TestCharge:
    """Test Charge model."""

    def test_charge_creation(self):
        """Test creating a Charge with all fields."""
        money = Money(amount=100.50, currency="USD")
        charge = Charge(
            charge_id="CHG123",
            folio_number="FOLIO1",
            transaction_code="ROOM",
            description="Room charge",
            amount=money,
            post_date=datetime(2024, 12, 25, 12, 0),
            posted_by="admin"
        )
        assert charge.charge_id == "CHG123"
        assert charge.folio_number == "FOLIO1"
        assert charge.transaction_code == "ROOM"
        assert charge.description == "Room charge"
        assert charge.amount == money
        assert charge.post_date == datetime(2024, 12, 25, 12, 0)
        assert charge.posted_by == "admin"

    def test_charge_creation_with_alias(self):
        """Test creating a Charge using field aliases."""
        money = Money(amount=50.0, currency="USD")
        charge = Charge(
            chargeId="CHG456",
            folioNumber="FOLIO2",
            transactionCode="DINING",
            description="Restaurant charge",
            amount=money,
            postDate=datetime(2024, 12, 25, 18, 30),
            postedBy="server1"
        )
        assert charge.charge_id == "CHG456"
        assert charge.folio_number == "FOLIO2"
        assert charge.transaction_code == "DINING"

    def test_charge_optional_charge_id(self):
        """Test creating a Charge without charge_id."""
        money = Money(amount=75.0, currency="USD")
        charge = Charge(
            folio_number="FOLIO3",
            transaction_code="SERVICE",
            description="Spa service",
            amount=money,
            post_date=datetime(2024, 12, 25, 14, 0),
            posted_by="spa"
        )
        assert charge.charge_id is None


class TestPayment:
    """Test Payment model."""

    def test_payment_creation(self):
        """Test creating a Payment with all fields."""
        money = Money(amount=200.0, currency="USD")
        payment = Payment(
            payment_id="PAY123",
            folio_number="FOLIO1",
            payment_method="CREDIT_CARD",
            amount=money,
            payment_date=datetime(2024, 12, 25, 12, 0),
            reference_number="REF456",
            processed_by="admin"
        )
        assert payment.payment_id == "PAY123"
        assert payment.folio_number == "FOLIO1"
        assert payment.payment_method == "CREDIT_CARD"
        assert payment.amount == money
        assert payment.payment_date == datetime(2024, 12, 25, 12, 0)
        assert payment.reference_number == "REF456"
        assert payment.processed_by == "admin"

    def test_payment_creation_with_alias(self):
        """Test creating a Payment using field aliases."""
        money = Money(amount=150.0, currency="EUR")
        payment = Payment(
            paymentId="PAY456",
            folioNumber="FOLIO2",
            paymentMethod="CASH",
            amount=money,
            paymentDate=datetime(2024, 12, 25, 13, 0),
            referenceNumber="REF789",
            processedBy="cashier"
        )
        assert payment.payment_id == "PAY456"
        assert payment.folio_number == "FOLIO2"
        assert payment.payment_method == "CASH"

    def test_payment_optional_fields(self):
        """Test creating a Payment without optional fields."""
        money = Money(amount=100.0, currency="USD")
        payment = Payment(
            folio_number="FOLIO3",
            payment_method="DEBIT_CARD",
            amount=money,
            payment_date=datetime(2024, 12, 25, 14, 0),
            processed_by="system"
        )
        assert payment.payment_id is None
        assert payment.reference_number is None


class TestFolio:
    """Test Folio model."""

    def test_folio_creation(self):
        """Test creating a Folio with all fields."""
        money = Money(amount=50.0, currency="USD")
        folio = Folio(
            folio_number="FOLIO1",
            confirmation_number="ABC123",
            guest_name="John Doe",
            charges=[],
            payments=[],
            balance=money,
            status="OPEN"
        )
        assert folio.folio_number == "FOLIO1"
        assert folio.confirmation_number == "ABC123"
        assert folio.guest_name == "John Doe"
        assert folio.charges == []
        assert folio.payments == []
        assert folio.balance == money
        assert folio.status == "OPEN"

    def test_folio_creation_with_alias(self):
        """Test creating a Folio using field aliases."""
        money = Money(amount=0.0, currency="USD")
        folio = Folio(
            folioNumber="FOLIO2",
            confirmationNumber="DEF456",
            guestName="Jane Smith",
            balance=money,
            status="CLOSED"
        )
        assert folio.folio_number == "FOLIO2"
        assert folio.confirmation_number == "DEF456"
        assert folio.guest_name == "Jane Smith"
        assert folio.status == "CLOSED"

    def test_folio_with_charges_and_payments(self):
        """Test creating a Folio with charges and payments."""
        charge_money = Money(amount=100.0, currency="USD")
        payment_money = Money(amount=50.0, currency="USD")
        balance_money = Money(amount=50.0, currency="USD")

        charge = Charge(
            folio_number="FOLIO1",
            transaction_code="ROOM",
            description="Room charge",
            amount=charge_money,
            post_date=datetime(2024, 12, 25),
            posted_by="system"
        )

        payment = Payment(
            folio_number="FOLIO1",
            payment_method="CASH",
            amount=payment_money,
            payment_date=datetime(2024, 12, 25),
            processed_by="cashier"
        )

        folio = Folio(
            folio_number="FOLIO1",
            confirmation_number="ABC123",
            guest_name="John Doe",
            charges=[charge],
            payments=[payment],
            balance=balance_money
        )
        assert len(folio.charges) == 1
        assert len(folio.payments) == 1
        assert folio.charges[0].transaction_code == "ROOM"
        assert folio.payments[0].payment_method == "CASH"

    def test_folio_default_status(self):
        """Test Folio default status is OPEN."""
        money = Money(amount=0.0, currency="USD")
        folio = Folio(
            folio_number="FOLIO1",
            confirmation_number="ABC123",
            guest_name="John Doe",
            balance=money
        )
        assert folio.status == "OPEN"

    def test_folio_default_empty_lists(self):
        """Test Folio default charges and payments are empty lists."""
        money = Money(amount=0.0, currency="USD")
        folio = Folio(
            folio_number="FOLIO1",
            confirmation_number="ABC123",
            guest_name="John Doe",
            balance=money
        )
        assert folio.charges == []
        assert folio.payments == []
