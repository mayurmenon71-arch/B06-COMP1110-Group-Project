"""
Input validation for restaurant configs and arrival data.
"""
from __future__ import annotations

from typing import List

from models.customer_group import CustomerGroup
from models.restaurant import Restaurant


def validate_restaurant(restaurant: Restaurant) -> None:
    """
    Raise ValueError if the restaurant config is invalid.
    Checks: at least one table, positive capacities, valid opening hours.
    """
    if not restaurant.tables:
        raise ValueError("Restaurant must have at least one table.")
    if restaurant.closing_time <= restaurant.opening_time:
        raise ValueError("Closing time must be later than opening time.")
    if restaurant.reservation_proportion < 0 or restaurant.reservation_proportion > 1:
        raise ValueError("Reservation proportion must be between 0 and 1.")
    if restaurant.reservation_hold_minutes <= 0:
        raise ValueError("Reservation hold duration must be positive.")
    if restaurant.reservation_window_minutes < 0:
        raise ValueError("Reservation arrival window cannot be negative.")
    if restaurant.reservation_fairness_wait_threshold < 0:
        raise ValueError("Reservation fairness threshold cannot be negative.")
    for table in restaurant.tables:
        if table.capacity <= 0:
            raise ValueError(f"Table {table.table_id} has invalid capacity {table.capacity}.")


def validate_arrivals(groups: List[CustomerGroup], restaurant: Restaurant) -> None:
    """
    Raise ValueError if any arrival data is invalid.
    Checks: positive group sizes, arrival times within operating hours,
    and warns if any group is larger than the largest table.
    """
    if not groups:
        raise ValueError("Arrivals list is empty — no customer groups to simulate.")

    max_capacity = max(t.capacity for t in restaurant.tables)

    for g in groups:
        if g.size <= 0:
            raise ValueError(f"Group {g.group_id} has invalid size {g.size}.")
        if g.dining_duration <= 0:
            raise ValueError(f"Group {g.group_id} has invalid dining duration {g.dining_duration}.")
        if g.arrival_time < restaurant.opening_time:
            raise ValueError(
                f"Group {g.group_id} arrives at {g.arrival_time} before opening time {restaurant.opening_time}."
            )
        if g.arrival_time > restaurant.closing_time:
            raise ValueError(
                f"Group {g.group_id} arrives at {g.arrival_time} after closing time {restaurant.closing_time}."
            )
        if g.is_reserved:
            if g.reservation_time is None:
                raise ValueError(f"Reserved group {g.group_id} is missing reservation_time.")
            if g.reservation_expiry_time is None:
                raise ValueError(f"Reserved group {g.group_id} is missing reservation_expiry_time.")
            if g.reservation_expiry_time < g.reservation_time:
                raise ValueError(
                    f"Reserved group {g.group_id} has expiry before reservation time."
                )
            if g.preferred_table_capacity is not None and g.preferred_table_capacity < g.size:
                raise ValueError(
                    f"Reserved group {g.group_id} has preferred table capacity "
                    f"{g.preferred_table_capacity} smaller than group size {g.size}."
                )
        if g.size > max_capacity:
            print(
                f"Warning: Group {g.group_id} (size {g.size}) exceeds max table capacity "
                f"({max_capacity}). They will drop out."
            )
