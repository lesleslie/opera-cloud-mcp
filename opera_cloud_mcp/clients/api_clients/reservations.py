"""
Reservations API client for OPERA Cloud.

Handles reservation management operations including search, create,
modify, and cancel reservations through the OPERA Cloud RSV API.
"""

import logging
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.models.reservation import (
    Guest,
    RoomStay,
)
from opera_cloud_mcp.utils.exceptions import ValidationError
from opera_cloud_mcp.utils.validators import (
    validate_confirmation_number,
    validate_date_format,
)

logger = logging.getLogger(__name__)


class ReservationSearchCriteria(BaseModel):
    """Search criteria model for reservation queries."""

    arrival_date: str | None = Field(None, description="Arrival date (YYYY-MM-DD)")
    departure_date: str | None = Field(None, description="Departure date (YYYY-MM-DD)")
    guest_name: str | None = Field(None, description="Guest name (partial match)")
    confirmation_number: str | None = Field(None, description="Confirmation number")
    guest_id: str | None = Field(None, description="Guest profile ID")
    room_number: str | None = Field(None, description="Room number")
    status: str | None = Field(None, description="Reservation status")
    rate_code: str | None = Field(None, description="Rate code")
    room_type: str | None = Field(None, description="Room type")
    created_from: str | None = Field(None, description="Created from date")
    created_to: str | None = Field(None, description="Created to date")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Results offset for pagination")

    @field_validator("arrival_date", "departure_date")
    @classmethod
    def validate_dates(cls, v: Any) -> Any:
        """Validate date format."""
        if v is not None:
            validate_date_format(v)
        return v

    @field_validator("confirmation_number")
    @classmethod
    def validate_confirmation(cls, v: Any) -> Any:
        """Validate confirmation number format."""
        if v is not None:
            validate_confirmation_number(v)
        return v


class ReservationCreateRequest(BaseModel):
    """Request model for creating new reservations."""

    guest: Guest = Field(description="Primary guest information")
    room_stay: RoomStay = Field(description="Room stay details")
    special_requests: str | None = Field(None, description="Special requests")
    comments: str | None = Field(None, description="Internal comments")
    guarantee_code: str | None = Field(None, description="Guarantee method")
    deposit_required: bool | None = Field(None, description="Deposit required flag")
    source_code: str | None = Field(None, description="Reservation source")
    travel_agent_id: str | None = Field(None, description="Travel agent ID")
    company_id: str | None = Field(None, description="Company ID")
    group_code: str | None = Field(None, description="Group code")


class ReservationModifyRequest(BaseModel):
    """Request model for modifying existing reservations."""

    room_stay: RoomStay | None = Field(None, description="Updated room stay details")
    special_requests: str | None = Field(None, description="Updated special requests")
    comments: str | None = Field(None, description="Updated internal comments")
    guarantee_code: str | None = Field(None, description="Updated guarantee method")


class ReservationCancelRequest(BaseModel):
    """Request model for canceling reservations."""

    reason: str = Field(description="Cancellation reason")
    charge_penalty: bool = Field(False, description="Charge cancellation penalty")
    notify_guest: bool = Field(True, description="Send notification to guest")


class ReservationsClient(BaseAPIClient):
    """
    Production-ready client for OPERA Cloud Reservations API.

    Provides methods for managing hotel reservations including
    search, creation, modification, and cancellation with comprehensive
    error handling, validation, and logging.

    Features:
    - Full CRUD operations for reservations
    - Advanced search with multiple criteria
    - Data validation and transformation
    - Support for both sync (rsv) and async (rsvasync) operations
    - Comprehensive error handling and recovery
    - Request/response logging and monitoring
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize reservations client with monitoring."""
        super().__init__(*args, **kwargs)
        self._operation_metrics = {
            "searches": 0,
            "creates": 0,
            "retrievals": 0,
            "modifications": 0,
            "cancellations": 0,
        }
        logger.info(
            "ReservationsClient initialized",
            extra={"hotel_id": self.hotel_id, "client_type": "reservations"},
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get client operation metrics."""
        base_metrics = self.get_health_status()
        base_metrics["operation_metrics"] = self._operation_metrics.copy()
        return base_metrics

    async def search_reservations(
        self,
        criteria: ReservationSearchCriteria | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> APIResponse:
        """
        Search for reservations by various criteria with advanced filtering.

        Args:
            criteria: Search criteria as model or dict
            **kwargs: Additional search parameters for convenience

        Returns:
            APIResponse containing reservation search results

        Raises:
            ValidationError: Invalid search criteria
            APIError: OPERA Cloud API error
        """
        logger.info(
            "Searching reservations",
            extra={"hotel_id": self.hotel_id, "has_criteria": criteria is not None},
        )

        try:
            # Convert criteria to standardized format
            if criteria is None:
                criteria = ReservationSearchCriteria(**kwargs)
            elif isinstance(criteria, dict):
                criteria = ReservationSearchCriteria(**criteria)
            elif not isinstance(criteria, ReservationSearchCriteria):
                raise ValidationError("Invalid criteria type")

            # Build query parameters for OPERA Cloud API
            params = self._build_search_params(criteria)

            # Log search parameters (sanitized)
            logger.debug(
                "Reservation search parameters",
                extra={
                    "params_count": len(params),
                    "has_dates": bool(
                        params.get("arrivalDate") or params.get("departureDate")
                    ),
                    "has_guest_filter": bool(
                        params.get("guestName") or params.get("guestId")
                    ),
                    "limit": params.get("limit", 10),
                },
            )

            # Execute search with proper endpoint
            endpoint = f"rsv/v1/hotels/{self.hotel_id}/reservations"
            response = await self.get(
                endpoint,
                params=params,
                timeout=30.0,  # Extended timeout for searches
                data_transformations={
                    "reservations": self._transform_reservation_list,
                    "totalCount": lambda x: int(x) if x is not None else 0,
                },
            )

            self._operation_metrics["searches"] += 1

            if response.success:
                logger.info(
                    "Reservation search completed",
                    extra={
                        "hotel_id": self.hotel_id,
                        "results_count": len(response.data.get("reservations", []))
                        if response.data
                        else 0,
                        "total_count": response.data.get("totalCount", 0)
                        if response.data
                        else 0,
                    },
                )

            return response

        except ValidationError:
            logger.warning(
                "Invalid reservation search criteria", extra={"criteria": str(criteria)}
            )
            raise
        except Exception as e:
            logger.error(f"Reservation search failed: {e}", exc_info=True)
            raise

    async def get_reservation(
        self,
        confirmation_number: str,
        include_history: bool = False,
        include_charges: bool = False,
    ) -> APIResponse:
        """
        Get detailed reservation information with optional inclusions.

        Args:
            confirmation_number: Reservation confirmation number
            include_history: Include reservation modification history
            include_charges: Include charge/payment details

        Returns:
            APIResponse containing complete reservation details

        Raises:
            ValidationError: Invalid confirmation number
            ResourceNotFoundError: Reservation not found
            APIError: OPERA Cloud API error
        """
        validate_confirmation_number(confirmation_number)

        logger.info(
            "Retrieving reservation",
            extra={
                "hotel_id": self.hotel_id,
                "confirmation_number": confirmation_number,
                "include_history": include_history,
                "include_charges": include_charges,
            },
        )

        try:
            # Build query parameters for additional data
            params = {}
            if include_history:
                params["includeHistory"] = "true"
            if include_charges:
                params["includeCharges"] = "true"

            endpoint = (
                f"rsv/v1/hotels/{self.hotel_id}/reservations/{confirmation_number}"
            )
            response = await self.get(
                endpoint,
                params=params or None,
                timeout=20.0,
                data_transformations={
                    "reservation": self._transform_reservation_data,
                },
            )

            self._operation_metrics["retrievals"] += 1

            if response.success:
                logger.info(
                    "Reservation retrieved successfully",
                    extra={
                        "hotel_id": self.hotel_id,
                        "confirmation_number": confirmation_number,
                        "status": response.data.get("reservation", {}).get("status")
                        if response.data
                        else None,
                    },
                )

            return response

        except Exception as e:
            logger.error(
                f"Failed to retrieve reservation {confirmation_number}: {e}",
                exc_info=True,
            )
            raise

    async def create_reservation(
        self, reservation_request: ReservationCreateRequest | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new reservation with comprehensive validation.

        Args:
            reservation_request: Reservation creation data

        Returns:
            APIResponse containing created reservation details

        Raises:
            ValidationError: Invalid reservation data
            APIError: OPERA Cloud API error
        """
        logger.info("Creating new reservation", extra={"hotel_id": self.hotel_id})

        try:
            # Validate and convert request data
            if isinstance(reservation_request, dict):
                reservation_request = ReservationCreateRequest(**reservation_request)
            elif not isinstance(reservation_request, ReservationCreateRequest):
                raise ValidationError("Invalid reservation request type")

            # Transform to OPERA Cloud API format
            api_data = self._transform_create_request(reservation_request)

            logger.debug(
                "Reservation creation data prepared",
                extra={
                    "hotel_id": self.hotel_id,
                    "guest_name": (
                        f"{reservation_request.guest.first_name} "
                        f"{reservation_request.guest.last_name}"
                    ),
                    "arrival_date": (
                        reservation_request.room_stay.arrival_date.isoformat()
                    ),
                    "departure_date": (
                        reservation_request.room_stay.departure_date.isoformat()
                    ),
                    "room_type": reservation_request.room_stay.room_type,
                },
            )

            endpoint = f"rsv/v1/hotels/{self.hotel_id}/reservations"
            response = await self.post(
                endpoint,
                json_data=api_data,
                timeout=30.0,
                data_transformations={
                    "reservation": self._transform_reservation_data,
                },
            )

            self._operation_metrics["creates"] += 1

            if response.success:
                created_reservation: dict[str, Any] = (
                    response.data.get("reservation", {}) if response.data else {}
                )
                logger.info(
                    "Reservation created successfully",
                    extra={
                        "hotel_id": self.hotel_id,
                        "confirmation_number": created_reservation.get(
                            "confirmationNumber"
                        ),
                        "status": created_reservation.get("status"),
                    },
                )

            return response

        except ValidationError:
            logger.warning("Invalid reservation creation data")
            raise
        except Exception as e:
            logger.error(f"Failed to create reservation: {e}", exc_info=True)
            raise

    async def modify_reservation(
        self,
        confirmation_number: str,
        modifications: ReservationModifyRequest | dict[str, Any],
    ) -> APIResponse:
        """
        Modify an existing reservation with validation and conflict detection.

        Args:
            confirmation_number: Reservation confirmation number
            modifications: Changes to apply to reservation

        Returns:
            APIResponse containing modified reservation details

        Raises:
            ValidationError: Invalid modification data
            ResourceNotFoundError: Reservation not found
            ConflictError: Modification conflicts with current state
            APIError: OPERA Cloud API error
        """
        validate_confirmation_number(confirmation_number)

        logger.info(
            "Modifying reservation",
            extra={
                "hotel_id": self.hotel_id,
                "confirmation_number": confirmation_number,
            },
        )

        try:
            # Validate and convert modification data
            if isinstance(modifications, dict):
                modifications = ReservationModifyRequest(**modifications)
            elif not isinstance(modifications, ReservationModifyRequest):
                raise ValidationError("Invalid modification request type")

            # Transform to OPERA Cloud API format
            api_data = self._transform_modify_request(modifications)

            logger.debug(
                "Reservation modification data prepared",
                extra={
                    "hotel_id": self.hotel_id,
                    "confirmation_number": confirmation_number,
                    "has_room_changes": modifications.room_stay is not None,
                    "has_requests_changes": modifications.special_requests is not None,
                },
            )

            endpoint = (
                f"rsv/v1/hotels/{self.hotel_id}/reservations/{confirmation_number}"
            )
            response = await self.put(
                endpoint,
                json_data=api_data,
                timeout=30.0,
                data_transformations={
                    "reservation": self._transform_reservation_data,
                },
            )

            self._operation_metrics["modifications"] += 1

            if response.success:
                modified_reservation: dict[str, Any] = (
                    response.data.get("reservation", {}) if response.data else {}
                )
                logger.info(
                    "Reservation modified successfully",
                    extra={
                        "hotel_id": self.hotel_id,
                        "confirmation_number": confirmation_number,
                        "status": modified_reservation.get("status"),
                    },
                )

            return response

        except ValidationError:
            logger.warning(
                f"Invalid reservation modification data for {confirmation_number}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Failed to modify reservation {confirmation_number}: {e}",
                exc_info=True,
            )
            raise

    def _handle_cancellation_input(
        self, cancellation: ReservationCancelRequest | dict[str, Any] | str | None
    ) -> ReservationCancelRequest:
        """Handle different cancellation input formats."""
        if cancellation is None:
            return ReservationCancelRequest(
                reason="Guest requested cancellation",
                charge_penalty=False,
                notify_guest=True,
            )
        elif isinstance(cancellation, str):
            return ReservationCancelRequest(
                reason=cancellation, charge_penalty=False, notify_guest=True
            )
        elif isinstance(cancellation, dict):
            # Ensure required fields are present
            if "reason" not in cancellation:
                cancellation["reason"] = "Guest requested cancellation"
            if "charge_penalty" not in cancellation:
                cancellation["charge_penalty"] = False
            if "notify_guest" not in cancellation:
                cancellation["notify_guest"] = True
            return ReservationCancelRequest(**cancellation)
        elif isinstance(cancellation, ReservationCancelRequest):
            return cancellation
        else:
            raise ValidationError("Invalid cancellation request type")

    def _prepare_cancel_response_data(
        self, response: APIResponse
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Prepare response data for cancellation."""
        if response.success:
            canceled_reservation: dict[str, Any] = (
                response.data.get("reservation", {}) if response.data else {}
            )
            charges: list[dict[str, Any]] = (
                response.data.get("charges", []) if response.data else []
            )
            return canceled_reservation, charges
        return {}, []

    async def cancel_reservation(
        self,
        confirmation_number: str,
        cancellation: ReservationCancelRequest | dict[str, Any] | str | None = None,
    ) -> APIResponse:
        """
        Cancel a reservation with proper handling of penalties and notifications.

        Args:
            confirmation_number: Reservation confirmation number
            cancellation: Cancellation details (reason, penalties, etc.)

        Returns:
            APIResponse containing cancellation result and any applicable charges

        Raises:
            ValidationError: Invalid cancellation data
            ResourceNotFoundError: Reservation not found
            APIError: OPERA Cloud API error
        """
        validate_confirmation_number(confirmation_number)

        logger.info(
            "Canceling reservation",
            extra={
                "hotel_id": self.hotel_id,
                "confirmation_number": confirmation_number,
            },
        )

        try:
            # Handle different cancellation input formats
            cancellation_request = self._handle_cancellation_input(cancellation)

            # Transform to OPERA Cloud API format
            api_data = self._transform_cancel_request(cancellation_request)

            logger.debug(
                "Reservation cancellation data prepared",
                extra={
                    "hotel_id": self.hotel_id,
                    "confirmation_number": confirmation_number,
                    "reason": cancellation_request.reason,
                    "charge_penalty": cancellation_request.charge_penalty,
                    "notify_guest": cancellation_request.notify_guest,
                },
            )

            endpoint = (
                f"rsv/v1/hotels/{self.hotel_id}/reservations/"
                + f"{confirmation_number}/cancel"
            )
            response = await self.post(
                endpoint,
                json_data=api_data,
                timeout=30.0,
                data_transformations={
                    "reservation": self._transform_reservation_data,
                    "charges": lambda x: self._transform_charges_data(x) if x else [],
                },
            )

            self._operation_metrics["cancellations"] += 1

            canceled_reservation, charges = self._prepare_cancel_response_data(response)

            if response.success:
                logger.info(
                    "Reservation canceled successfully",
                    extra={
                        "hotel_id": self.hotel_id,
                        "confirmation_number": confirmation_number,
                        "status": canceled_reservation.get("status"),
                        "penalty_charges": len(charges),
                    },
                )

            return response

        except ValidationError:
            logger.warning(
                f"Invalid reservation cancellation data for {confirmation_number}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Failed to cancel reservation {confirmation_number}: {e}",
                exc_info=True,
            )
            raise

    async def get_availability(
        self,
        arrival_date: str | date,
        departure_date: str | date,
        room_type: str | None = None,
        rate_code: str | None = None,
        adults: int = 1,
        children: int = 0,
    ) -> APIResponse:
        """
        Check room availability for given dates and criteria.

        Args:
            arrival_date: Arrival date (YYYY-MM-DD or date object)
            departure_date: Departure date (YYYY-MM-DD or date object)
            room_type: Specific room type filter
            rate_code: Specific rate code filter
            adults: Number of adults
            children: Number of children

        Returns:
            APIResponse containing available rooms and rates
        """
        # Convert dates to string format
        if isinstance(arrival_date, date):
            arrival_date = arrival_date.isoformat()
        if isinstance(departure_date, date):
            departure_date = departure_date.isoformat()

        validate_date_format(arrival_date)
        validate_date_format(departure_date)

        logger.info(
            "Checking room availability",
            extra={
                "hotel_id": self.hotel_id,
                "arrival_date": arrival_date,
                "departure_date": departure_date,
                "room_type": room_type,
                "adults": adults,
                "children": children,
            },
        )

        params = {
            "arrivalDate": arrival_date,
            "departureDate": departure_date,
            "adults": adults,
            "children": children,
        }

        if room_type:
            params["roomType"] = room_type
        if rate_code:
            params["rateCode"] = rate_code

        endpoint = f"rsv/v1/hotels/{self.hotel_id}/availability"
        return await self.get(endpoint, params=params, timeout=20.0)

    # Async operations support (rsvasync API)

    async def bulk_create_reservations(
        self, reservations: list[ReservationCreateRequest | dict[str, Any]]
    ) -> APIResponse:
        """
        Create multiple reservations in a single async operation.

        Args:
            reservations: List of reservation creation requests

        Returns:
            APIResponse containing async operation status and job ID
        """
        logger.info(
            "Starting bulk reservation creation",
            extra={"hotel_id": self.hotel_id, "count": len(reservations)},
        )

        # Transform all reservations
        api_data = {
            "reservations": [
                self._transform_create_request(
                    res
                    if isinstance(res, ReservationCreateRequest)
                    else ReservationCreateRequest(**res)
                )
                for res in reservations
            ]
        }

        endpoint = f"rsvasync/v1/hotels/{self.hotel_id}/reservations/bulk"
        return await self.post(endpoint, json_data=api_data, timeout=60.0)

    async def get_bulk_operation_status(self, job_id: str) -> APIResponse:
        """
        Get status of a bulk async operation.

        Args:
            job_id: Async operation job ID

        Returns:
            APIResponse containing operation status and results
        """
        endpoint = f"rsvasync/v1/hotels/{self.hotel_id}/jobs/{job_id}"
        return await self.get(endpoint, timeout=10.0)

    # Private helper methods for data transformation

    def _build_search_params(
        self, criteria: ReservationSearchCriteria
    ) -> dict[str, str | int]:
        """Build OPERA Cloud API parameters from search criteria."""
        params: dict[str, str | int] = {}

        if criteria.arrival_date:
            params["arrivalDate"] = criteria.arrival_date
        if criteria.departure_date:
            params["departureDate"] = criteria.departure_date
        if criteria.guest_name:
            params["guestName"] = criteria.guest_name
        if criteria.confirmation_number:
            params["confirmationNumber"] = criteria.confirmation_number
        if criteria.guest_id:
            params["guestId"] = criteria.guest_id
        if criteria.room_number:
            params["roomNumber"] = criteria.room_number
        if criteria.status:
            params["status"] = criteria.status
        if criteria.rate_code:
            params["rateCode"] = criteria.rate_code
        if criteria.room_type:
            params["roomType"] = criteria.room_type
        if criteria.created_from:
            params["createdFrom"] = criteria.created_from
        if criteria.created_to:
            params["createdTo"] = criteria.created_to
        if criteria.limit:
            params["limit"] = criteria.limit
        if criteria.offset > 0:
            params["offset"] = criteria.offset

        return params

    def _transform_reservation_list(
        self, reservations_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform list of reservations from OPERA Cloud format."""
        return [self._transform_reservation_data(res) for res in reservations_data]

    def _transform_reservation_data(
        self, reservation_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Transform single reservation from OPERA Cloud format to our model."""
        # This would contain the actual OPERA Cloud to internal format transformation
        # For now, return as-is with basic field mapping
        transformed = reservation_data.copy()

        # Map OPERA Cloud fields to our model fields
        field_mappings = {
            "confirmationId": "confirmationNumber",
            "hotelCode": "hotelId",
            "primaryGuest": "guest",
            "stayDetails": "roomStay",
            "reservationStatus": "status",
            "createdDateTime": "createdDate",
            "lastModifiedDateTime": "modifiedDate",
        }

        for opera_field, model_field in field_mappings.items():
            if opera_field in transformed:
                transformed[model_field] = transformed.pop(opera_field)

        return transformed

    def _transform_create_request(
        self, request: ReservationCreateRequest
    ) -> dict[str, Any]:
        """Transform reservation create request to OPERA Cloud format."""
        return {
            "reservationType": "INDIVIDUAL",
            "primaryGuest": {
                "firstName": request.guest.first_name,
                "lastName": request.guest.last_name,
                "middleName": request.guest.middle_name,
                "title": request.guest.title,
                "contact": request.guest.contact.model_dump()
                if request.guest.contact
                else None,
                "address": request.guest.address.model_dump()
                if request.guest.address
                else None,
                "loyaltyNumber": request.guest.loyalty_number,
                "vipStatus": request.guest.vip_status,
            },
            "stayDetails": {
                "arrivalDate": request.room_stay.arrival_date.isoformat(),
                "departureDate": request.room_stay.departure_date.isoformat(),
                "roomType": request.room_stay.room_type,
                "rateCode": request.room_stay.rate_code,
                "adults": request.room_stay.adults,
                "children": request.room_stay.children,
                "roomNumber": request.room_stay.room_number,
            },
            "specialRequests": request.special_requests,
            "comments": request.comments,
            "guaranteeCode": request.guarantee_code,
            "depositRequired": request.deposit_required,
            "sourceCode": request.source_code,
            "travelAgentId": request.travel_agent_id,
            "companyId": request.company_id,
            "groupCode": request.group_code,
        }

    def _transform_modify_request(
        self, request: ReservationModifyRequest
    ) -> dict[str, Any]:
        """Transform reservation modify request to OPERA Cloud format."""
        data: dict[str, Any] = {}

        if request.room_stay:
            data["stayDetails"] = {
                "arrivalDate": request.room_stay.arrival_date.isoformat(),
                "departureDate": request.room_stay.departure_date.isoformat(),
                "roomType": request.room_stay.room_type,
                "rateCode": request.room_stay.rate_code,
                "adults": request.room_stay.adults,
                "children": request.room_stay.children,
                "roomNumber": request.room_stay.room_number,
            }

        if request.special_requests is not None:
            data["specialRequests"] = request.special_requests
        if request.comments is not None:
            data["comments"] = request.comments
        if request.guarantee_code is not None:
            data["guaranteeCode"] = request.guarantee_code

        return data

    def _transform_cancel_request(
        self, request: ReservationCancelRequest
    ) -> dict[str, Any]:
        """Transform reservation cancel request to OPERA Cloud format."""
        return {
            "reason": request.reason,
            "chargePenalty": request.charge_penalty,
            "notifyGuest": request.notify_guest,
        }

    async def check_availability(
        self,
        availability_criteria: dict[str, Any],
    ) -> APIResponse:
        """
        Check room availability for given criteria.

        Args:
            availability_criteria: Search criteria for availability

        Returns:
            APIResponse containing availability results
        """
        logger.info(
            "Checking availability",
            extra={
                "hotel_id": self.hotel_id,
                "criteria": availability_criteria,
            },
        )

        endpoint = f"rsv/v1/hotels/{self.hotel_id}/availability"
        return await self.post(
            endpoint,
            json_data=availability_criteria,
            data_transformations={
                "rooms": self._transform_room_availability,
                "totalAvailable": int,
            },
        )

    async def get_guest_reservation_history(
        self,
        history_criteria: dict[str, Any],
    ) -> APIResponse:
        """
        Get guest reservation history based on criteria.

        Args:
            history_criteria: Search criteria for guest history

        Returns:
            APIResponse containing reservation history
        """
        logger.info(
            "Retrieving guest reservation history",
            extra={
                "hotel_id": self.hotel_id,
                "criteria": history_criteria,
            },
        )

        endpoint = f"rsv/v1/hotels/{self.hotel_id}/guests/history"
        return await self.post(
            endpoint,
            json_data=history_criteria,
            data_transformations={
                "reservations": self._transform_reservation_list,
                "total_count": int,
            },
        )

    def _transform_room_availability(
        self, rooms_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform room availability data from OPERA Cloud format."""
        return rooms_data

    def _transform_charges_data(
        self, charges_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform charges data from OPERA Cloud format."""
        # This would transform charge/financial data
        return charges_data
