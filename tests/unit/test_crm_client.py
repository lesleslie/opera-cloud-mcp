"""
Comprehensive unit tests for CRM API client.

Tests all CRM client functionality including guest profile management,
preferences, loyalty programs, search, and profile merging operations.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from opera_cloud_mcp.clients.api_clients.crm import CRMClient
from opera_cloud_mcp.clients.base_client import APIResponse
from opera_cloud_mcp.config.settings import Settings
from opera_cloud_mcp.models.guest import (
    GuestSearchCriteria,
    ProfileMergeRequest,
    VIPStatus,
)
from opera_cloud_mcp.utils.exceptions import (
    ResourceNotFoundError,
    ValidationError,
)


class TestCRMClient:
    """Comprehensive tests for CRM API client."""

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings."""
        return Settings(
            opera_client_id="test_id",
            opera_client_secret="test_secret",
            opera_base_url="https://api.test.com",
            opera_api_version="v1",
            request_timeout=30,
            max_retries=3,
            retry_backoff=1.0,
        )

    @pytest.fixture
    def mock_auth_handler(self) -> Mock:
        """Create mock auth handler."""
        handler = Mock()
        handler.get_token = AsyncMock(return_value="mock_token")
        handler.get_auth_header.return_value = {"Authorization": "Bearer mock_token"}
        handler.invalidate_token = AsyncMock()
        handler.get_token_info.return_value = {
            "has_token": True,
            "status": "valid",
            "expires_in": 3600,
        }
        return handler

    @pytest.fixture
    def crm_client(self, mock_auth_handler: Mock, mock_settings: Settings) -> CRMClient:
        """Create CRM client for testing."""
        return CRMClient(
            auth_handler=mock_auth_handler,
            hotel_id="TEST_HOTEL",
            settings=mock_settings,
            enable_rate_limiting=False,  # Disable for testing
            enable_monitoring=False,  # Disable for testing
        )

    @pytest.fixture
    def mock_guest_profile_data(self) -> dict:
        """Mock guest profile response data."""
        return {
            "guestProfile": {
                "guestId": "GUEST123",
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@test.com",
                "phone": "+1234567890",
                "birthDate": "1985-06-15",
                "status": "ACTIVE",
                "vipStatus": "VIP",
                "createdDate": "2024-01-15T10:00:00Z",
                "createdBy": "system",
                "dataProtectionConsent": True,
                "consentDate": "2024-01-15T10:00:00Z",
                "loyaltyPrograms": [
                    {
                        "programId": "REWARDS",
                        "programName": "Hotel Rewards",
                        "membershipNumber": "RW12345",
                        "tier": "GOLD",
                        "memberSince": "2020-01-01",
                        "isActive": True,
                        "points": {
                            "currentPoints": 15000,
                            "lifetimePoints": 45000,
                        },
                    }
                ],
                "preferences": [
                    {
                        "preferenceType": "ROOM_TYPE",
                        "preferenceValue": "Suite",
                        "priority": 1,
                        "isPrimary": True,
                    }
                ],
                "statistics": {
                    "totalStays": 15,
                    "totalNights": 45,
                    "totalRevenue": "12500.00",
                    "averageDailyRate": "275.00",
                    "firstStayDate": "2020-01-01",
                    "lastStayDate": "2024-01-01",
                },
            }
        }

    @pytest.fixture
    def mock_search_results_data(self) -> dict:
        """Mock guest search results data."""
        return {
            "guests": [
                {
                    "guestId": "GUEST123",
                    "firstName": "John",
                    "lastName": "Doe",
                    "email": "john.doe@test.com",
                    "status": "ACTIVE",
                    "vipStatus": "VIP",
                    "createdDate": "2024-01-15T10:00:00Z",
                },
                {
                    "guestId": "GUEST456",
                    "firstName": "Jane",
                    "lastName": "Smith",
                    "email": "jane.smith@test.com",
                    "status": "ACTIVE",
                    "vipStatus": "NONE",
                    "createdDate": "2024-01-10T10:00:00Z",
                },
            ],
            "pagination": {
                "page": 1,
                "pageSize": 20,
                "totalCount": 2,
                "totalPages": 1,
            },
            "searchDurationMs": 125,
        }

    # Test search_guests method
    @pytest.mark.asyncio
    async def test_search_guests_with_criteria(
        self, crm_client: CRMClient, mock_search_results_data: dict
    ):
        """Test guest search with structured criteria."""
        criteria = GuestSearchCriteria(
            name="John Doe",
            email="john.doe@test.com",
            vip_status=VIPStatus.VIP,
            page=1,
            page_size=20,
        )

        # Mock the request method
        with patch.object(crm_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data=mock_search_results_data,
                status_code=200,
            )

            result = await crm_client.search_guests(criteria=criteria)

            assert result.success is True
            assert result.data == mock_search_results_data

            # Verify request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "crm/v1/guests/search" in call_args[0]

    @pytest.mark.asyncio
    async def test_search_guests_with_parameters(
        self, crm_client: CRMClient, mock_search_results_data: dict
    ):
        """Test guest search with individual parameters."""
        with patch.object(crm_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data=mock_search_results_data,
                status_code=200,
            )

            result = await crm_client.search_guests(
                name="John Doe",
                email="john.doe@test.com",
                vip_status=VIPStatus.VIP,
                page=1,
                page_size=10,
            )

            assert result.success is True

            # Check that search data was built correctly
            call_args = mock_post.call_args
            request_data = call_args[1]["json_data"]
            assert request_data["searchCriteria"]["name"] == "John Doe"
            assert request_data["searchCriteria"]["email"] == "john.doe@test.com"
            assert request_data["searchCriteria"]["vipStatus"] == "VIP"

    @pytest.mark.asyncio
    async def test_search_guests_empty_results(self, crm_client: CRMClient):
        """Test guest search with no results."""
        empty_results = {
            "guests": [],
            "pagination": {
                "page": 1,
                "pageSize": 20,
                "totalCount": 0,
                "totalPages": 0,
            },
            "searchDurationMs": 50,
        }

        with patch.object(crm_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data=empty_results,
                status_code=200,
            )

            result = await crm_client.search_guests(name="NonExistent")

            assert result.success is True
            assert len(result.data["guests"]) == 0

    # Test get_guest_profile method
    @pytest.mark.asyncio
    async def test_get_guest_profile_success(
        self, crm_client: CRMClient, mock_guest_profile_data: dict
    ):
        """Test successful guest profile retrieval."""
        with patch.object(crm_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=mock_guest_profile_data,
                status_code=200,
            )

            result = await crm_client.get_guest_profile(
                guest_id="GUEST123",
                include_statistics=True,
                include_history=False,
            )

            assert result.success is True
            assert result.data["guestProfile"]["guestId"] == "GUEST123"

            # Check correct endpoint was called
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "crm/v1/guests/GUEST123" in call_args[0]

            # Check parameters were passed correctly
            params = call_args[1]["params"]
            assert params["includeStatistics"] is True
            assert params["includeHistory"] is False

    @pytest.mark.asyncio
    async def test_get_guest_profile_not_found(self, crm_client: CRMClient):
        """Test guest profile not found error."""
        with patch.object(crm_client, "get") as mock_get:
            mock_get.side_effect = ResourceNotFoundError("Guest profile not found")

            with pytest.raises(ResourceNotFoundError) as exc_info:
                await crm_client.get_guest_profile("NONEXISTENT")

            assert "not found" in str(exc_info.value).lower()

    # Test create_guest_profile method
    @pytest.mark.asyncio
    async def test_create_guest_profile_success(
        self, crm_client: CRMClient, mock_guest_profile_data: dict
    ):
        """Test successful guest profile creation."""
        with patch.object(crm_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data=mock_guest_profile_data,
                status_code=201,
            )

            result = await crm_client.create_guest_profile(
                first_name="John",
                last_name="Doe",
                email="john.doe@test.com",
                phone="+1234567890",
                birth_date=date(1985, 6, 15),
                vip_status=VIPStatus.VIP,
            )

            assert result.success is True

            # Check request data
            call_args = mock_post.call_args
            request_data = call_args[1]["json_data"]["guestProfile"]
            assert request_data["firstName"] == "John"
            assert request_data["lastName"] == "Doe"
            assert request_data["contact"]["email"] == "john.doe@test.com"
            assert request_data["vipStatus"] == "VIP"

    @pytest.mark.asyncio
    async def test_create_guest_profile_validation_error(self, crm_client: CRMClient):
        """Test guest profile creation with validation errors."""
        # Test missing first name
        with pytest.raises(ValidationError) as exc_info:
            await crm_client.create_guest_profile(
                first_name="",
                last_name="Doe",
            )
        assert "First name is required" in str(exc_info.value)

        # Test missing last name
        with pytest.raises(ValidationError) as exc_info:
            await crm_client.create_guest_profile(
                first_name="John",
                last_name="",
            )
        assert "Last name is required" in str(exc_info.value)

    # Test update_guest_profile method
    @pytest.mark.asyncio
    async def test_update_guest_profile_success(
        self, crm_client: CRMClient, mock_guest_profile_data: dict
    ):
        """Test successful guest profile update."""
        updates = {
            "email": "john.new@test.com",
            "vipStatus": "VVIP",
            "specialInstructions": "Prefers quiet rooms",
        }

        with patch.object(crm_client, "get_guest_profile") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=mock_guest_profile_data,
                status_code=200,
            )

            with patch.object(crm_client, "put") as mock_put:
                mock_put.return_value = APIResponse(
                    success=True,
                    data=mock_guest_profile_data,
                    status_code=200,
                )

                result = await crm_client.update_guest_profile(
                    guest_id="GUEST123",
                    updates=updates,
                    merge_preferences=True,
                )

                assert result.success is True

                # Verify profile validation was called
                mock_get.assert_called_once_with(
                    "GUEST123", include_statistics=False, include_history=False
                )

                # Check update request
                call_args = mock_put.call_args
                request_data = call_args[1]["json_data"]["guestProfile"]
                assert "modifiedDate" in request_data
                assert "modifiedBy" in request_data

    # Test get_guest_history method
    @pytest.mark.asyncio
    async def test_get_guest_history_success(self, crm_client: CRMClient):
        """Test successful guest history retrieval."""
        history_data = {
            "stays": [
                {
                    "reservationId": "RES123",
                    "confirmationNumber": "CONF123",
                    "hotelId": "HOTEL1",
                    "arrivalDate": "2024-01-01",
                    "departureDate": "2024-01-05",
                    "nights": 4,
                    "roomType": "Suite",
                    "status": "COMPLETED",
                    "roomRevenue": {"amount": 1200.00, "currency": "USD"},
                    "totalRevenue": {"amount": 1400.00, "currency": "USD"},
                }
            ],
            "statistics": {
                "totalStays": 1,
                "totalNights": 4,
                "totalRevenue": "1400.00",
            },
            "pagination": {
                "page": 1,
                "pageSize": 50,
                "totalCount": 1,
                "totalPages": 1,
            },
        }

        with patch.object(crm_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=history_data,
                status_code=200,
            )

            result = await crm_client.get_guest_history(
                guest_id="GUEST123",
                from_date=date(2024, 1, 1),
                to_date=date(2024, 12, 31),
                include_statistics=True,
            )

            assert result.success is True
            assert len(result.data["stays"]) == 1

            # Check parameters
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["fromDate"] == "2024-01-01"
            assert params["toDate"] == "2024-12-31"
            assert params["includeStatistics"] is True

    # Test merge_guest_profiles method
    @pytest.mark.asyncio
    async def test_merge_guest_profiles_success(self, crm_client: CRMClient):
        """Test successful guest profile merge."""
        merge_request = ProfileMergeRequest(
            sourceProfileId="GUEST123",
            targetProfileId="GUEST456",
            preserveHistory=True,
            mergePreferences=True,
            mergeLoyalty=True,
            mergeReason="Duplicate profiles detected",
            mergedBy="admin",
        )

        merge_result_data = {
            "mergeResult": {
                "success": True,
                "mergedProfileId": "GUEST456",
                "fieldsMerged": 15,
                "conflictsResolved": 2,
                "manualResolutionRequired": 0,
                "mergeDate": "2024-01-15T10:00:00Z",
                "processingTimeMs": 1500,
            },
            "conflicts": [],
            "warnings": [],
        }

        with patch.object(crm_client, "get_guest_profile") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data={"guestProfile": {"guestId": "test"}},
                status_code=200,
            )

            with patch.object(crm_client, "post") as mock_post:
                mock_post.return_value = APIResponse(
                    success=True,
                    data=merge_result_data,
                    status_code=200,
                )

                result = await crm_client.merge_guest_profiles(
                    primary_guest_id=merge_request.target_profile_id,
                    duplicate_guest_id=merge_request.source_profile_id,
                    merge_options={
                        "preserveHistory": merge_request.preserve_history,
                        "mergePreferences": merge_request.merge_preferences,
                        "mergeLoyalty": merge_request.merge_loyalty,
                        "mergeReason": merge_request.merge_reason,
                        "mergedBy": merge_request.merged_by,
                    },
                )

                assert result.success is True
                assert result.data["mergeResult"]["success"] is True

                # Verify both profiles were validated
                assert mock_get.call_count == 2

                # Check merge request
                call_args = mock_post.call_args
                assert "crm/v1/guests/merge" in call_args[0]

    # Test loyalty program methods
    @pytest.mark.asyncio
    async def test_get_loyalty_programs_success(self, crm_client: CRMClient):
        """Test successful loyalty programs retrieval."""
        loyalty_data = {
            "loyaltyPrograms": [
                {
                    "programId": "REWARDS",
                    "programName": "Hotel Rewards",
                    "membershipNumber": "RW12345",
                    "tier": "GOLD",
                    "memberSince": "2020-01-01",
                    "isActive": True,
                    "points": {
                        "currentPoints": 15000,
                        "lifetimePoints": 45000,
                        "pointsToNextTier": 5000,
                    },
                }
            ]
        }

        with patch.object(crm_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=loyalty_data,
                status_code=200,
            )

            result = await crm_client.get_loyalty_programs(
                guest_id="GUEST123",
                include_points=True,
                include_benefits=True,
            )

            assert result.success is True
            assert len(result.data["loyaltyPrograms"]) == 1

            # Check endpoint and parameters
            call_args = mock_get.call_args
            assert "crm/v1/guests/GUEST123/loyalty" in call_args[0]
            params = call_args[1]["params"]
            assert params["includePoints"] is True
            assert params["includeBenefits"] is True

    @pytest.mark.asyncio
    async def test_update_loyalty_points_success(self, crm_client: CRMClient):
        """Test successful loyalty points update."""
        points_result = {
            "loyaltyProgram": {
                "programId": "REWARDS",
                "points": {"currentPoints": 16000, "lifetimePoints": 46000},
            },
            "transaction": {
                "transactionType": "EARN",
                "pointsAdjustment": 1000,
                "transactionDate": "2024-01-15T10:00:00Z",
                "description": "Stay reward points",
            },
        }

        with patch.object(crm_client, "post") as mock_post:
            mock_post.return_value = APIResponse(
                success=True,
                data=points_result,
                status_code=200,
            )

            result = await crm_client.update_loyalty_points(
                guest_id="GUEST123",
                program_id="REWARDS",
                points_adjustment=1000,
                transaction_type="EARN",
                description="Stay reward points",
                reference_id="RES123",
            )

            assert result.success is True

            # Check request data
            call_args = mock_post.call_args
            request_data = call_args[1]["json_data"]["pointsTransaction"]
            assert request_data["programId"] == "REWARDS"
            assert request_data["pointsAdjustment"] == 1000
            assert request_data["transactionType"] == "EARN"
            assert request_data["description"] == "Stay reward points"
            assert request_data["referenceId"] == "RES123"

    # Test preference management methods
    @pytest.mark.asyncio
    async def test_get_guest_preferences_success(self, crm_client: CRMClient):
        """Test successful guest preferences retrieval."""
        preferences_data = {
            "preferences": [
                {
                    "preferenceId": "PREF123",
                    "preferenceType": "ROOM_TYPE",
                    "preferenceValue": "Suite",
                    "priority": 1,
                    "isPrimary": True,
                },
                {
                    "preferenceId": "PREF124",
                    "preferenceType": "FLOOR",
                    "preferenceValue": "High Floor",
                    "priority": 2,
                    "isPrimary": False,
                },
            ]
        }

        with patch.object(crm_client, "get") as mock_get:
            mock_get.return_value = APIResponse(
                success=True,
                data=preferences_data,
                status_code=200,
            )

            result = await crm_client.get_guest_preferences(
                guest_id="GUEST123",
                preference_type="ROOM_TYPE",
                hotel_specific=True,
            )

            assert result.success is True
            assert len(result.data["preferences"]) == 2

            # Check parameters
            call_args = mock_get.call_args
            params = call_args[1]["params"]
            assert params["preferenceType"] == "ROOM_TYPE"
            assert params["hotelSpecific"] == "true"

    @pytest.mark.asyncio
    async def test_update_guest_preferences_success(self, crm_client: CRMClient):
        """Test successful guest preferences update."""
        preferences = [
            {
                "preferenceType": "ROOM_TYPE",
                "preferenceValue": "Junior Suite",
                "priority": 1,
            },
            {
                "preferenceType": "FLOOR",
                "preferenceValue": "High Floor",
                "priority": 2,
            },
        ]

        updated_preferences_data = {"preferences": preferences}

        with patch.object(crm_client, "put") as mock_put:
            mock_put.return_value = APIResponse(
                success=True,
                data=updated_preferences_data,
                status_code=200,
            )

            result = await crm_client.update_guest_preferences(
                guest_id="GUEST123",
                preferences=preferences,
                merge_mode="merge",
            )

            assert result.success is True

            # Check request data
            call_args = mock_put.call_args
            request_data = call_args[1]["json_data"]
            assert request_data["preferences"] == preferences
            assert request_data["mergeMode"] == "merge"
            assert "modifiedDate" in request_data

    @pytest.mark.asyncio
    async def test_update_marketing_preferences_success(self, crm_client: CRMClient):
        """Test successful marketing preferences update."""
        marketing_prefs = {
            "emailMarketing": True,
            "smsMarketing": False,
            "promotionalOffers": True,
            "newsletter": True,
        }

        marketing_result = {
            "marketingPreferences": {
                **marketing_prefs,
                "consentDate": "2024-01-15T10:00:00Z",
                "modifiedDate": "2024-01-15T10:00:00Z",
            }
        }

        with patch.object(crm_client, "put") as mock_put:
            mock_put.return_value = APIResponse(
                success=True,
                data=marketing_result,
                status_code=200,
            )

            result = await crm_client.update_marketing_preferences(
                guest_id="GUEST123",
                marketing_preferences=marketing_prefs,
            )

            assert result.success is True

            # Check request data includes compliance fields
            call_args = mock_put.call_args
            request_data = call_args[1]["json_data"]["marketingPreferences"]
            assert "consentDate" in request_data
            assert "modifiedDate" in request_data

    # Test data transformation methods
    def test_transform_guest_profile(self, crm_client: CRMClient):
        """Test guest profile data transformation."""
        profile_data = {
            "guestId": "GUEST123",
            "firstName": "John",
            "lastName": "Doe",
            "birthDate": "1985-06-15",
            "createdDate": "2024-01-15T10:00:00Z",
            "loyaltyPrograms": [
                {
                    "programId": "REWARDS",
                    "memberSince": "2020-01-01",
                    "points": {
                        "expiryDate": "2025-12-31",
                        "lastActivityDate": "2024-01-01",
                    },
                }
            ],
            "statistics": {
                "totalRevenue": "12500.00",
                "averageDailyRate": "275.00",
                "firstStayDate": "2020-01-01",
            },
        }

        transformed = crm_client._transform_guest_profile(profile_data)

        # Check that date transformations were applied
        assert "birthDate" in transformed
        assert "createdDate" in transformed
        assert transformed["loyaltyPrograms"][0]["memberSince"] is not None
        assert transformed["statistics"]["totalRevenue"] == Decimal("12500.00")

    def test_parse_date_utility(self, crm_client: CRMClient):
        """Test date parsing utility method."""
        # Test valid date
        result = crm_client._parse_date("2024-01-15")
        assert result == "2024-01-15"

        # Test datetime string
        result = crm_client._parse_date("2024-01-15T10:00:00Z")
        assert result == "2024-01-15"

        # Test invalid date
        result = crm_client._parse_date("invalid-date")
        assert result == "invalid-date"  # Should return original

    def test_parse_datetime_utility(self, crm_client: CRMClient):
        """Test datetime parsing utility method."""
        # Test valid datetime
        result = crm_client._parse_datetime("2024-01-15T10:00:00Z")
        assert "2024-01-15T10:00:00" in result

        # Test invalid datetime
        result = crm_client._parse_datetime("invalid-datetime")
        assert result == "invalid-datetime"  # Should return original

    # Test error handling scenarios
    @pytest.mark.asyncio
    async def test_method_with_api_error(self, crm_client: CRMClient):
        """Test method behavior with API errors."""
        with patch.object(crm_client, "get") as mock_get:
            mock_get.side_effect = Exception("API connection error")

            with pytest.raises(Exception) as exc_info:
                await crm_client.get_guest_profile("GUEST123")

            assert "API connection error" in str(exc_info.value)

    # Test health check method
    def test_get_health_status(self, crm_client: CRMClient):
        """Test client health status method."""
        health_status = crm_client.get_health_status()

        assert "client_initialized" in health_status
        assert "hotel_id" in health_status
        assert health_status["hotel_id"] == "TEST_HOTEL"
        assert "authentication" in health_status

    # Test async context manager
    @pytest.mark.asyncio
    async def test_context_manager_usage(
        self, mock_auth_handler: Mock, mock_settings: Settings
    ):
        """Test CRM client as async context manager."""
        async with CRMClient(
            auth_handler=mock_auth_handler,
            hotel_id="TEST_HOTEL",
            settings=mock_settings,
        ) as client:
            assert client is not None
            health_status = client.get_health_status()
            assert health_status["hotel_id"] == "TEST_HOTEL"
