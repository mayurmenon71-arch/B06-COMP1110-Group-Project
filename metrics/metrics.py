"""
Performance metrics and reporting for simulation results.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from simulation.simulation_engine import SimulationResult


def avg_waiting_time(result: SimulationResult) -> float:
    """Average waiting time (minutes) for groups that were seated."""
    times = [g.waiting_time for g in result.completed_groups if g.waiting_time is not None]
    return round(sum(times) / len(times), 1) if times else 0.0


def max_waiting_time(result: SimulationResult) -> int:
    """Maximum waiting time (minutes) among seated groups."""
    times = [g.waiting_time for g in result.completed_groups if g.waiting_time is not None]
    return max(times) if times else 0


def groups_served(result: SimulationResult) -> int:
    """Number of groups that were seated and completed their meal."""
    return len(result.completed_groups)


def groups_left(result: SimulationResult) -> int:
    """Number of groups that left before being seated (dropouts)."""
    return len(result.left_groups)


def table_utilization(result: SimulationResult) -> float:
    """Percentage of time tables were occupied during the simulation."""
    max_possible = result.total_tables * result.total_ticks
    if max_possible == 0:
        return 0.0
    return round((result.occupied_ticks / max_possible) * 100, 1)


def service_level(result: SimulationResult, threshold_minutes: int = 15) -> float:
    """Percentage of seated groups who were seated within threshold_minutes."""
    seated = [g for g in result.completed_groups if g.waiting_time is not None]
    if not seated:
        return 0.0
    within = sum(1 for g in seated if g.waiting_time <= threshold_minutes)
    return round((within / len(seated)) * 100, 1)


def print_summary(result: SimulationResult, strategy_name: str) -> None:
    """Print a single-strategy summary to the terminal."""
    print(f"\n{'='*50}")
    print(f"  Strategy: {strategy_name}")
    print(f"{'='*50}")
    print(f"  Groups arrived:           {result.total_arrived}")
    print(f"  Groups served:            {groups_served(result)}")
    print(f"  Groups left (dropout):    {groups_left(result)}")
    print(f"  Still waiting at close:   {len(result.still_waiting)}")
    print(f"  Avg waiting time:         {avg_waiting_time(result)} min")
    print(f"  Max waiting time:         {max_waiting_time(result)} min")
    print(f"  Max queue length:         {result.max_queue_length}")
    print(f"  Table utilization:        {table_utilization(result)}%")
    print(f"  Service level (<15 min):  {service_level(result)}%")
    print(f"{'='*50}\n")


def compare_strategies(
    results: List[Tuple[str, SimulationResult]],
    scenario_name: str = "",
) -> None:
    """Print a side-by-side comparison table for multiple strategies."""
    if not results:
        print("No results to compare.")
        return

    names = [name for name, _ in results]
    col_w = max(18, max(len(n) for n in names) + 2)
    label_w = 28

    # Header
    header_label = f" Simulation Results"
    if scenario_name:
        header_label += f"  |  {scenario_name}"
    total_w = label_w + (col_w + 3) * len(results)
    print("\n" + "=" * total_w)
    print(header_label)
    print("=" * total_w)

    # Column headers
    row = f"{'Metric':<{label_w}}"
    for name in names:
        row += f"| {name:^{col_w}} "
    print(row)
    print("-" * label_w + ("+" + "-" * (col_w + 2)) * len(results))

    def _row(label: str, values: List[str]) -> str:
        r = f"{label:<{label_w}}"
        for v in values:
            r += f"| {v:^{col_w}} "
        return r

    rows_data = [
        ("Groups arrived",        [str(r.total_arrived) for _, r in results]),
        ("Groups served",         [str(groups_served(r)) for _, r in results]),
        ("Groups left (dropout)", [str(groups_left(r)) for _, r in results]),
        ("Still waiting at close",[str(len(r.still_waiting)) for _, r in results]),
        ("Avg wait time (min)",   [str(avg_waiting_time(r)) for _, r in results]),
        ("Max wait time (min)",   [str(max_waiting_time(r)) for _, r in results]),
        ("Max queue length",      [str(r.max_queue_length) for _, r in results]),
        ("Table utilization",     [f"{table_utilization(r)}%" for _, r in results]),
        ("Service level (<15min)",[f"{service_level(r)}%" for _, r in results]),
    ]

    for label, values in rows_data:
        print(_row(label, values))

    print("=" * total_w + "\n")
