---
title: "aion-clinical 2.0.1 — Release Notes"
date: 2026-05-12
category: release
lang: de
author: Friedhelm Matten
excerpt: "Version 2.0.1 des Python-Pakets aion-clinical ist auf PyPI verfügbar. Diese Version bringt eine vollständige Überarbeitung der Authentifizierungsschicht, verbessertes FHIR-Mapping und den neuen kausalen Query-Executor."
tags:
  - release
  - pypi
  - aion-clinical
  - cairn
  - fhir
---

## Überblick

Mit `aion-clinical 2.0.1` veröffentlichen wir das erste stabile Release der 2.x-Serie. Diese Version markiert den Übergang von der Pilot-Plattform zur produktionsbereiten klinischen Infrastruktur.

Das Paket ist ab sofort auf PyPI verfügbar:

```bash
pip install aion-clinical==2.0.1
```

oder über Codeberg:

```bash
pip install git+https://codeberg.org/fm2-project/cairn.git@v2.0.1
```

---

## Neuerungen in 2.0.1

### Überarbeitete Authentifizierungsschicht

Das pluggable Auth-Backend wurde vollständig neu geschrieben. Unterstützte Backends:

| Backend | Status | Beschreibung |
|---------|--------|--------------|
| `none`   | ✓ Stabil | Kein Auth — nur für lokale Entwicklung |
| `apikey` | ✓ Stabil | API-Keys mit Rollen und Ablaufdatum |
| `ldap`   | ✓ Stabil | LDAP/Active Directory — gegen echte AD-Instanzen getestet |
| `oidc`   | ✓ Stabil | OpenID Connect — gegen Keycloak und Azure AD getestet |

Konfiguration via YAML:

```yaml
auth:
  backend: ldap
  ldap:
    server: ldaps://ad.klinik-example.de
    base_dn: DC=klinik,DC=example,DC=de
    bind_dn: CN=aion-service,OU=Service,DC=klinik,DC=example,DC=de
    bind_password: ${LDAP_BIND_PASSWORD}
    user_filter: "(sAMAccountName={username})"
    role_attribute: memberOf
```

### Verbessertes FHIR R4 Mapping

Das bidirektionale AION↔FHIR R4 Mapping wurde in zwei Bereichen erweitert:

- **Encounter.location** wird jetzt korrekt auf die AION-Einheitszuordnung (`unit`) abgebildet
- **MedicationAdministration** unterstützt jetzt das vollständige AION-Ereignismodell inkl. `causal_relation`-Feld

```python
from aion_clinical import FHIRMapper

mapper = FHIRMapper(version="R4")
aion_event = mapper.from_fhir(fhir_observation)
fhir_bundle = mapper.to_fhir(aion_cohort)
```

### Kausaler Query-Executor

Der neue `CausalQueryExecutor` ermöglicht die direkte Ausführung von do-Operator-Abfragen auf dem klinischen Datenmodell:

```python
from aion_clinical import ClinicalDataStore, CausalQueryExecutor

store = ClinicalDataStore.from_fhir_bundle("icu_cohort.json")
executor = CausalQueryExecutor(store, causal_graph="icu_graph.yaml")

# do-Operator: Was wäre der Laktatspiegel, wenn Antibiotikum 2h früher?
result = executor.do(
    intervention={"type": "medication", "substance": "Cefuroxim", "delta_t": -7200},
    outcome="lactate",
    cohort_filter={"unit": "ICU", "stay_days_min": 3}
)
print(result.summary())
```

---

## Behobene Fehler

- **#247** — `TemporalAlgebra.allen_relation()` lieferte falsches Ergebnis für `finishes` bei Punktereignissen (tB == tE)
- **#251** — MLLP-Listener verlor Verbindung nach 300s Inaktivität (Keepalive-Timer ergänzt)
- **#258** — `FuzzyInterval` mit ε=0 verhielt sich nicht identisch zum exakten Intervall
- **#263** — SQLite-Migration schlug fehl bei Schemas mit benutzerdefinierten Ereignistypen

---

## Breaking Changes

!!! warning "Breaking Change: Auth-Konfiguration"
    Das Format der Auth-Konfiguration in `aion.yaml` hat sich geändert. Das alte Format `auth_backend: apikey` muss auf `auth.backend: apikey` umgestellt werden. Ein Migrationsskript ist verfügbar:

    ```bash
    python -m aion_clinical.migrate --config aion.yaml
    ```

---

## Migration von 1.10.x

```bash
# 1. Paket aktualisieren
pip install --upgrade aion-clinical==2.0.1

# 2. Konfiguration migrieren
python -m aion_clinical.migrate --config aion.yaml

# 3. Datenbank-Migrationen ausführen
aion db migrate

# 4. Auth-Layer testen
aion auth verify --backend ldap
```

---

## Verfügbarkeit

- **PyPI:** [pypi.org/project/aion-clinical/2.0.1](https://pypi.org/project/aion-clinical/2.0.1/)
- **Codeberg:** [codeberg.org/fm2-project/cairn](https://codeberg.org/fm2-project/cairn)
- **Zenodo:** DOI [10.5281/zenodo.19553130](https://zenodo.org/records/19553130)

Bei Fragen und Fehlerberichten: [info@iscad-it.de](mailto:info@iscad-it.de)
