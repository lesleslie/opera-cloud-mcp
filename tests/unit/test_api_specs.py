"""
Unit tests for OPERA Cloud API specifications.

These tests verify that the API specification data is correctly
structured and provides accurate endpoint information.
"""

from opera_cloud_mcp.resources.api_specs import (
    AUTH_REQUIREMENTS,
    ERROR_RESPONSE_SCHEMA,
    FIELD_FORMATS,
    HTTP_STATUS_CODES,
    OPERA_API_DOMAINS,
    RATE_LIMITS,
    get_all_endpoints,
    get_api_spec,
    get_example_request,
    validate_request_schema,
)


class TestAPISpecs:
    """Test suite for API specifications module."""

    def test_opera_api_domains_structure(self):
        """Test that OPERA_API_DOMAINS has expected structure."""
        assert isinstance(OPERA_API_DOMAINS, dict)

        # Check that required domains exist
        required_domains = ["oauth", "rsv", "crm", "inv", "fof", "csh", "hsk"]
        for domain in required_domains:
            assert domain in OPERA_API_DOMAINS

        # Check domain structure
        for _domain_key, domain_info in OPERA_API_DOMAINS.items():
            assert isinstance(domain_info, dict)
            assert "name" in domain_info
            assert "description" in domain_info
            assert "base_path" in domain_info
            assert "endpoints" in domain_info
            assert isinstance(domain_info["endpoints"], dict)

    def test_http_status_codes(self):
        """Test HTTP status codes dictionary."""
        assert isinstance(HTTP_STATUS_CODES, dict)

        # Check common status codes
        expected_codes = [200, 201, 400, 401, 403, 404, 409, 422, 429, 500, 502, 503]
        for code in expected_codes:
            assert code in HTTP_STATUS_CODES
            assert isinstance(HTTP_STATUS_CODES[code], str)
            assert len(HTTP_STATUS_CODES[code]) > 0

    def test_error_response_schema(self):
        """Test error response schema structure."""
        assert isinstance(ERROR_RESPONSE_SCHEMA, dict)
        assert "error" in ERROR_RESPONSE_SCHEMA

        error_schema = ERROR_RESPONSE_SCHEMA["error"]
        assert "code" in error_schema
        assert "message" in error_schema
        assert "details" in error_schema
        assert "timestamp" in error_schema
        assert "requestId" in error_schema

    def test_field_formats(self):
        """Test field format definitions."""
        assert isinstance(FIELD_FORMATS, dict)

        expected_fields = [
            "date",
            "datetime",
            "email",
            "phone",
            "confirmationNumber",
            "roomNumber",
            "currency",
            "hotelId",
        ]

        for field in expected_fields:
            assert field in FIELD_FORMATS
            assert isinstance(FIELD_FORMATS[field], str)
            assert len(FIELD_FORMATS[field]) > 0

    def test_rate_limits(self):
        """Test rate limit information."""
        assert isinstance(RATE_LIMITS, dict)

        expected_categories = [
            "default",
            "authentication",
            "bulk_operations",
            "reports",
        ]
        for category in expected_categories:
            assert category in RATE_LIMITS
            assert isinstance(RATE_LIMITS[category], str)
            assert "requests per minute" in RATE_LIMITS[category]

    def test_auth_requirements(self):
        """Test authentication requirements structure."""
        assert isinstance(AUTH_REQUIREMENTS, dict)

        required_fields = [
            "type",
            "header",
            "scope_required",
            "token_expiry",
            "refresh_strategy",
        ]
        for field in required_fields:
            assert field in AUTH_REQUIREMENTS

        assert AUTH_REQUIREMENTS["type"] == "OAuth2 Bearer Token"
        assert "Bearer" in AUTH_REQUIREMENTS["header"]
        assert isinstance(AUTH_REQUIREMENTS["scope_required"], bool)

    def test_get_api_spec_valid_domain(self):
        """Test get_api_spec with valid domain."""
        result = get_api_spec("rsv")

        assert isinstance(result, dict)
        assert "name" in result
        assert "description" in result
        assert "base_path" in result
        assert "endpoints" in result
        assert result["name"] == "Reservations"
        assert result["base_path"] == "/rsv"

    def test_get_api_spec_valid_domain_and_endpoint(self):
        """Test get_api_spec with valid domain and endpoint."""
        result = get_api_spec("rsv", "search")

        assert isinstance(result, dict)
        assert "domain" in result
        assert "endpoint" in result
        assert "spec" in result
        assert "base_path" in result

        assert result["domain"] == "rsv"
        assert result["endpoint"] == "search"
        assert result["base_path"] == "/rsv"

        # Check endpoint specification
        spec = result["spec"]
        assert "method" in spec
        assert "path" in spec
        assert "description" in spec

    def test_get_api_spec_invalid_domain(self):
        """Test get_api_spec with invalid domain."""
        result = get_api_spec("invalid_domain")

        assert isinstance(result, dict)
        assert "error" in result
        assert "Unknown API domain: invalid_domain" in result["error"]

    def test_get_api_spec_invalid_endpoint(self):
        """Test get_api_spec with invalid endpoint."""
        result = get_api_spec("rsv", "invalid_endpoint")

        assert isinstance(result, dict)
        assert "error" in result
        assert "Unknown endpoint: invalid_endpoint" in result["error"]

    def test_get_all_endpoints(self):
        """Test get_all_endpoints function."""
        endpoints = get_all_endpoints()

        assert isinstance(endpoints, list)
        assert len(endpoints) > 0

        # Check structure of first endpoint
        first_endpoint = endpoints[0]
        required_fields = [
            "domain",
            "domain_name",
            "endpoint",
            "method",
            "path",
            "description",
        ]
        for field in required_fields:
            assert field in first_endpoint

        # Check that we have endpoints from different domains
        domains = {ep["domain"] for ep in endpoints}
        assert len(domains) > 1
        assert "rsv" in domains
        assert "crm" in domains
        assert "fof" in domains

    def test_validate_request_schema_no_schema(self):
        """Test validate_request_schema when no schema is required."""
        result = validate_request_schema("fof", "arrivals_report", {})

        assert isinstance(result, dict)
        assert result["valid"]
        assert "No schema validation required" in result["message"]

    def test_validate_request_schema_valid_data(self):
        """Test validate_request_schema with valid data."""
        # This is a simplified test - in a real implementation,
        # we would have more sophisticated validation
        request_data = {
            "guestProfile": {"firstName": "John", "lastName": "Doe"},
            "arrivalDate": "2024-03-15",
            "departureDate": "2024-03-17",
        }

        result = validate_request_schema("rsv", "create", request_data)

        assert isinstance(result, dict)
        assert "valid" in result
        assert "message" in result

    def test_validate_request_schema_invalid_domain(self):
        """Test validate_request_schema with invalid domain."""
        result = validate_request_schema("invalid", "create", {})

        assert isinstance(result, dict)
        assert "error" in result

    def test_get_example_request_existing(self):
        """Test get_example_request for existing examples."""
        result = get_example_request("rsv", "create")

        assert isinstance(result, dict)
        assert "guestProfile" in result
        assert "arrivalDate" in result
        assert "departureDate" in result

        guest_profile = result["guestProfile"]
        assert "firstName" in guest_profile
        assert "lastName" in guest_profile
        assert "email" in guest_profile
        assert "phone" in guest_profile

    def test_get_example_request_crm_create(self):
        """Test get_example_request for CRM guest creation."""
        result = get_example_request("crm", "create_guest")

        assert isinstance(result, dict)
        assert "firstName" in result
        assert "lastName" in result
        assert "email" in result
        assert "address" in result
        assert "preferences" in result

        address = result["address"]
        assert "street" in address
        assert "city" in address
        assert "country" in address

    def test_get_example_request_front_office_checkin(self):
        """Test get_example_request for front office check-in."""
        result = get_example_request("fof", "checkin")

        assert isinstance(result, dict)
        assert "roomNumber" in result
        assert "arrivalTime" in result
        assert "keyCardsIssued" in result
        assert "idVerification" in result

    def test_get_example_request_cashiering_payment(self):
        """Test get_example_request for payment processing."""
        result = get_example_request("csh", "process_payment")

        assert isinstance(result, dict)
        assert "amount" in result
        assert "paymentMethod" in result
        assert "referenceNumber" in result
        assert "applyToBalance" in result

        # Check amount is a number
        assert isinstance(result["amount"], int | float)

    def test_get_example_request_non_existent(self):
        """Test get_example_request for non-existent example."""
        result = get_example_request("unknown", "endpoint")

        assert isinstance(result, dict)
        assert "message" in result
        assert "No example available" in result["message"]

    def test_reservation_domain_endpoints(self):
        """Test reservations domain endpoints."""
        rsv_domain = OPERA_API_DOMAINS["rsv"]

        expected_endpoints = ["search", "get", "create"]
        for endpoint in expected_endpoints:
            assert endpoint in rsv_domain["endpoints"]

        # Test search endpoint details
        search_endpoint = rsv_domain["endpoints"]["search"]
        assert search_endpoint["method"] == "GET"
        assert "/rsv/v1/hotels/{hotelId}/reservations" in search_endpoint["path"]
        assert "parameters" in search_endpoint
        assert "response_schema" in search_endpoint

    def test_crm_domain_endpoints(self):
        """Test CRM domain endpoints."""
        crm_domain = OPERA_API_DOMAINS["crm"]

        expected_endpoints = ["search_guests", "create_guest"]
        for endpoint in expected_endpoints:
            assert endpoint in crm_domain["endpoints"]

    def test_front_office_domain_endpoints(self):
        """Test Front Office domain endpoints."""
        fof_domain = OPERA_API_DOMAINS["fof"]

        expected_endpoints = [
            "checkin",
            "checkout",
            "arrivals_report",
            "departures_report",
        ]
        for endpoint in expected_endpoints:
            assert endpoint in fof_domain["endpoints"]

    def test_cashiering_domain_endpoints(self):
        """Test Cashiering domain endpoints."""
        csh_domain = OPERA_API_DOMAINS["csh"]

        expected_endpoints = ["folio", "post_charge", "process_payment"]
        for endpoint in expected_endpoints:
            assert endpoint in csh_domain["endpoints"]

    def test_api_spec_data_types(self):
        """Test that API spec data maintains proper types."""
        # Test that all domain names are strings
        for domain_key, domain_info in OPERA_API_DOMAINS.items():
            assert isinstance(domain_key, str)
            assert isinstance(domain_info["name"], str)
            assert isinstance(domain_info["description"], str)
            assert isinstance(domain_info["base_path"], str)

            # Test endpoint structure
            for endpoint_key, endpoint_info in domain_info["endpoints"].items():
                assert isinstance(endpoint_key, str)
                assert isinstance(endpoint_info["method"], str)
                assert isinstance(endpoint_info["path"], str)
                assert isinstance(endpoint_info["description"], str)

    def test_comprehensive_domain_coverage(self):
        """Test that we have comprehensive coverage of OPERA domains."""
        expected_domains = {
            "oauth": "Authentication",
            "rsv": "Reservations",
            "crm": "Customer Relations",
            "inv": "Inventory Management",
            "fof": "Front Office",
            "csh": "Cashiering",
            "hsk": "Housekeeping",
        }

        for domain_key, expected_name in expected_domains.items():
            assert domain_key in OPERA_API_DOMAINS
            assert OPERA_API_DOMAINS[domain_key]["name"] == expected_name

    def test_endpoint_parameter_structures(self):
        """Test that endpoints have proper parameter structures."""
        # Test reservations search parameters
        search_params = OPERA_API_DOMAINS["rsv"]["endpoints"]["search"]["parameters"]
        assert "hotelId" in search_params
        assert "arrivalDate" in search_params
        assert "limit" in search_params

        # Test parameter descriptions exist
        for _param_name, param_desc in search_params.items():
            assert isinstance(param_desc, str)
            assert len(param_desc) > 0
