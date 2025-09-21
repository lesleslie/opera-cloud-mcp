"""
OPERA Cloud MCP Authentication Module.

This module provides comprehensive authentication and security services
for the OPERA Cloud MCP server, including OAuth2 authentication,
security monitoring, audit logging, and threat detection.
"""

from pathlib import Path
from typing import Any, cast

from opera_cloud_mcp.auth.audit_logger import AuditLogger, audit_logger
from opera_cloud_mcp.auth.oauth_handler import OAuthHandler, Token, TokenCache
from opera_cloud_mcp.auth.secure_oauth_handler import SecureOAuthHandler, SecureToken
from opera_cloud_mcp.auth.security_enhancements import (
    RateLimiter,
    SecureTokenCache,
    SecurityMonitor,
    TokenBinding,
    security_monitor,
)
from opera_cloud_mcp.auth.security_middleware import (
    SecurityMiddleware,
    create_security_middleware,
)
from opera_cloud_mcp.config.security_settings import SecuritySettings
from opera_cloud_mcp.config.settings import Settings


def create_enhanced_oauth_security(
    client_id: str,
    client_secret: str,
    token_url: str,
    enable_security_monitoring: bool = True,
    enable_rate_limiting: bool = True,
    enable_token_binding: bool = True,
    enable_audit_logging: bool = True,
    cache_dir: Path | None = None,
    master_key: bytes | None = None,
    security_settings: SecuritySettings | None = None,
) -> tuple[SecureOAuthHandler, SecurityMiddleware, AuditLogger]:
    """
    Create comprehensive OAuth2 security components with enhanced features.

    This function integrates all enhanced security components including:
    - SecureOAuthHandler with token binding and monitoring
    - Security middleware with threat detection
    - Audit logging with tamper-resistant storage
    - Rate limiting and abuse detection

    Args:
        client_id: OAuth client ID
        client_secret: OAuth client secret
        token_url: OAuth token endpoint URL
        enable_security_monitoring: Enable comprehensive security monitoring
        enable_rate_limiting: Enable rate limiting and abuse detection
        enable_token_binding: Enable token binding for enhanced security
        enable_audit_logging: Enable tamper-resistant audit logging
        cache_dir: Custom cache directory for secure token storage
        master_key: Master encryption key for token security
        security_settings: Custom security settings (optional)

    Returns:
        Tuple of (SecureOAuthHandler, SecurityMiddleware, AuditLogger)
    """
    # Use default security settings if not provided
    if security_settings is None:
        # Create a minimal security settings instance with required fields
        security_settings = SecuritySettings(
            enable_security_monitoring=True,
            enable_audit_logging=True,
            enable_rate_limiting=True,
            enable_token_binding=True,
            auth_rate_limit_requests=10,
            auth_rate_limit_window_minutes=5,
            max_failed_attempts=5,
            client_lockout_duration_minutes=30,
            security_event_retention_days=90,
            token_max_lifetime_hours=24,
            token_refresh_threshold_minutes=30,
            token_binding_lifetime_hours=24,
            credential_rotation_interval_days=90,
            enable_credential_validation=True,
            allowed_ip_addresses=None,
            require_https=True,
            min_tls_version="TLSv1.2",
            audit_db_path=None,
            audit_db_encryption_key=None,
            enable_audit_db_compression=True,
            audit_db_max_size_mb=100,
            enable_security_headers=True,
            content_security_policy="default-src 'self'",
            enable_anomaly_detection=True,
            anomaly_detection_sensitivity=0.7,
            enable_ip_reputation_check=True,
            enable_gdpr_mode=False,
            data_retention_policy_days=365,
            enable_pii_anonymization=True,
            enable_automatic_incident_response=True,
            security_notification_webhook=None,
            security_notification_email=None,
            security_testing_mode=False,
            enable_security_debug_logs=False,
        )

    # Create SecureOAuthHandler with enhanced security features
    secure_oauth_handler = SecureOAuthHandler(
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
        timeout=30,  # Default timeout
        max_retries=3,  # Default retries
        retry_backoff=1.0,  # Default backoff
        enable_persistent_cache=True,
        cache_dir=cache_dir,
        enable_security_monitoring=enable_security_monitoring,
        enable_rate_limiting=enable_rate_limiting,
        enable_token_binding=enable_token_binding,
        master_key=master_key,
    )

    # Create audit logger if enabled
    audit_logger_instance = None
    if enable_audit_logging:
        audit_db_path = cache_dir / "audit" / "audit.db" if cache_dir else None
        audit_encryption_key = master_key
        audit_logger_instance = AuditLogger(audit_db_path, audit_encryption_key)
    else:
        audit_logger_instance = audit_logger  # Use global instance

    # Create security middleware
    security_middleware = SecurityMiddleware(security_settings)

    return secure_oauth_handler, security_middleware, audit_logger_instance


def create_oauth_handler(
    settings: Settings,
    enable_security_features: bool = True,
    master_key: bytes | None = None,
    allowed_ips: set[str] | None = None,
) -> OAuthHandler | SecureOAuthHandler:
    """
    Create OAuth handler with appropriate security level.

    Args:
        settings: Application settings instance
        enable_security_features: Whether to use secure OAuth handler
        master_key: Master encryption key for token storage
        allowed_ips: Set of allowed IP addresses

    Returns:
        OAuth handler instance (secure or basic)
    """
    from opera_cloud_mcp.utils.exceptions import AuthenticationError

    # Validate required settings
    missing_settings = settings.validate_required_settings()
    if missing_settings:
        raise AuthenticationError(
            f"Missing required settings: {', '.join(missing_settings)}"
        )

    # Get OAuth configuration from settings
    oauth_config = settings.get_oauth_handler_config()

    if enable_security_features:
        # Use secure OAuth handler with enhanced features
        return SecureOAuthHandler(
            client_id=oauth_config["client_id"],
            client_secret=oauth_config["client_secret"],
            token_url=oauth_config["token_url"],
            timeout=oauth_config["timeout"],
            max_retries=oauth_config["max_retries"],
            retry_backoff=oauth_config["retry_backoff"],
            enable_persistent_cache=oauth_config["enable_persistent_cache"],
            cache_dir=oauth_config["cache_dir"],
            enable_security_monitoring=True,
            enable_rate_limiting=True,
            enable_token_binding=True,
            master_key=master_key,
            allowed_ips=allowed_ips,
        )
    # Use basic OAuth handler
    return OAuthHandler(**oauth_config)


def create_security_components(
    security_settings: SecuritySettings | None = None,
    audit_db_path: Path | None = None,
    audit_encryption_key: bytes | None = None,
) -> tuple[SecurityMiddleware, AuditLogger, SecurityMonitor]:
    """
    Create integrated security components.

    Args:
        security_settings: Security configuration
        audit_db_path: Custom audit database path
        audit_encryption_key: Custom audit encryption key

    Returns:
        Tuple of (security_middleware, audit_logger, security_monitor)
    """
    # Use default security settings if none provided
    if security_settings is None:
        # Create a minimal security settings instance with required fields
        security_settings = SecuritySettings(
            enable_security_monitoring=True,
            enable_audit_logging=True,
            enable_rate_limiting=True,
            enable_token_binding=True,
            auth_rate_limit_requests=10,
            auth_rate_limit_window_minutes=5,
            max_failed_attempts=5,
            client_lockout_duration_minutes=30,
            security_event_retention_days=90,
            token_max_lifetime_hours=24,
            token_refresh_threshold_minutes=30,
            token_binding_lifetime_hours=24,
            credential_rotation_interval_days=90,
            enable_credential_validation=True,
            allowed_ip_addresses=None,
            require_https=True,
            min_tls_version="TLSv1.2",
            audit_db_path=None,
            audit_db_encryption_key=None,
            enable_audit_db_compression=True,
            audit_db_max_size_mb=100,
            enable_security_headers=True,
            content_security_policy="default-src 'self'",
            enable_anomaly_detection=True,
            anomaly_detection_sensitivity=0.7,
            enable_ip_reputation_check=True,
            enable_gdpr_mode=False,
            data_retention_policy_days=365,
            enable_pii_anonymization=True,
            enable_automatic_incident_response=True,
            security_notification_webhook=None,
            security_notification_email=None,
            security_testing_mode=False,
            enable_security_debug_logs=False,
        )

    # Create security middleware
    middleware = create_security_middleware(security_settings)

    # Create audit logger
    if audit_db_path or audit_encryption_key:
        audit_logger_instance = AuditLogger(audit_db_path, audit_encryption_key)
    else:
        audit_logger_instance = audit_logger  # Use global instance

    # Return components
    return middleware, audit_logger_instance, security_monitor


def _validate_main_settings(
    settings: Settings, validation_result: dict[str, Any]
) -> None:
    """Validate main settings."""
    missing_settings = settings.validate_required_settings()
    if missing_settings:
        cast("list[str]", validation_result["errors"]).extend(
            [f"Missing required setting: {setting}" for setting in missing_settings]
        )
        validation_result["valid"] = False


def _validate_security_settings(
    security_settings: SecuritySettings | None, validation_result: dict[str, Any]
) -> None:
    """Validate security settings if provided."""
    if security_settings:
        security_warnings = security_settings.validate_security_configuration()
        cast("list[str]", validation_result["warnings"]).extend(security_warnings)

        # Check for production readiness
        if hasattr(security_settings, "validate_production_readiness"):
            production_errors = security_settings.validate_production_readiness()
            if production_errors:
                cast("list[str]", validation_result["errors"]).extend(production_errors)
                validation_result["valid"] = False


def _add_security_recommendations(
    security_settings: SecuritySettings | None, validation_result: dict[str, Any]
) -> None:
    """Add security recommendations."""
    if not security_settings or not security_settings.enable_security_monitoring:
        cast("list[str]", validation_result["recommendations"]).append(
            "Enable security monitoring for production deployments"
        )

    if not security_settings or not security_settings.enable_audit_logging:
        cast("list[str]", validation_result["recommendations"]).append(
            "Enable audit logging for compliance and security analysis"
        )


def _validate_production_settings(
    settings: Settings,
    security_settings: SecuritySettings | None,
    validation_result: dict[str, Any],
) -> None:
    """Validate production-specific settings."""
    if settings.opera_environment == "production":
        if not security_settings or security_settings.security_testing_mode:
            cast("list[str]", validation_result["errors"]).append(
                "Security testing mode must be disabled in production"
            )
            validation_result["valid"] = False

        if not security_settings or not security_settings.require_https:
            cast("list[str]", validation_result["errors"]).append(
                "HTTPS must be required in production"
            )
            validation_result["valid"] = False


def validate_security_configuration(
    settings: Settings, security_settings: SecuritySettings | None = None
) -> dict[str, Any]:
    """
    Validate complete security configuration.

    Args:
        settings: Main application settings
        security_settings: Security configuration

    Returns:
        Validation results dictionary
    """
    # Initialize validation result with proper type annotations
    validation_result: dict[str, bool | list[str]] = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "recommendations": [],
    }

    # Validate main settings
    _validate_main_settings(settings, validation_result)

    # Validate security settings if provided
    _validate_security_settings(security_settings, validation_result)

    # Add recommendations based on configuration
    _add_security_recommendations(security_settings, validation_result)

    # Check for production-specific settings
    _validate_production_settings(settings, security_settings, validation_result)

    return validation_result


# Export public interface
__all__ = [
    # OAuth handlers
    "OAuthHandler",
    "SecureOAuthHandler",
    "Token",
    "SecureToken",
    "TokenCache",
    "SecureTokenCache",
    "TokenBinding",
    # Security components
    "SecurityMiddleware",
    "SecurityMonitor",
    "AuditLogger",
    "SecuritySettings",
    "RateLimiter",
    # Factory functions
    "create_oauth_handler",
    "create_enhanced_oauth_security",
    "create_security_components",
    "create_security_middleware",
    "validate_security_configuration",
    # Global instances
    "audit_logger",
    "security_monitor",
]
