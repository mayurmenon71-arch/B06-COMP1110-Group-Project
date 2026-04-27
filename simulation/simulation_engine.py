"""
Core simulation engine: drives event-compatible restaurant queue simulation.

Usage:
    result = run_simulation(restaurant, arrivals, queue_ranges)

The restaurant object is mutated in place. Pass a deep copy if you need
to run multiple strategies on the same scenario:

    import copy
    result = run_simulation(copy.deepcopy(restaurant), copy.deepcopy(arrivals), ranges)
"""
from __future__ import annotations

import random as random_module
from dataclasses import dataclass, field
from typing import List, Sequence

from models.customer_group import CustomerGroup
from models.restaurant import Restaurant
from models.table_assignment import run_seating_round
from models.queue_strategies import QueueRange, assign_queue_index
from simulation.abandonment import (
    AbandonmentConfig,
    SupportsRandom,
    should_group_abandon,
)


@dataclass
class SimulationResult:
    """Holds all output data from one simulation run."""

    completed_groups: List[CustomerGroup]
    left_groups: List[CustomerGroup]
    still_waiting: List[CustomerGroup]
    total_arrived: int
    max_queue_length: int
    occupied_ticks: int
    total_ticks: int
    total_tables: int
    reservation_enabled: bool
    total_reserved_groups: int
    served_reserved_groups: int
    served_reserved_with_priority_groups: int
    timeout_reserved_groups: int
    reserved_table_ticks: int
    reserved_capacity_ticks: int
    total_abandoned_groups: int = 0
    abandoned_reserved_groups: int = 0
    abandoned_walkin_groups: int = 0
    abandoned_covers: int = 0
    abandonment_wait_buckets: dict[str, int] = field(default_factory=dict)


def run_simulation(
    restaurant: Restaurant,
    arrivals: List[CustomerGroup],
    queue_ranges: Sequence[QueueRange],
    dropout_threshold: int | None = None,
    use_round_robin: bool = False,
    abandonment_config: AbandonmentConfig | None = None,
    rng: SupportsRandom | None = None,
) -> SimulationResult:
    """
    Run the restaurant queue simulation.

    ``dropout_threshold`` is retained for call-site compatibility. Abandonment is
    now handled by a cumulative waiting-time model checked at event-processing
    points, rather than a fixed 30-minute cutoff.
    """
    max_queue_length = 0
    occupied_ticks = 0
    reserved_table_ticks = 0
    total_ticks = restaurant.closing_time - restaurant.opening_time
    queues: List[List[CustomerGroup]] = [[] for _ in queue_ranges]
    round_robin_index = 0
    abandonment_config = abandonment_config or AbandonmentConfig()
    rng = rng or random_module

    arrivals_by_minute: dict[int, List[CustomerGroup]] = {}
    for group in arrivals:
        arrivals_by_minute.setdefault(group.arrival_time, []).append(group)

    for t in range(restaurant.opening_time, restaurant.closing_time + 1):
        event_happened = False

        arriving_groups = arrivals_by_minute.get(t, [])
        for group in arriving_groups:
            group.last_cumulative_abandonment_prob = 0.0
            restaurant.add_group_to_queue(group)
            _add_group_to_strategy_queues(group, queues, queue_ranges)
            event_happened = True

        if arriving_groups:
            _process_abandonment_event(
                restaurant,
                queues,
                queue_ranges,
                t,
                rng,
                abandonment_config,
            )

        released_tables = restaurant.release_finished_tables(t)
        reservation_event = _has_reservation_event(restaurant, t)
        restaurant.refresh_reservations(t)

        if released_tables or reservation_event:
            event_happened = True
            _process_abandonment_event(
                restaurant,
                queues,
                queue_ranges,
                t,
                rng,
                abandonment_config,
            )

        if event_happened and restaurant.waiting_queue:
            _process_abandonment_event(
                restaurant,
                queues,
                queue_ranges,
                t,
                rng,
                abandonment_config,
            )

            def before_select_group() -> None:
                _process_abandonment_event(
                    restaurant,
                    queues,
                    queue_ranges,
                    t,
                    rng,
                    abandonment_config,
                )

            round_robin_index, _ = run_seating_round(
                restaurant,
                t,
                queue_ranges,
                queues=queues,
                round_robin_index=round_robin_index,
                use_round_robin=use_round_robin,
                before_select_group=before_select_group,
            )

        q_len = len(restaurant.waiting_queue)
        if q_len > max_queue_length:
            max_queue_length = q_len

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
    abandonment_buckets = _abandonment_wait_buckets(restaurant.left_groups)

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
        total_abandoned_groups=len(restaurant.left_groups),
        abandoned_reserved_groups=sum(1 for group in restaurant.left_groups if group.is_reserved),
        abandoned_walkin_groups=sum(1 for group in restaurant.left_groups if not group.is_reserved),
        abandoned_covers=sum(group.size for group in restaurant.left_groups),
        abandonment_wait_buckets=abandonment_buckets,
    )


def _process_abandonment_event(
    restaurant: Restaurant,
    queues: Sequence[List[CustomerGroup]],
    queue_ranges: Sequence[QueueRange],
    current_time: int,
    rng: SupportsRandom,
    config: AbandonmentConfig,
) -> None:
    for group in list(restaurant.waiting_queue):
        if should_group_abandon(group, current_time, rng, config):
            _abandon_group(restaurant, group, queues, queue_ranges, current_time)


def _abandon_group(
    restaurant: Restaurant,
    group: CustomerGroup,
    queues: Sequence[List[CustomerGroup]],
    queue_ranges: Sequence[QueueRange],
    current_time: int,
) -> None:
    group.leave_queue(current_time)
    if group in restaurant.waiting_queue:
        restaurant.waiting_queue.remove(group)
    _remove_group_from_strategy_queues(group, queues, queue_ranges)
    restaurant.release_reservation_for_group(group.group_id, mark_timeout=False)
    restaurant.left_groups.append(group)


def _has_reservation_event(restaurant: Restaurant, current_time: int) -> bool:
    if not restaurant.reservation_enabled:
        return False
    for group in restaurant.waiting_queue:
        if group.reservation_priority_lost:
            continue
        if group.reservation_expiry_time is not None and current_time > group.reservation_expiry_time:
            return True
    for table in restaurant.tables:
        if table.reserved_until is not None and current_time > table.reserved_until:
            return True
    return False


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


def _abandonment_wait_buckets(groups: Sequence[CustomerGroup]) -> dict[str, int]:
    buckets = {
        "<5": 0,
        "5-10": 0,
        "10-15": 0,
        "15-20": 0,
        "20-25": 0,
        "25-30": 0,
        "30+": 0,
    }

    for group in groups:
        if group.leave_time is None:
            continue
        wait_time = group.leave_time - group.arrival_time
        if wait_time < 5:
            buckets["<5"] += 1
        elif wait_time < 10:
            buckets["5-10"] += 1
        elif wait_time < 15:
            buckets["10-15"] += 1
        elif wait_time < 20:
            buckets["15-20"] += 1
        elif wait_time < 25:
            buckets["20-25"] += 1
        elif wait_time < 30:
            buckets["25-30"] += 1
        else:
            buckets["30+"] += 1

    return buckets
