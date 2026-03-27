from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CustomerGroup:
    """
    Represents one arriving customer group in the simulation.

    Attributes:
        group_id: Unique identifier for the group.
        size: Number of customers in the group.
        arrival_time: Time the group arrives at the restaurant.
        dining_duration: Time the group occupies a table once seated.
    """

    group_id: int
    size: int
    arrival_time: int
    dining_duration: int
    seated_time: Optional[int] = None
    leave_time: Optional[int] = None
    assigned_table_id: Optional[int] = None
    status: str = "waiting"  # waiting, seated, completed, left

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("Group size must be positive.")
        if self.arrival_time < 0:
            raise ValueError("Arrival time cannot be negative.")
        if self.dining_duration <= 0:
            raise ValueError("Dining duration must be positive.")

    @property
    def waiting_time(self) -> Optional[int]:
        """Return waiting time after the group has been seated."""
        if self.seated_time is None:
            return None
        return self.seated_time - self.arrival_time

    def seat(self, table_id: int, current_time: int) -> None:
        """Mark the group as seated at a given time and table."""
        if current_time < self.arrival_time:
            raise ValueError("Cannot seat a group before it arrives.")

        self.seated_time = current_time
        self.leave_time = current_time + self.dining_duration
        self.assigned_table_id = table_id
        self.status = "seated"

    def complete_meal(self) -> None:
        """Mark the group as having finished dining."""
        self.status = "completed"

    def leave_queue(self) -> None:
        """Mark the group as having left before being seated."""
        self.status = "left"

    def can_fit(self, table_capacity: int) -> bool:
        """Return True if the group can fit at a table of given capacity."""
        return self.size <= table_capacity
