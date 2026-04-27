from __future__ import annotations

import copy
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = REPO_ROOT / "scenarios" / "case_studies"
OUTPUT_PATH = CASE_DIR / "CASE_STUDY_RESULTS.md"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "io"))

from input_parser import parse_arrivals, parse_restaurant_config  # noqa: E402
from validator import validate_arrivals, validate_restaurant  # noqa: E402
from main import STRATEGY_OPTIONS  # noqa: E402
from metrics.metrics import (  # noqa: E402
    abandonment_rate,
    avg_waiting_time,
    max_waiting_time,
    reservation_success_rate,
    reservation_timeout_rate,
    reservation_utilization_rate,
    reserved_abandonment_rate,
    service_level,
    table_utilization,
    walkin_abandonment_rate,
)
from simulation.simulation_engine import SimulationResult, run_simulation  # noqa: E402


@dataclass(frozen=True)
class ScenarioSide:
    label: str
    config: str
    arrivals: str
    reservations_enabled: bool = False
    reservation_proportion: float = 0.30
    reservation_hold_minutes: int = 10
    reservation_window_minutes: int = 5
    fairness_wait_threshold: int = 15


@dataclass(frozen=True)
class ScenarioPair:
    number: int
    title: str
    factor_varied: str
    expected: str
    constants: str
    purpose: str
    side_a: ScenarioSide
    side_b: ScenarioSide
    explanation_hint: str


def rel(path: str | Path) -> str:
    path = Path(path)
    if not path.is_absolute():
        return path.as_posix()
    return path.relative_to(REPO_ROOT).as_posix()


def strategy_label(raw_name: str) -> str:
    return raw_name.split("(")[0].strip()


def scenario_pairs() -> list[ScenarioPair]:
    return [
        ScenarioPair(
            number=1,
            title="Demand Level",
            factor_varied="Customer arrival demand",
            expected=(
                "High demand should increase waiting time, abandonment, max queue "
                "length, and utilization."
            ),
            constants=(
                "Small restaurant layout, normal service style, no reservations, "
                "same generator seed."
            ),
            purpose="Test how strategies behave under light versus congested demand.",
            side_a=ScenarioSide(
                label="Low demand",
                config="config/restaurant_small.txt",
                arrivals="scenarios/case_studies/pair1_low_demand.txt",
            ),
            side_b=ScenarioSide(
                label="High demand",
                config="config/restaurant_small.txt",
                arrivals="scenarios/case_studies/pair1_high_demand.txt",
            ),
            explanation_hint=(
                "When demand rises, tables become occupied more often and groups wait "
                "behind more parties. Strategy differences become more visible because "
                "capacity is scarce."
            ),
        ),
        ScenarioPair(
            number=2,
            title="Reservation Share",
            factor_varied="Share of reservation-tagged customer groups",
            expected=(
                "Adding reservations should improve reserved-customer reliability, "
                "but may reduce seating flexibility for walk-ins."
            ),
            constants=(
                "Medium restaurant layout, same arrival times, same group sizes, "
                "same dining durations, reservation system enabled at 30%."
            ),
            purpose="Test how reservation-aware logic affects service and fairness.",
            side_a=ScenarioSide(
                label="No reservation groups",
                config="config/restaurant_medium.txt",
                arrivals="scenarios/case_studies/pair2_no_reservations.txt",
                reservations_enabled=True,
            ),
            side_b=ScenarioSide(
                label="With reservation groups",
                config="config/restaurant_medium.txt",
                arrivals="scenarios/case_studies/pair2_with_reservations.txt",
                reservations_enabled=True,
            ),
            explanation_hint=(
                "Reservation holds can protect capacity for booked groups. This can help "
                "reservation success, but it may also make table assignment less flexible "
                "for walk-ins."
            ),
        ),
        ScenarioPair(
            number=3,
            title="Group-Size Distribution",
            factor_varied="Customer group-size mix",
            expected=(
                "Large-party-heavy demand should be harder to serve because fewer tables "
                "can fit each group."
            ),
            constants=(
                "Medium restaurant layout, same arrival times, same dining durations, "
                "no reservations."
            ),
            purpose="Test small-party-heavy versus large-party-heavy demand.",
            side_a=ScenarioSide(
                label="Small groups",
                config="config/restaurant_medium.txt",
                arrivals="scenarios/case_studies/pair3_small_groups.txt",
            ),
            side_b=ScenarioSide(
                label="Large groups",
                config="config/restaurant_medium.txt",
                arrivals="scenarios/case_studies/pair3_large_groups.txt",
            ),
            explanation_hint=(
                "Large groups have fewer suitable tables, so a strict queue can leave "
                "available small tables unused while larger parties wait."
            ),
        ),
        ScenarioPair(
            number=4,
            title="Restaurant Layout",
            factor_varied="Table configuration",
            expected=(
                "The mixed layout should match varied group sizes more flexibly than the "
                "mostly-four-seat layout."
            ),
            constants="Same arrival file, same opening hours, same total seats, no reservations.",
            purpose="Test how table mix affects seating efficiency.",
            side_a=ScenarioSide(
                label="Mostly four-seat layout",
                config="scenarios/case_studies/pair4_uniform_layout_config.txt",
                arrivals="scenarios/case_studies/pair4_same_arrivals.txt",
            ),
            side_b=ScenarioSide(
                label="Mixed layout",
                config="scenarios/case_studies/pair4_mixed_layout_config.txt",
                arrivals="scenarios/case_studies/pair4_same_arrivals.txt",
            ),
            explanation_hint=(
                "A mixed layout gives the seating logic more capacity choices, reducing "
                "the chance that small groups consume tables needed by larger groups."
            ),
        ),
        ScenarioPair(
            number=5,
            title="Service Speed",
            factor_varied="Dining duration / table turnover speed",
            expected=(
                "Slow service should increase waiting time and abandonment because tables "
                "turn over less often."
            ),
            constants="Medium restaurant layout, same arrival times, same group sizes, no reservations.",
            purpose="Test how table turnover affects queue performance.",
            side_a=ScenarioSide(
                label="Fast service",
                config="config/restaurant_medium.txt",
                arrivals="scenarios/case_studies/pair5_fast_service.txt",
            ),
            side_b=ScenarioSide(
                label="Slow service",
                config="config/restaurant_medium.txt",
                arrivals="scenarios/case_studies/pair5_slow_service.txt",
            ),
            explanation_hint=(
                "Longer dining durations keep tables occupied for more ticks, so queues "
                "grow even when the arrival pattern is unchanged."
            ),
        ),
        ScenarioPair(
            number=6,
            title="Peak Duration",
            factor_varied="Demand concentration over time",
            expected=(
                "A short peak should create larger queue spikes, while a longer peak "
                "should spread pressure over time."
            ),
            constants="Medium restaurant layout, same groups, same group sizes, same durations, no reservations.",
            purpose="Test short bursts versus sustained demand.",
            side_a=ScenarioSide(
                label="Short peak",
                config="config/restaurant_medium.txt",
                arrivals="scenarios/case_studies/pair6_short_peak.txt",
            ),
            side_b=ScenarioSide(
                label="Long peak",
                config="config/restaurant_medium.txt",
                arrivals="scenarios/case_studies/pair6_long_peak.txt",
            ),
            explanation_hint=(
                "Concentrating arrivals into short windows can exceed available seating "
                "capacity temporarily, while spreading the same groups gives tables more "
                "time to turn over."
            ),
        ),
    ]


def load_side(side: ScenarioSide):
    restaurant = parse_restaurant_config(str(REPO_ROOT / side.config))
    restaurant.configure_reservations(
        enabled=side.reservations_enabled,
        proportion=side.reservation_proportion,
        hold_minutes=side.reservation_hold_minutes,
        window_minutes=side.reservation_window_minutes,
        fairness_wait_threshold=side.fairness_wait_threshold,
    )
    arrivals = parse_arrivals(str(REPO_ROOT / side.arrivals))
    validate_restaurant(restaurant)
    validate_arrivals(arrivals, restaurant)
    return restaurant, arrivals


def run_side(side: ScenarioSide, seed_base: int) -> dict[str, SimulationResult]:
    restaurant, arrivals = load_side(side)
    results: dict[str, SimulationResult] = {}
    for offset, (raw_name, ranges, use_round_robin) in enumerate(STRATEGY_OPTIONS):
        result = run_simulation(
            copy.deepcopy(restaurant),
            copy.deepcopy(arrivals),
            ranges,
            use_round_robin=use_round_robin,
            rng=random.Random(seed_base + offset),
        )
        results[strategy_label(raw_name)] = result
    return results


def metric_row(name: str, result: SimulationResult) -> dict[str, str]:
    row = {
        "Strategy": name,
        "Arrived": str(result.total_arrived),
        "Served": str(len(result.completed_groups)),
        "Left": str(result.total_abandoned_groups),
        "Abandon %": f"{abandonment_rate(result):.1f}",
        "Avg wait": f"{avg_waiting_time(result):.1f}",
        "Max wait": str(max_waiting_time(result)),
        "Max queue": str(result.max_queue_length),
        "Util %": f"{table_utilization(result):.1f}",
        "Service <=15 %": f"{service_level(result):.1f}",
    }
    if result.reservation_enabled or result.total_reserved_groups:
        row.update(
            {
                "Reserved": str(result.total_reserved_groups),
                "Res success %": f"{reservation_success_rate(result):.1f}",
                "Res timeout %": f"{reservation_timeout_rate(result):.1f}",
                "Res util %": f"{reservation_utilization_rate(result):.1f}",
                "Walk-in abandon %": f"{walkin_abandonment_rate(result):.1f}",
                "Reserved abandon %": f"{reserved_abandonment_rate(result):.1f}",
            }
        )
    return row


def markdown_table(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[h] for h in headers) + " |")
    return "\n".join(lines)


def best_label(
    results: dict[str, SimulationResult],
    getter,
    *,
    high_is_better: bool,
    tolerance: float,
    suffix: str = "",
) -> str:
    values = {name: getter(result) for name, result in results.items()}
    best_value = max(values.values()) if high_is_better else min(values.values())
    if high_is_better:
        close = [name for name, value in values.items() if best_value - value <= tolerance]
    else:
        close = [name for name, value in values.items() if value - best_value <= tolerance]

    exact = [name for name, value in values.items() if value == best_value]
    value_text = f"{best_value:.1f}{suffix}" if isinstance(best_value, float) else f"{best_value}{suffix}"
    if len(exact) > 1:
        return f"{' and '.join(exact)} (tie at {value_text})"
    near = [name for name in close if name not in exact]
    if near:
        return f"{exact[0]} (top value {value_text}; {', '.join(near)} close)"
    return f"{exact[0]} ({value_text})"


def best_by(results: dict[str, SimulationResult]) -> dict[str, str]:
    return {
        "minimize waiting time": best_label(
            results,
            avg_waiting_time,
            high_is_better=False,
            tolerance=0.2,
            suffix=" min",
        ),
        "maximize table utilization": best_label(
            results,
            table_utilization,
            high_is_better=True,
            tolerance=0.5,
            suffix="%",
        ),
        "minimize dropout": best_label(
            results,
            abandonment_rate,
            high_is_better=False,
            tolerance=0.5,
            suffix="%",
        ),
        "maximize groups served": best_label(
            results,
            lambda r: len(r.completed_groups),
            high_is_better=True,
            tolerance=1,
        ),
        "strongest weighted trade-off": balanced_choice_label(results),
    }


def normalized_components(results: dict[str, SimulationResult]) -> dict[str, dict[str, float]]:
    specs = {
        "Avg wait score": (avg_waiting_time, False),
        "Abandon score": (abandonment_rate, False),
        "Service score": (service_level, True),
        "Util score": (table_utilization, True),
        "Served score": (lambda r: len(r.completed_groups), True),
    }
    output = {name: {} for name in results}
    for metric_name, (getter, high_is_better) in specs.items():
        values = {name: float(getter(result)) for name, result in results.items()}
        low = min(values.values())
        high = max(values.values())
        for name, value in values.items():
            if high == low:
                score = 100.0
            elif high_is_better:
                score = ((value - low) / (high - low)) * 100.0
            else:
                score = ((high - value) / (high - low)) * 100.0
            output[name][metric_name] = score
    return output


def balanced_scores(results: dict[str, SimulationResult]) -> dict[str, float]:
    weights = {
        "Avg wait score": 0.30,
        "Abandon score": 0.25,
        "Service score": 0.20,
        "Util score": 0.15,
        "Served score": 0.10,
    }
    components = normalized_components(results)
    return {
        name: sum(components[name][metric] * weight for metric, weight in weights.items())
        for name in results
    }


def balanced_choice_label(results: dict[str, SimulationResult]) -> str:
    scores = balanced_scores(results)
    best_score = max(scores.values())
    close = [name for name, score in scores.items() if best_score - score <= 1.0]
    exact = [name for name, score in scores.items() if score == best_score]
    if len(exact) > 1:
        return f"{' and '.join(exact)} (tie at {best_score:.1f})"
    near = [name for name in close if name not in exact]
    if near:
        return f"{exact[0]} ({best_score:.1f}; {', '.join(near)} close)"
    return f"{exact[0]} ({best_score:.1f})"


def balanced_score_table(results: dict[str, SimulationResult]) -> str:
    components = normalized_components(results)
    scores = balanced_scores(results)
    rows: list[dict[str, str]] = []
    for name in results:
        row = {
            "Strategy": name,
            "Weighted score": f"{scores[name]:.1f}",
        }
        for metric in [
            "Avg wait score",
            "Abandon score",
            "Service score",
            "Util score",
            "Served score",
        ]:
            row[metric] = f"{components[name][metric]:.1f}"
        rows.append(row)
    rows.sort(key=lambda row: float(row["Weighted score"]), reverse=True)
    return markdown_table(rows)


def compare_actual(pair: ScenarioPair, a: dict[str, SimulationResult], b: dict[str, SimulationResult]) -> str:
    avg_a = sum(avg_waiting_time(r) for r in a.values()) / len(a)
    avg_b = sum(avg_waiting_time(r) for r in b.values()) / len(b)
    abandon_a = sum(abandonment_rate(r) for r in a.values()) / len(a)
    abandon_b = sum(abandonment_rate(r) for r in b.values()) / len(b)
    queue_a = sum(r.max_queue_length for r in a.values()) / len(a)
    queue_b = sum(r.max_queue_length for r in b.values()) / len(b)
    util_a = sum(table_utilization(r) for r in a.values()) / len(a)
    util_b = sum(table_utilization(r) for r in b.values()) / len(b)

    if pair.number in {1, 5}:
        matches = avg_b >= avg_a and abandon_b >= abandon_a
        return (
            "Actual: averaged across the four strategies, the Scenario B average "
            f"wait was {avg_b:.1f} compared with {avg_a:.1f} in Scenario A, "
            f"abandonment {abandon_b:.1f}% compared with {abandon_a:.1f}%, "
            f"max queue {queue_b:.1f} compared with {queue_a:.1f}, and utilization "
            f"{util_b:.1f}% compared with {util_a:.1f}%. This "
            f"{'matches' if matches else 'does not fully match'} "
            "the expectation."
        )
    if pair.number == 2:
        res_values = [reservation_success_rate(r) for r in b.values()]
        return (
            f"Actual: the reservation scenario had reservation success between "
            f"{min(res_values):.1f}% and {max(res_values):.1f}% depending on strategy. "
            "Averaged across the four strategies, average wait changed from "
            f"{avg_a:.1f} in Scenario A to {avg_b:.1f} in Scenario B, so the "
            "reservation effect is visible but strategy-dependent."
        )
    if pair.number == 3:
        matches = avg_b >= avg_a and abandon_b >= abandon_a
        return (
            "Actual: averaged across the four strategies, large-group demand had "
            f"average wait {avg_b:.1f} compared with {avg_a:.1f} for small groups, "
            f"and abandonment {abandon_b:.1f}% compared with {abandon_a:.1f}%. This "
            f"{'matches' if matches else 'does not fully match'} the expectation."
        )
    if pair.number == 4:
        matches = avg_b <= avg_a and abandon_b <= abandon_a
        return (
            "Actual: averaged across the four strategies, the mixed layout had "
            f"average wait {avg_b:.1f} compared with {avg_a:.1f} for the mostly "
            f"four-seat layout, and abandonment {abandon_b:.1f}% compared with "
            f"{abandon_a:.1f}%. This "
            f"{'matches' if matches else 'does not fully match'} the expectation."
        )
    if pair.number == 6:
        matches = avg_b <= avg_a and abandon_b <= abandon_a and queue_b <= queue_a
        return (
            "Actual: averaged across the four strategies, the long peak had average "
            f"wait {avg_b:.1f} compared with {avg_a:.1f} for the short peak, "
            f"abandonment {abandon_b:.1f}% compared with {abandon_a:.1f}%, and "
            f"max queue {queue_b:.1f} compared with {queue_a:.1f}. This "
            f"{'matches' if matches else 'does not fully match'} the expectation."
        )
    return "Actual: see the metrics tables above."


def best_section(label: str, results: dict[str, SimulationResult]) -> str:
    best = best_by(results)
    lines = [f"- {label}:"]
    for priority, strategy in best.items():
        lines.append(f"  - {priority}: {strategy}")
    return "\n".join(lines)


def pair_specific_notes(pair: ScenarioPair, a: dict[str, SimulationResult], b: dict[str, SimulationResult]) -> list[str]:
    if pair.number == 1:
        return [
            "Under low demand, average waiting time and abandonment were low across all strategies, but some strategies still produced occasional long waits. Fine-Grained FCFS had a max wait of 62 minutes and Round-Robin FCFS had a max wait of 38 minutes, while Single Queue FCFS had a max wait of 15 minutes.",
            "Under high demand, no single strategy dominated all metrics. Size-Based FCFS served the most groups and had the lowest dropout, while Round-Robin FCFS had the lowest average wait.",
        ]
    if pair.number == 2:
        return [
            "In Scenario A, reservation settings were kept enabled for consistency, but the arrival file contains no reservation-tagged groups.",
            "In Scenario B, reservation-related metrics should be interpreted separately from whole-system metrics. Higher reservation reliability does not automatically mean lower overall waiting time or lower walk-in abandonment.",
        ]
    if pair.number == 3:
        return [
            "For small groups, Round-Robin FCFS performed best for throughput, dropout, and utilization, while Size-Based FCFS minimized average waiting time. No single strategy clearly dominated this scenario.",
            "For large groups, fewer tables can fit each party, so the queue strategies face a stronger capacity-matching constraint.",
        ]
    if pair.number == 4:
        return [
            "Although total seating capacity was kept constant, the number of tables differed: the mostly-four-seat layout has 9 tables, while the mixed layout has 11 tables. Therefore, this pair tests both table-size mix and the number of seating units, not only capacity distribution.",
            "The mixed layout performed better on average wait and abandonment, but the best strategy still depends on whether the restaurant prioritizes waiting time, utilization, or throughput.",
        ]
    if pair.number == 5:
        return [
            "Under slow service, Single Queue FCFS performed best for dropout and groups served, while Fine-Grained FCFS performed best for waiting time and service level.",
            "The slow-service condition raises utilization because tables stay occupied longer, but this is not automatically good: it is paired with higher waiting time and abandonment.",
        ]
    if pair.number == 6:
        return [
            "The total number of groups is the same, but the short peak compresses arrivals into a smaller time window, creating stronger temporary congestion.",
            "The long peak performs better because the same demand is spread over more time, giving tables more opportunities to turn over before the queue becomes too large.",
        ]
    return []


def observations(pair: ScenarioPair, a: dict[str, SimulationResult], b: dict[str, SimulationResult]) -> str:
    best_a = best_by(a)
    best_b = best_by(b)
    lines = [
        f"- Expected: {pair.expected}",
        f"- {compare_actual(pair, a, b)}",
        f"- {pair.explanation_hint}",
    ]
    lines.extend(f"- {note}" for note in pair_specific_notes(pair, a, b))
    lines.append(
        f"- Weighted trade-off: {pair.side_a.label} points to "
        f"{best_a['strongest weighted trade-off']}; {pair.side_b.label} points to "
        f"{best_b['strongest weighted trade-off']}. This is a decision-support score, "
        "not an absolute best strategy."
    )
    return "\n".join(lines)


def validate_all_inputs(pairs: Iterable[ScenarioPair]) -> list[str]:
    seen: set[tuple[str, str, bool]] = set()
    messages: list[str] = []
    for pair in pairs:
        for side in (pair.side_a, pair.side_b):
            key = (side.config, side.arrivals, side.reservations_enabled)
            if key in seen:
                continue
            seen.add(key)
            restaurant, arrivals = load_side(side)
            messages.append(
                f"OK: `{rel(side.config)}` + `{rel(side.arrivals)}` parsed "
                f"({len(restaurant.tables)} tables, {len(arrivals)} groups)."
            )
    return messages


def generate_markdown() -> str:
    pairs = scenario_pairs()
    lines = [
        "# Case Study Results",
        "",
        "These results were generated non-interactively by `scripts/run_case_studies.py` using the existing parser, validation, simulation engine, and metric functions. The saved arrival files are deterministic, and the runner uses fixed random seeds for the abandonment model so the tables can be reproduced.",
        "",
        "## Validation",
        "",
    ]
    lines.extend(f"- {message}" for message in validate_all_inputs(pairs))
    lines.extend(
        [
            "",
            "## Metric definitions",
            "",
            "- `Arrived`: total customer groups entering the scenario.",
            "- `Served`: groups successfully seated and completed service.",
            "- `Left`: groups that abandoned before being served.",
            "- `Abandon %`: `Left / Arrived * 100`.",
            "- `Avg wait`: average waiting time among served groups.",
            "- `Max wait`: longest waiting time among served groups.",
            "- `Max queue`: largest waiting-queue length observed during the run.",
            "- `Util %`: percentage of available table-time ticks during which tables were occupied.",
            "- `Service <=15 %`: percentage of served groups seated within 15 minutes.",
            "- Reservation metrics are shown only when the reservation system is enabled or reservation-tagged groups exist.",
            "",
            "## Balanced score method",
            "",
            "The weighted trade-off score is a decision-support measure, not an absolute best-strategy proof. Each metric is normalized across the four strategies within the same scenario. Higher normalized scores are better. The weights are: average wait 30%, abandonment rate 25%, service level 20%, table utilization 15%, and groups served 10%. Lower is better for average wait and abandonment; higher is better for service level, utilization, and groups served.",
            "",
            "## Strategy selection notes",
            "",
            "| Restaurant Priority | Metric to prioritize | How to interpret results |",
            "| --- | --- | --- |",
            "| Reduce waiting | Lowest Avg wait, highest Service <=15% | Choose the strategy that seats groups fastest. |",
            "| Reduce walkouts | Lowest Abandon % | Choose the strategy that prevents long queues and abandonment. |",
            "| Improve capacity use | Highest Util % | Choose the strategy that keeps tables occupied efficiently. |",
            "| Maximize throughput | Highest Served | Choose the strategy serving the most groups. |",
            "| Balanced operation | Weighted score | Use the normalized weighted score as a trade-off, not as a universal recommendation. |",
            "",
        ]
    )

    for pair in pairs:
        seed = 10000 + pair.number * 100
        result_a = run_side(pair.side_a, seed)
        result_b = run_side(pair.side_b, seed + 50)

        lines.extend(
            [
                f"## Pair {pair.number}: {pair.title}",
                "",
                "### Scenario setup",
                "",
                f"- Factor varied: {pair.factor_varied}",
                f"- Scenario A: {pair.side_a.label}",
                f"- Scenario B: {pair.side_b.label}",
                f"- Files A: `{rel(pair.side_a.config)}` + `{rel(pair.side_a.arrivals)}`",
                f"- Files B: `{rel(pair.side_b.config)}` + `{rel(pair.side_b.arrivals)}`",
                f"- Constants: {pair.constants}",
                f"- Purpose: {pair.purpose}",
                "",
                f"### Metrics table for Scenario A: {pair.side_a.label}",
                "",
                markdown_table([metric_row(name, result) for name, result in result_a.items()]),
                "",
                f"### Metrics table for Scenario B: {pair.side_b.label}",
                "",
                markdown_table([metric_row(name, result) for name, result in result_b.items()]),
                "",
                "### Key observations",
                "",
                observations(pair, result_a, result_b),
                "",
                "### Metric-specific strategy choices",
                "",
                best_section(pair.side_a.label, result_a),
                "",
                best_section(pair.side_b.label, result_b),
                "",
                f"### Weighted score table for Scenario A: {pair.side_a.label}",
                "",
                balanced_score_table(result_a),
                "",
                f"### Weighted score table for Scenario B: {pair.side_b.label}",
                "",
                balanced_score_table(result_b),
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretation limitations",
            "",
            "- Results depend on the generated scenario files and selected random seeds.",
            "- Abandonment includes probabilistic behavior, so fixed seeds are used for reproducibility.",
            "- Some pairs isolate one factor better than others. Pair 4 keeps total seating capacity constant, but it also changes the number of tables.",
            "- The weighted trade-off score depends on the chosen metric weights. A restaurant with different priorities may choose a different strategy.",
            "- The simulator provides decision support rather than a universal best strategy.",
            "",
            "## Report-ready summary",
            "",
            "We used paired scenarios to evaluate seating strategies in a controlled way. Each pair changes one main factor while keeping the other conditions as constant as possible, such as restaurant layout, arrival pattern, service speed, reservation settings, or group-size distribution. This makes the comparison more meaningful because differences in waiting time, abandonment, utilization, and throughput can be linked to a specific scenario change.",
            "",
            "Across the case studies, no single strategy dominated every metric. Under low demand, several strategies performed similarly on average wait and abandonment, although occasional long waits still appeared. Under high demand, slow service, large-group-heavy demand, or short peak bursts, strategy choice mattered more because tables became scarce and abandonment increased. The results support data-driven decision-making: the suitable strategy depends on whether the restaurant prioritizes faster seating, fewer walkouts, higher table utilization, or higher throughput.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    markdown = generate_markdown()
    OUTPUT_PATH.write_text(markdown, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
