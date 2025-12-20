"""
Room and inventory management tools for OPERA Cloud MCP.

Provides MCP tools for managing room status, availability, housekeeping,
and inventory operations through the OPERA Cloud Inventory and Housekeeping APIs.
"""

from datetime import date
from typing import Any

from fastmcp import FastMCP

from opera_cloud_mcp.utils.client_factory import (
    create_housekeeping_client,
    create_inventory_client,
)
from opera_cloud_mcp.utils.exceptions import ValidationError


def _validate_get_room_status_params(hotel_id: str | None) -> None:
    """Validate get room status parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _build_status_params(
    room_number: str | None,
    floor: str | None,
    room_type: str | None,
    status_filter: str | None,
    date_for: str | None,
) -> dict[str, Any]:
    """Build room status parameters dictionary."""
    status_params = {}
    if room_number:
        status_params["roomNumber"] = room_number
    if floor:
        status_params["floor"] = floor
    if room_type:
        status_params["roomType"] = room_type
    if status_filter:
        status_params["status"] = status_filter
    if date_for:
        status_params["date"] = date_for
    else:
        status_params["date"] = date.today().isoformat()

    return status_params


def _validate_update_room_status_params(hotel_id: str | None, new_status: str) -> None:
    """Validate update room status parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    valid_statuses = ["clean", "dirty", "out_of_order", "maintenance", "inspected"]
    if new_status not in valid_statuses:
        raise ValidationError(
            f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )


def _build_update_data(
    room_number: str,
    new_status: str,
    notes: str | None,
    maintenance_required: bool,
    estimated_completion: str | None,
) -> dict[str, Any]:
    """Build room update data dictionary."""
    return {
        "roomNumber": room_number,
        "status": new_status,
        "notes": notes,
        "maintenanceRequired": maintenance_required,
        "estimatedCompletion": estimated_completion,
        "updatedBy": "mcp_agent",
    }


def _validate_check_room_availability_dates(
    arrival_date: str, departure_date: str
) -> None:
    """Validate room availability dates."""
    try:
        arr_date = date.fromisoformat(arrival_date)
        dep_date = date.fromisoformat(departure_date)
        if arr_date >= dep_date:
            raise ValidationError("departure_date must be after arrival_date")
    except ValueError as e:
        raise ValidationError(f"Invalid date format: {e}") from e


def _validate_check_room_availability_params(
    hotel_id: str | None, arrival_date: str, departure_date: str, number_of_rooms: int
) -> None:
    """Validate check room availability parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    _validate_check_room_availability_dates(arrival_date, departure_date)

    if number_of_rooms < 1:
        raise ValidationError("number_of_rooms must be at least 1")


def _build_availability_params(
    arrival_date: str,
    departure_date: str,
    number_of_rooms: int,
    room_type: str | None,
    rate_code: str | None,
) -> dict[str, Any]:
    """Build availability parameters dictionary."""
    availability_params = {
        "arrivalDate": arrival_date,
        "departureDate": departure_date,
        "numberOfRooms": number_of_rooms,
    }

    if room_type:
        availability_params["roomType"] = room_type
    if rate_code:
        availability_params["rateCode"] = rate_code

    return availability_params


def _validate_get_housekeeping_tasks_params(hotel_id: str | None) -> None:
    """Validate get housekeeping tasks parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _build_task_params(
    task_date: str | None,
    room_number: str | None,
    task_status: str | None,
    assigned_to: str | None,
) -> dict[str, Any]:
    """Build housekeeping task parameters dictionary."""
    task_params = {}
    if task_date:
        task_params["date"] = task_date
    else:
        task_params["date"] = date.today().isoformat()

    if room_number:
        task_params["roomNumber"] = room_number
    if task_status:
        task_params["status"] = task_status
    if assigned_to:
        task_params["assignedTo"] = assigned_to

    return task_params


def _validate_create_housekeeping_task_params(
    hotel_id: str | None, task_type: str, priority: str
) -> None:
    """Validate create housekeeping task parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    valid_task_types = ["cleaning", "maintenance", "inspection", "deep_clean"]
    if task_type not in valid_task_types:
        raise ValidationError(
            f"Invalid task_type. Must be one of: {', '.join(valid_task_types)}"
        )

    valid_priorities = ["low", "normal", "high", "urgent"]
    if priority not in valid_priorities:
        raise ValidationError(
            f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
        )


def _build_task_data(
    room_number: str,
    task_type: str,
    priority: str,
    description: str | None,
    assigned_to: str | None,
    estimated_duration: int | None,
    due_date: str | None,
) -> dict[str, Any]:
    """Build housekeeping task data dictionary."""
    return {
        "roomNumber": room_number,
        "taskType": task_type,
        "priority": priority,
        "description": description,
        "assignedTo": assigned_to,
        "estimatedDuration": estimated_duration,
        "dueDate": due_date,
        "createdBy": "mcp_agent",
    }


def _validate_create_maintenance_request_params(
    hotel_id: str | None, priority: str
) -> None:
    """Validate create maintenance request parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    valid_priorities = ["low", "normal", "high", "urgent"]
    if priority not in valid_priorities:
        raise ValidationError(
            f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
        )


def _build_maintenance_data(
    room_number: str,
    issue_description: str,
    priority: str,
    category: str | None,
    estimated_cost: float | None,
    vendor_required: bool,
) -> dict[str, Any]:
    """Build maintenance request data dictionary."""
    return {
        "roomNumber": room_number,
        "issueDescription": issue_description,
        "priority": priority,
        "category": category,
        "estimatedCost": estimated_cost,
        "vendorRequired": vendor_required,
        "reportedBy": "mcp_agent",
    }


def _validate_get_inventory_status_params(hotel_id: str | None) -> None:
    """Validate get inventory status parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _build_inventory_params(
    item_category: str | None,
    location: str | None,
    low_stock_only: bool,
) -> dict[str, Any]:
    """Build inventory status parameters dictionary."""
    inventory_params: dict[str, Any] = {}
    if item_category:
        inventory_params["category"] = item_category
    if location:
        inventory_params["location"] = location
    if low_stock_only:
        inventory_params["lowStockOnly"] = True

    return inventory_params


def _validate_update_inventory_stock_params(
    hotel_id: str | None, adjustment_reason: str
) -> None:
    """Validate update inventory stock parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")

    valid_reasons = [
        "received",
        "used",
        "damaged",
        "lost",
        "transferred",
        "counted",
    ]
    if adjustment_reason not in valid_reasons:
        raise ValidationError(
            f"Invalid adjustment_reason. Must be one of: {', '.join(valid_reasons)}"
        )


def _build_adjustment_data(
    item_id: str,
    quantity_adjustment: int,
    adjustment_reason: str,
    location: str | None,
    notes: str | None,
) -> dict[str, Any]:
    """Build inventory adjustment data dictionary."""
    return {
        "itemId": item_id,
        "quantityAdjustment": quantity_adjustment,
        "adjustmentReason": adjustment_reason,
        "location": location,
        "notes": notes,
        "adjustedBy": "mcp_agent",
    }


def _validate_get_cleaning_schedule_params(hotel_id: str | None) -> None:
    """Validate get cleaning schedule parameters."""
    if hotel_id == "":
        raise ValidationError("hotel_id cannot be empty string")


def _build_schedule_params(
    schedule_date: str | None,
    room_type: str | None,
    staff_member: str | None,
) -> dict[str, Any]:
    """Build cleaning schedule parameters dictionary."""
    schedule_params = {}
    if schedule_date:
        schedule_params["date"] = schedule_date
    else:
        schedule_params["date"] = date.today().isoformat()

    if room_type:
        schedule_params["roomType"] = room_type
    if staff_member:
        schedule_params["staffMember"] = staff_member

    return schedule_params


def register_room_status_tool(app: FastMCP):
    """Register room status tool."""

    @app.tool()
    async def get_room_status(
        hotel_id: str | None = None,
        room_number: str | None = None,
        floor: str | None = None,
        room_type: str | None = None,
        status_filter: str | None = None,
        date_for: str | None = None,
    ) -> dict[str, Any]:
        """
        Get current room status information.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            room_number: Specific room number to check
            floor: Filter by floor number
            room_type: Filter by room type
            status_filter: Filter by status (clean, dirty, out_of_order, etc.)
            date_for: Date for status check in YYYY-MM-DD format (defaults to today)

        Returns:
            Dictionary containing room status information
        """
        _validate_get_room_status_params(hotel_id)

        client = create_housekeeping_client(hotel_id=hotel_id)

        status_params = _build_status_params(
            room_number, floor, room_type, status_filter, date_for
        )

        response = await client.get_room_status(status_params)

        if response.success:
            return {
                "success": True,
                "room_status": response.data.get("rooms", []),
                "summary": response.data.get("summary", {}),
                "hotel_id": hotel_id,
                "date": status_params["date"],
            }
        return {"success": False, "error": response.error, "hotel_id": hotel_id}


def register_update_room_status_tool(app: FastMCP):
    """Register update room status tool."""

    @app.tool()
    async def update_room_status(
        room_number: str,
        new_status: str,
        hotel_id: str | None = None,
        notes: str | None = None,
        maintenance_required: bool = False,
        estimated_completion: str | None = None,
    ) -> dict[str, Any]:
        """
        Update the status of a specific room.

        Args:
            room_number: Room number to update
            new_status: New room status (clean, dirty, out_of_order, maintenance)
            hotel_id: Hotel identifier (uses default if not provided)
            notes: Optional notes about the status change
            maintenance_required: Whether maintenance is required
            estimated_completion: Estimated completion time for maintenance/cleaning

        Returns:
            Dictionary containing status update confirmation
        """
        _validate_update_room_status_params(hotel_id, new_status)

        client = create_housekeeping_client(hotel_id=hotel_id)

        update_data = _build_update_data(
            room_number,
            new_status,
            notes,
            maintenance_required,
            estimated_completion,
        )

        response = await client.update_room_status(update_data)

        if response.success:
            return {
                "success": True,
                "room_status": response.data,
                "room_number": room_number,
                "new_status": new_status,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "room_number": room_number,
            "hotel_id": hotel_id,
        }


def register_check_room_availability_tool(app: FastMCP):
    """Register check room availability tool."""

    @app.tool()
    async def check_room_availability(
        arrival_date: str,
        departure_date: str,
        hotel_id: str | None = None,
        room_type: str | None = None,
        number_of_rooms: int = 1,
        rate_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Check room availability for specific dates.

        Args:
            arrival_date: Arrival date in YYYY-MM-DD format
            departure_date: Departure date in YYYY-MM-DD format
            hotel_id: Hotel identifier (uses default if not provided)
            room_type: Specific room type to check
            number_of_rooms: Number of rooms needed
            rate_code: Specific rate code to check

        Returns:
            Dictionary containing availability information
        """
        _validate_check_room_availability_params(
            hotel_id, arrival_date, departure_date, number_of_rooms
        )

        client = create_inventory_client(hotel_id=hotel_id)

        availability_params = _build_availability_params(
            arrival_date, departure_date, number_of_rooms, room_type, rate_code
        )

        response = await client.check_availability(availability_params)

        if response.success:
            return {
                "success": True,
                "availability": response.data.get("availability", []),
                "search_criteria": availability_params,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "search_criteria": availability_params,
            "hotel_id": hotel_id,
        }


def register_housekeeping_tasks_tool(app: FastMCP):
    """Register housekeeping tasks tool."""

    @app.tool()
    async def get_housekeeping_tasks(
        hotel_id: str | None = None,
        task_date: str | None = None,
        room_number: str | None = None,
        task_status: str | None = None,
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        """
        Get housekeeping tasks for rooms.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            task_date: Date for tasks in YYYY-MM-DD format (defaults to today)
            room_number: Filter by specific room number
            task_status: Filter by task status (pending, in_progress, completed)
            assigned_to: Filter by staff member assigned

        Returns:
            Dictionary containing housekeeping tasks
        """
        _validate_get_housekeeping_tasks_params(hotel_id)

        client = create_housekeeping_client(hotel_id=hotel_id)

        task_params = _build_task_params(
            task_date, room_number, task_status, assigned_to
        )

        response = await client.get_housekeeping_tasks(task_params)

        if response.success:
            return {
                "success": True,
                "tasks": response.data.get("tasks", []),
                "summary": response.data.get("summary", {}),
                "hotel_id": hotel_id,
                "date": task_params["date"],
            }
        return {"success": False, "error": response.error, "hotel_id": hotel_id}


def register_create_housekeeping_task_tool(app: FastMCP):
    """Register create housekeeping task tool."""

    @app.tool()
    async def create_housekeeping_task(
        room_number: str,
        task_type: str,
        priority: str = "normal",
        hotel_id: str | None = None,
        description: str | None = None,
        assigned_to: str | None = None,
        estimated_duration: int | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new housekeeping task for a room.

        Args:
            room_number: Room number for the task
            task_type: Type of task (cleaning, maintenance, inspection, etc.)
            priority: Task priority (low, normal, high, urgent)
            hotel_id: Hotel identifier (uses default if not provided)
            description: Detailed description of the task
            assigned_to: Staff member assigned to the task
            estimated_duration: Estimated time to complete in minutes
            due_date: Due date in YYYY-MM-DD format

        Returns:
            Dictionary containing task creation confirmation
        """
        _validate_create_housekeeping_task_params(hotel_id, task_type, priority)

        client = create_housekeeping_client(hotel_id=hotel_id)

        task_data = _build_task_data(
            room_number,
            task_type,
            priority,
            description,
            assigned_to,
            estimated_duration,
            due_date,
        )

        response = await client.create_housekeeping_task(task_data)

        if response.success:
            return {
                "success": True,
                "task": response.data,
                "room_number": room_number,
                "task_type": task_type,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "room_number": room_number,
            "hotel_id": hotel_id,
        }


def register_complete_housekeeping_task_tool(app: FastMCP):
    """Register complete housekeeping task tool."""

    @app.tool()
    async def complete_housekeeping_task(
        task_id: str,
        completed_by: str,
        hotel_id: str | None = None,
        notes: str | None = None,
        completion_time: str | None = None,
    ) -> dict[str, Any]:
        """
        Mark a housekeeping task as completed.

        Args:
            task_id: Task identifier
            completed_by: Staff member who completed the task
            hotel_id: Hotel identifier (uses default if not provided)
            notes: Additional notes about task completion
            completion_time: Completion time in HH:MM format (defaults to current time)

        Returns:
            Dictionary containing task completion confirmation
        """
        _validate_create_housekeeping_task_params(hotel_id, "completion", "normal")

        client = create_housekeeping_client(hotel_id=hotel_id)

        completion_data = _build_task_data(
            task_id, completed_by, "normal", notes, None, 30, completion_time
        )

        response = await client.complete_housekeeping_task(completion_data)

        if response.success:
            return {
                "success": True,
                "completed_task": response.data,
                "task_id": task_id,
                "completed_by": completed_by,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "task_id": task_id,
            "hotel_id": hotel_id,
        }


def register_inventory_levels_tool(app: FastMCP):
    """Register inventory levels tool."""

    @app.tool()
    async def get_inventory_levels(
        hotel_id: str | None = None,
        item_category: str | None = None,
        minimum_stock_level: int | None = None,
        include_low_stock: bool = True,
    ) -> dict[str, Any]:
        """
        Get current inventory levels for hotel supplies and amenities.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            item_category: Filter by item category (linen, amenity,
                cleaning_supply, etc.)
            minimum_stock_level: Minimum stock level to include
            include_low_stock: Include items with low stock alerts

        Returns:
            Dictionary containing inventory information
        """
        _validate_get_inventory_status_params(hotel_id)

        client = create_inventory_client(hotel_id=hotel_id)

        inventory_params = _build_inventory_params(
            item_category,
            str(minimum_stock_level) if minimum_stock_level is not None else None,
            include_low_stock,
        )

        response = await client.get_inventory_levels(inventory_params)

        if response.success:
            return {
                "success": True,
                "inventory_items": response.data.get("items", []),
                "summary": response.data.get("summary", {}),
                "low_stock_count": response.data.get("lowStockCount", 0),
                "hotel_id": hotel_id,
            }
        return {"success": False, "error": response.error, "hotel_id": hotel_id}


def register_update_inventory_tool(app: FastMCP):
    """Register update inventory tool."""

    @app.tool()
    async def update_inventory(
        item_id: str,
        quantity_change: int,
        hotel_id: str | None = None,
        reason: str | None = None,
        updated_by: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Update inventory levels for a specific item.

        Args:
            item_id: Item identifier
            quantity_change: Change in quantity (positive for additions,
                negative for removals)
            hotel_id: Hotel identifier (uses default if not provided)
            reason: Reason for inventory change (stocktake, delivery, usage, etc.)
            updated_by: Staff member making the update
            notes: Additional notes about the inventory change

        Returns:
            Dictionary containing inventory update confirmation
        """
        _validate_update_inventory_stock_params(hotel_id, item_id)

        client = create_inventory_client(hotel_id=hotel_id)

        update_data = _build_adjustment_data(
            item_id,
            quantity_change,
            reason or "Inventory adjustment",
            updated_by,
            notes,
        )

        response = await client.update_inventory(update_data)

        if response.success:
            return {
                "success": True,
                "updated_item": response.data,
                "item_id": item_id,
                "quantity_change": quantity_change,
                "new_quantity": response.data.get("currentQuantity"),
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "item_id": item_id,
            "hotel_id": hotel_id,
        }


def register_room_inspection_tool(app: FastMCP):
    """Register room inspection tool."""

    @app.tool()
    async def get_room_inspection(
        room_number: str,
        inspection_type: str,
        hotel_id: str | None = None,
        include_photos: bool = True,
        include_notes: bool = True,
    ) -> dict[str, Any]:
        """
        Get room inspection details and status.

        Args:
            room_number: Room number to inspect
            inspection_type: Type of inspection (check_in, check_out,
                maintenance, deep_clean)
            hotel_id: Hotel identifier (uses default if not provided)
            include_photos: Include inspection photos if available
            include_notes: Include inspection notes and comments

        Returns:
            Dictionary containing inspection details
        """
        _validate_get_inventory_status_params(hotel_id)

        client = create_housekeeping_client(hotel_id=hotel_id)

        inspection_params = _build_schedule_params(
            room_number,
            inspection_type,
            str(include_photos) if include_photos is not None else None,
        )

        response = await client.get_room_inspection(inspection_params)

        if response.success:
            return {
                "success": True,
                "inspection": response.data,
                "room_number": room_number,
                "inspection_type": inspection_type,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "room_number": room_number,
            "hotel_id": hotel_id,
        }


def register_create_maintenance_request_tool(app: FastMCP):
    """Register create maintenance request tool."""

    @app.tool()
    async def create_maintenance_request(
        room_number: str,
        issue_description: str,
        priority: str = "normal",
        hotel_id: str | None = None,
        category: str | None = None,
        estimated_cost: float | None = None,
        vendor_required: bool = False,
        assigned_to: str | None = None,
        due_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a maintenance request for a room.

        Args:
            room_number: Room number requiring maintenance
            issue_description: Detailed description of the issue
            priority: Priority level (low, normal, high, urgent)
            hotel_id: Hotel identifier (uses default if not provided)
            category: Category of maintenance (plumbing, electrical, HVAC, etc.)
            estimated_cost: Estimated cost of repairs
            vendor_required: Whether external vendor is required
            assigned_to: Staff member or vendor assigned to the task
            due_date: Due date for completion in YYYY-MM-DD format

        Returns:
            Dictionary containing maintenance request confirmation
        """
        _validate_create_maintenance_request_params(hotel_id, priority)

        client = create_housekeeping_client(hotel_id=hotel_id)

        maintenance_data = _build_maintenance_data(
            room_number,
            issue_description,
            priority,
            category,
            estimated_cost,
            vendor_required,
        )

        # Add additional fields
        maintenance_data["assignedTo"] = assigned_to
        maintenance_data["dueDate"] = due_date

        response = await client.create_maintenance_request(maintenance_data)

        if response.success:
            return {
                "success": True,
                "maintenance_request": response.data,
                "room_number": room_number,
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "room_number": room_number,
            "hotel_id": hotel_id,
        }


def register_get_inventory_status_tool(app: FastMCP):
    """Register get inventory status tool."""

    @app.tool()
    async def get_inventory_status(
        hotel_id: str | None = None,
        item_category: str | None = None,
        location: str | None = None,
        low_stock_only: bool = False,
    ) -> dict[str, Any]:
        """
        Get current inventory status for hotel supplies and amenities.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            item_category: Filter by item category (linen, amenity,
                cleaning_supply, etc.)
            location: Filter by location (all, rooms, housekeeping, etc.)
            low_stock_only: Only show items with low stock levels

        Returns:
            Dictionary containing inventory status information
        """
        _validate_get_inventory_status_params(hotel_id)

        client = create_inventory_client(hotel_id=hotel_id)

        inventory_params = _build_inventory_params(
            item_category, location, low_stock_only
        )

        response = await client.get_inventory_status(inventory_params)

        if response.success:
            return {
                "success": True,
                "inventory_items": response.data.get("items", []),
                "summary": response.data.get("summary", {}),
                "low_stock_count": response.data.get("lowStockCount", 0),
                "hotel_id": hotel_id,
            }
        return {"success": False, "error": response.error, "hotel_id": hotel_id}


def register_update_inventory_stock_tool(app: FastMCP):
    """Register update inventory stock tool."""

    @app.tool()
    async def update_inventory_stock(
        item_id: str,
        adjustment_reason: str,
        quantity_adjustment: int,
        hotel_id: str | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Update inventory stock levels for a specific item.

        Args:
            item_id: Item identifier
            adjustment_reason: Reason for adjustment (received, used, damaged, etc.)
            quantity_adjustment: Quantity to adjust (positive for additions,
                negative for removals)
            hotel_id: Hotel identifier (uses default if not provided)
            location: Specific location for the adjustment
            notes: Additional notes about the adjustment

        Returns:
            Dictionary containing inventory stock update confirmation
        """
        _validate_update_inventory_stock_params(hotel_id, adjustment_reason)

        client = create_inventory_client(hotel_id=hotel_id)

        adjustment_data = _build_adjustment_data(
            item_id, quantity_adjustment, adjustment_reason, location, notes
        )

        response = await client.update_inventory_stock(adjustment_data)

        if response.success:
            return {
                "success": True,
                "updated_item": response.data,
                "item_id": item_id,
                "quantity_adjustment": quantity_adjustment,
                "new_quantity": response.data.get("currentQuantity"),
                "hotel_id": hotel_id,
            }
        return {
            "success": False,
            "error": response.error,
            "item_id": item_id,
            "hotel_id": hotel_id,
        }


def register_get_cleaning_schedule_tool(app: FastMCP):
    """Register get cleaning schedule tool."""

    @app.tool()
    async def get_cleaning_schedule(
        hotel_id: str | None = None,
        schedule_date: str | None = None,
        room_type: str | None = None,
        staff_member: str | None = None,
    ) -> dict[str, Any]:
        """
        Get cleaning schedule for rooms.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            schedule_date: Date for schedule in YYYY-MM-DD format (defaults to today)
            room_type: Filter by room type
            staff_member: Filter by assigned staff member

        Returns:
            Dictionary containing cleaning schedule information
        """
        _validate_get_cleaning_schedule_params(hotel_id)

        client = create_housekeeping_client(hotel_id=hotel_id)

        schedule_params = _build_schedule_params(schedule_date, room_type, staff_member)

        response = await client.get_cleaning_schedule(schedule_params)

        if response.success:
            return {
                "success": True,
                "schedule": response.data.get("schedule", []),
                "summary": response.data.get("summary", {}),
                "hotel_id": hotel_id,
                "date": schedule_params.get("date"),
            }
        return {"success": False, "error": response.error, "hotel_id": hotel_id}


def register_room_tools(app: FastMCP):
    """Register all room and inventory management MCP tools."""
    register_room_status_tool(app)
    register_update_room_status_tool(app)
    register_check_room_availability_tool(app)
    register_housekeeping_tasks_tool(app)
    register_create_housekeeping_task_tool(app)
    register_complete_housekeeping_task_tool(app)
    register_inventory_levels_tool(app)
    register_update_inventory_tool(app)
    register_room_inspection_tool(app)
    register_create_maintenance_request_tool(app)
    register_get_inventory_status_tool(app)
    register_update_inventory_stock_tool(app)
    register_get_cleaning_schedule_tool(app)
