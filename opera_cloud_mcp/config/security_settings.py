"""
Production-grade security configuration for OPERA Cloud MCP server.

This module extends the base settings with comprehensive security configuration
including credential management, audit logging, and security monitoring.
"""

import base64
import ipaddress
import secrets
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    """
    Security-focused configuration settings for OPERA Cloud MCP server.

    Provides enterprise-grade security configuration with proper validation
    and secure defaults for production environments.
    """

    # Enhanced Authentication Security
    enable_security_monitoring: bool = Field(
        True,
        description="Enable comprehensive security monitoring and threat detection",
    )
    enable_audit_logging: bool = Field(
        True,
        description="Enable tamper-resistant audit logging for all security events",
    )
    enable_rate_limiting: bool = Field(
        True,
        description="Enable rate limiting to prevent abuse and brute force attacks",
    )
    enable_token_binding: bool = Field(
        True,
        description="Enable token binding for enhanced security against token theft",
    )

    # Rate Limiting Configuration
    auth_rate_limit_requests: int = Field(
        10, description="Maximum authentication requests per time window", ge=1, le=100
    )
    auth_rate_limit_window_minutes: int = Field(
        5, description="Rate limiting time window in minutes", ge=1, le=60
    )

    # Security Monitoring Configuration
    max_failed_attempts: int = Field(
        5,
        description="Maximum failed authentication attempts before blocking",
        ge=1,
        le=20,
    )
    client_lockout_duration_minutes: int = Field(
        15, description="Client lockout duration after max failures", ge=1, le=1440
    )
    security_event_retention_days: int = Field(
        90, description="Security event retention period in days", ge=1, le=365
    )

    # Token Security Configuration
    token_max_lifetime_hours: int = Field(
        24, description="Maximum token lifetime in hours", ge=1, le=168
    )
    token_refresh_threshold_minutes: int = Field(
        5, description="Token refresh threshold in minutes before expiry", ge=1, le=60
    )
    token_binding_lifetime_hours: int = Field(
        24, description="Token binding lifetime in hours", ge=1, le=48
    )

    # Credential Management
    credential_rotation_interval_days: int = Field(
        90, description="Recommended credential rotation interval", ge=1, le=365
    )
    enable_credential_validation: bool = Field(
        True, description="Enable credential validation on rotation"
    )

    # Network Security
    allowed_ip_addresses: str | None = Field(
        None, description="Comma-separated list of allowed IP addresses (CIDR notation)"
    )
    require_https: bool = Field(
        True, description="Require HTTPS for all communications"
    )
    min_tls_version: str = Field(
        "1.2", description="Minimum TLS version required", pattern=r"1\.[23]"
    )

    # Audit Database Configuration
    audit_db_path: str | None = Field(
        None, description="Custom path for audit database"
    )
    audit_db_encryption_key: str | None = Field(
        None, description="Base64-encoded encryption key for audit database"
    )
    enable_audit_db_compression: bool = Field(
        True, description="Enable audit database compression"
    )
    audit_db_max_size_mb: int = Field(
        1024, description="Maximum audit database size in MB", ge=100, le=10240
    )

    # Security Headers and Hardening
    enable_security_headers: bool = Field(
        True, description="Enable security headers in HTTP responses"
    )
    content_security_policy: str | None = Field(
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        + "style-src 'self' 'unsafe-inline'",
        description="Content Security Policy header value",
    )

    # Advanced Threat Detection
    enable_anomaly_detection: bool = Field(
        True, description="Enable behavioral anomaly detection"
    )
    anomaly_detection_sensitivity: float = Field(
        0.7, description="Anomaly detection sensitivity (0.0-1.0)", ge=0.0, le=1.0
    )
    enable_ip_reputation_check: bool = Field(
        False, description="Enable IP reputation checking (requires external service)"
    )

    # Compliance and Privacy
    enable_gdpr_mode: bool = Field(
        False, description="Enable GDPR compliance mode (enhanced privacy protection)"
    )
    data_retention_policy_days: int = Field(
        365,
        description="Data retention policy in days",
        ge=30,
        le=2555,  # 7 years max
    )
    enable_pii_anonymization: bool = Field(
        True, description="Enable automatic PII anonymization in logs"
    )

    # Incident Response
    enable_automatic_incident_response: bool = Field(
        True, description="Enable automatic incident response for critical events"
    )
    security_notification_webhook: str | None = Field(
        None, description="Webhook URL for security notifications"
    )
    security_notification_email: str | None = Field(
        None, description="Email address for security notifications"
    )

    # Development and Testing
    security_testing_mode: bool = Field(
        False, description="Enable security testing mode (reduces some restrictions)"
    )
    enable_security_debug_logs: bool = Field(
        False, description="Enable detailed security debug logging"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="OPERA_SECURITY_",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("allowed_ip_addresses")
    @classmethod
    def validate_ip_addresses(cls, v):
        """Validate IP address list format."""
        if not v:
            return v

        try:
            for ip_str in v.split(","):
                ip_str = ip_str.strip()
                if ip_str:  # Skip empty strings
                    # This will raise ValueError if invalid
                    ipaddress.ip_network(ip_str, strict=False)
            return v
        except ValueError as e:
            raise ValueError(f"Invalid IP address format: {e}") from None

    @field_validator("audit_db_encryption_key")
    @classmethod
    def validate_encryption_key(cls, v):
        """Validate encryption key format."""
        if not v:
            return v

        try:
            # Validate base64 format
            base64.b64decode(v, validate=True)
            # Check minimum length (32 bytes = 256 bits when base64 decoded)
            if len(base64.b64decode(v, validate=True)) < 32:
                raise ValueError("Encryption key must be at least 256 bits")
            return v
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}") from None

    def get_allowed_ips(self) -> set[str]:
        """Parse and return allowed IP addresses as a set."""
        if not self.allowed_ip_addresses:
            return set()

        return {addr.strip() for addr in self.allowed_ip_addresses.split(",")}

    def get_audit_db_path(self) -> Path:
        """Get audit database path."""
        if self.audit_db_path:
            return Path(self.audit_db_path)
        return Path.home() / ".opera_cloud_mcp" / "audit" / "audit.db"

    def get_audit_encryption_key(self) -> bytes | None:
        """Get audit database encryption key."""
        if not self.audit_db_encryption_key:
            return None

        import base64

        return base64.b64decode(self.audit_db_encryption_key)

    def get_security_headers(self) -> dict[str, str]:
        """Get security headers for HTTP responses."""
        if not self.enable_security_headers:
            return {}

        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        if self.content_security_policy:
            headers["Content-Security-Policy"] = self.content_security_policy

        return headers

    def _check_production_readiness(self) -> list[str]:
        """Check for production readiness issues."""
        warnings = []

        if not self.enable_security_monitoring:
            warnings.append(
                "Security monitoring is disabled - not recommended for production"
            )

        if not self.enable_audit_logging:
            warnings.append("Audit logging is disabled - required for compliance")

        if not self.enable_rate_limiting:
            warnings.append(
                "Rate limiting is disabled - vulnerable to brute force attacks"
            )

        if self.security_testing_mode:
            warnings.append("Security testing mode enabled - disable in production")

        if not self.require_https:
            warnings.append(
                "HTTPS not required - credentials may be transmitted insecurely"
            )

        return warnings

    def _check_weak_configurations(self) -> list[str]:
        """Check for weak configuration issues."""
        warnings = []

        if self.max_failed_attempts > 10:
            warnings.append(
                f"High failure threshold ({self.max_failed_attempts}) - "
                + "consider lowering"
            )

        if self.token_max_lifetime_hours > 48:
            warnings.append(
                f"Long token lifetime ({self.token_max_lifetime_hours}h) - "
                + "security risk"
            )

        if self.credential_rotation_interval_days > 180:
            warnings.append(
                "Long credential rotation interval - consider more frequent rotation"
            )

        return warnings

    def _check_missing_security_features(self) -> list[str]:
        """Check for missing security features."""
        warnings = []

        if not self.allowed_ip_addresses and not self.security_testing_mode:
            warnings.append("No IP restrictions configured - consider limiting access")

        if (
            not self.security_notification_webhook
            and not self.security_notification_email
        ):
            warnings.append(
                "No security notifications configured - incidents may go unnoticed"
            )

        return warnings

    def validate_security_configuration(self) -> list[str]:
        """Validate security configuration and return warnings."""
        # Check for production readiness
        production_warnings = self._check_production_readiness()

        # Check for weak configurations
        weak_config_warnings = self._check_weak_configurations()

        # Check for missing security features
        missing_feature_warnings = self._check_missing_security_features()

        # Combine all warnings
        return production_warnings + weak_config_warnings + missing_feature_warnings

    def generate_secure_defaults(self) -> dict[str, str]:
        """Generate secure default configuration for .env file."""
        # Generate secure random values
        audit_key = base64.b64encode(secrets.token_bytes(32)).decode()

        return {
            "OPERA_SECURITY_ENABLE_SECURITY_MONITORING": "true",
            "OPERA_SECURITY_ENABLE_AUDIT_LOGGING": "true",
            "OPERA_SECURITY_ENABLE_RATE_LIMITING": "true",
            "OPERA_SECURITY_ENABLE_TOKEN_BINDING": "true",
            "OPERA_SECURITY_AUTH_RATE_LIMIT_REQUESTS": "10",
            "OPERA_SECURITY_AUTH_RATE_LIMIT_WINDOW_MINUTES": "5",
            "OPERA_SECURITY_MAX_FAILED_ATTEMPTS": "5",
            "OPERA_SECURITY_CLIENT_LOCKOUT_DURATION_MINUTES": "15",
            "OPERA_SECURITY_TOKEN_MAX_LIFETIME_HOURS": "24",
            "OPERA_SECURITY_TOKEN_REFRESH_THRESHOLD_MINUTES": "5",
            "OPERA_SECURITY_REQUIRE_HTTPS": "true",
            "OPERA_SECURITY_MIN_TLS_VERSION": "1.2",
            "OPERA_SECURITY_AUDIT_DB_ENCRYPTION_KEY": audit_key,
            "OPERA_SECURITY_ENABLE_SECURITY_HEADERS": "true",
            "OPERA_SECURITY_ENABLE_ANOMALY_DETECTION": "true",
            "OPERA_SECURITY_ANOMALY_DETECTION_SENSITIVITY": "0.7",
            "OPERA_SECURITY_ENABLE_PII_ANONYMIZATION": "true",
            "OPERA_SECURITY_ENABLE_AUTOMATIC_INCIDENT_RESPONSE": "true",
            "OPERA_SECURITY_SECURITY_TESTING_MODE": "false",
        }


class ProductionSecuritySettings(SecuritySettings):
    """Production-hardened security settings with strict defaults."""

    # Override defaults for production
    enable_security_monitoring: bool = True
    enable_audit_logging: bool = True
    enable_rate_limiting: bool = True
    enable_token_binding: bool = True
    require_https: bool = True
    enable_security_headers: bool = True
    enable_anomaly_detection: bool = True
    enable_automatic_incident_response: bool = True
    security_testing_mode: bool = False
    enable_security_debug_logs: bool = False

    # Stricter limits for production
    max_failed_attempts: int = 3
    client_lockout_duration_minutes: int = 30
    token_max_lifetime_hours: int = 12
    auth_rate_limit_requests: int = 5

    def _check_critical_security_requirements(self) -> list[str]:
        """Check critical security requirements."""
        errors = []

        if not self.enable_security_monitoring:
            errors.append("Security monitoring must be enabled in production")

        if not self.enable_audit_logging:
            errors.append("Audit logging must be enabled in production")

        if not self.require_https:
            errors.append("HTTPS must be required in production")

        if self.security_testing_mode:
            errors.append("Security testing mode must be disabled in production")

        if self.enable_security_debug_logs:
            errors.append("Security debug logs should be disabled in production")

        return errors

    def _check_security_configuration_requirements(self) -> list[str]:
        """Check security configuration requirements."""
        errors = []

        if not self.allowed_ip_addresses:
            errors.append("IP address restrictions should be configured for production")

        if not self.audit_db_encryption_key:
            errors.append("Audit database encryption key must be configured")

        if not (self.security_notification_webhook or self.security_notification_email):
            errors.append(
                "Security notifications must be configured for incident response"
            )

        return errors

    def _check_weak_configurations(self) -> list[str]:
        """Check for weak configurations."""
        errors = []

        if self.max_failed_attempts > 5:
            errors.append("Maximum failed attempts should be <= 5 in production")

        if self.token_max_lifetime_hours > 24:
            errors.append("Token lifetime should be <= 24 hours in production")

        return errors

    def validate_production_readiness(self) -> list[str]:
        """Validate configuration for production deployment."""
        # Critical security requirements
        critical_errors = self._check_critical_security_requirements()

        # Security configuration requirements
        config_errors = self._check_security_configuration_requirements()

        # Check for weak configurations
        weak_config_errors = self._check_weak_configurations()

        # Combine all errors
        return critical_errors + config_errors + weak_config_errors
