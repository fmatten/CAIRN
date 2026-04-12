# CAIRN

**Clinical Interoperability Reference Architecture**

Built on [FM-2](https://codeberg.org/fm2-project/cairn) — a formal mathematical
model for clinical information systems.

[![Woodpecker CI](https://ci.codeberg.org/api/badges/fm2-project/cairn/status.svg)](https://ci.codeberg.org/fm2-project/cairn)
[![License: EUPL-1.2](https://img.shields.io/badge/License-EUPL--1.2-blue.svg)](https://eupl.eu/1.2/en/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![NOT a medical device](https://img.shields.io/badge/NOT%20a%20medical%20device-EU%20MDR%202017%2F745-red)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32017R0745)

---

## What is CAIRN?

When a laboratory result moves from a clinical information system into a FHIR
server, something can get lost. Not always. But systematically — and silently.

CAIRN detects this. It implements the **FM-2 formal event model** as executable
Python, provides adapters for FHIR R4 and HL7 v2, and includes **SILD** — a
Semantic Information Loss Detector that tracks what happens to clinical
information as it crosses system boundaries.

CAIRN is **not** a clinical application. It is the formal foundation on which
interoperable clinical applications can be built and verified.

---

## Core Concepts

### The FM-2 Event Model

Every clinical fact in CAIRN is a typed, time-stamped event — a 6-tuple:

```
e = (patient, stay, type, [t_begin, t_end], attributes, references)
```

Types form a hierarchy (`tau_lab → tau_obs → top`). Temporal relations between
events are expressed using all 13 Allen algebra relations.

### SILD — Semantic Information Loss Detector

SILD classifies what is lost when a clinical event crosses a system boundary:

| Loss Pattern | Description |
|---|---|
| Type narrowing | `tau_lab` → `tau_obs` (subtype information lost) |
| Temporal collapse | Interval `[t_B, t_E]` → single timestamp |
| Attribute dropping | Required attribute missing in target schema |
| Reference severing | `partOf` link to parent process removed |

### Allen Algebra

All 13 temporal interval relations are implemented as first-class predicates:

```
precedes · meets · overlaps · finished-by · contains · starts
equals · started-by · during · finishes · overlapped-by · met-by · preceded-by
```

---

## Installation

```bash
# From Codeberg
git clone https://codeberg.org/fm2-project/cairn.git
cd cairn
pip install -e ".[dev]"

# From PyPI (v1.1.0+)
pip install cairn
```

**Requirements:** Python 3.11+, z3-solver, fhir.resources, hl7

---

## Quick Start

### 1 — Define a clinical event

```python
from cairn.event import ClinicalEvent, EventType

# A laboratory observation: Lactate 2.1 mmol/l at day 15.3
e_lab = ClinicalEvent(
    pid=1,
    aid=1,
    event_type=EventType("tau_lab"),
    t_begin=15.3,
    t_end=15.3,
    attributes={"q_code": "lactate", "value": 2.1, "unit": "mmol/l"},
)
```

### 2 — Check Allen relations between events

```python
from cairn.allen import allen_relation, AllenRelation

# An HLM process: [15.2, 15.9]
e_hlm = ClinicalEvent(pid=1, aid=1, event_type=EventType("tau_hlm"),
                      t_begin=15.2, t_end=15.9, attributes={})

# Is the lab measurement during the HLM process?
rel = allen_relation(e_lab, e_hlm)
assert rel == AllenRelation.DURING   # [15.3, 15.3] d [15.2, 15.9]
```

### 3 — Load a FHIR Observation and detect information loss

```python
from cairn.fhir_r4 import FhirR4Adapter
from cairn.sild import SILDDetector

adapter = FhirR4Adapter()
sild    = SILDDetector()

# Load a FHIR Observation resource
fhir_obs = adapter.load_file("observation_lactate.json")

# Map to internal event model
event, losses = adapter.to_event(fhir_obs)

# Inspect what was lost
for loss in losses:
    print(f"[{loss.pattern}] {loss.description}")
# → [TEMPORAL_COLLAPSE] effectiveDateTime mapped to point interval
# → [REFERENCE_SEVERED] partOf not present in source resource
```

### 4 — Run a cohort query

```python
from cairn.cohort import CohortQuery

# phi_FM1: patients with arrhythmia diagnosis followed by ablation
# within 30 days (FM-2 Section 23, Example query)
query = CohortQuery.from_formula(
    diagnosis_code="d_Arr",
    procedure_code="o_ABL",
    max_days=30,
)

cohort = query.execute(event_store)
print(f"Cohort size: {len(cohort)}")
```

### 5 — Verify formal properties with Z3

```python
from cairn.homomorphism import FhirHomomorphismVerifier

verifier = FhirHomomorphismVerifier()

# Verify that the FHIR mapping preserves type hierarchy
result = verifier.verify_type_hierarchy_preservation()
print(result.is_sat)   # True if mapping is formally correct
```

---

## Adapters

| Adapter | Module | Supported formats |
|---|---|---|
| FHIR R4 | `cairn.fhir_r4` | Observation, Procedure, Condition, MedicationAdministration, Bundle |
| HL7 v2 | `cairn.hl7v2` | ORU^R01, ADT^A01, RXA |
| CSV / DataFrame | `cairn.csv_df` | pandas DataFrame, CSV files |

---

## SILD — Loss Pattern Classification

```python
from cairn.sild import SILDDetector, LossPattern

detector = SILDDetector()

# Analyse a full HL7 v2 → FHIR R4 conversion
report = detector.analyse_conversion(
    source_msg=hl7_message,
    target_resource=fhir_resource,
)

print(report.summary())
# Total events analysed: 147
# Events with loss:       23  (15.6%)
# Loss patterns:
#   TYPE_NARROWING:     11
#   TEMPORAL_COLLAPSE:   8
#   ATTRIBUTE_DROPPING:  3
#   REFERENCE_SEVERED:   1
```

---

## CLI

```bash
# Analyse a FHIR Bundle for information loss
cairn sild analyse --input bundle.json --format fhir-r4

# Run cohort query from formula file
cairn cohort query --formula phi_FM1.yaml --store events.db

# Verify FHIR mapping homomorphism properties
cairn verify homomorphism --adapter fhir_r4

# Show version
cairn version
```

---

## Project Structure

```
cairn/
├── allen.py          # All 13 Allen temporal relations
├── event.py          # Universal 6-tuple event model (FM-2 Section 4)
├── cohort.py         # Cohort query engine (FM-2 Section 10)
├── fhir_r4.py        # FHIR R4 adapter + SILD integration
├── hl7v2.py          # HL7 v2 adapter (ORU/ADT/RXA)
├── csv_df.py         # CSV / DataFrame adapter
├── homomorphism.py   # Z3-based formal verification (FM-2 Section 17)
├── sild.py           # Semantic Information Loss Detector
├── commands.py       # Click CLI
└── app.py            # FastAPI REST API
```

---

## Formal Foundation

CAIRN implements the mathematical structures from FM-2:

| FM-2 Concept | CAIRN Module |
|---|---|
| Type hierarchy $H_\mathcal{T}$ | `event.EventType`, `event.TypeDAG` |
| Universal event 6-tuple | `event.ClinicalEvent` |
| All 13 Allen relations | `allen.allen_relation` |
| Fuzzy time intervals (Section 5) | `allen.FuzzyInterval` |
| Cohort query language (Section 10) | `cohort.CohortQuery` |
| FHIR homomorphism (Section 17) | `homomorphism.FhirHomomorphismVerifier` |
| Validation operator $\Pi_l$ | `event.validate` |
| Confidence-weighted events | `event.ClinicalEvent.confidence` |

---

## Tests

```bash
# All tests
pytest tests/ -v

# By category
pytest tests/unit/        # Unit tests
pytest tests/integration/ # Integration tests
pytest tests/property/    # Property-based tests (Hypothesis)

# With coverage
pytest tests/ --cov=cairn --cov-report=term-missing
```

40 tests pass across Python 3.11 and 3.12.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Pull Request Template](.gitea/PULL_REQUEST_TEMPLATE.md).

All contributions must:
- Pass `ruff check` and `mypy cairn`
- Include tests (unit + property-based where applicable)
- Preserve FM-2 invariants (Allen mutual exclusivity, type DAG consistency)
- Be licensed under EUPL-1.2

---

## Licence

CAIRN is licensed under the
[European Union Public Licence 1.2 (EUPL-1.2)](https://eupl.eu/1.2/en/).

This is a **copyleft** licence compatible with GPL v2/v3, AGPL, MPL and others.
Modifications must be returned to the community under the same licence.

---

## ⚠️ Scope

**CAIRN is NOT a medical device** within the meaning of EU MDR 2017/745 / MPDG.

It is a software library for formal modelling, verification and analysis of
clinical information structures. It does not make clinical decisions, does not
interact with patients, and is not intended for direct clinical use.

---

## About

CAIRN is developed by [ISCaD GmbH](https://www.iscad.de) as part of the FM
(Formal Models for Clinical Information Systems) project series:

- **FM-1** — Formal model for cardiac surgery data (2020)
- **FM-2** — General clinical information model (formal foundation for CAIRN)
- **FM-3** — Implementation reference architecture (in preparation)

Contact: Friedhelm Matten · ISCaD GmbH · Braunschweig