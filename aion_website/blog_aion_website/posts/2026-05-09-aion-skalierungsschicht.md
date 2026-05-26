---
title: "AION-Skalierungsschicht: Wenn formale Abfragen auf Millionen Ereignisse treffen"
date: 2026-05-09
category: science
lang: de
author: Friedhelm Matten
excerpt: "Das Begleitpapier zur AION-Skalierungsschicht beschreibt, wie die formale AION-Abfragesprache auch auf großen klinischen Datensätzen praktikabel bleibt — durch approximative Algorithmen mit beweisbaren Genauigkeitsschranken."
tags:
  - aion
  - wissenschaft
  - skalierung
  - algorithmen
  - differential-privacy
---

## Hintergrund

AION v1.0 (FM-3) definiert ein vollständig allgemeines formal-mathematisches Modell für klinische Informationssysteme. Die zugehörige Abfragesprache ist ausdrucksstark — aber einige Fragmente sind für große Datensätze rechenintensiv.

Im Begleitpapier [*AION-Skalierungsschicht*](https://zenodo.org/records/20095470) (Zenodo, Mai 2026) beschreiben wir eine Sammlung approximativer und verteilter Auswertungsverfahren, die diese Lücke schließen.

## Das Komplexitätsproblem

Die folgende Tabelle aus AION v1.0 §13 zeigt, welche Abfragefragmente problematisch werden:

| Fragment | Datenkomplexität | Klasse |
|---|---|---|
| Einfache Kohorten | O(\|P\| · n_max) | P |
| RTP-Muster | O(\|P\| · n_max) | P |
| TCFG-Parsing | O(\|P\| · n³_max) | P |
| Backdoor-Adjustierung | O(∏\|V_z\|) in \|Z\| | PSPACE |
| Kontaktkohorten (naiv) | O(\|P\|²· d) | P |

Für Datensätze mit 10.000+ Patienten und Millionen von Ereignissen sind die kubischen und quadratischen Schranken prohibitiv.

## Die Lösung: Approximation mit Garantien

Der entscheidende Punkt: Wir approximieren **nicht unkontrolliert**, sondern mit formal bewiesenen Genauigkeitsschranken (ε, δ).

### Streaming-NFA für reguläre temporale Muster

Statt die gesamte Ereignissequenz im Speicher zu halten, verwenden wir Aho-Corasick-Automaten:

```python
from aion_clinical.scaling import StreamingNFAMatcher

pattern = "(τ_lab, q=lactate, val>4.0) << (τ_lab, q=lactate, val<=2.0)"
matcher = StreamingNFAMatcher(pattern)

for event in patient_stream:
    if matcher.feed(event):
        print(f"Muster gefunden: Patient {event.patient_id}")
```

**Komplexität:** O(n_k) Zeit, O(|π| · |T|) Speicher — **unabhängig** von der Sequenzlänge.

### Count-Min-Sketch für Musterhäufigkeiten

Für die Schätzung von Musterhäufigkeiten über große Kohorten verwenden wir Count-Min-Sketches:

```python
from aion_clinical.scaling import CMSketchCounter

# ε = 0.001 Genauigkeit, δ = 0.01 Fehlerwahrscheinlichkeit
counter = CMSketchCounter(epsilon=0.001, delta=0.01)

for patient in cohort:
    for match in matcher.match_all(patient.events):
        counter.add(match.pattern_id)

# Schätzung mit Garantie: Fehler ≤ ε · ||f||_1 mit Wahrscheinlichkeit ≥ 1-δ
freq = counter.estimate("pattern_lactate_recovery")
```

**Speicher:** O((1/ε) · log(1/δ)) — logarithmisch statt linear in |Π|.

### R-Tree-Indexierung für Kontaktkohorten

Die naive O(|P|²)-Berechnung der Kontaktrelation wird durch räumlich-zeitliche Indexierung auf O(|A| log |A|) reduziert:

```python
from aion_clinical.scaling import ContactIndex

index = ContactIndex(stays)
index.build()  # O(|A| log |A|)

# Kontakte für Station ICU
contacts = index.query(unit="ICU", interval=(t_start, t_end))
```

Für ein Krankenhaus mit 50.000 stationären Patienten pro Jahr läuft die Berechnung unter einer Sekunde.

## Föderierte Auswertung und Differential Privacy

Ein besonderes Merkmal der Skalierungsschicht: Alle approximativen Verfahren sind **konsistent mit den Differential-Privacy-Garantien** aus AION v1.0 §20.

```python
from aion_clinical.federated import FederatedCohortQuery

query = FederatedCohortQuery(
    formula=phi_sepsis,
    epsilon=0.5,      # Privacy-Budget pro Institution
    mechanism="laplace"
)

# Lokale Auswertung auf Institution Ik — keine Rohdaten verlassen das Haus
local_result = query.evaluate_local(local_store)
# Aggregation erfolgt nur über verrauschte Zählungen
global_estimate = query.aggregate([r1, r2, r3])
```

**Satz (Föderierte DP-Komposition):** Bei disjunkter Patientenpartitionierung addiert sich das Privacy-Budget *nicht* — jede Institution bleibt bei ihrem lokalen ε.

## Empfehlungen für die Praxis

| Anwendungsfall | Empfohlenes Verfahren |
|---|---|
| Echtzeit-Monitoring (ICU) | Streaming-NFA |
| Kohorten-Studien | Exact + CMSketch für Häufigkeiten |
| Nosokomiale Infektionen | R-Tree-Kontaktindex |
| Föderierte Forschung | Föderierte Auswertung + Laplace-Mechanismus |
| Kausalstrukturlernen | NOTEARS + Bootstrap (B=184 reicht für ±0.1) |

## Publikation

Das vollständige Begleitpapier ist auf Zenodo verfügbar:

> Friedhelm Matten (2026). *AION-Skalierungsschicht: Approximative und verteilte Auswertung der AION-Abfragesprache.* ISCaD GmbH. [zenodo.org/records/20095470](https://zenodo.org/records/20095470)

Die beschriebenen Verfahren sind in `aion-clinical >= 2.0.1` implementiert und über das `aion_clinical.scaling`-Modul zugänglich.
