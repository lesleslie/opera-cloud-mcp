"""
API specifications and schemas for OPERA Cloud API endpoints.

Provides detailed API specifications, example requests/responses,
and schema documentation for all supported OPERA Cloud domains.
"""

from typing import Any

# OPERA Cloud API Domains
OPERA_API_DOMAINS: dict[str, dict[str, Any]] = {
    "oauth": {
        "name": "Authentication",
        "description": "OAuth2 token management and authentication",
        "base_path": "/oauth",
        "endpoints": {
            "token": {
                "method": "POST",
                "path": "/oauth/v1/tokens",
                "description": "Obtain OAuth2 access token",
                "request_schema": {
                    "grant_type": "client_credentials",
                    "client_id": "string",
                    "client_secret": "string",
                    "scope": "string (optional)",
                },
                "response_schema": {
                    "access_token": "string",
                    "token_type": "Bearer",
                    "expires_in": "integer",
                    "scope": "string",
                },
            }
        },
    },
    "rsv": {
        "name": "Reservations",
        "description": "Booking management and reservation operations",
        "base_path": "/rsv",
        "endpoints": {
            "search": {
                "method": "GET",
                "path": "/rsv/v1/hotels/{hotelId}/reservations",
                "description": "Search for reservations with various criteria",
                "parameters": {
                    "hotelId": "string (path)",
                    "arrivalDate": "date (query, optional)",
                    "departureDate": "date (query, optional)",
                    "guestName": "string (query, optional)",
                    "confirmationNumber": "string (query, optional)",
                    "status": "string (query, optional)",
                    "roomType": "string (query, optional)",
                    "limit": "integer (query, default: 20)",
                },
                "response_schema": {
                    "reservations": [
                        {
                            "confirmationNumber": "string",
                            "guestName": "string",
                            "arrivalDate": "date",
                            "departureDate": "date",
                            "roomType": "string",
                            "rateCode": "string",
                            "status": "string",
                            "totalAmount": "number",
                            "adults": "integer",
                            "children": "integer",
                        }
                    ],
                    "totalResults": "integer",
                    "hasMore": "boolean",
                },
            },
            "get": {
                "method": "GET",
                "path": "/rsv/v1/hotels/{hotelId}/reservations/{confirmationNumber}",
                "description": "Get detailed reservation information",
                "parameters": {
                    "hotelId": "string (path)",
                    "confirmationNumber": "string (path)",
                },
                "response_schema": {
                    "confirmationNumber": "string",
                    "guestProfile": {
                        "firstName": "string",
                        "lastName": "string",
                        "email": "string",
                        "phone": "string",
                    },
                    "arrivalDate": "date",
                    "departureDate": "date",
                    "roomType": "string",
                    "assignedRoom": "string (optional)",
                    "rateCode": "string",
                    "rateAmount": "number",
                    "totalAmount": "number",
                    "status": "string",
                    "adults": "integer",
                    "children": "integer",
                    "specialRequests": "string (optional)",
                    "packages": ["array of package objects"],
                    "addOns": ["array of addon objects"],
                },
            },
            "create": {
                "method": "POST",
                "path": "/rsv/v1/hotels/{hotelId}/reservations",
                "description": "Create a new reservation",
                "parameters": {"hotelId": "string (path)"},
                "request_schema": {
                    "guestProfile": {
                        "firstName": "string",
                        "lastName": "string",
                        "email": "string",
                        "phone": "string",
                    },
                    "arrivalDate": "date",
                    "departureDate": "date",
                    "roomType": "string",
                    "rateCode": "string",
                    "adults": "integer",
                    "children": "integer (default: 0)",
                    "specialRequests": "string (optional)",
                    "packages": ["array (optional)"],
                    "addOns": ["array (optional)"],
                    "corporateAccount": "string (optional)",
                    "travelAgent": "string (optional)",
                },
                "response_schema": {
                    "confirmationNumber": "string",
                    "status": "confirmed",
                    "totalAmount": "number",
                    "message": "string",
                },
            },
        },
    },
    "crm": {
        "name": "Customer Relations",
        "description": "Guest profile management and customer relations",
        "base_path": "/crm",
        "endpoints": {
            "search_guests": {
                "method": "GET",
                "path": "/crm/v1/hotels/{hotelId}/guests",
                "description": "Search guest profiles",
                "parameters": {
                    "hotelId": "string (path)",
                    "firstName": "string (query, optional)",
                    "lastName": "string (query, optional)",
                    "email": "string (query, optional)",
                    "phone": "string (query, optional)",
                    "loyaltyNumber": "string (query, optional)",
                    "limit": "integer (query, default: 20)",
                },
            },
            "create_guest": {
                "method": "POST",
                "path": "/crm/v1/hotels/{hotelId}/guests",
                "description": "Create a new guest profile",
                "request_schema": {
                    "firstName": "string",
                    "lastName": "string",
                    "email": "string",
                    "phone": "string",
                    "dateOfBirth": "date (optional)",
                    "nationality": "string (optional)",
                    "address": {
                        "street": "string",
                        "city": "string",
                        "state": "string",
                        "postalCode": "string",
                        "country": "string",
                    },
                    "preferences": {
                        "roomType": "string (optional)",
                        "floor": "string (optional)",
                        "smoking": "boolean (optional)",
                        "specialRequests": "string (optional)",
                    },
                    "loyaltyPrograms": ["array (optional)"],
                },
            },
        },
    },
    "inv": {
        "name": "Inventory Management",
        "description": "Room inventory and availability management",
        "base_path": "/inv",
        "endpoints": {
            "availability": {
                "method": "GET",
                "path": "/inv/v1/hotels/{hotelId}/availability",
                "description": "Check room availability",
                "parameters": {
                    "hotelId": "string (path)",
                    "arrivalDate": "date (query)",
                    "departureDate": "date (query)",
                    "roomType": "string (query, optional)",
                    "adults": "integer (query, default: 1)",
                    "children": "integer (query, default: 0)",
                },
                "response_schema": {
                    "availableRoomTypes": [
                        {
                            "roomType": "string",
                            "available": "integer",
                            "rateCode": "string",
                            "rateAmount": "number",
                            "description": "string",
                        }
                    ],
                    "totalAvailable": "integer",
                },
            },
            "room_status": {
                "method": "GET",
                "path": "/inv/v1/hotels/{hotelId}/rooms/status",
                "description": "Get current room status",
                "parameters": {
                    "hotelId": "string (path)",
                    "roomNumber": "string (query, optional)",
                    "status": "string (query, optional)",
                    "floor": "string (query, optional)",
                },
            },
        },
    },
    "fof": {
        "name": "Front Office",
        "description": "Front desk operations and daily reports",
        "base_path": "/fof",
        "endpoints": {
            "checkin": {
                "method": "POST",
                "path": "/fof/v1/reservations/{confirmationNumber}/checkin",
                "description": "Check in a guest",
                "parameters": {"confirmationNumber": "string (path)"},
                "request_schema": {
                    "roomNumber": "string (optional)",
                    "arrivalTime": "datetime (optional)",
                    "specialRequests": "string (optional)",
                    "keyCardsIssued": "integer (default: 2)",
                    "idVerification": "boolean (default: true)",
                },
            },
            "checkout": {
                "method": "POST",
                "path": "/fof/v1/reservations/{confirmationNumber}/checkout",
                "description": "Check out a guest",
                "parameters": {"confirmationNumber": "string (path)"},
                "request_schema": {
                    "roomNumber": "string",
                    "departureTime": "datetime (optional)",
                    "expressCheckout": "boolean (default: false)",
                    "folioSettlement": "boolean (default: true)",
                    "keyCardsReturned": "integer (default: 0)",
                },
            },
            "arrivals_report": {
                "method": "GET",
                "path": "/fof/v1/reports/arrivals",
                "description": "Get arrivals report for a date",
                "parameters": {
                    "date": "date (query)",
                    "status": "string (query, optional)",
                    "roomType": "string (query, optional)",
                },
            },
            "departures_report": {
                "method": "GET",
                "path": "/fof/v1/reports/departures",
                "description": "Get departures report for a date",
                "parameters": {
                    "date": "date (query)",
                    "status": "string (query, optional)",
                },
            },
        },
    },
    "csh": {
        "name": "Cashiering",
        "description": "Financial operations and payment processing",
        "base_path": "/csh",
        "endpoints": {
            "folio": {
                "method": "GET",
                "path": "/csh/v1/reservations/{confirmationNumber}/folio",
                "description": "Get guest folio with charges and payments",
                "parameters": {
                    "confirmationNumber": "string (path)",
                    "type": "string (query, default: master)",
                },
            },
            "post_charge": {
                "method": "POST",
                "path": "/csh/v1/reservations/{confirmationNumber}/charges",
                "description": "Post a charge to guest folio",
                "request_schema": {
                    "amount": "number",
                    "description": "string",
                    "department": "string",
                    "date": "date (optional)",
                    "reference": "string (optional)",
                },
            },
            "process_payment": {
                "method": "POST",
                "path": "/csh/v1/reservations/{confirmationNumber}/payments",
                "description": "Process a payment",
                "request_schema": {
                    "amount": "number",
                    "paymentMethod": "string",
                    "referenceNumber": "string (optional)",
                    "notes": "string (optional)",
                    "applyToBalance": "boolean (default: true)",
                },
            },
        },
    },
    "hsk": {
        "name": "Housekeeping",
        "description": "Room status and housekeeping operations",
        "base_path": "/hsk",
        "endpoints": {
            "room_status": {
                "method": "PUT",
                "path": "/hsk/v1/hotels/{hotelId}/rooms/{roomNumber}/status",
                "description": "Update room status",
                "request_schema": {
                    "status": "string",
                    "notes": "string (optional)",
                    "maintenanceRequired": "boolean (default: false)",
                    "estimatedCompletion": "datetime (optional)",
                },
            },
            "housekeeping_tasks": {
                "method": "GET",
                "path": "/hsk/v1/hotels/{hotelId}/tasks",
                "description": "Get housekeeping tasks",
                "parameters": {
                    "hotelId": "string (path)",
                    "date": "date (query, optional)",
                    "status": "string (query, optional)",
                    "roomNumber": "string (query, optional)",
                },
            },
        },
    },
}

# Common Status Codes and Error Responses
HTTP_STATUS_CODES = {
    200: "OK - Request successful",
    201: "Created - Resource created successfully",
    400: "Bad Request - Invalid request parameters",
    401: "Unauthorized - Authentication required or invalid",
    403: "Forbidden - Access denied",
    404: "Not Found - Resource not found",
    409: "Conflict - Resource conflict (e.g., duplicate reservation)",
    422: "Unprocessable Entity - Validation error",
    429: "Too Many Requests - Rate limit exceeded",
    500: "Internal Server Error - Server error",
    502: "Bad Gateway - Upstream server error",
    503: "Service Unavailable - Service temporarily unavailable",
}

# Standard Error Response Schema
ERROR_RESPONSE_SCHEMA = {
    "error": {
        "code": "string",
        "message": "string",
        "details": "object (optional)",
        "timestamp": "datetime",
        "requestId": "string",
    }
}

# Common Field Formats and Validation Rules
FIELD_FORMATS = {
    "date": "YYYY-MM-DD (ISO 8601)",
    "datetime": "YYYY-MM-DDTHH:MM:SSZ (ISO 8601)",
    "email": "Valid email address format",
    "phone": "International format recommended (+1234567890)",
    "confirmationNumber": "Alphanumeric, 6-12 characters",
    "roomNumber": "Alphanumeric, property-specific format",
    "currency": "Decimal with 2 decimal places",
    "hotelId": "Property code as configured in OPERA Cloud",
}

# Rate Limiting Information
RATE_LIMITS = {
    "default": "100 requests per minute per client",
    "authentication": "10 requests per minute per client",
    "bulk_operations": "20 requests per minute per client",
    "reports": "30 requests per minute per client",
}

# Authentication Requirements
AUTH_REQUIREMENTS = {
    "type": "OAuth2 Bearer Token",
    "header": "Authorization: Bearer {access_token}",
    "scope_required": True,
    "token_expiry": "Typically 3600 seconds (1 hour)",
    "refresh_strategy": "Re-authenticate using client credentials",
}


def get_api_spec(domain: str, endpoint: str | None = None) -> dict[str, Any]:
    """
    Get API specification for a specific domain or endpoint.

    Args:
        domain: API domain (e.g., 'rsv', 'crm', 'fof')
        endpoint: Specific endpoint within domain (optional)

    Returns:
        Dictionary containing API specification details
    """
    if domain not in OPERA_API_DOMAINS:
        return {"error": f"Unknown API domain: {domain}"}

    domain_spec = OPERA_API_DOMAINS[domain]

    if endpoint:
        if endpoint not in domain_spec.get("endpoints", {}):
            return {"error": f"Unknown endpoint: {endpoint} in domain: {domain}"}
        return {
            "domain": domain,
            "endpoint": endpoint,
            "spec": domain_spec["endpoints"][endpoint],
            "base_path": domain_spec["base_path"],
        }

    return domain_spec


def get_all_endpoints() -> list[dict[str, Any]]:
    """
    Get a list of all available API endpoints across all domains.

    Returns:
        List of dictionaries containing endpoint information
    """
    all_endpoints = []

    for domain_key, domain_info in OPERA_API_DOMAINS.items():
        for endpoint_key, endpoint_info in domain_info.get("endpoints", {}).items():
            all_endpoints.append(
                {
                    "domain": domain_key,
                    "domain_name": domain_info["name"],
                    "endpoint": endpoint_key,
                    "method": endpoint_info.get("method", "GET"),
                    "path": endpoint_info.get("path", ""),
                    "description": endpoint_info.get("description", ""),
                }
            )

    return all_endpoints


def validate_request_schema(
    domain: str, endpoint: str, request_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Validate request data against the API schema.

    Args:
        domain: API domain
        endpoint: API endpoint
        request_data: Request data to validate

    Returns:
        Dictionary with validation results
    """
    spec = get_api_spec(domain, endpoint)

    if "error" in spec:
        return spec

    request_schema = spec["spec"].get("request_schema", {})

    if not request_schema:
        return {"valid": True, "message": "No schema validation required"}

    # Basic validation (in a real implementation, use jsonschema or similar)
    missing_required = [
        field
        for field, field_type in request_schema.items()
        if "string" in str(field_type) and field not in request_data
    ]

    if missing_required:
        return {
            "valid": False,
            "errors": missing_required,
            "message": f"Missing required fields: {', '.join(missing_required)}",
        }

    return {"valid": True, "message": "Request data is valid"}


def get_example_request(domain: str, endpoint: str) -> dict[str, Any]:
    """
    Generate an example request for a specific endpoint.

    Args:
        domain: API domain
        endpoint: API endpoint

    Returns:
        Dictionary containing example request data
    """
    examples: dict[tuple[str, str], dict[str, Any]] = {
        ("rsv", "create"): {
            "guestProfile": {
                "firstName": "John",
                "lastName": "Smith",
                "email": "john.smith@email.com",
                "phone": "+1-555-123-4567",
            },
            "arrivalDate": "2024-03-15",
            "departureDate": "2024-03-17",
            "roomType": "DLXK",
            "rateCode": "BAR",
            "adults": 2,
            "children": 0,
            "specialRequests": "High floor room preferred",
        },
        ("crm", "create_guest"): {
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "jane.doe@email.com",
            "phone": "+1-555-987-6543",
            "dateOfBirth": "1985-06-15",
            "nationality": "US",
            "address": {
                "street": "123 Main Street",
                "city": "New York",
                "state": "NY",
                "postalCode": "10001",
                "country": "US",
            },
            "preferences": {
                "roomType": "DLXK",
                "floor": "high",
                "smoking": False,
                "specialRequests": "Extra pillows",
            },
        },
        ("fof", "checkin"): {
            "roomNumber": "1015",
            "arrivalTime": "2024-03-15T15:30:00Z",
            "keyCardsIssued": 2,
            "idVerification": True,
        },
        ("csh", "process_payment"): {
            "amount": 299.99,
            "paymentMethod": "VISA",
            "referenceNumber": "TXN123456",
            "applyToBalance": True,
        },
    }

    # Get example for the specific domain and endpoint, or return default message
    return examples.get((domain, endpoint)) or {
        "message": "No example available for this endpoint"
    }
