---
title: "FM-4 & aion-clinical 2.0.4 — AGPL-3.0 Dual-Lizenz"
date: 2026-05-26
category: release
lang: de
author: Friedhelm Matten
excerpt: "FM-4 (Signal-Loss Inspection at Data-boundaries) formalisiert Informationsverluste bei klinischen Cross-System-Übertragungen als Detektorklasse. aion-clinical 2.0.4 wechselt auf AGPL-3.0-only OR Commercial — Dual-Lizenzmodell ab sofort aktiv."
tags:
  - release
  - fm4
  - sild
  - agpl
  - lizenz
  - zenodo
  - aion-clinical
---

## FM-4: Signal-Loss Inspection at Data-boundaries

Mit **FM-4** (*Signal-Loss Inspection at Data-boundaries*) legt ISCaD GmbH das vierte formale Modell der AION-Familie vor. FM-4 formalisiert, was passiert, wenn klinische Daten zwischen Systemen übertragen werden.

- **DOI:** [10.5281/zenodo.20391260](https://doi.org/10.5281/zenodo.20391260)
- **Version:** 2 (26. Mai 2026)
- **Lizenz:** AGPL-3.0-only OR Commercial (ISCaD GmbH)

### Die vier kanonischen Verlustmuster

| Kürzel | FM-4 Def. | Verlusttyp | Typisches Beispiel |
|--------|-----------|------------|-------------------|
| `TN` | 2.1 | Type Narrowing | FHIR `Quantity` → HL7 `NM`: Einheit geht verloren |
| `TC` | 2.2 | Temporal Collapse | Fuzzy-Zeitintervall → Punktzeitstempel |
| `AD` | 2.3 | Attribute Dropping | Optionale FHIR-Extensions werden ignoriert |
| `RS` | 2.4 | Reference Severing | Encounter-Referenz geht beim CDR-Import verloren |

Der **Vollständigkeitssatz (FM-4 Satz 2.5)** beweist: Jede verlustbehaftete Übertragung ist als Komposition dieser vier Muster darstellbar.

### SILD — die Referenzimplementierung

```python
from aion_clinical.sild import SILDDetector

detector = SILDDetector(mode="hl7v2")
report = detector.inspect(hl7_message)

for loss in report.losses:
    print(f"{loss.pattern.name}: {loss.field} → {loss.description}")
```

---

## aion-clinical 2.0.4 — Dual-Lizenz

Ab v2.0.3 (25. Mai 2026) gilt: **AGPL-3.0-only OR Commercial**.

| Lizenzform | Für wen? | Bedingung |
|-----------|---------|----------|
| **AGPL-3.0-only** | Open-Source, Forschung, interne Nutzung | Netzwerkdienste müssen Open Source sein |
| **Commercial** | Krankenhäuser, Health-IT-Anbieter | Keine Offenlegungspflicht — [licensing@iscad-it.de](mailto:licensing@iscad-it.de) |

Upgrade (vollständig rückwärtskompatibel):

```bash
pip install --upgrade aion-clinical==2.0.4
```

---

## Zusammenfassung

- FM-4 Paper v2 auf Zenodo: [doi.org/10.5281/zenodo.20391260](https://doi.org/10.5281/zenodo.20391260)
- Lizenzwechsel: EUPL-1.2 → AGPL-3.0-only OR Commercial
- Version 2.0.4 auf PyPI — rückwärtskompatibel zu 2.0.1
- Neue SPDX-Header in allen 116 Python-Quelldateien

Fragen: [info@iscad-it.de](mailto:info@iscad-it.de)
