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
    is_reserved: bool = False
    reservation_time: Optional[int] = None
    reservation_expiry_time: Optional[int] = None
    preferred_table_id: Optional[int] = None
    preferred_table_capacity: Optional[int] = None
    reserved_table_id: Optional[int] = None
    reservation_priority_lost: bool = False
    reservation_timed_out: bool = False
    reservation_late_arrival: bool = False
    reservation_seated_with_priority: bool = False
    has_left: bool = False
    last_cumulative_abandonment_prob: float = 0.0
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
        if self.reservation_time is not None and self.reservation_time < 0:
            raise ValueError("Reservation time cannot be negative.")
        if self.reservation_expiry_time is not None and self.reservation_expiry_time < 0:
            raise ValueError("Reservation expiry time cannot be negative.")
        if (
            self.reservation_time is not None
            and self.reservation_expiry_time is not None
            and self.reservation_expiry_time < self.reservation_time
        ):
            raise ValueError("Reservation expiry time cannot be earlier than reservation time.")
        if self.preferred_table_id is not None and self.preferred_table_id <= 0:
            raise ValueError("Preferred table id must be positive.")
        if self.preferred_table_capacity is not None and self.preferred_table_capacity <= 0:
            raise ValueError("Preferred table capacity must be positive.")
        if not (0.0 <= self.last_cumulative_abandonment_prob <= 1.0):
            raise ValueError("Last cumulative abandonment probability must be between 0 and 1.")

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

    def leave_queue(self, current_time: Optional[int] = None) -> None:
        """Mark the group as having left before being seated."""
        self.status = "left"
        self.has_left = True
        if current_time is not None:
            self.leave_time = current_time

    def can_fit(self, table_capacity: int) -> bool:
        """Return True if the group can fit at a table of given capacity."""
        return self.size <= table_capacity

    @property
    def is_reservation_customer(self) -> bool:
        return self.is_reserved

    @property
    def group_size(self) -> int:
        return self.size
