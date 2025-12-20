"""
Unit tests for data models.

Tests Pydantic models for validation, serialization, and deserialization.
"""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from opera_cloud_mcp.models.common import Address, Contact, Money
from opera_cloud_mcp.models.financial import Charge, Folio, Payment
from opera_cloud_mcp.models.guest import GuestPreference, GuestProfile
from opera_cloud_mcp.models.reservation import Guest, Reservation, RoomStay
from opera_cloud_mcp.models.room import Room, RoomAvailability, RoomStatus


class TestCommonModels:
    """Tests for common models."""

    def test_address_model(self):
        """Test Address model creation and validation."""
        address = Address(
            addressLine1="123 Main St",
            city="New York",
            stateProvince="NY",
            postalCode="10001",
            country="USA",
        )

        assert address.address_line1 == "123 Main St"
        assert address.city == "New York"
        assert address.state_province == "NY"
        assert address.postal_code == "10001"
        assert address.country == "USA"

    def test_contact_model(self):
        """Test Contact model creation."""
        contact = Contact(
            email="test@example.com", phone="+1234567890", mobile="+1234567891"
        )

        assert contact.email == "test@example.com"
        assert contact.phone == "+1234567890"
        assert contact.mobile == "+1234567891"

    def test_money_model(self):
        """Test Money model creation and defaults."""
        money = Money(amount=100.50)

        assert money.amount == 100.50
        assert money.currency_code == "USD"

        money_eur = Money(amount=85.75, currencyCode="EUR")
        assert money_eur.currency_code == "EUR"


class TestReservationModels:
    """Tests for reservation models."""

    def test_guest_model(self):
        """Test Guest model creation."""
        guest = Guest(
            firstName="John",
            lastName="Doe",
            contact=Contact(email="john.doe@example.com"),
            loyaltyNumber="LOYALTY123",
        )

        assert guest.first_name == "John"
        assert guest.last_name == "Doe"
        assert guest.contact.email == "john.doe@example.com"
        assert guest.loyalty_number == "LOYALTY123"

    def test_room_stay_model(self):
        """Test RoomStay model creation."""
        room_stay = RoomStay(
            roomType="STANDARD",
            arrivalDate=date(2024, 12, 1),
            departureDate=date(2024, 12, 3),
            adults=2,
            children=1,
            rateCode="BAR",
        )

        assert room_stay.room_type == "STANDARD"
        assert room_stay.arrival_date == date(2024, 12, 1)
        assert room_stay.departure_date == date(2024, 12, 3)
        assert room_stay.adults == 2
        assert room_stay.children == 1
        assert room_stay.rate_code == "BAR"

    def test_reservation_model(self):
        """Test complete Reservation model creation."""
        from datetime import datetime

        guest = Guest(
            firstName="John",
            lastName="Doe",
            contact=Contact(email="john.doe@example.com"),
        )
        room_stay = RoomStay(
            roomType="STANDARD",
            arrivalDate=date(2024, 12, 1),
            departureDate=date(2024, 12, 3),
            rateCode="BAR",
        )

        reservation = Reservation(
            confirmationNumber="ABC123456",
            hotelId="TEST_HOTEL",
            primaryGuest=guest,
            roomStay=room_stay,
            createdDate=datetime.now(UTC),
            status="CONFIRMED",
        )

        assert reservation.confirmation_number == "ABC123456"
        assert reservation.hotel_id == "TEST_HOTEL"
        assert reservation.primary_guest.first_name == "John"
        assert reservation.room_stay.room_type == "STANDARD"
        assert reservation.status == "CONFIRMED"

    def test_reservation_validation_errors(self):
        """Test reservation model validation errors."""
        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            Reservation()

        validation_error = exc_info.value
        errors = validation_error.errors()

        # Should have errors for missing required fields
        required_fields = {
            "confirmationNumber",
            "hotelId",
            "guest",
            "roomStay",
            "createdDate",
        }
        error_fields = {error["loc"][0] for error in errors}

        assert required_fields.intersection(error_fields)


class TestGuestModels:
    """Tests for guest models."""

    def test_guest_preference_model(self):
        """Test GuestPreference model."""
        preference = GuestPreference(
            preferenceType="ROOM_TYPE",
            preferenceValue="HIGH_FLOOR",
            description="Prefers high floor rooms",
        )

        assert preference.preference_type == "ROOM_TYPE"
        assert preference.preference_value == "HIGH_FLOOR"
        assert preference.description == "Prefers high floor rooms"

    def test_guest_profile_model(self):
        """Test GuestProfile model with all fields."""
        from datetime import datetime

        contact = Contact(email="jane@example.com", phone="+1234567890")
        address = Address(city="New York", country="USA")
        preference = GuestPreference(
            preferenceType="ROOM_TYPE", preferenceValue="QUIET"
        )

        profile = GuestProfile(
            guestId="GUEST123",
            firstName="Jane",
            lastName="Smith",
            birthDate=date(1990, 5, 15),
            gender="FEMALE",
            nationality="USA",
            contact=contact,
            address=address,
            loyaltyNumber="LOYALTY456",
            loyaltyLevel="GOLD",
            vipStatus="VIP",
            preferences=[preference],
            specialInstructions="Allergic to peanuts",
            createdDate=datetime.now(UTC),
            createdBy="test_user",
        )

        assert profile.guest_id == "GUEST123"
        assert profile.first_name == "Jane"
        assert profile.birth_date == date(1990, 5, 15)
        assert profile.contact.email == "jane@example.com"
        assert len(profile.preferences) == 1
        assert profile.preferences[0].preference_type == "ROOM_TYPE"


class TestRoomModels:
    """Tests for room models."""

    def test_room_model(self):
        """Test Room model creation."""
        room = Room(
            roomNumber="101",
            roomType="STANDARD",
            roomClass="STANDARD",
            floor="1",
            bedType="KING",
            maxOccupancy=2,
            smokingAllowed=False,
            accessible=True,
        )

        assert room.room_number == "101"
        assert room.room_type == "STANDARD"
        assert room.max_occupancy == 2
        assert room.smoking_allowed is False
        assert room.accessible is True

    def test_room_status_model(self):
        """Test RoomStatus model creation."""
        status = RoomStatus(
            roomNumber="101",
            housekeepingStatus="CLEAN",
            frontOfficeStatus="VACANT",
            outOfOrder=False,
            outOfInventory=False,
            maintenanceRequired=True,
        )

        assert status.room_number == "101"
        assert status.housekeeping_status == "CLEAN"
        assert status.front_office_status == "VACANT"
        assert status.maintenance_required is True

    def test_room_availability_model(self):
        """Test RoomAvailability model creation."""
        availability = RoomAvailability(
            date=date(2024, 12, 1),
            roomType="STANDARD",
            availableRooms=5,
            totalRooms=10,
            rateCode="BAR",
            rateAmount=199.00,
        )

        assert availability.date == date(2024, 12, 1)
        assert availability.room_type == "STANDARD"
        assert availability.available_rooms == 5
        assert availability.total_rooms == 10


class TestFinancialModels:
    """Tests for financial models."""

    def test_charge_model(self):
        """Test Charge model creation."""
        amount = Money(amount=50.00, currency_code="USD")
        charge = Charge(
            folioNumber="FOLIO123",
            transactionCode="ROOM",
            description="Room charge",
            amount=amount,
            postDate=datetime.now(UTC),
            postedBy="SYSTEM",
        )

        assert charge.folio_number == "FOLIO123"
        assert charge.transaction_code == "ROOM"
        assert charge.description == "Room charge"
        assert charge.amount.amount == 50.00
        assert charge.posted_by == "SYSTEM"

    def test_payment_model(self):
        """Test Payment model creation."""
        amount = Money(amount=100.00)
        payment = Payment(
            folioNumber="FOLIO123",
            paymentMethod="CASH",
            amount=amount,
            paymentDate=datetime.now(UTC),
            referenceNumber="PAY123",
            processedBy="CLERK01",
        )

        assert payment.folio_number == "FOLIO123"
        assert payment.payment_method == "CASH"
        assert payment.amount.amount == 100.00
        assert payment.reference_number == "PAY123"

    def test_folio_model(self):
        """Test Folio model creation."""
        balance = Money(amount=150.00)
        charge = Charge(
            folioNumber="FOLIO123",
            transactionCode="ROOM",
            description="Room charge",
            amount=Money(amount=200.00),
            postDate=datetime.now(UTC),
            postedBy="SYSTEM",
        )
        payment = Payment(
            folioNumber="FOLIO123",
            paymentMethod="CASH",
            amount=Money(amount=50.00),
            paymentDate=datetime.now(UTC),
            processedBy="CLERK01",
        )

        folio = Folio(
            folioNumber="FOLIO123",
            confirmationNumber="ABC123456",
            guestName="John Doe",
            charges=[charge],
            payments=[payment],
            balance=balance,
            status="OPEN",
        )

        assert folio.folio_number == "FOLIO123"
        assert folio.confirmation_number == "ABC123456"
        assert folio.guest_name == "John Doe"
        assert len(folio.charges) == 1
        assert len(folio.payments) == 1
        assert folio.balance.amount == 150.00
        assert folio.status == "OPEN"
