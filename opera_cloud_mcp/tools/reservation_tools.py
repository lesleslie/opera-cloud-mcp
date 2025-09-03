"""
Reservation management tools for OPERA Cloud MCP.

Provides MCP tools for searching, creating, modifying, and managing
hotel reservations through the OPERA Cloud Reservations API.
"""

from datetime import date, datetime
from typing import Any

from fastmcp import FastMCP

from opera_cloud_mcp.utils.client_factory import create_reservations_client
from opera_cloud_mcp.utils.exceptions import ValidationError


def register_reservation_tools(app: FastMCP):
    """Register all reservation-related MCP tools."""

    @app.tool()
    async def search_reservations(
        hotel_id: str | None = None,
        arrival_date: str | None = None,
        departure_date: str | None = None,
        guest_name: str | None = None,
        confirmation_number: str | None = None,
        status: str | None = None,
        room_type: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Search for hotel reservations by various criteria.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            arrival_date: Arrival date in YYYY-MM-DD format
            departure_date: Departure date in YYYY-MM-DD format
            guest_name: Guest name (partial match supported)
            confirmation_number: Exact confirmation number
            status: Reservation status (confirmed, cancelled, no_show, etc.)
            room_type: Room type code
            limit: Maximum results to return (1-100)

        Returns:
            Dictionary containing search results and metadata
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if limit < 1 or limit > 100:
            raise ValidationError("limit must be between 1 and 100")

        client = create_reservations_client(hotel_id=hotel_id)

        search_criteria = {}
        if arrival_date:
            search_criteria["arrival_date"] = arrival_date
        if departure_date:
            search_criteria["departure_date"] = departure_date
        if guest_name:
            search_criteria["guest_name"] = guest_name
        if confirmation_number:
            search_criteria["confirmation_number"] = confirmation_number
        if status:
            search_criteria["status"] = status
        if room_type:
            search_criteria["room_type"] = room_type

        search_criteria["limit"] = limit

        response = await client.search_reservations(search_criteria)

        if response.success:
            return {
                "success": True,
                "reservations": response.data.get("reservations", []),
                "total_count": response.data.get("total_count", 0),
                "hotel_id": hotel_id,
                "search_criteria": search_criteria,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "hotel_id": hotel_id,
                "search_criteria": search_criteria,
            }

    @app.tool()
    async def get_reservation(
        confirmation_number: str,
        hotel_id: str | None = None,
        include_folios: bool = False,
        include_history: bool = False,
    ) -> dict[str, Any]:
        """
        Get detailed information for a specific reservation.

        Args:
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier (uses default if not provided)
            include_folios: Include folio information in response
            include_history: Include reservation change history

        Returns:
            Dictionary containing reservation details
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_reservations_client(hotel_id=hotel_id)

        response = await client.get_reservation(
            confirmation_number=confirmation_number,
            include_folios=include_folios,
            include_history=include_history,
        )

        if response.success:
            return {
                "success": True,
                "reservation": response.data,
                "confirmation_number": confirmation_number,
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
    async def create_reservation(
        guest_first_name: str,
        guest_last_name: str,
        arrival_date: str,
        departure_date: str,
        room_type: str,
        rate_code: str,
        hotel_id: str | None = None,
        guest_email: str | None = None,
        guest_phone: str | None = None,
        special_requests: str | None = None,
        guarantee_type: str = "credit_card",
        credit_card_number: str | None = None,
        market_segment: str | None = None,
        source_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new hotel reservation.

        Args:
            guest_first_name: Guest's first name
            guest_last_name: Guest's last name
            arrival_date: Arrival date in YYYY-MM-DD format
            departure_date: Departure date in YYYY-MM-DD format
            room_type: Room type code
            rate_code: Rate code to use for pricing
            hotel_id: Hotel identifier (uses default if not provided)
            guest_email: Guest's email address
            guest_phone: Guest's phone number
            special_requests: Special requests or notes
            guarantee_type: Guarantee type (credit_card, corporate, cash)
            credit_card_number: Credit card for guarantee (if applicable)
            market_segment: Market segment code
            source_code: Booking source code

        Returns:
            Dictionary containing new reservation details
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        # Validate dates
        try:
            arr_date = date.fromisoformat(arrival_date)
            dep_date = date.fromisoformat(departure_date)
            if arr_date >= dep_date:
                raise ValidationError("departure_date must be after arrival_date")
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}")

        client = create_reservations_client(hotel_id=hotel_id)

        guest_profile = {
            "firstName": guest_first_name,
            "lastName": guest_last_name,
            "email": guest_email,
            "phoneNumber": guest_phone,
        }

        reservation_data = {
            "guestProfile": guest_profile,
            "arrivalDate": arrival_date,
            "departureDate": departure_date,
            "roomType": room_type,
            "rateCode": rate_code,
            "specialRequests": special_requests,
            "guaranteeType": guarantee_type,
            "creditCardNumber": credit_card_number,
            "marketSegment": market_segment,
            "sourceCode": source_code,
        }

        response = await client.create_reservation(reservation_data)

        if response.success:
            return {
                "success": True,
                "reservation": response.data,
                "confirmation_number": response.data.get("confirmationNumber"),
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "hotel_id": hotel_id,
                "guest_name": f"{guest_first_name} {guest_last_name}",
            }

    @app.tool()
    async def modify_reservation(
        confirmation_number: str,
        hotel_id: str | None = None,
        arrival_date: str | None = None,
        departure_date: str | None = None,
        room_type: str | None = None,
        rate_code: str | None = None,
        special_requests: str | None = None,
        guest_email: str | None = None,
        guest_phone: str | None = None,
    ) -> dict[str, Any]:
        """
        Modify an existing hotel reservation.

        Args:
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier (uses default if not provided)
            arrival_date: New arrival date in YYYY-MM-DD format
            departure_date: New departure date in YYYY-MM-DD format
            room_type: New room type code
            rate_code: New rate code
            special_requests: Updated special requests
            guest_email: Updated guest email
            guest_phone: Updated guest phone

        Returns:
            Dictionary containing updated reservation details
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        # Validate dates if provided
        if arrival_date and departure_date:
            try:
                arr_date = date.fromisoformat(arrival_date)
                dep_date = date.fromisoformat(departure_date)
                if arr_date >= dep_date:
                    raise ValidationError("departure_date must be after arrival_date")
            except ValueError as e:
                raise ValidationError(f"Invalid date format: {e}")

        client = create_reservations_client(hotel_id=hotel_id)

        modifications = {}
        if arrival_date:
            modifications["arrivalDate"] = arrival_date
        if departure_date:
            modifications["departureDate"] = departure_date
        if room_type:
            modifications["roomType"] = room_type
        if rate_code:
            modifications["rateCode"] = rate_code
        if special_requests:
            modifications["specialRequests"] = special_requests
        if guest_email:
            modifications["guestProfile"] = {"email": guest_email}
        if guest_phone:
            if "guestProfile" not in modifications:
                modifications["guestProfile"] = {}
            modifications["guestProfile"]["phoneNumber"] = guest_phone

        if not modifications:
            raise ValidationError(
                "At least one field must be provided for modification"
            )

        response = await client.modify_reservation(confirmation_number, modifications)

        if response.success:
            return {
                "success": True,
                "reservation": response.data,
                "confirmation_number": confirmation_number,
                "modifications_applied": modifications,
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
    async def cancel_reservation(
        confirmation_number: str,
        cancellation_reason: str,
        hotel_id: str | None = None,
        charge_cancellation_fee: bool = False,
        cancellation_fee_amount: float | None = None,
    ) -> dict[str, Any]:
        """
        Cancel a hotel reservation.

        Args:
            confirmation_number: Reservation confirmation number
            cancellation_reason: Reason for cancellation
            hotel_id: Hotel identifier (uses default if not provided)
            charge_cancellation_fee: Whether to charge a cancellation fee
            cancellation_fee_amount: Cancellation fee amount if applicable

        Returns:
            Dictionary containing cancellation confirmation
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_reservations_client(hotel_id=hotel_id)

        cancellation_data = {
            "cancellationReason": cancellation_reason,
            "chargeCancellationFee": charge_cancellation_fee,
            "cancellationFeeAmount": cancellation_fee_amount,
            "cancelledAt": datetime.now().isoformat(),
            "cancelledBy": "mcp_agent",
        }

        response = await client.cancel_reservation(
            confirmation_number, cancellation_data
        )

        if response.success:
            return {
                "success": True,
                "cancellation": response.data,
                "confirmation_number": confirmation_number,
                "cancellation_reason": cancellation_reason,
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
    async def check_room_availability(
        arrival_date: str,
        departure_date: str,
        hotel_id: str | None = None,
        room_type: str | None = None,
        rate_code: str | None = None,
        number_of_rooms: int = 1,
        adults: int = 1,
        children: int = 0,
    ) -> dict[str, Any]:
        """
        Check room availability and rates for given dates.

        Args:
            arrival_date: Arrival date in YYYY-MM-DD format
            departure_date: Departure date in YYYY-MM-DD format
            hotel_id: Hotel identifier (uses default if not provided)
            room_type: Specific room type to check (optional)
            rate_code: Specific rate code to check (optional)
            number_of_rooms: Number of rooms needed
            adults: Number of adults
            children: Number of children

        Returns:
            Dictionary containing availability and rate information
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        # Validate dates
        try:
            arr_date = date.fromisoformat(arrival_date)
            dep_date = date.fromisoformat(departure_date)
            if arr_date >= dep_date:
                raise ValidationError("departure_date must be after arrival_date")
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}")

        if number_of_rooms < 1:
            raise ValidationError("number_of_rooms must be at least 1")

        client = create_reservations_client(hotel_id=hotel_id)

        availability_criteria = {
            "arrivalDate": arrival_date,
            "departureDate": departure_date,
            "numberOfRooms": number_of_rooms,
            "adults": adults,
            "children": children,
        }

        if room_type:
            availability_criteria["roomType"] = room_type
        if rate_code:
            availability_criteria["rateCode"] = rate_code

        response = await client.check_availability(availability_criteria)

        if response.success:
            return {
                "success": True,
                "availability": response.data,
                "search_criteria": availability_criteria,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "search_criteria": availability_criteria,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_reservation_history(
        guest_email: str | None = None,
        guest_phone: str | None = None,
        guest_name: str | None = None,
        hotel_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get reservation history for a guest.

        Args:
            guest_email: Guest's email address
            guest_phone: Guest's phone number
            guest_name: Guest's name
            hotel_id: Hotel identifier (uses default if not provided)
            date_from: Start date for history in YYYY-MM-DD format
            date_to: End date for history in YYYY-MM-DD format
            limit: Maximum results to return

        Returns:
            Dictionary containing guest's reservation history
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        if not any([guest_email, guest_phone, guest_name]):
            raise ValidationError(
                "At least one guest identifier (email, phone, or name) must be provided"
            )

        client = create_reservations_client(hotel_id=hotel_id)

        history_criteria = {"limit": limit}
        if guest_email:
            history_criteria["guestEmail"] = guest_email
        if guest_phone:
            history_criteria["guestPhone"] = guest_phone
        if guest_name:
            history_criteria["guestName"] = guest_name
        if date_from:
            history_criteria["dateFrom"] = date_from
        if date_to:
            history_criteria["dateTo"] = date_to

        response = await client.get_guest_reservation_history(history_criteria)

        if response.success:
            return {
                "success": True,
                "history": response.data.get("reservations", []),
                "total_count": response.data.get("total_count", 0),
                "search_criteria": history_criteria,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "search_criteria": history_criteria,
                "hotel_id": hotel_id,
            }
