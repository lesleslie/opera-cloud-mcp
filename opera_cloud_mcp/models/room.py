"""
Room and inventory data models for OPERA Cloud MCP server.

Provides Pydantic models for room information, availability,
and housekeeping entities.
"""

from typing import TYPE_CHECKING

from pydantic import Field

from opera_cloud_mcp.models.common import OperaBaseModel

if TYPE_CHECKING:
    from datetime import date


class Room(OperaBaseModel):
    """Room information model."""

    room_number: str = Field(alias="roomNumber")
    room_type: str = Field(alias="roomType")
    room_class: str = Field(alias="roomClass")
    floor: str | None = None
    building: str | None = None
    bed_type: str | None = Field(None, alias="bedType")
    max_occupancy: int = Field(alias="maxOccupancy")
    smoking_allowed: bool = Field(False, alias="smokingAllowed")
    accessible: bool = False


class RoomStatus(OperaBaseModel):
    """Room status model."""

    room_number: str = Field(alias="roomNumber")
    housekeeping_status: str = Field(alias="housekeepingStatus")
    front_office_status: str = Field(alias="frontOfficeStatus")
    out_of_order: bool = Field(False, alias="outOfOrder")
    out_of_inventory: bool = Field(False, alias="outOfInventory")
    maintenance_required: bool = Field(False, alias="maintenanceRequired")


class RoomAvailability(OperaBaseModel):
    """Room availability model."""

    date: date
    room_type: str = Field(alias="roomType")
    available_rooms: int = Field(alias="availableRooms")
    total_rooms: int = Field(alias="totalRooms")
    rate_code: str | None = Field(None, alias="rateCode")
    rate_amount: float | None = Field(None, alias="rateAmount")
