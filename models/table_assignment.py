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
    find_fcfs_group_from_queues,
)


def run_seating_round(
    restaurant: Restaurant,
    current_time: int,
    queue_ranges: Sequence[QueueRange],
) -> List[Tuple[CustomerGroup, Table]]:
    """
    Attempt to seat as many waiting groups as possible at currently free tables.

    Tables are processed smallest-capacity-first (best-fit) to preserve large
    tables for large groups. The earliest-arriving eligible group across all
    queues (cross-queue FCFS by arrival_time) is selected for each table.

    Args:
        restaurant:    The restaurant whose waiting_queue and tables are used.
        current_time:  Current simulation time (minutes).
        queue_ranges:  Defines how groups are split into queues by size.
                       Use default_single_queue_range() for one queue,
                       default_multi_queue_ranges() for 1-2 / 3-4 / 5+ split,
                       or any custom Sequence[QueueRange].

    Returns:
        List of (CustomerGroup, Table) pairs seated this round.
    """
    available_tables = sorted(
        restaurant.available_tables(current_time),
        key=lambda t: t.capacity,
    )
    seated: List[Tuple[CustomerGroup, Table]] = []

    for table in available_tables:
        queues = _build_queues(restaurant.waiting_queue, queue_ranges, current_time)
        group = find_fcfs_group_from_queues(queues, table.capacity)
        if group is None:
            continue
        restaurant.seat_group_at_table(group, table, current_time)
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
