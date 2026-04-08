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


def sample_group_size() -> int:
    draw = random.random()
    cumulative = 0.0

    for size, weight in GROUP_SIZE_WEIGHTS:
        cumulative += weight
        if draw <= cumulative:
            return size

    return 2


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
) -> List[CustomerGroup]:
    """
    Generate realistic arrivals for one day.

    Parameters:
        opening_time: integer minutes from 00:00
        closing_time: integer minutes from 00:00
        service_speed: fast / normal / slow
        demand_level: low / average / high
        seed: optional random seed
    """
    service_speed = service_speed.lower().strip()
    demand_level = demand_level.lower().strip()

    if service_speed not in SCENARIO_PRESETS:
        raise ValueError("service_speed must be one of: fast, normal, slow")
    if demand_level not in DEMAND_MULTIPLIER:
        raise ValueError("demand_level must be one of: low, average, high")
    if closing_time <= opening_time:
        raise ValueError("Closing time must be later than opening time.")

    if seed is not None:
        random.seed(seed)

    base_rate = float(SCENARIO_PRESETS[service_speed]["base_arrival_rate"])
    demand_multiplier = DEMAND_MULTIPLIER[demand_level]

    total_minutes = closing_time - opening_time
    arrivals: List[CustomerGroup] = []
    group_id = 1

    for minute in range(opening_time, closing_time + 1):
        progress = (minute - opening_time) / total_minutes

        lam = base_rate * demand_multiplier * time_profile(progress, service_speed)

        # Poisson arrivals this minute
        num_arrivals = poisson_sample(lam)

        for _ in range(num_arrivals):
            size = sample_group_size()
            duration = sample_dining_duration(service_speed, size)

            arrivals.append(
                CustomerGroup(
                    group_id=group_id,
                    size=size,
                    arrival_time=minute,
                    dining_duration=duration,
                )
            )
            group_id += 1

    return arrivals


def save_arrivals_to_file(arrivals: List[CustomerGroup], filepath: str) -> None:
    """
    Save generated arrivals in parser-compatible format:
    group_id size arrival_time(HH:MM) dining_duration
    """
    with open(filepath, "w", encoding="utf-8") as file:
        file.write("# group_id size arrival_time dining_duration\n")
        for group in arrivals:
            file.write(
                f"{group.group_id} {group.size} "
                f"{minutes_to_time(group.arrival_time)} {group.dining_duration}\n"
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