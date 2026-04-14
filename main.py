"""
Restaurant Queue Simulation — main entry point.
Run with: python main.py
"""
from __future__ import annotations

import copy
import os
import sys
from typing import List, Optional, Tuple

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
from input_parser import parse_restaurant_config, parse_arrivals, _non_comment_lines
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

STRATEGY_OPTIONS: List[Tuple[str, tuple]] = [
    ("Single Queue FCFS  (all groups, one queue)",       default_single_queue_range()),
    ("Size-Based FCFS    (1-2 / 3-4 / 5+ queues)",      default_multi_queue_ranges()),
    ("Fine-Grained FCFS  (1 / 2 / 3-4 / 5+ queues)",   parse_queue_ranges([(1,1),(2,2),(3,4),(5,None)])),
]


# ── helpers ───────────────────────────────────────────────────────────────────

def _divider(char: str = "─", width: int = 50) -> None:
    print(char * width)


def _minutes_to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


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
    options.append("Load from file path")
    idx = _choose_from_list(options, "Select configuration")[0]

    if idx < len(CONFIG_PRESETS):
        name, path = CONFIG_PRESETS[idx]
        filepath = path
    else:
        filepath = input("  Enter file path: ").strip()

    try:
        restaurant = parse_restaurant_config(filepath)
        validate_restaurant(restaurant)
        state["restaurant_template"] = restaurant
        state["config_label"] = restaurant.name
        print(f"\n  Loaded: {restaurant.name}")
        print(f"  Operating hours: {_minutes_to_hhmm(restaurant.opening_time)} – "
              f"{_minutes_to_hhmm(restaurant.closing_time)}")
        _print_table_summary(restaurant.tables)
    except (FileNotFoundError, ValueError) as e:
        print(f"  Error: {e}")


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


def select_strategy(state: dict) -> None:
    print("\nQueue strategies (select one or more, e.g. 1,2):")
    options = [name for name, _ in STRATEGY_OPTIONS]
    indices = _choose_from_list(options, "Select strategy/strategies", allow_multiple=True)
    state["strategies"] = [(STRATEGY_OPTIONS[i][0].split("(")[0].strip(),
                            STRATEGY_OPTIONS[i][1]) for i in indices]
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
        arrivals = generate_arrivals(r.opening_time, r.closing_time, speed, demand)
        path = f"scenarios/arrivals_generated_{speed}_{demand}.txt"
        save_arrivals_to_file(arrivals, path)
        print(f"  Generated {len(arrivals)} groups. Saved to {path}")
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

    for strategy_name, queue_ranges in state["strategies"]:
        # Deep copy so each strategy starts with a fresh restaurant + arrivals
        restaurant_copy = copy.deepcopy(state["restaurant_template"])
        arrivals_copy = copy.deepcopy(state["arrivals"])
        result = run_simulation(restaurant_copy, arrivals_copy, queue_ranges)
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
