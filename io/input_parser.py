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
from typing import List

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
    Example:
        1 3 12:05 45
    """
    lines = _non_comment_lines(filepath)
    groups: List[CustomerGroup] = []

    for line in lines:
        parts = line.split()
        if len(parts) != 4:
            raise ValueError(
                f"Expected 'group_id size HH:MM dining_duration' but got: '{line}'"
            )
        group_id = int(parts[0])
        size = int(parts[1])
        arrival_time = _time_to_minutes(parts[2])
        dining_duration = int(parts[3])

        groups.append(CustomerGroup(
            group_id=group_id,
            size=size,
            arrival_time=arrival_time,
            dining_duration=dining_duration,
        ))

    return groups
