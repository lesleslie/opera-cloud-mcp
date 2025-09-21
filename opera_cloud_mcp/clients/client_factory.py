"""
Client factory for managing and creating OPERA Cloud API clients.

This module provides centralized client creation and management for all
OPERA Cloud API domains with shared resources and configuration.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Protocol

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler
from opera_cloud_mcp.auth.secure_oauth_handler import SecureOAuthHandler
from opera_cloud_mcp.config.settings import Settings
from opera_cloud_mcp.utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class APIClientProtocol(Protocol):
    """Protocol for API client classes."""

    def __init__(
        self,
        auth_handler: OAuthHandler | SecureOAuthHandler,
        hotel_id: str,
        settings: Settings,
        **kwargs: Any,
    ) -> None: ...


class ClientFactory:
    """
    Factory for creating and managing OPERA Cloud API clients.

    Provides centralized client creation with shared resources like
    connection pools, authentication handlers, and configuration.
    """

    def __init__(
        self,
        auth_handler: OAuthHandler | SecureOAuthHandler,
        settings: Settings,
        hotel_id: str | None = None,
    ):
        """
        Initialize the client factory.

        Args:
            auth_handler: OAuth2 authentication handler
            settings: Application settings
            hotel_id: Default hotel ID for all clients
        """
        self.auth_handler = auth_handler
        self.settings = settings
        self.default_hotel_id = hotel_id

        # Client registry
        self._client_registry: dict[str, type[APIClientProtocol]] = {}
        self._client_instances: dict[str, APIClientProtocol] = {}

        # Shared resources
        self._connection_pool_initialized = False
        self._shutdown_event = asyncio.Event()

        logger.info(
            "ClientFactory initialized",
            extra={
                "default_hotel_id": self.default_hotel_id,
                "registered_clients": len(self._client_registry),
            },
        )

    @classmethod
    def create_secure_factory(
        cls,
        client_id: str,
        client_secret: str,
        token_url: str,
        settings: Settings,
        hotel_id: str | None = None,
        enable_security_monitoring: bool = True,
        enable_rate_limiting: bool = True,
        enable_token_binding: bool = True,
        cache_dir: Path | None = None,
        master_key: bytes | None = None,
    ) -> "ClientFactory":
        """
        Create a ClientFactory with enhanced OAuth2 security components.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            token_url: OAuth token endpoint URL
            settings: Application settings
            hotel_id: Default hotel ID for all clients
            enable_security_monitoring: Enable comprehensive security monitoring
            enable_rate_limiting: Enable rate limiting and abuse detection
            enable_token_binding: Enable token binding for enhanced security
            cache_dir: Custom cache directory for secure token storage
            master_key: Master encryption key for token security

        Returns:
            ClientFactory instance with SecureOAuthHandler
        """
        # Create SecureOAuthHandler with enhanced security features
        secure_auth_handler = SecureOAuthHandler(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
            retry_backoff=settings.retry_backoff,
            enable_persistent_cache=True,
            cache_dir=cache_dir,
            enable_security_monitoring=enable_security_monitoring,
            enable_rate_limiting=enable_rate_limiting,
            enable_token_binding=enable_token_binding,
            master_key=master_key,
        )

        logger.info(
            "Created secure ClientFactory with enhanced OAuth2 security",
            extra={
                "security_monitoring": enable_security_monitoring,
                "rate_limiting": enable_rate_limiting,
                "token_binding": enable_token_binding,
                "secure_cache": cache_dir is not None,
            },
        )

        return cls(
            auth_handler=secure_auth_handler, settings=settings, hotel_id=hotel_id
        )

    @classmethod
    def create_basic_factory(
        cls,
        client_id: str,
        client_secret: str,
        token_url: str,
        settings: Settings,
        hotel_id: str | None = None,
        cache_dir: Path | None = None,
    ) -> "ClientFactory":
        """
        Create a ClientFactory with basic OAuth2 authentication.

        Use this for development/testing environments where enhanced security
        features are not required.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            token_url: OAuth token endpoint URL
            settings: Application settings
            hotel_id: Default hotel ID for all clients
            cache_dir: Custom cache directory for token storage

        Returns:
            ClientFactory instance with basic OAuthHandler
        """
        # Create basic OAuthHandler
        basic_auth_handler = OAuthHandler(
            client_id=client_id,
            client_secret=client_secret,
            token_url=token_url,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
            retry_backoff=settings.retry_backoff,
            enable_persistent_cache=True,
            cache_dir=cache_dir,
        )

        logger.info(
            "Created basic ClientFactory with standard OAuth2 authentication",
            extra={
                "secure_cache": cache_dir is not None,
            },
        )

        return cls(
            auth_handler=basic_auth_handler, settings=settings, hotel_id=hotel_id
        )

    def register_client(
        self, client_name: str, client_class: type[APIClientProtocol]
    ) -> None:
        """
        Register a client class with the factory.

        Args:
            client_name: Unique name for the client
            client_class: Client class to register
        """
        if client_name in self._client_registry:
            logger.warning(f"Overriding existing client registration: {client_name}")

        self._client_registry[client_name] = client_class
        logger.info(f"Registered client: {client_name}")

    async def get_client(
        self, client_name: str, hotel_id: str | None = None, **kwargs: Any
    ) -> APIClientProtocol:
        """
        Get or create a client instance.

        Args:
            client_name: Name of the registered client
            hotel_id: Hotel ID for the client (overrides default)
            **kwargs: Additional arguments for client initialization

        Returns:
            Client instance

        Raises:
            ConfigurationError: If client not registered or invalid configuration
        """
        if client_name not in self._client_registry:
            raise ConfigurationError(f"Client not registered: {client_name}")

        # Use provided hotel_id or default
        effective_hotel_id = hotel_id or self.default_hotel_id
        if not effective_hotel_id:
            raise ConfigurationError("No hotel ID provided and no default set")

        # Create cache key including hotel_id for multi-hotel support
        cache_key = f"{client_name}:{effective_hotel_id}"

        # Return cached instance if available
        if cache_key in self._client_instances:
            return self._client_instances[cache_key]

        # Create new instance
        client_class = self._client_registry[client_name]

        try:
            client_instance = client_class(
                auth_handler=self.auth_handler,
                hotel_id=effective_hotel_id,
                settings=self.settings,
                **kwargs,
            )

            # Cache the instance
            self._client_instances[cache_key] = client_instance

            logger.info(
                "Created client instance",
                extra={
                    "client_name": client_name,
                    "hotel_id": effective_hotel_id,
                    "cache_key": cache_key,
                },
            )

            return client_instance

        except Exception as e:
            logger.error(
                "Failed to create client instance",
                extra={
                    "client_name": client_name,
                    "hotel_id": effective_hotel_id,
                    "error": str(e),
                },
            )
            raise ConfigurationError(
                f"Failed to create {client_name} client: {e}"
            ) from e

    def list_registered_clients(self) -> dict[str, str]:
        """
        Get list of registered clients.

        Returns:
            Dictionary of client names and their class names
        """
        return {name: cls.__name__ for name, cls in self._client_registry.items()}

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on all active client instances.

        Returns:
            Health status information for all clients
        """
        health_results: dict[str, Any] = {
            "factory_status": "healthy",
            "registered_clients": len(self._client_registry),
            "active_instances": len(self._client_instances),
            "client_health": {},
        }

        # Check health of all active instances
        for cache_key, client in self._client_instances.items():
            try:
                if hasattr(client, "health_check"):
                    client_health = await client.health_check()
                    health_results["client_health"][cache_key] = client_health
                else:
                    health_results["client_health"][cache_key] = {
                        "status": "no_health_check",
                        "message": "Client doesn't support health checks",
                    }
            except Exception as e:
                health_results["client_health"][cache_key] = {
                    "status": "error",
                    "error": str(e),
                }

        # Determine overall health
        client_health_dict: dict[str, Any] = health_results["client_health"]
        unhealthy_clients = [
            key
            for key, health in client_health_dict.items()
            if health.get("status") not in ("healthy", "no_health_check")
        ]

        if unhealthy_clients:
            health_results["factory_status"] = "degraded"
            health_results["unhealthy_clients"] = unhealthy_clients

        return health_results

    async def cleanup(self) -> None:
        """Clean up all client instances and shared resources."""
        logger.info("Starting client factory cleanup")

        # Signal shutdown to all clients
        self._shutdown_event.set()

        # Clean up all client instances
        cleanup_tasks = []
        for cache_key, client in self._client_instances.items():
            if hasattr(client, "close"):
                task = asyncio.create_task(client.close(), name=f"cleanup-{cache_key}")
                cleanup_tasks.append(task)

        if cleanup_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True), timeout=30.0
                )
            except TimeoutError:
                logger.warning("Some clients failed to cleanup within timeout")

        self._client_instances.clear()
        logger.info("Client factory cleanup completed")


# Global factory instance (initialized by application)
_factory_instance: ClientFactory | None = None


def get_client_factory() -> ClientFactory:
    """
    Get the global client factory instance.

    Returns:
        ClientFactory instance

    Raises:
        RuntimeError: If factory not initialized
    """
    if _factory_instance is None:
        raise RuntimeError(
            "Client factory not initialized. Call initialize_client_factory() first."
        )
    return _factory_instance


def initialize_client_factory(
    auth_handler: OAuthHandler, settings: Settings, hotel_id: str | None = None
) -> ClientFactory:
    """
    Initialize the global client factory.

    Args:
        auth_handler: OAuth2 authentication handler
        settings: Application settings
        hotel_id: Default hotel ID

    Returns:
        Initialized ClientFactory instance
    """
    global _factory_instance

    if _factory_instance is not None:
        logger.warning(
            "Client factory already initialized, replacing existing instance"
        )

    _factory_instance = ClientFactory(
        auth_handler=auth_handler, settings=settings, hotel_id=hotel_id
    )

    return _factory_instance


async def cleanup_client_factory() -> None:
    """Clean up the global client factory."""
    global _factory_instance

    if _factory_instance is not None:
        await _factory_instance.cleanup()
        _factory_instance = None
