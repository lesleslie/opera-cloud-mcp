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


def register_room_tools(app: FastMCP):
    """Register all room and inventory management MCP tools."""

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
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_housekeeping_client(hotel_id=hotel_id)

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

        response = await client.get_room_status(status_params)

        if response.success:
            return {
                "success": True,
                "room_status": response.data.get("rooms", []),
                "summary": response.data.get("summary", {}),
                "hotel_id": hotel_id,
                "date": status_params["date"],
            }
        else:
            return {"success": False, "error": response.error, "hotel_id": hotel_id}

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
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        valid_statuses = ["clean", "dirty", "out_of_order", "maintenance", "inspected"]
        if new_status not in valid_statuses:
            raise ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        client = create_housekeeping_client(hotel_id=hotel_id)

        update_data = {
            "roomNumber": room_number,
            "status": new_status,
            "notes": notes,
            "maintenanceRequired": maintenance_required,
            "estimatedCompletion": estimated_completion,
            "updatedBy": "mcp_agent",
        }

        response = await client.update_room_status(update_data)

        if response.success:
            return {
                "success": True,
                "room_status": response.data,
                "room_number": room_number,
                "new_status": new_status,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "room_number": room_number,
                "hotel_id": hotel_id,
            }

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
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        # Validate dates
        try:
            arr_date = date.fromisoformat(arrival_date)
            dep_date = date.fromisoformat(departure_date)
            if arr_date >= dep_date:
                raise ValidationError("departure_date must be after arrival_date")
        except ValueError as e:
            raise ValidationError(f"Invalid date format: {e}")

        client = create_inventory_client(hotel_id=hotel_id)

        availability_params = {
            "arrivalDate": arrival_date,
            "departureDate": departure_date,
            "numberOfRooms": number_of_rooms,
        }

        if room_type:
            availability_params["roomType"] = room_type
        if rate_code:
            availability_params["rateCode"] = rate_code

        response = await client.check_availability(availability_params)

        if response.success:
            return {
                "success": True,
                "availability": response.data.get("availability", []),
                "search_criteria": availability_params,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "search_criteria": availability_params,
                "hotel_id": hotel_id,
            }

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
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_housekeeping_client(hotel_id=hotel_id)

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

        response = await client.get_housekeeping_tasks(task_params)

        if response.success:
            return {
                "success": True,
                "tasks": response.data.get("tasks", []),
                "summary": response.data.get("summary", {}),
                "hotel_id": hotel_id,
                "date": task_params["date"],
            }
        else:
            return {"success": False, "error": response.error, "hotel_id": hotel_id}

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
        Create a new housekeeping task.

        Args:
            room_number: Room number for the task
            task_type: Type of task (cleaning, maintenance, inspection, deep_clean)
            priority: Task priority (low, normal, high, urgent)
            hotel_id: Hotel identifier (uses default if not provided)
            description: Detailed task description
            assigned_to: Staff member to assign the task to
            estimated_duration: Estimated duration in minutes
            due_date: Due date in YYYY-MM-DD format

        Returns:
            Dictionary containing created task details
        """
        # Validate hotel_id - client factory will use default if None
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

        client = create_housekeeping_client(hotel_id=hotel_id)

        task_data = {
            "roomNumber": room_number,
            "taskType": task_type,
            "priority": priority,
            "description": description,
            "assignedTo": assigned_to,
            "estimatedDuration": estimated_duration,
            "dueDate": due_date,
            "createdBy": "mcp_agent",
        }

        response = await client.create_housekeeping_task(task_data)

        if response.success:
            return {
                "success": True,
                "task": response.data,
                "task_id": response.data.get("taskId"),
                "room_number": room_number,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "room_number": room_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def create_maintenance_request(
        room_number: str,
        issue_description: str,
        priority: str = "normal",
        hotel_id: str | None = None,
        category: str | None = None,
        estimated_cost: float | None = None,
        vendor_required: bool = False,
    ) -> dict[str, Any]:
        """
        Create a maintenance request for a room.

        Args:
            room_number: Room number requiring maintenance
            issue_description: Detailed description of the issue
            priority: Maintenance priority (low, normal, high, urgent)
            hotel_id: Hotel identifier (uses default if not provided)
            category: Maintenance category (electrical, plumbing, hvac, furniture)
            estimated_cost: Estimated cost for the repair
            vendor_required: Whether external vendor is required

        Returns:
            Dictionary containing maintenance request details
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        valid_priorities = ["low", "normal", "high", "urgent"]
        if priority not in valid_priorities:
            raise ValidationError(
                f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
            )

        client = create_housekeeping_client(hotel_id=hotel_id)

        maintenance_data = {
            "roomNumber": room_number,
            "issueDescription": issue_description,
            "priority": priority,
            "category": category,
            "estimatedCost": estimated_cost,
            "vendorRequired": vendor_required,
            "reportedBy": "mcp_agent",
        }

        response = await client.create_maintenance_request(maintenance_data)

        if response.success:
            return {
                "success": True,
                "maintenance_request": response.data,
                "request_id": response.data.get("requestId"),
                "room_number": room_number,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "room_number": room_number,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_inventory_status(
        hotel_id: str | None = None,
        item_category: str | None = None,
        location: str | None = None,
        low_stock_only: bool = False,
    ) -> dict[str, Any]:
        """
        Get hotel inventory status and stock levels.

        Args:
            hotel_id: Hotel identifier (uses default if not provided)
            item_category: Filter by item category (linens, amenities, cleaning)
            location: Filter by storage location
            low_stock_only: Show only items with low stock levels

        Returns:
            Dictionary containing inventory information
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_housekeeping_client(hotel_id=hotel_id)

        inventory_params = {}
        if item_category:
            inventory_params["category"] = item_category
        if location:
            inventory_params["location"] = location
        if low_stock_only:
            inventory_params["lowStockOnly"] = True

        response = await client.get_inventory_status(inventory_params)

        if response.success:
            return {
                "success": True,
                "inventory": response.data.get("items", []),
                "summary": response.data.get("summary", {}),
                "hotel_id": hotel_id,
            }
        else:
            return {"success": False, "error": response.error, "hotel_id": hotel_id}

    @app.tool()
    async def update_inventory_stock(
        item_id: str,
        quantity_adjustment: int,
        adjustment_reason: str,
        hotel_id: str | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Update inventory stock levels.

        Args:
            item_id: Inventory item identifier
            quantity_adjustment: Quantity change (positive or negative)
            adjustment_reason: Reason for adjustment (received, used, damaged, lost)
            hotel_id: Hotel identifier (uses default if not provided)
            location: Storage location for the items
            notes: Optional notes about the adjustment

        Returns:
            Dictionary containing inventory update confirmation
        """
        # Validate hotel_id - client factory will use default if None
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

        client = create_housekeeping_client(hotel_id=hotel_id)

        adjustment_data = {
            "itemId": item_id,
            "quantityAdjustment": quantity_adjustment,
            "adjustmentReason": adjustment_reason,
            "location": location,
            "notes": notes,
            "adjustedBy": "mcp_agent",
        }

        response = await client.update_inventory_stock(adjustment_data)

        if response.success:
            return {
                "success": True,
                "inventory_update": response.data,
                "item_id": item_id,
                "quantity_adjustment": quantity_adjustment,
                "hotel_id": hotel_id,
            }
        else:
            return {
                "success": False,
                "error": response.error,
                "item_id": item_id,
                "hotel_id": hotel_id,
            }

    @app.tool()
    async def get_cleaning_schedule(
        schedule_date: str | None = None,
        hotel_id: str | None = None,
        room_type: str | None = None,
        staff_member: str | None = None,
    ) -> dict[str, Any]:
        """
        Get cleaning schedule for rooms.

        Args:
            schedule_date: Date for schedule in YYYY-MM-DD format (defaults to today)
            hotel_id: Hotel identifier (uses default if not provided)
            room_type: Filter by room type
            staff_member: Filter by assigned staff member

        Returns:
            Dictionary containing cleaning schedule
        """
        # Validate hotel_id - client factory will use default if None
        if hotel_id == "":
            raise ValidationError("hotel_id cannot be empty string")

        client = create_housekeeping_client(hotel_id=hotel_id)

        schedule_params = {}
        if schedule_date:
            schedule_params["date"] = schedule_date
        else:
            schedule_params["date"] = date.today().isoformat()

        if room_type:
            schedule_params["roomType"] = room_type
        if staff_member:
            schedule_params["staffMember"] = staff_member

        response = await client.get_cleaning_schedule(schedule_params)

        if response.success:
            return {
                "success": True,
                "schedule": response.data.get("schedule", []),
                "summary": response.data.get("summary", {}),
                "date": schedule_params["date"],
                "hotel_id": hotel_id,
            }
        else:
            return {"success": False, "error": response.error, "hotel_id": hotel_id}
