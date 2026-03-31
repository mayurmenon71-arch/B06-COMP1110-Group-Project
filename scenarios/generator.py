from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from models.customer_group import CustomerGroup


SCENARIO_PRESETS: Dict[str, Dict[str, object]] = {
    "fast": {
        "duration_range": (15, 35),
        "base_arrival_rate": 0.80,
    },
    "normal": {
        "duration_range": (35, 70),
        "base_arrival_rate": 0.50,
    },
    "slow": {
        "duration_range": (70, 120),
        "base_arrival_rate": 0.25,
    },
}

DEMAND_MULTIPLIER: Dict[str, float] = {
    "low": 0.60,
    "average": 1.00,
    "high": 1.60,
}

# Probabilities for group sizes 1, 2, 3, 4, 5, 6
GROUP_SIZE_WEIGHTS: List[Tuple[int, float]] = [
    (1, 0.20),
    (2, 0.45),
    (3, 0.15),
    (4, 0.12),
    (5, 0.05),
    (6, 0.03),
]


def minutes_to_time(total_minutes: int) -> str:
    if total_minutes < 0:
        raise ValueError("Total minutes cannot be negative.")
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def poisson_sample(lam: float) -> int:
    """Draw one sample from a Poisson distribution using Knuth's algorithm."""
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
    """Draw one group size using realistic restaurant group-size probabilities."""
    draw = random.random()
    cumulative = 0.0

    for size, weight in GROUP_SIZE_WEIGHTS:
        cumulative += weight
        if draw <= cumulative:
            return size

    return 2


def sample_dining_duration(service_speed: str) -> int:
    """Sample one dining duration based on the selected service speed."""
    low, high = SCENARIO_PRESETS[service_speed]["duration_range"]
    return random.randint(low, high)


def peak_factor(current_minute: int, opening_time: int, closing_time: int) -> float:
    """
    Create realistic within-day peaks:
    - mild traffic after opening
    - lunch spike near midday
    - afternoon lull
    - dinner spike in early evening
    """
    total = max(1, closing_time - opening_time)
    progress = (current_minute - opening_time) / total

    lunch_peak = math.exp(-((progress - 0.25) ** 2) / 0.01)
    dinner_peak = math.exp(-((progress - 0.70) ** 2) / 0.02)

    return 0.35 + 1.20 * lunch_peak + 0.95 * dinner_peak


def generate_arrivals(
    opening_time: int,
    closing_time: int,
    service_speed: str,
    demand_level: str,
    seed: int | None = None,
) -> List[CustomerGroup]:
    """
    Generate a full-day arrival list using:
    - service speed: fast / normal / slow
    - demand level: low / average / high
    """
    service_speed = service_speed.lower().strip()
    demand_level = demand_level.lower().strip()

    if service_speed not in SCENARIO_PRESETS:
        raise ValueError("service_speed must be one of: fast, normal, slow")
    if demand_level not in DEMAND_MULTIPLIER:
        raise ValueError("demand_level must be one of: low, average, high")

    if seed is not None:
        random.seed(seed)

    if closing_time <= opening_time:
        raise ValueError("Closing time must be later than opening time.")

    base_rate = float(SCENARIO_PRESETS[service_speed]["base_arrival_rate"])
    multiplier = DEMAND_MULTIPLIER[demand_level]

    arrivals: List[CustomerGroup] = []
    group_id = 1

    for minute in range(opening_time, closing_time + 1):
        lam = base_rate * multiplier * peak_factor(minute, opening_time, closing_time)
        num_arrivals = poisson_sample(lam)

        for _ in range(num_arrivals):
            size = sample_group_size()
            duration = sample_dining_duration(service_speed)

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
        for group in arrivals:
            file.write(
                f"{group.group_id} {group.size} "
                f"{minutes_to_time(group.arrival_time)} {group.dining_duration}\n"
            )


def choose_generated_scenario() -> Tuple[str, str]:
    """Simple text-based scenario picker."""
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
