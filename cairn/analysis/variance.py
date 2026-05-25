# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
CAIRN Completeness Variance Analyzer.

Detects systematic field completeness differences across
hospital sites and source KIS systems (e.g. Agfa Orbis,
iMedOne, Soarian).

Variance types:
    SYSTEMATIC_VARIANCE : Pattern correlates with source KIS
    HUMAN_VARIANCE      : Pattern varies within same KIS
    COMPOUND_LOSS       : Both KIS-systematic and human variance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from cairn.core.event import EventCollection


class VarianceType(Enum):
    SYSTEMATIC_VARIANCE = auto()   # KIS-correlated
    HUMAN_VARIANCE      = auto()   # Within same KIS
    COMPOUND_LOSS       = auto()   # Both


@dataclass
class FieldCompletenessReport:
    site: str
    source_system: str
    field_name: str
    completeness: float        # 0.0–1.0
    total_events: int
    populated_events: int
    variance_type: Optional[VarianceType] = None

    def __str__(self) -> str:
        pct = f"{self.completeness*100:.1f}%"
        vt = self.variance_type.name if self.variance_type else "OK"
        return f"[{vt}] {self.site}/{self.source_system} field={self.field_name} completeness={pct}"


@dataclass
class VarianceReport:
    field_name: str
    reports: list[FieldCompletenessReport] = field(default_factory=list)

    @property
    def is_systematic(self) -> bool:
        """True if completeness correlates with source_system."""
        sys_completeness: dict[str, list[float]] = {}
        for r in self.reports:
            sys_completeness.setdefault(r.source_system, []).append(r.completeness)
        if len(sys_completeness) < 2:
            return False
        averages = {sys: sum(vals)/len(vals) for sys, vals in sys_completeness.items()}
        max_avg = max(averages.values())
        min_avg = min(averages.values())
        # If spread > 30pp → systematic
        return (max_avg - min_avg) > 0.30

    def print_summary(self) -> None:
        print(f"\nField: {self.field_name}")
        print(f"  Systematic variance: {'YES' if self.is_systematic else 'no'}")
        for r in sorted(self.reports, key=lambda x: x.completeness, reverse=True):
            bar = "█" * int(r.completeness * 20)
            print(f"  {r.site:12s} ({r.source_system:8s}) {bar:20s} {r.completeness*100:5.1f}%")


class CompletenessVarianceAnalyzer:
    """
    Analyse field completeness across multiple sites and KIS systems.

    Usage:
        analyzer = CompletenessVarianceAnalyzer()
        analyzer.add_collection(events_haus_a, site="Haus A", source_system="Orbis")
        analyzer.add_collection(events_haus_b, site="Haus B", source_system="iMedOne")
        analyzer.add_collection(events_haus_c, site="Haus C", source_system="Soarian")
        report = analyzer.analyze_field("laterality")
    """

    def __init__(self) -> None:
        self._collections: list[tuple[EventCollection, str, str]] = []

    def add_collection(
        self,
        collection: EventCollection,
        site: str,
        source_system: str,
    ) -> None:
        self._collections.append((collection, site, source_system))

    def analyze_field(self, field_name: str) -> VarianceReport:
        """Compute completeness of field_name across all registered collections."""
        report = VarianceReport(field_name=field_name)

        for collection, site, source_system in self._collections:
            total = len(collection)
            if total == 0:
                continue
            populated = sum(
                1 for e in collection
                if e.value_set.get(field_name) not in (None, "", [])
            )
            completeness = populated / total

            fcr = FieldCompletenessReport(
                site=site,
                source_system=source_system,
                field_name=field_name,
                completeness=completeness,
                total_events=total,
                populated_events=populated,
            )
            report.reports.append(fcr)

        # Classify variance
        if report.is_systematic:
            for r in report.reports:
                r.variance_type = VarianceType.SYSTEMATIC_VARIANCE

        return report

    def analyze_fields(self, fields: list[str]) -> list[VarianceReport]:
        return [self.analyze_field(f) for f in fields]
