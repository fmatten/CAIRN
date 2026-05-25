"""
Unit tests — FM-2 Core: Type DAG, Allen Algebra, Event Model.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from cairn.core.allen import (
    AllenRelation,
    TimeInterval,
    allen_relation,
    inverse_relation,
    temporal_containment,
)
from cairn.core.event import EventCollection, FMEvent
from cairn.core.type_dag import TypeDAG, TypeNode, build_clinical_type_dag


# ── TimeInterval ──────────────────────────────────────────────────────────────

def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 3, 15, hour, minute, 0, tzinfo=timezone.utc)


def test_interval_positive_duration_ok():
    i = TimeInterval(start=dt(8), end=dt(10))
    assert i.duration_seconds == 7200.0


def test_interval_zero_duration_raises():
    """FM-2 invariant: start < end strictly."""
    with pytest.raises(ValueError, match="strictly positive"):
        TimeInterval(start=dt(8), end=dt(8))


def test_interval_negative_duration_raises():
    with pytest.raises(ValueError):
        TimeInterval(start=dt(10), end=dt(8))


# ── Allen Relations ───────────────────────────────────────────────────────────

class TestAllenRelations:
    """All 13 Allen relations must be correctly identified."""

    def _i(self, hs, hm, he, hm2) -> TimeInterval:
        return TimeInterval(start=dt(hs, hm), end=dt(he, hm2))

    def test_precedes(self):
        a = TimeInterval(start=dt(8), end=dt(9))
        b = TimeInterval(start=dt(10), end=dt(11))
        assert allen_relation(a, b) == AllenRelation.PRECEDES

    def test_preceded_by(self):
        a = TimeInterval(start=dt(10), end=dt(11))
        b = TimeInterval(start=dt(8), end=dt(9))
        assert allen_relation(a, b) == AllenRelation.PRECEDED_BY

    def test_meets(self):
        a = TimeInterval(start=dt(8), end=dt(10))
        b = TimeInterval(start=dt(10), end=dt(12))
        assert allen_relation(a, b) == AllenRelation.MEETS

    def test_met_by(self):
        a = TimeInterval(start=dt(10), end=dt(12))
        b = TimeInterval(start=dt(8), end=dt(10))
        assert allen_relation(a, b) == AllenRelation.MET_BY

    def test_equals(self):
        a = TimeInterval(start=dt(8), end=dt(10))
        b = TimeInterval(start=dt(8), end=dt(10))
        assert allen_relation(a, b) == AllenRelation.EQUALS

    def test_during(self):
        a = TimeInterval(start=dt(9), end=dt(10))
        b = TimeInterval(start=dt(8), end=dt(11))
        assert allen_relation(a, b) == AllenRelation.DURING

    def test_contains(self):
        a = TimeInterval(start=dt(8), end=dt(11))
        b = TimeInterval(start=dt(9), end=dt(10))
        assert allen_relation(a, b) == AllenRelation.CONTAINS

    def test_overlaps(self):
        a = TimeInterval(start=dt(8), end=dt(10))
        b = TimeInterval(start=dt(9), end=dt(11))
        assert allen_relation(a, b) == AllenRelation.OVERLAPS

    def test_overlapped_by(self):
        a = TimeInterval(start=dt(9), end=dt(11))
        b = TimeInterval(start=dt(8), end=dt(10))
        assert allen_relation(a, b) == AllenRelation.OVERLAPPED_BY

    def test_started_by(self):
        a = TimeInterval(start=dt(8), end=dt(10))
        b = TimeInterval(start=dt(8), end=dt(12))
        assert allen_relation(a, b) == AllenRelation.STARTED_BY

    def test_starts_with(self):
        a = TimeInterval(start=dt(8), end=dt(12))
        b = TimeInterval(start=dt(8), end=dt(10))
        assert allen_relation(a, b) == AllenRelation.STARTS_WITH

    def test_finishes(self):
        a = TimeInterval(start=dt(9), end=dt(12))
        b = TimeInterval(start=dt(8), end=dt(12))
        assert allen_relation(a, b) == AllenRelation.FINISHES

    def test_finished_by(self):
        a = TimeInterval(start=dt(8), end=dt(12))
        b = TimeInterval(start=dt(9), end=dt(12))
        assert allen_relation(a, b) == AllenRelation.FINISHED_BY

    def test_inverse_symmetry(self):
        """inverse(inverse(r)) == r for all r."""
        from cairn.core.allen import AllenRelation as AR
        for r in AR:
            assert inverse_relation(inverse_relation(r)) == r


# ── Type DAG ──────────────────────────────────────────────────────────────────

class TestTypeDAG:

    def test_build_clinical_dag_is_acyclic(self):
        dag = build_clinical_type_dag()
        assert dag.validate_dag()

    def test_subtype_direct(self):
        dag = build_clinical_type_dag()
        assert dag.is_subtype(TypeNode("LabResult", "cairn"), TypeNode("Observation", "cairn"))

    def test_subtype_transitive(self):
        dag = build_clinical_type_dag()
        # LabResult → Observation → Resource
        assert dag.is_subtype(TypeNode("LabResult", "cairn"), TypeNode("Resource", "cairn"))

    def test_not_subtype(self):
        dag = build_clinical_type_dag()
        assert not dag.is_subtype(TypeNode("Condition", "cairn"), TypeNode("Observation", "cairn"))

    def test_lca(self):
        dag = build_clinical_type_dag()
        lca = dag.least_common_ancestor(
            TypeNode("LabResult", "cairn"),
            TypeNode("VitalSign", "cairn"),
        )
        assert lca is not None
        assert lca.code == "Observation"

    def test_self_is_subtype(self):
        dag = build_clinical_type_dag()
        node = TypeNode("Procedure", "cairn")
        assert dag.is_subtype(node, node)


# ── Event Model ───────────────────────────────────────────────────────────────

class TestFMEvent:

    def test_event_defaults(self):
        e = FMEvent()
        assert e.event_id != ""
        assert e.event_type.code == "Unknown"
        assert not e.has_temporal()

    def test_event_with_temporal(self):
        interval = TimeInterval(start=dt(8, 12), end=dt(11, 47))
        e = FMEvent(
            event_type=TypeNode("Anaesthesia", "cairn"),
            temporal=interval,
            value_set={"code": "72641008", "system": "http://snomed.info/sct"},
        )
        assert e.has_temporal()
        assert e.get_code() == "72641008"
        assert e.temporal.duration_seconds == pytest.approx(215 * 60)

    def test_negation_flag(self):
        e = FMEvent(
            event_type=TypeNode("AllergyStatement", "cairn"),
            value_set={"code": "716186003", "negation": True},
        )
        assert e.get_negation() is True

    def test_event_collection_filter(self):
        coll = EventCollection(source_label="test")
        coll.add(FMEvent(event_type=TypeNode("LabResult", "cairn"),
                         value_set={"code": "2093-3"}))
        coll.add(FMEvent(event_type=TypeNode("Condition", "cairn"),
                         value_set={"code": "I10"}))
        lab = coll.filter_by_type("LabResult")
        assert len(lab) == 1
