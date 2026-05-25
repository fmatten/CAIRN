# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
CAIRN Command-Line Interface.

Commands:
    cairn verify    — Compare CDR and FHIR bundles
    cairn drift     — Terminology drift analysis
    cairn variance  — Multi-site completeness variance
    cairn version   — Show version info
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

import cairn
from cairn.adapters import CSVAdapter, FHIRAdapter, HL7v2Adapter
from cairn.analysis import CompletenessVarianceAnalyzer, TerminologyDriftChecker
from cairn.verification import SILDAnalyzer


@click.group()
@click.version_option(cairn.__version__, prog_name="cairn")
def main() -> None:
    """CAIRN — Clinical interoperability reference architecture. Built on FM-2."""


@main.command()
@click.option("--source", "-s", required=True, type=click.Path(exists=True), help="Source CDR file (JSON/FHIR Bundle or HL7v2 or CSV)")
@click.option("--target", "-t", required=True, type=click.Path(exists=True), help="Target FHIR Bundle (JSON)")
@click.option("--output", "-o", default=None, type=click.Path(), help="Output file (JSON report). Default: stdout")
@click.option("--mapping-version", default="1.0.0", help="Mapping ruleset version for delta tracking")
@click.option("--source-format", type=click.Choice(["fhir", "hl7v2", "csv"]), default="fhir", help="Source format")
def verify(source: str, target: str, output: str, mapping_version: str, source_format: str) -> None:
    """Compare a CDR source to a FHIR target and detect silent information loss."""

    # Load source
    if source_format == "fhir":
        adapter = FHIRAdapter()
        cdr_events = adapter.load_bundle_file(source)
    elif source_format == "hl7v2":
        adapter_hl7 = HL7v2Adapter()
        cdr_events = adapter_hl7.parse_file(source)
    else:
        adapter_csv = CSVAdapter()
        cdr_events = adapter_csv.load_csv(source)

    cdr_events.source_label = f"CDR ({source_format.upper()})"

    # Load FHIR target
    fhir_adapter = FHIRAdapter()
    fhir_events = fhir_adapter.load_bundle_file(target)
    fhir_events.source_label = "FHIR-R4"

    # Analyse
    analyzer = SILDAnalyzer()
    report = analyzer.compare(cdr_events, fhir_events, mapping_version)
    report.print_summary()

    # Output
    report_dict = report.to_dict()
    if output:
        Path(output).write_text(json.dumps(report_dict, indent=2, ensure_ascii=False), encoding="utf-8")
        click.echo(f"Report written to: {output}")
    else:
        click.echo(json.dumps(report_dict, indent=2, ensure_ascii=False))

    # Exit code: 1 if critical findings
    sys.exit(1 if report.critical_count > 0 else 0)


@main.command()
@click.option("--source", "-s", required=True, type=click.Path(exists=True), help="CDR source bundle (JSON)")
@click.option("--target", "-t", required=True, type=click.Path(exists=True), help="FHIR target bundle (JSON)")
def drift(source: str, target: str) -> None:
    """Detect terminology drift between CDR and FHIR event collections."""
    adapter = FHIRAdapter()
    cdr_events = adapter.load_bundle_file(source)
    fhir_events = adapter.load_bundle_file(target)

    checker = TerminologyDriftChecker()
    findings = checker.check(cdr_events, fhir_events)

    if not findings:
        click.echo("✓ No terminology drift detected.")
    else:
        click.echo(f"Found {len(findings)} drift finding(s):\n")
        for f in findings:
            click.echo(f"  {f}")


@main.command()
@click.option("--files", "-f", required=True, multiple=True, help="CSV files to compare (format: file.csv:SiteName:KISName)")
@click.option("--fields", default="laterality,certainty,referenceRange,interpretation", help="Comma-separated field names to analyse")
def variance(files: tuple, fields: str) -> None:
    """Analyse field completeness variance across multiple sites and KIS systems."""
    analyzer = CompletenessVarianceAnalyzer()
    adapter = CSVAdapter()

    for file_spec in files:
        parts = file_spec.split(":")
        path = parts[0]
        site = parts[1] if len(parts) > 1 else Path(path).stem
        kis = parts[2] if len(parts) > 2 else "unknown"

        collection = adapter.load_csv(path)
        analyzer.add_collection(collection, site=site, source_system=kis)
        click.echo(f"  Loaded: {path} → {site} ({kis})")

    field_list = [f.strip() for f in fields.split(",")]
    for field_name in field_list:
        report = analyzer.analyze_field(field_name)
        report.print_summary()


@main.command(name="version")
def version_cmd() -> None:
    """Show CAIRN version and licence information."""
    click.echo(f"CAIRN {cairn.__version__}")
    click.echo(f"Licence  : {cairn.__licence__}")
    click.echo(f"Repo     : {cairn.__repository__}")
    click.echo(f"")
    click.echo(f"NOT a medical device (EU MDR 2017/745 / MPDG).")
    click.echo(f"For research and interoperability validation only.")
