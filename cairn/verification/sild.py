"""
SILD — Silent Information Loss Detector.

Core analysis engine for detecting information loss in CDR→FHIR mappings.

Classification scheme:
    REGRESSION  : Loss detected, worse than previous version
    IMPROVEMENT : Previously lost information now preserved
    PERSISTENT  : Loss detected, unchanged across versions
    SILENT_LOSS : Loss with no FHIR counterpart at all (cardinality n→0)
    DRIFT       : Terminology or value-set divergence over time

Real-world loss patterns (see README):
    1. Temporal precision   — anaesthesia 08:12–11:47 → 00:00–23:59
    2. Negation absence     — "no known allergy" → empty Bundle
    3. Terminology drift    — SNOMED laterality → ICD-10-GM (lost)
    4. HL7 field mapping    — reference range + flag dropped
    5. Cardinality collapse — 4 diagnoses → 2 diagnoses
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional

from cairn.analysis.terminology import TerminologyDriftChecker
from cairn.core.allen import AllenRelation, allen_relation
from cairn.core.event import EventCollection, FMEvent
from cairn.core.homomorphism import HomomorphismChecker
from cairn.core.type_dag import TypeDAG
from cairn.verification.z3_proofs import Z3ProofResult, Z3Verifier, verify_mapping_pair


class SILDClassification(Enum):
    REGRESSION  = auto()   # Loss detected, worse than reference
    IMPROVEMENT = auto()   # Information previously lost now preserved
    PERSISTENT  = auto()   # Loss unchanged across versions
    SILENT_LOSS = auto()   # Event present in CDR, absent in FHIR
    DRIFT       = auto()   # Terminology / value-set divergence
    OK          = auto()   # No loss detected


@dataclass
class SILDFinding:
    """A single detected information loss finding."""

    classification: SILDClassification
    event_code: str
    event_type: str
    description: str
    cdr_value: str = ""
    fhir_value: str = ""
    allen_relation: Optional[AllenRelation] = None
    z3_results: list[Z3ProofResult] = field(default_factory=list)
    severity: str = "MEDIUM"   # LOW / MEDIUM / HIGH / CRITICAL

    def __str__(self) -> str:
        return (
            f"[{self.classification.name}|{self.severity}] "
            f"{self.event_type}/{self.event_code}: {self.description}"
        )


@dataclass
class SILDReport:
    """Complete SILD analysis report for a CDR→FHIR mapping."""

    generated_at: datetime = field(default_factory=datetime.now)
    source_label: str = "CDR"
    target_label: str = "FHIR"
    cdr_event_count: int = 0
    fhir_event_count: int = 0
    findings: list[SILDFinding] = field(default_factory=list)
    mapping_version: str = "1.0.0"

    def add_finding(self, finding: SILDFinding) -> None:
        self.findings.append(finding)

    @property
    def has_loss(self) -> bool:
        return any(
            f.classification != SILDClassification.OK for f in self.findings
        )

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def regression_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.classification == SILDClassification.REGRESSION
        )

    @property
    def silent_loss_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.classification == SILDClassification.SILENT_LOSS
        )

    def by_classification(self, c: SILDClassification) -> list[SILDFinding]:
        return [f for f in self.findings if f.classification == c]

    def print_summary(self) -> None:
        print(f"\n{'═'*64}")
        print(f" CAIRN / SILD Report  —  {self.generated_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"{'═'*64}")
        print(f" Source : {self.source_label}  ({self.cdr_event_count} events)")
        print(f" Target : {self.target_label}  ({self.fhir_event_count} events)")
        print(f" Version: {self.mapping_version}")
        print(f"{'─'*64}")

        if not self.has_loss:
            print(" ✓ No information loss detected.")
        else:
            for f in self.findings:
                print(f" {f}")

        print(f"{'─'*64}")
        print(
            f" Total: {len(self.findings)} findings | "
            f"{self.regression_count} regressions | "
            f"{self.silent_loss_count} silent losses | "
            f"{self.critical_count} critical"
        )
        print(f"{'═'*64}\n")

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at.isoformat(),
            "source_label": self.source_label,
            "target_label": self.target_label,
            "cdr_event_count": self.cdr_event_count,
            "fhir_event_count": self.fhir_event_count,
            "mapping_version": self.mapping_version,
            "summary": {
                "total_findings": len(self.findings),
                "regressions": self.regression_count,
                "silent_losses": self.silent_loss_count,
                "critical": self.critical_count,
                "has_loss": self.has_loss,
            },
            "findings": [
                {
                    "classification": f.classification.name,
                    "severity": f.severity,
                    "event_code": f.event_code,
                    "event_type": f.event_type,
                    "description": f.description,
                    "cdr_value": f.cdr_value,
                    "fhir_value": f.fhir_value,
                    "allen_relation": f.allen_relation.name if f.allen_relation else None,
                }
                for f in self.findings
            ],
        }


class SILDAnalyzer:
    """
    Main SILD analysis engine.

    Compares CDR and FHIR EventCollections and produces a SILDReport
    with classified findings for each detected information loss.
    """

    def __init__(self, type_dag: Optional[TypeDAG] = None) -> None:
        self._dag = type_dag
        self._verifier = Z3Verifier()
        self._homo_checker = HomomorphismChecker(type_dag)

    def compare(
        self,
        cdr: EventCollection,
        fhir: EventCollection,
        mapping_version: str = "1.0.0",
        reference_report: Optional["SILDReport"] = None,
    ) -> SILDReport:
        report = SILDReport(
            source_label=cdr.source_label,
            target_label=fhir.source_label,
            cdr_event_count=len(cdr),
            fhir_event_count=len(fhir),
            mapping_version=mapping_version,
        )

        # H-1: Use list to handle multiple events with the same code
        fhir_by_code: dict[str, list[FMEvent]] = {}
        for e in fhir:
            code = e.get_code()
            if code:
                fhir_by_code.setdefault(code, []).append(e)

        # Track which event_codes already have findings (M-2: avoid double-counting)
        reported_codes: set[str] = set()

        for cdr_event in cdr:
            code = cdr_event.get_code() or "unknown"
            # H-1: pick the first available FHIR event for this code
            fhir_event: Optional[FMEvent] = None
            if fhir_by_code.get(code):
                fhir_event = fhir_by_code[code][0]

            # ── Silent loss: event completely absent in FHIR ───────────────
            if fhir_event is None:
                severity = "CRITICAL" if cdr_event.get_negation() else "HIGH"
                desc = (
                    "Negated event absent in FHIR — downstream reads as 'not recorded'"
                    if cdr_event.get_negation()
                    else "CDR event has no FHIR counterpart"
                )
                report.add_finding(SILDFinding(
                    classification=SILDClassification.SILENT_LOSS,
                    event_code=code,
                    event_type=cdr_event.event_type.code,
                    description=desc,
                    cdr_value=str(cdr_event.value_set),
                    fhir_value="∅",
                    severity=severity,
                ))
                reported_codes.add(code)
                continue

            # ── Temporal precision loss ────────────────────────────────────
            if cdr_event.has_temporal() and fhir_event.has_temporal():
                rel = allen_relation(cdr_event.temporal, fhir_event.temporal)  # type: ignore
                z3_result = self._verifier.prove_temporal_containment(
                    cdr_event.temporal,  # type: ignore
                    fhir_event.temporal,  # type: ignore
                )
                if z3_result.proved:  # CDR ⊂ FHIR → precision lost
                    cdr_dur = int(cdr_event.temporal.duration_seconds // 60)  # type: ignore
                    fhir_dur = int(fhir_event.temporal.duration_seconds // 60)  # type: ignore
                    report.add_finding(SILDFinding(
                        classification=SILDClassification.REGRESSION,
                        event_code=code,
                        event_type=cdr_event.event_type.code,
                        description=(
                            f"Temporal precision lost: CDR {cdr_event.temporal} "
                            f"({cdr_dur}min) → FHIR {fhir_event.temporal} ({fhir_dur}min)"
                        ),
                        cdr_value=str(cdr_event.temporal),
                        fhir_value=str(fhir_event.temporal),
                        allen_relation=rel,
                        z3_results=[z3_result],
                        severity="HIGH",
                    ))
                    reported_codes.add(code)

            elif cdr_event.has_temporal() and not fhir_event.has_temporal():
                report.add_finding(SILDFinding(
                    classification=SILDClassification.REGRESSION,
                    event_code=code,
                    event_type=cdr_event.event_type.code,
                    description="Temporal information completely absent in FHIR event",
                    cdr_value=str(cdr_event.temporal),
                    fhir_value="null",
                    severity="HIGH",
                ))
                reported_codes.add(code)

            # ── Value-space containment ────────────────────────────────────
            z3_vs = self._verifier.prove_value_space_contained(cdr_event, fhir_event)
            if not z3_vs.proved:
                report.add_finding(SILDFinding(
                    classification=SILDClassification.REGRESSION,
                    event_code=code,
                    event_type=cdr_event.event_type.code,
                    description=f"Value-space not preserved: {z3_vs.counterexample}",
                    cdr_value=str(cdr_event.value_set),
                    fhir_value=str(fhir_event.value_set),
                    z3_results=[z3_vs],
                    severity="MEDIUM",
                ))
                reported_codes.add(code)

        # ── Homomorphism check (M-2: only add non-duplicate structural findings) ──
        homo_result = self._homo_checker.check(cdr, fhir)
        if not homo_result.is_homomorphism:
            for detail in homo_result.details:
                # M-2: skip CARDINALITY_COLLAPSED / NEGATION_DROPPED for codes
                # already reported as SILENT_LOSS in the main loop
                skip = False
                for already_reported in reported_codes:
                    if already_reported in detail and already_reported != "STRUCTURE":
                        skip = True
                        break
                if not skip:
                    report.add_finding(SILDFinding(
                        classification=SILDClassification.PERSISTENT,
                        event_code="STRUCTURE",
                        event_type="Homomorphism",
                        description=detail,
                        severity="MEDIUM",
                    ))

        # ── Terminology drift check (K-1) ──────────────────────────────────
        drift_findings = TerminologyDriftChecker().check(cdr, fhir)
        for finding in drift_findings:
            report.add_finding(SILDFinding(
                classification=SILDClassification.DRIFT,
                event_code=finding.code,
                event_type="TerminologyDrift",
                description=finding.description,
                cdr_value=finding.source_system,
                fhir_value=finding.target_system,
                severity=finding.severity.name,
            ))

        # ── K-2: IMPROVEMENT classification vs reference report ───────────
        if reference_report is not None:
            # Collect codes that were REGRESSION or SILENT_LOSS in the reference
            ref_loss_codes: set[str] = {
                f.event_code
                for f in reference_report.findings
                if f.classification in (
                    SILDClassification.REGRESSION,
                    SILDClassification.SILENT_LOSS,
                )
            }
            # Current report codes with REGRESSION or SILENT_LOSS
            current_loss_codes: set[str] = {
                f.event_code
                for f in report.findings
                if f.classification in (
                    SILDClassification.REGRESSION,
                    SILDClassification.SILENT_LOSS,
                )
            }
            # Codes that were lost before but are now fixed
            improved_codes = ref_loss_codes - current_loss_codes
            for improved_code in sorted(improved_codes):
                report.add_finding(SILDFinding(
                    classification=SILDClassification.IMPROVEMENT,
                    event_code=improved_code,
                    event_type="Improvement",
                    description=f"Previously lost information now preserved for code {improved_code}",
                    severity="LOW",
                ))

        return report
