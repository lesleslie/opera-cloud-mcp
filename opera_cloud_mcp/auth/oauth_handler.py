"""
OAuth2 handler for Oracle OPERA Cloud authentication.

This module manages OAuth2 token lifecycle including acquisition,
caching, and automatic refresh for OPERA Cloud APIs.
"""

import asyncio
import base64
import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from cryptography.fernet import Fernet
from pydantic import BaseModel

from opera_cloud_mcp.utils.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


# S105: This is a standard OAuth token type, not a password
DEFAULT_TOKEN_TYPE = "Bearer"  # noqa: S105

# Default token expiry warning threshold in seconds
TOKEN_EXPIRY_WARNING_SECONDS = 300


class Token(BaseModel):
    """OAuth2 token model."""

    access_token: str
    token_type: str = DEFAULT_TOKEN_TYPE
    expires_in: int
    issued_at: datetime

    @property
    def expires_at(self) -> datetime:
        """Calculate token expiration time."""
        return self.issued_at + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 60 second buffer)."""
        # Ensure both datetimes are timezone-aware for comparison
        now = datetime.now(UTC)
        expires_at = self.expires_at

        # If expires_at is timezone-naive, make it timezone-aware to match 'now'
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        return now >= (expires_at - timedelta(seconds=60))


class TokenCache:
    """Persistent encrypted token cache."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """
        Initialize token cache.

        Args:
            cache_dir: Directory for cache files (defaults to ~/.opera_cloud_mcp/cache)
        """
        self.cache_dir = cache_dir or Path.home() / ".opera_cloud_mcp" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._key: bytes | None = None

    def _get_encryption_key(self, client_id: str) -> bytes:
        """Get or create encryption key for client."""
        if not self._key:
            # Create key from client_id (deterministic but unique per client)
            key_data = hashlib.sha256(f"opera_mcp_{client_id}".encode()).digest()
            self._key = base64.urlsafe_b64encode(key_data)
        return self._key

    def _get_cache_file(self, client_id: str) -> Path:
        """Get cache file path for client."""
        safe_client_id = hashlib.sha256(client_id.encode()).hexdigest()[:16]
        return self.cache_dir / f"token_{safe_client_id}.cache"

    def save_token(self, client_id: str, token: Token) -> None:
        """Save encrypted token to cache."""
        try:
            cache_file = self._get_cache_file(client_id)
            key = self._get_encryption_key(client_id)
            cipher = Fernet(key)

            token_data = {
                "access_token": token.access_token,
                "token_type": token.token_type,
                "expires_in": token.expires_in,
                "issued_at": token.issued_at.isoformat(),
            }

            encrypted_data = cipher.encrypt(json.dumps(token_data).encode())
            cache_file.write_bytes(encrypted_data)
            logger.debug(f"Token cached to {cache_file}")

        except Exception as e:
            logger.warning(f"Failed to save token to cache: {e}")

    def load_token(self, client_id: str) -> Token | None:
        """Load encrypted token from cache."""
        try:
            cache_file = self._get_cache_file(client_id)
            if not cache_file.exists():
                return None

            key = self._get_encryption_key(client_id)
            cipher = Fernet(key)

            encrypted_data = cache_file.read_bytes()
            decrypted_data = cipher.decrypt(encrypted_data)
            token_data = json.loads(decrypted_data.decode())

            token = Token(
                access_token=token_data["access_token"],
                token_type=token_data["token_type"],
                expires_in=token_data["expires_in"],
                issued_at=datetime.fromisoformat(token_data["issued_at"]),
            )

            logger.debug(f"Token loaded from cache: {cache_file}")
            return token

        except Exception as e:
            logger.warning(f"Failed to load token from cache: {e}")
            # Clean up corrupted cache file
            try:
                cache_file = self._get_cache_file(client_id)
                if cache_file.exists():
                    cache_file.unlink()
            except Exception as e:
                logger.debug(f"Failed to clean up cache file: {e}")
            return None

    def clear_token(self, client_id: str) -> None:
        """Clear cached token."""
        try:
            cache_file = self._get_cache_file(client_id)
            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"Token cache cleared: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to clear token cache: {e}")


class OAuthHandler:
    """
    Manages OAuth2 authentication for OPERA Cloud APIs.

    Handles token acquisition, caching, and automatic refresh
    according to OAuth2 client credentials flow with persistent
    encrypted caching and comprehensive error handling.
    """

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
    ) -> None:
        """
        Initialize OAuth handler.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            token_url: Token endpoint URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for token requests
            retry_backoff: Base backoff time for retries
            enable_persistent_cache: Enable persistent token caching
            cache_dir: Directory for cache files
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self._token_cache: Token | None = None
        self._token_lock = asyncio.Lock()
        self._token_refresh_count = 0
        self._last_refresh_attempt: datetime | None = None

        # Persistent cache
        self.enable_persistent_cache = enable_persistent_cache
        self.persistent_cache = (
            TokenCache(cache_dir) if enable_persistent_cache else None
        )

        # Validate credentials on initialization
        if not client_id or not client_secret:
            raise AuthenticationError("Client ID and client secret are required")

        if not token_url:
            raise AuthenticationError("Token URL is required")

        logger.info(f"OAuth handler initialized for client: {client_id[:8]}...")
        logger.debug(f"Token URL: {token_url}")
        logger.debug(
            f"Persistent cache: {'enabled' if enable_persistent_cache else 'disabled'}"
        )

    async def get_token(self) -> str:
        """
        Get a valid access token.

        Returns cached token if valid, otherwise requests a new one.
        Tries persistent cache first, then memory cache, then fresh token.
        Thread-safe with async locking.

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If token acquisition fails
        """
        async with self._token_lock:
            # Check memory cache first
            if self._token_cache and not self._token_cache.is_expired:
                logger.debug("Using memory cached OAuth token")
                return self._token_cache.access_token

            # Try persistent cache if enabled
            if self.persistent_cache:
                cached_token = self.persistent_cache.load_token(self.client_id)
                if cached_token and not cached_token.is_expired:
                    logger.debug("Using persistent cached OAuth token")
                    self._token_cache = cached_token
                    return cached_token.access_token
                elif cached_token:
                    logger.debug("Persistent cached token expired, clearing")
                    self.persistent_cache.clear_token(self.client_id)

            logger.info("Requesting new OAuth token")
            return await self._refresh_token()

    def _prepare_token_request(self) -> tuple[dict[str, str], dict[str, str]]:
        """Prepare headers and data for token request."""
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "OPERA-Cloud-MCP/1.0",
        }

        data = {
            "grant_type": "client_credentials",
        }

        return headers, data

    def _process_successful_token_response(
        self, token_data: dict[str, Any], attempt: int
    ) -> str:
        """Process successful token response and cache the token."""
        # Validate required fields
        required_fields = ["access_token", "expires_in"]
        missing_fields = [field for field in required_fields if field not in token_data]
        if missing_fields:
            raise AuthenticationError(
                f"Invalid token response: missing {missing_fields}"
            )

        # Create and cache new token
        self._token_cache = Token(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data["expires_in"],
            issued_at=datetime.now(UTC),
        )

        # Save to persistent cache if enabled
        if self.persistent_cache:
            self.persistent_cache.save_token(self.client_id, self._token_cache)

        self._token_refresh_count += 1

        logger.info(
            "Successfully obtained new OAuth token",
            extra={
                "attempt": attempt + 1,
                "refresh_count": self._token_refresh_count,
                "expires_in": token_data["expires_in"],
                "token_type": token_data.get("token_type", "Bearer"),
            },
        )

        return self._token_cache.access_token

    def _handle_error_response(self, response: httpx.Response, attempt: int) -> str:
        """Handle error response from token endpoint."""
        error_msg = f"Token request failed: HTTP {response.status_code}"
        error_details = {}

        try:
            error_data = response.json()
            if isinstance(error_data, dict):
                error_details = error_data
                error_description = error_data.get("error_description")
                error_code = error_data.get("error", "Unknown error")
                error_msg += f" - {error_description or error_code}"
        except Exception:
            error_msg += f" - {response.text[:200]}"

        logger.error(
            error_msg,
            extra={
                "status_code": response.status_code,
                "attempt": attempt + 1,
                "error_details": error_details,
            },
        )

        # Don't retry on authentication errors (400, 401, 403)
        if response.status_code in (400, 401, 403):
            raise AuthenticationError(error_msg)

        return error_msg

    async def _handle_request_exception(
        self, error: Exception, attempt: int
    ) -> tuple[bool, float]:
        """Handle exceptions during token request.

        Returns:
            Tuple of (should_retry, backoff_time)
        """
        if isinstance(error, httpx.TimeoutException):
            error_msg = f"Token request timeout after {self.timeout}s"
            logger.warning(f"{error_msg} (attempt {attempt + 1})")

            if attempt < self.max_retries:
                backoff_time = self.retry_backoff * (2**attempt)
                return True, backoff_time
            raise AuthenticationError(error_msg) from error

        elif isinstance(error, httpx.RequestError):
            error_msg = f"Token request network error: {error}"
            logger.warning(f"{error_msg} (attempt {attempt + 1})")

            if attempt < self.max_retries:
                backoff_time = self.retry_backoff * (2**attempt)
                return True, backoff_time
            raise AuthenticationError(error_msg) from error

        elif isinstance(error, KeyError | ValueError):
            # Don't retry on data format errors
            error_msg = f"Invalid token response format: {error}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg) from error

        else:
            error_msg = f"Unexpected error during token refresh: {error}"
            logger.error(f"{error_msg} (attempt {attempt + 1})")

            if attempt < self.max_retries:
                backoff_time = self.retry_backoff * (2**attempt)
                return True, backoff_time
            raise AuthenticationError(error_msg) from error

    async def _make_token_request(
        self, headers: dict[str, str], data: dict[str, str]
    ) -> httpx.Response:
        """Make the actual token request."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.debug(f"Requesting token from: {self.token_url}")
            return await client.post(self.token_url, headers=headers, data=data)

    async def _refresh_token(self) -> str:
        """
        Request a new token from the OAuth endpoint with retry logic.

        Uses client credentials grant type as per OAuth2 specification
        with comprehensive retry logic and error handling.

        Returns:
            New access token

        Raises:
            AuthenticationError: If token request fails after retries
        """
        self._last_refresh_attempt = datetime.now(UTC)
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    f"Token refresh attempt {attempt + 1}/{self.max_retries + 1}"
                )

                headers, data = self._prepare_token_request()
                response = await self._make_token_request(headers, data)

                if response.status_code == 200:
                    token_data = response.json()
                    return self._process_successful_token_response(token_data, attempt)
                else:
                    error_msg = self._handle_error_response(response, attempt)

                    # Retry on server errors or temporary issues
                    if attempt < self.max_retries:
                        backoff_time = self.retry_backoff * (2**attempt)
                        logger.warning(f"Retrying token request in {backoff_time}s...")
                        await asyncio.sleep(backoff_time)
                        continue
                    else:
                        raise AuthenticationError(error_msg)

            except Exception as e:
                last_error = e
                should_retry, backoff_time = await self._handle_request_exception(
                    e, attempt
                )

                if should_retry:
                    await asyncio.sleep(backoff_time)
                    continue
                # If we reach here, exception was already raised

        # Should not reach here, but just in case
        final_error_msg = f"Token refresh failed after {self.max_retries + 1} attempts"
        if last_error:
            final_error_msg += f": {last_error}"
        raise AuthenticationError(final_error_msg)

    async def invalidate_token(self) -> None:
        """
        Invalidate cached token to force refresh on next request.

        Clears both memory and persistent cache.
        Useful when receiving 401 responses that indicate token expiry.
        """
        async with self._token_lock:
            logger.info("Invalidating cached OAuth token")
            self._token_cache = None

            # Clear persistent cache if enabled
            if self.persistent_cache:
                self.persistent_cache.clear_token(self.client_id)

    async def revoke_token(self, revoke_url: str | None = None) -> bool:
        """
        Revoke the current token if revocation endpoint is available.

        Args:
            revoke_url: Token revocation endpoint URL

        Returns:
            True if revocation succeeded or no token to revoke, False otherwise
        """
        async with self._token_lock:
            if not self._token_cache or not revoke_url:
                logger.debug("No token to revoke or revocation URL not provided")
                return True

            try:
                logger.info("Revoking OAuth token")

                # Prepare revocation request
                credentials = base64.b64encode(
                    f"{self.client_id}:{self.client_secret}".encode()
                ).decode()

                headers = {
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                }

                data = {
                    "token": self._token_cache.access_token,
                    "token_type_hint": "access_token",
                }

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(revoke_url, headers=headers, data=data)

                    if response.status_code == 200:
                        logger.info("Token successfully revoked")
                        await self.invalidate_token()
                        return True
                    else:
                        logger.warning(
                            f"Token revocation failed: HTTP {response.status_code}"
                        )
                        return False

            except Exception as e:
                logger.error(f"Token revocation error: {e}")
                return False

    def get_auth_header(self, token: str) -> dict[str, str]:
        """
        Get authorization header for API requests.

        Args:
            token: Access token

        Returns:
            Dictionary containing Authorization header
        """
        return {"Authorization": f"Bearer {token}"}

    def get_token_info(self) -> dict[str, Any]:
        """
        Get information about the current token.

        Returns:
            Dictionary containing token status and metadata
        """
        if not self._token_cache:
            return {
                "has_token": False,
                "status": "no_token",
                "expires_at": None,
                "expires_in": None,
                "refresh_count": self._token_refresh_count,
                "last_refresh_attempt": self._last_refresh_attempt.isoformat()
                if self._last_refresh_attempt
                else None,
            }

        # Ensure both datetimes are timezone-aware for comparison
        now = datetime.now(UTC)
        token_expires_at = self._token_cache.expires_at
        if token_expires_at.tzinfo is None:
            token_expires_at = token_expires_at.replace(tzinfo=UTC)
        expires_in = max(0, (token_expires_at - now).total_seconds())

        status = "valid"
        if self._token_cache.is_expired:
            status = "expired"
        elif expires_in < TOKEN_EXPIRY_WARNING_SECONDS:
            status = "expiring_soon"

        return {
            "has_token": True,
            "status": status,
            "token_type": self._token_cache.token_type,
            "issued_at": self._token_cache.issued_at.isoformat(),
            "expires_at": self._token_cache.expires_at.isoformat(),
            "expires_in": int(expires_in),
            "refresh_count": self._token_refresh_count,
            "last_refresh_attempt": self._last_refresh_attempt.isoformat()
            if self._last_refresh_attempt
            else None,
            "persistent_cache_enabled": self.enable_persistent_cache,
        }

    async def ensure_valid_token(
        self, min_validity_seconds: int = TOKEN_EXPIRY_WARNING_SECONDS
    ) -> str:
        """
        Ensure we have a valid token with minimum remaining validity.

        Proactively refreshes token if it expires within the specified time.

        Args:
            min_validity_seconds: Minimum seconds of validity required

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If token cannot be obtained
        """
        async with self._token_lock:
            # Check if we need a new token
            needs_refresh = True

            if self._token_cache:
                # Ensure both datetimes are timezone-aware for comparison
                current_time = datetime.now(UTC)
                token_expires_at = self._token_cache.expires_at
                if token_expires_at.tzinfo is None:
                    token_expires_at = token_expires_at.replace(tzinfo=UTC)

                time_until_expiry = (token_expires_at - current_time).total_seconds()
                needs_refresh = time_until_expiry <= min_validity_seconds

                if not needs_refresh:
                    logger.debug(
                        f"Token valid for {int(time_until_expiry)} more seconds"
                    )
                    return self._token_cache.access_token

            logger.info(
                f"Token needs refresh (minimum validity: {min_validity_seconds}s)"
            )
            return await self._refresh_token()

    async def validate_credentials(self) -> bool:
        """
        Validate OAuth credentials by attempting to get a fresh token.

        This clears any cached tokens to force a fresh authentication attempt.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            logger.info("Validating OAuth credentials")

            # Clear any cached tokens to force fresh authentication
            await self.invalidate_token()

            # Try to get a fresh token
            await self.get_token()
            logger.info("OAuth credentials validated successfully")
            return True
        except AuthenticationError as e:
            logger.warning(f"OAuth credential validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during credential validation: {e}")
            return False
