from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from models.customer_group import CustomerGroup


SCENARIO_PRESETS: Dict[str, Dict[str, object]] = {
    "fast": {
        "duration_range": (15, 35),
        "base_arrival_rate": 0.55,
    },
    "normal": {
        "duration_range": (35, 70),
        "base_arrival_rate": 0.35,
    },
    "slow": {
        "duration_range": (70, 120),
        "base_arrival_rate": 0.18,
    },
}

DEMAND_MULTIPLIER: Dict[str, float] = {
    "low": 0.65,
    "average": 1.00,
    "high": 1.55,
}

RESERVATION_RATE = 0.15
DEFAULT_RESERVATION_PROPORTION = 0.30
DEFAULT_RESERVATION_WINDOW_MINUTES = 5
DEFAULT_RESERVATION_HOLD_MINUTES = 10

# Size distribution:
# 1-person: 18%
# 2-person: 42%
# 3-person: 16%
# 4-person: 14%
# 5-person: 6%
# 6-person: 4%
GROUP_SIZE_WEIGHTS: List[Tuple[int, float]] = [
    (1, 0.18),
    (2, 0.42),
    (3, 0.16),
    (4, 0.14),
    (5, 0.06),
    (6, 0.04),
]

REFERENCE_TOTAL_SEATS = 44
REFERENCE_TABLE_COUNT = 12


def minutes_to_time(total_minutes: int) -> str:
    if total_minutes < 0:
        raise ValueError("Total minutes cannot be negative.")

    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def poisson_sample(lam: float) -> int:
    """
    Sample from Poisson(lam) using Knuth's algorithm.
    Works well for small per-minute arrival rates.
    """
    if lam <= 0:
        return 0

    threshold = math.exp(-lam)
    count = 0
    product = 1.0

    while product > threshold:
        count += 1
        product *= random.random()

    return count - 1


def _filtered_group_size_weights(max_group_size: int | None = None) -> List[Tuple[int, float]]:
    if max_group_size is not None and max_group_size <= 0:
        raise ValueError("max_group_size must be positive when provided.")

    eligible_sizes = GROUP_SIZE_WEIGHTS
    if max_group_size is not None:
        eligible_sizes = [
            (size, weight) for size, weight in GROUP_SIZE_WEIGHTS
            if size <= max_group_size
        ]
        if not eligible_sizes:
            raise ValueError("No group sizes fit within max_group_size.")

    return eligible_sizes


def restaurant_arrival_multiplier(table_capacities: List[int]) -> float:
    """
    Scale arrival intensity based on restaurant size.
    Uses both seat count and table count, damped so custom layouts do not swing too wildly.
    """
    if not table_capacities:
        return 1.0

    total_seats = sum(table_capacities)
    table_count = len(table_capacities)

    seat_factor = math.sqrt(total_seats / REFERENCE_TOTAL_SEATS)
    table_factor = math.sqrt(table_count / REFERENCE_TABLE_COUNT)

    seat_factor = min(1.75, max(0.55, seat_factor))
    table_factor = min(1.40, max(0.70, table_factor))

    return seat_factor * (0.70 + 0.30 * table_factor)


def adjusted_group_size_weights(
    table_capacities: List[int],
    max_group_size: int | None = None,
) -> List[Tuple[int, float]]:
    """
    Bias group sizes toward what the current table mix seats well.
    Larger groups become less likely when only a few tables can handle them.
    """
    base_weights = _filtered_group_size_weights(max_group_size=max_group_size)
    if not table_capacities:
        return base_weights

    total_tables = len(table_capacities)
    adjusted: List[Tuple[int, float]] = []

    for size, base_weight in base_weights:
        fitting_tables = sum(1 for capacity in table_capacities if capacity >= size)
        if fitting_tables == 0:
            continue

        exact_fit_tables = sum(1 for capacity in table_capacities if capacity == size)
        layout_factor = (
            0.35
            + (fitting_tables / total_tables)
            + 0.25 * (exact_fit_tables / total_tables)
        )
        adjusted.append((size, base_weight * layout_factor))

    if not adjusted:
        raise ValueError("No group sizes fit within the restaurant table layout.")

    return adjusted


def sample_group_size(
    max_group_size: int | None = None,
    size_weights: List[Tuple[int, float]] | None = None,
) -> int:
    eligible_sizes = size_weights or _filtered_group_size_weights(max_group_size=max_group_size)

    total_weight = sum(weight for _, weight in eligible_sizes)
    draw = random.random()
    cumulative = 0.0

    for size, weight in eligible_sizes:
        cumulative += weight / total_weight
        if draw <= cumulative:
            return size

    return eligible_sizes[-1][0]


def sample_dining_duration(service_speed: str, group_size: int) -> int:
    """
    Larger groups tend to stay longer.
    """
    low, high = SCENARIO_PRESETS[service_speed]["duration_range"]

    # Add extra time for larger groups
    extra = 0
    if group_size >= 5:
        extra = 15
    elif group_size == 4:
        extra = 10
    elif group_size == 3:
        extra = 5

    return random.randint(low + extra, high + extra)


def gaussian_peak(progress: float, center: float, spread: float, height: float) -> float:
    return height * math.exp(-((progress - center) ** 2) / spread)


def time_profile(progress: float, service_speed: str) -> float:
    """
    Returns a traffic multiplier based on time of day.
    progress = how far through the operating window we are, from 0 to 1.
    """
    # General restaurant traffic shape
    # - low opening trickle
    # - lunch peak
    # - afternoon lull
    # - dinner peak
    # - taper near closing

    base = 0.18

    lunch_peak = gaussian_peak(progress, center=0.22, spread=0.008, height=1.35)
    dinner_peak = gaussian_peak(progress, center=0.68, spread=0.015, height=1.10)

    # light opening traffic
    opening_bump = gaussian_peak(progress, center=0.08, spread=0.006, height=0.20)

    # taper near closing
    closing_drop = 1.0
    if progress > 0.90:
        closing_drop = max(0.20, 1.0 - (progress - 0.90) * 5.5)

    profile = (base + opening_bump + lunch_peak + dinner_peak) * closing_drop

    # Fast places have stronger lunch spikes
    if service_speed == "fast":
        profile *= 1.15
    elif service_speed == "slow":
        profile *= 0.85

    return profile


def generate_arrivals(
    opening_time: int,
    closing_time: int,
    service_speed: str,
    demand_level: str,
    seed: int | None = None,
    max_group_size: int | None = None,
    table_capacities: List[int] | None = None,
    reservation_enabled: bool = False,
    reservation_rate: float = RESERVATION_RATE,
    max_reserved_tables: int | None = None,
    reservation_window_minutes: int = DEFAULT_RESERVATION_WINDOW_MINUTES,
    reservation_hold_minutes: int = DEFAULT_RESERVATION_HOLD_MINUTES,
) -> List[CustomerGroup]:
    """
    Generate realistic arrivals for one day.

    Parameters:
        opening_time: integer minutes from 00:00
        closing_time: integer minutes from 00:00
        service_speed: fast / normal / slow
        demand_level: low / average / high
        seed: optional random seed
        max_group_size: optional cap on generated group sizes
        table_capacities: optional restaurant table capacities used to adapt demand and size mix
        reservation_enabled: whether reservation groups should be generated
        reservation_rate: probability that an eligible generated group is a reservation
        max_reserved_tables: hard cap of reservation groups generated
        reservation_window_minutes: expected arrival window around reservation time
        reservation_hold_minutes: reservation hold timeout after reservation time
    """
    service_speed = service_speed.lower().strip()
    demand_level = demand_level.lower().strip()

    if service_speed not in SCENARIO_PRESETS:
        raise ValueError("service_speed must be one of: fast, normal, slow")
    if demand_level not in DEMAND_MULTIPLIER:
        raise ValueError("demand_level must be one of: low, average, high")
    if closing_time <= opening_time:
        raise ValueError("Closing time must be later than opening time.")
    if reservation_rate < 0 or reservation_rate > 1:
        raise ValueError("reservation_rate must be between 0 and 1.")
    if reservation_window_minutes < 0:
        raise ValueError("reservation_window_minutes cannot be negative.")
    if reservation_hold_minutes <= 0:
        raise ValueError("reservation_hold_minutes must be positive.")

    if seed is not None:
        random.seed(seed)

    base_rate = float(SCENARIO_PRESETS[service_speed]["base_arrival_rate"])
    demand_multiplier = DEMAND_MULTIPLIER[demand_level]
    layout_multiplier = restaurant_arrival_multiplier(table_capacities or [])
    size_weights = adjusted_group_size_weights(
        table_capacities or [],
        max_group_size=max_group_size,
    )

    total_minutes = closing_time - opening_time
    arrivals: List[CustomerGroup] = []
    group_id = 1
    reserved_count = 0

    if reservation_enabled:
        if max_reserved_tables is None:
            if table_capacities:
                max_reserved_tables = int(DEFAULT_RESERVATION_PROPORTION * len(table_capacities))
            else:
                max_reserved_tables = 0
        max_reserved_tables = max(0, max_reserved_tables)
    else:
        max_reserved_tables = 0

    for minute in range(opening_time, closing_time + 1):
        progress = (minute - opening_time) / total_minutes

        lam = (
            base_rate
            * demand_multiplier
            * layout_multiplier
            * time_profile(progress, service_speed)
        )

        # Poisson arrivals this minute
        num_arrivals = poisson_sample(lam)

        for _ in range(num_arrivals):
            size = sample_group_size(
                max_group_size=max_group_size,
                size_weights=size_weights,
            )
            duration = sample_dining_duration(service_speed, size)
            arrival_time = minute
            is_reserved = False
            reservation_time = None
            reservation_expiry_time = None
            preferred_table_capacity = None

            if (
                reservation_enabled
                and reserved_count < max_reserved_tables
                and random.random() < reservation_rate
            ):
                is_reserved = True
                reservation_time = minute
                arrival_time = minute + random.randint(-reservation_window_minutes, reservation_window_minutes)
                arrival_time = max(opening_time, min(closing_time, arrival_time))
                reservation_expiry_time = reservation_time + reservation_hold_minutes

                if table_capacities:
                    suitable_caps = sorted({cap for cap in table_capacities if cap >= size})
                    if suitable_caps:
                        preferred_table_capacity = suitable_caps[0]

                reserved_count += 1

            arrivals.append(
                CustomerGroup(
                    group_id=group_id,
                    size=size,
                    arrival_time=arrival_time,
                    dining_duration=duration,
                    is_reserved=is_reserved,
                    reservation_time=reservation_time,
                    reservation_expiry_time=reservation_expiry_time,
                    preferred_table_capacity=preferred_table_capacity,
                )
            )
            group_id += 1

    arrivals.sort(key=lambda g: (g.arrival_time, g.group_id))
    for idx, group in enumerate(arrivals, 1):
        group.group_id = idx

    return arrivals


def save_arrivals_to_file(arrivals: List[CustomerGroup], filepath: str) -> None:
    """
    Save generated arrivals in parser-compatible format:
    group_id size arrival_time(HH:MM) dining_duration
    is_reserved reservation_time reservation_expiry_time preferred_table_id preferred_table_capacity
    """
    with open(filepath, "w", encoding="utf-8") as file:
        file.write(
            "# group_id size arrival_time dining_duration "
            "is_reserved reservation_time reservation_expiry_time "
            "preferred_table_id preferred_table_capacity\n"
        )
        for group in arrivals:
            reservation_time = (
                minutes_to_time(group.reservation_time)
                if group.reservation_time is not None
                else "-"
            )
            reservation_expiry_time = (
                minutes_to_time(group.reservation_expiry_time)
                if group.reservation_expiry_time is not None
                else "-"
            )
            preferred_table_id = (
                str(group.preferred_table_id)
                if group.preferred_table_id is not None
                else "-"
            )
            preferred_table_capacity = (
                str(group.preferred_table_capacity)
                if group.preferred_table_capacity is not None
                else "-"
            )
            file.write(
                f"{group.group_id} {group.size} "
                f"{minutes_to_time(group.arrival_time)} {group.dining_duration} "
                f"{1 if group.is_reserved else 0} {reservation_time} "
                f"{reservation_expiry_time} {preferred_table_id} {preferred_table_capacity}\n"
            )


def choose_generated_scenario() -> Tuple[str, str]:
    print("Choose service speed level:")
    print("1. Fast")
    print("2. Normal")
    print("3. Slow")
    speed_choice = input("Enter choice: ").strip()

    speed_map = {"1": "fast", "2": "normal", "3": "slow"}
    if speed_choice not in speed_map:
        raise ValueError("Invalid service speed choice.")

    print("Choose demand level:")
    print("1. Low")
    print("2. Average")
    print("3. High")
    demand_choice = input("Enter choice: ").strip()

    demand_map = {"1": "low", "2": "average", "3": "high"}
    if demand_choice not in demand_map:
        raise ValueError("Invalid demand level choice.")

    return speed_map[speed_choice], demand_map[demand_choice]


def preview_arrivals(arrivals: List[CustomerGroup], limit: int = 20) -> None:
    """
    Print a small preview to terminal.
    """
    print("group_id size arrival_time dining_duration")
    for group in arrivals[:limit]:
        print(
            group.group_id,
            group.size,
            minutes_to_time(group.arrival_time),
            group.dining_duration,
        )
