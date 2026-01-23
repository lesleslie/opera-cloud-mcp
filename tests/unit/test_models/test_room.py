"""Unit tests for room models.

Tests for models in opera_cloud_mcp/models/room.py
"""

from datetime import date
import pytest

from opera_cloud_mcp.models.room import Room, RoomStatus, RoomAvailability


class TestRoom:
    """Test Room model."""

    def test_room_creation(self):
        """Test creating a Room with all fields."""
        room = Room(
            room_number="101",
            room_type="DELUXE",
            room_class="SUITE",
            floor="1",
            building="MAIN",
            bed_type="KING",
            max_occupancy=4,
            smoking_allowed=False,
            accessible=True
        )
        assert room.room_number == "101"
        assert room.room_type == "DELUXE"
        assert room.room_class == "SUITE"
        assert room.floor == "1"
        assert room.building == "MAIN"
        assert room.bed_type == "KING"
        assert room.max_occupancy == 4
        assert room.smoking_allowed is False
        assert room.accessible is True

    def test_room_creation_with_alias(self):
        """Test creating a Room using field aliases."""
        room = Room(
            roomNumber="202",
            roomType="STANDARD",
            roomClass="GUEST",
            floor="2",
            bedType="QUEEN",
            maxOccupancy=2
        )
        assert room.room_number == "202"
        assert room.room_type == "STANDARD"
        assert room.room_class == "GUEST"
        assert room.bed_type == "QUEEN"
        assert room.max_occupancy == 2

    def test_room_optional_fields(self):
        """Test creating a Room without optional fields."""
        room = Room(
            room_number="303",
            room_type="BASIC",
            room_class="GUEST",
            max_occupancy=2
        )
        assert room.floor is None
        assert room.building is None
        assert room.bed_type is None

    def test_room_default_smoking_allowed(self):
        """Test Room default smoking_allowed is False."""
        room = Room(
            room_number="404",
            room_type="BASIC",
            room_class="GUEST",
            max_occupancy=2
        )
        assert room.smoking_allowed is False

    def test_room_default_accessible(self):
        """Test Room default accessible is False."""
        room = Room(
            room_number="505",
            room_type="BASIC",
            room_class="GUEST",
            max_occupancy=2
        )
        assert room.accessible is False


class TestRoomStatus:
    """Test RoomStatus model."""

    def test_room_status_creation(self):
        """Test creating a RoomStatus with all fields."""
        room_status = RoomStatus(
            room_number="101",
            housekeeping_status="CLEAN",
            front_office_status="OCCUPIED",
            out_of_order=False,
            out_of_inventory=False,
            maintenance_required=False
        )
        assert room_status.room_number == "101"
        assert room_status.housekeeping_status == "CLEAN"
        assert room_status.front_office_status == "OCCUPIED"
        assert room_status.out_of_order is False
        assert room_status.out_of_inventory is False
        assert room_status.maintenance_required is False

    def test_room_status_with_alias(self):
        """Test creating a RoomStatus using field aliases."""
        room_status = RoomStatus(
            roomNumber="202",
            housekeepingStatus="DIRTY",
            frontOfficeStatus="VACANT",
            outOfOrder=True,
            outOfInventory=False,
            maintenanceRequired=True
        )
        assert room_status.room_number == "202"
        assert room_status.housekeeping_status == "DIRTY"
        assert room_status.front_office_status == "VACANT"
        assert room_status.out_of_order is True
        assert room_status.maintenance_required is True

    def test_room_status_default_flags(self):
        """Test RoomStatus default boolean flags are False."""
        room_status = RoomStatus(
            room_number="303",
            housekeeping_status="CLEAN",
            front_office_status="VACANT"
        )
        assert room_status.out_of_order is False
        assert room_status.out_of_inventory is False
        assert room_status.maintenance_required is False

    def test_room_status_maintenance_mode(self):
        """Test RoomStatus with maintenance required."""
        room_status = RoomStatus(
            room_number="404",
            housekeeping_status="CLEAN",
            front_office_status="OUT_OF_ORDER",
            out_of_order=True,
            maintenance_required=True
        )
        assert room_status.out_of_order is True
        assert room_status.maintenance_required is True


class TestRoomAvailability:
    """Test RoomAvailability model."""

    def test_room_availability_creation(self):
        """Test creating a RoomAvailability with all fields."""
        availability = RoomAvailability(
            date=date(2024, 12, 25),
            room_type="DELUXE",
            available_rooms=10,
            total_rooms=20,
            rate_code="RACK",
            rate_amount=199.99
        )
        assert availability.date == date(2024, 12, 25)
        assert availability.room_type == "DELUXE"
        assert availability.available_rooms == 10
        assert availability.total_rooms == 20
        assert availability.rate_code == "RACK"
        assert availability.rate_amount == 199.99

    def test_room_availability_with_alias(self):
        """Test creating a RoomAvailability using field aliases."""
        availability = RoomAvailability(
            date=date(2024, 12, 26),
            roomType="STANDARD",
            availableRooms=5,
            totalRooms=15,
            rateCode="DISCOUNT",
            rateAmount=149.50
        )
        assert availability.date == date(2024, 12, 26)
        assert availability.room_type == "STANDARD"
        assert availability.available_rooms == 5
        assert availability.total_rooms == 15
        assert availability.rate_code == "DISCOUNT"
        assert availability.rate_amount == 149.50

    def test_room_availability_without_rate(self):
        """Test creating a RoomAvailability without rate information."""
        availability = RoomAvailability(
            date=date(2024, 12, 27),
            room_type="BASIC",
            available_rooms=8,
            total_rooms=10
        )
        assert availability.rate_code is None
        assert availability.rate_amount is None

    def test_room_availability_sold_out(self):
        """Test RoomAvailability when sold out."""
        availability = RoomAvailability(
            date=date(2024, 12, 31),
            room_type="DELUXE",
            available_rooms=0,
            total_rooms=20
        )
        assert availability.available_rooms == 0
        assert availability.total_rooms == 20

    def test_room_availability_full_availability(self):
        """Test RoomAvailability when fully available."""
        availability = RoomAvailability(
            date=date(2024, 11, 1),
            room_type="STANDARD",
            available_rooms=50,
            total_rooms=50
        )
        assert availability.available_rooms == 50
        assert availability.total_rooms == 50
