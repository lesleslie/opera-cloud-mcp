"""
Activities and Amenities API client for OPERA Cloud.

Handles hotel activities, amenities booking, and experience management
through the OPERA Cloud ACT API.
"""

import asyncio
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.models.common import OperaBaseModel


class Activity(OperaBaseModel):
    """Hotel activity model."""

    activity_id: str = Field(alias="activityId")
    activity_code: str = Field(alias="activityCode")
    activity_name: str = Field(alias="activityName")
    category: str  # "dining", "spa", "recreation", "entertainment", "business"
    description: str
    location: str | None = None
    capacity: int = Field(ge=1)
    duration_minutes: int = Field(alias="durationMinutes", ge=1)
    price: Decimal = Field(ge=0)
    currency_code: str = Field(alias="currencyCode")
    age_restrictions: str | None = Field(None, alias="ageRestrictions")
    advance_booking_hours: int = Field(0, alias="advanceBookingHours", ge=0)
    cancellation_hours: int = Field(24, alias="cancellationHours", ge=0)
    requires_equipment: bool = Field(False, alias="requiresEquipment")
    equipment_cost: Decimal | None = Field(None, alias="equipmentCost")
    seasonal_availability: bool = Field(True, alias="seasonalAvailability")
    weather_dependent: bool = Field(False, alias="weatherDependent")
    is_active: bool = Field(True, alias="isActive")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        allowed = [
            "dining",
            "spa",
            "recreation",
            "entertainment",
            "business",
            "transportation",
            "tours",
        ]
        if v not in allowed:
            raise ValueError(f"Invalid activity category. Must be one of: {allowed}")
        return v


class ActivityBooking(OperaBaseModel):
    """Activity booking model."""

    booking_id: str = Field(alias="bookingId")
    activity_id: str = Field(alias="activityId")
    guest_name: str = Field(alias="guestName")
    reservation_number: str | None = Field(None, alias="reservationNumber")
    booking_date: date = Field(alias="bookingDate")
    booking_time: time = Field(alias="bookingTime")
    party_size: int = Field(alias="partySize", ge=1)
    total_price: Decimal = Field(alias="totalPrice", ge=0)
    special_requests: str | None = Field(None, alias="specialRequests")
    dietary_restrictions: str | None = Field(None, alias="dietaryRestrictions")
    contact_phone: str | None = Field(None, alias="contactPhone")
    contact_email: str | None = Field(None, alias="contactEmail")
    status: str = Field(
        default="confirmed"
    )  # "confirmed", "pending", "cancelled", "completed"
    payment_status: str = Field(
        "pending", alias="paymentStatus"
    )  # "pending", "paid", "refunded"
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = ["confirmed", "pending", "cancelled", "completed", "no_show"]
        if v not in allowed:
            raise ValueError(f"Invalid booking status. Must be one of: {allowed}")
        return v


class ActivitySchedule(OperaBaseModel):
    """Activity schedule model."""

    schedule_id: str = Field(alias="scheduleId")
    activity_id: str = Field(alias="activityId")
    schedule_date: date = Field(alias="scheduleDate")
    time_slots: list[dict[str, Any]] = Field(
        alias="timeSlots"
    )  # [{"time": "10:00", "available": 10}]
    operating_hours: dict[str, str] = Field(
        alias="operatingHours"
    )  # {"start": "09:00", "end": "18:00"}
    closed: bool = Field(False)
    closure_reason: str | None = Field(None, alias="closureReason")
    special_pricing: Decimal | None = Field(None, alias="specialPricing")
    maximum_bookings: int = Field(alias="maximumBookings", ge=0)
    current_bookings: int = Field(0, alias="currentBookings", ge=0)


class SpaService(OperaBaseModel):
    """Spa service model."""

    service_id: str = Field(alias="serviceId")
    service_code: str = Field(alias="serviceCode")
    service_name: str = Field(alias="serviceName")
    service_type: str = Field(
        alias="serviceType"
    )  # "massage", "facial", "body_treatment", "package"
    duration_minutes: int = Field(alias="durationMinutes", ge=15)
    price: Decimal = Field(ge=0)
    therapist_required: bool = Field(True, alias="therapistRequired")
    room_type: str | None = Field(
        None, alias="roomType"
    )  # "private", "couple", "group"
    gender_preference: str | None = Field(
        None, alias="genderPreference"
    )  # "male", "female", "any"
    contraindications: list[str] | None = None
    benefits: list[str] | None = None
    recommended_frequency: str | None = Field(None, alias="recommendedFrequency")

    @field_validator("service_type")
    @classmethod
    def validate_service_type(cls, v):
        allowed = [
            "massage",
            "facial",
            "body_treatment",
            "nail_service",
            "hair_service",
            "wellness",
            "package",
        ]
        if v not in allowed:
            raise ValueError(f"Invalid service type. Must be one of: {allowed}")
        return v


class DiningReservation(OperaBaseModel):
    """Dining reservation model."""

    reservation_id: str = Field(alias="reservationId")
    restaurant_id: str = Field(alias="restaurantId")
    guest_name: str = Field(alias="guestName")
    reservation_date: date = Field(alias="reservationDate")
    reservation_time: time = Field(alias="reservationTime")
    party_size: int = Field(alias="partySize", ge=1)
    table_preference: str | None = Field(None, alias="tablePreference")
    seating_area: str | None = Field(
        None, alias="seatingArea"
    )  # "indoor", "outdoor", "bar", "private"
    occasion: str | None = None  # "birthday", "anniversary", "business"
    dietary_restrictions: str | None = Field(None, alias="dietaryRestrictions")
    special_requests: str | None = Field(None, alias="specialRequests")
    contact_phone: str = Field(alias="contactPhone")
    confirmation_number: str = Field(alias="confirmationNumber")
    status: str = Field(default="confirmed")

    @field_validator("seating_area")
    @classmethod
    def validate_seating_area(cls, v):
        if v is None:
            return v
        allowed = ["indoor", "outdoor", "bar", "private", "terrace", "garden"]
        if v not in allowed:
            raise ValueError(f"Invalid seating area. Must be one of: {allowed}")
        return v


class Equipment(OperaBaseModel):
    """Activity equipment model."""

    equipment_id: str = Field(alias="equipmentId")
    equipment_code: str = Field(alias="equipmentCode")
    equipment_name: str = Field(alias="equipmentName")
    category: str  # "sports", "water", "fitness", "business", "entertainment"
    description: str
    rental_price: Decimal = Field(alias="rentalPrice", ge=0)
    deposit_required: Decimal = Field(Decimal(0), alias="depositRequired", ge=0)
    max_rental_hours: int = Field(24, alias="maxRentalHours", ge=1)
    available_quantity: int = Field(alias="availableQuantity", ge=0)
    maintenance_required: bool = Field(False, alias="maintenanceRequired")
    age_restriction: str | None = Field(None, alias="ageRestriction")
    size_options: list[str] | None = Field(None, alias="sizeOptions")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        allowed = [
            "sports",
            "water",
            "fitness",
            "business",
            "entertainment",
            "mobility",
        ]
        if v not in allowed:
            raise ValueError(f"Invalid equipment category. Must be one of: {allowed}")
        return v


class ActivitiesClient(BaseAPIClient):
    """
    Client for OPERA Cloud Activities and Amenities API.

    Provides comprehensive activity management operations including bookings,
    schedules, spa services, dining reservations, and equipment rental.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_domain = "act"

    # Activity Management

    async def get_activities(
        self,
        category: str | None = None,
        location: str | None = None,
        active_only: bool = True,
        available_date: date | None = None,
    ) -> APIResponse:
        """
        Get available activities with filtering options.

        Args:
            category: Filter by activity category
            location: Filter by location
            active_only: Show only active activities
            available_date: Check availability for specific date

        Returns:
            APIResponse with activities list
        """
        endpoint = f"{self.api_domain}/v1/activities"
        params = {}

        if category:
            params["category"] = category
        if location:
            params["location"] = location
        if active_only:
            params["activeOnly"] = "true"
        if available_date:
            params["availableDate"] = available_date.isoformat()

        return await self.get(endpoint, params=params)

    async def get_activity_details(self, activity_id: str) -> APIResponse:
        """
        Get detailed information for a specific activity.

        Args:
            activity_id: Activity identifier

        Returns:
            APIResponse with activity details
        """
        endpoint = f"{self.api_domain}/v1/activities/{activity_id}"

        return await self.get(endpoint)

    async def create_activity(
        self, activity_data: Activity | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new activity offering.

        Args:
            activity_data: Activity creation data

        Returns:
            APIResponse with created activity details
        """
        if isinstance(activity_data, dict):
            activity_data = Activity.model_validate(activity_data)

        endpoint = f"{self.api_domain}/v1/activities"

        payload = {
            "activityCode": activity_data.activity_code,
            "activityName": activity_data.activity_name,
            "category": activity_data.category,
            "description": activity_data.description,
            "location": activity_data.location,
            "capacity": activity_data.capacity,
            "durationMinutes": activity_data.duration_minutes,
            "price": str(activity_data.price),
            "currencyCode": activity_data.currency_code,
            "ageRestrictions": activity_data.age_restrictions,
            "advanceBookingHours": activity_data.advance_booking_hours,
            "cancellationHours": activity_data.cancellation_hours,
            "requiresEquipment": activity_data.requires_equipment,
            "equipmentCost": str(activity_data.equipment_cost)
            if activity_data.equipment_cost
            else None,
            "seasonalAvailability": activity_data.seasonal_availability,
            "weatherDependent": activity_data.weather_dependent,
            "isActive": activity_data.is_active,
        }

        return await self.post(endpoint, json_data=payload)

    # Activity Booking Management

    async def create_activity_booking(
        self, booking_data: ActivityBooking | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new activity booking.

        Args:
            booking_data: Activity booking details

        Returns:
            APIResponse with booking confirmation
        """
        if isinstance(booking_data, dict):
            booking_data = ActivityBooking.model_validate(booking_data)

        endpoint = f"{self.api_domain}/v1/bookings"

        payload = {
            "activityId": booking_data.activity_id,
            "guestName": booking_data.guest_name,
            "reservationNumber": booking_data.reservation_number,
            "bookingDate": booking_data.booking_date.isoformat(),
            "bookingTime": booking_data.booking_time.strftime("%H:%M:%S"),
            "partySize": booking_data.party_size,
            "totalPrice": str(booking_data.total_price),
            "specialRequests": booking_data.special_requests,
            "dietaryRestrictions": booking_data.dietary_restrictions,
            "contactPhone": booking_data.contact_phone,
            "contactEmail": booking_data.contact_email,
            "createdBy": booking_data.created_by,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_activity_bookings(
        self,
        booking_date: date | None = None,
        activity_id: str | None = None,
        guest_name: str | None = None,
        status: str | None = None,
    ) -> APIResponse:
        """
        Get activity bookings with filtering options.

        Args:
            booking_date: Filter by booking date
            activity_id: Filter by activity
            guest_name: Filter by guest name
            status: Filter by booking status

        Returns:
            APIResponse with bookings list
        """
        endpoint = f"{self.api_domain}/v1/bookings"
        params = {}

        if booking_date:
            params["bookingDate"] = booking_date.isoformat()
        if activity_id:
            params["activityId"] = activity_id
        if guest_name:
            params["guestName"] = guest_name
        if status:
            params["status"] = status

        return await self.get(endpoint, params=params)

    async def update_booking_status(
        self, booking_id: str, status: str, notes: str | None = None
    ) -> APIResponse:
        """
        Update activity booking status.

        Args:
            booking_id: Booking identifier
            status: New booking status
            notes: Optional status change notes

        Returns:
            APIResponse with update confirmation
        """
        endpoint = f"{self.api_domain}/v1/bookings/{booking_id}/status"

        payload = {
            "status": status,
            "notes": notes,
            "updatedAt": datetime.now().isoformat(),
        }

        return await self.put(endpoint, json_data=payload)

    async def cancel_activity_booking(
        self,
        booking_id: str,
        cancellation_reason: str | None = None,
        refund_amount: Decimal | None = None,
    ) -> APIResponse:
        """
        Cancel an activity booking.

        Args:
            booking_id: Booking identifier
            cancellation_reason: Reason for cancellation
            refund_amount: Amount to refund

        Returns:
            APIResponse with cancellation confirmation
        """
        endpoint = f"{self.api_domain}/v1/bookings/{booking_id}/cancel"

        payload = {
            "cancellationReason": cancellation_reason,
            "refundAmount": str(refund_amount) if refund_amount else None,
            "cancelledAt": datetime.now().isoformat(),
        }

        return await self.post(endpoint, json_data=payload)

    # Spa Services

    async def get_spa_services(
        self,
        service_type: str | None = None,
        duration_range: dict[str, int] | None = None,
        price_range: dict[str, Decimal] | None = None,
    ) -> APIResponse:
        """
        Get available spa services.

        Args:
            service_type: Filter by service type
            duration_range: Filter by duration {"min": minutes, "max": minutes}
            price_range: Filter by price {"min": amount, "max": amount}

        Returns:
            APIResponse with spa services list
        """
        endpoint = f"{self.api_domain}/v1/spa/services"
        params = {}

        if service_type:
            params["serviceType"] = service_type
        if duration_range:
            params["minDuration"] = str(duration_range.get("min", 0))
            params["maxDuration"] = str(duration_range.get("max", 999))
        if price_range:
            params["minPrice"] = str(price_range.get("min", 0))
            params["maxPrice"] = str(price_range.get("max", 9999))

        return await self.get(endpoint, params=params)

    async def book_spa_service(
        self, service_id: str, appointment_data: dict[str, Any]
    ) -> APIResponse:
        """
        Book a spa service appointment.

        Args:
            service_id: Spa service identifier
            appointment_data: Appointment details

        Returns:
            APIResponse with appointment confirmation
        """
        endpoint = f"{self.api_domain}/v1/spa/services/{service_id}/book"

        return await self.post(endpoint, json_data=appointment_data)

    async def get_spa_availability(
        self, service_id: str, target_date: date, preferred_time: str | None = None
    ) -> APIResponse:
        """
        Check spa service availability for a specific date.

        Args:
            service_id: Spa service identifier
            target_date: Date to check availability
            preferred_time: Preferred time slot

        Returns:
            APIResponse with availability details
        """
        endpoint = f"{self.api_domain}/v1/spa/services/{service_id}/availability"
        params = {"date": target_date.isoformat()}

        if preferred_time:
            params["preferredTime"] = preferred_time

        return await self.get(endpoint, params=params)

    # Dining Reservations

    async def get_restaurants(
        self, seating_area: str | None = None, cuisine_type: str | None = None
    ) -> APIResponse:
        """
        Get available restaurants and dining venues.

        Args:
            seating_area: Filter by seating area
            cuisine_type: Filter by cuisine type

        Returns:
            APIResponse with restaurants list
        """
        endpoint = f"{self.api_domain}/v1/dining/restaurants"
        params = {}

        if seating_area:
            params["seatingArea"] = seating_area
        if cuisine_type:
            params["cuisineType"] = cuisine_type

        return await self.get(endpoint, params=params)

    async def create_dining_reservation(
        self, reservation_data: DiningReservation | dict[str, Any]
    ) -> APIResponse:
        """
        Create a dining reservation.

        Args:
            reservation_data: Dining reservation details

        Returns:
            APIResponse with reservation confirmation
        """
        if isinstance(reservation_data, dict):
            reservation_data = DiningReservation.model_validate(reservation_data)

        endpoint = f"{self.api_domain}/v1/dining/reservations"

        payload = {
            "restaurantId": reservation_data.restaurant_id,
            "guestName": reservation_data.guest_name,
            "reservationDate": reservation_data.reservation_date.isoformat(),
            "reservationTime": reservation_data.reservation_time.strftime("%H:%M:%S"),
            "partySize": reservation_data.party_size,
            "tablePreference": reservation_data.table_preference,
            "seatingArea": reservation_data.seating_area,
            "occasion": reservation_data.occasion,
            "dietaryRestrictions": reservation_data.dietary_restrictions,
            "specialRequests": reservation_data.special_requests,
            "contactPhone": reservation_data.contact_phone,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_dining_availability(
        self,
        restaurant_id: str,
        reservation_date: date,
        party_size: int,
        preferred_time: str | None = None,
    ) -> APIResponse:
        """
        Check dining availability for specific criteria.

        Args:
            restaurant_id: Restaurant identifier
            reservation_date: Desired reservation date
            party_size: Number of guests
            preferred_time: Preferred dining time

        Returns:
            APIResponse with availability details
        """
        endpoint = (
            f"{self.api_domain}/v1/dining/restaurants/{restaurant_id}/availability"
        )
        params = {"date": reservation_date.isoformat(), "partySize": party_size}

        if preferred_time:
            params["preferredTime"] = preferred_time

        return await self.get(endpoint, params=params)

    # Equipment Rental

    async def get_equipment(
        self, category: str | None = None, available_only: bool = True
    ) -> APIResponse:
        """
        Get available equipment for rental.

        Args:
            category: Filter by equipment category
            available_only: Show only available equipment

        Returns:
            APIResponse with equipment list
        """
        endpoint = f"{self.api_domain}/v1/equipment"
        params = {}

        if category:
            params["category"] = category
        if available_only:
            params["availableOnly"] = "true"

        return await self.get(endpoint, params=params)

    async def rent_equipment(
        self, equipment_id: str, rental_data: dict[str, Any]
    ) -> APIResponse:
        """
        Create an equipment rental.

        Args:
            equipment_id: Equipment identifier
            rental_data: Rental details

        Returns:
            APIResponse with rental confirmation
        """
        endpoint = f"{self.api_domain}/v1/equipment/{equipment_id}/rent"

        return await self.post(endpoint, json_data=rental_data)

    async def return_equipment(
        self,
        rental_id: str,
        return_condition: str = "good",
        damage_notes: str | None = None,
    ) -> APIResponse:
        """
        Process equipment return.

        Args:
            rental_id: Rental identifier
            return_condition: Condition of returned equipment
            damage_notes: Notes about any damage

        Returns:
            APIResponse with return confirmation
        """
        endpoint = f"{self.api_domain}/v1/equipment/rentals/{rental_id}/return"

        payload = {
            "returnCondition": return_condition,
            "damageNotes": damage_notes,
            "returnedAt": datetime.now().isoformat(),
        }

        return await self.post(endpoint, json_data=payload)

    # Scheduling and Availability

    async def get_activity_schedule(
        self, activity_id: str, schedule_date: date
    ) -> APIResponse:
        """
        Get activity schedule for a specific date.

        Args:
            activity_id: Activity identifier
            schedule_date: Date to check schedule

        Returns:
            APIResponse with schedule details
        """
        endpoint = f"{self.api_domain}/v1/activities/{activity_id}/schedule"
        params = {"date": schedule_date.isoformat()}

        return await self.get(endpoint, params=params)

    async def update_activity_schedule(
        self, activity_id: str, schedule_data: ActivitySchedule | dict[str, Any]
    ) -> APIResponse:
        """
        Update activity schedule for a specific date.

        Args:
            activity_id: Activity identifier
            schedule_data: Schedule configuration

        Returns:
            APIResponse with schedule update confirmation
        """
        if isinstance(schedule_data, dict):
            schedule_data = ActivitySchedule.model_validate(schedule_data)

        endpoint = f"{self.api_domain}/v1/activities/{activity_id}/schedule"

        payload = {
            "scheduleDate": schedule_data.schedule_date.isoformat(),
            "timeSlots": schedule_data.time_slots,
            "operatingHours": schedule_data.operating_hours,
            "closed": schedule_data.closed,
            "closureReason": schedule_data.closure_reason,
            "specialPricing": str(schedule_data.special_pricing)
            if schedule_data.special_pricing
            else None,
            "maximumBookings": schedule_data.maximum_bookings,
        }

        return await self.put(endpoint, json_data=payload)

    # Reporting and Analytics

    async def get_activity_usage_report(
        self, start_date: date, end_date: date, activity_ids: list[str] | None = None
    ) -> APIResponse:
        """
        Get activity usage and booking statistics.

        Args:
            start_date: Report start date
            end_date: Report end date
            activity_ids: Specific activities to analyze

        Returns:
            APIResponse with usage statistics
        """
        endpoint = f"{self.api_domain}/v1/reports/activity-usage"
        params = {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}

        if activity_ids:
            params["activityIds"] = ",".join(activity_ids)

        return await self.get(endpoint, params=params)

    async def get_revenue_report(
        self, start_date: date, end_date: date, category: str | None = None
    ) -> APIResponse:
        """
        Get activities revenue report.

        Args:
            start_date: Report start date
            end_date: Report end date
            category: Optional category filter

        Returns:
            APIResponse with revenue statistics
        """
        endpoint = f"{self.api_domain}/v1/reports/revenue"
        params = {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}

        if category:
            params["category"] = category

        return await self.get(endpoint, params=params)

    # Batch Operations

    async def batch_update_bookings(
        self, booking_updates: list[dict[str, Any]]
    ) -> APIResponse:
        """
        Update multiple bookings in a single operation.

        Args:
            booking_updates: List of booking updates

        Returns:
            APIResponse with batch update results
        """
        tasks = [
            self.update_booking_status(
                update["booking_id"], update["status"], update.get("notes")
            )
            for update in booking_updates
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = []
        failed = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append(
                    {
                        "booking_id": booking_updates[i]["booking_id"],
                        "error": str(result),
                    }
                )
            elif isinstance(result, APIResponse) and result.success:
                successful.append(result.data)
            elif isinstance(result, APIResponse):
                failed.append(
                    {
                        "booking_id": booking_updates[i]["booking_id"],
                        "error": result.error or "Unknown error",
                    }
                )

        return APIResponse(
            success=len(failed) == 0,
            data={
                "successful_updates": successful,
                "failed_updates": failed,
                "total_processed": len(booking_updates),
                "success_count": len(successful),
                "failure_count": len(failed),
            },
        )

    # Convenience Methods

    async def get_guest_activity_history(
        self, guest_name: str, reservation_number: str | None = None
    ) -> APIResponse:
        """
        Get activity booking history for a guest.

        Args:
            guest_name: Guest name to search
            reservation_number: Optional reservation filter

        Returns:
            APIResponse with guest's activity history
        """
        endpoint = f"{self.api_domain}/v1/guests/activity-history"
        params = {"guestName": guest_name}

        if reservation_number:
            params["reservationNumber"] = reservation_number

        return await self.get(endpoint, params=params)

    async def get_popular_activities(
        self,
        time_period: str = "month",  # "week", "month", "quarter"
        limit: int = 10,
    ) -> APIResponse:
        """
        Get most popular activities by booking frequency.

        Args:
            time_period: Analysis time period
            limit: Number of activities to return

        Returns:
            APIResponse with popular activities list
        """
        endpoint = f"{self.api_domain}/v1/reports/popular-activities"
        params = {"timePeriod": time_period, "limit": limit}

        return await self.get(endpoint, params=params)
