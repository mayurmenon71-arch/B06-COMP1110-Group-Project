"""
Table assignment logic: given available tables and the waiting queue,
seat as many groups as possible each simulation tick using FCFS across queues.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

from .customer_group import CustomerGroup
from .restaurant import Restaurant
from .table import Table
from .queue_stratgies import (
    QueueRange,
    assign_queue_index,
    find_best_fit_group_from_queues,
    find_fcfs_group_for_table,
    find_fcfs_group_from_queues,
    find_group_by_queue_order,
)


def run_seating_round(
    restaurant: Restaurant,
    current_time: int,
    queue_ranges: Sequence[QueueRange],
    queues: Sequence[List[CustomerGroup]] | None = None,
) -> List[Tuple[CustomerGroup, Table]]:
    """
    Attempt to seat as many waiting groups as possible at currently free tables.

    Tables are processed smallest-capacity-first (best-fit) to preserve large
    tables for large groups.

    Args:
        restaurant:    The restaurant whose waiting_queue and tables are used.
        current_time:  Current simulation time (minutes).
        queue_ranges:  Defines how groups are split into queues by size.
                       Use default_single_queue_range() for one queue,
                       default_multi_queue_ranges() for 1-2 / 3-4 / 5+ split,
                       or any custom Sequence[QueueRange].
        queues:        Optional persistent queue-state lists maintained by the
                       simulation engine. If omitted, queues are rebuilt from
                       restaurant.waiting_queue for backward compatibility.

    Returns:
        List of (CustomerGroup, Table) pairs seated this round.
    """
    available_tables = sorted(
        restaurant.available_tables(current_time),
        key=lambda t: t.capacity,
    )
    seated: List[Tuple[CustomerGroup, Table]] = []
    fairness_override_active = _fairness_override_active(restaurant, current_time)

    for table in available_tables:
        queue_state = list(queues) if queues is not None else _build_queues(
            restaurant.waiting_queue, queue_ranges, current_time
        )
        eligible_queues = _filter_queues_for_table(queue_state, restaurant, table, current_time)

        reserved_priority_selected = False
        group = None
        if not fairness_override_active:
            group = _select_reserved_group_for_table(
                restaurant,
                eligible_queues,
                queue_ranges,
                table,
                current_time,
            )
            reserved_priority_selected = group is not None

        if group is None:
            group = _select_group_for_table(restaurant, eligible_queues, queue_ranges, table.capacity)

        if group is None:
            continue
        if reserved_priority_selected:
            group.reservation_seated_with_priority = True
        restaurant.seat_group_at_table(group, table, current_time)
        if queues is not None:
            _remove_group_from_queues(queues, group)
        seated.append((group, table))

    return seated


def _build_queues(
    waiting_queue: List[CustomerGroup],
    queue_ranges: Sequence[QueueRange],
    current_time: int,
) -> List[List[CustomerGroup]]:
    """
    Distribute waiting groups into sub-queues based on size ranges.
    Returns one list per range (snapshot copies, safe for FCFS selection).
    Groups whose size does not match any range are silently skipped.
    """
    queues: List[List[CustomerGroup]] = [[] for _ in queue_ranges]
    for group in waiting_queue:
        if group.arrival_time > current_time:
            continue  # group hasn't arrived yet
        try:
            idx = assign_queue_index(group.size, queue_ranges)
            queues[idx].append(group)
        except ValueError:
            pass  # group size outside all defined ranges — skip
    return queues


def _select_group_for_table(
    restaurant: Restaurant,
    queues: Sequence[Sequence[CustomerGroup]],
    queue_ranges: Sequence[QueueRange],
    table_capacity: int,
) -> CustomerGroup | None:
    """
    Use strategy-specific selection logic based on queue configuration:
    - 1 queue: classic single-queue FCFS.
    - 3 queues: size-based queue priority (queue order).
    - 4+ queues: best-fit across queues for finer seat matching.
    - fallback: global FCFS across queues.
    """
    num_queues = len(queue_ranges)

    if num_queues == 1:
        if queues:
            return find_fcfs_group_for_table(queues[0], table_capacity)
        return find_fcfs_group_for_table(restaurant.waiting_queue, table_capacity)

    if num_queues == 3:
        return find_group_by_queue_order(queues, table_capacity, queue_order=(0, 1, 2))

    if num_queues >= 4:
        return find_best_fit_group_from_queues(queues, table_capacity)

    return find_fcfs_group_from_queues(queues, table_capacity)


def _remove_group_from_queues(
    queues: Sequence[List[CustomerGroup]],
    group: CustomerGroup,
) -> None:
    for queue in queues:
        if group in queue:
            queue.remove(group)
            return


def _filter_queues_for_table(
    queues: Sequence[Sequence[CustomerGroup]],
    restaurant: Restaurant,
    table: Table,
    current_time: int,
) -> List[List[CustomerGroup]]:
    filtered: List[List[CustomerGroup]] = []
    for queue in queues:
        filtered.append(
            [
                group
                for group in queue
                if _group_can_use_table(group, restaurant, table, current_time)
            ]
        )
    return filtered


def _group_can_use_table(
    group: CustomerGroup,
    restaurant: Restaurant,
    table: Table,
    current_time: int,
) -> bool:
    if not group.can_fit(table.capacity):
        return False

    if restaurant.is_group_reservation_active(group, current_time):
        return restaurant.group_matches_reservation_table(group, table)

    return True


def _find_group_by_id_in_queues(
    queues: Sequence[Sequence[CustomerGroup]],
    group_id: int,
) -> CustomerGroup | None:
    for queue in queues:
        for group in queue:
            if group.group_id == group_id:
                return group
    return None


def _select_reserved_group_for_table(
    restaurant: Restaurant,
    queues: Sequence[Sequence[CustomerGroup]],
    queue_ranges: Sequence[QueueRange],
    table: Table,
    current_time: int,
) -> CustomerGroup | None:
    if not restaurant.reservation_enabled:
        return None

    if (
        table.reserved_for_group is not None
        and table.reserved_until is not None
        and current_time <= table.reserved_until
    ):
        reserved_group = _find_group_by_id_in_queues(queues, table.reserved_for_group)
        if (
            reserved_group is not None
            and restaurant.is_group_reservation_active(reserved_group, current_time)
        ):
            return reserved_group

    num_queues = len(queue_ranges)

    if num_queues == 1:
        if not queues:
            return None
        for group in queues[0]:
            if restaurant.is_group_reservation_active(group, current_time):
                return group
        return None

    if num_queues == 3:
        for queue_idx in (0, 1, 2):
            if queue_idx >= len(queues):
                continue
            for group in queues[queue_idx]:
                if restaurant.is_group_reservation_active(group, current_time):
                    return group
        return None

    candidates = [
        group
        for queue in queues
        for group in queue
        if restaurant.is_group_reservation_active(group, current_time)
    ]
    if not candidates:
        return None

    if num_queues >= 4:
        exact_fit = [group for group in candidates if group.size == table.capacity]
        if exact_fit:
            return min(exact_fit, key=lambda g: (g.arrival_time, g.group_id))
        return min(candidates, key=lambda g: (table.capacity - g.size, g.arrival_time, g.group_id))

    return min(candidates, key=lambda g: (g.arrival_time, g.group_id))


def _fairness_override_active(
    restaurant: Restaurant,
    current_time: int,
) -> bool:
    if not restaurant.reservation_enabled:
        return False

    walkin_waits: List[int] = []
    for group in restaurant.waiting_queue:
        if group.arrival_time > current_time:
            continue
        if restaurant.is_group_reservation_active(group, current_time):
            continue
        wait = current_time - group.arrival_time
        if wait >= 0:
            walkin_waits.append(wait)

    if not walkin_waits:
        return False

    avg_wait = sum(walkin_waits) / len(walkin_waits)
    return avg_wait > restaurant.reservation_fairness_wait_threshold
