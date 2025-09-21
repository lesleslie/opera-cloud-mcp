"""
Production-grade secure OAuth2 handler for Oracle OPERA Cloud authentication.

This module extends the base OAuth handler with comprehensive security features
including token binding, rate limiting, security monitoring, and audit logging.
"""

import asyncio
import base64
import hashlib
import hmac
import logging
import math
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from opera_cloud_mcp.auth.oauth_handler import DEFAULT_TOKEN_TYPE, OAuthHandler
from opera_cloud_mcp.auth.security_enhancements import (
    AuditEvent,
    SecureTokenCache,
    SecurityError,
    TokenBinding,
    rate_limiter,
    security_monitor,
)
from opera_cloud_mcp.utils.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class SecureToken(BaseModel):
    """Enhanced token model with security metadata."""

    access_token: str
    token_type: str = DEFAULT_TOKEN_TYPE
    expires_in: int
    issued_at: datetime
    binding: TokenBinding | None = None
    security_metadata: dict[str, Any] = {}

    @property
    def expires_at(self) -> datetime:
        """Calculate token expiration time."""
        return self.issued_at + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 60 second buffer)."""
        now = datetime.now(UTC)
        expires_at = self.expires_at

        # Handle timezone-aware vs timezone-naive datetime comparison
        if self.issued_at.tzinfo is not None:
            if now.tzinfo is None:
                now = now.replace(tzinfo=UTC)
        else:
            if expires_at.tzinfo is not None:
                expires_at = expires_at.replace(tzinfo=None)

        return now >= (expires_at - timedelta(seconds=60))

    @property
    def is_binding_valid(self) -> bool:
        """Check if token binding is still valid."""
        return self.binding is not None and self.binding.is_valid


class SecureOAuthHandler(OAuthHandler):
    """
    Production-grade secure OAuth2 handler with comprehensive security features.

    Enhances base OAuth handler with:
    - Token binding for additional security
    - Rate limiting and abuse detection
    - Security monitoring and audit logging
    - Enhanced token storage with integrity protection
    - Credential rotation and security hardening
    """

    # Instance attributes
    secure_cache: SecureTokenCache | None

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        enable_persistent_cache: bool = True,
        cache_dir: Path | None = None,
        enable_security_monitoring: bool = True,
        enable_rate_limiting: bool = True,
        enable_token_binding: bool = True,
        master_key: bytes | None = None,
        allowed_ips: set[str] | None = None,
    ) -> None:
        """
        Initialize secure OAuth handler.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            token_url: Token endpoint URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_backoff: Base backoff time for retries
            enable_persistent_cache: Enable persistent token caching
            cache_dir: Directory for cache files
            enable_security_monitoring: Enable security monitoring and audit logging
            enable_rate_limiting: Enable rate limiting protection
            enable_token_binding: Enable token binding for enhanced security
            master_key: Master encryption key for token storage
            allowed_ips: Set of allowed IP addresses (None for no restriction)
        """
        # Initialize parent class without persistent cache
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff=retry_backoff,
            enable_persistent_cache=False,  # We'll use our secure cache
            cache_dir=cache_dir,
        )

        # Security configuration
        self.enable_security_monitoring = enable_security_monitoring
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_token_binding = enable_token_binding
        self.allowed_ips = allowed_ips or set()

        # Initialize secure components
        if enable_persistent_cache:
            self.secure_cache = SecureTokenCache(cache_dir, master_key)
        else:
            self.secure_cache = None

        self.security_monitor = security_monitor if enable_security_monitoring else None
        self.rate_limiter = rate_limiter if enable_rate_limiting else None

        # Enhanced token storage
        self._secure_token_cache: SecureToken | None = None
        self._client_secret_hash = self._hash_secret(client_secret)

        # Security metrics
        self._security_events: list[AuditEvent] = []
        self._suspicious_activity_detected = False

        logger.info(
            "Secure OAuth handler initialized",
            extra={
                "client_id_hash": self._hash_client_id(client_id),
                "security_monitoring": enable_security_monitoring,
                "rate_limiting": enable_rate_limiting,
                "token_binding": enable_token_binding,
                "ip_restrictions": len(self.allowed_ips) > 0,
            },
        )

    async def get_token_secure(
        self,
        ip_address: str | None = None,
        user_agent: str | None = None,
        force_refresh: bool = False,
    ) -> str:
        """
        Get a valid access token with enhanced security validation.

        Args:
            ip_address: Client IP address for validation
            user_agent: Client user agent for binding
            force_refresh: Force token refresh even if cached token is valid

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If authentication fails
            SecurityError: If security validation fails
        """
        async with self._token_lock:
            # Security validations
            await self._validate_security_context(ip_address, user_agent)

            # Check rate limiting
            if self.rate_limiter and not await self.rate_limiter.check_rate_limit(
                self.client_id
            ):
                reset_time = self.rate_limiter.get_reset_time(self.client_id)
                self._record_security_event(
                    "rate_limit_exceeded",
                    ip_address,
                    user_agent,
                    {"reset_time": reset_time},
                )
                raise SecurityError(
                    f"Rate limit exceeded. Try again in {reset_time:.1f} seconds."
                )

            # Check if we need to refresh token
            needs_refresh = force_refresh or self._needs_token_refresh()

            if not needs_refresh:
                logger.debug("Using cached secure token")
                if self._secure_token_cache is not None:
                    return self._secure_token_cache.access_token
                # If we get here, we need to refresh anyway
                logger.info("Cached token is None, requesting new secure OAuth token")
                return await self._refresh_token_secure(ip_address, user_agent)

            logger.info("Requesting new secure OAuth token")
            return await self._refresh_token_secure(ip_address, user_agent)

    async def _handle_auth_success(
        self,
        token_data: dict[str, Any],
        ip_address: str | None,
        user_agent: str | None,
        attempt: int,
        start_time: datetime,
    ) -> str:
        """Handle successful authentication and return access token."""
        # Create secure token with binding
        secure_token = await self._create_secure_token(
            token_data, ip_address, user_agent
        )

        # Cache secure token
        await self._cache_secure_token(secure_token)

        # Record successful authentication
        duration = (datetime.now(UTC) - start_time).total_seconds()
        self._record_security_event(
            "auth_success",
            ip_address,
            user_agent,
            {
                "attempt": attempt + 1,
                "duration_seconds": duration,
                "token_expires_in": token_data["expires_in"],
            },
        )

        logger.info(
            "Secure OAuth token obtained successfully",
            extra={
                "attempt": attempt + 1,
                "duration_seconds": duration,
                "expires_in": token_data["expires_in"],
                "token_binding": self.enable_token_binding,
            },
        )

        return secure_token.access_token

    async def _should_retry_authentication(
        self, response: httpx.Response, attempt: int
    ) -> bool:
        """Check if we should retry authentication."""
        if response.status_code in (400, 401, 403):
            # Don't retry authentication errors
            return False

        # Retry on server errors
        if attempt < self.max_retries:
            backoff_time = self.retry_backoff * (2**attempt)
            logger.warning(f"Retrying secure token request in {backoff_time}s...")
            await asyncio.sleep(backoff_time)
            return True

        return False

    async def _refresh_token_secure(
        self, ip_address: str | None = None, user_agent: str | None = None
    ) -> str:
        """
        Request a new token with enhanced security features.

        Args:
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            New access token

        Raises:
            AuthenticationError: If token request fails
            SecurityError: If security validation fails
        """
        start_time = datetime.now(UTC)
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"Secure token refresh attempt {attempt + 1}/{self.max_retries + 1}"
                )

                # Enhanced request preparation
                token_request = await self._prepare_secure_token_request(
                    ip_address, user_agent
                )

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.debug(f"Requesting secure token from: {self.token_url}")

                    response = await client.post(**token_request)

                    if response.status_code == 200:
                        # Success - process secure token
                        token_data = response.json()

                        # Validate token response
                        await self._validate_token_response(token_data)

                        # Handle successful authentication
                        return await self._handle_auth_success(
                            token_data, ip_address, user_agent, attempt, start_time
                        )

                    else:
                        # Handle authentication failure
                        await self._handle_auth_failure(
                            response, attempt, ip_address, user_agent
                        )

                        # Check if we should retry
                        if not await self._should_retry_authentication(
                            response, attempt
                        ):
                            break

            except httpx.TimeoutException as e:
                last_error = e
                await self._handle_network_error(
                    "timeout", e, attempt, ip_address, user_agent
                )

            except httpx.RequestError as e:
                last_error = e
                await self._handle_network_error(
                    "network_error", e, attempt, ip_address, user_agent
                )

            except Exception as e:
                last_error = e
                await self._handle_unexpected_error(e, attempt, ip_address, user_agent)

        # All attempts failed
        duration = (datetime.now(UTC) - start_time).total_seconds()
        final_error_msg = (
            f"Secure token refresh failed after {self.max_retries + 1} attempts"
        )

        if last_error:
            final_error_msg += f": {last_error}"

        self._record_security_event(
            "auth_failed_all_attempts",
            ip_address,
            user_agent,
            {
                "total_attempts": self.max_retries + 1,
                "duration_seconds": duration,
                "last_error": str(last_error) if last_error else None,
            },
        )

        raise AuthenticationError(final_error_msg)

    async def _prepare_secure_token_request(
        self, ip_address: str | None = None, user_agent: str | None = None
    ) -> dict[str, Any]:
        """Prepare secure token request with enhanced headers."""
        # Generate request nonce for replay protection
        nonce = secrets.token_urlsafe(32)
        timestamp = str(int(datetime.now(UTC).timestamp()))

        # Prepare basic authentication
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": user_agent or "OPERA-Cloud-MCP-Secure/1.0",
            "X-Request-ID": secrets.token_urlsafe(16),
            "X-Request-Timestamp": timestamp,
            "X-Request-Nonce": nonce,
        }

        # Add client IP if available
        if ip_address:
            headers["X-Forwarded-For"] = ip_address
            headers["X-Real-IP"] = ip_address

        # Create signature for request integrity
        signature_data = f"{self.client_id}{timestamp}{nonce}{self.token_url}"
        signature = hmac.new(
            self.client_secret.encode(), signature_data.encode(), hashlib.sha256
        ).hexdigest()
        headers["X-Request-Signature"] = signature

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,  # Include in body for double verification
        }

        return {
            "url": self.token_url,
            "headers": headers,
            "data": data,
        }

    async def _validate_token_response(self, token_data: dict[str, Any]) -> None:
        """Validate token response with enhanced security checks."""
        # Basic validation
        required_fields = ["access_token", "expires_in"]
        missing_fields = [field for field in required_fields if field not in token_data]
        if missing_fields:
            raise AuthenticationError(
                f"Invalid token response: missing {missing_fields}"
            )

        # Security validation
        access_token = token_data["access_token"]
        expires_in = int(token_data["expires_in"])

        # Token format validation
        if not isinstance(access_token, str) or len(access_token) < 20:
            raise SecurityError("Invalid access token format")

        if not isinstance(expires_in, int) or expires_in <= 0:
            raise SecurityError("Invalid token expiration time")

        # Check for suspicious token characteristics
        if expires_in > 86400:  # More than 24 hours
            logger.warning(
                "Token has unusually long expiration time",
                extra={"expires_in": expires_in},
            )

        # Token entropy check (basic randomness validation)
        token_entropy = self._calculate_entropy(access_token)
        if token_entropy < 3.0:  # Low entropy threshold
            logger.warning(
                "Access token has low entropy", extra={"entropy": token_entropy}
            )

    async def _create_secure_token(
        self,
        token_data: dict[str, Any],
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SecureToken:
        """Create secure token with binding and metadata."""
        now = datetime.now(UTC)

        # Create token binding if enabled
        binding = None
        if self.enable_token_binding and self.secure_cache:
            binding = self.secure_cache.create_token_binding(
                self.client_id, ip_address, user_agent
            )

        # Security metadata
        security_metadata = {
            "issued_to_ip": ip_address,
            "user_agent_hash": hashlib.sha256(user_agent.encode()).hexdigest()[:16]
            if user_agent
            else None,
            "client_id_hash": self._hash_client_id(self.client_id),
            "token_version": "secure_v1",
            "entropy_score": self._calculate_entropy(token_data["access_token"]),
        }

        return SecureToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=int(token_data["expires_in"]),
            issued_at=now,
            binding=binding,
            security_metadata=security_metadata,
        )

    async def _cache_secure_token(self, secure_token: SecureToken) -> None:
        """Cache secure token with enhanced protection."""
        # Update memory cache
        self._secure_token_cache = secure_token

        # Save to secure persistent cache if enabled
        if self.secure_cache:
            token_data = {
                "access_token": secure_token.access_token,
                "token_type": secure_token.token_type,
                "expires_in": secure_token.expires_in,
                "issued_at": secure_token.issued_at.isoformat(),
                "security_metadata": secure_token.security_metadata,
            }

            self.secure_cache.save_token_secure(
                self.client_id, token_data, secure_token.binding
            )

    async def _validate_security_context(
        self, ip_address: str | None = None, user_agent: str | None = None
    ) -> None:
        """Validate security context before token operations."""
        # Check if client is blocked
        if self.security_monitor and self.security_monitor.is_client_blocked(
            self.client_id
        ):
            raise SecurityError(
                "Client is temporarily blocked due to security violations"
            )

        # IP address validation
        if self.allowed_ips and ip_address and ip_address not in self.allowed_ips:
            self._record_security_event(
                "unauthorized_ip",
                ip_address,
                user_agent,
                {"allowed_ips": list(self.allowed_ips)},
            )
            raise SecurityError(f"IP address {ip_address} not allowed")

        # Detect suspicious activity
        if await self._detect_suspicious_activity(ip_address, user_agent):
            self._suspicious_activity_detected = True
            self._record_security_event(
                "suspicious_activity",
                ip_address,
                user_agent,
                {"detection_time": datetime.now(UTC).isoformat()},
            )
            raise SecurityError("Suspicious activity detected")

    def _needs_token_refresh(self) -> bool:
        """Check if token refresh is needed with security considerations."""
        if not self._secure_token_cache:
            return True

        # Check token expiration
        if self._secure_token_cache.is_expired:
            return True

        # Check binding validity
        if (
            self.enable_token_binding
            and self._secure_token_cache.binding
            and not self._secure_token_cache.is_binding_valid
        ):
            logger.info("Token binding expired, refreshing token")
            return True

        return False

    def _record_security_event(
        self,
        event_type: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record security event for monitoring."""
        if not self.security_monitor:
            return

        success = event_type in ("auth_success", "token_refresh_success")

        self.security_monitor.record_authentication_attempt(
            self.client_id, success, ip_address, user_agent, details or {}
        )

    async def _detect_suspicious_activity(
        self, ip_address: str | None = None, user_agent: str | None = None
    ) -> bool:
        """Detect suspicious authentication patterns."""
        if not self.security_monitor:
            return False

        # Get risk assessment
        risk_assessment = self.security_monitor.get_risk_assessment(self.client_id)

        # Check for high-risk patterns
        if risk_assessment["risk_level"] == "high":
            return True

        # Check for rapid successive requests from different IPs
        recent_events = self.security_monitor.get_audit_events(
            hours=1, event_types={"auth_attempt", "auth_success", "auth_failure"}
        )

        if len(recent_events) > 20:  # More than 20 auth events in last hour
            unique_ips = set()
            for event in recent_events[-20:]:  # Check last 20 events
                if event.ip_address:
                    unique_ips.add(event.ip_address)

            if len(unique_ips) > 5:  # Requests from more than 5 different IPs
                return True

        return False

    async def _handle_auth_failure(
        self,
        response: httpx.Response,
        attempt: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Handle authentication failure with security logging."""
        error_msg = f"Token request failed: HTTP {response.status_code}"
        error_details: dict[str, Any] = {
            "status_code": response.status_code,
            "attempt": attempt + 1,
        }

        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                # Make sure we don't overwrite response_text with int values
                response_text = error_data.pop("response_text", None)
                error_details.update(error_data)
                error_description = error_data.get("error_description")
                error_code = error_data.get("error", "Unknown error")
                error_msg += f" - {error_description or error_code}"
                # Restore response_text if it was an int, or set it to None
                if response_text is not None and not isinstance(response_text, int):
                    error_details["response_text"] = response_text
        except Exception:
            error_msg += f" - {response.text[:200]}"
            error_details["response_text"] = response.text[:200]

        self._record_security_event(
            "auth_failure", ip_address, user_agent, error_details
        )

        logger.error(error_msg, extra=error_details)

        if response.status_code in (400, 401, 403):
            raise AuthenticationError(error_msg)

    async def _handle_network_error(
        self,
        error_type: str,
        error: Exception,
        attempt: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Handle network errors with security logging."""
        error_details: dict[str, Any] = {
            "error_type": error_type,
            "attempt": attempt + 1,
            "error_message": str(error),
        }

        self._record_security_event(
            "network_error", ip_address, user_agent, error_details
        )

        if attempt < self.max_retries:
            backoff_time = self.retry_backoff * (2**attempt)
            await asyncio.sleep(backoff_time)
        else:
            raise AuthenticationError(
                f"Authentication {error_type}: {error}"
            ) from error

    async def _handle_unexpected_error(
        self,
        error: Exception,
        attempt: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Handle unexpected errors with security logging."""
        error_details: dict[str, Any] = {
            "error_type": "unexpected_error",
            "attempt": attempt + 1,
            "error_class": error.__class__.__name__,
            "error_message": str(error),
        }

        self._record_security_event(
            "unexpected_error", ip_address, user_agent, error_details
        )

        logger.error(f"Unexpected error during secure token refresh: {error}")

        if attempt < self.max_retries:
            backoff_time = self.retry_backoff * (2**attempt)
            await asyncio.sleep(backoff_time)
        else:
            raise AuthenticationError(
                f"Unexpected authentication error: {error}"
            ) from error

    def _hash_client_id(self, client_id: str) -> str:
        """Hash client ID for privacy in logs."""
        return hashlib.sha256(f"client_{client_id}".encode()).hexdigest()[:16]

    def _hash_secret(self, secret: str) -> str:
        """Hash client secret for validation."""
        return hashlib.sha256(secret.encode()).hexdigest()

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0

        # Count character frequencies
        char_counts: dict[str, int] = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Calculate entropy
        length = len(text)
        entropy = 0.0

        for count in char_counts.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)

        return entropy

    # Enhanced API methods

    async def get_token(self) -> str:
        """Get token using the secure implementation."""
        return await self.get_token_secure()

    async def invalidate_token_secure(self, reason: str = "manual") -> None:
        """Invalidate cached token with security event logging."""
        async with self._token_lock:
            logger.info(f"Invalidating secure token: {reason}")

            self._record_security_event(
                "token_invalidated",
                details={"reason": reason, "timestamp": datetime.now(UTC).isoformat()},
            )

            # Clear memory cache
            self._secure_token_cache = None

            # Clear secure persistent cache
            if self.secure_cache:
                self.secure_cache.clear_token(self.client_id)

    def get_security_status(self) -> dict[str, Any]:
        """Get comprehensive security status."""
        status = {
            "client_id_hash": self._hash_client_id(self.client_id),
            "security_monitoring": self.enable_security_monitoring,
            "rate_limiting": self.enable_rate_limiting,
            "token_binding": self.enable_token_binding,
            "ip_restrictions": len(self.allowed_ips) > 0,
            "allowed_ip_count": len(self.allowed_ips),
            "suspicious_activity_detected": self._suspicious_activity_detected,
        }

        # Token information
        if self._secure_token_cache:
            status.update(
                {
                    "has_secure_token": True,
                    "token_expires_at": self._secure_token_cache.expires_at.isoformat(),
                    "token_binding_valid": self._secure_token_cache.is_binding_valid,
                    "token_security_metadata": (
                        self._secure_token_cache.security_metadata
                    ),
                }
            )
        else:
            status["has_secure_token"] = False

        # Risk assessment
        if self.security_monitor:
            risk_assessment = self.security_monitor.get_risk_assessment(self.client_id)
            status["risk_assessment"] = risk_assessment

            # Recent security events
            recent_events = self.security_monitor.get_audit_events(hours=24)
            status["recent_events_24h"] = len(recent_events)
            status["recent_failures"] = len(
                [
                    e
                    for e in recent_events
                    if e.event_type
                    in ("auth_failure", "network_error", "suspicious_activity")
                ]
            )

        return status

    async def rotate_credentials(
        self, new_client_secret: str, validate_new_credentials: bool = True
    ) -> bool:
        """
        Rotate OAuth credentials securely.

        Args:
            new_client_secret: New client secret
            validate_new_credentials: Whether to validate new credentials

        Returns:
            True if rotation succeeded, False otherwise
        """
        try:
            logger.info("Starting credential rotation")

            # Store old credentials for rollback
            old_secret = self.client_secret
            old_secret_hash = self._client_secret_hash

            # Update credentials
            self.client_secret = new_client_secret
            self._client_secret_hash = self._hash_secret(new_client_secret)

            # Validate new credentials if requested
            if validate_new_credentials:
                await self.invalidate_token_secure("credential_rotation")
                await self.get_token_secure()

                logger.info("Credential rotation completed successfully")

                self._record_security_event(
                    "credentials_rotated",
                    details={
                        "old_secret_hash": old_secret_hash[:8] + "...",
                        "new_secret_hash": self._client_secret_hash[:8] + "...",
                        "validation_successful": True,
                    },
                )

                return True
            else:
                # Just invalidate existing tokens
                await self.invalidate_token_secure("credential_rotation_unvalidated")

                logger.info("Credential rotation completed (unvalidated)")
                return True

        except Exception as e:
            # Rollback on failure
            logger.error(f"Credential rotation failed: {e}")
            self.client_secret = old_secret
            self._client_secret_hash = old_secret_hash

            self._record_security_event(
                "credential_rotation_failed",
                details={"error": str(e), "rollback_completed": True},
            )

            return False
