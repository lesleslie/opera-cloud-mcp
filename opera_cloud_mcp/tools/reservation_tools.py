"""
Reservation management tools for OPERA Cloud MCP.

Provides MCP tools for searching, creating, modifying, and managing
hotel reservations through the OPERA Cloud Reservations API.
"""

import inspect
from datetime import date, datetime
from typing import Any, cast

from fastmcp import FastMCP

from opera_cloud_mcp.utils.client_factory import create_reservations_client
from opera_cloud_mcp.utils.exceptions import ValidationError
from opera_cloud_mcp.utils.validators import validate_confirmation_number


def _get_reservations_client(hotel_id: str | None = None):
    """Internal function to get a reservations client, used for testing/mocking."""
    return create_reservations_client(hotel_id)


def _validate_search_reservations_params(
    hotel_id: str | None,
    limit: int,
    confirmation_number: str | None = None,
) -> None:
    """Validate search reservations parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    if limit < 1 or limit > 100:
        raise ValidationError("limit must be between 1 and 100")

    if confirmation_number:
        validate_confirmation_number(confirmation_number)


def _build_search_criteria(
    arrival_date: str | None,
    departure_date: str | None,
    guest_name: str | None,
    confirmation_number: str | None,
    status: str | None,
    room_type: str | None,
    limit: int,
) -> dict[str, Any]:
    """Build search criteria dictionary."""
    search_criteria: dict[str, Any] = {}
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
    return search_criteria


def _validate_get_reservation_params(hotel_id: str | None) -> None:
    """Validate get reservation parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _validate_create_reservation_dates(arrival_date: str, departure_date: str) -> None:
    """Validate reservation dates."""
    try:
        arr_date = date.fromisoformat(arrival_date)
        dep_date = date.fromisoformat(departure_date)
        if arr_date >= dep_date:
            raise ValidationError("departure_date must be after arrival_date")
    except ValueError as e:
        raise ValidationError(f"Invalid date format: {e}") from e


def _validate_create_reservation_params(
    hotel_id: str | None, arrival_date: str, departure_date: str
) -> None:
    """Validate create reservation parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    _validate_create_reservation_dates(arrival_date, departure_date)


def _build_guest_profile(
    guest_first_name: str,
    guest_last_name: str,
    guest_email: str | None,
    guest_phone: str | None,
) -> dict[str, Any]:
    """Build guest profile dictionary."""
    return {
        "firstName": guest_first_name,
        "lastName": guest_last_name,
        "email": guest_email,
        "phoneNumber": guest_phone,
    }


def _build_reservation_data(
    guest_profile: dict[str, Any],
    arrival_date: str,
    departure_date: str,
    room_type: str,
    rate_code: str,
    special_requests: str | None,
    guarantee_type: str,
    credit_card_number: str | None,
    market_segment: str | None,
    source_code: str | None,
) -> dict[str, Any]:
    """Build reservation data dictionary."""
    return {
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


def _validate_modify_reservation_dates(
    arrival_date: str | None, departure_date: str | None
) -> None:
    """Validate modification dates."""
    if arrival_date and departure_date:
        try:
            arr_date = date.fromisoformat(arrival_date)
            dep_date = date.fromisoformat(departure_date)
            if arr_date >= dep_date:
                raise ValidationError("departure_date must be after arrival_date")
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}") from e


def _validate_modify_reservation_params(
    hotel_id: str | None, arrival_date: str | None, departure_date: str | None
) -> None:
    """Validate modify reservation parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    _validate_modify_reservation_dates(arrival_date, departure_date)


def _build_modifications(
    arrival_date: str | None,
    departure_date: str | None,
    room_type: str | None,
    rate_code: str | None,
    special_requests: str | None,
    guest_email: str | None,
    guest_phone: str | None,
) -> dict[str, Any]:
    """Build modifications dictionary."""
    modifications: dict[str, Any] = {}
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

    return modifications


def _validate_cancel_reservation_params(hotel_id: str | None) -> None:
    """Validate cancel reservation parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _build_cancellation_data(
    cancellation_reason: str,
    charge_cancellation_fee: bool,
    cancellation_fee_amount: float | None,
) -> dict[str, Any]:
    """Build cancellation data dictionary."""
    return {
        "cancellationReason": cancellation_reason,
        "chargeCancellationFee": charge_cancellation_fee,
        "cancellationFeeAmount": cancellation_fee_amount,
        "cancelledAt": datetime.now().isoformat(),
        "cancelledBy": "mcp_agent",
    }


def _validate_check_room_availability_dates(
    arrival_date: str, departure_date: str
) -> None:
    """Validate room availability dates."""
    try:
        arr_date = date.fromisoformat(arrival_date)
        dep_date = date.fromisoformat(departure_date)
        if arr_date >= dep_date:
            raise ValidationError("departure_date must be after arrival_date")
    except ValueError as e:
        raise ValidationError(f"Invalid date format: {e}") from e


def _validate_check_room_availability_params(
    hotel_id: str | None, arrival_date: str, departure_date: str, number_of_rooms: int
) -> None:
    """Validate check room availability parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    _validate_check_room_availability_dates(arrival_date, departure_date)

    if number_of_rooms < 1:
        raise ValidationError("number_of_rooms must be at least 1")


def _build_availability_criteria(
    arrival_date: str,
    departure_date: str,
    number_of_rooms: int,
    adults: int,
    children: int,
    room_type: str | None,
    rate_code: str | None,
) -> dict[str, Any]:
    """Build availability criteria dictionary."""
    availability_criteria: dict[str, Any] = {
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

    return availability_criteria


def _validate_get_reservation_history_params(
    hotel_id: str | None,
    guest_email: str | None,
    guest_phone: str | None,
    guest_name: str | None,
) -> None:
    """Validate get reservation history parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    if not any([guest_email, guest_phone, guest_name]):
        raise ValidationError(
            "At least one guest identifier (email, phone, or name) must be provided"
        )


def _build_history_criteria(
    guest_email: str | None,
    guest_phone: str | None,
    guest_name: str | None,
    date_from: str | None,
    date_to: str | None,
    limit: int,
) -> dict[str, Any]:
    """Build history criteria dictionary."""
    history_criteria: dict[str, Any] = {"limit": limit}
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

    return history_criteria


async def _maybe_await(value: Any) -> Any:
    """Await coroutine-like values and return sync values unchanged."""
    if inspect.isawaitable(value):
        return await value
    return value


def _register_search_reservations_tool(app: FastMCP) -> Any:
    """Register search reservations tool."""

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
        _validate_search_reservations_params(hotel_id, limit, confirmation_number)

        client = _get_reservations_client(hotel_id=hotel_id)

        search_criteria = _build_search_criteria(
            arrival_date,
            departure_date,
            guest_name,
            confirmation_number,
            status,
            room_type,
            limit,
        )

        response = await client.search_reservations(search_criteria)

        if response.success:
            data = cast("dict[str, Any]", response.data or {})
            return {
                "success": True,
                "reservations": data.get("reservations", []),
                "total_count": data.get("total_count", 0),
                "hotel_id": hotel_id,
                "search_criteria": search_criteria,
            }
        return {
            "success": False,
            "error": response.error,
            "hotel_id": hotel_id,
            "search_criteria": search_criteria,
        }

    return search_reservations


def _register_get_reservation_tool(app: FastMCP) -> Any:
    """Register get reservation tool."""

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
        _validate_get_reservation_params(hotel_id)

        client = _get_reservations_client(hotel_id=hotel_id)

        response = await client.get_reservation(
            confirmation_number=confirmation_number,
            include_history=include_history,
            include_charges=include_folios,  # Map include_folios to include_charges
        )

        if response.success:
            return {
                "success": True,
                "reservation": response.data,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "confirmation_number": confirmation_number,
            "hotel_id": hotel_id,
        }

    return get_reservation


def _register_create_reservation_tool(app: FastMCP) -> Any:
    """Register create reservation tool."""

    @app.tool()
    async def create_reservation(
        guest_profile: dict[str, Any],
        arrival_date: str,
        departure_date: str,
        room_type: str,
        rate_code: str,
        hotel_id: str | None = None,
        adults: int = 1,
        children: int = 0,
        special_requests: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new hotel reservation.

        Args:
            guest_profile: Guest information including name, contact details
            arrival_date: Arrival date in YYYY-MM-DD format
            departure_date: Departure date in YYYY-MM-DD format
            room_type: Room type code
            rate_code: Rate code for pricing
            hotel_id: Hotel identifier (uses default if not provided)
            adults: Number of adults
            children: Number of children
            special_requests: Any special requests or notes

        Returns:
            Dictionary containing reservation confirmation details
        """
        _validate_create_reservation_params(hotel_id, arrival_date, departure_date)

        client = _get_reservations_client(hotel_id=hotel_id)

        reservation_data = _build_reservation_data(
            guest_profile,
            arrival_date,
            departure_date,
            room_type,
            rate_code,
            special_requests,
            "CC",  # guarantee_type - using CC as default
            None,  # credit_card_number - optional
            None,  # market_segment - optional
            None,  # source_code - optional
        )

        response = await client.create_reservation(reservation_data)

        if response.success:
            return {
                "success": True,
                "reservation": response.data,
                "confirmation_number": response.data.get("confirmationNumber")
                if response.data
                else None,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "hotel_id": hotel_id,
        }

    return create_reservation


def _register_modify_reservation_tool(app: FastMCP) -> Any:
    """Register modify reservation tool."""

    @app.tool()
    async def modify_reservation(
        confirmation_number: str,
        hotel_id: str | None = None,
        room_type: str | None = None,
        rate_code: str | None = None,
        departure_date: str | None = None,
        adults: int | None = None,
        children: int | None = None,
        special_requests: str | None = None,
    ) -> dict[str, Any]:
        """
        Modify an existing reservation.

        Args:
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier (uses default if not provided)
            room_type: New room type code (if changing)
            rate_code: New rate code (if changing)
            departure_date: New departure date (if extending)
            adults: New number of adults (if changing)
            children: New number of children (if changing)
            special_requests: Updated special requests

        Returns:
            Dictionary containing modification confirmation
        """
        _validate_modify_reservation_params(hotel_id, None, None)

        client = _get_reservations_client(hotel_id=hotel_id)

        modification_data = _build_modifications(
            None,  # arrival_date
            departure_date,
            room_type,
            rate_code,
            str(adults) if adults is not None else None,
            str(children) if children is not None else None,
            special_requests,
        )

        response = await client.modify_reservation(
            confirmation_number, modification_data
        )

        if response.success:
            return {
                "success": True,
                "reservation": response.data,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "confirmation_number": confirmation_number,
            "hotel_id": hotel_id,
        }

    return modify_reservation


def _register_cancel_reservation_tool(app: FastMCP) -> Any:
    """Register cancel reservation tool."""

    @app.tool()
    async def cancel_reservation(
        confirmation_number: str,
        hotel_id: str | None = None,
        cancellation_reason: str | None = None,
        charge_penalty: bool = False,
        notify_guest: bool = True,
    ) -> dict[str, Any]:
        """
        Cancel an existing reservation.

        Args:
            confirmation_number: Reservation confirmation number
            hotel_id: Hotel identifier (uses default if not provided)
            cancellation_reason: Reason for cancellation
            charge_penalty: Whether to charge cancellation penalty
            notify_guest: Whether to send cancellation notification to guest

        Returns:
            Dictionary containing cancellation confirmation
        """
        _validate_cancel_reservation_params(hotel_id)

        client = _get_reservations_client(hotel_id=hotel_id)

        cancellation_data = _build_cancellation_data(
            cancellation_reason or "No reason provided",
            charge_penalty,
            50.0 if notify_guest else None,
        )

        response = await client.cancel_reservation(
            confirmation_number, cancellation_data
        )

        if response.success:
            return {
                "success": True,
                "cancellation_details": response.data,
                "confirmation_number": confirmation_number,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "confirmation_number": confirmation_number,
            "hotel_id": hotel_id,
        }

    return cancel_reservation


def _register_check_room_availability_tool(app: FastMCP) -> None:
    """Register availability tool."""

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
        _validate_check_room_availability_params(
            hotel_id, arrival_date, departure_date, number_of_rooms
        )

        client = _get_reservations_client(hotel_id=hotel_id)

        availability_criteria = _build_availability_criteria(
            arrival_date,
            departure_date,
            number_of_rooms,
            adults,
            children,
            room_type,
            rate_code,
        )

        response = await client.check_availability(availability_criteria)

        if response.success:
            return {
                "success": True,
                "availability": response.data,
                "search_criteria": availability_criteria,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "search_criteria": availability_criteria,
            "hotel_id": hotel_id,
        }


def _register_reservation_history_tool(app: FastMCP) -> None:
    """Register reservation history tool."""

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
        _validate_get_reservation_history_params(
            hotel_id, guest_email, guest_phone, guest_name
        )

        client = _get_reservations_client(hotel_id=hotel_id)

        history_criteria = _build_history_criteria(
            guest_email, guest_phone, guest_name, date_from, date_to, limit
        )

        response = await client.get_guest_reservation_history(history_criteria)

        if response.success:
            data = cast("dict[str, Any]", response.data or {})
            return {
                "success": True,
                "history": data.get("reservations", []),
                "total_count": data.get("total_count", 0),
                "search_criteria": history_criteria,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "search_criteria": history_criteria,
            "hotel_id": hotel_id,
        }


def _register_bulk_reservation_tools(app: FastMCP) -> None:
    """Register bulk reservation tools."""

    @app.tool()
    async def bulk_create_reservations(
        reservations_data: list[dict[str, Any]],
        hotel_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create multiple reservations in a bulk operation.

        Args:
            reservations_data: List of reservation payloads
            hotel_id: Hotel identifier (uses default if not provided)

        Returns:
            Dictionary containing bulk job details
        """
        client = _get_reservations_client(hotel_id=hotel_id)
        response = await client.bulk_create_reservations(reservations_data)

        if response.success:
            data = cast("dict[str, Any]", response.data or {})
            job_id = data.get("jobId")
            return {
                "success": True,
                "job_id": job_id,
                "status": data.get("status"),
                "data": data,
                "hotel_id": hotel_id,
                "message": f"Bulk operation started: {job_id}",
            }
        return {
            "success": False,
            "error": response.error,
            "hotel_id": hotel_id,
        }

    @app.tool()
    async def get_bulk_operation_status(
        job_id: str,
        hotel_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve status for a bulk reservation operation.

        Args:
            job_id: Bulk operation job identifier
            hotel_id: Hotel identifier (uses default if not provided)

        Returns:
            Dictionary containing bulk operation status
        """
        client = _get_reservations_client(hotel_id=hotel_id)
        response = await client.get_bulk_operation_status(job_id)

        if response.success:
            data = cast("dict[str, Any]", response.data or {})
            processed = data.get("processedCount")
            total = data.get("totalReservations")
            progress = (
                f"({processed}/{total} processed)"
                if processed is not None and total is not None
                else "(progress unknown)"
            )
            status = data.get("status")
            return {
                "success": True,
                "job_id": job_id,
                "status": status,
                "data": data,
                "hotel_id": hotel_id,
                "message": f"Bulk operation {status} {progress}",
            }
        return {
            "success": False,
            "error": response.error,
            "hotel_id": hotel_id,
        }


def _register_reservation_metrics_tool(app: FastMCP) -> None:
    """Register reservation metrics tool."""

    @app.tool()
    async def get_reservation_client_metrics(
        hotel_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get client metrics for reservation operations.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)

        Returns:
            Dictionary containing client metrics and health status
        """
        client = _get_reservations_client(hotel_id=hotel_id)
        metrics = await _maybe_await(client.get_metrics())
        return {
            "success": True,
            "data": {
                "hotel_id": hotel_id,
                "metrics": metrics,
            },
        }


def _register_reservation_support_tools(app: FastMCP) -> None:
    """Register availability, history, and bulk reservation tools."""
    _register_check_room_availability_tool(app)
    _register_reservation_history_tool(app)
    _register_bulk_reservation_tools(app)
    _register_reservation_metrics_tool(app)


def register_reservation_tools(app: FastMCP):
    """Register all reservation-related MCP tools."""
    _register_search_reservations_tool(app)
    _register_get_reservation_tool(app)
    _register_create_reservation_tool(app)
    _register_modify_reservation_tool(app)
    _register_cancel_reservation_tool(app)
    _register_reservation_support_tools(app)
