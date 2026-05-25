"""
FM-2 Graph Homomorphism — Structure Preservation Checker.

A mapping f: CDR_events → FHIR_events is structure-preserving (a homomorphism)
if and only if:

    1. Type preservation:    f(e).type is subtype of e.type
    2. Temporal preservation: allen_relation(f(e).temporal, e.temporal)
                              is in ACCEPTABLE_RELATIONS
    3. Surjectivity:          every FHIR event has a CDR preimage
                              (no FHIR events appear from nowhere)
    4. Value-space:           value_space(f(e)) ⊆ value_space(e)

Violations of these properties constitute detected information loss.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from cairn.core.allen import AllenRelation, allen_relation
from cairn.core.event import EventCollection, FMEvent
from cairn.core.type_dag import TypeDAG


class HomomorphismViolation(Enum):
    TYPE_NOT_PRESERVED         = auto()
    TEMPORAL_NOT_PRESERVED     = auto()
    VALUE_SPACE_NOT_CONTAINED  = auto()
    SURJECTIVITY_VIOLATED      = auto()
    CARDINALITY_COLLAPSED      = auto()
    NEGATION_DROPPED           = auto()


@dataclass
class HomomorphismResult:
    """Result of a structure-preservation check between two event collections."""

    is_homomorphism: bool
    violations: list[HomomorphismViolation] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    cdr_count: int = 0
    fhir_count: int = 0

    def add_violation(self, v: HomomorphismViolation, detail: str) -> None:
        self.violations.append(v)
        self.details.append(detail)
        self.is_homomorphism = False

    def summary(self) -> str:
        if self.is_homomorphism:
            return f"✓ Structure preserved ({self.cdr_count} CDR → {self.fhir_count} FHIR events)"
        lines = [f"✗ Structure NOT preserved ({self.cdr_count} CDR → {self.fhir_count} FHIR events)"]
        for v, d in zip(self.violations, self.details):
            lines.append(f"  [{v.name}] {d}")
        return "\n".join(lines)


# Allen relations considered acceptable for temporal preservation
ACCEPTABLE_TEMPORAL_RELATIONS: set[AllenRelation] = {
    AllenRelation.EQUALS,       # Perfect temporal preservation
    AllenRelation.STARTED_BY,   # Same start, FHIR longer — acceptable
    AllenRelation.FINISHES,     # Same end, FHIR longer — marginal
}

# Relations that indicate temporal precision loss (CDR more precise than FHIR)
TEMPORAL_LOSS_RELATIONS: set[AllenRelation] = {
    AllenRelation.DURING,        # CDR strictly inside FHIR window
    AllenRelation.CONTAINS,      # CDR contains FHIR — unusual, suspect
    AllenRelation.OVERLAPS,
    AllenRelation.OVERLAPPED_BY,
}


class HomomorphismChecker:
    """
    Checks whether a CDR→FHIR mapping preserves FM-2 structure.

    Matches events by primary clinical code and checks each
    of the four homomorphism properties.
    """

    def __init__(self, type_dag: Optional[TypeDAG] = None) -> None:
        self._dag = type_dag

    def check(
        self,
        cdr: EventCollection,
        fhir: EventCollection,
    ) -> HomomorphismResult:
        result = HomomorphismResult(
            is_homomorphism=True,
            cdr_count=len(cdr),
            fhir_count=len(fhir),
        )

        # Build lookup: code → list of FHIR events (preserve duplicates)
        fhir_by_code: dict[str, list[FMEvent]] = {}
        for e in fhir:
            code = e.get_code()
            if code:
                fhir_by_code.setdefault(code, []).append(e)

        fhir_codes_matched: set[str] = set()

        for cdr_event in cdr:
            code = cdr_event.get_code()
            # Pop the first available FHIR event for this code to avoid double-matching
            fhir_event: Optional[FMEvent] = None
            if code and fhir_by_code.get(code):
                fhir_event = fhir_by_code[code].pop(0)
                if not fhir_by_code[code]:
                    del fhir_by_code[code]

            # ── Negation dropped ──────────────────────────────────────────────
            if cdr_event.get_negation() and fhir_event is None:
                result.add_violation(
                    HomomorphismViolation.NEGATION_DROPPED,
                    f"Negated event {cdr_event} has no FHIR counterpart — "
                    f"'not stated' silently becomes 'not recorded'",
                )
                continue

            # ── Cardinality collapsed ─────────────────────────────────────────
            if fhir_event is None:
                result.add_violation(
                    HomomorphismViolation.CARDINALITY_COLLAPSED,
                    f"CDR event {cdr_event} has no FHIR counterpart",
                )
                continue

            fhir_codes_matched.add(code)  # type: ignore[arg-type]

            # ── Type preservation ─────────────────────────────────────────────
            if self._dag is not None:
                if not self._dag.is_subtype(fhir_event.event_type, cdr_event.event_type):
                    result.add_violation(
                        HomomorphismViolation.TYPE_NOT_PRESERVED,
                        f"Type not preserved: {cdr_event.event_type} → {fhir_event.event_type}",
                    )

            # ── Temporal preservation ─────────────────────────────────────────
            if cdr_event.has_temporal() and fhir_event.has_temporal():
                rel = allen_relation(cdr_event.temporal, fhir_event.temporal)  # type: ignore
                if rel in TEMPORAL_LOSS_RELATIONS:
                    result.add_violation(
                        HomomorphismViolation.TEMPORAL_NOT_PRESERVED,
                        f"Temporal precision lost for {code}: "
                        f"CDR={cdr_event.temporal} FHIR={fhir_event.temporal} "
                        f"relation={rel.name}",
                    )
            elif cdr_event.has_temporal() and not fhir_event.has_temporal():
                result.add_violation(
                    HomomorphismViolation.TEMPORAL_NOT_PRESERVED,
                    f"Temporal information completely absent in FHIR event for {code}",
                )

            # ── Value-space containment ───────────────────────────────────────
            cdr_keys = set(cdr_event.value_set.keys())
            fhir_keys = set(fhir_event.value_set.keys())
            missing_keys = cdr_keys - fhir_keys
            if missing_keys:
                result.add_violation(
                    HomomorphismViolation.VALUE_SPACE_NOT_CONTAINED,
                    f"Value-space not preserved for {code}: "
                    f"missing fields {missing_keys}",
                )

        # ── Surjectivity: unmapped FHIR events ───────────────────────────────
        all_fhir_codes = {e.get_code() for e in fhir if e.get_code()}
        unmapped = all_fhir_codes - fhir_codes_matched
        if unmapped:
            result.add_violation(
                HomomorphismViolation.SURJECTIVITY_VIOLATED,
                f"FHIR events with no CDR origin (surjectivity violated): {unmapped}",
            )

        return result
