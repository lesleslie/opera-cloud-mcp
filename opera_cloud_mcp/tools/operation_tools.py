"""
Daily operations tools for OPERA Cloud MCP.

Provides MCP tools for front office operations, reports, and daily
management tasks through the OPERA Cloud Front Office API.
"""

from datetime import date
from typing import Any

from fastmcp import FastMCP

from opera_cloud_mcp.utils.client_factory import (
    create_activities_client,
    create_front_office_client,
)
from opera_cloud_mcp.utils.exceptions import ValidationError


def register_operation_tools(app: FastMCP):
    """Register all daily operations MCP tools."""

    @app.tool()
    async def check_in_guest(
        confirmation_number: str,
        hotel_id: str | None = None,
        room_number: str | None = None,
        special_requests: str | None = None,
        key_cards_issued: int = 2,
        id_verification: bool = True,
    ) -> dict[str, Any]:
        """
        Check in a guest to their assigned room.

        Args:
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier (uses default if not provided)
            room_number: Specific room number to assign (optional)
            special_requests: Any special requests from guest
            key_cards_issued: Number of key cards to issue
            id_verification: Whether ID was verified

        Returns:
            Dictionary containing check-in confirmation and room details
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if key_cards_issued < 1 or key_cards_issued > 10:
            raise ValidationError("key_cards_issued must be between 1 and 10")

        client = create_front_office_client(hotel_id=hotel_id)

        checkin_data = {
            "confirmationNumber": confirmation_number,
            "roomNumber": room_number,
            "specialRequests": special_requests,
            "keyCardsIssued": key_cards_issued,
            "idVerification": id_verification,
            "checkedInBy": "mcp_agent",
        }

        response = await client.check_in_guest(checkin_data)

        if response.success:
            return {
                "success": True,
                "checkin_details": response.data,
                "confirmation_number": confirmation_number,
                "room_number": response.data.get("assignedRoom"),
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def check_out_guest(
        confirmation_number: str,
        hotel_id: str | None = None,
        express_checkout: bool = False,
        key_cards_returned: int = 0,
        room_damages: str | None = None,
        guest_satisfaction: int | None = None,
    ) -> dict[str, Any]:
        """
        Check out a guest and finalize their folio.

        Args:
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier (uses default if not provided)
            express_checkout: Whether this is express checkout
            key_cards_returned: Number of key cards returned
            room_damages: Any room damages noted
            guest_satisfaction: Guest satisfaction rating (1-5)

        Returns:
            Dictionary containing checkout confirmation and final folio
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if guest_satisfaction is not None and (
            guest_satisfaction < 1 or guest_satisfaction > 5
        ):
            raise ValidationError("guest_satisfaction must be between 1 and 5")

        client = create_front_office_client(hotel_id=hotel_id)

        checkout_data = {
            "confirmationNumber": confirmation_number,
            "expressCheckout": express_checkout,
            "keyCardsReturned": key_cards_returned,
            "roomDamages": room_damages,
            "guestSatisfaction": guest_satisfaction,
            "checkedOutBy": "mcp_agent",
        }

        response = await client.check_out_guest(checkout_data)

        if response.success:
            return {
                "success": True,
                "checkout_details": response.data,
                "confirmation_number": confirmation_number,
                "final_balance": response.data.get("finalBalance"),
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def process_walk_in(
        guest_first_name: str,
        guest_last_name: str,
        room_type: str,
        nights: int,
        rate_code: str,
        hotel_id: str | None = None,
        guest_email: str | None = None,
        guest_phone: str | None = None,
        special_requests: str | None = None,
        credit_card_required: bool = True,
    ) -> dict[str, Any]:
        """
        Process a walk-in guest reservation and check-in.

        Args:
            guest_first_name: Guest's first name
            guest_last_name: Guest's last name
            room_type: Requested room type
            nights: Number of nights staying
            rate_code: Rate code to apply
            hotel_id: Hotel identifier (uses default if not provided)
            guest_email: Guest's email address
            guest_phone: Guest's phone number
            special_requests: Any special requests
            credit_card_required: Whether credit card is required

        Returns:
            Dictionary containing walk-in reservation and check-in details
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if nights < 1:
            raise ValidationError("nights must be at least 1")

        client = create_front_office_client(hotel_id=hotel_id)

        guest_profile = {
            "firstName": guest_first_name,
            "lastName": guest_last_name,
            "email": guest_email,
            "phoneNumber": guest_phone,
        }

        walkin_data = {
            "guestProfile": guest_profile,
            "roomType": room_type,
            "nights": nights,
            "rateCode": rate_code,
            "specialRequests": special_requests,
            "creditCardRequired": credit_card_required,
            "processedBy": "mcp_agent",
        }

        response = await client.process_walk_in(walkin_data)

        if response.success:
            return {
                "success": True,
                "walkin_details": response.data,
                "confirmation_number": response.data.get("confirmationNumber"),
                "room_number": response.data.get("assignedRoom"),
                "guest_name": f"{guest_first_name} {guest_last_name}",
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "guest_name": f"{guest_first_name} {guest_last_name}",
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_arrivals_report(
        report_date: str | None = None,
        hotel_id: str | None = None,
        status_filter: str | None = None,
        room_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Get today's arrivals report with guest details.

        Args:
            report_date: Date for report in YYYY-MM-DD format (defaults to today)
            hotel_id: Hotel identifier (uses default if not provided)
            status_filter: Filter by status (all, confirmed, checked_in, no_show)
            room_type: Filter by room type

        Returns:
            Dictionary containing arrivals information and statistics
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_front_office_client(hotel_id=hotel_id)

        if not report_date:
            report_date = date.today().isoformat()

        response = await client.get_arrivals_report(
            report_date=date.fromisoformat(report_date),
            status_filter=status_filter,
            room_type=room_type,
        )

        if response.success:
            return {
                "success": True,
                "arrivals": response.data.get("arrivals", []),
                "summary": response.data.get("summary", {}),
                "report_date": report_date,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "report_date": report_date,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_departures_report(
        report_date: str | None = None,
        hotel_id: str | None = None,
        checkout_status: str | None = None,
    ) -> dict[str, Any]:
        """
        Get today's departures report with checkout status.

        Args:
            report_date: Date for report in YYYY-MM-DD format (defaults to today)
            hotel_id: Hotel identifier (uses default if not provided)
            checkout_status: Filter by status (all, pending, checked_out, late_checkout)

        Returns:
            Dictionary containing departures and outstanding balances
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_front_office_client(hotel_id=hotel_id)

        if not report_date:
            report_date = date.today().isoformat()

        response = await client.get_departures_report(
            report_date=date.fromisoformat(report_date), checkout_status=checkout_status
        )

        if response.success:
            return {
                "success": True,
                "departures": response.data.get("departures", []),
                "summary": response.data.get("summary", {}),
                "report_date": report_date,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "report_date": report_date,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_occupancy_report(
        report_date: str | None = None, hotel_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get hotel occupancy statistics and room status summary.

        Args:
            report_date: Date for report in YYYY-MM-DD format (defaults to today)
            hotel_id: Hotel identifier (uses default if not provided)

        Returns:
            Dictionary containing occupancy statistics by room type
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_front_office_client(hotel_id=hotel_id)

        if not report_date:
            report_date = date.today().isoformat()

        response = await client.get_occupancy_report(
            report_date=date.fromisoformat(report_date)
        )

        if response.success:
            return {
                "success": True,
                "occupancy": response.data,
                "report_date": report_date,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "report_date": report_date,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_no_show_report(
        report_date: str | None = None, hotel_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get no-show report for reservations that didn't arrive.

        Args:
            report_date: Date for report in YYYY-MM-DD format (defaults to today)
            hotel_id: Hotel identifier (uses default if not provided)

        Returns:
            Dictionary containing no-show reservation details
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_front_office_client(hotel_id=hotel_id)

        if not report_date:
            report_date = date.today().isoformat()

        response = await client.get_no_show_report(
            report_date=date.fromisoformat(report_date)
        )

        if response.success:
            return {
                "success": True,
                "no_shows": response.data.get("no_shows", []),
                "summary": response.data.get("summary", {}),
                "report_date": report_date,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "report_date": report_date,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def assign_room(
        confirmation_number: str,
        room_number: str,
        hotel_id: str | None = None,
        upgrade_reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Assign or reassign a room to a reservation.

        Args:
            confirmation_number: Reservation confirmation number
            room_number: Room number to assign
            hotel_id: Hotel identifier (uses default if not provided)
            upgrade_reason: Reason for room upgrade if applicable

        Returns:
            Dictionary containing room assignment confirmation
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_front_office_client(hotel_id=hotel_id)

        response = await client.assign_room(
            confirmation_number=confirmation_number,
            room_number=room_number,
            upgrade_reason=upgrade_reason,
        )

        if response.success:
            return {
                "success": True,
                "assignment_details": response.data,
                "confirmation_number": confirmation_number,
                "room_number": room_number,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "confirmation_number": confirmation_number,
                "room_number": room_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_in_house_guests(
        hotel_id: str | None = None,
        search_term: str | None = None,
        room_number: str | None = None,
        vip_only: bool = False,
    ) -> dict[str, Any]:
        """
        Search for currently in-house guests.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            search_term: Search by guest name, email, or phone
            room_number: Filter by specific room number
            vip_only: Show only VIP guests

        Returns:
            Dictionary containing in-house guest information
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_front_office_client(hotel_id=hotel_id)

        search_criteria = {}
        if search_term:
            search_criteria["searchTerm"] = search_term
        if room_number:
            search_criteria["roomNumber"] = room_number
        if vip_only:
            search_criteria["vipOnly"] = True

        response = await client.search_in_house_guests(search_criteria)

        if response.success:
            return {
                "success": True,
                "in_house_guests": response.data.get("guests", []),
                "total_count": response.data.get("total_count", 0),
                "search_criteria": search_criteria,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "search_criteria": search_criteria,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_front_desk_summary(
        summary_date: str | None = None, hotel_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get comprehensive front desk summary for operational overview.

        Args:
            summary_date: Date for summary in YYYY-MM-DD format (defaults to today)
            hotel_id: Hotel identifier (uses default if not provided)

        Returns:
            Dictionary containing arrivals, departures, occupancy, and no-shows
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_front_office_client(hotel_id=hotel_id)

        if not summary_date:
            summary_date = date.today().isoformat()

        response = await client.get_front_desk_summary(
            summary_date=date.fromisoformat(summary_date)
        )

        if response.success:
            return {
                "success": True,
                "summary": response.data,
                "summary_date": summary_date,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "summary_date": summary_date,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def create_activity_booking(
        activity_id: str,
        guest_name: str,
        booking_date: str,
        start_time: str,
        participants: int,
        hotel_id: str | None = None,
        guest_room: str | None = None,
        special_requirements: str | None = None,
    ) -> dict[str, Any]:
        """
        Book a hotel activity for a guest.

        Args:
            activity_id: Activity identifier
            guest_name: Guest's name
            booking_date: Date for activity in YYYY-MM-DD format
            start_time: Start time in HH:MM format
            participants: Number of participants
            hotel_id: Hotel identifier (uses default if not provided)
            guest_room: Guest's room number
            special_requirements: Any special requirements

        Returns:
            Dictionary containing activity booking confirmation
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if participants < 1:
            raise ValidationError("participants must be at least 1")

        client = create_activities_client(hotel_id=hotel_id)

        booking_data = {
            "activityId": activity_id,
            "guestName": guest_name,
            "bookingDate": booking_date,
            "startTime": start_time,
            "participants": participants,
            "guestRoom": guest_room,
            "specialRequirements": special_requirements,
            "bookedBy": "mcp_agent",
        }

        response = await client.create_activity_booking(booking_data)

        if response.success:
            return {
                "success": True,
                "booking": response.data,
                "booking_id": response.data.get("bookingId"),
                "activity_id": activity_id,
                "guest_name": guest_name,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "activity_id": activity_id,
                "guest_name": guest_name,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def create_dining_reservation(
        restaurant_id: str,
        guest_name: str,
        reservation_date: str,
        reservation_time: str,
        party_size: int,
        hotel_id: str | None = None,
        guest_room: str | None = None,
        special_requests: str | None = None,
        dietary_restrictions: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a dining reservation for hotel restaurant.

        Args:
            restaurant_id: Restaurant identifier
            guest_name: Guest's name
            reservation_date: Date for reservation in YYYY-MM-DD format
            reservation_time: Time for reservation in HH:MM format
            party_size: Number of people in the party
            hotel_id: Hotel identifier (uses default if not provided)
            guest_room: Guest's room number
            special_requests: Any special requests
            dietary_restrictions: Dietary restrictions or allergies

        Returns:
            Dictionary containing dining reservation confirmation
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if party_size < 1:
            raise ValidationError("party_size must be at least 1")

        client = create_activities_client(hotel_id=hotel_id)

        reservation_data = {
            "restaurantId": restaurant_id,
            "guestName": guest_name,
            "reservationDate": reservation_date,
            "reservationTime": reservation_time,
            "partySize": party_size,
            "guestRoom": guest_room,
            "specialRequests": special_requests,
            "dietaryRestrictions": dietary_restrictions,
            "reservedBy": "mcp_agent",
        }

        response = await client.create_dining_reservation(reservation_data)

        if response.success:
            return {
                "success": True,
                "reservation": response.data,
                "reservation_id": response.data.get("reservationId"),
                "restaurant_id": restaurant_id,
                "guest_name": guest_name,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "restaurant_id": restaurant_id,
                "guest_name": guest_name,
                "hotel_id": hotel_id,
            }
