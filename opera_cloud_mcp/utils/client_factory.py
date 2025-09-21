"""
Client factory utilities for OPERA Cloud MCP.

Provides factory functions for creating API clients with proper
authentication and configuration, avoiding circular imports.
"""

from opera_cloud_mcp.auth.oauth_handler import OAuthHandler
from opera_cloud_mcp.clients.api_clients.crm import CRMClient
from opera_cloud_mcp.clients.api_clients.reservations import ReservationsClient
from opera_cloud_mcp.config.settings import Settings, get_settings

# Global instances to avoid recreation
_settings: Settings | None = None
_oauth_handler: OAuthHandler | None = None


def get_oauth_handler() -> OAuthHandler:
    """
    Get the global OAuth handler instance.

    Returns:
        OAuthHandler instance
    """
    global _oauth_handler, _settings

    if _oauth_handler is None:
        if _settings is None:
            _settings = get_settings()

        _oauth_handler = OAuthHandler(
            client_id=_settings.opera_client_id,
            client_secret=_settings.opera_client_secret,
            token_url=_settings.opera_token_url,
        )

    return _oauth_handler


def create_reservations_client(hotel_id: str | None = None) -> ReservationsClient:
    """
    Create a ReservationsClient instance.

    Args:
        hotel_id: Hotel ID for the client (uses default if not provided)

    Returns:
        ReservationsClient instance
    """
    settings = get_settings()
    auth_handler = get_oauth_handler()

    if hotel_id is None:
        hotel_id = settings.default_hotel_id

    if hotel_id is None:
        raise ValueError("Hotel ID must be provided or set in settings")
    return ReservationsClient(
        auth_handler=auth_handler, hotel_id=hotel_id, settings=settings
    )


def create_crm_client(hotel_id: str | None = None) -> CRMClient:
    """
    Create a CRMClient instance.

    Args:
        hotel_id: Hotel ID for the client (uses default if not provided)

    Returns:
        CRMClient instance
    """
    settings = get_settings()
    auth_handler = get_oauth_handler()

    if hotel_id is None:
        hotel_id = settings.default_hotel_id

    if hotel_id is None:
        raise ValueError("Hotel ID must be provided or set in settings")
    return CRMClient(auth_handler=auth_handler, hotel_id=hotel_id, settings=settings)


def create_inventory_client(hotel_id: str | None = None):
    """
    Create an InventoryClient instance.

    Args:
        hotel_id: Hotel ID for the client (uses default if not provided)

    Returns:
        InventoryClient instance
    """
    from opera_cloud_mcp.clients.api_clients.inventory import InventoryClient

    settings = get_settings()
    auth_handler = get_oauth_handler()

    if hotel_id is None:
        hotel_id = settings.default_hotel_id

    return InventoryClient(
        auth_handler=auth_handler, hotel_id=hotel_id, settings=settings
    )


def create_front_office_client(hotel_id: str | None = None):
    """
    Create a FrontOfficeClient instance.

    Args:
        hotel_id: Hotel ID for the client (uses default if not provided)

    Returns:
        FrontOfficeClient instance
    """
    from opera_cloud_mcp.clients.api_clients.front_office import FrontOfficeClient

    settings = get_settings()
    auth_handler = get_oauth_handler()

    if hotel_id is None:
        hotel_id = settings.default_hotel_id

    return FrontOfficeClient(
        auth_handler=auth_handler, hotel_id=hotel_id, settings=settings
    )


def create_cashier_client(hotel_id: str | None = None):
    """
    Create a CashierClient instance.

    Args:
        hotel_id: Hotel ID for the client (uses default if not provided)

    Returns:
        CashierClient instance
    """
    from opera_cloud_mcp.clients.api_clients.cashier import CashierClient

    settings = get_settings()
    auth_handler = get_oauth_handler()

    if hotel_id is None:
        hotel_id = settings.default_hotel_id

    return CashierClient(
        auth_handler=auth_handler, hotel_id=hotel_id, settings=settings
    )


def create_housekeeping_client(hotel_id: str | None = None):
    """
    Create a HousekeepingClient instance.

    Args:
        hotel_id: Hotel ID for the client (uses default if not provided)

    Returns:
        HousekeepingClient instance
    """
    from opera_cloud_mcp.clients.api_clients.housekeeping import HousekeepingClient

    settings = get_settings()
    auth_handler = get_oauth_handler()

    if hotel_id is None:
        hotel_id = settings.default_hotel_id

    return HousekeepingClient(
        auth_handler=auth_handler, hotel_id=hotel_id, settings=settings
    )


def create_activities_client(hotel_id: str | None = None):
    """
    Create an ActivitiesClient instance.

    Args:
        hotel_id: Hotel ID for the client (uses default if not provided)

    Returns:
        ActivitiesClient instance
    """
    from opera_cloud_mcp.clients.api_clients.activities import ActivitiesClient

    settings = get_settings()
    auth_handler = get_oauth_handler()

    if hotel_id is None:
        hotel_id = settings.default_hotel_id

    return ActivitiesClient(
        auth_handler=auth_handler, hotel_id=hotel_id, settings=settings
    )
