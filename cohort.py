"""
CAIRN Analysis — FM-2 Cohort Queries (φA–φD).

φA: Event selection by type and code
φB: Comorbidity / co-occurrence detection
φC: Site-specific (laterality-aware) queries
φD: Temporal sequence queries (Allen-based)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cairn.core.allen import AllenRelation, allen_relation
from cairn.core.event import EventCollection, FMEvent
from cairn.core.type_dag import TypeDAG, TypeNode


@dataclass
class CohortResult:
    query_name: str
    events: list[FMEvent] = field(default_factory=list)
    count: int = 0

    def __post_init__(self) -> None:
        self.count = len(self.events)


class CohortAnalyzer:
    """FM-2 Cohort Queries φA–φD."""

    def __init__(self, dag: Optional[TypeDAG] = None) -> None:
        self._dag = dag

    def phi_a(self, collection: EventCollection, type_code: str, code: Optional[str] = None) -> CohortResult:
        """φA: Select events by type (and optionally code)."""
        results = []
        for e in collection:
            type_match = e.event_type.code == type_code
            if self._dag and not type_match:
                target = TypeNode(type_code)
                type_match = self._dag.is_subtype(e.event_type, target)
            code_match = (code is None) or (e.get_code() == code)
            if type_match and code_match:
                results.append(e)
        return CohortResult(query_name=f"φA({type_code},{code})", events=results)

    def phi_b(self, collection: EventCollection, code_a: str, code_b: str) -> CohortResult:
        """φB: Find events where code_a and code_b co-occur (same subject/encounter)."""
        subjects_a: dict[str, FMEvent] = {}
        for e in collection:
            if e.get_code() == code_a:
                key = e.context.get("subject") or e.context.get("encounter") or "global"
                subjects_a[key] = e

        results = []
        for e in collection:
            if e.get_code() == code_b:
                key = e.context.get("subject") or e.context.get("encounter") or "global"
                if key in subjects_a:
                    results.append(subjects_a[key])
                    results.append(e)

        return CohortResult(query_name=f"φB({code_a}∩{code_b})", events=results)

    def phi_c(self, collection: EventCollection, code: str, laterality: str) -> CohortResult:
        """φC: Site-specific query — filter by code and laterality."""
        results = [
            e for e in collection
            if e.get_code() == code and e.get_laterality() == laterality
        ]
        return CohortResult(query_name=f"φC({code},{laterality})", events=results)

    def phi_d(
        self,
        collection: EventCollection,
        code_a: str,
        code_b: str,
        relation: AllenRelation,
    ) -> CohortResult:
        """φD: Temporal sequence — find pairs where event(code_a) relation event(code_b)."""
        events_a = [e for e in collection if e.get_code() == code_a and e.has_temporal()]
        events_b = [e for e in collection if e.get_code() == code_b and e.has_temporal()]

        results = []
        for ea in events_a:
            for eb in events_b:
                rel = allen_relation(ea.temporal, eb.temporal)  # type: ignore
                if rel == relation:
                    results.extend([ea, eb])

        return CohortResult(query_name=f"φD({code_a} {relation.name} {code_b})", events=results)
