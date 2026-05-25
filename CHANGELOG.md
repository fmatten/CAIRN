# CHANGELOG

All notable changes to CAIRN are documented here.
Format: [Semantic Versioning](https://semver.org/)

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
**Platform**: Codeberg — https://codeberg.org/fm2-project/cairn
**NOT a medical device** (EU MDR 2017/745 / MPDG)

---

## Upcoming

### [1.1.0] — planned
- MkDocs documentation (DE + EN)
- Woodpecker CI/CD pipeline
- openEHR ADL/OPT adapter
- IPS conformance checker
- Delta analyzer (mapping regression/improvement across versions)
- PyPI publication as `cairn`
