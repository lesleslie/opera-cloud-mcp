"""
Rate Planning API client for OPERA Cloud.

Handles rate planning, pricing management, and yield optimization
through the OPERA Cloud RTP API.
"""

import asyncio
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import Field, validator

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.models.common import OperaBaseModel


class RateCode(OperaBaseModel):
    """Rate code model."""

    rate_code: str = Field(alias="rateCode")
    rate_name: str = Field(alias="rateName")
    rate_category: str = Field(
        alias="rateCategory"
    )  # "corporate", "leisure", "group", "government"
    room_type: str = Field(alias="roomType")
    base_amount: Decimal = Field(alias="baseAmount")
    currency_code: str = Field(alias="currencyCode")
    effective_date: date = Field(alias="effectiveDate")
    expiry_date: date | None = Field(None, alias="expiryDate")
    minimum_los: int = Field(1, alias="minimumLOS", ge=1)  # Length of Stay
    maximum_los: int | None = Field(None, alias="maximumLOS")
    advance_booking_days: int = Field(0, alias="advanceBookingDays", ge=0)
    cancellation_policy: str | None = Field(None, alias="cancellationPolicy")
    deposit_required: bool = Field(False, alias="depositRequired")
    deposit_percentage: int | None = Field(
        None, alias="depositPercentage", ge=0, le=100
    )
    is_qualified: bool = Field(False, alias="isQualified")  # Requires qualification
    qualification_rules: str | None = Field(None, alias="qualificationRules")
    market_segment: str | None = Field(None, alias="marketSegment")
    source_code: str | None = Field(None, alias="sourceCode")

    @validator("rate_category")
    def validate_rate_category(self, v):
        allowed = [
            "corporate",
            "leisure",
            "group",
            "government",
            "package",
            "promotional",
        ]
        if v not in allowed:
            raise ValueError(f"Invalid rate category. Must be one of: {allowed}")
        return v


class RatePlan(OperaBaseModel):
    """Rate plan model."""

    plan_id: str = Field(alias="planId")
    plan_code: str = Field(alias="planCode")
    plan_name: str = Field(alias="planName")
    plan_type: str = Field(alias="planType")  # "standard", "package", "promotion"
    rate_codes: list[str] = Field(alias="rateCodes")
    stay_dates: dict[str, date] = Field(
        alias="stayDates"
    )  # {"start": date, "end": date}
    booking_dates: dict[str, date] = Field(
        alias="bookingDates"
    )  # {"start": date, "end": date}
    restrictions: dict[str, Any] = Field(default_factory=dict)
    inclusions: list[str] | None = None  # Breakfast, WiFi, etc.
    terms_conditions: str | None = Field(None, alias="termsConditions")
    marketing_text: str | None = Field(None, alias="marketingText")
    is_active: bool = Field(True, alias="isActive")

    @validator("plan_type")
    def validate_plan_type(self, v):
        allowed = ["standard", "package", "promotion", "corporate", "group"]
        if v not in allowed:
            raise ValueError(f"Invalid plan type. Must be one of: {allowed}")
        return v


class RateRestriction(OperaBaseModel):
    """Rate restriction model."""

    rate_code: str = Field(alias="rateCode")
    room_type: str = Field(alias="roomType")
    restriction_date: date = Field(alias="restrictionDate")
    closed_to_arrival: bool = Field(False, alias="closedToArrival")
    closed_to_departure: bool = Field(False, alias="closedToDeparture")
    closed: bool = Field(False, alias="closed")
    minimum_los: int | None = Field(None, alias="minimumLOS")
    maximum_los: int | None = Field(None, alias="maximumLOS")
    stop_sell: bool = Field(False, alias="stopSell")
    master_restriction: bool = Field(False, alias="masterRestriction")

    @validator("minimum_los", "maximum_los")
    def validate_los(self, v):
        if v is not None and v < 1:
            raise ValueError("Length of stay must be at least 1")
        return v


class YieldConfiguration(OperaBaseModel):
    """Yield management configuration."""

    config_id: str = Field(alias="configId")
    room_type: str = Field(alias="roomType")
    base_rate: Decimal = Field(alias="baseRate")
    occupancy_thresholds: dict[str, int] = Field(
        alias="occupancyThresholds"
    )  # {percentage: multiplier}
    lead_time_factors: dict[str, Decimal] = Field(
        alias="leadTimeFactors"
    )  # {days: factor}
    seasonal_adjustments: dict[str, Decimal] = Field(
        alias="seasonalAdjustments"
    )  # {season: factor}
    demand_adjustments: dict[str, Decimal] = Field(
        alias="demandAdjustments"
    )  # {demand_level: factor}
    minimum_rate: Decimal = Field(alias="minimumRate")
    maximum_rate: Decimal = Field(alias="maximumRate")
    auto_yield_enabled: bool = Field(True, alias="autoYieldEnabled")

    @validator("occupancy_thresholds")
    def validate_occupancy_thresholds(self, v):
        for threshold in v:
            if not (0 <= int(threshold) <= 100):
                raise ValueError("Occupancy thresholds must be between 0 and 100")
        return v


class PromotionalRate(OperaBaseModel):
    """Promotional rate model."""

    promo_code: str = Field(alias="promoCode")
    promo_name: str = Field(alias="promoName")
    rate_code: str = Field(alias="rateCode")
    discount_type: str = Field(
        alias="discountType"
    )  # "percentage", "amount", "fixed_rate"
    discount_value: Decimal = Field(alias="discountValue")
    valid_from: date = Field(alias="validFrom")
    valid_to: date = Field(alias="validTo")
    booking_from: date | None = Field(None, alias="bookingFrom")
    booking_to: date | None = Field(None, alias="bookingTo")
    room_types: list[str] = Field(alias="roomTypes")
    minimum_nights: int = Field(1, alias="minimumNights", ge=1)
    maximum_usage: int | None = Field(None, alias="maximumUsage")
    current_usage: int = Field(0, alias="currentUsage")
    combinable: bool = Field(False)  # Can be combined with other promos
    qualification_criteria: str | None = Field(None, alias="qualificationCriteria")

    @validator("discount_type")
    def validate_discount_type(self, v):
        allowed = ["percentage", "amount", "fixed_rate"]
        if v not in allowed:
            raise ValueError(f"Invalid discount type. Must be one of: {allowed}")
        return v


class RatesClient(BaseAPIClient):
    """
    Client for OPERA Cloud Rate Planning API.

    Provides comprehensive rate management operations including rate codes,
    plans, restrictions, yield management, and promotional pricing.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_domain = "rtp"

    # Rate Code Management

    async def get_rate_codes(
        self,
        rate_category: str | None = None,
        room_type: str | None = None,
        effective_date: date | None = None,
        active_only: bool = True,
    ) -> APIResponse:
        """
        Get available rate codes with filtering options.

        Args:
            rate_category: Filter by rate category
            room_type: Filter by room type
            effective_date: Filter by effective date
            active_only: Show only active rate codes

        Returns:
            APIResponse with rate codes list
        """
        endpoint = f"{self.api_domain}/v1/rates"
        params = {}

        if rate_category:
            params["category"] = rate_category
        if room_type:
            params["roomType"] = room_type
        if effective_date:
            params["effectiveDate"] = effective_date.isoformat()
        if active_only:
            params["activeOnly"] = "true"

        return await self.get(endpoint, params=params)

    async def create_rate_code(
        self, rate_data: RateCode | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new rate code.

        Args:
            rate_data: Rate code creation data

        Returns:
            APIResponse with created rate code details
        """
        if isinstance(rate_data, dict):
            rate_data = RateCode.model_validate(rate_data)

        endpoint = f"{self.api_domain}/v1/rates"

        payload = {
            "rateCode": rate_data.rate_code,
            "rateName": rate_data.rate_name,
            "rateCategory": rate_data.rate_category,
            "roomType": rate_data.room_type,
            "baseAmount": str(rate_data.base_amount),
            "currencyCode": rate_data.currency_code,
            "effectiveDate": rate_data.effective_date.isoformat(),
            "expiryDate": rate_data.expiry_date.isoformat()
            if rate_data.expiry_date
            else None,
            "minimumLOS": rate_data.minimum_los,
            "maximumLOS": rate_data.maximum_los,
            "advanceBookingDays": rate_data.advance_booking_days,
            "cancellationPolicy": rate_data.cancellation_policy,
            "depositRequired": rate_data.deposit_required,
            "depositPercentage": rate_data.deposit_percentage,
            "isQualified": rate_data.is_qualified,
            "qualificationRules": rate_data.qualification_rules,
            "marketSegment": rate_data.market_segment,
            "sourceCode": rate_data.source_code,
        }

        return await self.post(endpoint, json_data=payload)

    async def update_rate_code(
        self, rate_code: str, updates: dict[str, Any]
    ) -> APIResponse:
        """
        Update an existing rate code.

        Args:
            rate_code: Rate code identifier
            updates: Fields to update

        Returns:
            APIResponse with update confirmation
        """
        endpoint = f"{self.api_domain}/v1/rates/{rate_code}"

        return await self.put(endpoint, json_data=updates)

    async def get_rate_code_details(self, rate_code: str) -> APIResponse:
        """
        Get detailed information for a specific rate code.

        Args:
            rate_code: Rate code identifier

        Returns:
            APIResponse with rate code details
        """
        endpoint = f"{self.api_domain}/v1/rates/{rate_code}"

        return await self.get(endpoint)

    # Rate Plans

    async def create_rate_plan(
        self, plan_data: RatePlan | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new rate plan.

        Args:
            plan_data: Rate plan creation data

        Returns:
            APIResponse with created plan details
        """
        if isinstance(plan_data, dict):
            plan_data = RatePlan.model_validate(plan_data)

        endpoint = f"{self.api_domain}/v1/plans"

        payload = {
            "planCode": plan_data.plan_code,
            "planName": plan_data.plan_name,
            "planType": plan_data.plan_type,
            "rateCodes": plan_data.rate_codes,
            "stayDates": {
                "start": plan_data.stay_dates["start"].isoformat(),
                "end": plan_data.stay_dates["end"].isoformat(),
            },
            "bookingDates": {
                "start": plan_data.booking_dates["start"].isoformat(),
                "end": plan_data.booking_dates["end"].isoformat(),
            },
            "restrictions": plan_data.restrictions,
            "inclusions": plan_data.inclusions,
            "termsConditions": plan_data.terms_conditions,
            "marketingText": plan_data.marketing_text,
            "isActive": plan_data.is_active,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_rate_plans(
        self, plan_type: str | None = None, active_only: bool = True
    ) -> APIResponse:
        """
        Get available rate plans.

        Args:
            plan_type: Filter by plan type
            active_only: Show only active plans

        Returns:
            APIResponse with rate plans list
        """
        endpoint = f"{self.api_domain}/v1/plans"
        params = {}

        if plan_type:
            params["planType"] = plan_type
        if active_only:
            params["activeOnly"] = "true"

        return await self.get(endpoint, params=params)

    # Rate Restrictions

    async def set_rate_restriction(
        self, restriction_data: RateRestriction | dict[str, Any]
    ) -> APIResponse:
        """
        Set rate restriction for specific date and room type.

        Args:
            restriction_data: Restriction configuration

        Returns:
            APIResponse with restriction confirmation
        """
        if isinstance(restriction_data, dict):
            restriction_data = RateRestriction.model_validate(restriction_data)

        endpoint = f"{self.api_domain}/v1/restrictions"

        payload = {
            "rateCode": restriction_data.rate_code,
            "roomType": restriction_data.room_type,
            "restrictionDate": restriction_data.restriction_date.isoformat(),
            "closedToArrival": restriction_data.closed_to_arrival,
            "closedToDeparture": restriction_data.closed_to_departure,
            "closed": restriction_data.closed,
            "minimumLOS": restriction_data.minimum_los,
            "maximumLOS": restriction_data.maximum_los,
            "stopSell": restriction_data.stop_sell,
            "masterRestriction": restriction_data.master_restriction,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_rate_restrictions(
        self,
        rate_code: str,
        start_date: date,
        end_date: date,
        room_type: str | None = None,
    ) -> APIResponse:
        """
        Get rate restrictions for a date range.

        Args:
            rate_code: Rate code to check
            start_date: Start date of range
            end_date: End date of range
            room_type: Optional room type filter

        Returns:
            APIResponse with restrictions list
        """
        endpoint = f"{self.api_domain}/v1/restrictions"
        params = {
            "rateCode": rate_code,
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }

        if room_type:
            params["roomType"] = room_type

        return await self.get(endpoint, params=params)

    async def bulk_update_restrictions(
        self, restrictions: list[RateRestriction]
    ) -> APIResponse:
        """
        Update multiple rate restrictions in a single operation.

        Args:
            restrictions: List of rate restrictions

        Returns:
            APIResponse with bulk update results
        """
        endpoint = f"{self.api_domain}/v1/restrictions/bulk"

        payload = {
            "restrictions": [
                {
                    "rateCode": r.rate_code,
                    "roomType": r.room_type,
                    "restrictionDate": r.restriction_date.isoformat(),
                    "closedToArrival": r.closed_to_arrival,
                    "closedToDeparture": r.closed_to_departure,
                    "closed": r.closed,
                    "minimumLOS": r.minimum_los,
                    "maximumLOS": r.maximum_los,
                    "stopSell": r.stop_sell,
                    "masterRestriction": r.master_restriction,
                }
                for r in restrictions
            ]
        }

        return await self.post(endpoint, json_data=payload)

    # Yield Management

    async def configure_yield_management(
        self, config_data: YieldConfiguration | dict[str, Any]
    ) -> APIResponse:
        """
        Configure yield management settings.

        Args:
            config_data: Yield configuration data

        Returns:
            APIResponse with configuration confirmation
        """
        if isinstance(config_data, dict):
            config_data = YieldConfiguration.model_validate(config_data)

        endpoint = f"{self.api_domain}/v1/yield/config"

        payload = {
            "roomType": config_data.room_type,
            "baseRate": str(config_data.base_rate),
            "occupancyThresholds": config_data.occupancy_thresholds,
            "leadTimeFactors": {
                k: str(v) for k, v in config_data.lead_time_factors.items()
            },
            "seasonalAdjustments": {
                k: str(v) for k, v in config_data.seasonal_adjustments.items()
            },
            "demandAdjustments": {
                k: str(v) for k, v in config_data.demand_adjustments.items()
            },
            "minimumRate": str(config_data.minimum_rate),
            "maximumRate": str(config_data.maximum_rate),
            "autoYieldEnabled": config_data.auto_yield_enabled,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_yield_recommendations(
        self, room_type: str, target_date: date, current_occupancy: int, lead_days: int
    ) -> APIResponse:
        """
        Get yield management rate recommendations.

        Args:
            room_type: Room type to analyze
            target_date: Date for recommendations
            current_occupancy: Current occupancy percentage
            lead_days: Days until target date

        Returns:
            APIResponse with rate recommendations
        """
        endpoint = f"{self.api_domain}/v1/yield/recommendations"
        params = {
            "roomType": room_type,
            "targetDate": target_date.isoformat(),
            "currentOccupancy": current_occupancy,
            "leadDays": lead_days,
        }

        return await self.get(endpoint, params=params)

    # Promotional Rates

    async def create_promotional_rate(
        self, promo_data: PromotionalRate | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new promotional rate.

        Args:
            promo_data: Promotional rate data

        Returns:
            APIResponse with created promotion details
        """
        if isinstance(promo_data, dict):
            promo_data = PromotionalRate.model_validate(promo_data)

        endpoint = f"{self.api_domain}/v1/promotions"

        payload = {
            "promoCode": promo_data.promo_code,
            "promoName": promo_data.promo_name,
            "rateCode": promo_data.rate_code,
            "discountType": promo_data.discount_type,
            "discountValue": str(promo_data.discount_value),
            "validFrom": promo_data.valid_from.isoformat(),
            "validTo": promo_data.valid_to.isoformat(),
            "bookingFrom": promo_data.booking_from.isoformat()
            if promo_data.booking_from
            else None,
            "bookingTo": promo_data.booking_to.isoformat()
            if promo_data.booking_to
            else None,
            "roomTypes": promo_data.room_types,
            "minimumNights": promo_data.minimum_nights,
            "maximumUsage": promo_data.maximum_usage,
            "combinable": promo_data.combinable,
            "qualificationCriteria": promo_data.qualification_criteria,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_promotional_rates(
        self, active_only: bool = True, room_type: str | None = None
    ) -> APIResponse:
        """
        Get available promotional rates.

        Args:
            active_only: Show only active promotions
            room_type: Filter by room type

        Returns:
            APIResponse with promotions list
        """
        endpoint = f"{self.api_domain}/v1/promotions"
        params = {}

        if active_only:
            params["activeOnly"] = "true"
        if room_type:
            params["roomType"] = room_type

        return await self.get(endpoint, params=params)

    async def validate_promotional_code(
        self, promo_code: str, check_in_date: date, check_out_date: date, room_type: str
    ) -> APIResponse:
        """
        Validate a promotional code for specific criteria.

        Args:
            promo_code: Promotional code to validate
            check_in_date: Proposed check-in date
            check_out_date: Proposed check-out date
            room_type: Room type for booking

        Returns:
            APIResponse with validation results and applicable discount
        """
        endpoint = f"{self.api_domain}/v1/promotions/{promo_code}/validate"
        params = {
            "checkInDate": check_in_date.isoformat(),
            "checkOutDate": check_out_date.isoformat(),
            "roomType": room_type,
        }

        return await self.get(endpoint, params=params)

    # Rate Analysis and Reporting

    async def get_rate_analysis(
        self,
        start_date: date,
        end_date: date,
        room_types: list[str] | None = None,
        rate_categories: list[str] | None = None,
    ) -> APIResponse:
        """
        Get comprehensive rate analysis report.

        Args:
            start_date: Analysis start date
            end_date: Analysis end date
            room_types: Room types to analyze
            rate_categories: Rate categories to include

        Returns:
            APIResponse with rate analysis data
        """
        endpoint = f"{self.api_domain}/v1/reports/rate-analysis"
        params = {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}

        if room_types:
            params["roomTypes"] = ",".join(room_types)
        if rate_categories:
            params["rateCategories"] = ",".join(rate_categories)

        return await self.get(endpoint, params=params)

    async def get_competitive_analysis(
        self, target_date: date, room_type: str, competitors: list[str] | None = None
    ) -> APIResponse:
        """
        Get competitive rate analysis for market positioning.

        Args:
            target_date: Date for analysis
            room_type: Room type to compare
            competitors: List of competitor codes

        Returns:
            APIResponse with competitive rate data
        """
        endpoint = f"{self.api_domain}/v1/reports/competitive-analysis"
        params = {"targetDate": target_date.isoformat(), "roomType": room_type}

        if competitors:
            params["competitors"] = ",".join(competitors)

        return await self.get(endpoint, params=params)

    # Batch Operations

    async def batch_create_rate_codes(self, rate_codes: list[RateCode]) -> APIResponse:
        """
        Create multiple rate codes in a single operation.

        Args:
            rate_codes: List of rate codes to create

        Returns:
            APIResponse with batch creation results
        """
        tasks = [self.create_rate_code(rate_code) for rate_code in rate_codes]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = []
        failed = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append(
                    {"rate_code": rate_codes[i].rate_code, "error": str(result)}
                )
            elif isinstance(result, APIResponse) and result.success:
                successful.append(result.data)
            elif isinstance(result, APIResponse):
                failed.append(
                    {
                        "rate_code": rate_codes[i].rate_code,
                        "error": result.error or "Unknown error",
                    }
                )

        return APIResponse(
            success=len(failed) == 0,
            data={
                "successful_rates": successful,
                "failed_rates": failed,
                "total_processed": len(rate_codes),
                "success_count": len(successful),
                "failure_count": len(failed),
            },
        )

    # Convenience Methods

    async def get_best_available_rates(
        self,
        check_in_date: date,
        check_out_date: date,
        room_type: str,
        guest_count: int = 1,
    ) -> APIResponse:
        """
        Get best available rates for specific criteria.

        Args:
            check_in_date: Check-in date
            check_out_date: Check-out date
            room_type: Room type needed
            guest_count: Number of guests

        Returns:
            APIResponse with best available rates
        """
        endpoint = f"{self.api_domain}/v1/rates/best-available"
        params = {
            "checkInDate": check_in_date.isoformat(),
            "checkOutDate": check_out_date.isoformat(),
            "roomType": room_type,
            "guestCount": guest_count,
        }

        return await self.get(endpoint, params=params)
