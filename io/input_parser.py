from __future__ import annotations

from typing import List

from models.customer_group import CustomerGroup
from models.restaurant import Restaurant
from models.table import Table


def time_to_minutes(time_str: str) -> int:
    """
    Convert HH:MM string to total minutes from 00:00.

    Example:
        "11:30" -> 690
    """
    try:
        hour_str, minute_str = time_str.strip().split(":")
        hours = int(hour_str)
        minutes = int(minute_str)
    except ValueError as exc:
        raise ValueError(f"Invalid time format: '{time_str}'. Expected HH:MM.") from exc

    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError(f"Invalid time value: '{time_str}'.")

    return hours * 60 + minutes


def minutes_to_time(total_minutes: int) -> str:
    """
    Convert total minutes from 00:00 back to HH:MM format.
    """
    if total_minutes < 0:
        raise ValueError("Total minutes cannot be negative.")

    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}:{minutes:02d}"


def build_tables_from_counts(
    num_2_seat: int,
    num_4_seat: int,
    num_6_seat: int
) -> List[Table]:
    """
    Build a list of Table objects from user-input table counts.
    """
    if num_2_seat < 0 or num_4_seat < 0 or num_6_seat < 0:
        raise ValueError("Number of tables cannot be negative.")

    tables: List[Table] = []
    table_id = 1

    for _ in range(num_2_seat):
        tables.append(Table(table_id=table_id, capacity=2))
        table_id += 1

    for _ in range(num_4_seat):
        tables.append(Table(table_id=table_id, capacity=4))
        table_id += 1

    for _ in range(num_6_seat):
        tables.append(Table(table_id=table_id, capacity=6))
        table_id += 1

    if not tables:
        raise ValueError("Restaurant must have at least one table.")

    return tables


def build_restaurant_from_user_input() -> Restaurant:
    """
    Interactively build a Restaurant object from user input.
    """
    name = input("Enter restaurant name: ").strip()

    open_time_str = input("Enter opening time (HH:MM): ").strip()
    close_time_str = input("Enter closing time (HH:MM): ").strip()

    opening_time = time_to_minutes(open_time_str)
    closing_time = time_to_minutes(close_time_str)

    if closing_time <= opening_time:
        raise ValueError("Closing time must be later than opening time.")

    num_2_seat = int(input("Enter number of 2-seat tables: ").strip())
    num_4_seat = int(input("Enter number of 4-seat tables: ").strip())
    num_6_seat = int(input("Enter number of 6-seat tables: ").strip())

    tables = build_tables_from_counts(
        num_2_seat=num_2_seat,
        num_4_seat=num_4_seat,
        num_6_seat=num_6_seat
    )

    restaurant = Restaurant(name=name, tables=tables)
    restaurant.opening_time = opening_time
    restaurant.closing_time = closing_time

    return restaurant


def parse_arrivals(filepath: str) -> List[CustomerGroup]:
    """
    Parse customer arrival file.

    Expected format:
        group_id size arrival_time dining_duration

    Example:
        1 2 11:30 45
        2 4 11:45 60
        3 3 12:10 40
    """
    groups: List[CustomerGroup] = []

    with open(filepath, "r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            parts = line.split()

            if len(parts) != 4:
                raise ValueError(
                    f"Invalid arrival format at line {line_number}: '{line}'"
                )

            try:
                group_id = int(parts[0])
                size = int(parts[1])
                arrival_time = time_to_minutes(parts[2])
                dining_duration = int(parts[3])
            except ValueError as exc:
                raise ValueError(
                    f"Invalid arrival data at line {line_number}: '{line}'"
                ) from exc

            groups.append(
                CustomerGroup(
                    group_id=group_id,
                    size=size,
                    arrival_time=arrival_time,
                    dining_duration=dining_duration,
                )
            )

    return groups


def validate_arrivals(restaurant: Restaurant, groups: List[CustomerGroup]) -> None:
    """
    Ensure all arrivals occur within operating hours.
    """
    opening_time = getattr(restaurant, "opening_time", None)
    closing_time = getattr(restaurant, "closing_time", None)

    if opening_time is None or closing_time is None:
        raise ValueError("Restaurant must have opening_time and closing_time defined.")

    for group in groups:
        if group.arrival_time < opening_time or group.arrival_time > closing_time:
            raise ValueError(
                f"Group {group.group_id} arrives at "
                f"{minutes_to_time(group.arrival_time)}, "
                f"which is outside operating hours."
            )


def load_scenario_from_user_input(arrivals_path: str):
    """
    Build restaurant from user input and load arrivals from file.
    """
    restaurant = build_restaurant_from_user_input()
    groups = parse_arrivals(arrivals_path)
    validate_arrivals(restaurant, groups)
    return restaurant, groups