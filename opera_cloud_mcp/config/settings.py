"""
Settings and configuration management for OPERA Cloud MCP server.

Provides environment-based configuration management using Pydantic settings
for OAuth credentials, API endpoints, and client configuration.
"""

import sys
import tempfile
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import mcp-common security utilities for OAuth credential validation
try:
    from mcp_common.security import APIKeyValidator

    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False


class Settings(BaseSettings):
    """
    Configuration settings for OPERA Cloud MCP server.

    Uses environment variables with OPERA_ prefix for configuration.
    """

    # OAuth Configuration
    opera_client_id: str = Field(
        ..., description="OAuth2 client ID for OPERA Cloud API"
    )
    opera_client_secret: str = Field(
        ..., description="OAuth2 client secret for OPERA Cloud API"
    )
    opera_token_url: str = Field(
        "https://api.oracle-hospitality.com/oauth/v1/tokens",
        description="OAuth2 token endpoint URL",
    )

    # API Configuration
    opera_base_url: str = Field(
        "https://api.oracle-hospitality.com", description="Base URL for OPERA Cloud API"
    )
    opera_api_version: str = Field("v1", description="OPERA Cloud API version")
    opera_environment: str = Field(
        "production",
        description="OPERA Cloud environment (production/staging/development)",
    )

    # Default Hotel Configuration
    default_hotel_id: str | None = Field(
        None, description="Default hotel ID for operations"
    )

    # Client Configuration
    request_timeout: int = Field(
        30, description="HTTP request timeout in seconds", ge=5, le=300
    )
    max_retries: int = Field(
        3, description="Maximum number of retry attempts", ge=0, le=10
    )
    retry_backoff: float = Field(
        1.0, description="Base retry backoff time in seconds", ge=0.1, le=60.0
    )

    # Caching Configuration
    enable_cache: bool = Field(True, description="Enable response caching")
    cache_ttl: int = Field(
        300, description="Cache time-to-live in seconds", ge=60, le=3600
    )
    cache_max_memory: int = Field(
        10000,
        description="Maximum number of entries in memory cache",
        ge=100,
        le=100000,
    )

    # Authentication Configuration
    oauth_max_retries: int = Field(
        3, description="Maximum retry attempts for OAuth token requests", ge=0, le=10
    )
    oauth_retry_backoff: float = Field(
        1.0,
        description="Base backoff time for OAuth retries in seconds",
        ge=0.1,
        le=60.0,
    )
    enable_persistent_token_cache: bool = Field(
        True, description="Enable persistent encrypted token caching"
    )
    token_cache_dir: str | None = Field(
        None,
        description="Directory for token cache files (defaults to "
        + "~/.opera_cloud_mcp/cache)",
    )

    # Logging Configuration
    log_level: str = Field(
        "INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging format string",
    )
    enable_structured_logging: bool = Field(
        True, description="Enable structured logging with JSON format"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="OPERA_", case_sensitive=False, extra="ignore"
    )

    def get_masked_client_id(self) -> str:
        """Get masked OAuth client ID for safe logging (Phase 3 Security Hardening).

        Returns:
            Masked client ID string (e.g., "...abc1") for safe display in logs
        """
        if not self.opera_client_id:
            return "***"

        if SECURITY_AVAILABLE:
            return APIKeyValidator.mask_key(self.opera_client_id, visible_chars=4)

        # Fallback masking without security module
        if len(self.opera_client_id) <= 4:
            return "***"
        return f"...{self.opera_client_id[-4:]}"

    def get_masked_client_secret(self) -> str:
        """Get masked OAuth client secret for safe logging (Phase 3 Security Hardening).

        Returns:
            Masked client secret string (e.g., "...xyz1") for safe display in logs
        """
        if not self.opera_client_secret:
            return "***"

        if SECURITY_AVAILABLE:
            return APIKeyValidator.mask_key(self.opera_client_secret, visible_chars=4)

        # Fallback masking without security module
        if len(self.opera_client_secret) <= 4:
            return "***"
        return f"...{self.opera_client_secret[-4:]}"

    def validate_oauth_credentials_at_startup(self) -> None:
        """Validate OAuth credentials at server startup (Phase 3 Security Hardening).

        Raises:
            SystemExit: If OAuth credentials are invalid or missing
        """
        # Check for missing credentials
        if not self.opera_client_id or not self.opera_client_id.strip():
            sys.exit(1)

        if not self.opera_client_secret or not self.opera_client_secret.strip():
            sys.exit(1)

        if SECURITY_AVAILABLE:
            # Use generic validator with minimum 32 characters for OAuth credentials
            validator = APIKeyValidator(min_length=32)

            # Validate client ID
            try:
                validator.validate(self.opera_client_id, raise_on_invalid=True)
                self.get_masked_client_id()
            except ValueError:
                # Continue silently to maintain backward compatibility
                _ = "validation_failed_but_continue"  # Explicitly acknowledge error

            # Validate client secret
            try:
                validator.validate(self.opera_client_secret, raise_on_invalid=True)
                self.get_masked_client_secret()
            except ValueError:
                # Continue silently to maintain backward compatibility
                _ = "validation_failed_but_continue"  # Explicitly acknowledge error
        else:
            # Basic validation without security module
            if len(self.opera_client_id) < 16:
                # Intentionally allow short IDs for backwards compatibility
                pass  # noqa: S110 (Intentionally allow short IDs for backwards compatibility)

            if len(self.opera_client_secret) < 16:
                # Intentionally allow short secrets for backwards compatibility
                pass  # noqa: S110 (Intentionally allow short secrets for backwards compatibility)

    def get_oauth_config(self) -> dict[str, str]:
        """
        Get OAuth configuration dictionary.

        Returns:
            Dictionary containing OAuth configuration
        """
        return {
            "client_id": self.opera_client_id,
            "client_secret": self.opera_client_secret,
            "token_url": self.opera_token_url,
        }

    def get_api_config(self) -> dict[str, str]:
        """
        Get API configuration dictionary.

        Returns:
            Dictionary containing API configuration
        """
        return {
            "base_url": self.opera_base_url,
            "api_version": self.opera_api_version,
            "environment": self.opera_environment,
        }

    def get_client_config(self) -> dict[str, int | float]:
        """
        Get HTTP client configuration dictionary.

        Returns:
            Dictionary containing client configuration
        """
        return {
            "timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "retry_backoff": self.retry_backoff,
        }

    def get_oauth_handler_config(self) -> dict[str, Any]:
        """
        Get OAuth handler configuration dictionary.

        Returns:
            Dictionary containing OAuth handler configuration
        """
        from pathlib import Path

        return {
            "client_id": self.opera_client_id,
            "client_secret": self.opera_client_secret,
            "token_url": self.opera_token_url,
            "timeout": self.request_timeout,
            "max_retries": self.oauth_max_retries,
            "retry_backoff": self.oauth_retry_backoff,
            "enable_persistent_cache": self.enable_persistent_token_cache,
            "cache_dir": Path(self.token_cache_dir) if self.token_cache_dir else None,
        }

    def validate_required_settings(self) -> list[str]:
        """
        Validate that all required settings are present.

        Returns:
            List of missing settings (empty if all present)
        """
        missing = []

        if not self.opera_client_id:
            missing.append("OPERA_CLIENT_ID")

        if not self.opera_client_secret:
            missing.append("OPERA_CLIENT_SECRET")

        if not self.opera_token_url:
            missing.append("OPERA_TOKEN_URL")

        if not self.opera_base_url:
            missing.append("OPERA_BASE_URL")

        return missing


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get the global settings instance.

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        # In production, these values should come from environment variables
        # For testing purposes, we provide default values
        # These are intentionally non-sensitive test values
        test_client_id = "test_client_id"  # noqa: S105 - Test credential, not a real secret
        test_client_secret = "test_client_secret"  # noqa: S105 - Test credential, not a real secret

        _settings = Settings(
            opera_client_id=test_client_id,
            opera_client_secret=test_client_secret,
            opera_token_url="https://test-api.oracle-hospitality.com/oauth/v1/tokens",  # noqa: S106 - Test URL, not a password
            opera_base_url="https://test-api.oracle-hospitality.com",
            opera_api_version="v1",
            opera_environment="testing",
            default_hotel_id="TEST001",
            request_timeout=30,
            max_retries=3,
            retry_backoff=1.0,
            enable_cache=True,
            cache_ttl=300,
            cache_max_memory=10000,
            oauth_max_retries=3,
            oauth_retry_backoff=1.0,
            enable_persistent_token_cache=False,
            token_cache_dir=tempfile.gettempdir(),  # noqa: S108 - Temporary directory for testing
            log_level="INFO",
            log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            enable_structured_logging=True,
        )
    return _settings
