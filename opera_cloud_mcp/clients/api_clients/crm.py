"""
CRM API client for OPERA Cloud.

Handles comprehensive customer relationship management including guest profiles,
preferences, history tracking, loyalty programs, and profile merging through
the OPERA Cloud CRM API.
"""

import logging
from contextlib import suppress
from datetime import UTC, date, datetime
from typing import Any

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.models.guest import (
    GuestSearchCriteria,
    ProfileStatus,
    VIPStatus,
)
from opera_cloud_mcp.utils.exceptions import ResourceNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class CRMClient(BaseAPIClient):
    """
    Comprehensive client for OPERA Cloud CRM API.

    Provides methods for guest profile management, preference handling,
    loyalty program integration, stay history tracking, and profile merging
    with conflict resolution capabilities.
    """

    async def search_guests(
        self,
        criteria: GuestSearchCriteria | None = None,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        guest_id: str | None = None,
        loyalty_number: str | None = None,
        vip_status: VIPStatus | None = None,
        status: ProfileStatus | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "lastName",
        sort_order: str = "ASC",
    ) -> APIResponse:
        """
        Search guest profiles with comprehensive filtering options.

        Args:
            criteria: Structured search criteria object
            name: Fuzzy search across first, middle, last names
            email: Guest email address
            phone: Guest phone number
            guest_id: Specific guest ID
            loyalty_number: Loyalty program membership number
            vip_status: VIP status filter
            status: Profile status filter
            page: Page number (1-based)
            page_size: Number of results per page (1-100)
            sort_by: Field to sort by
            sort_order: Sort direction (ASC/DESC)

        Returns:
            APIResponse containing GuestSearchResult with pagination
        """
        logger.info(
            "Searching guests with criteria",
            extra={
                "hotel_id": self.hotel_id,
                "name": name,
                "email": email,
                "page": page,
                "page_size": page_size,
            },
        )

        # Build search parameters
        params = {
            "page": page,
            "pageSize": page_size,
            "sortBy": sort_by,
            "sortOrder": sort_order.upper(),
        }

        # Use structured criteria if provided, otherwise build from
        # individual parameters
        search_data = self._build_search_data(
            criteria, name, email, phone, guest_id, loyalty_number, vip_status, status
        )

        # Add search criteria to request body
        request_data = {
            "searchCriteria": search_data,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "sortBy": sort_by,
                "sortOrder": sort_order.upper(),
            },
        }

        return await self.post(
            "crm/v1/guests/search",
            json_data=request_data,
            params=params,
            data_transformations={
                "guests": self._transform_guest_profiles,
                "pagination.totalCount": int,
                "searchDurationMs": int,
            },
        )

    async def get_guest_profile(
        self,
        guest_id: str,
        include_statistics: bool = True,
        include_history: bool = False,
        include_preferences: bool = True,
        include_loyalty: bool = True,
    ) -> APIResponse:
        """
        Get comprehensive guest profile details.

        Args:
            guest_id: Guest identifier
            include_statistics: Include stay statistics
            include_history: Include stay history
            include_preferences: Include guest preferences
            include_loyalty: Include loyalty program information

        Returns:
            APIResponse containing GuestProfile

        Raises:
            ResourceNotFoundError: If guest profile not found
        """
        logger.info(
            "Retrieving guest profile",
            extra={
                "hotel_id": self.hotel_id,
                "guest_id": guest_id,
                "include_statistics": include_statistics,
                "include_history": include_history,
            },
        )

        params = {
            "includeStatistics": include_statistics,
            "includeHistory": include_history,
            "includePreferences": include_preferences,
            "includeLoyalty": include_loyalty,
        }

        try:
            return await self.get(
                f"crm/v1/guests/{guest_id}",
                params=params,
                data_transformations={
                    "guestProfile": self._transform_guest_profile,
                    "statistics": self._transform_guest_statistics,
                    "loyaltyPrograms": self._transform_loyalty_programs,
                },
            )
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise ResourceNotFoundError(
                    f"Guest profile not found: {guest_id}"
                ) from e
            raise

    def _validate_guest_profile_fields(self, first_name: str, last_name: str) -> None:
        """Validate required fields for guest profile creation."""
        if not first_name or not first_name.strip():
            raise ValidationError("First name is required")
        if not last_name or not last_name.strip():
            raise ValidationError("Last name is required")

    def _build_contact_info(
        self, email: str | None, phone: str | None
    ) -> dict[str, Any] | None:
        """Build contact information dictionary."""
        contact_info = {}
        if email:
            contact_info["email"] = email
        if phone:
            contact_info["phone"] = phone
        return contact_info if contact_info else None

    def _build_search_data_from_criteria(
        self,
        criteria: GuestSearchCriteria | None,
    ) -> dict[str, Any]:
        """Build search data from structured criteria."""
        if criteria:
            return criteria.model_dump(exclude_none=True, by_alias=True)
        return {}

    def _build_search_data_from_individual_params(
        self,
        name: str | None,
        email: str | None,
        phone: str | None,
        guest_id: str | None,
        loyalty_number: str | None,
        vip_status: VIPStatus | None,
        status: ProfileStatus | None,
    ) -> dict[str, Any]:
        """Build search data from individual parameters."""
        search_data = {}
        if name:
            search_data["name"] = name
        if email:
            search_data["email"] = email
        if phone:
            search_data["phone"] = phone
        if guest_id:
            search_data["guestId"] = guest_id
        if loyalty_number:
            search_data["loyaltyNumber"] = loyalty_number
        if vip_status:
            search_data["vipStatus"] = vip_status.value
        if status:
            search_data["status"] = status.value
        return search_data

    def _build_search_data(
        self,
        criteria: GuestSearchCriteria | None,
        name: str | None,
        email: str | None,
        phone: str | None,
        guest_id: str | None,
        loyalty_number: str | None,
        vip_status: VIPStatus | None,
        status: ProfileStatus | None,
    ) -> dict[str, Any]:
        """Build search data from criteria or individual parameters."""
        if criteria:
            return self._build_search_data_from_criteria(criteria)
        else:
            return self._build_search_data_from_individual_params(
                name, email, phone, guest_id, loyalty_number, vip_status, status
            )

    def _build_guest_profile_data(
        self,
        first_name: str,
        last_name: str,
        contact_info: dict[str, Any] | None,
        address: dict[str, Any] | None,
        birth_date: date | None,
        gender: str | None,
        nationality: str | None,
        language: str | None,
        vip_status: VIPStatus | None,
        preferences: list[dict[str, Any]] | None,
        marketing_preferences: dict[str, Any] | None,
        special_instructions: str | None,
    ) -> dict[str, Any]:
        """Build the guest profile data dictionary."""
        guest_data: dict[str, Any] = {
            "firstName": first_name.strip().title(),
            "lastName": last_name.strip().title(),
            "status": ProfileStatus.ACTIVE.value,
            "createdDate": datetime.now(tz=UTC).isoformat(),
            "createdBy": "system",  # This would come from auth context
            "dataProtectionConsent": True,
            "consentDate": datetime.now(tz=UTC).isoformat(),
        }

        if contact_info:
            guest_data["contact"] = contact_info

        if address:
            guest_data["address"] = address

        if birth_date:
            guest_data["birthDate"] = birth_date.isoformat()

        if gender:
            guest_data["gender"] = gender

        if nationality:
            guest_data["nationality"] = nationality

        if language:
            guest_data["language"] = language

        if vip_status:
            guest_data["vipStatus"] = vip_status.value

        if preferences:
            guest_data["preferences"] = preferences

        if marketing_preferences:
            guest_data["marketingPreferences"] = marketing_preferences

        if special_instructions:
            guest_data["specialInstructions"] = special_instructions

        return guest_data

    async def create_guest_profile(
        self,
        first_name: str,
        last_name: str,
        email: str | None = None,
        phone: str | None = None,
        address: dict[str, Any] | None = None,
        birth_date: date | None = None,
        gender: str | None = None,
        nationality: str | None = None,
        language: str | None = None,
        vip_status: VIPStatus | None = None,
        preferences: list[dict[str, Any]] | None = None,
        marketing_preferences: dict[str, Any] | None = None,
        special_instructions: str | None = None,
    ) -> APIResponse:
        """
        Create a new guest profile.

        Args:
            first_name: Guest first name (required)
            last_name: Guest last name (required)
            email: Guest email address
            phone: Guest phone number
            address: Guest address information
            birth_date: Guest birth date
            gender: Guest gender
            nationality: Guest nationality
            language: Primary language code
            vip_status: VIP status level
            preferences: List of guest preferences
            marketing_preferences: Marketing communication preferences
            special_instructions: Special handling instructions

        Returns:
            APIResponse containing created GuestProfile

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        logger.info(
            "Creating guest profile",
            extra={
                "hotel_id": self.hotel_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },
        )

        # Validate required fields
        self._validate_guest_profile_fields(first_name, last_name)

        # Build contact information
        contact_info = self._build_contact_info(email, phone)

        # Build guest profile data
        guest_data = self._build_guest_profile_data(
            first_name,
            last_name,
            contact_info,
            address,
            birth_date,
            gender,
            nationality,
            language,
            vip_status,
            preferences,
            marketing_preferences,
            special_instructions,
        )

        return await self.post(
            "crm/v1/guests",
            json_data={"guestProfile": guest_data},
            data_transformations={
                "guestProfile": self._transform_guest_profile,
            },
        )

    async def update_guest_profile(
        self,
        guest_id: str,
        updates: dict[str, Any],
        merge_preferences: bool = True,
        preserve_history: bool = True,
    ) -> APIResponse:
        """
        Update guest profile with comprehensive field support.

        Args:
            guest_id: Guest identifier
            updates: Profile updates to apply
            merge_preferences: Whether to merge or replace preferences
            preserve_history: Whether to preserve existing history

        Returns:
            APIResponse containing updated GuestProfile

        Raises:
            ResourceNotFoundError: If guest profile not found
            ValidationError: If updates are invalid
        """
        logger.info(
            "Updating guest profile",
            extra={
                "hotel_id": self.hotel_id,
                "guest_id": guest_id,
                "update_fields": list(updates.keys()),
                "merge_preferences": merge_preferences,
            },
        )

        # Validate guest exists first
        await self.get_guest_profile(
            guest_id, include_statistics=False, include_history=False
        )

        # Add metadata to updates
        update_data = updates.copy()
        update_data.update(
            {
                "modifiedDate": datetime.now(tz=UTC).isoformat(),
                "modifiedBy": "system",  # This would come from auth context
            }
        )

        params = {
            "mergePreferences": merge_preferences,
            "preserveHistory": preserve_history,
        }

        return await self.put(
            f"crm/v1/guests/{guest_id}",
            json_data={"guestProfile": update_data},
            params=params,
            data_transformations={
                "guestProfile": self._transform_guest_profile,
            },
        )

    async def get_guest_history(
        self,
        guest_id: str,
        hotel_ids: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        status: str | None = None,
        include_statistics: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> APIResponse:
        """
        Get guest stay history with filtering and analytics.

        Args:
            guest_id: Guest identifier
            hotel_ids: Filter by specific hotels
            from_date: Start date for history range
            to_date: End date for history range
            status: Filter by stay status
            include_statistics: Include stay statistics summary
            page: Page number for pagination
            page_size: Results per page

        Returns:
            APIResponse containing stay history and statistics
        """
        logger.info(
            "Retrieving guest history",
            extra={
                "hotel_id": self.hotel_id,
                "guest_id": guest_id,
                "from_date": from_date,
                "to_date": to_date,
                "include_statistics": include_statistics,
            },
        )

        params: dict[str, str | int | bool] = {
            "page": page,
            "pageSize": page_size,
            "includeStatistics": include_statistics,
        }

        if hotel_ids:
            params["hotelIds"] = ",".join(hotel_ids)

        if from_date:
            params["fromDate"] = from_date.isoformat()

        if to_date:
            params["toDate"] = to_date.isoformat()

        if status:
            params["status"] = status

        return await self.get(
            f"crm/v1/guests/{guest_id}/history",
            params=params,
            data_transformations={
                "stays": self._transform_stay_history,
                "statistics": self._transform_guest_statistics,
                "pagination.totalCount": int,
            },
        )

    async def merge_guest_profiles(
        self,
        primary_guest_id: str,
        duplicate_guest_id: str,
        merge_options: dict[str, Any] | None = None,
    ) -> APIResponse:
        """
        Merge guest profiles with the specified options.

        Args:
            primary_guest_id: ID of the profile to keep as primary
            duplicate_guest_id: ID of the profile to merge and remove
            merge_options: Options for how to handle the merge

        Returns:
            APIResponse containing merge result

        Raises:
            ValidationError: If merge request is invalid
            ResourceNotFoundError: If source or target profile not found
        """
        logger.info(
            "Merging guest profiles",
            extra={
                "hotel_id": self.hotel_id,
                "primary_guest_id": primary_guest_id,
                "duplicate_guest_id": duplicate_guest_id,
                "merge_options": merge_options,
            },
        )

        # Validate profiles exist
        await self.get_guest_profile(
            primary_guest_id,
            include_statistics=False,
            include_history=False,
        )
        await self.get_guest_profile(
            duplicate_guest_id,
            include_statistics=False,
            include_history=False,
        )

        merge_data = {
            "primaryGuestId": primary_guest_id,
            "duplicateGuestId": duplicate_guest_id,
            "mergeOptions": merge_options or {},
        }

        return await self.post(
            "crm/v1/guests/merge",
            json_data=merge_data,
            data_transformations={
                "mergeResult": self._transform_merge_result,
                "conflicts": self._transform_merge_conflicts,
                "processingTimeMs": int,
            },
        )

    async def get_loyalty_programs(
        self,
        guest_id: str,
        include_points: bool = True,
        include_benefits: bool = True,
    ) -> APIResponse:
        """
        Get guest loyalty program information.

        Args:
            guest_id: Guest identifier
            include_points: Include current points information
            include_benefits: Include program benefits

        Returns:
            APIResponse containing loyalty programs
        """
        params = {
            "includePoints": include_points,
            "includeBenefits": include_benefits,
        }

        return await self.get(
            f"crm/v1/guests/{guest_id}/loyalty",
            params=params,
            data_transformations={
                "loyaltyPrograms": self._transform_loyalty_programs,
            },
        )

    async def update_loyalty_points(
        self,
        guest_id: str,
        program_id: str,
        points_adjustment: int,
        transaction_type: str,
        description: str | None = None,
        reference_id: str | None = None,
    ) -> APIResponse:
        """
        Update guest loyalty points.

        Args:
            guest_id: Guest identifier
            program_id: Loyalty program identifier
            points_adjustment: Points to add/subtract (can be negative)
            transaction_type: Type of transaction (EARN, REDEEM, ADJUST, EXPIRE)
            description: Transaction description
            reference_id: External reference ID

        Returns:
            APIResponse containing updated loyalty information
        """
        logger.info(
            "Updating loyalty points",
            extra={
                "hotel_id": self.hotel_id,
                "guest_id": guest_id,
                "program_id": program_id,
                "points_adjustment": points_adjustment,
                "transaction_type": transaction_type,
            },
        )

        transaction_data = {
            "programId": program_id,
            "pointsAdjustment": points_adjustment,
            "transactionType": transaction_type,
            "transactionDate": datetime.now(tz=UTC).isoformat(),
            "processedBy": "system",  # This would come from auth context
        }

        if description:
            transaction_data["description"] = description

        if reference_id:
            transaction_data["referenceId"] = reference_id

        return await self.post(
            f"crm/v1/guests/{guest_id}/loyalty/points",
            json_data={"pointsTransaction": transaction_data},
            data_transformations={
                "loyaltyProgram": self._transform_loyalty_program,
                "transaction": self._transform_points_transaction,
            },
        )

    async def get_guest_preferences(
        self,
        guest_id: str,
        preference_type: str | None = None,
        hotel_specific: bool = False,
    ) -> APIResponse:
        """
        Get guest preferences with filtering options.

        Args:
            guest_id: Guest identifier
            preference_type: Filter by preference type
            hotel_specific: Include only hotel-specific preferences

        Returns:
            APIResponse containing guest preferences
        """
        params = {}

        if preference_type:
            params["preferenceType"] = preference_type

        if hotel_specific:
            params["hotelSpecific"] = "true"

        return await self.get(
            f"crm/v1/guests/{guest_id}/preferences",
            params=params,
            data_transformations={
                "preferences": self._transform_guest_preferences,
            },
        )

    async def update_guest_preferences(
        self,
        guest_id: str,
        preferences: list[dict[str, Any]],
        merge_mode: str = "merge",
    ) -> APIResponse:
        """
        Update guest preferences.

        Args:
            guest_id: Guest identifier
            preferences: List of preferences to update
            merge_mode: How to handle existing preferences ('merge', 'replace')

        Returns:
            APIResponse containing updated preferences
        """
        logger.info(
            "Updating guest preferences",
            extra={
                "hotel_id": self.hotel_id,
                "guest_id": guest_id,
                "preference_count": len(preferences),
                "merge_mode": merge_mode,
            },
        )

        request_data = {
            "preferences": preferences,
            "mergeMode": merge_mode,
            "modifiedDate": datetime.now(tz=UTC).isoformat(),
            "modifiedBy": "system",  # This would come from auth context
        }

        return await self.put(
            f"crm/v1/guests/{guest_id}/preferences",
            json_data=request_data,
            data_transformations={
                "preferences": self._transform_guest_preferences,
            },
        )

    async def update_marketing_preferences(
        self,
        guest_id: str,
        marketing_preferences: dict[str, Any],
    ) -> APIResponse:
        """
        Update guest marketing communication preferences.

        Args:
            guest_id: Guest identifier
            marketing_preferences: Marketing preference settings

        Returns:
            APIResponse containing updated marketing preferences
        """
        logger.info(
            "Updating marketing preferences",
            extra={
                "hotel_id": self.hotel_id,
                "guest_id": guest_id,
                "preferences": list(marketing_preferences.keys()),
            },
        )

        # Add compliance tracking
        preference_data = marketing_preferences.copy()
        preference_data.update(
            {
                "consentDate": datetime.now(tz=UTC).isoformat(),
                "modifiedDate": datetime.now(tz=UTC).isoformat(),
            }
        )

        return await self.put(
            f"crm/v1/guests/{guest_id}/marketing-preferences",
            json_data={"marketingPreferences": preference_data},
            data_transformations={
                "marketingPreferences": self._transform_marketing_preferences,
            },
        )

    async def get_guest_stay_history(
        self,
        guest_id: str,
        history_params: dict[str, Any] | None = None,
    ) -> APIResponse:
        """
        Get guest stay history with filtering parameters.

        Args:
            guest_id: Guest identifier
            history_params: Optional filtering parameters

        Returns:
            APIResponse containing stay history
        """
        logger.info(
            "Retrieving guest stay history",
            extra={
                "hotel_id": self.hotel_id,
                "guest_id": guest_id,
                "history_params": history_params,
            },
        )

        params = history_params or {}

        return await self.get(
            f"crm/v1/guests/{guest_id}/stays",
            params=params,
            data_transformations={
                "stays": self._transform_stay_history,
                "total_count": int,
            },
        )

    async def get_guest_loyalty_info(
        self,
        guest_id: str,
    ) -> APIResponse:
        """
        Get guest loyalty program information.

        Args:
            guest_id: Guest identifier

        Returns:
            APIResponse containing loyalty information
        """
        logger.info(
            "Retrieving guest loyalty info",
            extra={
                "hotel_id": self.hotel_id,
                "guest_id": guest_id,
            },
        )

        return await self.get(
            f"crm/v1/guests/{guest_id}/loyalty-info",
            data_transformations={
                "loyaltyPrograms": self._transform_loyalty_programs,
            },
        )

    # Data transformation methods

    def _transform_guest_profiles(
        self, profiles_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform guest profile data from API response."""
        return [self._transform_guest_profile(profile) for profile in profiles_data]

    def _transform_guest_profile(self, profile_data: dict[str, Any]) -> dict[str, Any]:
        """Transform individual guest profile data."""
        # Convert date strings to proper format
        if "birthDate" in profile_data and profile_data["birthDate"]:
            profile_data["birthDate"] = self._parse_date(profile_data["birthDate"])

        if "createdDate" in profile_data and profile_data["createdDate"]:
            profile_data["createdDate"] = self._parse_datetime(
                profile_data["createdDate"]
            )

        if "modifiedDate" in profile_data and profile_data["modifiedDate"]:
            profile_data["modifiedDate"] = self._parse_datetime(
                profile_data["modifiedDate"]
            )

        # Transform nested objects
        if "loyaltyPrograms" in profile_data:
            profile_data["loyaltyPrograms"] = self._transform_loyalty_programs(
                profile_data["loyaltyPrograms"]
            )

        if "preferences" in profile_data:
            profile_data["preferences"] = self._transform_guest_preferences(
                profile_data["preferences"]
            )

        if "statistics" in profile_data:
            profile_data["statistics"] = self._transform_guest_statistics(
                profile_data["statistics"]
            )

        return profile_data

    def _transform_loyalty_programs(
        self, programs_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform loyalty programs data."""
        return [self._transform_loyalty_program(program) for program in programs_data]

    def _transform_loyalty_program(
        self, program_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform individual loyalty program data."""
        # Convert date strings
        date_fields = ["memberSince", "tierQualificationDate", "tierExpiryDate"]
        for field in date_fields:
            if field in program_data and program_data[field]:
                program_data[field] = self._parse_date(program_data[field])

        # Transform points data
        if "points" in program_data and program_data["points"]:
            points_data = program_data["points"]
            if "expiryDate" in points_data and points_data["expiryDate"]:
                points_data["expiryDate"] = self._parse_date(points_data["expiryDate"])
            if "lastActivityDate" in points_data and points_data["lastActivityDate"]:
                points_data["lastActivityDate"] = self._parse_date(
                    points_data["lastActivityDate"]
                )

        return program_data

    def _transform_guest_preferences(
        self, preferences_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform guest preferences data."""
        for preference in preferences_data:
            if "createdDate" in preference and preference["createdDate"]:
                preference["createdDate"] = self._parse_datetime(
                    preference["createdDate"]
                )
            if "modifiedDate" in preference and preference["modifiedDate"]:
                preference["modifiedDate"] = self._parse_datetime(
                    preference["modifiedDate"]
                )

        return preferences_data

    def _transform_guest_statistics(self, stats_data: dict[str, Any]) -> dict[str, Any]:
        """Transform guest statistics data."""
        # Convert date strings
        date_fields = ["firstStayDate", "lastStayDate"]
        for field in date_fields:
            if field in stats_data and stats_data[field]:
                stats_data[field] = self._parse_date(stats_data[field])

        # Convert numeric fields
        numeric_fields = ["totalRevenue", "averageDailyRate"]
        for field in numeric_fields:
            if field in stats_data and stats_data[field] is not None:
                with suppress(ValueError, TypeError):
                    from decimal import Decimal

                    stats_data[field] = Decimal(str(stats_data[field]))

        return stats_data

    def _transform_stay_history(
        self, history_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform stay history data."""
        for stay in history_data:
            # Convert dates
            date_fields = ["arrivalDate", "departureDate"]
            for field in date_fields:
                if field in stay and stay[field]:
                    stay[field] = self._parse_date(stay[field])

            # Convert timestamps
            if "createdDate" in stay and stay["createdDate"]:
                stay["createdDate"] = self._parse_datetime(stay["createdDate"])
            if "modifiedDate" in stay and stay["modifiedDate"]:
                stay["modifiedDate"] = self._parse_datetime(stay["modifiedDate"])

        return history_data

    def _transform_marketing_preferences(
        self, prefs_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform marketing preferences data."""
        # Convert timestamps
        timestamp_fields = ["consentDate", "optOutDate"]
        for field in timestamp_fields:
            if field in prefs_data and prefs_data[field]:
                prefs_data[field] = self._parse_datetime(prefs_data[field])

        return prefs_data

    def _transform_merge_result(self, result_data: dict[str, Any]) -> dict[str, Any]:
        """Transform profile merge result data."""
        if "mergeDate" in result_data and result_data["mergeDate"]:
            result_data["mergeDate"] = self._parse_datetime(result_data["mergeDate"])

        return result_data

    def _transform_merge_conflicts(
        self, conflicts_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform merge conflicts data."""
        return conflicts_data  # No special transformation needed

    def _transform_points_transaction(
        self, transaction_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform loyalty points transaction data."""
        if (
            "transactionDate" in transaction_data
            and transaction_data["transactionDate"]
        ):
            transaction_data["transactionDate"] = self._parse_datetime(
                transaction_data["transactionDate"]
            )

        return transaction_data

    # Utility methods

    def _parse_date(self, date_string: str) -> str:
        """Parse date string and return in ISO format."""
        try:
            if isinstance(date_string, str):
                from dateutil import parser

                parsed_date = parser.parse(date_string).date()
                return parsed_date.isoformat()
        except Exception as e:
            logger.warning(f"Failed to parse date string: {e}")
        return date_string

    def _parse_datetime(self, datetime_string: str) -> str:
        """Parse datetime string and return in ISO format."""
        try:
            if isinstance(datetime_string, str):
                from dateutil import parser

                parsed_datetime = parser.parse(datetime_string)
                return parsed_datetime.isoformat()
        except Exception as e:
            logger.warning(f"Failed to parse datetime string: {e}")
        return datetime_string
