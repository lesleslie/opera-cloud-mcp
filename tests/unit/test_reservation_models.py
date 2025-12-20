"""
Unit tests for reservation data models.

Tests Pydantic models for validation, transformation, and business rules.
"""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from opera_cloud_mcp.models.common import Address, Contact
from opera_cloud_mcp.models.reservation import (
    AvailabilityResult,
    BulkReservationResult,
    ComprehensiveReservation,
    GuaranteeType,
    Guest,
    GuestProfile,
    PaymentMethod,
    RateType,
    Reservation,
    ReservationSearchResult,
    ReservationStatus,
    RoomStay,
    RoomStayDetails,
    RoomType,
)


class TestGuestProfile:
    """Test suite for GuestProfile model."""

    def test_valid_guest_profile(self):
        """Test creating a valid guest profile."""
        from datetime import datetime

        contact = Contact(email="john.doe@example.com", phone="+1-555-123-4567")
        address = Address(
            addressLine1="123 Main St",
            city="Anytown",
            stateProvince="CA",
            postalCode="12345",
            country="US",
        )

        guest = GuestProfile(
            guestId="GUEST123",
            firstName="John",
            lastName="Doe",
            middleName="Michael",
            title="Mr.",
            gender="M",  # M, F, or O as per pattern
            dateOfBirth=date(1985, 5, 15),
            nationality="US",
            contact=contact,
            address=address,
            loyaltyNumber="GOLD123456",
            vipStatus="VIP",
            createdDate=datetime.now(UTC),
            createdBy="test_user",
        )

        assert guest.first_name == "John"
        assert guest.last_name == "Doe"
        assert guest.middle_name == "Michael"
        assert guest.gender == "M"
        assert guest.nationality == "US"
        assert guest.loyalty_number == "GOLD123456"

    def test_guest_profile_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError) as exc_info:
            GuestProfile(last_name="Doe")  # Missing first_name

        errors = exc_info.value.errors()
        assert any("firstName" in error["loc"] for error in errors)

        with pytest.raises(ValidationError) as exc_info:
            GuestProfile(first_name="John")  # Missing last_name

        errors = exc_info.value.errors()
        assert any("lastName" in error["loc"] for error in errors)

    def test_guest_profile_field_validation(self):
        """Test field-specific validation."""
        # Test name length limits
        with pytest.raises(ValidationError):
            GuestProfile(firstName="", lastName="Doe")  # Empty first name

        with pytest.raises(ValidationError):
            GuestProfile(firstName="A" * 51, lastName="Doe")  # Too long

        # Test gender validation
        with pytest.raises(ValidationError):
            GuestProfile(firstName="John", lastName="Doe", gender="X")  # Invalid gender

        # Valid genders
        for gender in ["M", "F", "O"]:
            guest = GuestProfile(firstName="John", lastName="Doe", gender=gender)
            assert guest.gender == gender

    def test_guest_profile_birth_date_validation(self):
        """Test birth date validation logic."""
        # Future date should be invalid
        with pytest.raises(ValidationError):
            GuestProfile(firstName="John", lastName="Doe", dateOfBirth=date(2030, 1, 1))

        # Very old date should be invalid
        with pytest.raises(ValidationError):
            GuestProfile(firstName="John", lastName="Doe", dateOfBirth=date(1800, 1, 1))

        # Valid birth date
        guest = GuestProfile(
            firstName="John", lastName="Doe", dateOfBirth=date(1985, 5, 15)
        )
        assert guest.date_of_birth == date(1985, 5, 15)

    def test_guest_profile_contact_validation(self):
        """Test contact information validation."""
        # Valid contact
        contact = Contact(email="valid@example.com", phone="+1-555-123-4567")
        guest = GuestProfile(firstName="John", lastName="Doe", contact=contact)
        assert guest.contact.email == "valid@example.com"

    def test_backward_compatibility_guest_alias(self):
        """Test that Guest is still available as an alias."""
        guest = Guest(firstName="John", lastName="Doe")
        assert isinstance(guest, GuestProfile)
        assert guest.first_name == "John"


class TestRoomStayDetails:
    """Test suite for RoomStayDetails model."""

    def test_valid_room_stay(self):
        """Test creating a valid room stay."""
        room_stay = RoomStayDetails(
            roomType="DELUXE",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 18),
            adults=2,
            children=1,
            rateCode="CORPORATE",
        )

        assert room_stay.room_type == "DELUXE"
        assert room_stay.arrival_date == date(2024, 12, 15)
        assert room_stay.departure_date == date(2024, 12, 18)
        assert room_stay.adults == 2
        assert room_stay.children == 1
        assert room_stay.nights == 3  # Auto-calculated

    def test_room_stay_required_fields(self):
        """Test required field validation."""
        with pytest.raises(ValidationError) as exc_info:
            RoomStayDetails(
                arrivalDate=date(2024, 12, 15),
                departureDate=date(2024, 12, 18),
                # Missing roomType and rateCode
            )

        errors = exc_info.value.errors()
        required_aliases = ["roomType", "rateCode"]
        for alias in required_aliases:
            assert any(alias in error["loc"] for error in errors)

    def test_room_stay_date_validation(self):
        """Test date validation logic."""
        # Departure before arrival should be invalid
        with pytest.raises(ValidationError) as exc_info:
            RoomStayDetails(
                roomType="STANDARD",
                rateCode="RACK",
                arrivalDate=date(2024, 12, 18),
                departureDate=date(2024, 12, 15),  # Before arrival
            )

        # Just check that validation failed - don't check specific messages
        assert exc_info.value is not None

    def test_room_stay_nights_calculation(self):
        """Test automatic nights calculation."""
        room_stay = RoomStayDetails(
            roomType="SUITE",
            rateCode="PACKAGE",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 20),
        )

        assert room_stay.nights == 5

    def test_room_stay_nights_validation(self):
        """Test nights field validation when provided."""
        # Nights that don't match date range should be invalid
        with pytest.raises(ValidationError) as exc_info:
            RoomStayDetails(
                roomType="STANDARD",
                rateCode="RACK",
                arrivalDate=date(2024, 12, 15),
                departureDate=date(2024, 12, 18),
                nights=5,  # Should be 3
            )

        error_messages = [error["msg"] for error in exc_info.value.errors()]
        assert any("doesn't match date range" in msg for msg in error_messages)

    def test_room_stay_occupancy_validation(self):
        """Test occupancy limits."""
        # Too many adults
        with pytest.raises(ValidationError):
            RoomStayDetails(
                room_type="STANDARD",
                rate_code="RACK",
                arrival_date=date(2024, 12, 15),
                departure_date=date(2024, 12, 18),
                adults=15,  # Over limit
            )

        # Too many children
        with pytest.raises(ValidationError):
            RoomStayDetails(
                room_type="STANDARD",
                rate_code="RACK",
                arrival_date=date(2024, 12, 15),
                departure_date=date(2024, 12, 18),
                children=15,  # Over limit
            )

        # Zero adults should be invalid
        with pytest.raises(ValidationError):
            RoomStayDetails(
                room_type="STANDARD",
                rate_code="RACK",
                arrival_date=date(2024, 12, 15),
                departure_date=date(2024, 12, 18),
                adults=0,
            )

    def test_backward_compatibility_room_stay_alias(self):
        """Test that RoomStay is still available as an alias."""
        room_stay = RoomStay(
            roomType="STANDARD",
            rateCode="RACK",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 18),
        )
        assert isinstance(room_stay, RoomStayDetails)
        assert room_stay.room_type == "STANDARD"


class TestComprehensiveReservation:
    """Test suite for ComprehensiveReservation model."""

    def test_valid_comprehensive_reservation(self):
        """Test creating a valid comprehensive reservation."""
        guest = GuestProfile(firstName="John", lastName="Doe")
        room_stay = RoomStayDetails(
            roomType="DELUXE",
            rateCode="CORPORATE",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 18),
        )

        reservation = ComprehensiveReservation(
            confirmationNumber="ABC123456",
            hotelId="TEST_HOTEL",
            status=ReservationStatus.CONFIRMED,
            primaryGuest=guest,
            roomStay=room_stay,
            createdDate=datetime(2024, 12, 1, 10, 0, 0),
            guaranteeType=GuaranteeType.CREDIT_CARD,
            specialRequests="Late checkout please",
        )

        assert reservation.confirmation_number == "ABC123456"
        assert reservation.status == ReservationStatus.CONFIRMED
        assert reservation.guarantee_type == GuaranteeType.CREDIT_CARD
        assert reservation.special_requests == "Late checkout please"

    def test_reservation_confirmation_number_validation(self):
        """Test confirmation number validation."""
        guest = GuestProfile(firstName="John", lastName="Doe")
        room_stay = RoomStayDetails(
            roomType="STANDARD",
            rateCode="RACK",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 18),
        )

        # Invalid confirmation number format
        with pytest.raises(ValidationError):
            ComprehensiveReservation(
                confirmationNumber="AB",  # Too short/invalid format
                hotelId="TEST_HOTEL",
                primaryGuest=guest,
                roomStay=room_stay,
                createdDate=datetime.now(UTC),
            )

    def test_reservation_timestamp_validation(self):
        """Test timestamp validation."""
        guest = GuestProfile(firstName="John", lastName="Doe")
        room_stay = RoomStayDetails(
            roomType="STANDARD",
            rateCode="RACK",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 18),
        )

        # Future timestamp should be invalid
        with pytest.raises(ValidationError):
            ComprehensiveReservation(
                confirmationNumber="ABC123456",
                hotelId="TEST_HOTEL",
                primaryGuest=guest,
                roomStay=room_stay,
                createdDate=datetime(2030, 1, 1),  # Future date
            )

    def test_reservation_modification_consistency(self):
        """Test modification field consistency validation."""
        guest = GuestProfile(firstName="John", lastName="Doe")
        room_stay = RoomStayDetails(
            roomType="STANDARD",
            rateCode="RACK",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 18),
        )

        # Should auto-set modified_by when modified_date is provided
        reservation = ComprehensiveReservation(
            confirmationNumber="ABC123456",
            hotelId="TEST_HOTEL",
            primaryGuest=guest,
            roomStay=room_stay,
            createdDate=datetime(2024, 12, 1, 10, 0, 0),
            modifiedDate=datetime(2024, 12, 2, 11, 0, 0),
            # modified_by not provided
        )

        assert reservation.modified_by == "SYSTEM"

    def test_backward_compatibility_reservation_alias(self):
        """Test that Reservation is still available as an alias."""
        guest = GuestProfile(firstName="John", lastName="Doe")
        room_stay = RoomStayDetails(
            roomType="STANDARD",
            rateCode="RACK",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 18),
        )

        reservation = Reservation(
            confirmationNumber="ABC123456",
            hotelId="TEST_HOTEL",
            primaryGuest=guest,
            roomStay=room_stay,
            createdDate=datetime.now(UTC),
        )

        assert isinstance(reservation, ComprehensiveReservation)
        assert reservation.confirmation_number == "ABC123456"


class TestReservationSearchResult:
    """Test suite for ReservationSearchResult model."""

    def test_valid_search_result(self):
        """Test creating a valid search result."""
        guest = GuestProfile(firstName="John", lastName="Doe")
        room_stay = RoomStayDetails(
            roomType="STANDARD",
            rateCode="RACK",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 18),
        )
        reservation = ComprehensiveReservation(
            confirmationNumber="ABC123456",
            hotelId="TEST_HOTEL",
            primaryGuest=guest,
            roomStay=room_stay,
            createdDate=datetime.now(UTC),
        )

        search_result = ReservationSearchResult(
            reservations=[reservation],
            totalCount=1,
            page=1,
            pageSize=10,
        )

        assert len(search_result.reservations) == 1
        assert search_result.total_count == 1
        assert search_result.page == 1
        assert search_result.page_size == 10
        assert search_result.reservations[0].confirmation_number == "ABC123456"

    def test_search_result_pagination_validation(self):
        """Test pagination parameter validation."""
        # Invalid page number
        with pytest.raises(ValidationError):
            ReservationSearchResult(
                reservations=[],
                total_count=0,
                page=0,  # Must be >= 1
                page_size=10,
            )

        # Invalid page size
        with pytest.raises(ValidationError):
            ReservationSearchResult(
                reservations=[],
                total_count=0,
                page=1,
                page_size=0,  # Must be >= 1
            )

        # Page size too large
        with pytest.raises(ValidationError):
            ReservationSearchResult(
                reservations=[],
                total_count=0,
                page=1,
                page_size=101,  # Must be <= 100
            )


class TestEnumerations:
    """Test suite for reservation enumerations."""

    def test_reservation_status_enum(self):
        """Test ReservationStatus enumeration."""
        assert ReservationStatus.CONFIRMED == "CONFIRMED"
        assert ReservationStatus.CANCELED == "CANCELED"
        assert ReservationStatus.CHECKED_IN == "CHECKED_IN"

        # Test enum in model
        guest = GuestProfile(firstName="John", lastName="Doe")
        room_stay = RoomStayDetails(
            roomType="STANDARD",
            rateCode="RACK",
            arrivalDate=date(2024, 12, 15),
            departureDate=date(2024, 12, 18),
        )

        reservation = ComprehensiveReservation(
            confirmationNumber="ABC123456",
            hotelId="TEST_HOTEL",
            primaryGuest=guest,
            roomStay=room_stay,
            createdDate=datetime.now(UTC),
            status=ReservationStatus.PROVISIONAL,
        )

        assert reservation.status == ReservationStatus.PROVISIONAL

    def test_guarantee_type_enum(self):
        """Test GuaranteeType enumeration."""
        assert GuaranteeType.CREDIT_CARD == "CREDIT_CARD"
        assert GuaranteeType.DEPOSIT == "DEPOSIT"
        assert GuaranteeType.NONE == "NONE"

    def test_room_type_enum(self):
        """Test RoomType enumeration."""
        assert RoomType.STANDARD == "STANDARD"
        assert RoomType.DELUXE == "DELUXE"
        assert RoomType.SUITE == "SUITE"
        assert RoomType.PRESIDENTIAL == "PRESIDENTIAL"

    def test_rate_type_enum(self):
        """Test RateType enumeration."""
        assert RateType.RACK == "RACK"
        assert RateType.CORPORATE == "CORPORATE"
        assert RateType.GROUP == "GROUP"
        assert RateType.GOVERNMENT == "GOVERNMENT"


class TestPaymentMethod:
    """Test suite for PaymentMethod model."""

    def test_valid_payment_method(self):
        """Test creating a valid payment method."""
        payment = PaymentMethod(
            type="CREDIT_CARD",
            card_number_masked="****-****-****-1234",
            card_type="VISA",
            expiry_date="12/25",
            holder_name="JOHN DOE",
        )

        assert payment.type == "CREDIT_CARD"
        assert payment.card_number_masked == "****-****-****-1234"
        assert payment.card_type == "VISA"
        assert payment.expiry_date == "12/25"
        assert payment.holder_name == "JOHN DOE"


class TestBulkReservationResult:
    """Test suite for BulkReservationResult model."""

    def test_valid_bulk_result(self):
        """Test creating a valid bulk operation result."""
        result = BulkReservationResult(
            job_id="BULK12345",
            status="COMPLETED",
            total_reservations=10,
            processed_count=10,
            success_count=8,
            error_count=2,
            successful_reservations=["ABC123", "DEF456"],
            failed_reservations=[
                {"index": 3, "error": "Invalid room type"},
                {"index": 7, "error": "Guest validation failed"},
            ],
        )

        assert result.job_id == "BULK12345"
        assert result.total_reservations == 10
        assert result.success_count == 8
        assert result.error_count == 2
        assert len(result.successful_reservations) == 2
        assert len(result.failed_reservations) == 2


class TestAvailabilityResult:
    """Test suite for AvailabilityResult model."""

    def test_valid_availability_result(self):
        """Test creating a valid availability result."""
        result = AvailabilityResult(
            room_type="DELUXE",
            room_type_description="Deluxe King Room",
            available_rooms=5,
            rate_plans=[
                {"rate_code": "RACK", "amount": 199.00},
                {"rate_code": "CORPORATE", "amount": 179.00},
            ],
            restrictions={"min_stay": 2, "max_stay": 14},
        )

        assert result.room_type == "DELUXE"
        assert result.available_rooms == 5
        assert len(result.rate_plans) == 2
        assert result.restrictions["min_stay"] == 2

    def test_availability_result_validation(self):
        """Test availability result validation."""
        # Negative available rooms should be invalid
        with pytest.raises(ValidationError):
            AvailabilityResult(
                room_type="STANDARD",
                available_rooms=-1,  # Cannot be negative
            )
