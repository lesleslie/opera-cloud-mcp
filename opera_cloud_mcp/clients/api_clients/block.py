"""
Block Management API client for OPERA Cloud.

Handles group bookings, room blocks, and group reservation management
through the OPERA Cloud BLK API.
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, validator

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.models.common import OperaBaseModel


class RoomBlock(OperaBaseModel):
    """Room block model for group reservations."""

    block_id: str = Field(alias="blockId")
    block_code: str = Field(alias="blockCode")
    block_name: str = Field(alias="blockName")
    account_name: str = Field(alias="accountName")
    contact_name: str = Field(alias="contactName")
    contact_email: str | None = Field(None, alias="contactEmail")
    contact_phone: str | None = Field(None, alias="contactPhone")
    arrival_date: date = Field(alias="arrivalDate")
    departure_date: date = Field(alias="departureDate")
    room_nights: int = Field(alias="roomNights")
    rate_code: str = Field(alias="rateCode")
    rate_amount: Decimal = Field(alias="rateAmount")
    currency_code: str = Field(alias="currencyCode")
    status: str  # "tentative", "definite", "cancelled", "picked_up"
    cutoff_date: date | None = Field(None, alias="cutoffDate")
    special_instructions: str | None = Field(None, alias="specialInstructions")
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(alias="createdAt")

    @validator("status")
    def validate_status(self, v):
        allowed = ["tentative", "definite", "cancelled", "picked_up", "active"]
        if v not in allowed:
            raise ValueError(f"Invalid block status. Must be one of: {allowed}")
        return v


class BlockInventory(OperaBaseModel):
    """Block inventory allocation model."""

    block_id: str = Field(alias="blockId")
    room_type: str = Field(alias="roomType")
    blocked_rooms: int = Field(alias="blockedRooms")
    picked_up_rooms: int = Field(alias="pickedUpRooms")
    available_rooms: int = Field(alias="availableRooms")
    rate_amount: Decimal = Field(alias="rateAmount")
    rate_code: str = Field(alias="rateCode")
    allocation_date: date = Field(alias="allocationDate")


class GroupReservation(OperaBaseModel):
    """Group reservation model."""

    reservation_id: str = Field(alias="reservationId")
    block_id: str = Field(alias="blockId")
    guest_name: str = Field(alias="guestName")
    room_type: str = Field(alias="roomType")
    room_number: str | None = Field(None, alias="roomNumber")
    arrival_date: date = Field(alias="arrivalDate")
    departure_date: date = Field(alias="departureDate")
    adults: int = Field(default=1, ge=1)
    children: int = Field(default=0, ge=0)
    rate_code: str = Field(alias="rateCode")
    rate_amount: Decimal = Field(alias="rateAmount")
    special_requests: str | None = Field(None, alias="specialRequests")
    status: str = Field(default="confirmed")
    vip_status: str | None = Field(None, alias="vipStatus")


class BlockRoomingList(OperaBaseModel):
    """Block rooming list model."""

    block_id: str = Field(alias="blockId")
    guest_name: str = Field(alias="guestName")
    room_type: str = Field(alias="roomType")
    arrival_date: date = Field(alias="arrivalDate")
    departure_date: date = Field(alias="departureDate")
    adults: int = Field(default=1, ge=1)
    children: int = Field(default=0, ge=0)
    special_requests: str | None = Field(None, alias="specialRequests")
    dietary_requirements: str | None = Field(None, alias="dietaryRequirements")
    accessibility_needs: str | None = Field(None, alias="accessibilityNeeds")
    vip_status: str | None = Field(None, alias="vipStatus")
    arrival_time: str | None = Field(None, alias="arrivalTime")
    departure_time: str | None = Field(None, alias="departureTime")


class BlockContract(OperaBaseModel):
    """Block contract and terms model."""

    block_id: str = Field(alias="blockId")
    contract_number: str = Field(alias="contractNumber")
    pickup_percentage: int = Field(alias="pickupPercentage", ge=0, le=100)
    attrition_percentage: int = Field(alias="attritionPercentage", ge=0, le=100)
    deposit_required: bool = Field(False, alias="depositRequired")
    deposit_amount: Decimal | None = Field(None, alias="depositAmount")
    deposit_due_date: date | None = Field(None, alias="depositDueDate")
    cancellation_policy: str | None = Field(None, alias="cancellationPolicy")
    payment_terms: str | None = Field(None, alias="paymentTerms")
    catering_minimum: Decimal | None = Field(None, alias="cateringMinimum")
    complimentary_rooms: int = Field(default=0, alias="complimentaryRooms")
    group_benefits: list[str] | None = Field(None, alias="groupBenefits")


class BlockClient(BaseAPIClient):
    """
    Client for OPERA Cloud Block Management API.

    Provides comprehensive block management operations including room blocks,
    group reservations, rooming lists, and contract management.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_domain = "blk"

    # Block Management

    async def get_blocks(
        self,
        block_date: date | None = None,
        status: str | None = None,
        account_name: str | None = None,
        block_code: str | None = None,
    ) -> APIResponse:
        """
        Get blocks for specified criteria.

        Args:
            block_date: Date to filter blocks (defaults to today)
            status: Filter by block status
            account_name: Filter by account name
            block_code: Specific block code to retrieve

        Returns:
            APIResponse with block details
        """
        if block_date is None:
            block_date = date.today()

        endpoint = f"{self.api_domain}/v1/blocks"
        params = {"date": block_date.isoformat()}

        if status:
            params["status"] = status
        if account_name:
            params["accountName"] = account_name
        if block_code:
            params["blockCode"] = block_code

        return await self.get(endpoint, params=params)

    async def create_room_block(
        self, block_data: RoomBlock | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new room block for group bookings.

        Args:
            block_data: Block creation data

        Returns:
            APIResponse with created block details
        """
        if isinstance(block_data, dict):
            block_data = RoomBlock.model_validate(block_data)

        endpoint = f"{self.api_domain}/v1/blocks"

        payload = {
            "blockCode": block_data.block_code,
            "blockName": block_data.block_name,
            "accountName": block_data.account_name,
            "contactName": block_data.contact_name,
            "contactEmail": block_data.contact_email,
            "contactPhone": block_data.contact_phone,
            "arrivalDate": block_data.arrival_date.isoformat(),
            "departureDate": block_data.departure_date.isoformat(),
            "roomNights": block_data.room_nights,
            "rateCode": block_data.rate_code,
            "rateAmount": str(block_data.rate_amount),
            "currencyCode": block_data.currency_code,
            "status": block_data.status,
            "cutoffDate": block_data.cutoff_date.isoformat()
            if block_data.cutoff_date
            else None,
            "specialInstructions": block_data.special_instructions,
            "createdBy": block_data.created_by,
        }

        return await self.post(endpoint, json_data=payload)

    async def update_block_status(
        self, block_id: str, status: str, notes: str | None = None
    ) -> APIResponse:
        """
        Update block status.

        Args:
            block_id: Block identifier
            status: New block status
            notes: Optional update notes

        Returns:
            APIResponse with update confirmation
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/status"

        payload = {
            "status": status,
            "notes": notes,
            "updatedAt": datetime.now().isoformat(),
        }

        return await self.put(endpoint, json_data=payload)

    async def get_block_details(self, block_id: str) -> APIResponse:
        """
        Get detailed information for a specific block.

        Args:
            block_id: Block identifier

        Returns:
            APIResponse with comprehensive block details
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}"

        return await self.get(endpoint)

    # Block Inventory Management

    async def allocate_block_inventory(
        self, block_id: str, room_allocations: list[BlockInventory]
    ) -> APIResponse:
        """
        Allocate room inventory to a block.

        Args:
            block_id: Block identifier
            room_allocations: List of room type allocations

        Returns:
            APIResponse with allocation confirmation
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/inventory"

        payload = {
            "allocations": [
                {
                    "roomType": allocation.room_type,
                    "blockedRooms": allocation.blocked_rooms,
                    "rateAmount": str(allocation.rate_amount),
                    "rateCode": allocation.rate_code,
                    "allocationDate": allocation.allocation_date.isoformat(),
                }
                for allocation in room_allocations
            ]
        }

        return await self.post(endpoint, json_data=payload)

    async def get_block_inventory(
        self, block_id: str, inventory_date: date | None = None
    ) -> APIResponse:
        """
        Get block inventory allocation details.

        Args:
            block_id: Block identifier
            inventory_date: Specific date to check inventory

        Returns:
            APIResponse with inventory allocation details
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/inventory"
        params = {}

        if inventory_date:
            params["date"] = inventory_date.isoformat()

        return await self.get(endpoint, params=params)

    async def release_block_inventory(
        self, block_id: str, room_type: str, rooms_to_release: int
    ) -> APIResponse:
        """
        Release rooms from block inventory back to general availability.

        Args:
            block_id: Block identifier
            room_type: Room type to release
            rooms_to_release: Number of rooms to release

        Returns:
            APIResponse with release confirmation
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/inventory/release"

        payload = {
            "roomType": room_type,
            "roomsToRelease": rooms_to_release,
            "releasedAt": datetime.now().isoformat(),
        }

        return await self.post(endpoint, json_data=payload)

    # Group Reservations

    async def create_group_reservation(
        self, reservation_data: GroupReservation | dict[str, Any]
    ) -> APIResponse:
        """
        Create a group reservation within a block.

        Args:
            reservation_data: Group reservation details

        Returns:
            APIResponse with reservation confirmation
        """
        if isinstance(reservation_data, dict):
            reservation_data = GroupReservation.model_validate(reservation_data)

        endpoint = (
            f"{self.api_domain}/v1/blocks/{reservation_data.block_id}/reservations"
        )

        payload = {
            "guestName": reservation_data.guest_name,
            "roomType": reservation_data.room_type,
            "roomNumber": reservation_data.room_number,
            "arrivalDate": reservation_data.arrival_date.isoformat(),
            "departureDate": reservation_data.departure_date.isoformat(),
            "adults": reservation_data.adults,
            "children": reservation_data.children,
            "rateCode": reservation_data.rate_code,
            "rateAmount": str(reservation_data.rate_amount),
            "specialRequests": reservation_data.special_requests,
            "vipStatus": reservation_data.vip_status,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_block_reservations(
        self, block_id: str, status: str | None = None
    ) -> APIResponse:
        """
        Get all reservations within a block.

        Args:
            block_id: Block identifier
            status: Filter by reservation status

        Returns:
            APIResponse with block reservation list
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/reservations"
        params = {}

        if status:
            params["status"] = status

        return await self.get(endpoint, params=params)

    # Rooming List Management

    async def upload_rooming_list(
        self, block_id: str, rooming_list: list[BlockRoomingList]
    ) -> APIResponse:
        """
        Upload a rooming list for a block.

        Args:
            block_id: Block identifier
            rooming_list: List of guest room assignments

        Returns:
            APIResponse with upload results
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/rooming-list"

        payload = {
            "roomingList": [
                {
                    "guestName": guest.guest_name,
                    "roomType": guest.room_type,
                    "arrivalDate": guest.arrival_date.isoformat(),
                    "departureDate": guest.departure_date.isoformat(),
                    "adults": guest.adults,
                    "children": guest.children,
                    "specialRequests": guest.special_requests,
                    "dietaryRequirements": guest.dietary_requirements,
                    "accessibilityNeeds": guest.accessibility_needs,
                    "vipStatus": guest.vip_status,
                    "arrivalTime": guest.arrival_time,
                    "departureTime": guest.departure_time,
                }
                for guest in rooming_list
            ]
        }

        return await self.post(endpoint, json_data=payload)

    async def get_rooming_list(
        self, block_id: str, format_type: str = "detailed"
    ) -> APIResponse:
        """
        Get the rooming list for a block.

        Args:
            block_id: Block identifier
            format_type: Format type (summary, detailed, export)

        Returns:
            APIResponse with rooming list data
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/rooming-list"
        params = {"format": format_type}

        return await self.get(endpoint, params=params)

    # Contract Management

    async def create_block_contract(
        self, contract_data: BlockContract | dict[str, Any]
    ) -> APIResponse:
        """
        Create or update block contract terms.

        Args:
            contract_data: Block contract details

        Returns:
            APIResponse with contract creation confirmation
        """
        if isinstance(contract_data, dict):
            contract_data = BlockContract.model_validate(contract_data)

        endpoint = f"{self.api_domain}/v1/blocks/{contract_data.block_id}/contract"

        payload = {
            "contractNumber": contract_data.contract_number,
            "pickupPercentage": contract_data.pickup_percentage,
            "attritionPercentage": contract_data.attrition_percentage,
            "depositRequired": contract_data.deposit_required,
            "depositAmount": str(contract_data.deposit_amount)
            if contract_data.deposit_amount
            else None,
            "depositDueDate": contract_data.deposit_due_date.isoformat()
            if contract_data.deposit_due_date
            else None,
            "cancellationPolicy": contract_data.cancellation_policy,
            "paymentTerms": contract_data.payment_terms,
            "cateringMinimum": str(contract_data.catering_minimum)
            if contract_data.catering_minimum
            else None,
            "complimentaryRooms": contract_data.complimentary_rooms,
            "groupBenefits": contract_data.group_benefits,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_block_contract(self, block_id: str) -> APIResponse:
        """
        Get block contract terms and conditions.

        Args:
            block_id: Block identifier

        Returns:
            APIResponse with contract details
        """
        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/contract"

        return await self.get(endpoint)

    # Reporting and Analytics

    async def get_block_pickup_report(
        self, block_id: str, as_of_date: date | None = None
    ) -> APIResponse:
        """
        Get block pickup performance report.

        Args:
            block_id: Block identifier
            as_of_date: Report date (defaults to today)

        Returns:
            APIResponse with pickup statistics
        """
        if as_of_date is None:
            as_of_date = date.today()

        endpoint = f"{self.api_domain}/v1/blocks/{block_id}/reports/pickup"
        params = {"asOfDate": as_of_date.isoformat()}

        return await self.get(endpoint, params=params)

    async def get_blocks_summary_report(
        self, start_date: date, end_date: date, status: str | None = None
    ) -> APIResponse:
        """
        Get comprehensive blocks summary report.

        Args:
            start_date: Report start date
            end_date: Report end date
            status: Filter by block status

        Returns:
            APIResponse with blocks summary
        """
        endpoint = f"{self.api_domain}/v1/reports/blocks-summary"
        params = {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}

        if status:
            params["status"] = status

        return await self.get(endpoint, params=params)

    # Batch Operations

    async def batch_create_group_reservations(
        self, block_id: str, reservations: list[GroupReservation]
    ) -> APIResponse:
        """
        Create multiple group reservations in a single operation.

        Args:
            block_id: Block identifier
            reservations: List of group reservations to create

        Returns:
            APIResponse with batch creation results
        """
        tasks = [
            self.create_group_reservation(reservation) for reservation in reservations
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = []
        failed = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append(
                    {"guest_name": reservations[i].guest_name, "error": str(result)}
                )
            elif isinstance(result, APIResponse) and result.success:
                successful.append(result.data)
            elif isinstance(result, APIResponse):
                failed.append(
                    {
                        "guest_name": reservations[i].guest_name,
                        "error": result.error or "Unknown error",
                    }
                )

        return APIResponse(
            success=len(failed) == 0,
            data={
                "successful_reservations": successful,
                "failed_reservations": failed,
                "total_processed": len(reservations),
                "success_count": len(successful),
                "failure_count": len(failed),
            },
        )

    # Convenience Methods

    async def get_block_availability(
        self,
        arrival_date: date,
        departure_date: date,
        room_nights: int,
        room_types: list[str] | None = None,
    ) -> APIResponse:
        """
        Check availability for creating a new block.

        Args:
            arrival_date: Block arrival date
            departure_date: Block departure date
            room_nights: Required room nights
            room_types: Specific room types needed

        Returns:
            APIResponse with availability details
        """
        endpoint = f"{self.api_domain}/v1/blocks/availability"
        params = {
            "arrivalDate": arrival_date.isoformat(),
            "departureDate": departure_date.isoformat(),
            "roomNights": room_nights,
        }

        if room_types:
            params["roomTypes"] = ",".join(room_types)

        return await self.get(endpoint, params=params)
