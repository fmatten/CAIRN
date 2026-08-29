# CHANGELOG

All notable changes to CAIRN are documented here.
Format: [Semantic Versioning](https://semver.org/)

---

## [1.0.5] — 2026-08-29

### Version metadata harmonised, Zenodo source archive replaced

- Version numbers unified across the three metadata files, which had drifted
  apart: `pyproject.toml` 1.0.4, `CITATION.cff` 1.0.2, `.zenodo.json` 1.0.1.
  `.zenodo.json` had never been advanced past 1.0.1 and still carried the 1.0.1
  release description.
- **Reason for the release.** The Zenodo record 10.5281/zenodo.20375036 declares
  version 1.0.4 and the licence AGPL-3.0-only OR Commercial, but the archive
  attached to it is `cairn-1.0.1-source.zip`, whose `LICENCE` is the EUPL-1.2
  text and which has no `LICENSE-COMMERCIAL.md`. Published Zenodo files cannot be
  replaced in place, so the correction is made by publishing a new version with a
  source archive built from the `v1.0.5` tag.
- `tools/zenodo_upload.py`: `UPLOAD_FILES` now points at the 1.0.5 source
  archive; the three previous entries referred to files that no longer exist, so
  a run would have deleted the files of the new version and uploaded nothing.

### Carried in from the metadata work of 28–29 August 2026

- `.zenodo.json`: licence field corrected `eupl-1.2` → `agpl-3.0-only`; keyword
  "SNOMED CT" removed; keyword "openEHR" removed.
- `pyproject.toml`, `CITATION.cff`, `docs/CODEBERG_SETUP.md`: keyword "openEHR"
  removed. The openEHR ADL/OPT adapter is listed under *Upcoming* in this file
  and is not implemented; the keyword claimed it as present. The openEHR
  reference in the `.zenodo.json` bibliography and the planned entry below are
  unaffected.
- `tools/zenodo_upload.py`: `RECORD_ID` corrected from 19483182 (version 1.0.0,
  9 April 2026, superseded) to 20375036 (the current version); comment added
  recording that the licence field is not writable through the legacy deposit
  API, which accepts it with HTTP 200/202 and does not store it.
- Source licence headers unified on `AGPL-3.0-only OR LicenseRef-ISCaD-Commercial`;
  the runtime no longer reports EUPL to its users.

---

## [1.0.3] — 2026-05-25

### Licence Change: EUPL-1.2 → AGPL-3.0

- Replaced EUPL-1.2 with GNU Affero General Public License v3 (AGPL-3.0-only)
- Updated `LICENCE` file with full AGPL-3.0 text
- Updated `pyproject.toml`: classifier → `GNU Affero General Public License v3`
- Added `SPDX-License-Identifier: AGPL-3.0-only` headers to all 21 Python source files
- Updated README badge: EUPL-1.2 → AGPL-3.0

---

## [1.0.3] — 2026-05-25

### Licence Change: EUPL-1.2 → AGPL-3.0-only OR Commercial

- Replaced EUPL-1.2 with AGPL-3.0-only OR LicenseRef-ISCaD-Commercial (Dual-Lizenz)
- Updated LICENCE file with full AGPL-3.0 text
- Added LICENSE-COMMERCIAL.md for commercial licensing
- Updated pyproject.toml classifier
- Updated SPDX headers in all 21 Python source files
- Updated README badge and licence section

---

## [1.0.2] — 2026-05-25

### PyPI Metadata

- Updated `description` field: now reflects FM-2, Allen algebra, Z3, SILD explicitly
- URLs: all `fm2-project/cairn` references replaced with `iscad/cairn`
- Synchronized GitHub, Codeberg, Zenodo, PyPI

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

**PyPI**: Published as [`cairn-clinical`](https://pypi.org/project/cairn-clinical/) (`pip install cairn-clinical`)

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
**Platform**: Codeberg — https://codeberg.org/iscad/cairn · GitHub — https://github.com/fmatten/CAIRN
**NOT a medical device** (EU MDR 2017/745 / MPDG)

---

## Upcoming

### [1.1.0] — planned
- MkDocs documentation (DE + EN)
- Woodpecker CI/CD pipeline
- openEHR ADL/OPT adapter
- IPS conformance checker
- PyPI publication as `cairn`
