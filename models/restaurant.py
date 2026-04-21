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
    reservation_enabled: bool = False
    reservation_proportion: float = 0.30
    reservation_hold_minutes: int = 10
    reservation_window_minutes: int = 5
    reservation_fairness_wait_threshold: int = 15
    waiting_queue: List[CustomerGroup] = field(default_factory=list)
    seated_groups: Dict[int, CustomerGroup] = field(default_factory=dict)
    completed_groups: List[CustomerGroup] = field(default_factory=list)
    left_groups: List[CustomerGroup] = field(default_factory=list)
    reserved_tables: set[int] = field(default_factory=set)
    max_reserved_tables: int = 0

    def __post_init__(self) -> None:
        self._recalculate_max_reserved_tables()

    def _recalculate_max_reserved_tables(self) -> None:
        if not self.reservation_enabled:
            self.max_reserved_tables = 0
            self.reserved_tables.clear()
            return
<<<<<<< HEAD
        raw_limit = int(self.reservation_proportion * len(self.tables))
        if self.reservation_proportion > 0 and len(self.tables) > 0:
            raw_limit = max(1, raw_limit)
        self.max_reserved_tables = min(len(self.tables), raw_limit)
=======
        self.max_reserved_tables = int(self.reservation_proportion * len(self.tables))
>>>>>>> 3b56da46aab2a7c4b0f1d9ea53c401d035d65df4

    def configure_reservations(
        self,
        *,
        enabled: bool,
        proportion: float = 0.30,
        hold_minutes: int = 10,
        window_minutes: int = 5,
        fairness_wait_threshold: int = 15,
    ) -> None:
        if proportion < 0 or proportion > 1:
            raise ValueError("Reservation proportion must be between 0 and 1.")
        if hold_minutes <= 0:
            raise ValueError("Reservation hold minutes must be positive.")
        if window_minutes < 0:
            raise ValueError("Reservation window minutes cannot be negative.")
        if fairness_wait_threshold < 0:
            raise ValueError("Fairness wait threshold cannot be negative.")

        self.reservation_enabled = enabled
        self.reservation_proportion = proportion
        self.reservation_hold_minutes = hold_minutes
        self.reservation_window_minutes = window_minutes
        self.reservation_fairness_wait_threshold = fairness_wait_threshold
        self._recalculate_max_reserved_tables()

    def add_group_to_queue(self, group: CustomerGroup) -> None:
        if group.status != "waiting":
            raise ValueError("Only waiting groups can be added to the queue.")

        if group.is_reserved:
            if group.reservation_time is None:
                group.reservation_time = group.arrival_time
            if group.reservation_expiry_time is None:
                group.reservation_expiry_time = group.reservation_time + self.reservation_hold_minutes

            if not self.reservation_enabled:
                group.reservation_priority_lost = True
            elif not self._in_reservation_window(group):
                group.reservation_priority_lost = True
                group.reservation_late_arrival = True

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

        used_reserved_hold = table.reserved_for_group == group.group_id
        table.seat_group(group.group_id, current_time, group.dining_duration)
        group.seat(table.table_id, current_time)
        if used_reserved_hold:
            group.reservation_seated_with_priority = True
        group.reserved_table_id = None

        self.waiting_queue.remove(group)
        self.seated_groups[group.group_id] = group
        self.reserved_tables.discard(table.table_id)

    def available_tables(self, current_time: int) -> List[Table]:
        return [table for table in self.tables if table.is_available(current_time)]

    def total_capacity(self) -> int:
        return sum(table.capacity for table in self.tables)

    def queue_length(self) -> int:
        return len(self.waiting_queue)

    def customers_waiting(self) -> int:
        return sum(group.size for group in self.waiting_queue)

    def get_table_by_id(self, table_id: int) -> Optional[Table]:
        for table in self.tables:
            if table.table_id == table_id:
                return table
        return None

    def _in_reservation_window(self, group: CustomerGroup) -> bool:
        if group.reservation_time is None:
            return False
        return abs(group.arrival_time - group.reservation_time) <= self.reservation_window_minutes

    def is_group_reservation_active(self, group: CustomerGroup, current_time: int) -> bool:
        if not self.reservation_enabled:
            return False
        if not group.is_reserved:
            return False
        if group.status != "waiting":
            return False
        if group.reservation_priority_lost:
            return False
        if group.reservation_time is None or group.reservation_expiry_time is None:
            return False
        if not self._in_reservation_window(group):
            return False
        if current_time > group.reservation_expiry_time:
            return False
        return True

    def group_matches_reservation_table(self, group: CustomerGroup, table: Table) -> bool:
        if not group.can_fit(table.capacity):
            return False
        if group.reserved_table_id is not None and table.table_id != group.reserved_table_id:
            return False
        if group.preferred_table_id is not None and table.table_id != group.preferred_table_id:
            return False
        if group.preferred_table_capacity is not None and table.capacity != group.preferred_table_capacity:
            return False
        return True

    def release_reservation_for_group(self, group_id: int, *, mark_timeout: bool = False) -> None:
        for table in self.tables:
            if table.reserved_for_group == group_id:
                table.clear_reservation()
                self.reserved_tables.discard(table.table_id)

        for group in self.waiting_queue:
            if group.group_id == group_id:
                group.reserved_table_id = None
                if mark_timeout:
                    group.reservation_priority_lost = True
                    group.reservation_timed_out = True
                return

    def _reservation_candidate_tables(
        self,
        group: CustomerGroup,
        current_time: int,
    ) -> List[Table]:
        candidates: List[tuple[int, int, int, int, Table]] = []

        for table in self.tables:
            if table.reserved_for_group is not None and table.reserved_for_group != group.group_id:
                continue
            if not self.group_matches_reservation_table(group, table):
                continue

            available_at = current_time
            if table.occupied_until is not None and table.occupied_until > current_time:
                available_at = table.occupied_until

            if (
                group.reservation_expiry_time is not None
                and available_at > group.reservation_expiry_time
            ):
                continue

            availability_rank = 0 if table.is_available(current_time) else 1
            candidates.append((availability_rank, available_at, table.capacity, table.table_id, table))

        candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        return [table for _, _, _, _, table in candidates]

    def refresh_reservations(self, current_time: int) -> None:
        if not self.reservation_enabled:
            for table in self.tables:
                if table.reserved_for_group is not None:
                    table.clear_reservation()
            self.reserved_tables.clear()
            return

        waiting_by_id = {group.group_id: group for group in self.waiting_queue}

        for table in self.tables:
            if table.reserved_for_group is None:
                continue

            reserved_group = waiting_by_id.get(table.reserved_for_group)
            hold_expired = table.reserved_until is not None and current_time > table.reserved_until
            group_missing = reserved_group is None

            if hold_expired or group_missing:
                if reserved_group is not None and hold_expired:
                    reserved_group.reservation_priority_lost = True
                    reserved_group.reservation_timed_out = True
                    reserved_group.reserved_table_id = None
                table.clear_reservation()
                self.reserved_tables.discard(table.table_id)

        timed_out_group_ids: List[int] = []
        for group in self.waiting_queue:
            if not group.is_reserved:
                continue
            if group.reservation_priority_lost:
                continue
            if (
                group.reservation_expiry_time is not None
                and current_time > group.reservation_expiry_time
            ):
                group.reservation_priority_lost = True
                group.reservation_timed_out = True
                timed_out_group_ids.append(group.group_id)

        for group_id in timed_out_group_ids:
            self.release_reservation_for_group(group_id, mark_timeout=False)

        if self.max_reserved_tables <= 0:
            return

        sorted_waiting = sorted(
            self.waiting_queue,
            key=lambda g: (
                g.reservation_time if g.reservation_time is not None else g.arrival_time,
                g.arrival_time,
                g.group_id,
            ),
        )

        for group in sorted_waiting:
            if not self.is_group_reservation_active(group, current_time):
                continue

            if group.reserved_table_id is not None:
                assigned_table = self.get_table_by_id(group.reserved_table_id)
                if assigned_table is not None and assigned_table.reserved_for_group == group.group_id:
                    continue
                group.reserved_table_id = None

            if len(self.reserved_tables) >= self.max_reserved_tables:
                break

            candidates = self._reservation_candidate_tables(group, current_time)
            if not candidates:
                continue

            table = candidates[0]
            expiry = group.reservation_expiry_time
            if expiry is None:
                expiry = current_time + self.reservation_hold_minutes
                group.reservation_expiry_time = expiry

            table.reserve_for_group(group.group_id, expiry)
            group.reserved_table_id = table.table_id
            self.reserved_tables.add(table.table_id)
