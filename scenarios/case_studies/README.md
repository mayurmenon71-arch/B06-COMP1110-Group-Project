# Case Study Scenario Package

This folder provides a reproducible set of paired Topic C case-study inputs. Each pair varies one factor while keeping the other settings as constant as possible under the current program design.

## Scenario Pair Summary

| Pair | Factor Varied | File A | File B | Constants | Purpose | Expected Effect |
|---|---|---|---|---|---|---|
| 1 | Demand level | `pair1_low_demand.txt` | `pair1_high_demand.txt` | `config/restaurant_small.txt`, normal service style, no reservations, same generator seed | Compare light vs congested demand | Higher demand should increase wait, abandonment, queue length, and utilization |
| 2 | Reservation customer share | `pair2_no_reservations.txt` | `pair2_with_reservations.txt` | `config/restaurant_medium.txt`, same arrival times/sizes/durations, same restaurant reservation settings | Compare all-walk-in demand vs mixed walk-in/reserved demand | Reserved reliability should improve, walk-in wait may increase |
| 3 | Group-size mix | `pair3_small_groups.txt` | `pair3_large_groups.txt` | `config/restaurant_medium.txt`, same arrival times and dining durations, no reservations | Compare small-party-heavy vs large-party-heavy demand | Layout-fit, utilization, and wait patterns should shift |
| 4 | Restaurant layout | `pair4_uniform_layout_config.txt` + `pair4_same_arrivals.txt` | `pair4_mixed_layout_config.txt` + `pair4_same_arrivals.txt` | Same arrivals file, same opening hours, same total seats (40) | Compare a mostly 4-seat layout vs a mixed 2/4/6-seat layout | The mixed layout should fit varied party sizes more flexibly |
| 5 | Service speed / dining duration | `pair5_fast_service.txt` | `pair5_slow_service.txt` | `config/restaurant_medium.txt`, same arrival times/sizes, no reservations | Compare fast turnover vs slow turnover | Slow service should increase waits, queueing, and abandonment |
| 6 | Peak duration / congestion shape | `pair6_short_peak.txt` | `pair6_long_peak.txt` | `config/restaurant_medium.txt`, same groups/sizes/durations, no reservations | Compare short bursts vs sustained pressure | Short peaks may create higher queue spikes; long peaks may create longer sustained waits |

## How to Reproduce in the Current Menu Program

Use the normal interactive menu with all four strategies selected (`1,2,3,4`) unless you only want a single-strategy smoke test.

General menu flow:
1. Run `python main.py`
2. Choose `1. Load restaurant configuration`
3. Load the config file shown below
4. Enter the reservation settings listed below
5. Choose `2. Select queue strategy` and enter `1,2,3,4`
6. Choose `3. Choose arrival scenario`
7. Select `Load from file path`
8. Enter the scenario file path shown below
9. Choose `4. Run simulation`
10. Choose `5. View results`

### Pair 1
- Config: `config/restaurant_small.txt`
- Reservation setting: disabled
- Arrival files:
  - `scenarios/case_studies/pair1_low_demand.txt`
  - `scenarios/case_studies/pair1_high_demand.txt`

### Pair 2
- Config: `config/restaurant_medium.txt`
- Reservation setting: enabled, proportion `30`, hold duration `10`
- Arrival files:
  - `scenarios/case_studies/pair2_no_reservations.txt`
  - `scenarios/case_studies/pair2_with_reservations.txt`

### Pair 3
- Config: `config/restaurant_medium.txt`
- Reservation setting: disabled
- Arrival files:
  - `scenarios/case_studies/pair3_small_groups.txt`
  - `scenarios/case_studies/pair3_large_groups.txt`

### Pair 4
- Config files:
  - `scenarios/case_studies/pair4_uniform_layout_config.txt`
  - `scenarios/case_studies/pair4_mixed_layout_config.txt`
- Reservation setting: disabled
- Shared arrivals: `scenarios/case_studies/pair4_same_arrivals.txt`

### Pair 5
- Config: `config/restaurant_medium.txt`
- Reservation setting: disabled
- Arrival files:
  - `scenarios/case_studies/pair5_fast_service.txt`
  - `scenarios/case_studies/pair5_slow_service.txt`

### Pair 6
- Config: `config/restaurant_medium.txt`
- Reservation setting: disabled
- Arrival files:
  - `scenarios/case_studies/pair6_short_peak.txt`
  - `scenarios/case_studies/pair6_long_peak.txt`

## Notes and Assumptions

- The arrival files use the parser-supported reservation-aware format written by `save_arrivals_to_file`, so every file can be loaded by the current `parse_arrivals()` function.
- Pair 2 varies the share of reservation-tagged groups in the arrival file while keeping the restaurant reservation settings fixed. This is the cleanest file-based approximation of a reservation-ratio experiment supported by the current program.
- The current restaurant config parser does not store reservation settings in config files, so reservation enable/disable and reservation table proportion must still be entered interactively.
- `temp_scenario.txt` is not used so these files remain stable for report reproduction.

## Summary
To evaluate seating strategies systematically, we created paired scenario sets where each pair varies only one factor while keeping other settings constant. The varied factors include demand level, reservation customer share, group-size distribution, restaurant layout, service speed, and peak duration. This controlled design allows fair comparison of strategy performance across different restaurant settings.
