"""
File input parsing: read restaurant config and customer arrival files.

Restaurant config format (config/restaurant_*.txt):
    # comments are ignored
    Small Cafe                      <- restaurant name
    660 1320                        <- opening_time closing_time (minutes from midnight)
    2 6                             <- capacity count (one line per table type)
    4 2

Arrivals format (scenarios/arrivals_*.txt):
    # group_id size arrival_time dining_duration
    1 3 12:05 45
    2 1 12:07 30
"""
from __future__ import annotations

import os
from typing import List, Optional

from models.customer_group import CustomerGroup
from models.restaurant import Restaurant
from models.table import Table


def _time_to_minutes(time_str: str) -> int:
    """Convert HH:MM string to integer minutes from midnight."""
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM.")
    hours, minutes = int(parts[0]), int(parts[1])
    return hours * 60 + minutes


def _parse_optional_time(value: str) -> Optional[int]:
    token = value.strip()
    if token in {"-", "none", "None", ""}:
        return None
    return _time_to_minutes(token)


def _parse_optional_int(value: str) -> Optional[int]:
    token = value.strip()
    if token in {"-", "none", "None", ""}:
        return None
    return int(token)


def _parse_bool(value: str) -> bool:
    token = value.strip().lower()
    if token in {"1", "true", "t", "y", "yes", "reserved", "r"}:
        return True
    if token in {"0", "false", "f", "n", "no", "walkin", "w"}:
        return False
    raise ValueError(f"Invalid boolean value '{value}'.")


def _non_comment_lines(filepath: str) -> List[str]:
    """Read file and return non-empty, non-comment lines."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    lines = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
    return lines


def parse_restaurant_config(filepath: str) -> Restaurant:
    """
    Parse a restaurant config file and return a Restaurant object.

    Expected format (non-comment lines in order):
        1. Restaurant name (string)
        2. opening_time closing_time (two integers, minutes from midnight)
        3+. capacity count (one pair per line, repeated for each table type)

    Tables are assigned sequential IDs starting from 1.
    """
    lines = _non_comment_lines(filepath)
    if len(lines) < 3:
        raise ValueError(
            f"Config file '{filepath}' is too short. "
            "Expected: name, opening/closing times, then table lines."
        )

    name = lines[0]

    time_parts = lines[1].split()
    if len(time_parts) != 2:
        raise ValueError(f"Expected 'opening_time closing_time' on line 2, got: '{lines[1]}'")
    opening_time, closing_time = int(time_parts[0]), int(time_parts[1])

    tables: List[Table] = []
    table_id = 1
    for line in lines[2:]:
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Expected 'capacity count' but got: '{line}'")
        capacity, count = int(parts[0]), int(parts[1])
        for _ in range(count):
            tables.append(Table(table_id=table_id, capacity=capacity))
            table_id += 1

    return Restaurant(
        name=name,
        opening_time=opening_time,
        closing_time=closing_time,
        tables=tables,
    )


def parse_arrivals(filepath: str) -> List[CustomerGroup]:
    """
    Parse a customer arrivals file and return a list of CustomerGroup objects.

    Expected format per non-comment line:
        group_id size HH:MM dining_duration
    Optional reservation columns:
        is_reserved reservation_time reservation_expiry_time preferred_table_id preferred_table_capacity
    Example:
        1 3 12:05 45
        2 4 18:02 60 1 18:00 18:10 - 4
    """
    lines = _non_comment_lines(filepath)
    groups: List[CustomerGroup] = []

    for line in lines:
        parts = line.split()
        if len(parts) not in {4, 9}:
            raise ValueError(
                "Expected either "
                "'group_id size HH:MM dining_duration' or "
                "'group_id size HH:MM dining_duration is_reserved reservation_time "
                "reservation_expiry_time preferred_table_id preferred_table_capacity' "
                f"but got: '{line}'"
            )
        group_id = int(parts[0])
        size = int(parts[1])
        arrival_time = _time_to_minutes(parts[2])
        dining_duration = int(parts[3])
        is_reserved = False
        reservation_time = None
        reservation_expiry_time = None
        preferred_table_id = None
        preferred_table_capacity = None

        if len(parts) == 9:
            is_reserved = _parse_bool(parts[4])
            reservation_time = _parse_optional_time(parts[5])
            reservation_expiry_time = _parse_optional_time(parts[6])
            preferred_table_id = _parse_optional_int(parts[7])
            preferred_table_capacity = _parse_optional_int(parts[8])

        groups.append(
            CustomerGroup(
                group_id=group_id,
                size=size,
                arrival_time=arrival_time,
                dining_duration=dining_duration,
                is_reserved=is_reserved,
                reservation_time=reservation_time,
                reservation_expiry_time=reservation_expiry_time,
                preferred_table_id=preferred_table_id,
                preferred_table_capacity=preferred_table_capacity,
            )
        )

    return groups


def prompt_reservation_settings(restaurant: Restaurant) -> None:
    """
    Interactive reservation setup used by the CLI after loading/creating a restaurant.
    """
    while True:
        raw = input("  Enable reservation system? (y/n) [n]: ").strip().lower()
        if raw in {"", "n", "no"}:
            restaurant.configure_reservations(enabled=False)
            return
        if raw in {"y", "yes"}:
            break
        print("  Please enter y or n.")

    default_percent = int(restaurant.reservation_proportion * 100)
    while True:
        raw = input(f"  Reservation proportion % [{default_percent}]: ").strip()
        if not raw:
            percent = default_percent
            break
        try:
            percent = int(raw)
            if 0 <= percent <= 100:
                break
        except ValueError:
            pass
        print("  Please enter an integer from 0 to 100.")

    while True:
        raw = input(f"  Reservation hold duration minutes [{restaurant.reservation_hold_minutes}]: ").strip()
        if not raw:
            hold_minutes = restaurant.reservation_hold_minutes
            break
        try:
            hold_minutes = int(raw)
            if hold_minutes > 0:
                break
        except ValueError:
            pass
        print("  Please enter a positive whole number.")

    restaurant.configure_reservations(
        enabled=True,
        proportion=percent / 100.0,
        hold_minutes=hold_minutes,
    )
