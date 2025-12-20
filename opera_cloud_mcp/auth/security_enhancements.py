"""
Production-grade security enhancements for OPERA Cloud MCP authentication.

This module provides comprehensive security hardening for OAuth2 authentication
including token binding, security monitoring, and audit logging.
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel

from opera_cloud_mcp.utils.exceptions import SecurityError

logger = logging.getLogger(__name__)


class TokenBinding(BaseModel):
    """Token binding information for enhanced security."""

    client_fingerprint: str
    issued_at: datetime
    bound_ip: str | None = None
    user_agent_hash: str | None = None
    session_id: str | None = None

    @property
    def is_valid(self) -> bool:
        """Check if token binding is still valid."""
        # Token binding expires after 24 hours
        max_age = timedelta(hours=24)
        return datetime.now(UTC) - self.issued_at < max_age


class AuditEvent(BaseModel):
    """Security audit event model."""

    event_type: str
    timestamp: datetime
    client_id_hash: str  # Hashed for privacy
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict[str, Any] = {}
    risk_score: int = 0  # 0-100 risk assessment


class SecurityMonitor:
    """Monitors authentication security events and detects anomalies."""

    def __init__(self) -> None:
        self._failed_attempts: dict[str, list] = {}
        self._successful_auths: dict[str, datetime] = {}
        self._blocked_clients: set[str] = set()
        self._audit_log: list[AuditEvent] = []
        self._max_failed_attempts = 5
        self._lockout_duration = timedelta(minutes=15)

    def record_authentication_attempt(
        self,
        client_id: str,
        success: bool,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record authentication attempt for monitoring."""
        client_id_hash = self._hash_client_id(client_id)
        now = datetime.now(UTC)

        event = AuditEvent(
            event_type="auth_attempt" if success else "auth_failure",
            timestamp=now,
            client_id_hash=client_id_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )

        if success:
            # Clear failed attempts on success
            if client_id in self._failed_attempts:
                del self._failed_attempts[client_id]
            self._successful_auths[client_id] = now
            event.risk_score = 0
        else:
            # Track failed attempts
            if client_id not in self._failed_attempts:
                self._failed_attempts[client_id] = []

            self._failed_attempts[client_id].append(now)

            # Remove old failed attempts (older than 1 hour)
            cutoff = now - timedelta(hours=1)
            self._failed_attempts[client_id] = [
                attempt
                for attempt in self._failed_attempts[client_id]
                if attempt > cutoff
            ]

            # Calculate risk score based on failed attempts
            recent_failures = len(self._failed_attempts[client_id])
            event.risk_score = min(100, recent_failures * 20)

            # Block client if too many failures
            if recent_failures >= self._max_failed_attempts:
                self._blocked_clients.add(client_id)
                logger.warning(
                    f"Client blocked due to {recent_failures} "
                    + "failed authentication attempts",
                    extra={
                        "client_id_hash": client_id_hash,
                        "failed_attempts": recent_failures,
                        "ip_address": ip_address,
                    },
                )

        self._audit_log.append(event)
        self._cleanup_audit_log()

        logger.info(
            f"Authentication {'succeeded' if success else 'failed'}",
            extra={
                "event_type": event.event_type,
                "client_id_hash": client_id_hash,
                "risk_score": event.risk_score,
                "ip_address": ip_address,
            },
        )

    def is_client_blocked(self, client_id: str) -> bool:
        """Check if client is currently blocked."""
        if client_id not in self._blocked_clients:
            return False

        # Check if lockout has expired
        if client_id in self._failed_attempts:
            last_failure = max(self._failed_attempts[client_id])
            if datetime.now(UTC) - last_failure > self._lockout_duration:
                # Unblock client
                self._blocked_clients.discard(client_id)
                if client_id in self._failed_attempts:
                    del self._failed_attempts[client_id]
                return False

        return True

    def get_risk_assessment(self, client_id: str) -> dict[str, Any]:
        """Get risk assessment for a client."""
        client_id_hash = self._hash_client_id(client_id)
        now = datetime.now(UTC)

        # Recent failed attempts
        failed_count = 0
        if client_id in self._failed_attempts:
            cutoff = now - timedelta(hours=1)
            failed_count = len(
                [
                    attempt
                    for attempt in self._failed_attempts[client_id]
                    if attempt > cutoff
                ]
            )

        # Time since last successful auth
        last_success = self._successful_auths.get(client_id)
        hours_since_success = None
        if last_success:
            hours_since_success = (now - last_success).total_seconds() / 3600

        risk_level = "low"
        if failed_count >= 3:
            risk_level = "high"
        elif failed_count >= 1 or (
            hours_since_success and hours_since_success > 168
        ):  # 1 week
            risk_level = "medium"

        return {
            "client_id_hash": client_id_hash,
            "risk_level": risk_level,
            "failed_attempts_1h": failed_count,
            "hours_since_success": hours_since_success,
            "is_blocked": self.is_client_blocked(client_id),
            "assessment_time": now.isoformat(),
        }

    def get_audit_events(
        self, hours: int = 24, event_types: set[str] | None = None
    ) -> list[AuditEvent]:
        """Get audit events from specified time period."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        events = [event for event in self._audit_log if event.timestamp > cutoff]

        if event_types:
            events = [event for event in events if event.event_type in event_types]

        return sorted(events, key=lambda e: e.timestamp, reverse=True)

    def _hash_client_id(self, client_id: str) -> str:
        """Hash client ID for privacy."""
        return hashlib.sha256(f"client_{client_id}".encode()).hexdigest()[:16]

    def _cleanup_audit_log(self) -> None:
        """Clean up old audit events."""
        if len(self._audit_log) > 10000:  # Keep max 10k events
            cutoff = datetime.now(UTC) - timedelta(days=30)
            self._audit_log = [
                event for event in self._audit_log if event.timestamp > cutoff
            ]


class SecureTokenCache:
    """Enhanced secure token cache with token binding and integrity protection."""

    def __init__(self, cache_dir: Path | None = None, master_key: bytes | None = None):
        """Initialize secure token cache."""
        self.cache_dir = cache_dir or Path.home() / ".opera_cloud_mcp" / "cache"
        self.cache_dir.mkdir(
            parents=True, exist_ok=True, mode=0o700
        )  # Restrictive permissions

        # Use provided master key or derive from system entropy
        if master_key:
            self._master_key = master_key
        else:
            self._master_key = self._derive_master_key()

        self._token_bindings: dict[str, TokenBinding] = {}

    def _derive_master_key(self) -> bytes:
        """Derive master encryption key from system-specific data."""
        key_file = self.cache_dir / ".master_key"

        if key_file.exists():
            # Load existing key
            try:
                with key_file.open("rb") as f:
                    salt = f.read(32)
                    if len(salt) != 32:
                        raise ValueError("Invalid salt length")
            except Exception as e:
                logger.warning(f"Failed to load master key, generating new one: {e}")
                key_file.unlink(missing_ok=True)

        if not key_file.exists():
            # Generate new key
            salt = secrets.token_bytes(32)
            key_file.write_bytes(salt)
            # Set restrictive permissions
            key_file.chmod(0o600)

        # Derive key from salt + system-specific data
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        # Include system-specific entropy
        system_entropy = f"{Path.home()}{self.cache_dir}".encode()
        key = kdf.derive(system_entropy)

        return key

    def _get_cipher(self, client_id: str) -> Fernet:
        """Get Fernet cipher for specific client."""
        # Client-specific key derivation
        client_key = hmac.new(
            self._master_key, f"client_{client_id}".encode(), hashlib.sha256
        ).digest()

        return Fernet(
            Fernet.generate_key()
            if len(client_key) != 32
            else client_key + b"\x00" * (32 - len(client_key))
        )

    def save_token_secure(
        self,
        client_id: str,
        token_data: dict[str, Any],
        binding: TokenBinding | None = None,
    ) -> None:
        """Save token with enhanced security and integrity protection."""
        try:
            cache_file = self._get_cache_file(client_id)
            cipher = self._get_cipher(client_id)

            # Add integrity protection
            payload = {
                "token_data": token_data,
                "binding": binding.model_dump() if binding else None,
                "checksum": self._calculate_checksum(token_data),
                "timestamp": datetime.now(UTC).isoformat(),
            }

            encrypted_data = cipher.encrypt(json.dumps(payload).encode())

            # Atomic write with restrictive permissions
            temp_file = cache_file.with_suffix(".tmp")
            temp_file.write_bytes(encrypted_data)
            temp_file.chmod(0o600)
            temp_file.rename(cache_file)

            # Store binding in memory
            if binding:
                self._token_bindings[client_id] = binding

            logger.debug("Token securely cached with binding protection")

        except Exception as e:
            logger.error(f"Failed to save secure token: {e}")
            raise SecurityError(f"Token caching failed: {e}") from e

    def load_token_secure(
        self, client_id: str, validate_binding: bool = True
    ) -> dict[str, Any] | None:
        """Load token with security validation."""
        try:
            cache_file = self._get_cache_file(client_id)
            if not cache_file.exists():
                return None

            cipher = self._get_cipher(client_id)

            with cache_file.open("rb") as f:
                encrypted_data = f.read()

            decrypted_data = cipher.decrypt(encrypted_data)
            payload = json.loads(decrypted_data.decode())

            # Verify integrity
            token_data = payload["token_data"]
            stored_checksum = payload.get("checksum")
            if stored_checksum and stored_checksum != self._calculate_checksum(
                token_data
            ):
                logger.error("Token integrity check failed")
                self.clear_token(client_id)
                raise SecurityError("Token integrity violation")

            # Validate token binding if present
            if validate_binding and payload.get("binding"):
                binding = TokenBinding(**payload["binding"])
                if not binding.is_valid:
                    logger.warning("Token binding expired, clearing token")
                    self.clear_token(client_id)
                    return None

                self._token_bindings[client_id] = binding

            return token_data

        except SecurityError:
            raise
        except Exception as e:
            logger.warning(f"Failed to load secure token: {e}")
            # Clean up corrupted cache
            self.clear_token(client_id)
            return None

    def create_token_binding(
        self,
        client_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenBinding:
        """Create token binding for enhanced security."""
        fingerprint_data = f"{client_id}_{time.time()}_{secrets.token_hex(16)}"
        client_fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()

        user_agent_hash = None
        if user_agent:
            user_agent_hash = hashlib.sha256(user_agent.encode()).hexdigest()[:16]

        return TokenBinding(
            client_fingerprint=client_fingerprint,
            issued_at=datetime.now(UTC),
            bound_ip=ip_address,
            user_agent_hash=user_agent_hash,
            session_id=secrets.token_urlsafe(32),
        )

    def validate_token_binding(self, client_id: str, binding: TokenBinding) -> bool:
        """Validate token binding against stored binding."""
        stored_binding = self._token_bindings.get(client_id)
        if not stored_binding:
            return False

        # Check binding validity
        if not stored_binding.is_valid:
            return False

        # Compare binding attributes
        return (
            stored_binding.client_fingerprint == binding.client_fingerprint
            and stored_binding.session_id == binding.session_id
        )

    def _calculate_checksum(self, token_data: dict[str, Any]) -> str:
        """Calculate integrity checksum for token data."""
        # Sort keys for consistent hashing
        normalized = json.dumps(token_data, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _get_cache_file(self, client_id: str) -> Path:
        """Get cache file path with secure naming."""
        # Use HMAC for secure filename generation
        filename_hash = hmac.new(
            self._master_key, f"cache_{client_id}".encode(), hashlib.sha256
        ).hexdigest()[:32]

        return self.cache_dir / f"token_{filename_hash}.secure"

    def clear_token(self, client_id: str) -> None:
        """Securely clear cached token."""
        try:
            cache_file = self._get_cache_file(client_id)
            if cache_file.exists():
                # Secure deletion - overwrite before deleting
                with cache_file.open("r+b") as f:
                    f.seek(0)
                    f.write(secrets.token_bytes(f.seek(0, 2)))
                    f.flush()
                cache_file.unlink()

            # Clear memory binding
            self._token_bindings.pop(client_id, None)

            logger.debug("Token securely cleared")
        except Exception as e:
            logger.warning(f"Failed to clear token cache: {e}")


class RateLimiter:
    """Token-aware rate limiter for authentication endpoints."""

    def __init__(self, max_requests: int = 10, window_minutes: int = 5):
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self._requests: dict[str, list] = {}

    async def check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits."""
        now = time.time()

        # Clean old requests
        if client_id not in self._requests:
            self._requests[client_id] = []

        # Remove requests outside the window
        window_start = now - self.window_seconds
        self._requests[client_id] = [
            req_time
            for req_time in self._requests[client_id]
            if req_time > window_start
        ]

        # Check limit
        if len(self._requests[client_id]) >= self.max_requests:
            logger.warning(
                "Rate limit exceeded for client",
                extra={
                    "client_id_hash": hashlib.sha256(client_id.encode()).hexdigest()[
                        :16
                    ],
                    "requests_in_window": len(self._requests[client_id]),
                    "max_requests": self.max_requests,
                },
            )
            return False

        # Record request
        self._requests[client_id].append(now)
        return True

    def get_reset_time(self, client_id: str) -> float | None:
        """Get time until rate limit resets."""
        if client_id not in self._requests or not self._requests[client_id]:
            return None

        oldest_request = min(self._requests[client_id])
        reset_time = oldest_request + self.window_seconds

        return max(0, reset_time - time.time())


# Global instances
security_monitor = SecurityMonitor()
rate_limiter = RateLimiter()
