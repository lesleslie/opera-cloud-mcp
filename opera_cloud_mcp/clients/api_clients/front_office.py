"""
Front Office API client for OPERA Cloud.

Handles front office operations including check-in, check-out,
and daily operational reports through the OPERA Cloud FOF API.
"""

import asyncio
from datetime import date, datetime
from typing import Any

from pydantic import Field, field_validator

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.models.common import OperaBaseModel
from opera_cloud_mcp.models.guest import GuestProfile


class CheckInRequest(OperaBaseModel):
    """Check-in request model."""

    confirmation_number: str = Field(alias="confirmationNumber")
    room_number: str | None = Field(None, alias="roomNumber")
    arrival_time: datetime | None = Field(None, alias="arrivalTime")
    special_requests: str | None = Field(None, alias="specialRequests")
    guest_signature: str | None = Field(None, alias="guestSignature")
    id_verification: bool = Field(True, alias="idVerification")
    credit_card_authorization: str | None = Field(None, alias="creditCardAuth")
    key_cards_issued: int = Field(1, alias="keyCardsIssued")

    @field_validator("arrival_time", mode="before")
    @classmethod
    def parse_arrival_time(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v


class CheckOutRequest(OperaBaseModel):
    """Check-out request model."""

    confirmation_number: str = Field(alias="confirmationNumber")
    room_number: str = Field(alias="roomNumber")
    departure_time: datetime | None = Field(None, alias="departureTime")
    express_checkout: bool = Field(False, alias="expressCheckout")
    folio_settlement: bool = Field(True, alias="folioSettlement")
    key_cards_returned: int = Field(0, alias="keyCardsReturned")
    room_damages: str | None = Field(None, alias="roomDamages")
    guest_satisfaction: int | None = Field(None, alias="guestSatisfaction", ge=1, le=5)

    @field_validator("departure_time", mode="before")
    @classmethod
    def parse_departure_time(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v


class WalkInRequest(OperaBaseModel):
    """Walk-in guest request model."""

    guest_profile: GuestProfile
    room_type: str = Field(alias="roomType")
    nights: int = Field(ge=1)
    rate_code: str = Field(alias="rateCode")
    special_requests: str | None = Field(None, alias="specialRequests")
    corporate_account: str | None = Field(None, alias="corporateAccount")
    credit_card_required: bool = Field(True, alias="creditCardRequired")


class ArrivalSummary(OperaBaseModel):
    """Arrival summary for reports."""

    confirmation_number: str = Field(alias="confirmationNumber")
    guest_name: str = Field(alias="guestName")
    room_type: str = Field(alias="roomType")
    assigned_room: str | None = Field(None, alias="assignedRoom")
    arrival_time: datetime | None = Field(None, alias="arrivalTime")
    nights: int
    rate_code: str = Field(alias="rateCode")
    rate_amount: float = Field(alias="rateAmount")
    status: str  # "confirmed", "checked_in", "no_show"
    vip_status: str | None = Field(None, alias="vipStatus")
    special_requests: str | None = Field(None, alias="specialRequests")


class DepartureSummary(OperaBaseModel):
    """Departure summary for reports."""

    confirmation_number: str = Field(alias="confirmationNumber")
    guest_name: str = Field(alias="guestName")
    room_number: str = Field(alias="roomNumber")
    departure_time: datetime | None = Field(None, alias="departureTime")
    checkout_status: str = Field(
        alias="checkoutStatus"
    )  # "pending", "checked_out", "late_checkout"
    folio_balance: float = Field(alias="folioBalance")
    room_charges: float = Field(alias="roomCharges")
    incidental_charges: float = Field(alias="incidentalCharges")
    payment_method: str | None = Field(None, alias="paymentMethod")


class FrontOfficeClient(BaseAPIClient):
    """
    Client for OPERA Cloud Front Office API.

    Provides comprehensive front office operations including guest check-in/out,
    walk-in processing, room assignments, and operational reports.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_domain = "fof"

    # Check-In Operations

    async def check_in_guest(
        self, check_in_data: CheckInRequest | dict[str, Any]
    ) -> APIResponse:
        """
        Check in a guest to their assigned room.

        Args:
            check_in_data: Check-in information including confirmation number
                          and room assignment details

        Returns:
            APIResponse with check-in confirmation and room key information
        """
        if isinstance(check_in_data, dict):
            check_in_data = CheckInRequest.model_validate(check_in_data)

        endpoint = (
            f"{self.api_domain}/v1/reservations/"
            + f"{check_in_data.confirmation_number}/checkin"
        )

        payload = {
            "roomNumber": check_in_data.room_number,
            "arrivalTime": check_in_data.arrival_time.isoformat()
            if check_in_data.arrival_time
            else None,
            "specialRequests": check_in_data.special_requests,
            "guestSignature": check_in_data.guest_signature,
            "idVerification": check_in_data.id_verification,
            "creditCardAuth": check_in_data.credit_card_authorization,
            "keyCardsIssued": check_in_data.key_cards_issued,
        }

        return await self.post(endpoint, json_data=payload)

    async def check_out_guest(
        self, checkout_data: CheckOutRequest | dict[str, Any]
    ) -> APIResponse:
        """
        Check out a guest and finalize their folio.

        Args:
            checkout_data: Check-out information including room number
                          and departure details

        Returns:
            APIResponse with checkout confirmation and final folio
        """
        if isinstance(checkout_data, dict):
            checkout_data = CheckOutRequest.model_validate(checkout_data)

        endpoint = (
            f"{self.api_domain}/v1/reservations/"
            + f"{checkout_data.confirmation_number}/checkout"
        )

        payload = {
            "roomNumber": checkout_data.room_number,
            "departureTime": checkout_data.departure_time.isoformat()
            if checkout_data.departure_time
            else None,
            "expressCheckout": checkout_data.express_checkout,
            "folioSettlement": checkout_data.folio_settlement,
            "keyCardsReturned": checkout_data.key_cards_returned,
            "roomDamages": checkout_data.room_damages,
            "guestSatisfaction": checkout_data.guest_satisfaction,
        }

        return await self.post(endpoint, json_data=payload)

    async def process_walk_in(
        self, walk_in_data: WalkInRequest | dict[str, Any]
    ) -> APIResponse:
        """
        Process a walk-in guest reservation and check-in.

        Args:
            walk_in_data: Walk-in guest information and room requirements

        Returns:
            APIResponse with new reservation and check-in details
        """
        if isinstance(walk_in_data, dict):
            walk_in_data = WalkInRequest.model_validate(walk_in_data)

        endpoint = f"{self.api_domain}/v1/walkins"

        payload = {
            "guestProfile": walk_in_data.guest_profile.model_dump(by_alias=True),
            "roomType": walk_in_data.room_type,
            "nights": walk_in_data.nights,
            "rateCode": walk_in_data.rate_code,
            "specialRequests": walk_in_data.special_requests,
            "corporateAccount": walk_in_data.corporate_account,
            "creditCardRequired": walk_in_data.credit_card_required,
        }

        return await self.post(endpoint, json_data=payload)

    # Room Management

    async def assign_room(
        self,
        confirmation_number: str,
        room_number: str,
        upgrade_reason: str | None = None,
    ) -> APIResponse:
        """
        Assign or reassign a room to a reservation.

        Args:
            confirmation_number: Reservation confirmation number
            room_number: Room number to assign
            upgrade_reason: Reason for room upgrade if applicable

        Returns:
            APIResponse with room assignment confirmation
        """
        endpoint = (
            f"{self.api_domain}/v1/reservations/{confirmation_number}/room-assignment"
        )

        payload = {
            "roomNumber": room_number,
            "upgradeReason": upgrade_reason,
            "assignedBy": "front_desk",  # Could be parameterized
            "assignedAt": datetime.now().isoformat(),
        }

        return await self.post(endpoint, json_data=payload)

    async def get_room_assignments(
        self, assignment_date: date | None = None
    ) -> APIResponse:
        """
        Get current room assignments for a specific date.

        Args:
            assignment_date: Date to check assignments for (defaults to today)

        Returns:
            APIResponse with room assignment details
        """
        if assignment_date is None:
            assignment_date = date.today()

        endpoint = f"{self.api_domain}/v1/room-assignments"
        params = {"date": assignment_date.isoformat()}

        return await self.get(endpoint, params=params)

    # Daily Reports

    async def get_arrivals_report(
        self,
        report_date: date | None = None,
        status_filter: str | None = None,
        room_type: str | None = None,
    ) -> APIResponse:
        """
        Get arrivals report for a specific date.

        Args:
            report_date: Date for the report (defaults to today)
            status_filter: Filter by status ('all', 'confirmed',
                          'checked_in', 'no_show')
            room_type: Filter by room type

        Returns:
            APIResponse with arrival details and statistics
        """
        if report_date is None:
            report_date = date.today()

        endpoint = f"{self.api_domain}/v1/reports/arrivals"
        params = {"date": report_date.isoformat()}

        if status_filter:
            params["status"] = status_filter
        if room_type:
            params["roomType"] = room_type

        return await self.get(endpoint, params=params)

    async def get_departures_report(
        self, report_date: date | None = None, checkout_status: str | None = None
    ) -> APIResponse:
        """
        Get departures report for a specific date.

        Args:
            report_date: Date for the report (defaults to today)
            checkout_status: Filter by checkout status ('all', 'pending', 'checked_out')

        Returns:
            APIResponse with departure details and outstanding balances
        """
        if report_date is None:
            report_date = date.today()

        endpoint = f"{self.api_domain}/v1/reports/departures"
        params = {"date": report_date.isoformat()}

        if checkout_status:
            params["status"] = checkout_status

        return await self.get(endpoint, params=params)

    async def get_occupancy_report(
        self, report_date: date | None = None
    ) -> APIResponse:
        """
        Get occupancy report showing current hotel occupancy.

        Args:
            report_date: Date for the report (defaults to today)

        Returns:
            APIResponse with occupancy statistics by room type
        """
        if report_date is None:
            report_date = date.today()

        endpoint = f"{self.api_domain}/v1/reports/occupancy"
        params = {"date": report_date.isoformat()}

        return await self.get(endpoint, params=params)

    async def get_no_show_report(self, report_date: date | None = None) -> APIResponse:
        """
        Get no-show report for reservations that didn't arrive.

        Args:
            report_date: Date for the report (defaults to today)

        Returns:
            APIResponse with no-show reservation details
        """
        if report_date is None:
            report_date = date.today()

        endpoint = f"{self.api_domain}/v1/reports/no-shows"
        params = {"date": report_date.isoformat()}

        return await self.get(endpoint, params=params)

    # Folio Operations

    async def get_guest_folio(
        self, confirmation_number: str, folio_type: str = "master"
    ) -> APIResponse:
        """
        Retrieve guest folio with all charges and payments.

        Args:
            confirmation_number: Reservation confirmation number
            folio_type: Type of folio ('master', 'individual', 'group')

        Returns:
            APIResponse with detailed folio information
        """
        endpoint = f"{self.api_domain}/v1/reservations/{confirmation_number}/folio"
        params = {"type": folio_type}

        return await self.get(endpoint, params=params)

    async def post_charge_to_room(
        self, confirmation_number: str, charge_data: dict[str, Any]
    ) -> APIResponse:
        """
        Post a charge to a guest's room folio.

        Args:
            confirmation_number: Reservation confirmation number
            charge_data: Charge details (amount, description, department)

        Returns:
            APIResponse with charge posting confirmation
        """
        endpoint = f"{self.api_domain}/v1/reservations/{confirmation_number}/charges"

        return await self.post(endpoint, json_data=charge_data)

    # Batch Operations

    async def batch_check_in(self, check_in_list: list[CheckInRequest]) -> APIResponse:
        """
        Process multiple check-ins in a single operation.

        Args:
            check_in_list: List of check-in requests

        Returns:
            APIResponse with batch operation results
        """
        # Process check-ins concurrently for better performance
        tasks = [self.check_in_guest(check_in_data) for check_in_data in check_in_list]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        successful = []
        failed = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append(
                    {
                        "confirmation_number": check_in_list[i].confirmation_number,
                        "error": str(result),
                    }
                )
            elif isinstance(result, APIResponse) and result.success:
                successful.append(result.data)
            elif isinstance(result, APIResponse):
                failed.append(
                    {
                        "confirmation_number": check_in_list[i].confirmation_number,
                        "error": result.error or "Unknown error",
                    }
                )

        return APIResponse(
            success=len(failed) == 0,
            data={
                "successful_checkins": successful,
                "failed_checkins": failed,
                "total_processed": len(check_in_list),
                "success_count": len(successful),
                "failure_count": len(failed),
            },
        )

    # Convenience Methods

    async def get_front_desk_summary(
        self, summary_date: date | None = None
    ) -> APIResponse:
        """
        Get comprehensive front desk summary for the day.

        Args:
            summary_date: Date for the summary (defaults to today)

        Returns:
            APIResponse with arrivals, departures, occupancy, and no-shows
        """
        if summary_date is None:
            summary_date = date.today()

        # Fetch all reports concurrently
        arrivals_task = self.get_arrivals_report(summary_date)
        departures_task = self.get_departures_report(summary_date)
        occupancy_task = self.get_occupancy_report(summary_date)
        no_shows_task = self.get_no_show_report(summary_date)

        arrivals, departures, occupancy, no_shows = await asyncio.gather(
            arrivals_task,
            departures_task,
            occupancy_task,
            no_shows_task,
            return_exceptions=True,
        )

        summary_data = {
            "date": summary_date.isoformat(),
            "arrivals": arrivals.data
            if isinstance(arrivals, APIResponse) and arrivals.success
            else None,
            "departures": departures.data
            if isinstance(departures, APIResponse) and departures.success
            else None,
            "occupancy": occupancy.data
            if isinstance(occupancy, APIResponse) and occupancy.success
            else None,
            "no_shows": no_shows.data
            if isinstance(no_shows, APIResponse) and no_shows.success
            else None,
        }

        return APIResponse(success=True, data=summary_data)

    async def search_in_house_guests(
        self, search_criteria: dict[str, Any] | None = None
    ) -> APIResponse:
        """
        Search for currently in-house guests.

        Args:
            search_criteria: Search criteria (guest name, room number, etc.)

        Returns:
            APIResponse with matching in-house guest information
        """
        endpoint = f"{self.api_domain}/v1/guests/in-house"
        params = search_criteria or {}

        return await self.get(endpoint, params=params)
