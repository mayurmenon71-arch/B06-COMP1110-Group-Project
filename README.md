# Restaurant Queue Simulation — Group B06

COMP1110: Computing and Data Science in Everyday Life
The University of Hong Kong, Semester 2, 2025–2026

**Topic C: Restaurant Queue Simulation**

---

## Overview

This project simulates how a restaurant manages queues and seats customer groups under different queue strategies. It compares strategies such as a single queue versus size-based queues, and measures performance using metrics like average waiting time and table utilization.

---

## How to Run

**Requirements:** Python 3.10 or above. No external libraries required.

```
python main.py
```

Run from the project root directory.

---

## Program Menu

```
1. Load restaurant configuration   — choose a preset, create one interactively, or load from file
2. Select queue strategy           — single queue, size-based, or fine-grained
3. Choose arrival scenario         — preset scenario or generate/load your own
4. Run simulation                  — runs all selected strategies
5. View results                    — side-by-side comparison table
6. Exit
```

You can select multiple strategies at step 2 (e.g. enter `1,2`) to compare them side by side.

---

## Input File Formats

### Restaurant Configuration (`config/*.txt`)

```
# comments are ignored
Small Cafe
660 1320
2 6
4 2
```

- Line 1: restaurant name
- Line 2: `opening_time closing_time` in minutes from midnight (e.g. `660` = 11:00, `1320` = 22:00)
- Remaining lines: `capacity count` — one line per table type

You can also choose `Create custom configuration` in the program menu and enter:
- restaurant name
- opening time
- closing time
- table capacity and number of tables for each table type
- reservation settings (enable/disable, reservation table proportion, hold duration)

### Customer Arrivals (`scenarios/*.txt`)

```
# group_id size arrival_time dining_duration
1 3 12:05 45
2 1 12:07 30
```

Optional reservation-aware format:

```
# group_id size arrival_time dining_duration is_reserved reservation_time reservation_expiry_time preferred_table_id preferred_table_capacity
10 4 18:02 60 1 18:00 18:10 - 4
11 2 18:05 45 0 - - - -
```

- `group_id`: unique integer
- `size`: number of people in the group
- `arrival_time`: HH:MM format
- `dining_duration`: how long the group dines, in minutes

---

## Preset Files

### Restaurant Configurations (`config/`)

| File | Description |
|------|-------------|
| `restaurant_small.txt` | Small cafe: 6x2-seat, 2x4-seat |
| `restaurant_medium.txt` | Medium restaurant: 4x2-seat, 6x4-seat, 2x6-seat |
| `restaurant_large.txt` | Large dim sum hall: 4x2-seat, 4x4-seat, 4x6-seat, 2x8-seat |

### Arrival Scenarios (`scenarios/`)

| File | Description |
|------|-------------|
| `arrivals_small_low.txt` | Fast service, low demand (~180 groups) |
| `arrivals_medium_normal.txt` | Normal service, average demand (~155 groups) |
| `arrivals_peak_high.txt` | Normal service, high demand (~236 groups) |

---

## Generating New Scenarios

Select option 3 then "Generate new scenario" from the arrival menu. You will be asked to choose:
- **Service speed**: fast / normal / slow (affects dining duration)
- **Demand level**: low / average / high (affects number of arrivals)

Generated arrivals use the currently loaded restaurant's opening and closing times, including any custom times entered interactively.
The generator also adapts to the loaded restaurant layout:
- larger restaurants generate more traffic than smaller ones
- the table-size mix influences the generated group-size mix
- generated group sizes are capped to the restaurant's largest table, so impossible-to-seat groups are not created
- if reservations are enabled, generated scenarios include reservation groups and reservation metadata

The generated file is saved as `scenarios/temp_scenario.txt` and overwritten each time you generate a new scenario.

---

## Queue Strategies

| Strategy | Description |
|----------|-------------|
| Single Queue FCFS | All groups share one queue. When a table frees, the earliest-arriving group that fits is seated. |
| Size-Based FCFS | Groups are split into three queues: 1-2, 3-4, and 5+ people. FCFS within each. |
| Fine-Grained FCFS | Four queues: 1, 2, 3-4, and 5+. More precise size matching. |

---

## Performance Metrics

| Metric | Description |
|--------|-------------|
| Groups arrived | Total customer groups that showed up |
| Groups served | Groups successfully seated and finished dining |
| Groups left (dropout) | Groups that left after waiting more than 30 minutes |
| Avg / Max waiting time | Time from arrival to being seated |
| Max queue length | Peak number of groups waiting simultaneously |
| Table utilization | % of time tables were occupied during operating hours |
| Service level | % of served groups seated within 15 minutes |
| Reservation utilization | % of reservation groups seated with reservation priority |
| Reservation success rate | % of reservation groups eventually served |
| Reservation timeout rate | % of reservation groups that lost reservation priority by timeout |

---

## Project Structure

```
├── main.py                    Entry point — text-based menu
├── models/
│   ├── customer_group.py      CustomerGroup dataclass
│   ├── table.py               Table dataclass
│   ├── restaurant.py          Restaurant dataclass
│   ├── queue_stratgies.py     Queue range definitions and FCFS selection logic
│   └── table_assignment.py    Seating algorithm (best-fit + cross-queue FCFS)
├── simulation/
│   └── simulation_engine.py   Minute-by-minute simulation loop
├── metrics/
│   └── metrics.py             Performance metrics and comparison table output
├── io/
│   ├── input_parser.py        Parses restaurant config and arrival files
│   └── validator.py           Input validation
├── scenarios/
│   ├── generator.py           Generates realistic arrival data (Poisson model)
│   └── arrivals_*.txt         Pre-generated scenario files
├── config/
│   └── restaurant_*.txt       Restaurant layout configuration files
└── README.md
```

---

## Team

Group B06 — HKU COMP1110 Semester 2, 2025-2026

| Name | Student ID | Role |
|------|-----------|------|
| Bae Junyoung | 3035716464 | Research & System Design Lead, GitHub, README |
| Kalpally Pulapra Mayur Menon | 3036609187 | Core Simulation Lead, Queue Strategies |
| Pham Khanh Huyen | 3036517384 | Data Model & File I/O Lead |
| Gu Eric Yimiao | 3036588307 | Metrics & Testing Lead |
