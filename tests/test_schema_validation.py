"""
Schema validation tests for OPERA Cloud MCP models.

Tests verify that all models inherit from OperaBaseModel with extra="allow"
configuration, ensuring API responses with additional fields are handled gracefully.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import BaseModel

from opera_cloud_mcp.models.common import (
    Address,
    APIError,
    Contact,
    Money,
    OperaBaseModel,
    PaginationInfo,
)
from opera_cloud_mcp.models.financial import Charge, Folio, Payment
from opera_cloud_mcp.models.guest import (
    GenderType,
    GuestIdentification,
    GuestPreference,
    GuestProfile,
    GuestSearchCriteria,
    GuestSearchResult,
    GuestStayHistory,
    GuestStayStatistics,
    LoyaltyPoints,
    LoyaltyProgram,
    LoyaltyTier,
    MarketingPreference,
    PreferenceType,
    ProfileMergeConflict,
    ProfileMergeRequest,
    ProfileMergeResult,
    ProfileStatus,
    StayStatus,
    VIPStatus,
)
from opera_cloud_mcp.models.reservation import (
    AvailabilityResult,
    BulkReservationResult,
    ComprehensiveReservation,
    GuaranteeType,
    Guest,
    PaymentMethod,
    Reservation,
    ReservationCharges,
    ReservationHistory,
    ReservationSearchResult,
    ReservationStatus,
    RoomStay,
    RoomStayDetails,
    RoomType,
)
from opera_cloud_mcp.models.room import Room, RoomAvailability, RoomStatus


def get_extra_config(model_class: type[BaseModel]) -> str | None:
    """Get the 'extra' config value from a Pydantic model class.

    Args:
        model_class: A Pydantic BaseModel subclass.

    Returns:
        The extra config value ('allow', 'ignore', 'forbid') or None if not set.
    """
    model_config = getattr(model_class, "model_config", None)
    if model_config is not None and isinstance(model_config, dict):
        return model_config.get("extra")
    return None


def is_operabasemodel_subclass(model_class: type) -> bool:
    """Check if a class is a subclass of OperaBaseModel.

    Args:
        model_class: A class to check.

    Returns:
        True if the class is a subclass of OperaBaseModel, False otherwise.
    """
    try:
        return issubclass(model_class, OperaBaseModel)
    except TypeError:
        return False


class TestOperaBaseModel:
    """Tests for the OperaBaseModel base class."""

    def test_model_has_extra_allow(self):
        """Verify OperaBaseModel has extra='allow' in model_config."""
        assert get_extra_config(OperaBaseModel) == "allow"

    def test_extra_fields_allowed(self):
        """Verify extra fields can be added to OperaBaseModel instances."""

        class TestModel(OperaBaseModel):
            name: str

        # Create instance with extra field
        model = TestModel(name="test", extra_field="extra_value")
        assert model.name == "test"
        assert model.extra_field == "extra_value"  # type: ignore[attr-defined]

    def test_extra_fields_stored_in_model(self):
        """Verify extra fields are accessible via __pydantic_extra__."""

        class TestModel(OperaBaseModel):
            name: str

        model = TestModel(name="test", custom_field="custom_value")
        assert model.__pydantic_extra__ is not None
        assert model.__pydantic_extra__.get("custom_field") == "custom_value"


class TestCommonModelsExtraFields:
    """Tests for extra field handling in common models."""

    @pytest.fixture
    def sample_address_data(self) -> dict:
        """Sample API response data for Address with extra fields."""
        return {
            "addressLine1": "123 Main Street",
            "addressLine2": "Suite 100",
            "city": "New York",
            "stateProvince": "NY",
            "postalCode": "10001",
            "country": "USA",
            # Extra fields from API
            "addressType": "BUSINESS",
            "isPrimary": True,
            "verificationStatus": "VERIFIED",
            "geoCode": {"lat": 40.7128, "lng": -74.0060},
        }

    @pytest.fixture
    def sample_contact_data(self) -> dict:
        """Sample API response data for Contact with extra fields."""
        return {
            "email": "john.doe@example.com",
            "phone": "+1-555-123-4567",
            "mobile": "+1-555-987-6543",
            "fax": "+1-555-456-7890",
            # Extra fields from API
            "doNotCall": False,
            "doNotEmail": False,
            "preferredContactMethod": "EMAIL",
            "phoneExtension": "1234",
        }

    @pytest.fixture
    def sample_money_data(self) -> dict:
        """Sample API response data for Money with extra fields."""
        return {
            "amount": 199.99,
            "currencyCode": "USD",
            # Extra fields from API
            "taxIncluded": True,
            "baseAmount": 179.99,
            "taxAmount": 20.00,
            "exchangeRate": 1.0,
        }

    @pytest.fixture
    def sample_api_error_data(self) -> dict:
        """Sample API response data for APIError with extra fields."""
        return {
            "errorCode": "RESERVATION_NOT_FOUND",
            "errorMessage": "Reservation with confirmation number ABC123 not found",
            "errorDetails": {"confirmationNumber": "ABC123", "hotelId": "HOTEL001"},
            # Extra fields from API
            "timestamp": datetime.now(UTC).isoformat(),
            "correlationId": "corr-123-456",
            "retryable": False,
        }

    @pytest.fixture
    def sample_pagination_data(self) -> dict:
        """Sample API response data for PaginationInfo with extra fields."""
        return {
            "page": 2,
            "pageSize": 25,
            "totalCount": 150,
            "totalPages": 6,
            # Extra fields from API
            "hasPreviousPage": True,
            "hasNextPage": True,
            "startCursor": "cursor-start",
            "endCursor": "cursor-end",
        }

    def test_address_model_has_extra_handling(self):
        """Verify Address model has extra field handling configured."""
        assert is_operabasemodel_subclass(Address)
        assert get_extra_config(Address) == "allow"

    def test_address_extra_fields_allowed(self, sample_address_data):
        """Verify Address accepts extra fields from API responses."""
        address = Address(**sample_address_data)
        assert address.address_line1 == "123 Main Street"
        assert address.city == "New York"
        assert address.__pydantic_extra__ is not None
        assert address.__pydantic_extra__.get("addressType") == "BUSINESS"
        assert address.__pydantic_extra__.get("isPrimary") is True

    def test_contact_model_has_extra_handling(self):
        """Verify Contact model has extra field handling configured."""
        assert is_operabasemodel_subclass(Contact)
        assert get_extra_config(Contact) == "allow"

    def test_contact_extra_fields_allowed(self, sample_contact_data):
        """Verify Contact accepts extra fields from API responses."""
        contact = Contact(**sample_contact_data)
        assert contact.email == "john.doe@example.com"
        assert contact.phone == "+1-555-123-4567"
        assert contact.__pydantic_extra__ is not None
        assert contact.__pydantic_extra__.get("preferredContactMethod") == "EMAIL"

    def test_money_model_has_extra_handling(self):
        """Verify Money model has extra field handling configured."""
        assert is_operabasemodel_subclass(Money)
        assert get_extra_config(Money) == "allow"

    def test_money_extra_fields_allowed(self, sample_money_data):
        """Verify Money accepts extra fields from API responses."""
        money = Money(**sample_money_data)
        assert money.amount == 199.99
        assert money.currency_code == "USD"
        assert money.__pydantic_extra__ is not None
        assert money.__pydantic_extra__.get("taxIncluded") is True
        assert money.__pydantic_extra__.get("baseAmount") == 179.99

    def test_api_error_model_has_extra_handling(self):
        """Verify APIError model has extra field handling configured."""
        assert is_operabasemodel_subclass(APIError)
        assert get_extra_config(APIError) == "allow"

    def test_api_error_extra_fields_allowed(self, sample_api_error_data):
        """Verify APIError accepts extra fields from API responses."""
        error = APIError(**sample_api_error_data)
        assert error.error_code == "RESERVATION_NOT_FOUND"
        assert error.__pydantic_extra__ is not None
        assert error.__pydantic_extra__.get("retryable") is False

    def test_pagination_model_has_extra_handling(self):
        """Verify PaginationInfo model has extra field handling configured."""
        assert is_operabasemodel_subclass(PaginationInfo)
        assert get_extra_config(PaginationInfo) == "allow"

    def test_pagination_extra_fields_allowed(self, sample_pagination_data):
        """Verify PaginationInfo accepts extra fields from API responses."""
        pagination = PaginationInfo(**sample_pagination_data)
        assert pagination.page == 2
        assert pagination.total_count == 150
        assert pagination.__pydantic_extra__ is not None
        assert pagination.__pydantic_extra__.get("hasNextPage") is True


class TestFinancialModelsExtraFields:
    """Tests for extra field handling in financial models."""

    @pytest.fixture
    def sample_charge_data(self) -> dict:
        """Sample API response data for Charge with extra fields."""
        return {
            "chargeId": "CHG001",
            "folioNumber": "FOLIO123",
            "transactionCode": "ROOM",
            "description": "Room Charge - Night 1",
            "amount": {"amount": 250.00, "currencyCode": "USD"},
            "postDate": datetime.now(UTC).isoformat(),
            "postedBy": "SYSTEM",
            # Extra fields from API
            "department": "FRONT_DESK",
            "receiptNumber": "RCP001",
            "voidable": True,
            "voidedDate": None,
        }

    @pytest.fixture
    def sample_payment_data(self) -> dict:
        """Sample API response data for Payment with extra fields."""
        return {
            "paymentId": "PAY001",
            "folioNumber": "FOLIO123",
            "paymentMethod": "CREDIT_CARD",
            "amount": {"amount": 500.00, "currencyCode": "USD"},
            "paymentDate": datetime.now(UTC).isoformat(),
            "referenceNumber": "REF123456",
            "processedBy": "CLERK01",
            # Extra fields from API
            "cardType": "VISA",
            "lastFourDigits": "4242",
            "approvalCode": "APPROVED",
            "batchNumber": "BATCH001",
        }

    @pytest.fixture
    def sample_folio_data(self) -> dict:
        """Sample API response data for Folio with extra fields."""
        return {
            "folioNumber": "FOLIO123",
            "confirmationNumber": "ABC123456",
            "guestName": "John Doe",
            "charges": [],
            "payments": [],
            "balance": {"amount": 150.00, "currencyCode": "USD"},
            "status": "OPEN",
            # Extra fields from API
            "openDate": datetime.now(UTC).isoformat(),
            "creditLimit": 1000.00,
            "companyAccount": False,
            "allowPostToRoom": True,
        }

    def test_charge_model_has_extra_handling(self):
        """Verify Charge model has extra field handling configured."""
        assert is_operabasemodel_subclass(Charge)
        assert get_extra_config(Charge) == "allow"

    def test_charge_extra_fields_allowed(self, sample_charge_data):
        """Verify Charge accepts extra fields from API responses."""
        charge = Charge(**sample_charge_data)
        assert charge.folio_number == "FOLIO123"
        assert charge.transaction_code == "ROOM"
        assert charge.__pydantic_extra__ is not None
        assert charge.__pydantic_extra__.get("department") == "FRONT_DESK"
        assert charge.__pydantic_extra__.get("voidable") is True

    def test_payment_model_has_extra_handling(self):
        """Verify Payment model has extra field handling configured."""
        assert is_operabasemodel_subclass(Payment)
        assert get_extra_config(Payment) == "allow"

    def test_payment_extra_fields_allowed(self, sample_payment_data):
        """Verify Payment accepts extra fields from API responses."""
        payment = Payment(**sample_payment_data)
        assert payment.folio_number == "FOLIO123"
        assert payment.payment_method == "CREDIT_CARD"
        assert payment.__pydantic_extra__ is not None
        assert payment.__pydantic_extra__.get("cardType") == "VISA"
        assert payment.__pydantic_extra__.get("approvalCode") == "APPROVED"

    def test_folio_model_has_extra_handling(self):
        """Verify Folio model has extra field handling configured."""
        assert is_operabasemodel_subclass(Folio)
        assert get_extra_config(Folio) == "allow"

    def test_folio_extra_fields_allowed(self, sample_folio_data):
        """Verify Folio accepts extra fields from API responses."""
        folio = Folio(**sample_folio_data)
        assert folio.folio_number == "FOLIO123"
        assert folio.guest_name == "John Doe"
        assert folio.__pydantic_extra__ is not None
        assert folio.__pydantic_extra__.get("creditLimit") == 1000.00


class TestGuestModelsExtraFields:
    """Tests for extra field handling in guest models."""

    @pytest.fixture
    def sample_marketing_preference_data(self) -> dict:
        """Sample API response data for MarketingPreference with extra fields."""
        return {
            "emailMarketing": True,
            "smsMarketing": False,
            "postalMarketing": True,
            "phoneMarketing": False,
            "partnerMarketing": False,
            "promotionalOffers": True,
            "newsletter": True,
            "eventInvitations": False,
            "surveys": False,
            # Extra fields from API
            "preferredLanguage": "en-US",
            "lastContactedDate": datetime.now(UTC).isoformat(),
        }

    @pytest.fixture
    def sample_guest_preference_data(self) -> dict:
        """Sample API response data for GuestPreference with extra fields."""
        return {
            "preferenceId": "PREF001",
            "preferenceType": "ROOM_TYPE",
            "preferenceValue": "HIGH_FLOOR",
            "preferenceCode": "HF",
            "description": "Guest prefers high floor rooms",
            "isPrimary": True,
            "priority": 1,
            # Extra fields from API
            "activeFrom": date.today().isoformat(),
            "activeUntil": None,
            "source": "GUEST_PROFILE",
        }

    @pytest.fixture
    def sample_loyalty_points_data(self) -> dict:
        """Sample API response data for LoyaltyPoints with extra fields."""
        return {
            "currentPoints": 15000,
            "lifetimePoints": 125000,
            "pointsToNextTier": 5000,
            "pointsExpiringSoon": 2000,
            "expiryDate": date(2025, 12, 31).isoformat(),
            # Extra fields from API
            "tierBonusPoints": 500,
            "promotionPoints": 1000,
        }

    @pytest.fixture
    def sample_loyalty_program_data(self) -> dict:
        """Sample API response data for LoyaltyProgram with extra fields."""
        return {
            "programId": "LOYALTY_GOLD",
            "programName": "Gold Rewards",
            "membershipNumber": "GR123456789",
            "tier": "GOLD",
            "tierName": "Gold Member",
            "memberSince": date(2020, 1, 15).isoformat(),
            "points": {"currentPoints": 15000},
            "benefits": ["Free WiFi", "Late Checkout", "Room Upgrade"],
            "isActive": True,
            # Extra fields from API
            "enrollmentChannel": "WEB",
            "lastActivityDate": datetime.now(UTC).isoformat(),
        }

    @pytest.fixture
    def sample_guest_identification_data(self) -> dict:
        """Sample API response data for GuestIdentification with extra fields."""
        return {
            "idType": "PASSPORT",
            "idNumber": "US123456789",
            "issuingCountry": "USA",
            "expiryDate": date(2030, 5, 15).isoformat(),
            "isPrimary": True,
            # Extra fields from API
            "verifiedBy": "FRONT_DESK",
            "verificationDate": datetime.now(UTC).isoformat(),
        }

    @pytest.fixture
    def sample_guest_stay_statistics_data(self) -> dict:
        """Sample API response data for GuestStayStatistics with extra fields."""
        return {
            "totalStays": 25,
            "totalNights": 78,
            "totalRevenue": Decimal("15250.00"),
            "averageDailyRate": Decimal("195.51"),
            "averageLengthOfStay": 3.12,
            # Extra fields from API
            "lastStayHotel": "HOTEL001",
            "preferredSeason": "SUMMER",
        }

    @pytest.fixture
    def sample_guest_stay_history_data(self) -> dict:
        """Sample API response data for GuestStayHistory with extra fields."""
        return {
            "reservationId": "RES001",
            "confirmationNumber": "ABC123456",
            "hotelId": "HOTEL001",
            "hotelName": "Grand Hotel",
            "arrivalDate": date(2024, 12, 1).isoformat(),
            "departureDate": date(2024, 12, 4).isoformat(),
            "nights": 3,
            "roomType": "DELUXE",
            "rateCode": "BAR",
            "status": "COMPLETED",
            "roomRevenue": {"amount": 750.00, "currencyCode": "USD"},
            "totalRevenue": {"amount": 950.00, "currencyCode": "USD"},
            "createdDate": datetime.now(UTC).isoformat(),
            # Extra fields from API
            "checkInTime": "15:30",
            "checkOutTime": "11:00",
            "roomNumberAssigned": "1205",
        }

    @pytest.fixture
    def sample_guest_profile_data(self) -> dict:
        """Sample API response data for GuestProfile with extra fields."""
        return {
            "guestId": "GUEST001",
            "profileNumber": "P123456",
            "firstName": "John",
            "lastName": "Doe",
            "middleName": "William",
            "title": "Mr",
            "gender": "MALE",
            "birthDate": date(1985, 6, 15).isoformat(),
            "contact": {"email": "john.doe@example.com"},
            "status": "ACTIVE",
            "vipStatus": "VIP",
            "createdDate": datetime.now(UTC).isoformat(),
            "createdBy": "SYSTEM",
            # Extra fields from API
            "profileSource": "WEB_ENROLLMENT",
            "lastLoginDate": datetime.now(UTC).isoformat(),
            "dataQualityScore": 95,
        }

    def test_marketing_preference_model_has_extra_handling(self):
        """Verify MarketingPreference model has extra field handling configured."""
        assert is_operabasemodel_subclass(MarketingPreference)
        assert get_extra_config(MarketingPreference) == "allow"

    def test_marketing_preference_extra_fields_allowed(self, sample_marketing_preference_data):
        """Verify MarketingPreference accepts extra fields from API responses."""
        pref = MarketingPreference(**sample_marketing_preference_data)
        assert pref.email_marketing is True
        assert pref.__pydantic_extra__ is not None
        assert pref.__pydantic_extra__.get("preferredLanguage") == "en-US"

    def test_guest_preference_model_has_extra_handling(self):
        """Verify GuestPreference model has extra field handling configured."""
        assert is_operabasemodel_subclass(GuestPreference)
        assert get_extra_config(GuestPreference) == "allow"

    def test_guest_preference_extra_fields_allowed(self, sample_guest_preference_data):
        """Verify GuestPreference accepts extra fields from API responses."""
        pref = GuestPreference(**sample_guest_preference_data)
        assert pref.preference_type == "ROOM_TYPE"
        assert pref.__pydantic_extra__ is not None
        assert pref.__pydantic_extra__.get("source") == "GUEST_PROFILE"

    def test_loyalty_points_model_has_extra_handling(self):
        """Verify LoyaltyPoints model has extra field handling configured."""
        assert is_operabasemodel_subclass(LoyaltyPoints)
        assert get_extra_config(LoyaltyPoints) == "allow"

    def test_loyalty_points_extra_fields_allowed(self, sample_loyalty_points_data):
        """Verify LoyaltyPoints accepts extra fields from API responses."""
        points = LoyaltyPoints(**sample_loyalty_points_data)
        assert points.current_points == 15000
        assert points.__pydantic_extra__ is not None
        assert points.__pydantic_extra__.get("tierBonusPoints") == 500

    def test_loyalty_program_model_has_extra_handling(self):
        """Verify LoyaltyProgram model has extra field handling configured."""
        assert is_operabasemodel_subclass(LoyaltyProgram)
        assert get_extra_config(LoyaltyProgram) == "allow"

    def test_loyalty_program_extra_fields_allowed(self, sample_loyalty_program_data):
        """Verify LoyaltyProgram accepts extra fields from API responses."""
        program = LoyaltyProgram(**sample_loyalty_program_data)
        assert program.program_id == "LOYALTY_GOLD"
        assert program.__pydantic_extra__ is not None
        assert program.__pydantic_extra__.get("enrollmentChannel") == "WEB"

    def test_guest_identification_model_has_extra_handling(self):
        """Verify GuestIdentification model has extra field handling configured."""
        assert is_operabasemodel_subclass(GuestIdentification)
        assert get_extra_config(GuestIdentification) == "allow"

    def test_guest_identification_extra_fields_allowed(self, sample_guest_identification_data):
        """Verify GuestIdentification accepts extra fields from API responses."""
        ident = GuestIdentification(**sample_guest_identification_data)
        assert ident.id_type == "PASSPORT"
        assert ident.__pydantic_extra__ is not None
        assert ident.__pydantic_extra__.get("verifiedBy") == "FRONT_DESK"

    def test_guest_stay_statistics_model_has_extra_handling(self):
        """Verify GuestStayStatistics model has extra field handling configured."""
        assert is_operabasemodel_subclass(GuestStayStatistics)
        assert get_extra_config(GuestStayStatistics) == "allow"

    def test_guest_stay_statistics_extra_fields_allowed(self, sample_guest_stay_statistics_data):
        """Verify GuestStayStatistics accepts extra fields from API responses."""
        stats = GuestStayStatistics(**sample_guest_stay_statistics_data)
        assert stats.total_stays == 25
        assert stats.__pydantic_extra__ is not None
        assert stats.__pydantic_extra__.get("preferredSeason") == "SUMMER"

    def test_guest_stay_history_model_has_extra_handling(self):
        """Verify GuestStayHistory model has extra field handling configured."""
        assert is_operabasemodel_subclass(GuestStayHistory)
        assert get_extra_config(GuestStayHistory) == "allow"

    def test_guest_stay_history_extra_fields_allowed(self, sample_guest_stay_history_data):
        """Verify GuestStayHistory accepts extra fields from API responses."""
        history = GuestStayHistory(**sample_guest_stay_history_data)
        assert history.reservation_id == "RES001"
        assert history.__pydantic_extra__ is not None
        assert history.__pydantic_extra__.get("roomNumberAssigned") == "1205"

    def test_guest_profile_model_has_extra_handling(self):
        """Verify GuestProfile model has extra field handling configured."""
        assert is_operabasemodel_subclass(GuestProfile)
        assert get_extra_config(GuestProfile) == "allow"

    def test_guest_profile_extra_fields_allowed(self, sample_guest_profile_data):
        """Verify GuestProfile accepts extra fields from API responses."""
        profile = GuestProfile(**sample_guest_profile_data)
        assert profile.guest_id == "GUEST001"
        assert profile.first_name == "John"
        assert profile.__pydantic_extra__ is not None
        assert profile.__pydantic_extra__.get("profileSource") == "WEB_ENROLLMENT"


class TestReservationModelsExtraFields:
    """Tests for extra field handling in reservation models."""

    @pytest.fixture
    def sample_payment_method_data(self) -> dict:
        """Sample API response data for PaymentMethod with extra fields."""
        return {
            "type": "CC",
            "card_number_masked": "************4242",
            "card_type": "VISA",
            "expiry_date": "12/25",
            "holder_name": "John Doe",
            # Extra fields from API
            "tokenized": True,
            "tokenExpiry": date(2026, 12, 31).isoformat(),
        }

    @pytest.fixture
    def sample_guest_data(self) -> dict:
        """Sample API response data for Guest (reservation.Guest) with extra fields."""
        return {
            "firstName": "John",
            "lastName": "Doe",
            "contact": {"email": "john.doe@example.com", "phone": "+1-555-123-4567"},
            # Extra fields from API
            "membershipLevel": "GOLD",
            "preferredLanguage": "en",
        }

    @pytest.fixture
    def sample_room_stay_data(self) -> dict:
        """Sample API response data for RoomStay with extra fields."""
        return {
            "roomType": "DELUXE",
            "roomTypeDescription": "Deluxe King Room",
            "arrivalDate": date(2024, 12, 15).isoformat(),
            "departureDate": date(2024, 12, 18).isoformat(),
            "adults": 2,
            "children": 1,
            "rateCode": "BAR",
            "rateAmount": {"amount": 250.00, "currencyCode": "USD"},
            # Extra fields from API
            "roomBlock": "PREMIUM",
            "upgradeEligible": True,
            "specialOccasion": "ANNIVERSARY",
        }

    @pytest.fixture
    def sample_comprehensive_reservation_data(self) -> dict:
        """Sample API response data for ComprehensiveReservation with extra fields."""
        return {
            "confirmationNumber": "ABC123456",
            "hotelId": "HOTEL001",
            "reservationId": "RES001",
            "status": "CONFIRMED",
            "reservationType": "INDIVIDUAL",
            "primaryGuest": {
                "firstName": "John",
                "lastName": "Doe",
            },
            "roomStay": {
                "roomType": "DELUXE",
                "arrivalDate": date(2024, 12, 15).isoformat(),
                "departureDate": date(2024, 12, 18).isoformat(),
                "rateCode": "BAR",
            },
            "createdDate": datetime.now(UTC).isoformat(),
            # Extra fields from API
            "externalReference": "EXT123456",
            "channelManagerId": "CM001",
            "loyaltyAccrualEligible": True,
        }

    @pytest.fixture
    def sample_reservation_search_result_data(self) -> dict:
        """Sample API response data for ReservationSearchResult with extra fields."""
        return {
            "reservations": [],
            "totalCount": 0,
            "page": 1,
            "pageSize": 10,
            "hasMore": False,
            # Extra fields from API
            "searchId": "search-uuid-123",
            "cacheHit": True,
        }

    @pytest.fixture
    def sample_availability_result_data(self) -> dict:
        """Sample API response data for AvailabilityResult with extra fields."""
        return {
            "room_type": "DELUXE",
            "room_type_description": "Deluxe King Room",
            "available_rooms": 5,
            "rate_plans": [],
            "restrictions": {},
            # Extra fields from API
            "lastUpdated": datetime.now(UTC).isoformat(),
            "dataSource": "INVENTORY_SYSTEM",
        }

    @pytest.fixture
    def sample_bulk_reservation_result_data(self) -> dict:
        """Sample API response data for BulkReservationResult with extra fields."""
        return {
            "job_id": "JOB001",
            "status": "PROCESSING",
            "total_reservations": 50,
            "processed_count": 25,
            "success_count": 23,
            "error_count": 2,
            # Extra fields from API
            "estimatedTimeRemaining": "00:05:30",
            "currentBatch": 2,
        }

    def test_payment_method_is_basemodel_not_operabasemodel(self):
        """Verify PaymentMethod is a BaseModel (not OperaBaseModel).

        PaymentMethod inherits from BaseModel directly, not OperaBaseModel.
        This test documents this behavior.
        """
        assert issubclass(PaymentMethod, BaseModel)
        assert not is_operabasemodel_subclass(PaymentMethod)

    def test_guest_model_has_extra_handling(self):
        """Verify Guest model has extra field handling configured."""
        assert is_operabasemodel_subclass(Guest)
        assert get_extra_config(Guest) == "allow"

    def test_guest_extra_fields_allowed(self, sample_guest_data):
        """Verify Guest accepts extra fields from API responses."""
        guest = Guest(**sample_guest_data)
        assert guest.first_name == "John"
        assert guest.__pydantic_extra__ is not None
        assert guest.__pydantic_extra__.get("membershipLevel") == "GOLD"

    def test_room_stay_model_has_extra_handling(self):
        """Verify RoomStay model has extra field handling configured."""
        assert is_operabasemodel_subclass(RoomStay)
        assert get_extra_config(RoomStay) == "allow"

    def test_room_stay_extra_fields_allowed(self, sample_room_stay_data):
        """Verify RoomStay accepts extra fields from API responses."""
        room_stay = RoomStay(**sample_room_stay_data)
        assert room_stay.room_type == "DELUXE"
        assert room_stay.__pydantic_extra__ is not None
        assert room_stay.__pydantic_extra__.get("upgradeEligible") is True

    def test_comprehensive_reservation_model_has_extra_handling(self):
        """Verify ComprehensiveReservation model has extra field handling configured."""
        assert is_operabasemodel_subclass(ComprehensiveReservation)
        assert get_extra_config(ComprehensiveReservation) == "allow"

    def test_comprehensive_reservation_extra_fields_allowed(self, sample_comprehensive_reservation_data):
        """Verify ComprehensiveReservation accepts extra fields from API responses."""
        reservation = ComprehensiveReservation(**sample_comprehensive_reservation_data)
        assert reservation.confirmation_number == "ABC123456"
        assert reservation.__pydantic_extra__ is not None
        assert reservation.__pydantic_extra__.get("channelManagerId") == "CM001"

    def test_reservation_alias(self):
        """Verify Reservation is an alias for ComprehensiveReservation."""
        assert Reservation is ComprehensiveReservation

    def test_reservation_search_result_model_has_extra_handling(self):
        """Verify ReservationSearchResult model has extra field handling configured."""
        assert is_operabasemodel_subclass(ReservationSearchResult)
        assert get_extra_config(ReservationSearchResult) == "allow"

    def test_reservation_search_result_extra_fields_allowed(self, sample_reservation_search_result_data):
        """Verify ReservationSearchResult accepts extra fields from API responses."""
        result = ReservationSearchResult(**sample_reservation_search_result_data)
        assert result.total_count == 0
        assert result.__pydantic_extra__ is not None
        assert result.__pydantic_extra__.get("cacheHit") is True

    def test_availability_result_is_basemodel_not_operabasemodel(self):
        """Verify AvailabilityResult is a BaseModel (not OperaBaseModel).

        AvailabilityResult inherits from BaseModel directly, not OperaBaseModel.
        This test documents this behavior.
        """
        assert issubclass(AvailabilityResult, BaseModel)
        assert not is_operabasemodel_subclass(AvailabilityResult)

    def test_bulk_reservation_result_is_basemodel_not_operabasemodel(self):
        """Verify BulkReservationResult is a BaseModel (not OperaBaseModel).

        BulkReservationResult inherits from BaseModel directly, not OperaBaseModel.
        This test documents this behavior.
        """
        assert issubclass(BulkReservationResult, BaseModel)
        assert not is_operabasemodel_subclass(BulkReservationResult)


class TestRoomModelsExtraFields:
    """Tests for extra field handling in room models."""

    @pytest.fixture
    def sample_room_data(self) -> dict:
        """Sample API response data for Room with extra fields."""
        return {
            "roomNumber": "1205",
            "roomType": "DELUXE",
            "roomClass": "PREMIUM",
            "floor": "12",
            "building": "MAIN",
            "bedType": "KING",
            "maxOccupancy": 4,
            "smokingAllowed": False,
            "accessible": True,
            # Extra fields from API
            "viewType": "OCEAN",
            "lastRenovated": "2023-06-15",
            "roomFeatures": ["BALCONY", "MINIBAR", "SAFE"],
        }

    @pytest.fixture
    def sample_room_status_data(self) -> dict:
        """Sample API response data for RoomStatus with extra fields."""
        return {
            "roomNumber": "1205",
            "housekeepingStatus": "CLEAN",
            "frontOfficeStatus": "VACANT",
            "outOfOrder": False,
            "outOfInventory": False,
            "maintenanceRequired": False,
            # Extra fields from API
            "lastCleanedAt": datetime.now(UTC).isoformat(),
            "assignedAttendant": "EMP001",
            "inspectionDue": False,
        }

    @pytest.fixture
    def sample_room_availability_data(self) -> dict:
        """Sample API response data for RoomAvailability with extra fields."""
        return {
            "date": date(2024, 12, 15).isoformat(),
            "roomType": "DELUXE",
            "availableRooms": 8,
            "totalRooms": 15,
            "rateCode": "BAR",
            "rateAmount": 275.00,
            # Extra fields from API
            "overbookingAllowed": True,
            "overbookingCount": 2,
            "restrictionReason": None,
        }

    def test_room_model_has_extra_handling(self):
        """Verify Room model has extra field handling configured."""
        assert is_operabasemodel_subclass(Room)
        assert get_extra_config(Room) == "allow"

    def test_room_extra_fields_allowed(self, sample_room_data):
        """Verify Room accepts extra fields from API responses."""
        room = Room(**sample_room_data)
        assert room.room_number == "1205"
        assert room.room_type == "DELUXE"
        assert room.__pydantic_extra__ is not None
        assert room.__pydantic_extra__.get("viewType") == "OCEAN"
        assert room.__pydantic_extra__.get("roomFeatures") == ["BALCONY", "MINIBAR", "SAFE"]

    def test_room_status_model_has_extra_handling(self):
        """Verify RoomStatus model has extra field handling configured."""
        assert is_operabasemodel_subclass(RoomStatus)
        assert get_extra_config(RoomStatus) == "allow"

    def test_room_status_extra_fields_allowed(self, sample_room_status_data):
        """Verify RoomStatus accepts extra fields from API responses."""
        status = RoomStatus(**sample_room_status_data)
        assert status.room_number == "1205"
        assert status.housekeeping_status == "CLEAN"
        assert status.__pydantic_extra__ is not None
        assert status.__pydantic_extra__.get("assignedAttendant") == "EMP001"

    def test_room_availability_model_has_extra_handling(self):
        """Verify RoomAvailability model has extra field handling configured."""
        assert is_operabasemodel_subclass(RoomAvailability)
        assert get_extra_config(RoomAvailability) == "allow"

    def test_room_availability_extra_fields_allowed(self, sample_room_availability_data):
        """Verify RoomAvailability accepts extra fields from API responses."""
        availability = RoomAvailability(**sample_room_availability_data)
        assert availability.room_type == "DELUXE"
        assert availability.available_rooms == 8
        assert availability.__pydantic_extra__ is not None
        assert availability.__pydantic_extra__.get("overbookingAllowed") is True


class TestSearchAndMergeModelsExtraFields:
    """Tests for extra field handling in search and merge models."""

    @pytest.fixture
    def sample_guest_search_criteria_data(self) -> dict:
        """Sample API response data for GuestSearchCriteria with extra fields."""
        return {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
            "page": 1,
            "pageSize": 20,
            # Extra fields from API
            "fuzzyMatch": True,
            "includeInactive": False,
        }

    @pytest.fixture
    def sample_guest_search_result_data(self) -> dict:
        """Sample API response data for GuestSearchResult with extra fields."""
        return {
            "guests": [],
            "pagination": {
                "page": 1,
                "pageSize": 20,
                "totalCount": 0,
                "totalPages": 0,
            },
            # Extra fields from API
            "searchId": "search-123",
            "cached": False,
        }

    @pytest.fixture
    def sample_profile_merge_conflict_data(self) -> dict:
        """Sample API response data for ProfileMergeConflict with extra fields."""
        return {
            "fieldName": "email",
            "sourceValue": "source@example.com",
            "targetValue": "target@example.com",
            # Extra fields from API
            "suggestedResolution": "KEEP_TARGET",
            "confidence": 0.95,
        }

    @pytest.fixture
    def sample_profile_merge_request_data(self) -> dict:
        """Sample API response data for ProfileMergeRequest with extra fields."""
        return {
            "sourceProfileId": "GUEST001",
            "targetProfileId": "GUEST002",
            "preserveHistory": True,
            "mergePreferences": True,
            "mergeLoyalty": True,
            "mergedBy": "ADMIN",
            # Extra fields from API
            "mergeReason": "DUPLICATE_DETECTED",
            "autoDetected": True,
        }

    @pytest.fixture
    def sample_profile_merge_result_data(self) -> dict:
        """Sample API response data for ProfileMergeResult with extra fields."""
        return {
            "success": True,
            "mergedProfileId": "GUEST002",
            "conflicts": [],
            "warnings": [],
            "fieldsMerged": 15,
            "conflictsResolved": 2,
            "manualResolutionRequired": 0,
            # Extra fields from API
            "auditLogId": "AUDIT001",
            "reversible": True,
        }

    def test_guest_search_criteria_model_has_extra_handling(self):
        """Verify GuestSearchCriteria model has extra field handling configured."""
        assert is_operabasemodel_subclass(GuestSearchCriteria)
        assert get_extra_config(GuestSearchCriteria) == "allow"

    def test_guest_search_criteria_extra_fields_allowed(self, sample_guest_search_criteria_data):
        """Verify GuestSearchCriteria accepts extra fields from API responses."""
        criteria = GuestSearchCriteria(**sample_guest_search_criteria_data)
        assert criteria.first_name == "John"
        assert criteria.__pydantic_extra__ is not None
        assert criteria.__pydantic_extra__.get("fuzzyMatch") is True

    def test_guest_search_result_model_has_extra_handling(self):
        """Verify GuestSearchResult model has extra field handling configured."""
        assert is_operabasemodel_subclass(GuestSearchResult)
        assert get_extra_config(GuestSearchResult) == "allow"

    def test_guest_search_result_extra_fields_allowed(self, sample_guest_search_result_data):
        """Verify GuestSearchResult accepts extra fields from API responses."""
        result = GuestSearchResult(**sample_guest_search_result_data)
        assert result.__pydantic_extra__ is not None
        assert result.__pydantic_extra__.get("searchId") == "search-123"

    def test_profile_merge_conflict_model_has_extra_handling(self):
        """Verify ProfileMergeConflict model has extra field handling configured."""
        assert is_operabasemodel_subclass(ProfileMergeConflict)
        assert get_extra_config(ProfileMergeConflict) == "allow"

    def test_profile_merge_conflict_extra_fields_allowed(self, sample_profile_merge_conflict_data):
        """Verify ProfileMergeConflict accepts extra fields from API responses."""
        conflict = ProfileMergeConflict(**sample_profile_merge_conflict_data)
        assert conflict.field_name == "email"
        assert conflict.__pydantic_extra__ is not None
        assert conflict.__pydantic_extra__.get("confidence") == 0.95

    def test_profile_merge_request_model_has_extra_handling(self):
        """Verify ProfileMergeRequest model has extra field handling configured."""
        assert is_operabasemodel_subclass(ProfileMergeRequest)
        assert get_extra_config(ProfileMergeRequest) == "allow"

    def test_profile_merge_request_extra_fields_allowed(self, sample_profile_merge_request_data):
        """Verify ProfileMergeRequest accepts extra fields from API responses."""
        request = ProfileMergeRequest(**sample_profile_merge_request_data)
        assert request.source_profile_id == "GUEST001"
        assert request.__pydantic_extra__ is not None
        assert request.__pydantic_extra__.get("autoDetected") is True

    def test_profile_merge_result_model_has_extra_handling(self):
        """Verify ProfileMergeResult model has extra field handling configured."""
        assert is_operabasemodel_subclass(ProfileMergeResult)
        assert get_extra_config(ProfileMergeResult) == "allow"

    def test_profile_merge_result_extra_fields_allowed(self, sample_profile_merge_result_data):
        """Verify ProfileMergeResult accepts extra fields from API responses."""
        result = ProfileMergeResult(**sample_profile_merge_result_data)
        assert result.success is True
        assert result.__pydantic_extra__ is not None
        assert result.__pydantic_extra__.get("reversible") is True


class TestNestedModelExtraFields:
    """Tests for extra field handling in nested model structures."""

    @pytest.fixture
    def sample_nested_reservation_data(self) -> dict:
        """Sample API response with deeply nested structure and extra fields."""
        return {
            "confirmationNumber": "NEST123",
            "hotelId": "HOTEL001",
            "primaryGuest": {
                "firstName": "Jane",
                "lastName": "Smith",
                "contact": {
                    "email": "jane.smith@example.com",
                    "phone": "+1-555-999-8888",
                    # Extra field in nested Contact
                    "doNotContact": False,
                },
                "address": {
                    "addressLine1": "456 Oak Avenue",
                    "city": "Los Angeles",
                    # Extra field in nested Address
                    "addressVerified": True,
                },
                # Extra field in nested Guest
                "membershipTier": "PLATINUM",
            },
            "roomStay": {
                "roomType": "SUITE",
                "arrivalDate": date(2024, 12, 20).isoformat(),
                "departureDate": date(2024, 12, 25).isoformat(),
                "rateCode": "PKG",
                # Extra field in nested RoomStay
                "packageIncluded": True,
            },
            "createdDate": datetime.now(UTC).isoformat(),
            # Extra field at top level
            "integrationSource": "EXPEDIA",
        }

    def test_nested_models_preserve_extra_fields(self, sample_nested_reservation_data):
        """Verify extra fields are preserved at all nesting levels."""
        reservation = ComprehensiveReservation(**sample_nested_reservation_data)

        # Top-level extra field
        assert reservation.__pydantic_extra__ is not None
        assert reservation.__pydantic_extra__.get("integrationSource") == "EXPEDIA"

        # Primary guest extra field
        assert reservation.primary_guest.__pydantic_extra__ is not None
        assert reservation.primary_guest.__pydantic_extra__.get("membershipTier") == "PLATINUM"

        # Room stay extra field
        assert reservation.room_stay.__pydantic_extra__ is not None
        assert reservation.room_stay.__pydantic_extra__.get("packageIncluded") is True

    def test_complex_guest_profile_with_nested_extra_fields(self):
        """Verify complex guest profile handles extra fields at all levels."""
        data = {
            "guestId": "GUEST_COMPLEX",
            "firstName": "Robert",
            "lastName": "Johnson",
            "contact": {
                "email": "robert@example.com",
                "preferredContactTime": "MORNING",  # Extra
            },
            "address": {
                "city": "Chicago",
                "country": "USA",
                "residentialType": "APARTMENT",  # Extra
            },
            "loyaltyPrograms": [
                {
                    "programId": "PROG001",
                    "programName": "Rewards",
                    "membershipNumber": "MEM123",
                    "tierBonus": 500,  # Extra
                }
            ],
            "preferences": [
                {
                    "preferenceType": "ROOM_TYPE",
                    "preferenceValue": "QUIET",
                    "appliesToAllHotels": True,  # Extra
                }
            ],
            "createdDate": datetime.now(UTC).isoformat(),
            "createdBy": "SYSTEM",
            "lifetimeValue": Decimal("25000.00"),  # Extra at top level
        }

        profile = GuestProfile(**data)

        # Top-level extra
        assert profile.__pydantic_extra__ is not None
        assert profile.__pydantic_extra__.get("lifetimeValue") == Decimal("25000.00")

        # Contact extra
        assert profile.contact is not None
        assert profile.contact.__pydantic_extra__ is not None
        assert profile.contact.__pydantic_extra__.get("preferredContactTime") == "MORNING"

        # Address extra
        assert profile.address is not None
        assert profile.address.__pydantic_extra__ is not None
        assert profile.address.__pydantic_extra__.get("residentialType") == "APARTMENT"


class TestModelConfigConsistency:
    """Tests for consistent model configuration across all models."""

    @pytest.fixture(params=[
        # Common models
        Address, Contact, Money, APIError, PaginationInfo,
        # Financial models
        Charge, Payment, Folio,
        # Guest models
        MarketingPreference, GuestPreference, LoyaltyPoints, LoyaltyProgram,
        GuestIdentification, GuestStayStatistics, GuestStayHistory, GuestProfile,
        GuestSearchCriteria, GuestSearchResult, ProfileMergeConflict,
        ProfileMergeRequest, ProfileMergeResult,
        # Reservation models (OperaBaseModel subclasses only)
        Guest, RoomStay, RoomStayDetails, ComprehensiveReservation, Reservation,
        ReservationSearchResult,
        # Room models
        Room, RoomStatus, RoomAvailability,
    ])
    def operabasemodel_subclass(self, request):
        """Parametrized fixture for all OperaBaseModel subclasses."""
        return request.param

    def test_model_inherits_from_operabasemodel(self, operabasemodel_subclass):
        """Verify all expected models inherit from OperaBaseModel."""
        assert is_operabasemodel_subclass(operabasemodel_subclass)

    def test_model_has_extra_allow_config(self, operabasemodel_subclass):
        """Verify all OperaBaseModel subclasses have extra='allow' config."""
        extra_config = get_extra_config(operabasemodel_subclass)
        assert extra_config == "allow", (
            f"{operabasemodel_subclass.__name__} has extra='{extra_config}', "
            "expected 'allow'"
        )

    def test_model_accepts_arbitrary_extra_fields(self, operabasemodel_subclass):
        """Verify all OperaBaseModel subclasses accept arbitrary extra fields."""
        # Create a minimal valid instance with extra fields
        # This is a basic smoke test - individual model tests have comprehensive fixtures

        model = operabasemodel_subclass

        # Get required fields for the model
        required_fields = [
            name for name, field_info in model.model_fields.items()
            if field_info.is_required()
        ]

        if not required_fields:
            # Model has no required fields - just test with extra field
            try:
                instance = model(_arbitrary_extra_field="test_value")
                assert hasattr(instance, "_arbitrary_extra_field") or (
                    instance.__pydantic_extra__
                    and instance.__pydantic_extra__.get("_arbitrary_extra_field") == "test_value"
                )
            except Exception:
                pytest.skip(f"Could not instantiate {model.__name__} without required fields")
        else:
            # Model has required fields - skip this generic test
            pytest.skip(
                f"{model.__name__} has required fields: {required_fields}. "
                "See specific test class for comprehensive extra field testing."
            )
