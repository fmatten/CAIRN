"""
CAIRN Test Configuration.

Shared fixtures for unit, integration and property tests.
"""

import pytest
from datetime import datetime, timezone

from cairn.core.allen import TimeInterval
from cairn.core.event import EventCollection, FMEvent
from cairn.core.type_dag import TypeNode, build_clinical_type_dag


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 3, 15, hour, minute, 0, tzinfo=timezone.utc)


@pytest.fixture
def clinical_dag():
    return build_clinical_type_dag()


@pytest.fixture
def anaesthesia_cdr_event():
    return FMEvent(
        event_type=TypeNode("Anaesthesia", "cairn"),
        temporal=TimeInterval(start=dt(8, 12), end=dt(11, 47)),
        value_set={"code": "72641008", "system": "http://snomed.info/sct"},
    )


@pytest.fixture
def anaesthesia_fhir_event_precision_lost():
    """FHIR event with temporal precision lost (00:00–23:59)."""
    return FMEvent(
        event_type=TypeNode("Procedure", "cairn"),
        temporal=TimeInterval(start=dt(0, 0), end=dt(23, 59)),
        value_set={"code": "72641008", "system": "http://snomed.info/sct"},
    )


@pytest.fixture
def negated_allergy_cdr():
    return FMEvent(
        event_type=TypeNode("AllergyStatement", "cairn"),
        value_set={
            "code": "716186003",
            "system": "http://snomed.info/sct",
            "negation": True,
            "substance": "Penicillin",
        },
    )
