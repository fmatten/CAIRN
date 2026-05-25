# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
CAIRN Terminology Drift Checker.

Detects drift between code systems across mapping versions.
Supported systems: ICD-10-GM, SNOMED CT, LOINC, ATC, OPS, ICD-10-CM, UCUM, HL7v2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from cairn.core.event import EventCollection, FMEvent


class DriftSeverity(Enum):
    LOW    = auto()
    MEDIUM = auto()
    HIGH   = auto()


@dataclass
class TerminologyDriftFinding:
    code: str
    source_system: str
    target_system: str
    lost_attributes: list[str]
    severity: DriftSeverity
    description: str

    def __str__(self) -> str:
        return (
            f"[DRIFT|{self.severity.name}] {self.source_system}→{self.target_system} "
            f"code={self.code} lost={self.lost_attributes}"
        )


# Known attribute losses per system mapping
KNOWN_LOSSES: dict[tuple[str, str], list[str]] = {
    ("http://snomed.info/sct",      "http://fhir.de/CodeSystem/dimdi/icd-10-gm"): ["laterality", "morphology", "severity"],
    ("http://snomed.info/sct",      "http://hl7.org/fhir/sid/icd-10"):            ["laterality", "morphology", "severity"],
    ("http://loinc.org",            "http://fhir.de/CodeSystem/dimdi/icd-10-gm"): ["panel", "method", "specimen"],
    ("http://www.whocc.no/atc",     "http://fhir.de/CodeSystem/dimdi/icd-10-gm"): ["substance", "route", "dose"],
    ("http://www.whocc.no/atc",     "http://snomed.info/sct"):                     ["route", "dose", "substance"],
    ("http://fhir.de/CodeSystem/dimdi/ops", "http://snomed.info/sct"):             ["laterality", "approach"],
    ("http://loinc.org",            "http://snomed.info/sct"):                     ["method", "specimen", "panel"],
    ("http://hl7.org/fhir/sid/icd-10-cm", "http://fhir.de/CodeSystem/dimdi/icd-10-gm"): ["manifestation", "etiology"],
}


class TerminologyDriftChecker:
    """Detects terminology drift between CDR and FHIR event collections."""

    def check(
        self,
        cdr: EventCollection,
        fhir: EventCollection,
    ) -> list[TerminologyDriftFinding]:
        findings: list[TerminologyDriftFinding] = []

        fhir_by_code = {e.get_code(): e for e in fhir if e.get_code()}

        for cdr_event in cdr:
            code = cdr_event.get_code()
            fhir_event = fhir_by_code.get(code)
            if not fhir_event:
                continue

            src_sys = cdr_event.get_system() or ""
            tgt_sys = fhir_event.get_system() or ""

            if src_sys == tgt_sys:
                continue

            known = KNOWN_LOSSES.get((src_sys, tgt_sys), [])
            actual_lost = [
                attr for attr in known
                if cdr_event.value_set.get(attr) and not fhir_event.value_set.get(attr)
            ]

            if actual_lost:
                severity = (
                    DriftSeverity.HIGH if len(actual_lost) >= 2
                    else DriftSeverity.MEDIUM
                )
                findings.append(TerminologyDriftFinding(
                    code=code,
                    source_system=src_sys,
                    target_system=tgt_sys,
                    lost_attributes=actual_lost,
                    severity=severity,
                    description=f"Terminology mapping lost: {actual_lost}",
                ))

        return findings
