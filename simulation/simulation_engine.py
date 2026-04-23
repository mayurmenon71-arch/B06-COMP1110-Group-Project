"""
Core simulation engine: drives the minute-by-minute time loop.

Usage:
    result = run_simulation(restaurant, arrivals, queue_ranges)

The restaurant object is mutated in place. Pass a deep copy if you need
to run multiple strategies on the same scenario:

    import copy
    result = run_simulation(copy.deepcopy(restaurant), copy.deepcopy(arrivals), ranges)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from models.customer_group import CustomerGroup
from models.restaurant import Restaurant
from models.table_assignment import run_seating_round
from models.queue_stratgies import QueueRange, assign_queue_index


@dataclass
class SimulationResult:
    """Holds all output data from one simulation run."""
    completed_groups: List[CustomerGroup]   # seated and finished dining
    left_groups: List[CustomerGroup]        # dropped out before being seated
    still_waiting: List[CustomerGroup]      # still in queue at closing time
    total_arrived: int                      # total groups that showed up
    max_queue_length: int                   # peak waiting queue length
    occupied_ticks: int                     # sum of occupied-table-count across all ticks
    total_ticks: int                        # simulation duration in minutes
    total_tables: int                       # number of tables in the restaurant
    reservation_enabled: bool               # whether reservation system was enabled
    total_reserved_groups: int              # reservation groups that arrived
    served_reserved_groups: int             # reservation groups that were served
    served_reserved_with_priority_groups: int  # reserved groups seated with reservation priority
    timeout_reserved_groups: int            # reservation groups that lost priority due timeout
    reserved_table_ticks: int               # active reserved-table holds across ticks
    reserved_capacity_ticks: int            # max possible reserved-table ticks


def run_simulation(
    restaurant: Restaurant,
    arrivals: List[CustomerGroup],
    queue_ranges: Sequence[QueueRange],
    dropout_threshold: int = 30,
    use_round_robin: bool = False,
) -> SimulationResult:
    """
    Run the restaurant queue simulation minute by minute.

    Args:
        restaurant:        A fresh Restaurant object (will be mutated).
        arrivals:          List of CustomerGroup objects sorted by arrival_time.
        queue_ranges:      Defines queue strategy (single or size-based).
        dropout_threshold: Minutes a group waits before leaving (default 30).

    Returns:
        SimulationResult with all metrics data.
    """
    max_queue_length = 0
    occupied_ticks = 0
    reserved_table_ticks = 0
    total_ticks = restaurant.closing_time - restaurant.opening_time
    queues: List[List[CustomerGroup]] = [[] for _ in queue_ranges]

    round_robin_index: int = 0

    # Index arrivals by minute for O(1) lookup
    arrivals_by_minute: dict[int, List[CustomerGroup]] = {}
    for group in arrivals:
        arrivals_by_minute.setdefault(group.arrival_time, []).append(group)

    for t in range(restaurant.opening_time, restaurant.closing_time + 1):
        # 1. Add new arrivals this minute
        for group in arrivals_by_minute.get(t, []):
            restaurant.add_group_to_queue(group)
            _add_group_to_strategy_queues(group, queues, queue_ranges)

        # 2. Dropout: remove groups that have waited too long
        to_drop = [
            g for g in restaurant.waiting_queue
            if (t - g.arrival_time) > dropout_threshold
        ]
        for group in to_drop:
            group.leave_queue()
            restaurant.waiting_queue.remove(group)
            _remove_group_from_strategy_queues(group, queues, queue_ranges)
            restaurant.release_reservation_for_group(group.group_id, mark_timeout=False)
            restaurant.left_groups.append(group)

        # 3. Free tables whose groups have finished dining
        restaurant.release_finished_tables(t)
        restaurant.refresh_reservations(t)

        # 4. Seat as many waiting groups as possible
        round_robin_index, _ = run_seating_round(
            restaurant, t, queue_ranges,
            queues=queues,
            round_robin_index=round_robin_index,
            use_round_robin=use_round_robin,
        )

        # 5. Track peak queue length
        q_len = len(restaurant.waiting_queue)
        if q_len > max_queue_length:
            max_queue_length = q_len

        # 6. Count occupied tables this tick for utilization
        occupied_ticks += sum(
            1 for table in restaurant.tables if not table.is_available(t)
        )
        reserved_table_ticks += sum(
            1
            for table in restaurant.tables
            if table.reserved_for_group is not None
            and table.reserved_until is not None
            and t <= table.reserved_until
        )

    total_reserved_groups = sum(1 for group in arrivals if group.is_reserved)
    served_reserved_groups = sum(1 for group in restaurant.completed_groups if group.is_reserved)
    served_reserved_with_priority_groups = sum(
        1 for group in restaurant.completed_groups if group.reservation_seated_with_priority
    )
    timeout_reserved_groups = sum(1 for group in arrivals if group.is_reserved and group.reservation_timed_out)
    reserved_capacity_ticks = restaurant.max_reserved_tables * total_ticks

    return SimulationResult(
        completed_groups=list(restaurant.completed_groups),
        left_groups=list(restaurant.left_groups),
        still_waiting=list(restaurant.waiting_queue),
        total_arrived=len(arrivals),
        max_queue_length=max_queue_length,
        occupied_ticks=occupied_ticks,
        total_ticks=total_ticks,
        total_tables=len(restaurant.tables),
        reservation_enabled=restaurant.reservation_enabled,
        total_reserved_groups=total_reserved_groups,
        served_reserved_groups=served_reserved_groups,
        served_reserved_with_priority_groups=served_reserved_with_priority_groups,
        timeout_reserved_groups=timeout_reserved_groups,
        reserved_table_ticks=reserved_table_ticks,
        reserved_capacity_ticks=reserved_capacity_ticks,
    )


def _add_group_to_strategy_queues(
    group: CustomerGroup,
    queues: Sequence[List[CustomerGroup]],
    queue_ranges: Sequence[QueueRange],
) -> None:
    try:
        idx = assign_queue_index(group.size, queue_ranges)
    except ValueError:
        return
    queues[idx].append(group)


def _remove_group_from_strategy_queues(
    group: CustomerGroup,
    queues: Sequence[List[CustomerGroup]],
    queue_ranges: Sequence[QueueRange],
) -> None:
    try:
        idx = assign_queue_index(group.size, queue_ranges)
    except ValueError:
        return
    if group in queues[idx]:
        queues[idx].remove(group)
