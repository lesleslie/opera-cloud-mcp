"""
Guest profile management tools for OPERA Cloud MCP.

Provides MCP tools for managing guest profiles, preferences, and
customer relationship management through the OPERA Cloud CRM API.
"""

from typing import Any

from fastmcp import FastMCP

from opera_cloud_mcp.utils.client_factory import create_crm_client
from opera_cloud_mcp.utils.exceptions import ValidationError


def _validate_search_guests_params(hotel_id: str | None, limit: int) -> None:
    """Validate search guests parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    if limit < 1 or limit > 100:
        raise ValidationError("limit must be between 1 and 100")


def _validate_search_guests_criteria(
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    phone: str | None,
    loyalty_number: str | None,
    company_name: str | None,
) -> None:
    """Validate that at least one search criteria is provided."""
    if not any([first_name, last_name, email, phone, loyalty_number, company_name]):
        raise ValidationError("At least one search criteria must be provided")


def _validate_get_guest_profile_params(hotel_id: str | None) -> None:
    """Validate get guest profile parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _validate_create_guest_profile_params(hotel_id: str | None) -> None:
    """Validate create guest profile parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _build_profile_data(
    first_name: str,
    last_name: str,
    email: str | None,
    phone: str | None,
    address_line1: str | None,
    address_line2: str | None,
    city: str | None,
    state: str | None,
    postal_code: str | None,
    country: str | None,
    date_of_birth: str | None,
    gender: str | None,
    nationality: str | None,
    language: str | None,
    company_name: str | None,
    loyalty_number: str | None,
) -> dict[str, Any]:
    """Build profile data dictionary."""
    profile_data = {"firstName": first_name, "lastName": last_name}

    # Add optional fields
    optional_fields = {
        "email": email,
        "phoneNumber": phone,
        "addressLine1": address_line1,
        "addressLine2": address_line2,
        "city": city,
        "state": state,
        "postalCode": postal_code,
        "country": country,
        "dateOfBirth": date_of_birth,
        "gender": gender,
        "nationality": nationality,
        "language": language,
        "companyName": company_name,
        "loyaltyNumber": loyalty_number,
    }

    for key, value in optional_fields.items():
        if value is not None:
            profile_data[key] = value

    return profile_data


def _validate_update_guest_profile_params(hotel_id: str | None) -> None:
    """Validate update guest profile parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _build_update_data(
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    phone: str | None,
    address_line1: str | None,
    address_line2: str | None,
    city: str | None,
    state: str | None,
    postal_code: str | None,
    country: str | None,
    date_of_birth: str | None,
    gender: str | None,
    nationality: str | None,
    language: str | None,
    company_name: str | None,
    loyalty_number: str | None,
) -> dict[str, Any]:
    """Build update data dictionary."""
    updates = {}
    update_fields = {
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "phoneNumber": phone,
        "addressLine1": address_line1,
        "addressLine2": address_line2,
        "city": city,
        "state": state,
        "postalCode": postal_code,
        "country": country,
        "dateOfBirth": date_of_birth,
        "gender": gender,
        "nationality": nationality,
        "language": language,
        "companyName": company_name,
        "loyaltyNumber": loyalty_number,
    }

    for key, value in update_fields.items():
        if value is not None:
            updates[key] = value

    return updates


def _validate_get_guest_preferences_params(hotel_id: str | None) -> None:
    """Validate get guest preferences parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _validate_update_guest_preferences_params(
    hotel_id: str | None, preferences: list[dict[str, Any]]
) -> None:
    """Validate update guest preferences parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    if not preferences:
        raise ValidationError("At least one preference must be provided")

    # Validate preference format
    for pref in preferences:
        if not all(key in pref for key in ("category", "type", "value")):
            raise ValidationError(
                "Each preference must have 'category', 'type', and 'value' fields"
            )


def _validate_get_guest_stay_history_params(hotel_id: str | None) -> None:
    """Validate get guest stay history parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _build_history_params(
    date_from: str | None, date_to: str | None, limit: int
) -> dict[str, str | int]:
    """Build history parameters dictionary."""
    history_params: dict[str, str | int] = {"limit": limit}
    if date_from:
        history_params["dateFrom"] = date_from
    if date_to:
        history_params["dateTo"] = date_to

    return history_params


def _validate_merge_guest_profiles_params(
    hotel_id: str | None, primary_guest_id: str, duplicate_guest_id: str
) -> None:
    """Validate merge guest profiles parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    if primary_guest_id == duplicate_guest_id:
        raise ValidationError("Primary and duplicate guest IDs cannot be the same")


def _build_merge_options(
    merge_preferences: bool, merge_history: bool, merge_loyalty: bool
) -> dict[str, bool]:
    """Build merge options dictionary."""
    return {
        "mergePreferences": merge_preferences,
        "mergeHistory": merge_history,
        "mergeLoyalty": merge_loyalty,
    }


def _validate_get_guest_loyalty_info_params(hotel_id: str | None) -> None:
    """Validate get guest loyalty info parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _build_search_name(first_name: str | None, last_name: str | None) -> str | None:
    """Build search name by combining first and last names."""
    name_parts = []
    if first_name:
        name_parts.append(first_name)
    if last_name:
        name_parts.append(last_name)
    return " ".join(name_parts) if name_parts else None


def _build_address_data(
    address_line1: str | None,
    address_line2: str | None,
    city: str | None,
    state: str | None,
    postal_code: str | None,
    country: str | None,
) -> dict[str, str | None] | None:
    """Build address dictionary if any address fields are provided."""
    if any([address_line1, city, state, postal_code, country]):
        return {
            "addressLine1": address_line1,
            "addressLine2": address_line2,
            "city": city,
            "state": state,
            "postalCode": postal_code,
            "country": country,
        }
    return None


def _parse_birth_date(date_of_birth: str | None) -> Any:
    """Parse birth date string to date object if provided."""
    if not date_of_birth:
        return None

    from contextlib import suppress
    from datetime import datetime

    with suppress(ValueError):
        return datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    return None


def _register_search_guests_tool(app: FastMCP) -> None:
    """Register the search_guests tool."""

    @app.tool()
    async def search_guests(
        hotel_id: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        loyalty_number: str | None = None,
        company_name: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Search for guest profiles by various criteria.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            first_name: Guest's first name (partial match)
            last_name: Guest's last name (partial match)
            email: Guest's email address
            phone: Guest's phone number
            loyalty_number: Loyalty program number
            company_name: Company name for corporate guests
            limit: Maximum results to return (1-100)

        Returns:
            Dictionary containing matching guest profiles
        """
        _validate_search_guests_params(hotel_id, limit)
        _validate_search_guests_criteria(
            first_name, last_name, email, phone, loyalty_number, company_name
        )

        client = create_crm_client(hotel_id=hotel_id)
        search_name = _build_search_name(first_name, last_name)

        response = await client.search_guests(
            name=search_name,
            email=email,
            phone=phone,
            loyalty_number=loyalty_number,
            page_size=min(limit, 100),
        )

        search_criteria = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "loyalty_number": loyalty_number,
            "limit": limit,
        }

        if response.success:
            data = response.data or {}
            return {
                "success": True,
                "guests": data.get("profiles", []),
                "total_count": data.get("total_count", 0),
                "search_criteria": search_criteria,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error or "Unknown error occurred",
            "search_criteria": search_criteria,
            "hotel_id": hotel_id,
        }


def _register_get_guest_profile_tool(app: FastMCP) -> None:
    """Register the get_guest_profile tool."""

    @app.tool()
    async def get_guest_profile(
        guest_id: str,
        hotel_id: str | None = None,
        include_preferences: bool = True,
        include_history: bool = True,
        include_loyalty: bool = True,
    ) -> dict[str, Any]:
        """
        Get detailed guest profile information.

        Args:
            guest_id: Unique guest identifier
            hotel_id: Hotel identifier (uses default if not provided)
            include_preferences: Include guest preferences in response
            include_history: Include stay history in response
            include_loyalty: Include loyalty program information

        Returns:
            Dictionary containing complete guest profile
        """
        _validate_get_guest_profile_params(hotel_id)

        client = create_crm_client(hotel_id=hotel_id)

        response = await client.get_guest_profile(
            guest_id=guest_id,
            include_preferences=include_preferences,
            include_history=include_history,
            include_loyalty=include_loyalty,
        )

        if response.success:
            return {
                "success": True,
                "guest_profile": response.data,
                "guest_id": guest_id,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "guest_id": guest_id,
            "hotel_id": hotel_id,
        }


def _register_create_guest_profile_tool(app: FastMCP) -> None:
    """Register the create_guest_profile tool."""

    @app.tool()
    async def create_guest_profile(
        first_name: str,
        last_name: str,
        hotel_id: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        address_line1: str | None = None,
        address_line2: str | None = None,
        city: str | None = None,
        state: str | None = None,
        postal_code: str | None = None,
        country: str | None = None,
        date_of_birth: str | None = None,
        gender: str | None = None,
        nationality: str | None = None,
        language: str | None = None,
        company_name: str | None = None,
        loyalty_number: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new guest profile.

        Args:
            first_name: Guest's first name
            last_name: Guest's last name
            hotel_id: Hotel identifier (uses default if not provided)
            email: Guest's email address
            phone: Guest's phone number
            address_line1: Primary address line
            address_line2: Secondary address line
            city: City name
            state: State or province
            postal_code: Postal/zip code
            country: Country code
            date_of_birth: Date of birth in YYYY-MM-DD format
            gender: Gender (M/F/O)
            nationality: Nationality code
            language: Preferred language code
            company_name: Company name for corporate guests
            loyalty_number: Loyalty program number

        Returns:
            Dictionary containing new guest profile details
        """
        _validate_create_guest_profile_params(hotel_id)

        client = create_crm_client(hotel_id=hotel_id)

        address_data = _build_address_data(
            address_line1, address_line2, city, state, postal_code, country
        )
        birth_date_obj = _parse_birth_date(date_of_birth)

        response = await client.create_guest_profile(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address=address_data,
            birth_date=birth_date_obj,
            gender=gender,
            nationality=nationality,
            language=language,
        )

        if response.success:
            return {
                "success": True,
                "guest_profile": response.data,
                "guest_id": response.data.get("guestId") if response.data else None,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error or "Unknown error occurred",
            "hotel_id": hotel_id,
            "guest_name": f"{first_name} {last_name}",
        }


def _register_update_guest_profile_tool(app: FastMCP) -> None:
    """Register the update_guest_profile tool."""

    @app.tool()
    async def update_guest_profile(
        guest_id: str,
        hotel_id: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        address_line1: str | None = None,
        address_line2: str | None = None,
        city: str | None = None,
        state: str | None = None,
        postal_code: str | None = None,
        country: str | None = None,
        date_of_birth: str | None = None,
        gender: str | None = None,
        nationality: str | None = None,
        language: str | None = None,
        company_name: str | None = None,
        loyalty_number: str | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing guest profile.

        Args:
            guest_id: Unique guest identifier
            hotel_id: Hotel identifier (uses default if not provided)
            first_name: Updated first name
            last_name: Updated last name
            email: Updated email address
            phone: Updated phone number
            address_line1: Updated primary address
            address_line2: Updated secondary address
            city: Updated city
            state: Updated state/province
            postal_code: Updated postal code
            country: Updated country code
            date_of_birth: Updated date of birth
            gender: Updated gender
            nationality: Updated nationality
            language: Updated language preference
            company_name: Updated company name
            loyalty_number: Updated loyalty number

        Returns:
            Dictionary containing updated guest profile
        """
        _validate_update_guest_profile_params(hotel_id)

        # Build update data from provided fields
        updates = _build_update_data(
            first_name,
            last_name,
            email,
            phone,
            address_line1,
            address_line2,
            city,
            state,
            postal_code,
            country,
            date_of_birth,
            gender,
            nationality,
            language,
            company_name,
            loyalty_number,
        )

        if not updates:
            raise ValidationError("At least one field must be provided for update")

        client = create_crm_client(hotel_id=hotel_id)

        response = await client.update_guest_profile(guest_id, updates)

        if response.success:
            return {
                "success": True,
                "guest_profile": response.data,
                "guest_id": guest_id,
                "updates_applied": updates,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "guest_id": guest_id,
            "hotel_id": hotel_id,
        }


def _register_get_guest_preferences_tool(app: FastMCP) -> None:
    """Register get guest preferences tool."""

    @app.tool()
    async def get_guest_preferences(
        guest_id: str,
        hotel_id: str | None = None,
        preference_category: str | None = None,
    ) -> dict[str, Any]:
        """
        Get guest preferences and special requirements.

        Args:
            guest_id: Unique guest identifier
            hotel_id: Hotel identifier (uses default if not provided)
            preference_category: Filter by preference category (room, dining, amenities)

        Returns:
            Dictionary containing guest preferences
        """
        _validate_get_guest_preferences_params(hotel_id)

        client = create_crm_client(hotel_id=hotel_id)

        params = {}
        if preference_category:
            params["category"] = preference_category

        # Extract preference_type from params if provided
        preference_type = params.get("type") if params else None

        response = await client.get_guest_preferences(guest_id, preference_type)

        if response.success:
            return {
                "success": True,
                "preferences": response.data.get("preferences", [])
                if response.data
                else [],
                "guest_id": guest_id,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "guest_id": guest_id,
            "hotel_id": hotel_id,
        }


def _register_update_guest_preferences_tool(app: FastMCP) -> None:
    """Register update guest preferences tool."""

    @app.tool()
    async def update_guest_preferences(
        guest_id: str, preferences: list[dict[str, Any]], hotel_id: str | None = None
    ) -> dict[str, Any]:
        """
        Update guest preferences and special requirements.

        Args:
            guest_id: Unique guest identifier
            preferences: List of preference objects with category, type, and value
            hotel_id: Hotel identifier (uses default if not provided)

        Example preferences format:
            [
                {"category": "room", "type": "floor_preference",
                 "value": "high"},
                {"category": "dining", "type": "dietary_restriction",
                 "value": "vegetarian"},
                {"category": "amenities", "type": "pillow_type",
                 "value": "hypoallergenic"}
            ]

        Returns:
            Dictionary containing updated preferences
        """
        _validate_update_guest_preferences_params(hotel_id, preferences)

        client = create_crm_client(hotel_id=hotel_id)

        response = await client.update_guest_preferences(guest_id, preferences)

        if response.success:
            return {
                "success": True,
                "preferences": response.data,
                "guest_id": guest_id,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error or "Unknown error occurred",
            "guest_id": guest_id,
            "hotel_id": hotel_id,
        }


def _register_get_guest_stay_history_tool(app: FastMCP) -> None:
    """Register get guest stay history tool."""

    @app.tool()
    async def get_guest_stay_history(
        guest_id: str,
        hotel_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get guest's stay history across the hotel group.

        Args:
            guest_id: Unique guest identifier
            hotel_id: Hotel identifier (uses default if not provided)
            date_from: Start date for history in YYYY-MM-DD format
            date_to: End date for history in YYYY-MM-DD format
            limit: Maximum results to return

        Returns:
            Dictionary containing guest's historical stays
        """
        _validate_get_guest_stay_history_params(hotel_id)

        client = create_crm_client(hotel_id=hotel_id)

        history_params = _build_history_params(date_from, date_to, limit)

        response = await client.get_guest_stay_history(guest_id, history_params)

        if response.success:
            data = response.data or {}
            return {
                "success": True,
                "stay_history": data.get("stays", []),
                "total_count": data.get("total_count", 0),
                "guest_id": guest_id,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "guest_id": guest_id,
            "hotel_id": hotel_id,
        }


def _register_merge_guest_profiles_tool(app: FastMCP) -> None:
    """Register merge guest profiles tool."""

    @app.tool()
    async def merge_guest_profiles(
        primary_guest_id: str,
        duplicate_guest_id: str,
        hotel_id: str | None = None,
        merge_preferences: bool = True,
        merge_history: bool = True,
        merge_loyalty: bool = True,
    ) -> dict[str, Any]:
        """
        Merge duplicate guest profiles into a primary profile.

        Args:
            primary_guest_id: ID of the profile to keep
            duplicate_guest_id: ID of the profile to merge and remove
            hotel_id: Hotel identifier (uses default if not provided)
            merge_preferences: Whether to merge preferences
            merge_history: Whether to merge stay history
            merge_loyalty: Whether to merge loyalty information

        Returns:
            Dictionary containing merge operation results
        """
        _validate_merge_guest_profiles_params(
            hotel_id, primary_guest_id, duplicate_guest_id
        )

        client = create_crm_client(hotel_id=hotel_id)

        merge_options = _build_merge_options(
            merge_preferences, merge_history, merge_loyalty
        )

        response = await client.merge_guest_profiles(
            primary_guest_id, duplicate_guest_id, merge_options
        )

        if response.success:
            return {
                "success": True,
                "merged_profile": response.data,
                "primary_guest_id": primary_guest_id,
                "duplicate_guest_id": duplicate_guest_id,
                "merge_options": merge_options,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "primary_guest_id": primary_guest_id,
            "duplicate_guest_id": duplicate_guest_id,
            "hotel_id": hotel_id,
        }


def _register_get_guest_loyalty_info_tool(app: FastMCP) -> None:
    """Register get guest loyalty info tool."""

    @app.tool()
    async def get_guest_loyalty_info(
        guest_id: str, hotel_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get guest loyalty program information and tier status.

        Args:
            guest_id: Unique guest identifier
            hotel_id: Hotel identifier (uses default if not provided)

        Returns:
            Dictionary containing loyalty program details
        """
        _validate_get_guest_loyalty_info_params(hotel_id)

        client = create_crm_client(hotel_id=hotel_id)

        response = await client.get_guest_loyalty_info(guest_id)

        if response.success:
            return {
                "success": True,
                "loyalty_info": response.data,
                "guest_id": guest_id,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "guest_id": guest_id,
            "hotel_id": hotel_id,
        }


def register_guest_tools(app: FastMCP) -> None:
    """Register all guest profile management MCP tools."""
    _register_search_guests_tool(app)
    _register_get_guest_profile_tool(app)
    _register_create_guest_profile_tool(app)
    _register_update_guest_profile_tool(app)
    _register_get_guest_preferences_tool(app)
    _register_update_guest_preferences_tool(app)
    _register_get_guest_stay_history_tool(app)
    _register_merge_guest_profiles_tool(app)
    _register_get_guest_loyalty_info_tool(app)
