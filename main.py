"""
Restaurant Queue Simulation — main entry point.
Run with: python main.py
"""
from __future__ import annotations

import copy
import os
import sys
from typing import List, Optional, Tuple

from models.restaurant import Restaurant
from models.table import Table
from models.queue_stratgies import (
    QueueRange,
    default_single_queue_range,
    default_multi_queue_ranges,
    parse_queue_ranges,
)

# The local 'io/' folder conflicts with Python's stdlib 'io' module.
# We import from the local files directly by temporarily adding io/ to sys.path.
_IO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "io")
sys.path.insert(0, _IO_DIR)
from input_parser import (
    parse_restaurant_config,
    parse_arrivals,
    prompt_reservation_settings,
    _non_comment_lines,
)
from validator import validate_restaurant, validate_arrivals
sys.path.pop(0)

from simulation.simulation_engine import run_simulation, SimulationResult
from metrics.metrics import print_summary, compare_strategies


# ── built-in presets ──────────────────────────────────────────────────────────

CONFIG_PRESETS = [
    ("Small Cafe",          "config/restaurant_small.txt"),
    ("Medium Restaurant",   "config/restaurant_medium.txt"),
    ("Large Dim Sum Hall",  "config/restaurant_large.txt"),
]

SCENARIO_PRESETS = [
    ("Small cafe, low demand",        "scenarios/arrivals_small_low.txt"),
    ("Medium restaurant, normal demand", "scenarios/arrivals_medium_normal.txt"),
    ("Peak-hour, high demand",        "scenarios/arrivals_peak_high.txt"),
]


STRATEGY_OPTIONS: List[Tuple[str, tuple, bool]] = [
    ("Single Queue FCFS  (all groups, one queue)",       default_single_queue_range(),                     False),
    ("Size-Based FCFS    (1-2 / 3-4 / 5+ queues)",      default_multi_queue_ranges(),                     False),
    ("Fine-Grained FCFS  (1 / 2 / 3-4 / 5+ queues)",   parse_queue_ranges([(1,1),(2,2),(3,4),(5,None)]), False),
    ("Round-Robin FCFS   (1-2 / 3-4 / 5+ rotating)",   default_multi_queue_ranges(),                     True),
]

DEFAULT_OPENING_TIME = 11 * 60
DEFAULT_CLOSING_TIME = 22 * 60
TEMP_SCENARIO_PATH = "scenarios/temp_scenario.txt"


# ── helpers ───────────────────────────────────────────────────────────────────

def _divider(char: str = "─", width: int = 50) -> None:
    try:
        print(char * width)
    except UnicodeEncodeError:
        print("-" * width)


def _minutes_to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _parse_time_input(raw: str) -> int:
    value = raw.strip()
    if not value:
        raise ValueError("Time cannot be empty.")

    if ":" in value:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("Use HH:MM format, e.g. 22:00.")
        hours = int(parts[0])
        minutes = int(parts[1])
        if not (0 <= hours <= 24 and 0 <= minutes < 60):
            raise ValueError("Time must be between 00:00 and 24:00.")
        if hours == 24 and minutes != 0:
            raise ValueError("24:00 is the latest valid HH:MM time.")
        return hours * 60 + minutes

    total_minutes = int(value)
    if not (0 <= total_minutes <= 24 * 60):
        raise ValueError("Minutes must be between 0 and 1440.")
    return total_minutes


def _prompt_non_empty(prompt: str, default: Optional[str] = None) -> str:
    while True:
        raw = input(prompt).strip()
        if raw:
            return raw
        if default is not None:
            return default
        print("  Input cannot be empty.")


def _prompt_positive_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
            if value > 0:
                return value
        except ValueError:
            pass
        print("  Please enter a positive whole number.")


def _prompt_time(prompt: str, default_minutes: Optional[int] = None) -> int:
    while True:
        if default_minutes is None:
            raw = input(prompt).strip()
        else:
            default_label = _minutes_to_hhmm(default_minutes)
            raw = input(f"{prompt} [{default_label}]: ").strip()
            if not raw:
                return default_minutes

        try:
            return _parse_time_input(raw)
        except ValueError as e:
            print(f"  {e}")


def _print_header() -> None:
    _divider("=", 50)
    print("   Restaurant Queue Simulation")
    _divider("=", 50)


def _print_menu(loaded_config: Optional[str], loaded_scenario: Optional[str],
                selected_strategies: List[str]) -> None:
    print()
    _divider()
    config_label  = f" [{loaded_config}]"  if loaded_config  else " (none)"
    scenario_label = f" [{loaded_scenario}]" if loaded_scenario else " (none)"
    strategy_label = f" [{', '.join(selected_strategies)}]" if selected_strategies else " (none)"
    print(f"  1. Load restaurant configuration{config_label}")
    print(f"  2. Select queue strategy{strategy_label}")
    print(f"  3. Choose arrival scenario{scenario_label}")
    print(f"  4. Run simulation")
    print(f"  5. View results")
    print(f"  6. Exit")
    _divider()


def _choose_from_list(options: List[str], prompt: str,
                      allow_multiple: bool = False) -> List[int]:
    """Display numbered options and return list of chosen 0-based indices."""
    for i, opt in enumerate(options, 1):
        print(f"  [{i}] {opt}")
    while True:
        raw = input(f"\n{prompt}: ").strip()
        try:
            if allow_multiple:
                indices = [int(x.strip()) - 1 for x in raw.split(",")]
            else:
                indices = [int(raw) - 1]
            if all(0 <= idx < len(options) for idx in indices):
                return indices
        except ValueError:
            pass
        print(f"  Invalid input. Enter a number between 1 and {len(options)}.")


# ── menu actions ──────────────────────────────────────────────────────────────

def load_config(state: dict) -> None:
    print("\nAvailable configurations:")
    options = [f"{name}  ({_describe_config(path)})" for name, path in CONFIG_PRESETS]
    options.append("Create custom configuration")
    options.append("Load from file path")
    idx = _choose_from_list(options, "Select configuration")[0]

    if idx < len(CONFIG_PRESETS):
        name, path = CONFIG_PRESETS[idx]
        filepath = path
        try:
            restaurant = parse_restaurant_config(filepath)
        except (FileNotFoundError, ValueError) as e:
            print(f"  Error: {e}")
            return
    elif idx == len(CONFIG_PRESETS):
        try:
            restaurant = _create_custom_restaurant()
        except ValueError as e:
            print(f"  Error: {e}")
            return
    else:
        filepath = input("  Enter file path: ").strip()
        try:
            restaurant = parse_restaurant_config(filepath)
        except (FileNotFoundError, ValueError) as e:
            print(f"  Error: {e}")
            return

    try:
        prompt_reservation_settings(restaurant)
        validate_restaurant(restaurant)
    except ValueError as e:
        print(f"  Error: {e}")
        return

    state["restaurant_template"] = restaurant
    state["config_label"] = restaurant.name
    print(f"\n  Loaded: {restaurant.name}")
    print(f"  Operating hours: {_minutes_to_hhmm(restaurant.opening_time)} – "
          f"{_minutes_to_hhmm(restaurant.closing_time)}")
    _print_table_summary(restaurant.tables)
    if restaurant.reservation_enabled:
        print(
            "  Reservations: enabled "
            f"(max reserved tables: {restaurant.max_reserved_tables}, "
            f"hold: {restaurant.reservation_hold_minutes} min)"
        )
    else:
        print("  Reservations: disabled")


def _create_custom_restaurant() -> Restaurant:
    print("\nCreate custom restaurant configuration")
    print("  Enter times as HH:MM or minutes from midnight.")
    print("  Add each table type as 'capacity + number of tables'.")

    name = _prompt_non_empty("  Restaurant name [Custom Restaurant]: ", default="Custom Restaurant")
    opening_time = _prompt_time("  Opening time", default_minutes=DEFAULT_OPENING_TIME)
    closing_time = _prompt_time("  Closing time", default_minutes=DEFAULT_CLOSING_TIME)

    if closing_time <= opening_time:
        raise ValueError("Closing time must be later than opening time.")

    tables: List[Table] = []
    table_id = 1

    while True:
        capacity_raw = input("  Table capacity (press Enter when finished): ").strip()
        if not capacity_raw:
            if tables:
                break
            print("  Add at least one table type first.")
            continue

        try:
            capacity = int(capacity_raw)
        except ValueError:
            print("  Capacity must be a whole number.")
            continue

        if capacity <= 0:
            print("  Capacity must be positive.")
            continue

        count = _prompt_positive_int(f"  Number of {capacity}-seat tables: ")
        for _ in range(count):
            tables.append(Table(table_id=table_id, capacity=capacity))
            table_id += 1

    restaurant = Restaurant(
        name=name,
        opening_time=opening_time,
        closing_time=closing_time,
        tables=tables,
    )
    validate_restaurant(restaurant)
    return restaurant


def _describe_config(path: str) -> str:
    if not os.path.exists(path):
        return "file missing"
    try:
        lines = _non_comment_lines(path)
        table_lines = lines[2:]
        parts = []
        for line in table_lines:
            cap, cnt = line.split()
            parts.append(f"{cnt}x{cap}-seat")
        return ", ".join(parts)
    except Exception:
        return path


def _print_table_summary(tables) -> None:
    from collections import Counter
    counts = Counter(t.capacity for t in tables)
    parts = [f"{cnt} tables ({cap}-seat)" for cap, cnt in sorted(counts.items())]
    print(f"  Tables: {', '.join(parts)}")
    print(f"  Total: {len(tables)} tables, {sum(t.capacity for t in tables)} seats")


def _fit_arrivals_to_restaurant(arrivals, restaurant: Restaurant):
    max_capacity = max(table.capacity for table in restaurant.tables)
    valid_table_ids = {table.table_id for table in restaurant.tables}
    kept = [
        group for group in arrivals
        if (
            restaurant.opening_time <= group.arrival_time <= restaurant.closing_time
            and group.size <= max_capacity
        )
    ]

    removed_before = sum(1 for group in arrivals if group.arrival_time < restaurant.opening_time)
    removed_after = sum(1 for group in arrivals if group.arrival_time > restaurant.closing_time)
    removed_too_large = sum(1 for group in arrivals if group.size > max_capacity)
    adjusted_table_preferences = 0

    for group in kept:
        if group.preferred_table_id is not None and group.preferred_table_id not in valid_table_ids:
            group.preferred_table_id = None
            adjusted_table_preferences += 1
        if (
            group.preferred_table_capacity is not None
            and group.preferred_table_capacity > max_capacity
        ):
            group.preferred_table_capacity = None
            adjusted_table_preferences += 1

    if removed_before or removed_after or removed_too_large or adjusted_table_preferences:
        print(
            "  Adjusted scenario to match restaurant settings "
            f"({_minutes_to_hhmm(restaurant.opening_time)} – "
            f"{_minutes_to_hhmm(restaurant.closing_time)})."
        )
        if removed_before:
            print(f"  Removed {removed_before} groups arriving before opening.")
        if removed_after:
            print(f"  Removed {removed_after} groups arriving after closing.")
        if removed_too_large:
            print(f"  Removed {removed_too_large} groups larger than the biggest table ({max_capacity} seats).")
        if adjusted_table_preferences:
            print(f"  Cleared {adjusted_table_preferences} invalid reservation table preferences.")

    return kept


def _ensure_reservations_in_loaded_scenario(arrivals, restaurant: Restaurant) -> int:
    """
    Backward-compatibility helper:
    Old scenario files may have no reservation columns. If reservation mode is enabled
    and no reservation groups exist, tag a small subset as reservation groups so the
    reservation system can be exercised without regenerating files.
    """
    if not restaurant.reservation_enabled:
        return 0
    if restaurant.max_reserved_tables <= 0:
        return 0
    if any(group.is_reserved for group in arrivals):
        return 0

    candidates = [group for group in arrivals if group.size <= max(table.capacity for table in restaurant.tables)]
    if not candidates:
        return 0

    target = min(len(candidates), max(1, restaurant.max_reserved_tables))
    step = max(1, len(candidates) // target)
    selected = candidates[::step][:target]
    table_capacities = sorted({table.capacity for table in restaurant.tables})

    for group in selected:
        group.is_reserved = True
        group.reservation_time = group.arrival_time
        group.reservation_expiry_time = group.reservation_time + restaurant.reservation_hold_minutes
        suitable = [cap for cap in table_capacities if cap >= group.size]
        group.preferred_table_capacity = suitable[0] if suitable else None

    return len(selected)

def select_strategy(state: dict) -> None:
    print("\nQueue strategies (select one or more, e.g. 1,2):")
    options = [name for name, _, __ in STRATEGY_OPTIONS]
    indices = _choose_from_list(options, "Select strategy/strategies", allow_multiple=True)
    state["strategies"] = [(STRATEGY_OPTIONS[i][0].split("(")[0].strip(),
                            STRATEGY_OPTIONS[i][1],
                            STRATEGY_OPTIONS[i][2]) for i in indices]
    state["strategy_label"] = " + ".join(s[0] for s in state["strategies"])
    print(f"  Selected: {state['strategy_label']}")


def choose_scenario(state: dict) -> None:
    print("\nArrival scenarios:")
    options = [name for name, _ in SCENARIO_PRESETS]
    options.append("Generate new scenario")
    options.append("Load from file path")
    idx = _choose_from_list(options, "Select scenario")[0]

    if idx < len(SCENARIO_PRESETS):
        name, path = SCENARIO_PRESETS[idx]
        filepath = path
        label = name
    elif idx == len(SCENARIO_PRESETS):
        filepath, label = _generate_scenario(state)
        if filepath is None:
            return
    else:
        filepath = input("  Enter file path: ").strip()
        label = os.path.basename(filepath)

    try:
        arrivals = parse_arrivals(filepath)
        if state.get("restaurant_template"):
            arrivals = _fit_arrivals_to_restaurant(arrivals, state["restaurant_template"])
            added_reservations = _ensure_reservations_in_loaded_scenario(arrivals, state["restaurant_template"])
            if added_reservations:
                print(
                    "  Added "
                    f"{added_reservations} reservation groups to this scenario "
                    "for reservation-mode compatibility."
                )
            validate_arrivals(arrivals, state["restaurant_template"])
        state["arrivals"] = arrivals
        state["scenario_label"] = label
        print(f"  Loaded {len(arrivals)} customer groups.")
    except (FileNotFoundError, ValueError) as e:
        print(f"  Error: {e}")


def _generate_scenario(state: dict) -> Tuple[Optional[str], str]:
    from scenarios.generator import generate_arrivals, save_arrivals_to_file, choose_generated_scenario
    if not state.get("restaurant_template"):
        print("  Please load a restaurant configuration first.")
        return None, ""
    try:
        speed, demand = choose_generated_scenario()
        r = state["restaurant_template"]
        table_capacities = [table.capacity for table in r.tables]
        max_table_capacity = max(table.capacity for table in r.tables)
        arrivals = generate_arrivals(
            r.opening_time,
            r.closing_time,
            speed,
            demand,
            max_group_size=max_table_capacity,
            table_capacities=table_capacities,
            reservation_enabled=r.reservation_enabled,
            max_reserved_tables=r.max_reserved_tables,
            reservation_window_minutes=r.reservation_window_minutes,
            reservation_hold_minutes=r.reservation_hold_minutes,
        )
        path = TEMP_SCENARIO_PATH
        save_arrivals_to_file(arrivals, path)
        print(f"  Generated {len(arrivals)} groups. Saved to {path} (overwritten each time).")
        return path, f"Generated ({speed}, {demand})"
    except (ValueError, KeyboardInterrupt) as e:
        print(f"  Error: {e}")
        return None, ""


def run_sim(state: dict) -> None:
    if not state.get("restaurant_template"):
        print("\n  Please load a restaurant configuration first (option 1).")
        return
    if not state.get("arrivals"):
        print("\n  Please choose an arrival scenario first (option 3).")
        return
    if not state.get("strategies"):
        print("\n  Please select a queue strategy first (option 2).")
        return

    print("\nRunning simulation...")
    results: List[Tuple[str, SimulationResult]] = []

    for strategy_name, queue_ranges, use_round_robin in state["strategies"]:
        # Deep copy so each strategy starts with a fresh restaurant + arrivals
        restaurant_copy = copy.deepcopy(state["restaurant_template"])
        arrivals_copy = copy.deepcopy(state["arrivals"])
        result = run_simulation(restaurant_copy, arrivals_copy, queue_ranges,
                                use_round_robin=use_round_robin)
        results.append((strategy_name, result))
        served = len(result.completed_groups)
        avg = sum(g.waiting_time for g in result.completed_groups if g.waiting_time is not None)
        avg_w = round(avg / served, 1) if served else 0
        print(f"  {strategy_name:<30} ... done  "
              f"({result.total_arrived} groups arrived, {avg_w} min avg wait)")

    state["results"] = results
    print("\n  Simulation complete. Select option 5 to view results.")


def view_results(state: dict) -> None:
    if not state.get("results"):
        print("\n  No results yet. Run the simulation first (option 4).")
        return

    results = state["results"]
    scenario = state.get("scenario_label", "")

    if len(results) == 1:
        name, result = results[0]
        print_summary(result, name)
    else:
        compare_strategies(results, scenario_name=scenario)

    print("  View detailed breakdown for one strategy? (y/n): ", end="")
    if input().strip().lower() == "y":
        print("\nChoose strategy:")
        for name, result in results:
            print_summary(result, name)


# ── main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    state: dict = {
        "restaurant_template": None,
        "arrivals": None,
        "strategies": [],
        "results": None,
        "config_label": None,
        "scenario_label": None,
        "strategy_label": None,
    }

    _print_header()

    while True:
        _print_menu(
            loaded_config=state["config_label"],
            loaded_scenario=state["scenario_label"],
            selected_strategies=[s[0] for s in state.get("strategies", [])],
        )
        choice = input("Enter option: ").strip()

        if choice == "1":
            load_config(state)
        elif choice == "2":
            select_strategy(state)
        elif choice == "3":
            choose_scenario(state)
        elif choice == "4":
            run_sim(state)
        elif choice == "5":
            view_results(state)
        elif choice == "6":
            print("\nGoodbye!")
            break
        else:
            print("  Invalid option. Please enter 1–6.")


if __name__ == "__main__":
    main()
