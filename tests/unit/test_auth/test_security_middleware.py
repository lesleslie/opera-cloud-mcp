"""Unit tests for security middleware.

Tests for opera_cloud_mcp/auth/security_middleware.py
"""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from opera_cloud_mcp.auth.security_middleware import (
    SecurityContext,
    ThreatDetector,
    SecurityMiddleware,
    create_security_middleware,
)
from opera_cloud_mcp.config.security_settings import SecuritySettings
from opera_cloud_mcp.utils.exceptions import SecurityError


class TestSecurityContext:
    """Test SecurityContext model."""

    def test_security_context_creation(self):
        """Test creating a security context with all fields."""
        context = SecurityContext(
            request_id="req_001",
            timestamp=datetime.now(UTC),
            client_id="test_client",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            risk_score=10,
            blocked_reason="Test block",
            security_flags={"flag1", "flag2"},
        )
        assert context.request_id == "req_001"
        assert context.client_id == "test_client"
        assert context.ip_address == "192.168.1.1"
        assert context.user_agent == "Mozilla/5.0"
        assert context.risk_score == 10
        assert context.blocked_reason == "Test block"
        assert "flag1" in context.security_flags
        assert "flag2" in context.security_flags

    def test_security_context_defaults(self):
        """Test security context default values."""
        context = SecurityContext(
            request_id="req_002",
            timestamp=datetime.now(UTC),
        )
        assert context.client_id is None
        assert context.ip_address is None
        assert context.user_agent is None
        assert context.risk_score == 0
        assert context.blocked_reason is None
        assert context.security_flags == set()

    def test_security_context_security_flags_mutable(self):
        """Test that security_flags can be modified."""
        context = SecurityContext(
            request_id="req_003",
            timestamp=datetime.now(UTC),
        )

        context.security_flags.add("new_flag")
        assert "new_flag" in context.security_flags


class TestThreatDetector:
    """Test ThreatDetector class."""

    @pytest.fixture
    def security_settings(self):
        """Create test security settings."""
        return SecuritySettings(
            enable_rate_limiting=True,
            enable_anomaly_detection=True,
            enable_ip_reputation_check=False,
            enable_audit_logging=False,
            require_https=False,
            security_testing_mode=True,
        )

    def test_threat_detector_init(self, security_settings):
        """Test threat detector initialization."""
        detector = ThreatDetector(security_settings)

        assert detector.settings == security_settings
        assert detector._suspicious_ips == {}
        assert len(detector._user_agent_patterns) > 0
        assert len(detector._known_attack_patterns) > 0

    def test_analyze_request_no_threats(self, security_settings):
        """Test request analysis with no threats."""
        detector = ThreatDetector(security_settings)

        context = SecurityContext(
            request_id="req_001",
            timestamp=datetime.now(UTC),
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            client_id="test_client",
        )

        risk_score, threats = asyncio.run(detector.analyze_request(context))

        assert risk_score >= 0
        assert isinstance(threats, list)
        assert risk_score <= 100

    def test_analyze_request_suspicious_user_agent(self, security_settings):
        """Test request analysis with suspicious user agent."""
        detector = ThreatDetector(security_settings)

        context = SecurityContext(
            request_id="req_002",
            timestamp=datetime.now(UTC),
            user_agent="curl/7.0",
        )

        risk_score, threats = asyncio.run(detector.analyze_request(context))

        assert risk_score > 0
        # Check that we got at least one threat indicator
        assert len(threats) > 0 or risk_score > 0

    def test_analyze_request_missing_user_agent(self, security_settings):
        """Test request analysis with missing user agent."""
        detector = ThreatDetector(security_settings)

        context = SecurityContext(
            request_id="req_003",
            timestamp=datetime.now(UTC),
            user_agent="ShortUA",  # Less than 10 characters
        )

        risk_score, threats = asyncio.run(detector.analyze_request(context))

        assert risk_score >= 15  # Missing/short user agent adds at least 15 to risk score

    def test_analyze_request_invalid_ip(self, security_settings):
        """Test request analysis with invalid IP address."""
        detector = ThreatDetector(security_settings)

        context = SecurityContext(
            request_id="req_004",
            timestamp=datetime.now(UTC),
            ip_address="invalid_ip_address",
        )

        risk_score, threats = asyncio.run(detector.analyze_request(context))

        assert risk_score >= 50
        assert "invalid_ip_address" in threats

    def test_analyze_user_agent_legitimate(self, security_settings):
        """Test user agent analysis with legitimate browser."""
        detector = ThreatDetector(security_settings)

        risk_score, threats = detector._analyze_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )

        assert risk_score == 0
        assert threats == []

    def test_analyze_user_agent_suspicious_pattern(self, security_settings):
        """Test user agent analysis with suspicious pattern."""
        detector = ThreatDetector(security_settings)

        risk_score, threats = detector._analyze_user_agent("BadBot/1.0")

        assert risk_score > 0
        assert any("suspicious_user_agent" in t for t in threats)

    def test_analyze_user_agent_attack_pattern(self, security_settings):
        """Test user agent analysis with attack pattern."""
        detector = ThreatDetector(security_settings)

        risk_score, threats = detector._analyze_user_agent(
            "Mozilla/5.0 <script>alert('xss')</script>"
        )

        assert risk_score >= 40
        assert any("attack_pattern" in t for t in threats)

    def test_analyze_user_agent_too_long(self, security_settings):
        """Test user agent analysis with extremely long UA."""
        detector = ThreatDetector(security_settings)

        long_ua = "A" * 2500
        risk_score, threats = detector._analyze_user_agent(long_ua)

        assert risk_score >= 20
        assert any("extremely_long_user_agent" in t for t in threats)

    def test_record_ip_request(self, security_settings):
        """Test recording IP requests for frequency analysis."""
        detector = ThreatDetector(security_settings)

        ip_address = "192.168.1.1"

        # Record multiple requests
        for _ in range(5):
            detector._record_ip_request(ip_address)

        assert ip_address in detector._suspicious_ips
        assert len(detector._suspicious_ips[ip_address]) == 5

    def test_record_ip_request_cleanup_old(self, security_settings):
        """Test that old IP requests are cleaned up."""
        detector = ThreatDetector(security_settings)

        ip_address = "192.168.1.2"

        # Mock old requests
        old_time = datetime.now(UTC) - timedelta(hours=2)
        with patch("opera_cloud_mcp.auth.security_middleware.datetime") as mock_dt:
            mock_dt.now.return_value = old_time
            detector._record_ip_request(ip_address)

        # Record new request
        detector._record_ip_request(ip_address)

        # Should only have the recent request
        assert len(detector._suspicious_ips[ip_address]) == 1

    def test_check_request_frequency_high(self, security_settings):
        """Test high-frequency request detection."""
        detector = ThreatDetector(security_settings)

        ip_address = "10.0.0.1"

        # Add 60 requests within 10 minutes (more than 50 threshold)
        now = datetime.now(UTC)
        detector._suspicious_ips[ip_address] = [
            now - timedelta(seconds=i * 10) for i in range(60)  # All within 10 minutes
        ]

        risk_score, threats = detector._check_request_frequency(ip_address, 0, [])

        assert risk_score >= 40
        assert "high_frequency_requests" in threats

    def test_check_request_frequency_elevated(self, security_settings):
        """Test elevated frequency request detection."""
        detector = ThreatDetector(security_settings)

        ip_address = "10.0.0.2"

        # Add 25 requests within 10 minutes (more than 20 threshold, less than 50)
        now = datetime.now(UTC)
        detector._suspicious_ips[ip_address] = [
            now - timedelta(seconds=i * 20) for i in range(25)  # All within 10 minutes
        ]

        risk_score, threats = detector._check_request_frequency(ip_address, 0, [])

        assert risk_score >= 20
        assert "elevated_request_frequency" in threats

    def test_is_suspicious_ip_range(self, security_settings):
        """Test suspicious IP range detection."""
        detector = ThreatDetector(security_settings)

        # Test IP in suspicious range (10.0.0.0/8)
        import ipaddress

        suspicious_ip = ipaddress.ip_address("10.0.0.5")
        assert detector._is_suspicious_ip_range(suspicious_ip) is True

        # Test IP not in suspicious range
        normal_ip = ipaddress.ip_address("8.8.8.8")
        assert detector._is_suspicious_ip_range(normal_ip) is False


class TestSecurityMiddleware:
    """Test SecurityMiddleware class."""

    @pytest.fixture
    def security_settings(self):
        """Create test security settings."""
        return SecuritySettings(
            enable_rate_limiting=True,
            enable_anomaly_detection=False,
            enable_ip_reputation_check=False,
            enable_audit_logging=False,
            require_https=False,
            security_testing_mode=True,
            auth_rate_limit_requests=10,
            auth_rate_limit_window_minutes=1,
            client_lockout_duration_minutes=5,
        )

    @pytest.fixture
    def middleware(self, security_settings):
        """Create security middleware instance."""
        return SecurityMiddleware(security_settings)

    def test_security_middleware_init(self, middleware):
        """Test middleware initialization."""
        assert middleware.settings is not None
        assert middleware.threat_detector is not None
        assert middleware._request_counter == 0
        assert middleware._blocked_ips == {}
        assert middleware._blocked_clients == {}
        assert middleware._rate_limits == {}

    def test_process_request_basic(self, middleware):
        """Test basic request processing."""
        context = asyncio.run(
            middleware.process_request(
                request_data={"test": "data"},
                client_context={
                    "ip_address": "192.168.1.1",
                    "user_agent": "Mozilla/5.0",
                    "client_id": "test_client",
                },
            )
        )

        assert context.request_id is not None
        assert context.ip_address == "192.168.1.1"
        assert context.user_agent == "Mozilla/5.0"
        assert context.client_id == "test_client"
        assert middleware._request_counter == 1

    def test_process_request_no_client_context(self, middleware):
        """Test request processing without client context."""
        context = asyncio.run(
            middleware.process_request(
                request_data={"test": "data"},
                client_context=None,
            )
        )

        assert context.ip_address is None
        assert context.user_agent is None
        assert context.client_id is None

    def test_validate_ip_restrictions_no_restrictions(self, middleware):
        """Test IP validation when no restrictions set."""
        context = SecurityContext(
            request_id="req_001",
            timestamp=datetime.now(UTC),
            ip_address="192.168.1.1",
        )

        # Should not raise
        asyncio.run(middleware._validate_ip_restrictions(context))

    def test_validate_ip_restrictions_allowed_ip(self, middleware):
        """Test IP validation with allowed IP."""
        # Set allowed IPs as comma-separated string
        middleware.settings.allowed_ip_addresses = "192.168.1.0/24"

        context = SecurityContext(
            request_id="req_002",
            timestamp=datetime.now(UTC),
            ip_address="192.168.1.100",
        )

        # Should not raise for IP in allowed range
        asyncio.run(middleware._validate_ip_restrictions(context))

    def test_validate_ip_restrictions_blocked_ip(self, middleware):
        """Test IP validation with blocked IP."""
        # Set allowed IPs as comma-separated string
        middleware.settings.allowed_ip_addresses = "10.0.0.0/24"

        context = SecurityContext(
            request_id="req_003",
            timestamp=datetime.now(UTC),
            ip_address="192.168.1.1",
        )

        # Should raise SecurityError
        with pytest.raises(SecurityError, match="IP address not allowed"):
            asyncio.run(middleware._validate_ip_restrictions(context))

        assert "ip_not_allowed" in context.security_flags

    def test_check_blocked_entities_not_blocked(self, middleware):
        """Test blocked entity check when not blocked."""
        context = SecurityContext(
            request_id="req_004",
            timestamp=datetime.now(UTC),
            ip_address="10.0.0.1",
        )

        # Should not raise
        asyncio.run(middleware._check_blocked_entities(context))

    def test_check_blocked_entities_blocked_ip(self, middleware):
        """Test blocked entity check with blocked IP."""
        ip_address = "10.0.0.2"

        # Block IP
        middleware._blocked_ips[ip_address] = datetime.now(UTC) + timedelta(
            minutes=5
        )

        context = SecurityContext(
            request_id="req_005",
            timestamp=datetime.now(UTC),
            ip_address=ip_address,
        )

        # Should raise SecurityError
        with pytest.raises(SecurityError, match="IP blocked"):
            asyncio.run(middleware._check_blocked_entities(context))

    def test_check_blocked_entities_expired_block(self, middleware):
        """Test blocked entity check with expired block."""
        ip_address = "10.0.0.3"

        # Block IP in the past
        middleware._blocked_ips[ip_address] = datetime.now(UTC) - timedelta(
            minutes=5
        )

        context = SecurityContext(
            request_id="req_006",
            timestamp=datetime.now(UTC),
            ip_address=ip_address,
        )

        # Should not raise (block expired and removed)
        asyncio.run(middleware._check_blocked_entities(context))
        assert ip_address not in middleware._blocked_ips

    def test_enforce_rate_limits_disabled(self, middleware):
        """Test rate limiting when disabled."""
        middleware.settings.enable_rate_limiting = False

        context = SecurityContext(
            request_id="req_007",
            timestamp=datetime.now(UTC),
            ip_address="10.0.0.4",
        )

        # Should not raise
        asyncio.run(middleware._enforce_rate_limits(context))

    def test_enforce_rate_limits_under_limit(self, middleware):
        """Test rate limiting under the limit."""
        context = SecurityContext(
            request_id="req_008",
            timestamp=datetime.now(UTC),
            ip_address="10.0.0.5",
        )

        # Should not raise (under limit)
        asyncio.run(middleware._enforce_rate_limits(context))

    def test_enforce_rate_limits_exceeded(self, middleware):
        """Test rate limiting when limit exceeded."""
        ip_address = "10.0.0.6"

        # Add requests up to the limit
        middleware._rate_limits[ip_address] = [
            datetime.now(UTC) - timedelta(seconds=i) for i in range(10)
        ]

        context = SecurityContext(
            request_id="req_009",
            timestamp=datetime.now(UTC),
            ip_address=ip_address,
        )

        # Should raise SecurityError
        with pytest.raises(SecurityError, match="Rate limit exceeded"):
            asyncio.run(middleware._enforce_rate_limits(context))

    def test_enforce_rate_limits_auto_block(self, middleware):
        """Test automatic blocking for severe rate limit violations."""
        ip_address = "10.0.0.7"

        # Add requests well over the limit (> 2x limit)
        middleware._rate_limits[ip_address] = [
            datetime.now(UTC) - timedelta(seconds=i) for i in range(25)
        ]

        context = SecurityContext(
            request_id="req_010",
            timestamp=datetime.now(UTC),
            ip_address=ip_address,
        )

        # Should raise SecurityError and block IP
        with pytest.raises(SecurityError, match="Rate limit exceeded"):
            asyncio.run(middleware._enforce_rate_limits(context))

        # Verify IP was temporarily blocked
        assert ip_address in middleware._blocked_ips

    def test_get_security_status(self, middleware):
        """Test getting security status."""
        # Add some test data
        middleware._request_counter = 100
        middleware._blocked_ips["10.0.0.1"] = datetime.now(UTC) + timedelta(minutes=5)
        middleware._blocked_clients["client1"] = datetime.now(UTC) + timedelta(minutes=5)
        middleware._rate_limits["10.0.0.2"] = [datetime.now(UTC)]

        status = middleware.get_security_status()

        assert status["middleware_active"] is True
        assert status["request_count"] == 100
        assert status["active_ip_blocks"] == 1
        assert status["active_client_blocks"] == 1
        assert status["active_rate_limits"] == 1
        assert "security_features" in status

    def test_handle_high_risk_request_no_incident_response(self, middleware):
        """Test high-risk request handling without incident response."""
        middleware.settings.enable_automatic_incident_response = False

        context = SecurityContext(
            request_id="req_011",
            timestamp=datetime.now(UTC),
            ip_address="10.0.0.8",
            risk_score=85,
            security_flags={"threat1", "threat2"},
        )

        # Should not raise (incident response disabled)
        asyncio.run(middleware._handle_high_risk_request(context))

    def test_handle_high_risk_request_with_incident_response(self, middleware):
        """Test high-risk request handling with incident response."""
        middleware.settings.enable_automatic_incident_response = True

        context = SecurityContext(
            request_id="req_012",
            timestamp=datetime.now(UTC),
            ip_address="10.0.0.9",
            risk_score=85,
            security_flags={"threat1"},
        )

        # Should not raise for risk_score 85 (< 90)
        asyncio.run(middleware._handle_high_risk_request(context))

    def test_handle_very_high_risk_request(self, middleware):
        """Test very high-risk request handling (auto-block)."""
        middleware.settings.enable_automatic_incident_response = True

        context = SecurityContext(
            request_id="req_013",
            timestamp=datetime.now(UTC),
            ip_address="10.0.0.10",
            client_id="test_client",
            risk_score=95,
            security_flags={"critical_threat"},
        )

        # Should raise SecurityError and block
        with pytest.raises(SecurityError, match="security policy violation"):
            asyncio.run(middleware._handle_high_risk_request(context))

        # Verify blocking occurred
        assert context.ip_address in middleware._blocked_ips
        assert context.client_id in middleware._blocked_clients


class TestCreateSecurityMiddleware:
    """Test create_security_middleware factory function."""

    def test_create_security_middleware(self):
        """Test security middleware factory function."""
        settings = SecuritySettings(
            enable_rate_limiting=True,
            enable_anomaly_detection=False,
        )

        middleware = create_security_middleware(settings)

        assert isinstance(middleware, SecurityMiddleware)
        assert middleware.settings == settings
