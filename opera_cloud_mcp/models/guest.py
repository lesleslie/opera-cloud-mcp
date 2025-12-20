"""Guest and profile data models for OPERA Cloud MCP server.

Provides comprehensive Pydantic models for guest profiles, preferences,
loyalty programs, history tracking, and customer relationship management.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from opera_cloud_mcp.models.common import (
    Address,
    Contact,
    Money,
    OperaBaseModel,
    PaginationInfo,
)


class GenderType(str, Enum):
    """Guest gender enumeration."""

    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    NOT_SPECIFIED = "NOT_SPECIFIED"


class VIPStatus(str, Enum):
    """VIP status levels."""

    NONE = "NONE"
    VIP = "VIP"
    VVIP = "VVIP"
    CELEBRITY = "CELEBRITY"
    GOVERNMENT = "GOVERNMENT"
    CORPORATE = "CORPORATE"


class LoyaltyTier(str, Enum):
    """Loyalty program tier levels."""

    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    DIAMOND = "DIAMOND"
    ELITE = "ELITE"


class PreferenceType(str, Enum):
    """Guest preference categories."""

    ROOM_TYPE = "ROOM_TYPE"
    FLOOR = "FLOOR"
    BED_TYPE = "BED_TYPE"
    AMENITIES = "AMENITIES"
    DINING = "DINING"
    RECREATION = "RECREATION"
    TRANSPORT = "TRANSPORT"
    COMMUNICATION = "COMMUNICATION"
    ACCESSIBILITY = "ACCESSIBILITY"
    MARKETING = "MARKETING"
    PRIVACY = "PRIVACY"
    OTHER = "OTHER"


class StayStatus(str, Enum):
    """Guest stay status."""

    COMPLETED = "COMPLETED"
    IN_HOUSE = "IN_HOUSE"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    CHECKED_OUT = "CHECKED_OUT"


class ProfileStatus(str, Enum):
    """Guest profile status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MERGED = "MERGED"
    DUPLICATE = "DUPLICATE"
    BLOCKED = "BLOCKED"


class MarketingPreference(OperaBaseModel):
    """Guest marketing communication preferences."""

    email_marketing: bool = Field(True, alias="emailMarketing")
    sms_marketing: bool = Field(True, alias="smsMarketing")
    postal_marketing: bool = Field(True, alias="postalMarketing")
    phone_marketing: bool = Field(False, alias="phoneMarketing")
    partner_marketing: bool = Field(False, alias="partnerMarketing")

    # Marketing categories
    promotional_offers: bool = Field(True, alias="promotionalOffers")
    newsletter: bool = Field(True, alias="newsletter")
    event_invitations: bool = Field(True, alias="eventInvitations")
    surveys: bool = Field(False, alias="surveys")

    # Compliance tracking
    gdpr_consent: bool | None = Field(None, alias="gdprConsent")
    consent_date: datetime | None = Field(None, alias="consentDate")
    opt_out_date: datetime | None = Field(None, alias="optOutDate")


class GuestPreference(OperaBaseModel):
    """Enhanced guest preference model."""

    preference_id: str | None = Field(None, alias="preferenceId")
    preference_type: PreferenceType = Field(alias="preferenceType")
    preference_value: str = Field(alias="preferenceValue")
    preference_code: str | None = Field(None, alias="preferenceCode")
    description: str | None = None
    is_primary: bool = Field(False, alias="isPrimary")
    priority: int = Field(1, ge=1, le=10)  # 1 = highest priority
    created_date: datetime | None = Field(None, alias="createdDate")
    modified_date: datetime | None = Field(None, alias="modifiedDate")
    hotel_id: str | None = Field(None, alias="hotelId")  # Hotel-specific preferences

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        """Validate priority is between 1 and 10."""
        if v < 1 or v > 10:
            raise ValueError("Priority must be between 1 and 10")
        return v


class LoyaltyPoints(OperaBaseModel):
    """Loyalty points information."""

    current_points: int = Field(0, alias="currentPoints")
    lifetime_points: int = Field(0, alias="lifetimePoints")
    points_to_next_tier: int | None = Field(None, alias="pointsToNextTier")
    points_expiring_soon: int = Field(0, alias="pointsExpiringSoon")
    expiry_date: date | None = Field(None, alias="expiryDate")
    last_activity_date: date | None = Field(None, alias="lastActivityDate")


class LoyaltyProgram(OperaBaseModel):
    """Guest loyalty program information."""

    program_id: str = Field(alias="programId")
    program_name: str = Field(alias="programName")
    membership_number: str = Field(alias="membershipNumber")
    tier: LoyaltyTier | None = None
    tier_name: str | None = Field(None, alias="tierName")
    member_since: date | None = Field(None, alias="memberSince")
    tier_qualification_date: date | None = Field(None, alias="tierQualificationDate")
    tier_expiry_date: date | None = Field(None, alias="tierExpiryDate")

    # Points information
    points: LoyaltyPoints | None = None

    # Program benefits
    benefits: list[str] = Field(default_factory=list)

    # Status
    is_active: bool = Field(True, alias="isActive")
    enrollment_hotel: str | None = Field(None, alias="enrollmentHotel")


class GuestIdentification(OperaBaseModel):
    """Guest identification documents."""

    id_type: str = Field(alias="idType")  # PASSPORT, DRIVER_LICENSE, NATIONAL_ID, etc.
    id_number: str = Field(alias="idNumber")
    issuing_country: str | None = Field(None, alias="issuingCountry")
    issuing_authority: str | None = Field(None, alias="issuingAuthority")
    issue_date: date | None = Field(None, alias="issueDate")
    expiry_date: date | None = Field(None, alias="expiryDate")
    place_of_issue: str | None = Field(None, alias="placeOfIssue")
    is_primary: bool = Field(True, alias="isPrimary")


class GuestStayStatistics(OperaBaseModel):
    """Guest stay statistics and analytics."""

    total_stays: int = Field(0, alias="totalStays")
    total_nights: int = Field(0, alias="totalNights")
    total_revenue: Decimal = Field(Decimal("0.00"), alias="totalRevenue")
    average_daily_rate: Decimal = Field(Decimal("0.00"), alias="averageDailyRate")
    average_length_of_stay: float = Field(0.0, alias="averageLengthOfStay")

    first_stay_date: date | None = Field(None, alias="firstStayDate")
    last_stay_date: date | None = Field(None, alias="lastStayDate")

    # Hotel-specific stats
    favorite_hotel: str | None = Field(None, alias="favoriteHotel")
    favorite_room_type: str | None = Field(None, alias="favoriteRoomType")

    # Behavioral patterns
    preferred_check_in_time: str | None = Field(None, alias="preferredCheckInTime")
    preferred_check_out_time: str | None = Field(None, alias="preferredCheckOutTime")
    typical_advance_booking: int | None = Field(
        None, alias="typicalAdvanceBooking"
    )  # Days

    # Satisfaction metrics
    average_rating: float | None = Field(None, alias="averageRating")
    complaints_count: int = Field(0, alias="complaintsCount")
    compliments_count: int = Field(0, alias="complimentsCount")


class GuestStayHistory(OperaBaseModel):
    """Individual guest stay record."""

    reservation_id: str = Field(alias="reservationId")
    confirmation_number: str = Field(alias="confirmationNumber")
    hotel_id: str = Field(alias="hotelId")
    hotel_name: str | None = Field(None, alias="hotelName")

    arrival_date: date = Field(alias="arrivalDate")
    departure_date: date = Field(alias="departureDate")
    nights: int = Field(ge=1)

    room_number: str | None = Field(None, alias="roomNumber")
    room_type: str = Field(alias="roomType")
    rate_code: str = Field(alias="rateCode")

    status: StayStatus

    # Financial information
    room_revenue: Money = Field(alias="roomRevenue")
    total_revenue: Money = Field(alias="totalRevenue")

    # Guest satisfaction
    rating: int | None = Field(None, ge=1, le=5)
    review: str | None = None

    # Service records
    special_requests: list[str] = Field(default_factory=list, alias="specialRequests")
    incidents: list[str] = Field(default_factory=list)  # Issues or complaints
    compliments: list[str] = Field(default_factory=list)  # Positive feedback

    created_date: datetime = Field(alias="createdDate")
    modified_date: datetime | None = Field(None, alias="modifiedDate")


class GuestProfile(OperaBaseModel):
    """Comprehensive guest profile model."""

    # Basic identification
    guest_id: str = Field(alias="guestId")
    profile_number: str | None = Field(
        None, alias="profileNumber"
    )  # External reference

    # Personal information
    title: str | None = None
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    middle_name: str | None = Field(None, alias="middleName")
    display_name: str | None = Field(None, alias="displayName")  # Preferred name

    birth_date: date | None = Field(None, alias="birthDate")
    gender: GenderType | None = None
    nationality: str | None = None
    language: str | None = None  # Primary language code (ISO 639-1)

    # Contact information
    contact: Contact | None = None
    address: Address | None = None

    # Identification documents
    identifications: list[GuestIdentification] = Field(default_factory=list)

    # Status and classification
    status: ProfileStatus = ProfileStatus.ACTIVE
    vip_status: VIPStatus = VIPStatus.NONE

    # Loyalty program information
    loyalty_programs: list[LoyaltyProgram] = Field(
        default_factory=list, alias="loyaltyPrograms"
    )
    primary_loyalty: str | None = Field(
        None, alias="primaryLoyalty"
    )  # Primary program ID

    # Preferences
    preferences: list[GuestPreference] = Field(default_factory=list)
    marketing_preferences: MarketingPreference | None = Field(
        None, alias="marketingPreferences"
    )

    # Special requirements
    special_instructions: str | None = Field(None, alias="specialInstructions")
    accessibility_needs: list[str] = Field(
        default_factory=list, alias="accessibilityNeeds"
    )
    dietary_restrictions: list[str] = Field(
        default_factory=list, alias="dietaryRestrictions"
    )
    allergies: list[str] = Field(default_factory=list)

    # Stay statistics
    statistics: GuestStayStatistics | None = None

    # Profile management
    created_date: datetime = Field(alias="createdDate")
    created_by: str = Field(alias="createdBy")
    modified_date: datetime | None = Field(None, alias="modifiedDate")
    modified_by: str | None = Field(None, alias="modifiedBy")

    # Data privacy and compliance
    data_protection_consent: bool = Field(True, alias="dataProtectionConsent")
    consent_date: datetime | None = Field(None, alias="consentDate")

    # Merge/duplicate tracking
    master_profile_id: str | None = Field(None, alias="masterProfileId")
    merged_profiles: list[str] = Field(default_factory=list, alias="mergedProfiles")

    @field_validator("guest_id")
    @classmethod
    def validate_guest_id(cls, v):
        """Validate guest ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Guest ID cannot be empty")
        return v.strip()

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v):
        """Validate names are not empty."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip().title()

    def get_full_name(self) -> str:
        """Get formatted full name."""
        parts = [self.title, self.first_name, self.middle_name, self.last_name]
        return " ".join(part for part in parts if part)

    def get_primary_loyalty_program(self) -> LoyaltyProgram | None:
        """Get primary loyalty program."""
        if not self.loyalty_programs:
            return None

        # Return primary if specified
        if self.primary_loyalty:
            for program in self.loyalty_programs:
                if program.program_id == self.primary_loyalty:
                    return program

        # Return first active program
        for program in self.loyalty_programs:
            if program.is_active:
                return program

        return None

    def get_preferences_by_type(
        self, preference_type: PreferenceType
    ) -> list[GuestPreference]:
        """Get preferences by type, sorted by priority."""
        filtered = [p for p in self.preferences if p.preference_type == preference_type]
        return sorted(filtered, key=lambda x: x.priority)


class GuestSearchCriteria(OperaBaseModel):
    """Guest search criteria model."""

    name: str | None = None  # Fuzzy search across first, middle, last names
    first_name: str | None = Field(None, alias="firstName")
    last_name: str | None = Field(None, alias="lastName")
    email: str | None = None
    phone: str | None = None
    guest_id: str | None = Field(None, alias="guestId")
    profile_number: str | None = Field(None, alias="profileNumber")
    loyalty_number: str | None = Field(None, alias="loyaltyNumber")

    # Status filters
    status: ProfileStatus | None = None
    vip_status: VIPStatus | None = Field(None, alias="vipStatus")

    # Date range filters
    created_from: date | None = Field(None, alias="createdFrom")
    created_to: date | None = Field(None, alias="createdTo")
    last_stay_from: date | None = Field(None, alias="lastStayFrom")
    last_stay_to: date | None = Field(None, alias="lastStayTo")

    # Hotel filters
    hotel_ids: list[str] | None = Field(None, alias="hotelIds")

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100, alias="pageSize")

    # Sorting
    sort_by: str = Field("lastName", alias="sortBy")
    sort_order: str = Field("ASC", alias="sortOrder")  # ASC or DESC


class GuestSearchResult(OperaBaseModel):
    """Enhanced guest search result model."""

    guests: list[GuestProfile]
    pagination: PaginationInfo
    search_criteria: GuestSearchCriteria | None = Field(None, alias="searchCriteria")
    search_duration_ms: int | None = Field(None, alias="searchDurationMs")


class ProfileMergeConflict(OperaBaseModel):
    """Profile merge conflict information."""

    field_name: str = Field(alias="fieldName")
    source_value: Any = Field(alias="sourceValue")
    target_value: Any = Field(alias="targetValue")
    resolution: str | None = None  # 'source', 'target', 'merge', 'manual'
    resolved_value: Any | None = Field(None, alias="resolvedValue")


class ProfileMergeRequest(OperaBaseModel):
    """Request model for merging guest profiles."""

    source_profile_id: str = Field(alias="sourceProfileId")  # Profile to merge from
    target_profile_id: str = Field(alias="targetProfileId")  # Profile to merge into

    # Merge options
    preserve_history: bool = Field(True, alias="preserveHistory")
    merge_preferences: bool = Field(True, alias="mergePreferences")
    merge_loyalty: bool = Field(True, alias="mergeLoyalty")

    # Conflict resolution rules
    default_resolution: str = Field(
        "target", alias="defaultResolution"
    )  # 'source', 'target', 'manual'
    field_resolutions: dict[str, str] | None = Field(None, alias="fieldResolutions")

    # Audit information
    merge_reason: str | None = Field(None, alias="mergeReason")
    merged_by: str = Field(alias="mergedBy")


class ProfileMergeResult(OperaBaseModel):
    """Result of profile merge operation."""

    success: bool
    merged_profile_id: str | None = Field(None, alias="mergedProfileId")
    conflicts: list[ProfileMergeConflict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    # Statistics
    fields_merged: int = Field(0, alias="fieldsMerged")
    conflicts_resolved: int = Field(0, alias="conflictsResolved")
    manual_resolution_required: int = Field(0, alias="manualResolutionRequired")

    merge_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC), alias="mergeDate"
    )
    processing_time_ms: int | None = Field(None, alias="processingTimeMs")
