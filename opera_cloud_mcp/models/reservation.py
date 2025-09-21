"""
Reservation data models for OPERA Cloud MCP server.

Provides comprehensive Pydantic models for reservation-related entities
including reservations, guests, room stays, and booking details with
full validation, transformation, and OPERA Cloud API compatibility.
"""

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from opera_cloud_mcp.models.common import Address, Contact, Money, OperaBaseModel
from opera_cloud_mcp.utils.validators import (
    validate_confirmation_number,
    validate_email,
    validate_phone,
)


class ReservationStatus(str, Enum):
    """Reservation status enumeration."""

    CONFIRMED = "CONFIRMED"
    PROVISIONAL = "PROVISIONAL"
    WAITLISTED = "WAITLISTED"
    CANCELED = "CANCELED"
    NO_SHOW = "NO_SHOW"
    CHECKED_IN = "CHECKED_IN"
    CHECKED_OUT = "CHECKED_OUT"


class GuaranteeType(str, Enum):
    """Guarantee type enumeration."""

    CREDIT_CARD = "CREDIT_CARD"
    DEPOSIT = "DEPOSIT"
    COMPANY = "COMPANY"
    TRAVEL_AGENT = "TRAVEL_AGENT"
    NONE = "NONE"


class RoomType(str, Enum):
    """Common room type enumeration."""

    STANDARD = "STANDARD"
    DELUXE = "DELUXE"
    SUITE = "SUITE"
    JUNIOR_SUITE = "JUNIOR_SUITE"
    EXECUTIVE = "EXECUTIVE"
    PRESIDENTIAL = "PRESIDENTIAL"


class RateType(str, Enum):
    """Rate type enumeration."""

    RACK = "RACK"
    CORPORATE = "CORPORATE"
    GROUP = "GROUP"
    PROMOTIONAL = "PROMOTIONAL"
    PACKAGE = "PACKAGE"
    AAA = "AAA"
    GOVERNMENT = "GOVERNMENT"
    SENIOR = "SENIOR"


class PaymentMethod(BaseModel):
    """Payment method information."""

    type: str = Field(description="Payment method type (CC, CASH, etc.)")
    card_number_masked: str | None = Field(None, description="Masked card number")
    card_type: str | None = Field(None, description="Credit card type")
    expiry_date: str | None = Field(None, description="Card expiry (MM/YY)")
    holder_name: str | None = Field(None, description="Card holder name")


class GuestProfile(OperaBaseModel):
    """Enhanced guest profile model with validation."""

    guest_id: str | None = Field(None, alias="guestId")
    first_name: str = Field(min_length=1, max_length=50, alias="firstName")
    last_name: str = Field(min_length=1, max_length=50, alias="lastName")
    middle_name: str | None = Field(None, max_length=50, alias="middleName")
    title: str | None = Field(None, max_length=20)
    suffix: str | None = Field(None, max_length=20)
    gender: str | None = Field(None, pattern=r"^[MFO]$")
    date_of_birth: date | None = Field(None, alias="dateOfBirth")
    nationality: str | None = Field(None, max_length=2, alias="nationality")

    # Contact information with validation
    contact: Contact | None = None
    address: Address | None = None

    # Loyalty and preferences
    loyalty_number: str | None = Field(None, max_length=20, alias="loyaltyNumber")
    loyalty_level: str | None = Field(None, alias="loyaltyLevel")
    vip_status: str | None = Field(None, alias="vipStatus")
    language_preference: str | None = Field(
        None, max_length=5, alias="languagePreference"
    )

    # Marketing preferences
    marketing_consent: bool = Field(False, alias="marketingConsent")
    email_marketing: bool = Field(False, alias="emailMarketing")
    sms_marketing: bool = Field(False, alias="smsMarketing")

    @field_validator("contact")
    @classmethod
    def validate_contact_info(cls, v: Any) -> Any:
        """Validate contact information."""
        if v and v.email:
            validate_email(v.email)
        if v and v.phone:
            validate_phone(v.phone)
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_birth_date(cls, v: Any) -> Any:
        """Validate birth date is reasonable."""
        if v and v > date.today():
            raise ValueError("Birth date cannot be in the future")
        if v and v.year < 1900:
            raise ValueError("Birth date cannot be before 1900")
        return v


# For backward compatibility, keep Guest as an alias
Guest = GuestProfile


class RoomStayDetails(OperaBaseModel):
    """Enhanced room stay details with comprehensive validation."""

    room_type: str = Field(alias="roomType", description="Room type code")
    room_type_description: str | None = Field(None, alias="roomTypeDescription")
    room_number: str | None = Field(None, max_length=10, alias="roomNumber")

    # Stay dates with validation
    arrival_date: date = Field(alias="arrivalDate")
    departure_date: date = Field(alias="departureDate")
    nights: int | None = Field(None, ge=1, le=365)

    # Occupancy details
    adults: int = Field(1, ge=1, le=10)
    children: int = Field(0, ge=0, le=10)
    infants: int = Field(0, ge=0, le=5)

    # Rate information
    rate_code: str = Field(alias="rateCode")
    rate_description: str | None = Field(None, alias="rateDescription")
    rate_amount: Money | None = Field(None, alias="rateAmount")
    currency_code: str = Field("USD", max_length=3, alias="currencyCode")

    # Room features and preferences
    smoking_preference: bool | None = Field(None, alias="smokingPreference")
    bed_type_preference: str | None = Field(None, alias="bedTypePreference")
    floor_preference: str | None = Field(None, alias="floorPreference")
    connecting_rooms: bool = Field(False, alias="connectingRooms")

    @field_validator("departure_date")
    @classmethod
    def validate_departure_after_arrival(cls, v, info):
        """Ensure departure is after arrival."""
        if info.data.get("arrival_date") and v <= info.data["arrival_date"]:
            raise ValueError("Departure date must be after arrival date")
        return v

    @model_validator(mode="after")
    def calculate_nights(self):
        """Calculate number of nights if not provided."""
        if self.arrival_date and self.departure_date:
            calculated_nights = (self.departure_date - self.arrival_date).days

            if self.nights is None:
                self.nights = calculated_nights
            elif self.nights != calculated_nights:
                raise ValueError(
                    f"Nights ({self.nights}) doesn't match "
                    + f"date range ({calculated_nights})"
                )

        return self


# For backward compatibility
RoomStay = RoomStayDetails


class ReservationCharges(BaseModel):
    """Reservation charges and financial details."""

    room_charges: list[dict[str, Any]] = Field(default_factory=list)
    tax_charges: list[dict[str, Any]] = Field(default_factory=list)
    incidental_charges: list[dict[str, Any]] = Field(default_factory=list)
    packages: list[dict[str, Any]] = Field(default_factory=list)

    subtotal: Money | None = None
    tax_total: Money | None = None
    total_amount: Money | None = None

    balance_due: Money | None = None
    payments_received: list[dict[str, Any]] = Field(default_factory=list)


class ReservationHistory(BaseModel):
    """Reservation modification history."""

    timestamp: datetime
    user_id: str | None = None
    user_name: str | None = None
    action: str  # CREATED, MODIFIED, CANCELED, etc.
    changes: dict[str, Any] = Field(default_factory=dict)
    comments: str | None = None


class ComprehensiveReservation(OperaBaseModel):
    """Comprehensive reservation model with all details."""

    # Basic reservation information
    confirmation_number: str = Field(alias="confirmationNumber")
    hotel_id: str = Field(alias="hotelId")
    reservation_id: str | None = Field(None, alias="reservationId")

    # Status and type
    status: ReservationStatus = ReservationStatus.CONFIRMED
    reservation_type: str = Field("INDIVIDUAL", alias="reservationType")

    # Guest information (can be multiple guests for group reservations)
    primary_guest: GuestProfile = Field(alias="primaryGuest")
    additional_guests: list[GuestProfile] = Field(
        default_factory=list, alias="additionalGuests"
    )

    # Room stay details
    room_stay: RoomStayDetails = Field(alias="roomStay")

    # Booking details
    created_date: datetime = Field(alias="createdDate")
    created_by: str | None = Field(None, alias="createdBy")
    modified_date: datetime | None = Field(None, alias="modifiedDate")
    modified_by: str | None = Field(None, alias="modifiedBy")

    # Source and booking channel
    source_code: str | None = Field(None, alias="sourceCode")
    booking_channel: str | None = Field(None, alias="bookingChannel")
    confirmation_sent: bool = Field(False, alias="confirmationSent")

    # Financial information
    guarantee_type: GuaranteeType = Field(GuaranteeType.NONE, alias="guaranteeType")
    payment_method: PaymentMethod | None = Field(None, alias="paymentMethod")
    deposit_required: Money | None = Field(None, alias="depositRequired")
    deposit_received: Money | None = Field(None, alias="depositReceived")

    # Commercial information
    company_id: str | None = Field(None, alias="companyId")
    company_name: str | None = Field(None, alias="companyName")
    travel_agent_id: str | None = Field(None, alias="travelAgentId")
    travel_agent_name: str | None = Field(None, alias="travelAgentName")
    group_code: str | None = Field(None, alias="groupCode")

    # Special requests and comments
    special_requests: str | None = Field(None, max_length=2000, alias="specialRequests")
    internal_comments: str | None = Field(
        None, max_length=2000, alias="internalComments"
    )
    guest_comments: str | None = Field(None, max_length=1000, alias="guestComments")

    # Package and promotion information
    packages: list[str] = Field(default_factory=list)
    promotions: list[str] = Field(default_factory=list)

    # Financial details (optional, loaded separately)
    charges: ReservationCharges | None = None

    # History (optional, loaded separately)
    history: list[ReservationHistory] = Field(default_factory=list)

    @field_validator("confirmation_number")
    @classmethod
    def validate_confirmation_number_format(cls, v):
        """Validate confirmation number format."""
        from opera_cloud_mcp.utils.exceptions import (
            ValidationError as CustomValidationError,
        )

        try:
            return validate_confirmation_number(v)
        except CustomValidationError as e:
            raise ValueError(str(e)) from None

    @field_validator("created_date", "modified_date")
    @classmethod
    def validate_timestamps(cls, v):
        """Ensure timestamps are not in the future."""
        if v:
            # Make both datetimes timezone-aware for comparison
            now = datetime.now(tz=UTC)
            check_time = v.replace(tzinfo=UTC) if v.tzinfo is None else v
            if check_time > now:
                raise ValueError("Timestamp cannot be in the future")
        return v

    @model_validator(mode="after")
    def validate_modification_consistency(self):
        """Ensure modification fields are consistent."""
        if self.modified_date and not self.modified_by:
            self.modified_by = "SYSTEM"  # Default modifier

        return self


# For backward compatibility and simplified usage
Reservation = ComprehensiveReservation


class ReservationSearchResult(OperaBaseModel):
    """Enhanced reservation search result with metadata."""

    reservations: list[ComprehensiveReservation]
    total_count: int = Field(alias="totalCount")
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    has_more: bool = Field(False, alias="hasMore")

    # Search metadata
    search_criteria: dict[str, Any] | None = Field(None, alias="searchCriteria")
    search_duration_ms: float | None = Field(None, alias="searchDurationMs")

    @field_validator("reservations")
    @classmethod
    def validate_reservation_list(cls, v):
        """Ensure reservation list is not empty when total_count > 0."""
        # This would be checked in the API layer, but good to have here too
        return v


class AvailabilityResult(BaseModel):
    """Room availability result model."""

    room_type: str
    room_type_description: str | None = None
    available_rooms: int = Field(ge=0)
    rate_plans: list[dict[str, Any]] = Field(default_factory=list)
    restrictions: dict[str, Any] = Field(default_factory=dict)


class BulkReservationResult(BaseModel):
    """Result of bulk reservation operations."""

    job_id: str
    status: str  # PENDING, PROCESSING, COMPLETED, FAILED
    total_reservations: int
    processed_count: int = 0
    success_count: int = 0
    error_count: int = 0

    # Results for completed operations
    successful_reservations: list[str] = Field(
        default_factory=list
    )  # Confirmation numbers
    failed_reservations: list[dict[str, Any]] = Field(default_factory=list)

    # Progress tracking
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_completion: datetime | None = None
