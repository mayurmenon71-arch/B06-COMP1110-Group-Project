from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .customer_group import CustomerGroup
from .table import Table


@dataclass
class Restaurant:
    name: str
    opening_time: int
    closing_time: int
    tables: List[Table]
    waiting_queue: List[CustomerGroup] = field(default_factory=list)
    seated_groups: Dict[int, CustomerGroup] = field(default_factory=dict)
    completed_groups: List[CustomerGroup] = field(default_factory=list)
    left_groups: List[CustomerGroup] = field(default_factory=list)

    def add_group_to_queue(self, group: CustomerGroup) -> None:
        if group.status != "waiting":
            raise ValueError("Only waiting groups can be added to the queue.")
        self.waiting_queue.append(group)

    def release_finished_tables(self, current_time: int) -> List[int]:
        released: List[int] = []

        for table in self.tables:
            if table.current_group_id is None:
                continue

            group_id = table.current_group_id
            if table.clear_if_finished(current_time):
                released.append(table.table_id)
                if group_id is not None and group_id in self.seated_groups:
                    group = self.seated_groups.pop(group_id)
                    group.complete_meal()
                    self.completed_groups.append(group)

        return released

    def find_earliest_suitable_group(self, table: Table) -> Optional[CustomerGroup]:
        for group in self.waiting_queue:
            if group.can_fit(table.capacity):
                return group
        return None

    def seat_group_at_table(self, group: CustomerGroup, table: Table, current_time: int) -> None:
        if group not in self.waiting_queue:
            raise ValueError("Group must be in the waiting queue before seating.")
        if not group.can_fit(table.capacity):
            raise ValueError("Group does not fit the selected table.")

        table.seat_group(group.group_id, current_time, group.dining_duration)
        group.seat(table.table_id, current_time)

        self.waiting_queue.remove(group)
        self.seated_groups[group.group_id] = group

    def available_tables(self, current_time: int) -> List[Table]:
        return [table for table in self.tables if table.is_available(current_time)]

    def total_capacity(self) -> int:
        return sum(table.capacity for table in self.tables)

    def queue_length(self) -> int:
        return len(self.waiting_queue)

    def customers_waiting(self) -> int:
        return sum(group.size for group in self.waiting_queue)
