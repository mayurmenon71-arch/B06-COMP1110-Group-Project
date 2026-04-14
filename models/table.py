from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Table:
    """
    Represents one table in the restaurant.
    Current MVP assumes no table sharing.
    """

    table_id: int
    capacity: int
    occupied_until: Optional[int] = None
    current_group_id: Optional[int] = None
    reserved_until: Optional[int] = None
    reserved_for_group: Optional[int] = None

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("Table capacity must be positive.")

    def is_available(self, current_time: int) -> bool:
        """Return True if the table is free at the given time."""
        return self.occupied_until is None or current_time >= self.occupied_until

    def seat_group(self, group_id: int, current_time: int, dining_duration: int) -> None:
        """Assign a group to the table until current_time + dining_duration."""
        if not self.is_available(current_time):
            raise ValueError(f"Table {self.table_id} is not available at time {current_time}.")
        if dining_duration <= 0:
            raise ValueError("Dining duration must be positive.")

        # Once a table is seated, any hold on that table is consumed.
        self.clear_reservation()
        self.current_group_id = group_id
        self.occupied_until = current_time + dining_duration

    def clear_if_finished(self, current_time: int) -> bool:
        """
        Free the table if the current group has finished dining.
        Returns True if the table changed from occupied to available.
        """
        if self.occupied_until is not None and current_time >= self.occupied_until:
            self.current_group_id = None
            self.occupied_until = None
            return True
        return False

    @property
    def occupied(self) -> bool:
        """Return whether the table is currently occupied."""
        return self.current_group_id is not None

    def reserve_for_group(self, group_id: int, reserved_until: int) -> None:
        if reserved_until < 0:
            raise ValueError("Reserved-until time cannot be negative.")
        self.reserved_for_group = group_id
        self.reserved_until = reserved_until

    def clear_reservation(self) -> None:
        self.reserved_until = None
        self.reserved_for_group = None
