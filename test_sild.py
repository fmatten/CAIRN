"""
Integration tests — SILD real-world loss patterns.

Tests the five canonical loss patterns from CAIRN documentation:
    1. Temporal precision loss     (anaesthesia 08:12–11:47 → 00:00–23:59)
    2. Negation absence            ("no known allergy" → empty Bundle)
    3. Terminology drift           (SNOMED laterality → ICD-10-GM)
    4. HL7 field mapping loss      (ref range + flag dropped)
    5. Cardinality collapse        (4 diagnoses → 2)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cairn.core.allen import TimeInterval
from cairn.core.event import EventCollection, FMEvent
from cairn.core.type_dag import TypeNode
from cairn.verification import SILDAnalyzer, SILDClassification


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 3, 15, hour, minute, 0, tzinfo=timezone.utc)


def make_collection(*events: FMEvent, label: str = "test") -> EventCollection:
    c = EventCollection(source_label=label)
    for e in events:
        c.add(e)
    return c


# ── 1. Temporal precision loss ────────────────────────────────────────────────

class TestTemporalPrecisionLoss:

    def test_anaesthesia_precision_lost(self):
        """08:12–11:47 → 00:00–23:59: SILD must detect REGRESSION."""
        cdr = make_collection(
            FMEvent(
                event_type=TypeNode("Anaesthesia", "cairn"),
                temporal=TimeInterval(start=dt(8, 12), end=dt(11, 47)),
                value_set={"code": "72641008", "system": "http://snomed.info/sct"},
            ),
            label="CDR",
        )
        fhir = make_collection(
            FMEvent(
                event_type=TypeNode("Procedure", "cairn"),
                temporal=TimeInterval(start=dt(0, 0), end=dt(23, 59)),
                value_set={"code": "72641008", "system": "http://snomed.info/sct"},
            ),
            label="FHIR",
        )

        report = SILDAnalyzer().compare(cdr, fhir)
        assert report.has_loss
        regressions = report.by_classification(SILDClassification.REGRESSION)
        temporal_regressions = [
            f for f in regressions if "temporal" in f.description.lower()
        ]
        assert len(temporal_regressions) >= 1

    def test_equal_temporal_no_loss(self):
        """Same interval: no temporal loss."""
        interval = TimeInterval(start=dt(8, 12), end=dt(11, 47))
        cdr = make_collection(
            FMEvent(
                event_type=TypeNode("Procedure", "cairn"),
                temporal=interval,
                value_set={"code": "A01", "system": "local"},
            ),
            label="CDR",
        )
        fhir = make_collection(
            FMEvent(
                event_type=TypeNode("Procedure", "cairn"),
                temporal=interval,
                value_set={"code": "A01", "system": "local"},
            ),
            label="FHIR",
        )
        report = SILDAnalyzer().compare(cdr, fhir)
        temporal_regressions = [
            f for f in report.findings
            if "temporal" in f.description.lower()
        ]
        assert len(temporal_regressions) == 0


# ── 2. Negation absence ───────────────────────────────────────────────────────

class TestNegationAbsence:

    def test_negated_allergy_missing_in_fhir_is_critical(self):
        """'No known allergy' → empty Bundle: SILENT_LOSS, CRITICAL severity."""
        cdr = make_collection(
            FMEvent(
                event_type=TypeNode("AllergyStatement", "cairn"),
                value_set={
                    "code": "716186003",
                    "system": "http://snomed.info/sct",
                    "negation": True,
                    "substance": "Penicillin",
                },
            ),
            label="CDR",
        )
        fhir = make_collection(label="FHIR")  # empty — negation not mapped

        report = SILDAnalyzer().compare(cdr, fhir)
        assert report.has_loss
        silent = report.by_classification(SILDClassification.SILENT_LOSS)
        assert len(silent) == 1
        assert silent[0].severity == "CRITICAL"

    def test_non_negated_event_missing_is_high(self):
        """Normal event missing in FHIR: SILENT_LOSS, HIGH severity."""
        cdr = make_collection(
            FMEvent(
                event_type=TypeNode("Condition", "cairn"),
                value_set={"code": "I10", "system": "http://fhir.de/CodeSystem/dimdi/icd-10-gm"},
            ),
            label="CDR",
        )
        fhir = make_collection(label="FHIR")

        report = SILDAnalyzer().compare(cdr, fhir)
        silent = report.by_classification(SILDClassification.SILENT_LOSS)
        assert len(silent) >= 1
        assert silent[0].severity == "HIGH"


# ── 3. HL7 field mapping loss ─────────────────────────────────────────────────

class TestHL7FieldMappingLoss:

    def test_reference_range_and_flag_dropped(self):
        """Cholesterol: ref range + 'H' flag lost in FHIR → value-space REGRESSION."""
        cdr = make_collection(
            FMEvent(
                event_type=TypeNode("LabResult", "cairn"),
                temporal=TimeInterval(start=dt(9), end=dt(9, 1)),
                value_set={
                    "code": "2093-3",
                    "system": "http://loinc.org",
                    "value": 5.8,
                    "unit": "mmol/L",
                    "referenceRange": "<5.2",
                    "interpretation": "H",
                },
            ),
            label="HL7v2",
        )
        fhir = make_collection(
            FMEvent(
                event_type=TypeNode("Observation", "cairn"),
                temporal=TimeInterval(start=dt(9), end=dt(9, 1)),
                value_set={
                    "code": "2093-3",
                    "system": "http://loinc.org",
                    "value": 5.8,
                    "unit": "mmol/L",
                    # referenceRange: missing
                    # interpretation: missing
                },
            ),
            label="FHIR",
        )

        report = SILDAnalyzer().compare(cdr, fhir)
        assert report.has_loss
        regressions = report.by_classification(SILDClassification.REGRESSION)
        value_space_losses = [
            f for f in regressions if "value-space" in f.description.lower()
        ]
        assert len(value_space_losses) >= 1


# ── 4. Cardinality collapse ───────────────────────────────────────────────────

class TestCardinalityCollapse:

    def test_four_diagnoses_to_two(self):
        """4 CDR diagnoses → 2 FHIR diagnoses: SILENT_LOSS for missing pair."""
        def make_diagnosis(code: str, certainty: str = "confirmed") -> FMEvent:
            return FMEvent(
                event_type=TypeNode("Condition", "cairn"),
                value_set={
                    "code": code,
                    "system": "http://fhir.de/CodeSystem/dimdi/icd-10-gm",
                    "certainty": certainty,
                },
            )

        cdr = make_collection(
            make_diagnosis("I10"),          # Hauptdiagnose
            make_diagnosis("E11"),          # Nebendiagnose
            make_diagnosis("N18", "suspected"),  # suspected → dropped in FHIR
            make_diagnosis("Z87.3"),        # historical → dropped in FHIR
            label="CDR",
        )
        fhir = make_collection(
            make_diagnosis("I10"),
            make_diagnosis("E11"),
            label="FHIR",
        )

        report = SILDAnalyzer().compare(cdr, fhir)
        silent = report.by_classification(SILDClassification.SILENT_LOSS)
        assert len(silent) == 2  # N18 and Z87.3 both missing
        missing_codes = {f.event_code for f in silent}
        assert "N18" in missing_codes
        assert "Z87.3" in missing_codes


# ── 5. No loss — clean mapping ────────────────────────────────────────────────

class TestNoLoss:

    def test_perfect_mapping_no_findings(self):
        """A perfect mapping produces no SILD findings."""
        event = FMEvent(
            event_type=TypeNode("LabResult", "cairn"),
            temporal=TimeInterval(start=dt(9), end=dt(9, 1)),
            value_set={
                "code": "2093-3",
                "system": "http://loinc.org",
                "value": 5.8,
                "unit": "mmol/L",
                "referenceRange": "<5.2",
                "interpretation": "H",
            },
        )
        cdr = make_collection(event, label="CDR")
        fhir = make_collection(event, label="FHIR")

        report = SILDAnalyzer().compare(cdr, fhir)
        loss_findings = [
            f for f in report.findings
            if f.classification != SILDClassification.OK
            and "STRUCTURE" not in f.event_code
        ]
        assert len(loss_findings) == 0
