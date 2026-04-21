"""
Event-compatible abandonment model for physical restaurant queues.

Research rationale:
- Longer restaurant waits are associated with reneging behavior and worse downstream
  customer behavior.
- Waiting tolerance weakens meaningfully around 15 minutes.
- A practical upper patience boundary for many diners is around 30 minutes.

These motivate a cumulative curve that rises gradually at first, then more sharply
after 15 minutes. The curve values are cumulative probabilities, not per-event or
per-minute probabilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from models.customer_group import CustomerGroup


ABANDONMENT_CURVE = [
    (5, 0.02),
    (10, 0.08),
    (15, 0.18),
    (20, 0.35),
    (25, 0.55),
    (30, 0.72),
    (float("inf"), 0.85),
]

RESERVATION_MULTIPLIER = 0.65
ABANDONMENT_CAP = 0.95


class SupportsRandom(Protocol):
    def random(self) -> float:
        ...


@dataclass(frozen=True)
class AbandonmentConfig:
    abandonment_curve: tuple[tuple[float, float], ...] = tuple(ABANDONMENT_CURVE)
    reservation_multiplier: float = RESERVATION_MULTIPLIER
    abandonment_cap: float = ABANDONMENT_CAP


def get_base_cumulative_abandonment(wait_time: int | float) -> float:
    if wait_time < 5:
        return 0.02
    elif wait_time < 10:
        return 0.08
    elif wait_time < 15:
        return 0.18
    elif wait_time < 20:
        return 0.35
    elif wait_time < 25:
        return 0.55
    elif wait_time < 30:
        return 0.72
    else:
        return 0.85


def get_adjusted_cumulative_abandonment(
    group: CustomerGroup,
    wait_time: int | float,
    config: AbandonmentConfig,
) -> float:
    p = get_base_cumulative_abandonment(wait_time)
    if group.is_reserved:
        p *= config.reservation_multiplier
    return min(p, config.abandonment_cap)


def get_incremental_abandonment_probability(p_now: float, p_prev: float) -> float:
    if p_now <= p_prev:
        return 0.0
    if p_prev >= 1.0:
        return 0.0
    return (p_now - p_prev) / (1 - p_prev)


def should_group_abandon(
    group: CustomerGroup,
    current_time: int,
    rng: SupportsRandom,
    config: AbandonmentConfig,
) -> bool:
    wait_time = current_time - group.arrival_time
    if wait_time < 0:
        return False

    p_now = get_adjusted_cumulative_abandonment(group, wait_time, config)
    p_prev = group.last_cumulative_abandonment_prob

    incremental_p = get_incremental_abandonment_probability(p_now, p_prev)
    if incremental_p <= 0:
        return False

    group.last_cumulative_abandonment_prob = p_now
    return rng.random() < incremental_p
