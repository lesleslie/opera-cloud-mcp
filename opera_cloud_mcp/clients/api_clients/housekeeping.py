"""
Housekeeping API client for OPERA Cloud.

Handles housekeeping operations including room status management,
cleaning schedules, and maintenance operations through the OPERA Cloud HSK API.
"""

import asyncio
from datetime import date, datetime, time
from typing import Any

from pydantic import Field, validator

from opera_cloud_mcp.clients.base_client import APIResponse, BaseAPIClient
from opera_cloud_mcp.models.common import OperaBaseModel


class HousekeepingTask(OperaBaseModel):
    """Housekeeping task model."""

    task_id: str = Field(alias="taskId")
    room_number: str = Field(alias="roomNumber")
    task_type: str = Field(alias="taskType")  # "cleaning", "maintenance", "inspection"
    priority: int = Field(ge=1, le=5)  # 1 = low, 5 = urgent
    status: str = Field(
        default="pending"
    )  # "pending", "assigned", "in_progress", "completed", "cancelled"
    assigned_to: str | None = Field(None, alias="assignedTo")
    estimated_duration: int = Field(alias="estimatedDuration")  # minutes
    actual_duration: int | None = Field(None, alias="actualDuration")
    special_instructions: str | None = Field(None, alias="specialInstructions")
    supplies_needed: list[str] | None = Field(None, alias="suppliesNeeded")
    created_at: datetime = Field(alias="createdAt")
    scheduled_at: datetime | None = Field(None, alias="scheduledAt")
    completed_at: datetime | None = Field(None, alias="completedAt")


class RoomStatusUpdate(OperaBaseModel):
    """Room status update model."""

    room_number: str = Field(alias="roomNumber")
    housekeeping_status: str = Field(
        alias="housekeepingStatus"
    )  # "clean", "dirty", "out_of_order", "maintenance"
    front_office_status: str = Field(
        alias="frontOfficeStatus"
    )  # "occupied", "vacant_dirty", "vacant_clean", "out_of_service"
    maintenance_required: bool = Field(False, alias="maintenanceRequired")
    room_condition: str | None = Field(
        None, alias="roomCondition"
    )  # "excellent", "good", "fair", "poor"
    cleaning_notes: str | None = Field(None, alias="cleaningNotes")
    maintenance_notes: str | None = Field(None, alias="maintenanceNotes")
    updated_by: str = Field(alias="updatedBy")
    updated_at: datetime = Field(default_factory=datetime.now, alias="updatedAt")

    @validator("housekeeping_status")
    def validate_housekeeping_status(self, v):
        allowed = ["clean", "dirty", "out_of_order", "maintenance", "inspected"]
        if v not in allowed:
            raise ValueError(f"Invalid housekeeping status. Must be one of: {allowed}")
        return v


class MaintenanceRequest(OperaBaseModel):
    """Maintenance request model."""

    room_number: str = Field(alias="roomNumber")
    request_type: str = Field(alias="requestType")  # "urgent", "routine", "preventive"
    category: str  # "electrical", "plumbing", "hvac", "furniture", "other"
    description: str
    priority: int = Field(ge=1, le=5)
    reported_by: str = Field(alias="reportedBy")
    guest_impact: bool = Field(False, alias="guestImpact")
    estimated_completion: datetime | None = Field(None, alias="estimatedCompletion")
    parts_needed: list[str] | None = Field(None, alias="partsNeeded")

    @validator("category")
    def validate_category(self, v):
        allowed = [
            "electrical",
            "plumbing",
            "hvac",
            "furniture",
            "appliances",
            "safety",
            "other",
        ]
        if v not in allowed:
            raise ValueError(f"Invalid category. Must be one of: {allowed}")
        return v


class CleaningSchedule(OperaBaseModel):
    """Cleaning schedule model."""

    schedule_date: date = Field(alias="scheduleDate")
    shift: str  # "morning", "afternoon", "night"
    room_assignments: dict[str, str] = Field(
        alias="roomAssignments"
    )  # {room_number: housekeeper_id}
    special_rooms: list[str] | None = Field(
        None, alias="specialRooms"
    )  # VIP, maintenance, etc.
    estimated_completion: time = Field(alias="estimatedCompletion")

    @validator("shift")
    def validate_shift(self, v):
        allowed = ["morning", "afternoon", "night"]
        if v not in allowed:
            raise ValueError(f"Invalid shift. Must be one of: {allowed}")
        return v


class InventoryItem(OperaBaseModel):
    """Housekeeping inventory item model."""

    item_code: str = Field(alias="itemCode")
    item_name: str = Field(alias="itemName")
    category: str  # "cleaning_supplies", "linens", "amenities", "equipment"
    current_stock: int = Field(alias="currentStock")
    minimum_stock: int = Field(alias="minimumStock")
    unit_cost: float = Field(alias="unitCost")
    supplier: str | None = None
    last_restocked: date | None = Field(None, alias="lastRestocked")


class HousekeepingClient(BaseAPIClient):
    """
    Client for OPERA Cloud Housekeeping API.

    Provides comprehensive housekeeping operations including room status management,
    cleaning schedules, maintenance requests, and inventory tracking.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_domain = "hsk"

    # Room Status Management

    async def get_room_status(
        self,
        room_number: str | None = None,
        status_filter: str | None = None,
        floor: str | None = None,
    ) -> APIResponse:
        """
        Get current room status information.

        Args:
            room_number: Specific room number to check
            status_filter: Filter by status (clean, dirty, out_of_order, etc.)
            floor: Filter by floor number

        Returns:
            APIResponse with room status details
        """
        endpoint = f"{self.api_domain}/v1/rooms/status"
        params = {}

        if room_number:
            params["roomNumber"] = room_number
        if status_filter:
            params["status"] = status_filter
        if floor:
            params["floor"] = floor

        return await self.get(endpoint, params=params)

    async def update_room_status(
        self, status_update: RoomStatusUpdate | dict[str, Any]
    ) -> APIResponse:
        """
        Update room status and condition.

        Args:
            status_update: Room status update information

        Returns:
            APIResponse with update confirmation
        """
        if isinstance(status_update, dict):
            status_update = RoomStatusUpdate.model_validate(status_update)

        endpoint = f"{self.api_domain}/v1/rooms/{status_update.room_number}/status"

        payload = {
            "housekeepingStatus": status_update.housekeeping_status,
            "frontOfficeStatus": status_update.front_office_status,
            "maintenanceRequired": status_update.maintenance_required,
            "roomCondition": status_update.room_condition,
            "cleaningNotes": status_update.cleaning_notes,
            "maintenanceNotes": status_update.maintenance_notes,
            "updatedBy": status_update.updated_by,
            "updatedAt": status_update.updated_at.isoformat(),
        }

        return await self.put(endpoint, json_data=payload)

    async def bulk_status_update(
        self, status_updates: list[RoomStatusUpdate]
    ) -> APIResponse:
        """
        Update multiple room statuses in a single operation.

        Args:
            status_updates: List of room status updates

        Returns:
            APIResponse with bulk update results
        """
        endpoint = f"{self.api_domain}/v1/rooms/status/bulk"

        payload = {
            "updates": [
                {
                    "roomNumber": update.room_number,
                    "housekeepingStatus": update.housekeeping_status,
                    "frontOfficeStatus": update.front_office_status,
                    "maintenanceRequired": update.maintenance_required,
                    "roomCondition": update.room_condition,
                    "cleaningNotes": update.cleaning_notes,
                    "maintenanceNotes": update.maintenance_notes,
                    "updatedBy": update.updated_by,
                    "updatedAt": update.updated_at.isoformat(),
                }
                for update in status_updates
            ]
        }

        return await self.post(endpoint, json_data=payload)

    # Task Management

    async def get_housekeeping_tasks(
        self,
        task_date: date | None = None,
        status: str | None = None,
        assigned_to: str | None = None,
        room_number: str | None = None,
    ) -> APIResponse:
        """
        Get housekeeping tasks for specified criteria.

        Args:
            task_date: Date to filter tasks (defaults to today)
            status: Filter by task status
            assigned_to: Filter by assigned housekeeper
            room_number: Filter by room number

        Returns:
            APIResponse with task list
        """
        if task_date is None:
            task_date = date.today()

        endpoint = f"{self.api_domain}/v1/tasks"
        params = {"date": task_date.isoformat()}

        if status:
            params["status"] = status
        if assigned_to:
            params["assignedTo"] = assigned_to
        if room_number:
            params["roomNumber"] = room_number

        return await self.get(endpoint, params=params)

    async def create_housekeeping_task(
        self, task_data: HousekeepingTask | dict[str, Any]
    ) -> APIResponse:
        """
        Create a new housekeeping task.

        Args:
            task_data: Task creation data

        Returns:
            APIResponse with created task details
        """
        if isinstance(task_data, dict):
            task_data = HousekeepingTask.model_validate(task_data)

        endpoint = f"{self.api_domain}/v1/tasks"

        payload = {
            "roomNumber": task_data.room_number,
            "taskType": task_data.task_type,
            "priority": task_data.priority,
            "assignedTo": task_data.assigned_to,
            "estimatedDuration": task_data.estimated_duration,
            "specialInstructions": task_data.special_instructions,
            "suppliesNeeded": task_data.supplies_needed,
            "scheduledAt": task_data.scheduled_at.isoformat()
            if task_data.scheduled_at
            else None,
        }

        return await self.post(endpoint, json_data=payload)

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        notes: str | None = None,
        actual_duration: int | None = None,
    ) -> APIResponse:
        """
        Update task status and completion details.

        Args:
            task_id: Task identifier
            status: New task status
            notes: Optional completion notes
            actual_duration: Actual time taken in minutes

        Returns:
            APIResponse with update confirmation
        """
        endpoint = f"{self.api_domain}/v1/tasks/{task_id}"

        payload = {
            "status": status,
            "completionNotes": notes,
            "actualDuration": actual_duration,
            "updatedAt": datetime.now().isoformat(),
        }

        if status == "completed":
            payload["completedAt"] = datetime.now().isoformat()

        return await self.put(endpoint, json_data=payload)

    # Cleaning Schedules

    async def get_cleaning_schedule(
        self, schedule_date: date | None = None, shift: str | None = None
    ) -> APIResponse:
        """
        Get cleaning schedule for specified date and shift.

        Args:
            schedule_date: Date for schedule (defaults to today)
            shift: Specific shift to retrieve

        Returns:
            APIResponse with cleaning schedule
        """
        if schedule_date is None:
            schedule_date = date.today()

        endpoint = f"{self.api_domain}/v1/schedules/cleaning"
        params = {"date": schedule_date.isoformat()}

        if shift:
            params["shift"] = shift

        return await self.get(endpoint, params=params)

    async def create_cleaning_schedule(
        self, schedule_data: CleaningSchedule | dict[str, Any]
    ) -> APIResponse:
        """
        Create or update cleaning schedule.

        Args:
            schedule_data: Schedule configuration data

        Returns:
            APIResponse with schedule creation confirmation
        """
        if isinstance(schedule_data, dict):
            schedule_data = CleaningSchedule.model_validate(schedule_data)

        endpoint = f"{self.api_domain}/v1/schedules/cleaning"

        payload = {
            "scheduleDate": schedule_data.schedule_date.isoformat(),
            "shift": schedule_data.shift,
            "roomAssignments": schedule_data.room_assignments,
            "specialRooms": schedule_data.special_rooms,
            "estimatedCompletion": schedule_data.estimated_completion.strftime(
                "%H:%M:%S"
            ),
        }

        return await self.post(endpoint, json_data=payload)

    # Maintenance Management

    async def create_maintenance_request(
        self, maintenance_data: MaintenanceRequest | dict[str, Any]
    ) -> APIResponse:
        """
        Create a maintenance request for a room.

        Args:
            maintenance_data: Maintenance request details

        Returns:
            APIResponse with maintenance request ID
        """
        if isinstance(maintenance_data, dict):
            maintenance_data = MaintenanceRequest.model_validate(maintenance_data)

        endpoint = f"{self.api_domain}/v1/maintenance/requests"

        payload = {
            "roomNumber": maintenance_data.room_number,
            "requestType": maintenance_data.request_type,
            "category": maintenance_data.category,
            "description": maintenance_data.description,
            "priority": maintenance_data.priority,
            "reportedBy": maintenance_data.reported_by,
            "guestImpact": maintenance_data.guest_impact,
            "estimatedCompletion": maintenance_data.estimated_completion.isoformat()
            if maintenance_data.estimated_completion
            else None,
            "partsNeeded": maintenance_data.parts_needed,
        }

        return await self.post(endpoint, json_data=payload)

    async def get_maintenance_requests(
        self,
        status: str | None = None,
        priority: int | None = None,
        room_number: str | None = None,
    ) -> APIResponse:
        """
        Get maintenance requests by criteria.

        Args:
            status: Filter by request status
            priority: Filter by priority level
            room_number: Filter by room number

        Returns:
            APIResponse with maintenance request list
        """
        endpoint = f"{self.api_domain}/v1/maintenance/requests"
        params = {}

        if status:
            params["status"] = status
        if priority:
            params["priority"] = str(priority)
        if room_number:
            params["roomNumber"] = room_number

        return await self.get(endpoint, params=params)

    # Inventory Management

    async def get_inventory_status(
        self, category: str | None = None, low_stock_only: bool = False
    ) -> APIResponse:
        """
        Get housekeeping inventory status.

        Args:
            category: Filter by item category
            low_stock_only: Show only items below minimum stock

        Returns:
            APIResponse with inventory details
        """
        endpoint = f"{self.api_domain}/v1/inventory"
        params = {}

        if category:
            params["category"] = category
        if low_stock_only:
            params["lowStockOnly"] = "true"

        return await self.get(endpoint, params=params)

    async def update_inventory_stock(
        self, item_code: str, quantity_change: int, transaction_type: str = "adjustment"
    ) -> APIResponse:
        """
        Update inventory stock levels.

        Args:
            item_code: Inventory item code
            quantity_change: Positive or negative quantity change
            transaction_type: Type of transaction (adjustment, usage, restock)

        Returns:
            APIResponse with updated inventory status
        """
        endpoint = f"{self.api_domain}/v1/inventory/{item_code}"

        payload = {
            "quantityChange": quantity_change,
            "transactionType": transaction_type,
            "updatedAt": datetime.now().isoformat(),
        }

        return await self.put(endpoint, json_data=payload)

    # Reporting and Analytics

    async def get_housekeeping_summary(
        self, report_date: date | None = None
    ) -> APIResponse:
        """
        Get comprehensive housekeeping summary report.

        Args:
            report_date: Date for the report (defaults to today)

        Returns:
            APIResponse with housekeeping metrics and status
        """
        if report_date is None:
            report_date = date.today()

        endpoint = f"{self.api_domain}/v1/reports/summary"
        params = {"date": report_date.isoformat()}

        return await self.get(endpoint, params=params)

    async def get_productivity_report(
        self, start_date: date, end_date: date, housekeeper_id: str | None = None
    ) -> APIResponse:
        """
        Get housekeeping productivity report.

        Args:
            start_date: Report start date
            end_date: Report end date
            housekeeper_id: Specific housekeeper to analyze

        Returns:
            APIResponse with productivity metrics
        """
        endpoint = f"{self.api_domain}/v1/reports/productivity"
        params = {"startDate": start_date.isoformat(), "endDate": end_date.isoformat()}

        if housekeeper_id:
            params["housekeeperId"] = housekeeper_id

        return await self.get(endpoint, params=params)

    # Batch Operations

    async def batch_create_tasks(
        self, task_list: list[HousekeepingTask]
    ) -> APIResponse:
        """
        Create multiple housekeeping tasks in a single operation.

        Args:
            task_list: List of tasks to create

        Returns:
            APIResponse with batch creation results
        """
        tasks = [self.create_housekeeping_task(task_data) for task_data in task_list]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = []
        failed = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append(
                    {"room_number": task_list[i].room_number, "error": str(result)}
                )
            elif isinstance(result, APIResponse) and result.success:
                successful.append(result.data)
            elif isinstance(result, APIResponse):
                failed.append(
                    {
                        "room_number": task_list[i].room_number,
                        "error": result.error or "Unknown error",
                    }
                )

        return APIResponse(
            success=len(failed) == 0,
            data={
                "successful_tasks": successful,
                "failed_tasks": failed,
                "total_processed": len(task_list),
                "success_count": len(successful),
                "failure_count": len(failed),
            },
        )
