# CHANGELOG

All notable changes to CAIRN are documented here.
Format: [Semantic Versioning](https://semver.org/)

---

## [1.0.1] — 2026-05-25

### FM-2 Compliance Fixes (9 findings closed)

**Critical**
- K-1: `TerminologyDriftChecker` integrated into `SILDAnalyzer.compare()` — DRIFT findings now emitted at runtime for all 8 known system-pair mappings
- K-2: `compare()` accepts optional `reference_report` parameter — IMPROVEMENT findings emitted for event codes resolved since previous version

**High**
- H-1: Fixed silent data loss in `fhir_by_code` lookup — changed from `dict[str, FMEvent]` (last-write-wins) to `dict[str, list[FMEvent]]` with pop-based matching in both `SILDAnalyzer` and `HomomorphismChecker`
- H-2: Added integration test `TestTerminologyDrift` for Loss Pattern 3 (SNOMED laterality → ICD-10-GM)

**Medium**
- M-1: Corrected misleading comment for `AllenRelation.CONTAINS` in `PRECISION_LOSS_RELATIONS` (allen.py)
- M-2: Added `reported_codes` set in `SILDAnalyzer` to prevent homomorphism checker from double-reporting findings already classified as SILENT_LOSS or REGRESSION
- M-3: Property test P4 (`test_p4_equals_implies_containment`) now uses `interval_pairs()` + `assume()` instead of trivial self-containment

**Low**
- N-1: Added unit tests for CLI (`test_cli.py`) and FastAPI REST API (`test_api.py`)
- N-2: Extended `KNOWN_LOSSES` in `TerminologyDriftChecker` with 4 additional system-pair mappings: ATC→SNOMED, OPS→SNOMED, LOINC→SNOMED, ICD-10-CM→ICD-10-GM

**Tests**: 50 passed (was 40) — +10 new tests across unit, integration, property suites

---

## [1.0.0] — 2025-01-01

### Initial Release

**FM-2 Core Engine**
- Type system as directed acyclic graph (DAG) via `networkx`
- Allen temporal algebra — all 13 interval relations
- Universal event model as 6-tuple (id, type, temporal, value_set, context, provenance)
- Graph homomorphism checker for structure-preservation verification

**Formal Verification**
- Z3 SMT proofs: value-space containment, temporal precision, interval positivity
- SILD (Silent Information Loss Detector): REGRESSION / IMPROVEMENT / PERSISTENT / SILENT_LOSS / DRIFT classification

**Adapters**
- FHIR R4: Observation, Condition, Procedure, MedicationRequest, AllergyIntolerance, Encounter
- HL7 v2: ORU^R01 (OBX reference range + flag preserved), ADT^A01, RXA
- CSV/DataFrame: column auto-detection

**Analysis Modules**
- Cohort queries φA–φD (FM-2 §10)
- Terminology drift checker (SNOMED→ICD-10-GM, LOINC→ICD-10-GM, ATC→ICD-10-GM)
- Completeness variance analyzer (multi-site KIS comparison: Orbis / iMedOne / Soarian)

**Infrastructure**
- FastAPI REST API (`POST /verify`, `POST /drift`, `GET /health`)
- Click CLI (`cairn verify`, `cairn drift`, `cairn variance`, `cairn version`)
- Hypothesis property-based tests (P1–P6 FM-2 invariants)
- Integration tests for all 5 canonical loss patterns

**Licence**: EUPL-1.2
**Platform**: Codeberg — https://codeberg.org/fm2-project/cairn · GitHub — https://github.com/fmatten/CAIRN
**NOT a medical device** (EU MDR 2017/745 / MPDG)

---

## Upcoming

### [1.1.0] — planned
- MkDocs documentation (DE + EN)
- Woodpecker CI/CD pipeline
- openEHR ADL/OPT adapter
- IPS conformance checker
- PyPI publication as `cairn`
