"""
Queue strategy helpers: queue definitions, routing by group size, and FCFS / priority
selection of the next group when a table becomes free.

The simulation engine should:
- On arrival: append each group to the queue returned by ``assign_queue_index`` (single
  logical queue or one of several lists).
- On table free: use ``find_fcfs_group_for_table`` (one list) or
  ``find_fcfs_group_from_queues`` (several lists) to pick the next group to seat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

from .customer_group import CustomerGroup


@dataclass(frozen=True)
class QueueRange:
    """
    Inclusive size range for one logical queue.

    ``max_size`` ``None`` means no upper bound (e.g. "5+").
    """

    min_size: int
    max_size: Optional[int]

    def __post_init__(self) -> None:
        if self.min_size <= 0:
            raise ValueError("min_size must be positive.")
        if self.max_size is not None:
            if self.max_size < self.min_size:
                raise ValueError("max_size cannot be less than min_size.")


def group_matches_range(size: int, qr: QueueRange) -> bool:
    """Return True if ``size`` falls in ``qr`` (inclusive bounds)."""
    if size < qr.min_size:
        return False
    if qr.max_size is None:
        return True
    return size <= qr.max_size


def assign_queue_index(group_size: int, ranges: Sequence[QueueRange]) -> int:
    """
    Return the index of the queue that serves ``group_size``.

    Raises:
        ValueError: If no range matches or more than one range matches (invalid config).
    """
    matches = [i for i, r in enumerate(ranges) if group_matches_range(group_size, r)]
    if not matches:
        raise ValueError(f"No queue range matches group size {group_size}.")
    if len(matches) > 1:
        raise ValueError(
            f"Group size {group_size} matches multiple queue ranges at indices {matches}."
        )
    return matches[0]


def _ranges_overlap(a: QueueRange, b: QueueRange) -> bool:
    """True if some group size could match both ranges."""
    lo = max(a.min_size, b.min_size)
    a_hi = a.max_size if a.max_size is not None else float("inf")
    b_hi = b.max_size if b.max_size is not None else float("inf")
    hi = min(a_hi, b_hi)
    return lo <= hi


def validate_queue_ranges(ranges: Sequence[QueueRange]) -> None:
    """Raise if any two ranges overlap (same size could be routed to two queues)."""
    for i, a in enumerate(ranges):
        for b in ranges[i + 1 :]:
            if _ranges_overlap(a, b):
                raise ValueError(f"Overlapping queue ranges: {a!r} and {b!r}.")


def default_single_queue_range() -> Tuple[QueueRange, ...]:
    """One queue that accepts any group size (use a large upper bound or unbounded)."""
    return (QueueRange(1, None),)


def default_multi_queue_ranges() -> Tuple[QueueRange, ...]:
    """Example: 1–2, 3–4, 5+ (adjust in file/config for case studies)."""
    return (
        QueueRange(1, 2),
        QueueRange(3, 4),
        QueueRange(5, None),
    )


def parse_queue_ranges(specs: Iterable[Tuple[int, Optional[int]]]) -> Tuple[QueueRange, ...]:
    """
    Build ``QueueRange`` tuples from simple (min, max) pairs; ``max`` None means unbounded.
    """
    return tuple(QueueRange(mn, mx) for mn, mx in specs)


def eligible_groups_for_table(
    waiting_queue: Sequence[CustomerGroup],
    table_capacity: int,
) -> List[CustomerGroup]:
    """All waiting groups that can sit at a table of ``table_capacity`` (order preserved)."""
    return [g for g in waiting_queue if g.can_fit(table_capacity)]


def find_fcfs_group_for_table(
    waiting_queue: Sequence[CustomerGroup],
    table_capacity: int,
) -> Optional[CustomerGroup]:
    """
    First-come-first-served within one queue: earliest *in queue order* group that fits.

    This matches iterating ``waiting_queue`` front-to-back and taking the first that fits.
    """
    for group in waiting_queue:
        if group.can_fit(table_capacity):
            return group
    return None


def find_fcfs_group_from_queues(
    queues: Sequence[Sequence[CustomerGroup]],
    table_capacity: int,
) -> Optional[CustomerGroup]:
    """
    FCFS across several queues: among all waiting groups that fit the table, choose the
    one with the smallest ``arrival_time`` (ties broken by ``group_id``).

    This is the usual rule when multiple size-based queues feed one pool of tables:
    global order by arrival, not per-queue order in isolation at seating time.
    """
    return find_group_for_table_with_key(
        queues,
        table_capacity,
        sort_key=lambda g: (g.arrival_time, g.group_id),
    )


def find_group_for_table_with_key(
    queues: Sequence[Sequence[CustomerGroup]],
    table_capacity: int,
    *,
    sort_key: Callable[[CustomerGroup], Tuple],
) -> Optional[CustomerGroup]:
    """
    Pick one eligible group using a total ordering ``sort_key`` (smaller = earlier service).

    Examples:

    - Same as multi-queue FCFS::

        sort_key=lambda g: (g.arrival_time, g.group_id)

    - VIP first (higher ``vip_rank`` served first), then FCFS::

        sort_key=lambda g: (-vip_rank[g.group_id], g.arrival_time, g.group_id)
    """
    candidates: List[CustomerGroup] = []
    for queue in queues:
        for group in queue:
            if group.can_fit(table_capacity):
                candidates.append(group)
    if not candidates:
        return None
    return min(candidates, key=sort_key)


def vip_then_fcfs_key(
    vip_rank: Callable[[CustomerGroup], int],
) -> Callable[[CustomerGroup], Tuple]:
    """
    Build a ``sort_key`` for ``find_group_for_table_with_key``: higher rank leaves first
    (more important), then earlier arrival, then lower ``group_id``.
    """
    return lambda g: (-vip_rank(g), g.arrival_time, g.group_id)

