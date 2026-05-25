# CAIRN

**Clinical interoperability reference architecture. Built on FM-2.**

[![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)](https://github.com/fmatten/CAIRN/releases)
[![Licence: EUPL-1.2](https://img.shields.io/badge/Licence-EUPL--1.2-blue.svg)](https://eupl.eu/1.2/en/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20375036.svg)](https://doi.org/10.5281/zenodo.20375036)
[![PyPI](https://img.shields.io/pypi/v/cairn-clinical.svg)](https://pypi.org/project/cairn-clinical/)
[![Tests](https://img.shields.io/badge/tests-50%20passed-brightgreen.svg)](https://github.com/fmatten/CAIRN)
[![NOT a Medical Device](https://img.shields.io/badge/NOT%20a-Medical%20Device-important.svg)](#not-a-medical-device)

---

> ⚠️ **CAIRN is NOT a medical device** as defined by EU MDR 2017/745, EU IVDR 2017/746, or MPDG.
> It is a mathematical framework for research and interoperability validation only.
> It does not process real patient data in production contexts.

---

## What is CAIRN?

CAIRN is an open-source reference architecture for formal verification of clinical
interoperability mappings. It implements FM-2 — a mathematical framework
modelling clinical data through:

- a **type system** as a directed acyclic graph (DAG)
- **Allen temporal algebra** (13 interval relations)
- a **universal event model** as a 6-tuple: `(id, type, temporal, value_set, context, provenance)`
- **Z3 SMT proofs** for value-space containment and structural preservation
- **SILD** (Silent Information Loss Detector) for CDR-to-FHIR mapping verification

CAIRN answers a practical question:

> *What is silently lost when clinical data moves from one system to another —
> and how can we prove it formally, before production?*

---

## Was ist CAIRN?

CAIRN ist eine offene Referenzarchitektur für die formale Verifikation klinischer
Interoperabilitäts-Mappings. Sie implementiert FM-2 — ein mathematisches Modell
klinischer Daten auf Basis von:

- einem **Typsystem** als gerichtetem azyklischen Graphen (DAG)
- **Allen-Temporalalgebra** (13 Intervallrelationen)
- einem **universellen Ereignismodell** als 6-Tupel: `(id, type, temporal, value_set, context, provenance)`
- **Z3 SMT-Beweisen** für Werteraum-Containment und Strukturerhalt
- **SILD** (Silent Information Loss Detector) zur CDR-zu-FHIR-Verifikation

> *Was geht beim Datentransfer zwischen klinischen Systemen still verloren —
> und wie lässt sich das formal nachweisen, bevor es in Produktion geht?*

---

## Real-World Loss Patterns Detected by CAIRN

| Loss Class | Clinical Example | FM-2 Formalism | SILD Class |
|---|---|---|---|
| Temporal precision | Anaesthesia 08:12–11:47 → 00:00–23:59 | Allen: DURING | REGRESSION |
| Negation absence | "No known allergy" → empty FHIR Bundle | Cardinality n→0 | SILENT\_LOSS |
| Terminology drift | SNOMED laterality → ICD-10-GM (lost) | Value-space ⊊ | DRIFT |
| HL7 field mapping | Cholesterol ref. range + "H" flag dropped | Z3: not surjective | PERSISTENT |
| Cardinality collapse | 4 CDR diagnoses → 2 FHIR diagnoses | φ\_B: CDR ≠ FHIR | REGRESSION |

---

## Quickstart

```bash
pip install cairn-clinical
```

```python
from cairn.adapters import FHIRAdapter
from cairn.verification import SILDAnalyzer

# Load CDR source and FHIR target
adapter     = FHIRAdapter()
cdr_events  = adapter.load_bundle_file("source_cdr.json")
fhir_events = adapter.load_bundle_file("mapped_fhir.json")

# Detect silent information loss
report = SILDAnalyzer().compare(cdr_events, fhir_events)
report.print_summary()
```

```
════════════════════════════════════════════════════════════════
 CAIRN / SILD Report  —  2026-05-25 09:00
════════════════════════════════════════════════════════════════
 Source : CDR  (5 events)
 Target : FHIR-R4  (3 events)
────────────────────────────────────────────────────────────────
 [SILENT_LOSS|CRITICAL] AllergyStatement/716186003: Negated event absent in FHIR
 [REGRESSION|HIGH]      Anaesthesia/72641008: Temporal precision lost (215min → 1439min)
 [DRIFT|HIGH]           TerminologyDrift/416098002: SNOMED laterality → ICD-10-GM (lost)
 [REGRESSION|MEDIUM]    LabResult/2093-3: Value-space not preserved: missing referenceRange
────────────────────────────────────────────────────────────────
 Total: 4 findings | 2 regressions | 1 silent losses | 1 critical
════════════════════════════════════════════════════════════════
```

```bash
# CLI
cairn verify   --source cdr.json  --target fhir.json  --output report.json
cairn drift    --source cdr.json  --target fhir.json
cairn variance --files a.csv:HausA:Orbis  --files b.csv:HausB:iMedOne
cairn version
```

### Version comparison (IMPROVEMENT detection)

```python
# Compare two mapping versions — detect improvements and regressions
report_v1 = SILDAnalyzer().compare(cdr_events, fhir_v1_events, mapping_version="1.0")
report_v2 = SILDAnalyzer().compare(cdr_events, fhir_v2_events, mapping_version="2.0",
                                    reference_report=report_v1)
# IMPROVEMENT findings mark event codes resolved since v1
report_v2.print_summary()
```

---

## Modules

| Module | Contents |
|---|---|
| `cairn.core` | Type DAG · Allen algebra (13 relations) · 6-tuple event model · Homomorphism checker |
| `cairn.verification` | Z3 SMT proofs · Value-space containment · SILD engine (all 6 classifications) |
| `cairn.adapters` | FHIR R4 · HL7 v2 (ORU/ADT/RXA) · CSV/DataFrame |
| `cairn.analysis` | Cohort queries φA–φD · Terminology drift (8 system pairs) · Multi-site KIS variance |
| `cairn.api` | FastAPI REST (`POST /verify` · `POST /drift` · `GET /health`) |
| `cairn.cli` | Click CLI (`verify` · `drift` · `variance` · `version`) |

---

## Architecture

```
cairn/
├── core/
│   ├── allen.py          # Allen temporal algebra — 13 interval relations
│   ├── event.py          # Universal event model — 6-tuple (FMEvent)
│   ├── homomorphism.py   # Structure-preservation checker
│   └── type_dag.py       # Type system as directed acyclic graph
│
├── verification/
│   ├── sild.py           # Silent Information Loss Detector (SILD)
│   └── z3_proofs.py      # Z3 SMT formal proofs
│
├── adapters/
│   ├── csv_df.py         # CSV / pandas DataFrame
│   ├── fhir_r4.py        # FHIR R4 (Observation, Condition, Procedure, ...)
│   └── hl7v2.py          # HL7 v2 (ORU^R01, ADT^A01, RXA)
│
├── analysis/
│   ├── cohort.py         # FM-2 cohort queries φA–φD
│   ├── terminology.py    # Terminology drift checker (8 system-pair mappings)
│   └── variance.py       # Multi-site completeness variance (KIS comparison)
│
├── api/
│   └── app.py            # FastAPI REST API
│
└── cli/
    └── commands.py       # Click command-line interface

tests/
├── unit/                 # FM-2 core + CLI + API (32 tests)
├── integration/          # SILD — all 5 real-world loss patterns + drift (8 tests)
└── property/             # Hypothesis property tests — FM-2 invariants P1–P6
```

---

## Dependencies

CAIRN is built exclusively on publicly available PyPI libraries.
All dependencies with their licences are documented in [NOTICE](./NOTICE).

```toml
# Core
networkx       >= 3.2    # Type DAG, homomorphism       BSD-3-Clause
z3-solver      >= 4.12   # SMT formal verification       MIT
pydantic       >= 2.5    # Schema validation             MIT
pandas         >= 2.1    # DataFrame adapter             BSD-3-Clause

# Healthcare standards
fhir.resources >= 7.1    # FHIR R4                      BSD-3-Clause
hl7            >= 0.4    # HL7 v2 parsing               BSD-3-Clause

# API & CLI
fastapi        >= 0.110  # REST API                      MIT
httpx          >= 0.27   # API test client               BSD-3-Clause
click          >= 8.1    # CLI                           BSD-3-Clause
```

---

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

```
50 passed in 3.16s

tests/unit/        32 tests  (Type DAG · Allen algebra · event model · CLI · API)
tests/integration/  8 tests  (5 SILD loss patterns + terminology drift)
tests/property/     6 tests  (Hypothesis: FM-2 invariants P1–P6)
```

---

## Licence

CAIRN is licensed under the **European Union Public Licence v. 1.2 (EUPL-1.2)**.

- Free to use, modify, and distribute
- Modifications **must be contributed back** under the same licence
- Copyleft covers network use (SaaS)
- Legally valid in all EU member states in their official languages

See [LICENCE](./LICENCE) for the full text.

---

## Not a Medical Device

CAIRN is a mathematical research tool. It is **not** a medical device under:

- EU MDR 2017/745 (Medical Device Regulation)
- EU IVDR 2017/746 (In Vitro Diagnostic Regulation)
- MPDG — Medizinprodukterecht-Durchführungsgesetz (Deutschland)

See [NOTICE](./NOTICE) for the complete disclaimer.

---

## Contributing

Contributions are welcome under EUPL-1.2.
By contributing, you agree your changes will be returned to the reference system.

- Issues: https://github.com/fmatten/CAIRN/issues
- Mirror: https://codeberg.org/iscad/cairn
- Guide: [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## Citation

```bibtex
@software{cairn2026,
  title   = {CAIRN — Clinical interoperability reference architecture},
  author  = {Matten, Friedhelm},
  year    = {2026},
  doi     = {10.5281/zenodo.20375036},
  url     = {https://github.com/fmatten/CAIRN},
  licence = {EUPL-1.2},
  version = {1.0.1}
}
```
