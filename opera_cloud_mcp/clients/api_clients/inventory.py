"""
Inventory API client for OPERA Cloud.

Handles room inventory and availability management
through the OPERA Cloud INV API.
"""

from datetime import date, datetime
from typing import Any

from pydantic import Field, validator

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.models.common import OperaBaseModel


class AvailabilityRequest(OperaBaseModel):
    """Room availability request model."""

    arrival_date: date = Field(alias="arrivalDate")
    departure_date: date = Field(alias="departureDate")
    room_types: list[str] | None = Field(None, alias="roomTypes")
    adults: int = Field(1, ge=1, le=8)
    children: int = Field(0, ge=0, le=4)
    rate_codes: list[str] | None = Field(None, alias="rateCodes")
    corporate_id: str | None = Field(None, alias="corporateId")
    promo_code: str | None = Field(None, alias="promoCode")

    @validator("departure_date")
    def validate_departure_after_arrival(self, v, values):
        if "arrival_date" in values and v <= values["arrival_date"]:
            raise ValueError("Departure date must be after arrival date")
        return v


class RoomTypeAvailability(OperaBaseModel):
    """Room type availability details."""

    room_type: str = Field(alias="roomType")
    room_class: str = Field(alias="roomClass")
    available_rooms: int = Field(alias="availableRooms")
    total_rooms: int = Field(alias="totalRooms")
    min_rate: float = Field(alias="minRate")
    max_rate: float = Field(alias="maxRate")
    available_rate_codes: list[str] = Field(
        default_factory=list, alias="availableRateCodes"
    )
    restrictions: dict[str, Any] | None = None
    amenities: list[str] = Field(default_factory=list)


class InventoryRestriction(OperaBaseModel):
    """Inventory restriction model."""

    restriction_type: str = Field(
        alias="restrictionType"
    )  # "CTA", "CTD", "MINSTAY", "MAXSTAY"
    room_type: str = Field(alias="roomType")
    rate_code: str | None = Field(None, alias="rateCode")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    minimum_stay: int | None = Field(None, alias="minimumStay", ge=1)
    maximum_stay: int | None = Field(None, alias="maximumStay", ge=1)
    restriction_value: str | None = Field(None, alias="restrictionValue")
    active: bool = Field(True)
    created_by: str | None = Field(None, alias="createdBy")
    created_at: datetime | None = Field(None, alias="createdAt")


class RateAvailability(OperaBaseModel):
    """Rate availability details."""

    rate_code: str = Field(alias="rateCode")
    rate_description: str = Field(alias="rateDescription")
    rate_amount: float = Field(alias="rateAmount")
    currency: str = "USD"
    available: bool = True
    restrictions: list[str] = Field(default_factory=list)
    packages: list[str] = Field(default_factory=list)
    cancellation_policy: str | None = Field(None, alias="cancellationPolicy")


class RoomBlock(OperaBaseModel):
    """Room block model for inventory allocation."""

    block_id: str = Field(alias="blockId")
    block_name: str = Field(alias="blockName")
    room_type: str = Field(alias="roomType")
    blocked_rooms: int = Field(alias="blockedRooms")
    released_rooms: int = Field(0, alias="releasedRooms")
    picked_up_rooms: int = Field(0, alias="pickedUpRooms")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    cutoff_date: date | None = Field(None, alias="cutoffDate")
    rate_code: str = Field(alias="rateCode")
    block_status: str = Field(
        "ACTIVE", alias="blockStatus"
    )  # "ACTIVE", "RELEASED", "CANCELLED"


class InventoryAdjustment(OperaBaseModel):
    """Inventory adjustment model."""

    room_type: str = Field(alias="roomType")
    adjustment_date: date = Field(alias="adjustmentDate")
    adjustment_type: str = Field(alias="adjustmentType")  # "ADD", "SUBTRACT", "SET"
    adjustment_value: int = Field(alias="adjustmentValue")
    reason_code: str = Field(alias="reasonCode")
    comments: str | None = None
    adjusted_by: str | None = Field(None, alias="adjustedBy")


class InventoryClient(BaseAPIClient):
    """
    Client for OPERA Cloud Inventory API.

    Provides comprehensive room inventory management including availability,
    restrictions, rate management, and room block allocation.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_domain = "inv"

    # Availability Management

    async def check_room_availability(
        self, availability_request: AvailabilityRequest | dict[str, Any]
    ) -> APIResponse:
        """
        Check room availability for specific dates and criteria.

        Args:
            availability_request: Availability search criteria

        Returns:
            APIResponse with available room types and rates
        """
        if isinstance(availability_request, dict):
            availability_request = AvailabilityRequest.model_validate(
                availability_request
            )

        endpoint = f"{self.api_domain}/v1/availability"

        params = {
            "arrivalDate": availability_request.arrival_date.isoformat(),
            "departureDate": availability_request.departure_date.isoformat(),
            "adults": availability_request.adults,
            "children": availability_request.children,
        }

        if availability_request.room_types:
            params["roomTypes"] = ",".join(availability_request.room_types)
        if availability_request.rate_codes:
            params["rateCodes"] = ",".join(availability_request.rate_codes)
        if availability_request.corporate_id:
            params["corporateId"] = availability_request.corporate_id
        if availability_request.promo_code:
            params["promoCode"] = availability_request.promo_code

        return await self.get(endpoint, params=params)

    async def get_room_type_availability(
        self, room_type: str, start_date: date, end_date: date
    ) -> APIResponse:
        """
        Get detailed availability for a specific room type over a date range.

        Args:
            room_type: Room type code
            start_date: Start date for availability check
            end_date: End date for availability check

        Returns:
            APIResponse with day-by-day availability details
        """
        endpoint = f"{self.api_domain}/v1/room-types/{room_type}/availability"

        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }

        return await self.get(endpoint, params=params)

    async def get_availability_calendar(
        self, year: int, month: int, room_type: str | None = None
    ) -> APIResponse:
        """
        Get availability calendar for a specific month.

        Args:
            year: Calendar year
            month: Calendar month (1-12)
            room_type: Optional room type filter

        Returns:
            APIResponse with monthly availability calendar
        """
        endpoint = f"{self.api_domain}/v1/availability/calendar"

        params: dict[str, str | int] = {
            "year": year,
            "month": month,
        }

        if room_type:
            params["roomType"] = room_type

        return await self.get(endpoint, params=params)

    # Rate Management

    async def get_available_rates(
        self,
        arrival_date: date,
        departure_date: date,
        room_type: str,
        corporate_id: str | None = None,
    ) -> APIResponse:
        """
        Get available rates for a room type and date range.

        Args:
            arrival_date: Arrival date
            departure_date: Departure date
            room_type: Room type code
            corporate_id: Corporate ID for negotiated rates

        Returns:
            APIResponse with available rates and restrictions
        """
        endpoint = f"{self.api_domain}/v1/rates/available"

        params = {
            "arrivalDate": arrival_date.isoformat(),
            "departureDate": departure_date.isoformat(),
            "roomType": room_type,
        }

        if corporate_id:
            params["corporateId"] = corporate_id

        return await self.get(endpoint, params=params)

    async def get_rate_details(
        self, rate_code: str, check_date: date | None = None
    ) -> APIResponse:
        """
        Get detailed rate information including packages and restrictions.

        Args:
            rate_code: Rate code to retrieve
            check_date: Date to check rate validity (defaults to today)

        Returns:
            APIResponse with detailed rate information
        """
        endpoint = f"{self.api_domain}/v1/rates/{rate_code}"

        params = {}
        if check_date:
            params["date"] = check_date.isoformat()

        return await self.get(endpoint, params=params)

    # Inventory Restrictions

    async def get_restrictions(
        self,
        room_type: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> APIResponse:
        """
        Get inventory restrictions for room types and date ranges.

        Args:
            room_type: Optional room type filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            APIResponse with active restrictions
        """
        endpoint = f"{self.api_domain}/v1/restrictions"

        params = {}
        if room_type:
            params["roomType"] = room_type
        if start_date:
            params["startDate"] = start_date.isoformat()
        if end_date:
            params["endDate"] = end_date.isoformat()

        return await self.get(endpoint, params=params)

    async def create_restriction(
        self, restriction_data: InventoryRestriction | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new inventory restriction.

        Args:
            restriction_data: Restriction details and rules

        Returns:
            APIResponse with created restriction details
        """
        if isinstance(restriction_data, dict):
            restriction_data = InventoryRestriction.model_validate(restriction_data)

        endpoint = f"{self.api_domain}/v1/restrictions"

        payload = {
            "restrictionType": restriction_data.restriction_type,
            "roomType": restriction_data.room_type,
            "rateCode": restriction_data.rate_code,
            "startDate": restriction_data.start_date.isoformat(),
            "endDate": restriction_data.end_date.isoformat(),
            "minimumStay": restriction_data.minimum_stay,
            "maximumStay": restriction_data.maximum_stay,
            "restrictionValue": restriction_data.restriction_value,
            "active": restriction_data.active,
        }

        return await self.post(endpoint, json_data=payload)

    async def update_restriction(
        self, restriction_id: str, update_data: dict[str, Any]
    ) -> APIResponse:
        """
        Update an existing inventory restriction.

        Args:
            restriction_id: Restriction ID to update
            update_data: Fields to update

        Returns:
            APIResponse with updated restriction details
        """
        endpoint = f"{self.api_domain}/v1/restrictions/{restriction_id}"

        return await self.put(endpoint, json_data=update_data)

    async def delete_restriction(self, restriction_id: str) -> APIResponse:
        """
        Delete an inventory restriction.

        Args:
            restriction_id: Restriction ID to delete

        Returns:
            APIResponse with deletion confirmation
        """
        endpoint = f"{self.api_domain}/v1/restrictions/{restriction_id}"

        return await self.delete(endpoint)

    # Room Block Management

    async def get_room_blocks(
        self,
        block_status: str | None = None,
        date_range_start: date | None = None,
        date_range_end: date | None = None,
    ) -> APIResponse:
        """
        Get room blocks with optional filtering.

        Args:
            block_status: Filter by block status
            date_range_start: Start date for date range filter
            date_range_end: End date for date range filter

        Returns:
            APIResponse with room block details
        """
        endpoint = f"{self.api_domain}/v1/blocks"

        params = {}
        if block_status:
            params["status"] = block_status
        if date_range_start:
            params["startDate"] = date_range_start.isoformat()
        if date_range_end:
            params["endDate"] = date_range_end.isoformat()

        return await self.get(endpoint, params=params)

    async def create_room_block(
        self, block_data: RoomBlock | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new room block allocation.

        Args:
            block_data: Room block details and allocation

        Returns:
            APIResponse with created block information
        """
        if isinstance(block_data, dict):
            block_data = RoomBlock.model_validate(block_data)

        endpoint = f"{self.api_domain}/v1/blocks"

        payload = {
            "blockName": block_data.block_name,
            "roomType": block_data.room_type,
            "blockedRooms": block_data.blocked_rooms,
            "startDate": block_data.start_date.isoformat(),
            "endDate": block_data.end_date.isoformat(),
            "cutoffDate": block_data.cutoff_date.isoformat()
            if block_data.cutoff_date
            else None,
            "rateCode": block_data.rate_code,
        }

        return await self.post(endpoint, json_data=payload)

    async def update_room_block(
        self, block_id: str, update_data: dict[str, Any]
    ) -> APIResponse:
        """
        Update an existing room block.

        Args:
            block_id: Block ID to update
            update_data: Fields to update

        Returns:
            APIResponse with updated block information
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}"

        return await self.put(endpoint, json_data=update_data)

    async def release_room_block(
        self, block_id: str, release_rooms: int, release_date: date | None = None
    ) -> APIResponse:
        """
        Release rooms from a block back to general inventory.

        Args:
            block_id: Block ID to release rooms from
            release_rooms: Number of rooms to release
            release_date: Date of release (defaults to today)

        Returns:
            APIResponse with release confirmation
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/release"

        payload = {
            "releaseRooms": release_rooms,
            "releaseDate": (release_date or date.today()).isoformat(),
        }

        return await self.post(endpoint, json_data=payload)

    # Inventory Adjustments

    async def get_inventory_levels(
        self,
        room_type: str | None = None,
        date_range_start: date | None = None,
        date_range_end: date | None = None,
    ) -> APIResponse:
        """
        Get current inventory levels for room types.

        Args:
            room_type: Optional room type filter
            date_range_start: Start date for inventory query
            date_range_end: End date for inventory query

        Returns:
            APIResponse with inventory levels and allocations
        """
        endpoint = f"{self.api_domain}/v1/inventory/levels"

        params = {}
        if room_type:
            params["roomType"] = room_type
        if date_range_start:
            params["startDate"] = date_range_start.isoformat()
        if date_range_end:
            params["endDate"] = date_range_end.isoformat()

        return await self.get(endpoint, params=params)

    async def adjust_inventory(
        self, adjustment_data: InventoryAdjustment | dict[str, Any]
    ) -> APIResponse:
        """
        Make an inventory adjustment for a room type.

        Args:
            adjustment_data: Inventory adjustment details

        Returns:
            APIResponse with adjustment confirmation
        """
        if isinstance(adjustment_data, dict):
            adjustment_data = InventoryAdjustment.model_validate(adjustment_data)

        endpoint = f"{self.api_domain}/v1/inventory/adjustments"

        payload = {
            "roomType": adjustment_data.room_type,
            "adjustmentDate": adjustment_data.adjustment_date.isoformat(),
            "adjustmentType": adjustment_data.adjustment_type,
            "adjustmentValue": adjustment_data.adjustment_value,
            "reasonCode": adjustment_data.reason_code,
            "comments": adjustment_data.comments,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_adjustment_history(
        self,
        room_type: str | None = None,
        start_date: date | None = None,
        limit: int = 100,
    ) -> APIResponse:
        """
        Get inventory adjustment history.

        Args:
            room_type: Optional room type filter
            start_date: Start date for history query
            limit: Maximum number of records to return

        Returns:
            APIResponse with adjustment history
        """
        endpoint = f"{self.api_domain}/v1/inventory/adjustments/history"

        params: dict[str, str | int] = {"limit": limit}
        if room_type:
            params["roomType"] = room_type
        if start_date:
            params["startDate"] = start_date.isoformat()

        return await self.get(endpoint, params=params)

    # Batch Operations

    async def bulk_update_availability(
        self, updates: list[dict[str, Any]]
    ) -> APIResponse:
        """
        Perform bulk availability updates across multiple room types/dates.

        Args:
            updates: List of availability updates

        Returns:
            APIResponse with bulk operation results
        """
        endpoint = f"{self.api_domain}/v1/availability/bulk-update"

        payload = {"updates": updates}

        return await self.post(endpoint, json_data=payload)

    async def bulk_create_restrictions(
        self, restrictions: list[InventoryRestriction]
    ) -> APIResponse:
        """
        Create multiple restrictions in a single operation.

        Args:
            restrictions: List of restrictions to create

        Returns:
            APIResponse with bulk creation results
        """
        endpoint = f"{self.api_domain}/v1/restrictions/bulk"

        payload = {
            "restrictions": [
                {
                    "restrictionType": r.restriction_type,
                    "roomType": r.room_type,
                    "rateCode": r.rate_code,
                    "startDate": r.start_date.isoformat(),
                    "endDate": r.end_date.isoformat(),
                    "minimumStay": r.minimum_stay,
                    "maximumStay": r.maximum_stay,
                    "restrictionValue": r.restriction_value,
                    "active": r.active,
                }
                for r in restrictions
            ]
        }

        return await self.post(endpoint, json_data=payload)

    # Analytics and Reporting

    async def get_availability_trends(
        self, room_type: str, days_ahead: int = 90
    ) -> APIResponse:
        """
        Get availability trends for forecasting and analysis.

        Args:
            room_type: Room type to analyze
            days_ahead: Number of days to look ahead

        Returns:
            APIResponse with availability trend data
        """
        endpoint = f"{self.api_domain}/v1/analytics/availability-trends"

        params = {
            "roomType": room_type,
            "daysAhead": days_ahead,
        }

        return await self.get(endpoint, params=params)

    async def get_pickup_report(
        self, start_date: date, end_date: date, room_type: str | None = None
    ) -> APIResponse:
        """
        Get pickup report showing booking patterns and trends.

        Args:
            start_date: Report start date
            end_date: Report end date
            room_type: Optional room type filter

        Returns:
            APIResponse with pickup analysis
        """
        endpoint = f"{self.api_domain}/v1/reports/pickup"

        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }

        if room_type:
            params["roomType"] = room_type

        return await self.get(endpoint, params=params)

    async def get_displacement_report(
        self, analysis_date: date, room_type: str | None = None
    ) -> APIResponse:
        """
        Get displacement analysis showing potential revenue impact.

        Args:
            analysis_date: Date to analyze for displacement
            room_type: Optional room type filter

        Returns:
            APIResponse with displacement analysis
        """
        endpoint = f"{self.api_domain}/v1/reports/displacement"

        params = {"analysisDate": analysis_date.isoformat()}

        if room_type:
            params["roomType"] = room_type

        return await self.get(endpoint, params=params)

    # Convenience Methods

    async def get_best_available_rate(
        self, arrival_date: date, departure_date: date, room_type: str, adults: int = 1
    ) -> APIResponse:
        """
        Get the best available rate for given criteria.

        Args:
            arrival_date: Arrival date
            departure_date: Departure date
            room_type: Room type code
            adults: Number of adults

        Returns:
            APIResponse with best available rate
        """
        # First check availability
        availability_request = AvailabilityRequest(
            arrivalDate=arrival_date,
            departureDate=departure_date,
            roomTypes=[room_type],
            adults=adults,
            children=0,
            rateCodes=[],
            corporateId=None,
            promoCode=None,
        )

        availability = await self.check_room_availability(availability_request)

        if not availability.success:
            return availability

        # Then get rates for available room type
        rates = await self.get_available_rates(arrival_date, departure_date, room_type)

        if not rates.success:
            return rates

        # Combine availability and rate data
        combined_data = {
            "availability": availability.data,
            "rates": rates.data,
            "best_rate": None,
        }

        # Find best rate (lowest available rate)
        if rates.data and "rates" in rates.data:
            available_rates = [
                r for r in rates.data["rates"] if r.get("available", True)
            ]
            if available_rates:
                best_rate = min(
                    available_rates, key=lambda x: x.get("rateAmount", float("inf"))
                )
                combined_data["best_rate"] = best_rate

        return APIResponse(success=True, data=combined_data)

    async def check_minimum_stay_compliance(
        self,
        arrival_date: date,
        departure_date: date,
        room_type: str,
        rate_code: str | None = None,
    ) -> APIResponse:
        """
        Check if a stay meets minimum stay requirements.

        Args:
            arrival_date: Arrival date
            departure_date: Departure date
            room_type: Room type code
            rate_code: Optional rate code

        Returns:
            APIResponse with compliance check results
        """
        nights = (departure_date - arrival_date).days

        # Get applicable restrictions
        restrictions_response = await self.get_restrictions(
            room_type=room_type, start_date=arrival_date, end_date=departure_date
        )

        if not restrictions_response.success:
            return restrictions_response

        compliance_data: dict[str, Any] = {
            "compliant": True,
            "nights_requested": nights,
            "minimum_stay_violations": [],
            "applicable_restrictions": restrictions_response.data,
        }

        # Check for minimum stay violations
        if restrictions_response.data and "restrictions" in restrictions_response.data:
            for restriction in restrictions_response.data["restrictions"]:
                if (
                    restriction.get("restrictionType") == "MINSTAY"
                    and restriction.get("roomType") == room_type
                ):
                    min_stay = restriction.get("minimumStay", 0)
                    if nights < min_stay:
                        compliance_data["compliant"] = False
                        compliance_data["minimum_stay_violations"].append(
                            {
                                "restriction_id": restriction.get("id"),
                                "required_nights": min_stay,
                                "requested_nights": nights,
                                "shortage": min_stay - nights,
                            }
                        )

        return APIResponse(success=True, data=compliance_data)
