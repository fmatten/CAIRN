"""
FM-2 Allen Temporal Algebra — 13 interval relations.

Reference: Allen, J.F. (1983). Maintaining knowledge about temporal intervals.
Communications of the ACM, 26(11), 832–843.

CRITICAL INVARIANT: All intervals must be strictly positive.
    interval.start < interval.end  (strictly less than, NOT equal)

Point intervals (start == end) cause mutual exclusivity violations
between MEETS, MET_BY, and EQUALS relations. Enforced via Z3 in
cairn.verification.z3_proofs and validated here at construction time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class AllenRelation(Enum):
    """The 13 Allen interval relations."""

    PRECEDES      = auto()   # a < b        (a ends before b starts)
    MET_BY        = auto()   # a m- b       (a end == b start, non-overlapping)
    OVERLAPPED_BY = auto()   # a oi b
    FINISHED_BY   = auto()   # a fi b       (same end, a longer)
    CONTAINS      = auto()   # a di b       (b strictly inside a)
    STARTS_WITH   = auto()   # a si b       (same start, a longer)
    EQUALS        = auto()   # a = b        (identical interval)
    STARTED_BY    = auto()   # a s b        (same start, b longer)  [inverse si]
    DURING        = auto()   # a d b        (a strictly inside b)   [inverse di]
    FINISHES      = auto()   # a f b        (same end, b longer)    [inverse fi]
    OVERLAPS      = auto()   # a o b
    MEETS         = auto()   # a m b        (a end == b start)
    PRECEDED_BY   = auto()   # a > b        (b ends before a starts)


@dataclass
class TimeInterval:
    """
    A closed temporal interval [start, end].

    Invariant: start < end  (strictly positive duration).
    Point intervals (start == end) are not permitted in FM-2
    as they violate mutual exclusivity of Allen relations.
    """

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError(
                f"FM-2 invariant violated: interval must be strictly positive. "
                f"Got start={self.start!r}, end={self.end!r}. "
                f"Use start < end (point intervals are not permitted)."
            )

    @property
    def duration_seconds(self) -> float:
        return (self.end - self.start).total_seconds()

    def __str__(self) -> str:
        fmt = "%Y-%m-%d %H:%M:%S"
        return f"[{self.start.strftime(fmt)} → {self.end.strftime(fmt)}]"


def allen_relation(a: TimeInterval, b: TimeInterval) -> AllenRelation:
    """
    Compute the Allen relation between intervals a and b.

    Returns the unique relation r such that a r b.

    All 13 relations are mutually exclusive and exhaustive
    for strictly positive intervals.
    """
    a_s, a_e = a.start, a.end
    b_s, b_e = b.start, b.end

    if a_e < b_s:
        return AllenRelation.PRECEDES
    if a_s > b_e:
        return AllenRelation.PRECEDED_BY
    if a_e == b_s:
        return AllenRelation.MEETS
    if a_s == b_e:
        return AllenRelation.MET_BY
    if a_s < b_s and a_e < b_e and a_e > b_s:
        return AllenRelation.OVERLAPS
    if a_s > b_s and a_e > b_e and a_s < b_e:
        return AllenRelation.OVERLAPPED_BY
    if a_s == b_s and a_e < b_e:
        return AllenRelation.STARTED_BY
    if a_s == b_s and a_e > b_e:
        return AllenRelation.STARTS_WITH
    if a_e == b_e and a_s > b_s:
        return AllenRelation.FINISHES
    if a_e == b_e and a_s < b_s:
        return AllenRelation.FINISHED_BY
    if a_s > b_s and a_e < b_e:
        return AllenRelation.DURING
    if a_s < b_s and a_e > b_e:
        return AllenRelation.CONTAINS
    # a_s == b_s and a_e == b_e
    return AllenRelation.EQUALS


def inverse_relation(r: AllenRelation) -> AllenRelation:
    """Return the inverse (converse) of an Allen relation."""
    inverses = {
        AllenRelation.PRECEDES:      AllenRelation.PRECEDED_BY,
        AllenRelation.PRECEDED_BY:   AllenRelation.PRECEDES,
        AllenRelation.MEETS:         AllenRelation.MET_BY,
        AllenRelation.MET_BY:        AllenRelation.MEETS,
        AllenRelation.OVERLAPS:      AllenRelation.OVERLAPPED_BY,
        AllenRelation.OVERLAPPED_BY: AllenRelation.OVERLAPS,
        AllenRelation.STARTS_WITH:   AllenRelation.STARTED_BY,
        AllenRelation.STARTED_BY:    AllenRelation.STARTS_WITH,
        AllenRelation.DURING:        AllenRelation.CONTAINS,
        AllenRelation.CONTAINS:      AllenRelation.DURING,
        AllenRelation.FINISHES:      AllenRelation.FINISHED_BY,
        AllenRelation.FINISHED_BY:   AllenRelation.FINISHES,
        AllenRelation.EQUALS:        AllenRelation.EQUALS,
    }
    return inverses[r]


def temporal_containment(a: TimeInterval, b: TimeInterval) -> bool:
    """
    Return True if interval a is temporally contained within b.
    (a DURING b, or a EQUALS b, or a STARTED_BY b, or a FINISHES b)
    """
    r = allen_relation(a, b)
    return r in {
        AllenRelation.DURING,
        AllenRelation.EQUALS,
        AllenRelation.STARTED_BY,
        AllenRelation.FINISHES,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Allen relation composition table (partial — key pairs for SILD analysis)
# Full table: 13×13 = 169 entries, here the most clinically relevant subset
# ──────────────────────────────────────────────────────────────────────────────

PRECISION_LOSS_RELATIONS: set[AllenRelation] = {
    AllenRelation.CONTAINS,      # CDR interval strictly inside FHIR interval
    AllenRelation.OVERLAPS,      # Partial overlap — boundary information lost
    AllenRelation.OVERLAPPED_BY, # Partial overlap — boundary information lost
    AllenRelation.DURING,        # FHIR interval inside CDR — unusual, noteworthy
}
"""
Allen relations indicating temporal precision loss when mapping CDR→FHIR.

If allen_relation(cdr_event, fhir_event) is in this set, temporal information
was lost during the mapping (the FHIR representation is less precise).
"""
