"""
Mock API responses for testing.

Provides realistic mock responses for various OPERA Cloud API endpoints
to support comprehensive testing without real API calls.
"""

from typing import Any


class MockOperaAPIResponses:
    """Collection of mock OPERA Cloud API responses."""

    @staticmethod
    def oauth_token_success() -> dict[str, Any]:
        """Mock successful OAuth token response."""
        return {
            "access_token": "mock_access_token_for_testing",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "read write",
        }

    @staticmethod
    def oauth_token_error() -> dict[str, Any]:
        """Mock OAuth token error response."""
        return {
            "error": "invalid_client",
            "error_description": "Client authentication failed",
        }

    @staticmethod
    def reservation_search_success() -> dict[str, Any]:
        """Mock successful reservation search response."""
        return {
            "reservations": [
                {
                    "confirmationNumber": "ABC123456",
                    "hotelId": "TEST_HOTEL",
                    "status": "CONFIRMED",
                    "guest": {
                        "guestId": "GUEST123",
                        "firstName": "John",
                        "lastName": "Doe",
                        "email": "john.doe@example.com",
                        "phone": "+1234567890",
                    },
                    "roomStay": {
                        "arrivalDate": "2024-12-01",
                        "departureDate": "2024-12-03",
                        "roomType": "STANDARD",
                        "roomNumber": "101",
                        "rateCode": "BAR",
                        "adults": 2,
                        "children": 0,
                    },
                    "totalAmount": {"amount": 398.00, "currencyCode": "USD"},
                    "createdDate": "2024-11-15T10:30:00Z",
                    "modifiedDate": "2024-11-16T14:20:00Z",
                },
                {
                    "confirmationNumber": "DEF789012",
                    "hotelId": "TEST_HOTEL",
                    "status": "CONFIRMED",
                    "guest": {
                        "guestId": "GUEST456",
                        "firstName": "Jane",
                        "lastName": "Smith",
                        "email": "jane.smith@example.com",
                        "phone": "+1234567891",
                    },
                    "roomStay": {
                        "arrivalDate": "2024-12-02",
                        "departureDate": "2024-12-04",
                        "roomType": "DELUXE",
                        "roomNumber": "201",
                        "rateCode": "CORP",
                        "adults": 1,
                        "children": 1,
                    },
                    "totalAmount": {"amount": 596.00, "currencyCode": "USD"},
                    "createdDate": "2024-11-16T09:15:00Z",
                },
            ],
            "totalCount": 2,
            "pageSize": 10,
            "page": 1,
        }

    @staticmethod
    def reservation_create_success() -> dict[str, Any]:
        """Mock successful reservation creation response."""
        return {
            "confirmationNumber": "NEW123456",
            "hotelId": "TEST_HOTEL",
            "status": "CONFIRMED",
            "guest": {
                "guestId": "GUEST789",
                "firstName": "Alice",
                "lastName": "Johnson",
                "email": "alice.johnson@example.com",
                "phone": "+1234567892",
            },
            "roomStay": {
                "arrivalDate": "2024-12-05",
                "departureDate": "2024-12-07",
                "roomType": "SUITE",
                "rateCode": "PROMO",
                "adults": 2,
                "children": 0,
            },
            "totalAmount": {"amount": 798.00, "currencyCode": "USD"},
            "depositRequired": {"amount": 199.50, "currencyCode": "USD"},
            "createdDate": "2024-11-20T16:45:00Z",
        }

    @staticmethod
    def guest_search_success() -> dict[str, Any]:
        """Mock successful guest search response."""
        return {
            "guests": [
                {
                    "guestId": "GUEST123",
                    "firstName": "John",
                    "lastName": "Doe",
                    "email": "john.doe@example.com",
                    "phone": "+1234567890",
                    "address": {
                        "addressLine1": "123 Main St",
                        "city": "New York",
                        "stateProvince": "NY",
                        "postalCode": "10001",
                        "country": "USA",
                    },
                    "loyaltyNumber": "LOYALTY123",
                    "loyaltyLevel": "GOLD",
                    "vipStatus": "VIP",
                    "preferences": [
                        {
                            "preferenceType": "ROOM",
                            "preferenceValue": "HIGH_FLOOR",
                            "description": "Prefers high floor rooms",
                        }
                    ],
                }
            ],
            "totalCount": 1,
        }

    @staticmethod
    def room_availability_success() -> dict[str, Any]:
        """Mock successful room availability response."""
        return {
            "availability": [
                {
                    "date": "2024-12-01",
                    "roomType": "STANDARD",
                    "availableRooms": 5,
                    "totalRooms": 10,
                    "rateCode": "BAR",
                    "rateAmount": 199.00,
                },
                {
                    "date": "2024-12-01",
                    "roomType": "DELUXE",
                    "availableRooms": 3,
                    "totalRooms": 8,
                    "rateCode": "BAR",
                    "rateAmount": 299.00,
                },
            ]
        }

    @staticmethod
    def room_status_success() -> dict[str, Any]:
        """Mock successful room status response."""
        return {
            "rooms": [
                {
                    "roomNumber": "101",
                    "roomType": "STANDARD",
                    "housekeepingStatus": "CLEAN",
                    "frontOfficeStatus": "VACANT",
                    "outOfOrder": False,
                    "outOfInventory": False,
                    "maintenanceRequired": False,
                },
                {
                    "roomNumber": "102",
                    "roomType": "STANDARD",
                    "housekeepingStatus": "DIRTY",
                    "frontOfficeStatus": "OCCUPIED",
                    "outOfOrder": False,
                    "outOfInventory": False,
                    "maintenanceRequired": False,
                },
            ]
        }

    @staticmethod
    def validation_error_response() -> dict[str, Any]:
        """Mock validation error response."""
        return {
            "errorCode": "VALIDATION_ERROR",
            "errorMessage": "Invalid request parameters",
            "errorDetails": {
                "arrivalDate": "Date format must be YYYY-MM-DD",
                "adults": "Must be at least 1",
            },
        }

    @staticmethod
    def authentication_error_response() -> dict[str, Any]:
        """Mock authentication error response."""
        return {
            "errorCode": "AUTHENTICATION_ERROR",
            "errorMessage": "Invalid or expired token",
            "errorDetails": {"token": "Token has expired and must be refreshed"},
        }

    @staticmethod
    def resource_not_found_response() -> dict[str, Any]:
        """Mock resource not found response."""
        return {
            "errorCode": "RESOURCE_NOT_FOUND",
            "errorMessage": "Reservation not found",
            "errorDetails": {
                "confirmationNumber": "ABC123456 was not found in the system"
            },
        }

    @staticmethod
    def rate_limit_error_response() -> dict[str, Any]:
        """Mock rate limit error response."""
        return {
            "errorCode": "RATE_LIMIT_EXCEEDED",
            "errorMessage": "Too many requests",
            "errorDetails": {"retryAfter": 60, "limit": 100, "window": 3600},
        }
