---
title: "CAIRN & FHIR R4: Von der Observation zum AION-Ereignis in 10 Minuten"
date: 2026-04-20
category: tutorial
lang: de
author: Friedhelm Matten
excerpt: "Schritt-für-Schritt-Tutorial: Wie Sie FHIR R4 Observations in das formale AION-Ereignismodell überführen, temporale Abfragen ausführen und Ergebnisse zurück nach FHIR exportieren."
tags:
  - tutorial
  - cairn
  - fhir
  - python
  - hl7
---

## Voraussetzungen

Für dieses Tutorial benötigen Sie:

- Python 3.11+
- `aion-clinical >= 2.0.1`
- Ein FHIR R4-Server oder eine FHIR-Bundle-Datei (wir verwenden [Synthea](https://synthea.mitre.org/)-Testdaten)

Installation:

```bash
pip install aion-clinical==2.0.1 requests
```

---

## Schritt 1: FHIR-Bundle laden

CAIRN unterstützt FHIR-Bundles direkt als JSON-Datei oder via REST-API:

```python
from aion_clinical import ClinicalDataStore

# Aus lokaler FHIR-Bundle-Datei
store = ClinicalDataStore.from_fhir_bundle("synthea_100_patients.json")

# Oder direkt vom FHIR-Server
store = ClinicalDataStore.from_fhir_server(
    base_url="https://hapi.fhir.org/baseR4",
    patient_ids=["patient-001", "patient-002"]
)

print(f"Geladen: {store.n_patients} Patienten, {store.n_events} Ereignisse")
# → Geladen: 100 Patienten, 47.832 Ereignisse
```

## Schritt 2: FHIR Observation → AION Ereignis

Das bidirektionale Mapping übernimmt CAIRN automatisch. Schauen wir uns an, was passiert:

```python
from aion_clinical import FHIRMapper

mapper = FHIRMapper(version="R4")

# FHIR Observation (vereinfacht)
fhir_obs = {
    "resourceType": "Observation",
    "id": "obs-lactate-001",
    "status": "final",
    "code": {"coding": [{"system": "http://loinc.org", "code": "2524-7"}]},
    "subject": {"reference": "Patient/patient-001"},
    "effectiveDateTime": "2026-04-15T14:23:00+02:00",
    "valueQuantity": {"value": 3.8, "unit": "mmol/L"}
}

# → AION-Ereignis
aion_event = mapper.from_fhir(fhir_obs)
print(aion_event)
# ClinicalEvent(
#   type=τ_lab, q_code='lactate', value=3.8, unit='mmol/L',
#   t_begin=2026-04-15T12:23:00Z, t_end=2026-04-15T12:23:00Z,
#   patient='patient-001', confidence=1.0
# )
```

Die LOINC-Code-Zuordnung (`2524-7` → `lactate`) erfolgt über die mitgelieferte Terminologie-Bibliothek.

## Schritt 3: Temporale Abfrage mit Allen-Relationen

Jetzt wird es interessant. Wir suchen alle Patienten, bei denen ein Laktatwert > 4.0 mmol/L **vor** einem Laktatwert ≤ 2.0 mmol/L aufgetreten ist (klassisches Laktat-Clearance-Muster):

```python
from aion_clinical.query import EventQuery, AllenRelation

# Abfrage formulieren
query = EventQuery(store)

cohort = query.filter(
    lambda p: query.exists_sequence(
        p,
        event1={"type": "τ_lab", "q_code": "lactate", "value_gt": 4.0},
        relation=AllenRelation.BEFORE,
        event2={"type": "τ_lab", "q_code": "lactate", "value_lte": 2.0},
        max_gap_hours=24  # innerhalb von 24 Stunden
    )
)

print(f"Kohorte: {len(cohort)} Patienten zeigen Laktat-Clearance-Muster")
# → Kohorte: 23 Patienten zeigen Laktat-Clearance-Muster
```

Dieselbe Abfrage mit unscharfen Zeitintervallen (Fuzzy-Logik, für unvollständig dokumentierte Zeiten):

```python
cohort_fuzzy = query.filter(
    lambda p: query.exists_sequence(
        p,
        event1={"type": "τ_lab", "q_code": "lactate", "value_gt": 4.0},
        relation=AllenRelation.BEFORE,
        event2={"type": "τ_lab", "q_code": "lactate", "value_lte": 2.0},
        max_gap_hours=24,
        confidence_threshold=0.85  # probabilistisches Allen-Prädikat
    )
)
```

## Schritt 4: Kausale Analyse

Wir möchten wissen, ob frühe Antibiotikagabe kausal für das Laktat-Clearance-Muster ist:

```python
from aion_clinical.causal import BackdoorAdjustment

# Backdoor-Kriterium: Adjustierung über Diagnose und APACHE-Score
adjustment = BackdoorAdjustment(
    store=store,
    treatment="early_antibiotic",   # τ_med: Antibiotikum < 6h nach Aufnahme
    outcome="lactate_clearance",    # unser Kohorten-Prädikat
    adjustment_set=["diagnosis", "apache_score"],
    method="IPW"   # Inverse Probability Weighting
)

result = adjustment.estimate()
print(result)
# CausalEffect(
#   ATE=0.18, CI_95=(0.09, 0.27), p=0.001,
#   interpretation="Frühe Antibiotikagabe erhöht Laktat-Clearance-Wahrscheinlichkeit um 18%"
# )
```

## Schritt 5: Ergebnis zurück nach FHIR exportieren

Die Kohorte und die kausalen Ergebnisse können als FHIR-Bundle exportiert werden:

```python
# Kohorte als FHIR Group exportieren
fhir_group = mapper.cohort_to_fhir_group(cohort, name="Laktat-Clearance-Kohorte")

# Kausalanalyse als FHIR ResearchDefinition
fhir_research = mapper.causal_result_to_fhir(result)

# Als Bundle speichern
mapper.export_bundle(
    [fhir_group, fhir_research],
    output_path="lactate_clearance_analysis.json"
)
```

---

## Zusammenfassung

In 10 Minuten haben wir:

1. Ein FHIR R4-Bundle in das AION-Datenmodell geladen
2. Eine temporale Kohortendefinition mit Allen-Relationen formuliert
3. Eine kausale Wirksamkeitsschätzung berechnet (Backdoor-Adjustierung)
4. Ergebnisse zurück nach FHIR exportiert

Der vollständige Code dieses Tutorials ist auf Codeberg verfügbar:  
[codeberg.org/fm2-project/cairn/examples/fhir-tutorial](https://codeberg.org/fm2-project/cairn)

## Weiterführendes

- [AION v1.0 — Formales Modell (Zenodo)](https://zenodo.org/records/19553130)
- [CAIRN — Technische Dokumentation (Zenodo)](https://zenodo.org/records/19483182)
- [aion-clinical auf PyPI](https://pypi.org/project/aion-clinical/)

Bei Fragen: [info@iscad-it.de](mailto:info@iscad-it.de)
