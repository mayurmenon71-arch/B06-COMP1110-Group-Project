# Case Study Results

These results were generated non-interactively by `scripts/run_case_studies.py` using the existing parser, validation, simulation engine, and metric functions. The saved arrival files are deterministic, and the runner uses fixed random seeds for the abandonment model so the tables can be reproduced.

## Validation

- OK: `config/restaurant_small.txt` + `scenarios/case_studies/pair1_low_demand.txt` parsed (8 tables, 61 groups).
- OK: `config/restaurant_small.txt` + `scenarios/case_studies/pair1_high_demand.txt` parsed (8 tables, 160 groups).
- OK: `config/restaurant_medium.txt` + `scenarios/case_studies/pair2_no_reservations.txt` parsed (12 tables, 135 groups).
- OK: `config/restaurant_medium.txt` + `scenarios/case_studies/pair2_with_reservations.txt` parsed (12 tables, 135 groups).
- OK: `config/restaurant_medium.txt` + `scenarios/case_studies/pair3_small_groups.txt` parsed (12 tables, 135 groups).
- OK: `config/restaurant_medium.txt` + `scenarios/case_studies/pair3_large_groups.txt` parsed (12 tables, 135 groups).
- OK: `scenarios/case_studies/pair4_uniform_layout_config.txt` + `scenarios/case_studies/pair4_same_arrivals.txt` parsed (9 tables, 135 groups).
- OK: `scenarios/case_studies/pair4_mixed_layout_config.txt` + `scenarios/case_studies/pair4_same_arrivals.txt` parsed (11 tables, 135 groups).
- OK: `config/restaurant_medium.txt` + `scenarios/case_studies/pair5_fast_service.txt` parsed (12 tables, 135 groups).
- OK: `config/restaurant_medium.txt` + `scenarios/case_studies/pair5_slow_service.txt` parsed (12 tables, 135 groups).
- OK: `config/restaurant_medium.txt` + `scenarios/case_studies/pair6_short_peak.txt` parsed (12 tables, 135 groups).
- OK: `config/restaurant_medium.txt` + `scenarios/case_studies/pair6_long_peak.txt` parsed (12 tables, 135 groups).

## Metric definitions

- `Arrived`: total customer groups entering the scenario.
- `Served`: groups successfully seated and completed service.
- `Left`: groups that abandoned before being served.
- `Abandon %`: `Left / Arrived * 100`.
- `Avg wait`: average waiting time among served groups.
- `Max wait`: longest waiting time among served groups.
- `Max queue`: largest waiting-queue length observed during the run.
- `Util %`: percentage of available table-time ticks during which tables were occupied.
- `Service <=15 %`: percentage of served groups seated within 15 minutes.
- Reservation metrics are shown only when the reservation system is enabled or reservation-tagged groups exist.

## Balanced score method

The weighted trade-off score is a decision-support measure, not an absolute best-strategy proof. Each metric is normalized across the four strategies within the same scenario. Higher normalized scores are better. The weights are: average wait 30%, abandonment rate 25%, service level 20%, table utilization 15%, and groups served 10%. Lower is better for average wait and abandonment; higher is better for service level, utilization, and groups served.

## Strategy selection notes

| Restaurant Priority | Metric to prioritize | How to interpret results |
| --- | --- | --- |
| Reduce waiting | Lowest Avg wait, highest Service <=15% | Choose the strategy that seats groups fastest. |
| Reduce walkouts | Lowest Abandon % | Choose the strategy that prevents long queues and abandonment. |
| Improve capacity use | Highest Util % | Choose the strategy that keeps tables occupied efficiently. |
| Maximize throughput | Highest Served | Choose the strategy serving the most groups. |
| Balanced operation | Weighted score | Use the normalized weighted score as a trade-off, not as a universal recommendation. |

## Pair 1: Demand Level

### Scenario setup

- Factor varied: Customer arrival demand
- Scenario A: Low demand
- Scenario B: High demand
- Files A: `config/restaurant_small.txt` + `scenarios/case_studies/pair1_low_demand.txt`
- Files B: `config/restaurant_small.txt` + `scenarios/case_studies/pair1_high_demand.txt`
- Constants: Small restaurant layout, normal service style, no reservations, same generator seed.
- Purpose: Test how strategies behave under light versus congested demand.

### Metrics table for Scenario A: Low demand

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 61 | 53 | 7 | 11.5 | 1.2 | 15 | 6 | 52.0 | 100.0 |
| Size-Based FCFS | 61 | 54 | 6 | 9.8 | 2.0 | 18 | 5 | 53.0 | 96.3 |
| Fine-Grained FCFS | 61 | 54 | 6 | 9.8 | 3.0 | 62 | 6 | 53.1 | 94.4 |
| Round-Robin FCFS | 61 | 53 | 7 | 11.5 | 3.1 | 38 | 5 | 52.0 | 92.5 |

### Metrics table for Scenario B: High demand

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 160 | 82 | 76 | 47.5 | 10.9 | 54 | 19 | 83.2 | 65.9 |
| Size-Based FCFS | 160 | 85 | 71 | 44.4 | 16.9 | 171 | 18 | 87.2 | 63.5 |
| Fine-Grained FCFS | 160 | 81 | 77 | 48.1 | 12.9 | 149 | 17 | 82.6 | 74.1 |
| Round-Robin FCFS | 160 | 83 | 75 | 46.9 | 10.7 | 106 | 15 | 84.1 | 72.3 |

### Key observations

- Expected: High demand should increase waiting time, abandonment, max queue length, and utilization.
- Actual: averaged across the four strategies, the Scenario B average wait was 12.8 compared with 2.3 in Scenario A, abandonment 46.7% compared with 10.7%, max queue 17.2 compared with 5.5, and utilization 84.3% compared with 52.5%. This matches the expectation.
- When demand rises, tables become occupied more often and groups wait behind more parties. Strategy differences become more visible because capacity is scarce.
- Under low demand, average waiting time and abandonment were low across all strategies, but some strategies still produced occasional long waits. Fine-Grained FCFS had a max wait of 62 minutes and Round-Robin FCFS had a max wait of 38 minutes, while Single Queue FCFS had a max wait of 15 minutes.
- Under high demand, no single strategy dominated all metrics. Size-Based FCFS served the most groups and had the lowest dropout, while Round-Robin FCFS had the lowest average wait.
- Weighted trade-off: Low demand points to Size-Based FCFS (76.1); High demand points to Round-Robin FCFS (64.6). This is a decision-support score, not an absolute best strategy.

### Metric-specific strategy choices

- Low demand:
  - minimize waiting time: Single Queue FCFS (1.2 min)
  - maximize table utilization: Fine-Grained FCFS (top value 53.1%; Size-Based FCFS close)
  - minimize dropout: Size-Based FCFS and Fine-Grained FCFS (tie at 9.8%)
  - maximize groups served: Size-Based FCFS and Fine-Grained FCFS (tie at 54)
  - strongest weighted trade-off: Size-Based FCFS (76.1)

- High demand:
  - minimize waiting time: Round-Robin FCFS (10.7 min)
  - maximize table utilization: Size-Based FCFS (87.2%)
  - minimize dropout: Size-Based FCFS (44.4%)
  - maximize groups served: Size-Based FCFS (85)
  - strongest weighted trade-off: Round-Robin FCFS (64.6)

### Weighted score table for Scenario A: Low demand

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Size-Based FCFS | 76.1 | 57.9 | 100.0 | 50.7 | 90.9 | 100.0 |
| Fine-Grained FCFS | 56.6 | 5.3 | 100.0 | 25.3 | 100.0 | 100.0 |
| Single Queue FCFS | 50.0 | 100.0 | 0.0 | 100.0 | 0.0 | 0.0 |
| Round-Robin FCFS | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

### Weighted score table for Scenario B: High demand

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Round-Robin FCFS | 64.6 | 100.0 | 32.4 | 83.0 | 32.6 | 50.0 |
| Size-Based FCFS | 50.0 | 0.0 | 100.0 | 0.0 | 100.0 | 100.0 |
| Single Queue FCFS | 42.1 | 96.8 | 16.2 | 22.6 | 13.0 | 25.0 |
| Fine-Grained FCFS | 39.4 | 64.5 | 0.0 | 100.0 | 0.0 | 0.0 |

## Pair 2: Reservation Share

### Scenario setup

- Factor varied: Share of reservation-tagged customer groups
- Scenario A: No reservation groups
- Scenario B: With reservation groups
- Files A: `config/restaurant_medium.txt` + `scenarios/case_studies/pair2_no_reservations.txt`
- Files B: `config/restaurant_medium.txt` + `scenarios/case_studies/pair2_with_reservations.txt`
- Constants: Medium restaurant layout, same arrival times, same group sizes, same dining durations, reservation system enabled at 30%.
- Purpose: Test how reservation-aware logic affects service and fairness.

### Metrics table for Scenario A: No reservation groups

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % | Reserved | Res success % | Res timeout % | Res util % | Walk-in abandon % | Reserved abandon % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 100 | 35 | 25.9 | 5.8 | 31 | 17 | 68.8 | 82.0 | 0 | 0.0 | 0.0 | 0.0 | 25.9 | 0.0 |
| Size-Based FCFS | 135 | 102 | 33 | 24.4 | 7.7 | 112 | 18 | 69.4 | 79.4 | 0 | 0.0 | 0.0 | 0.0 | 24.4 | 0.0 |
| Fine-Grained FCFS | 135 | 103 | 32 | 23.7 | 6.0 | 65 | 16 | 71.6 | 87.4 | 0 | 0.0 | 0.0 | 0.0 | 23.7 | 0.0 |
| Round-Robin FCFS | 135 | 97 | 38 | 28.1 | 6.5 | 31 | 17 | 66.8 | 75.3 | 0 | 0.0 | 0.0 | 0.0 | 28.1 | 0.0 |

### Metrics table for Scenario B: With reservation groups

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % | Reserved | Res success % | Res timeout % | Res util % | Walk-in abandon % | Reserved abandon % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 100 | 35 | 25.9 | 6.1 | 42 | 16 | 68.7 | 84.0 | 34 | 88.2 | 23.5 | 73.5 | 30.7 | 11.8 |
| Size-Based FCFS | 135 | 103 | 32 | 23.7 | 8.2 | 68 | 15 | 70.4 | 81.6 | 34 | 82.4 | 23.5 | 70.6 | 25.7 | 17.6 |
| Fine-Grained FCFS | 135 | 98 | 37 | 27.4 | 8.0 | 68 | 17 | 67.8 | 83.7 | 34 | 79.4 | 32.4 | 58.8 | 29.7 | 20.6 |
| Round-Robin FCFS | 135 | 100 | 35 | 25.9 | 6.1 | 38 | 17 | 68.9 | 83.0 | 34 | 85.3 | 29.4 | 67.6 | 29.7 | 14.7 |

### Key observations

- Expected: Adding reservations should improve reserved-customer reliability, but may reduce seating flexibility for walk-ins.
- Actual: the reservation scenario had reservation success between 79.4% and 88.2% depending on strategy. Averaged across the four strategies, average wait changed from 6.5 in Scenario A to 7.1 in Scenario B, so the reservation effect is visible but strategy-dependent.
- Reservation holds can protect capacity for booked groups. This can help reservation success, but it may also make table assignment less flexible for walk-ins.
- In Scenario A, reservation settings were kept enabled for consistency, but the arrival file contains no reservation-tagged groups.
- In Scenario B, reservation-related metrics should be interpreted separately from whole-system metrics. Higher reservation reliability does not automatically mean lower overall waiting time or lower walk-in abandonment.
- Weighted trade-off: No reservation groups points to Fine-Grained FCFS (96.8); With reservation groups points to Single Queue FCFS (69.3). This is a decision-support score, not an absolute best strategy.

### Metric-specific strategy choices

- No reservation groups:
  - minimize waiting time: Single Queue FCFS (5.8 min)
  - maximize table utilization: Fine-Grained FCFS (71.6%)
  - minimize dropout: Fine-Grained FCFS (23.7%)
  - maximize groups served: Fine-Grained FCFS (top value 103; Size-Based FCFS close)
  - strongest weighted trade-off: Fine-Grained FCFS (96.8)

- With reservation groups:
  - minimize waiting time: Single Queue FCFS and Round-Robin FCFS (tie at 6.1 min)
  - maximize table utilization: Size-Based FCFS (70.4%)
  - minimize dropout: Size-Based FCFS (23.7%)
  - maximize groups served: Size-Based FCFS (103)
  - strongest weighted trade-off: Single Queue FCFS (69.3)

### Weighted score table for Scenario A: No reservation groups

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Fine-Grained FCFS | 96.8 | 89.5 | 100.0 | 100.0 | 100.0 | 100.0 |
| Single Queue FCFS | 64.8 | 100.0 | 50.0 | 55.4 | 41.7 | 50.0 |
| Size-Based FCFS | 44.3 | 0.0 | 84.1 | 33.9 | 54.2 | 83.3 |
| Round-Robin FCFS | 18.9 | 63.2 | 0.0 | 0.0 | 0.0 | 0.0 |

### Weighted score table for Scenario B: With reservation groups

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 69.3 | 100.0 | 40.5 | 100.0 | 34.6 | 40.0 |
| Round-Robin FCFS | 62.1 | 100.0 | 40.5 | 58.3 | 42.3 | 40.0 |
| Size-Based FCFS | 50.0 | 0.0 | 100.0 | 0.0 | 100.0 | 100.0 |
| Fine-Grained FCFS | 20.4 | 9.5 | 0.0 | 87.5 | 0.0 | 0.0 |

## Pair 3: Group-Size Distribution

### Scenario setup

- Factor varied: Customer group-size mix
- Scenario A: Small groups
- Scenario B: Large groups
- Files A: `config/restaurant_medium.txt` + `scenarios/case_studies/pair3_small_groups.txt`
- Files B: `config/restaurant_medium.txt` + `scenarios/case_studies/pair3_large_groups.txt`
- Constants: Medium restaurant layout, same arrival times, same dining durations, no reservations.
- Purpose: Test small-party-heavy versus large-party-heavy demand.

### Metrics table for Scenario A: Small groups

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 100 | 35 | 25.9 | 5.6 | 31 | 16 | 69.8 | 85.0 |
| Size-Based FCFS | 135 | 96 | 39 | 28.9 | 4.4 | 36 | 15 | 66.7 | 90.6 |
| Fine-Grained FCFS | 135 | 98 | 37 | 27.4 | 5.5 | 54 | 14 | 69.2 | 85.7 |
| Round-Robin FCFS | 135 | 103 | 32 | 23.7 | 7.3 | 42 | 19 | 72.0 | 81.6 |

### Metrics table for Scenario B: Large groups

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 75 | 60 | 44.4 | 10.0 | 37 | 16 | 52.3 | 68.0 |
| Size-Based FCFS | 135 | 78 | 57 | 42.2 | 13.7 | 129 | 20 | 53.1 | 65.4 |
| Fine-Grained FCFS | 135 | 75 | 60 | 44.4 | 7.8 | 48 | 15 | 51.5 | 78.7 |
| Round-Robin FCFS | 135 | 76 | 59 | 43.7 | 9.2 | 95 | 16 | 52.2 | 69.7 |

### Key observations

- Expected: Large-party-heavy demand should be harder to serve because fewer tables can fit each group.
- Actual: averaged across the four strategies, large-group demand had average wait 10.2 compared with 5.7 for small groups, and abandonment 43.7% compared with 26.5%. This matches the expectation.
- Large groups have fewer suitable tables, so a strict queue can leave available small tables unused while larger parties wait.
- For small groups, Round-Robin FCFS performed best for throughput, dropout, and utilization, while Size-Based FCFS minimized average waiting time. No single strategy clearly dominated this scenario.
- For large groups, fewer tables can fit each party, so the queue strategies face a stronger capacity-matching constraint.
- Weighted trade-off: Small groups points to Single Queue FCFS (54.1); Large groups points to Size-Based FCFS and Fine-Grained FCFS (tie at 50.0). This is a decision-support score, not an absolute best strategy.

### Metric-specific strategy choices

- Small groups:
  - minimize waiting time: Size-Based FCFS (4.4 min)
  - maximize table utilization: Round-Robin FCFS (72.0%)
  - minimize dropout: Round-Robin FCFS (23.7%)
  - maximize groups served: Round-Robin FCFS (103)
  - strongest weighted trade-off: Single Queue FCFS (54.1)

- Large groups:
  - minimize waiting time: Fine-Grained FCFS (7.8 min)
  - maximize table utilization: Size-Based FCFS (53.1%)
  - minimize dropout: Size-Based FCFS (42.2%)
  - maximize groups served: Size-Based FCFS (78)
  - strongest weighted trade-off: Size-Based FCFS and Fine-Grained FCFS (tie at 50.0)

### Weighted score table for Scenario A: Small groups

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 54.1 | 58.6 | 57.7 | 37.8 | 58.5 | 57.1 |
| Size-Based FCFS | 50.0 | 100.0 | 0.0 | 100.0 | 0.0 | 0.0 |
| Round-Robin FCFS | 50.0 | 0.0 | 100.0 | 0.0 | 100.0 | 100.0 |
| Fine-Grained FCFS | 44.9 | 62.1 | 28.8 | 45.6 | 47.2 | 28.6 |

### Weighted score table for Scenario B: Large groups

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Size-Based FCFS | 50.0 | 0.0 | 100.0 | 0.0 | 100.0 | 100.0 |
| Fine-Grained FCFS | 50.0 | 100.0 | 0.0 | 100.0 | 0.0 | 0.0 |
| Round-Robin FCFS | 47.2 | 76.3 | 31.8 | 32.3 | 43.8 | 33.3 |
| Single Queue FCFS | 30.2 | 62.7 | 0.0 | 19.5 | 50.0 | 0.0 |

## Pair 4: Restaurant Layout

### Scenario setup

- Factor varied: Table configuration
- Scenario A: Mostly four-seat layout
- Scenario B: Mixed layout
- Files A: `scenarios/case_studies/pair4_uniform_layout_config.txt` + `scenarios/case_studies/pair4_same_arrivals.txt`
- Files B: `scenarios/case_studies/pair4_mixed_layout_config.txt` + `scenarios/case_studies/pair4_same_arrivals.txt`
- Constants: Same arrival file, same opening hours, same total seats, no reservations.
- Purpose: Test how table mix affects seating efficiency.

### Metrics table for Scenario A: Mostly four-seat layout

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 86 | 49 | 36.3 | 8.2 | 32 | 17 | 79.0 | 74.4 |
| Size-Based FCFS | 135 | 87 | 48 | 35.6 | 10.8 | 135 | 19 | 80.3 | 77.0 |
| Fine-Grained FCFS | 135 | 88 | 47 | 34.8 | 13.8 | 129 | 17 | 82.6 | 76.1 |
| Round-Robin FCFS | 135 | 84 | 51 | 37.8 | 10.1 | 44 | 17 | 77.9 | 64.3 |

### Metrics table for Scenario B: Mixed layout

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 97 | 38 | 28.1 | 7.6 | 47 | 18 | 73.8 | 84.5 |
| Size-Based FCFS | 135 | 92 | 43 | 31.9 | 6.5 | 33 | 17 | 68.4 | 79.3 |
| Fine-Grained FCFS | 135 | 94 | 41 | 30.4 | 7.4 | 66 | 15 | 70.4 | 81.9 |
| Round-Robin FCFS | 135 | 96 | 39 | 28.9 | 7.9 | 34 | 18 | 73.6 | 72.9 |

### Key observations

- Expected: The mixed layout should match varied group sizes more flexibly than the mostly-four-seat layout.
- Actual: averaged across the four strategies, the mixed layout had average wait 7.3 compared with 10.7 for the mostly four-seat layout, and abandonment 29.8% compared with 36.1%. This matches the expectation.
- A mixed layout gives the seating logic more capacity choices, reducing the chance that small groups consume tables needed by larger groups.
- Although total seating capacity was kept constant, the number of tables differed: the mostly-four-seat layout has 9 tables, while the mixed layout has 11 tables. Therefore, this pair tests both table-size mix and the number of seating units, not only capacity distribution.
- The mixed layout performed better on average wait and abandonment, but the best strategy still depends on whether the restaurant prioritizes waiting time, utilization, or throughput.
- Weighted trade-off: Mostly four-seat layout points to Size-Based FCFS (69.6; Fine-Grained FCFS close); Mixed layout points to Single Queue FCFS (76.4). This is a decision-support score, not an absolute best strategy.

### Metric-specific strategy choices

- Mostly four-seat layout:
  - minimize waiting time: Single Queue FCFS (8.2 min)
  - maximize table utilization: Fine-Grained FCFS (82.6%)
  - minimize dropout: Fine-Grained FCFS (34.8%)
  - maximize groups served: Fine-Grained FCFS (top value 88; Size-Based FCFS close)
  - strongest weighted trade-off: Size-Based FCFS (69.6; Fine-Grained FCFS close)

- Mixed layout:
  - minimize waiting time: Size-Based FCFS (6.5 min)
  - maximize table utilization: Single Queue FCFS (top value 73.8%; Round-Robin FCFS close)
  - minimize dropout: Single Queue FCFS (28.1%)
  - maximize groups served: Single Queue FCFS (top value 97; Round-Robin FCFS close)
  - strongest weighted trade-off: Single Queue FCFS (76.4)

### Weighted score table for Scenario A: Mostly four-seat layout

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Size-Based FCFS | 69.6 | 53.6 | 73.3 | 100.0 | 51.1 | 75.0 |
| Fine-Grained FCFS | 68.6 | 0.0 | 100.0 | 92.9 | 100.0 | 100.0 |
| Single Queue FCFS | 66.9 | 100.0 | 50.0 | 79.5 | 23.4 | 50.0 |
| Round-Robin FCFS | 19.8 | 66.1 | 0.0 | 0.0 | 0.0 | 0.0 |

### Weighted score table for Scenario B: Mixed layout

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 76.4 | 21.4 | 100.0 | 100.0 | 100.0 | 100.0 |
| Fine-Grained FCFS | 45.7 | 35.7 | 39.5 | 77.6 | 37.0 | 40.0 |
| Round-Robin FCFS | 42.2 | 0.0 | 78.9 | 0.0 | 96.3 | 80.0 |
| Size-Based FCFS | 41.0 | 100.0 | 0.0 | 55.2 | 0.0 | 0.0 |

## Pair 5: Service Speed

### Scenario setup

- Factor varied: Dining duration / table turnover speed
- Scenario A: Fast service
- Scenario B: Slow service
- Files A: `config/restaurant_medium.txt` + `scenarios/case_studies/pair5_fast_service.txt`
- Files B: `config/restaurant_medium.txt` + `scenarios/case_studies/pair5_slow_service.txt`
- Constants: Medium restaurant layout, same arrival times, same group sizes, no reservations.
- Purpose: Test how table turnover affects queue performance.

### Metrics table for Scenario A: Fast service

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 116 | 19 | 14.1 | 4.0 | 24 | 14 | 51.8 | 92.2 |
| Size-Based FCFS | 135 | 118 | 17 | 12.6 | 3.8 | 56 | 13 | 52.9 | 94.9 |
| Fine-Grained FCFS | 135 | 116 | 19 | 14.1 | 3.7 | 37 | 12 | 53.1 | 92.2 |
| Round-Robin FCFS | 135 | 118 | 17 | 12.6 | 3.6 | 46 | 14 | 53.0 | 94.9 |

### Metrics table for Scenario B: Slow service

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 81 | 52 | 38.5 | 8.6 | 39 | 18 | 82.5 | 76.5 |
| Size-Based FCFS | 135 | 76 | 57 | 42.2 | 9.9 | 53 | 17 | 76.8 | 72.4 |
| Fine-Grained FCFS | 135 | 79 | 54 | 40.0 | 7.0 | 52 | 18 | 82.7 | 84.8 |
| Round-Robin FCFS | 135 | 78 | 53 | 39.3 | 9.5 | 53 | 15 | 83.0 | 74.4 |

### Key observations

- Expected: Slow service should increase waiting time and abandonment because tables turn over less often.
- Actual: averaged across the four strategies, the Scenario B average wait was 8.8 compared with 3.8 in Scenario A, abandonment 40.0% compared with 13.3%, max queue 17.0 compared with 13.2, and utilization 81.2% compared with 52.7%. This matches the expectation.
- Longer dining durations keep tables occupied for more ticks, so queues grow even when the arrival pattern is unchanged.
- Under slow service, Single Queue FCFS performed best for dropout and groups served, while Fine-Grained FCFS performed best for waiting time and service level.
- The slow-service condition raises utilization because tables stay occupied longer, but this is not automatically good: it is paired with higher waiting time and abandonment.
- Weighted trade-off: Fast service points to Round-Robin FCFS (98.8); Slow service points to Fine-Grained FCFS (85.1). This is a decision-support score, not an absolute best strategy.

### Metric-specific strategy choices

- Fast service:
  - minimize waiting time: Round-Robin FCFS (top value 3.6 min; Size-Based FCFS, Fine-Grained FCFS close)
  - maximize table utilization: Fine-Grained FCFS (top value 53.1%; Size-Based FCFS, Round-Robin FCFS close)
  - minimize dropout: Size-Based FCFS and Round-Robin FCFS (tie at 12.6%)
  - maximize groups served: Size-Based FCFS and Round-Robin FCFS (tie at 118)
  - strongest weighted trade-off: Round-Robin FCFS (98.8)

- Slow service:
  - minimize waiting time: Fine-Grained FCFS (7.0 min)
  - maximize table utilization: Round-Robin FCFS (top value 83.0%; Single Queue FCFS, Fine-Grained FCFS close)
  - minimize dropout: Single Queue FCFS (38.5%)
  - maximize groups served: Single Queue FCFS (81)
  - strongest weighted trade-off: Fine-Grained FCFS (85.1)

### Weighted score table for Scenario A: Fast service

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Round-Robin FCFS | 98.8 | 100.0 | 100.0 | 100.0 | 92.3 | 100.0 |
| Size-Based FCFS | 82.7 | 50.0 | 100.0 | 100.0 | 84.6 | 100.0 |
| Fine-Grained FCFS | 37.5 | 75.0 | 0.0 | 0.0 | 100.0 | 0.0 |
| Single Queue FCFS | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

### Weighted score table for Scenario B: Slow service

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Fine-Grained FCFS | 85.1 | 100.0 | 59.5 | 100.0 | 95.2 | 60.0 |
| Single Queue FCFS | 68.9 | 44.8 | 100.0 | 33.1 | 91.9 | 100.0 |
| Round-Robin FCFS | 46.0 | 13.8 | 78.4 | 16.1 | 100.0 | 40.0 |
| Size-Based FCFS | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Pair 6: Peak Duration

### Scenario setup

- Factor varied: Demand concentration over time
- Scenario A: Short peak
- Scenario B: Long peak
- Files A: `config/restaurant_medium.txt` + `scenarios/case_studies/pair6_short_peak.txt`
- Files B: `config/restaurant_medium.txt` + `scenarios/case_studies/pair6_long_peak.txt`
- Constants: Medium restaurant layout, same groups, same group sizes, same durations, no reservations.
- Purpose: Test short bursts versus sustained demand.

### Metrics table for Scenario A: Short peak

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 62 | 73 | 54.1 | 17.1 | 61 | 19 | 43.6 | 38.7 |
| Size-Based FCFS | 135 | 65 | 70 | 51.9 | 18.5 | 98 | 21 | 45.5 | 41.5 |
| Fine-Grained FCFS | 135 | 61 | 74 | 54.8 | 18.2 | 102 | 18 | 43.7 | 55.7 |
| Round-Robin FCFS | 135 | 61 | 73 | 54.1 | 18.5 | 105 | 20 | 42.6 | 39.3 |

### Metrics table for Scenario B: Long peak

| Strategy | Arrived | Served | Left | Abandon % | Avg wait | Max wait | Max queue | Util % | Service <=15 % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single Queue FCFS | 135 | 106 | 29 | 21.5 | 8.0 | 22 | 6 | 73.0 | 84.9 |
| Size-Based FCFS | 135 | 106 | 28 | 20.7 | 7.1 | 64 | 7 | 72.0 | 86.8 |
| Fine-Grained FCFS | 135 | 107 | 27 | 20.0 | 7.3 | 106 | 7 | 74.2 | 88.8 |
| Round-Robin FCFS | 135 | 107 | 28 | 20.7 | 7.4 | 37 | 6 | 74.0 | 88.8 |

### Key observations

- Expected: A short peak should create larger queue spikes, while a longer peak should spread pressure over time.
- Actual: averaged across the four strategies, the long peak had average wait 7.4 compared with 18.1 for the short peak, abandonment 20.7% compared with 53.7%, and max queue 6.5 compared with 19.5. This matches the expectation.
- Concentrating arrivals into short windows can exceed available seating capacity temporarily, while spreading the same groups gives tables more time to turn over.
- The total number of groups is the same, but the short peak compresses arrivals into a smaller time window, creating stronger temporary congestion.
- The long peak performs better because the same demand is spread over more time, giving tables more opportunities to turn over before the queue becomes too large.
- Weighted trade-off: Short peak points to Size-Based FCFS (53.3); Long peak points to Fine-Grained FCFS (93.3). This is a decision-support score, not an absolute best strategy.

### Metric-specific strategy choices

- Short peak:
  - minimize waiting time: Single Queue FCFS (17.1 min)
  - maximize table utilization: Size-Based FCFS (45.5%)
  - minimize dropout: Size-Based FCFS (51.9%)
  - maximize groups served: Size-Based FCFS (65)
  - strongest weighted trade-off: Size-Based FCFS (53.3)

- Long peak:
  - minimize waiting time: Size-Based FCFS (7.1 min)
  - maximize table utilization: Fine-Grained FCFS (top value 74.2%; Round-Robin FCFS close)
  - minimize dropout: Fine-Grained FCFS (20.0%)
  - maximize groups served: Fine-Grained FCFS and Round-Robin FCFS (tie at 107)
  - strongest weighted trade-off: Fine-Grained FCFS (93.3)

### Weighted score table for Scenario A: Short peak

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Size-Based FCFS | 53.3 | 0.0 | 100.0 | 16.5 | 100.0 | 100.0 |
| Single Queue FCFS | 43.7 | 100.0 | 24.1 | 0.0 | 34.5 | 25.0 |
| Fine-Grained FCFS | 32.1 | 21.4 | 0.0 | 100.0 | 37.9 | 0.0 |
| Round-Robin FCFS | 6.7 | 0.0 | 24.1 | 3.5 | 0.0 | 0.0 |

### Weighted score table for Scenario B: Long peak

| Strategy | Weighted score | Avg wait score | Abandon score | Service score | Util score | Served score |
| --- | --- | --- | --- | --- | --- | --- |
| Fine-Grained FCFS | 93.3 | 77.8 | 100.0 | 100.0 | 100.0 | 100.0 |
| Round-Robin FCFS | 77.0 | 66.7 | 53.3 | 100.0 | 90.9 | 100.0 |
| Size-Based FCFS | 53.1 | 100.0 | 53.3 | 48.7 | 0.0 | 0.0 |
| Single Queue FCFS | 6.8 | 0.0 | 0.0 | 0.0 | 45.5 | 0.0 |

## Interpretation limitations

- Results depend on the generated scenario files and selected random seeds.
- Abandonment includes probabilistic behavior, so fixed seeds are used for reproducibility.
- Some pairs isolate one factor better than others. Pair 4 keeps total seating capacity constant, but it also changes the number of tables.
- The weighted trade-off score depends on the chosen metric weights. A restaurant with different priorities may choose a different strategy.
- The simulator provides decision support rather than a universal best strategy.

## Report-ready summary

We used paired scenarios to evaluate seating strategies in a controlled way. Each pair changes one main factor while keeping the other conditions as constant as possible, such as restaurant layout, arrival pattern, service speed, reservation settings, or group-size distribution. This makes the comparison more meaningful because differences in waiting time, abandonment, utilization, and throughput can be linked to a specific scenario change.

Across the case studies, no single strategy dominated every metric. Under low demand, several strategies performed similarly on average wait and abandonment, although occasional long waits still appeared. Under high demand, slow service, large-group-heavy demand, or short peak bursts, strategy choice mattered more because tables became scarce and abandonment increased. The results support data-driven decision-making: the suitable strategy depends on whether the restaurant prioritizes faster seating, fewer walkouts, higher table utilization, or higher throughput.
