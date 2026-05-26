---
title: "demo.aion-clinical.de — Die AION-Plattform zum Ausprobieren"
date: 2026-05-25
category: clinical
lang: de
author: Friedhelm Matten
excerpt: "Vier interaktive Demonstrationen zeigen, was AION in der klinischen Praxis leistet: Sepsis-Früherkennung auf der Intensivstation, kausale Analyse eines postoperativen Verlaufs, föderierte Multicenter-Auswertung mit Differential Privacy — und ein DAG-Editor für klinische Workflows."
tags:
  - demo
  - aion-clinical
  - klinische-simulation
  - kausalanalyse
  - differential-privacy
  - fhir
---

Unter **[demo.aion-clinical.de](https://demo.aion-clinical.de)** ist die interaktive Demonstrationsplattform von AION Clinical zugänglich. Alle Szenarien arbeiten mit fiktiven, klinisch plausibel konstruierten Daten — sie geben aber einen authentischen Eindruck davon, wie AION formale Modelltheorie in konkrete klinische Entscheidungsunterstützung übersetzt.

Die Plattform besteht aus vier Modulen.

---

## Simulation I — Ein postoperativer Fall in sieben Akten

*Wenn die Daten sprechen könnten — was würden sie sagen?*

Ausgangssituation: ein 71-jähriger Patient nach aortokoronarer Bypass-Operation (CABG). In den Stunden nach dem Eingriff entwickelt sich eine akute Nierenschädigung (AKI). Die Simulation führt durch sieben Akte:

1. **Ereignistypisierung** — Rohdaten (Vitalzeichen, Laborwerte, Medikamente) werden in das formale AION-Ereignismodell überführt. Jedes Ereignis erhält einen Typ (`τ_lab`, `τ_med`, `τ_vital`), ein Fuzzy-Zeitintervall und einen Konfidenzwert.

2. **Temporale Struktur** — Die Allen-Algebra ordnet Ereignisse: Welche Ereignisse fallen zusammen, welche gehen voran, welche überlappen? Aus Rohdaten wird eine geordnete Ereignischronologie.

3. **Mustersuche** — Das AION-Abfragesystem sucht nach RTP-Mustern (Regular Temporal Patterns): z. B. `Kreatinin-Anstieg > 0,3 mg/dl` *followed-by* `Oligurie < 0,5 ml/kg/h` innerhalb von 6 Stunden — das AKI-Frühwarnsignal nach KDIGO-Leitlinie.

4. **Korrelation vs. Kausalität** — War der ACE-Hemmer ursächlich? Der do-Kalkül nach Pearl ermöglicht kontrafaktische Fragen: *P(AKI | do(kein ACE-Hemmer))*. Das Ergebnis quantifiziert, ob die Medikation kausal oder nur korreliert war.

5. **Kontrafaktische Intervention** — Was wäre passiert, wenn die Flüssigkeitsgabe 2 Stunden früher begonnen hätte? Der AION-Simulator berechnet die kontrafaktische Trajektorie unter Berücksichtigung der Backdoor-Adjustierung (§ 22.3 AION v1.0).

6. **Erklärbarkeit (Shapley-Attribution)** — Welche Ereignisse trugen wie viel zur Risikoschätzung bei? Die Shapley-Werte (§ 22.4 AION v1.0) weisen jedem Ereignis einen quantifizierten Beitrag zur Vorhersage zu.

7. **Systemarchitektur** — Abschließend zeigt die Simulation, welche der sechs AION-Schichten (Typisierung, Temporal, Kohorte, Kausal, Erklärbarkeit, Interoperabilität) in diesem Fall zusammenspielen.

→ [Simulation I starten](https://demo.aion-clinical.de/simulation-i/)

---

## Simulation II — Sepsis auf der Allgemeinstation

*Auf einer Station mit zwölf Patienten — welche zwei brauchen jetzt Aufmerksamkeit?*

Es ist Donnerstag, 22:00 Uhr, Internistische Allgemeinstation. Zwölf Patienten, drei Pflegekräfte, keine Anwesenheit eines Arztes. Welcher Patient verschlechtert sich gerade?

AION wertet kontinuierlich aus, ob die Sepsis-3-Definition zutrifft: SOFA-Score-Anstieg ≥ 2 Punkte, kombiniert mit Infektionsverdacht. Die Demonstration zeigt:

### Temporale Mustererkennung mit dem NFA-Operator

Das Sepsis-Muster lässt sich als nichtdeterministischer Automat (NFA) formulieren:

```
(Fieber > 38°C ODER Hypothermie < 36°C)
  BEFORE  (Atemfrequenz > 22/min WITH_OVERLAP Laktat > 2 mmol/l)
  BEFORE  (SOFA-Anstieg ≥ 2 Punkte)
```

AION evaluiert dieses Muster in **O(|π| · n_k)** — unabhängig von der Gesamtlänge der Ereignissequenz. Für 12 Patienten mit je einigen Hundert täglichen Messwerten bedeutet das: Neubewertung in Echtzeit bei jeder eingehenden Vitalwertmessung.

### SEP-1 Bundle-Compliance

Parallel zur Früherkennung prüft AION die Einhaltung des SEP-1-Maßnahmen-Bündels: Blutkulturen vor Antibiotikagabe, Antibiotikum innerhalb einer Stunde, Laktat-Kontrolle. Abweichungen werden zeitlich präzise dokumentiert — für Qualitätssicherung und Haftungsklarheit.

### Trajektorienvorhersage

Für den wahrscheinlichsten Patienten berechnet AION eine 6-Stunden-Laktat-Trajektorie mit Konfidenzintervall. Die Vorhersage basiert auf dem formalen Verlaufsmodell — nicht auf Black-Box-Regression.

→ [Simulation II starten](https://demo.aion-clinical.de/simulation-ii/)

---

## Simulation III — Multicenter-Studie mit Differential Privacy

*Drei Kliniken, eine Forschungsfrage, keine Datenkopie.*

Ausgangslage: Idiopathische Pulmonale Fibrose (IPF), eine seltene Erkrankung. Klinik A, B und C haben jeweils 80–120 Patientenfälle — zu wenige für statistisch robuste Aussagen. Die naheliegende Lösung — Daten zentralisieren — scheitert an DSGVO, Krankenhausverträgen und berechtigten Datenschutzinteressen.

AION löst dies durch **föderierte Auswertung mit formalen Datenschutzgarantien**:

### Disjunkte Patientenpartition

Jede Klinik wertet lokal aus. Kein Rohdatum verlässt das Haus. Ausgetauscht werden ausschließlich verrauschte Zählungen.

### Laplace-Mechanismus und ε-Differential Privacy

Der Laplace-Mechanismus fügt gezieltes Rauschen hinzu:

```
M(D) = f(D) + Laplace(Δf / ε)
```

`ε` ist das Privacy-Budget — ein formaler, quantifizierter Datenschutzparameter. Die Demonstration zeigt interaktiv, wie sich `ε` auf Genauigkeit und Datenschutz auswirkt.

### Das Kompositions-Theorem

Entscheidend: Bei disjunkter Patientenpartitionierung *addiert* sich das Privacy-Budget nicht. Jede Institution bleibt bei ihrem lokalen `ε`. Das ist kein Versprechen, sondern ein mathematisch bewiesener Satz (§ 20.3 AION v1.0).

Die Simulation lässt `ε` per Schieberegler einstellen und zeigt live, wie sich Schätzgenauigkeit und Datenschutzgarantie gegenüberstehen — eine Grundlage für informierte Studiendesign-Entscheidungen.

→ [Simulation III starten](https://demo.aion-clinical.de/simulation-iii/)

---

## AION DAG-Editor — Klinische Workflows modellieren

Der DAG-Editor ist ein browserbasierter Graph-Editor für klinische Behandlungspfade. Workflows werden als gerichtete azyklische Graphen (DAGs) modelliert: Diagnose → Intervention → Bewertung → Entlassung.

Knoten-Typen:

| Typ | Bedeutung |
|---|---|
| `τ_diag` | Diagnose-Ereignis |
| `τ_med` | Medikamentengabe |
| `τ_proc` | Prozedur / Eingriff |
| `τ_obs` | Beobachtung / Messung |
| `τ_dec` | Entscheidungsknoten |

Der Editor exportiert den modellierten Workflow als strukturiertes JSON — kompatibel mit der AION-Backend-API. In der Demo ist die API-Anbindung aktiviert und simuliert einen Roundtrip gegen das AION-Production-Backend.

→ [DAG-Editor öffnen](https://demo.aion-clinical.de/)

---

## Technischer Hintergrund

Alle vier Demonstrationen laufen als statische HTML/JS-Seiten gegen ein gemeinsames AION-Backend. Die Produktionsinfrastruktur (Docker Compose, nginx, PostgreSQL, Keycloak-OIDC) ist identisch mit dem Setup, das in realen Pilotinstallationen eingesetzt wird.

Die Demo-Daten sind klinisch plausibel konstruiert, basierend auf:
- Sepsis-3-Definition (Singer et al., 2016)
- KDIGO-AKI-Leitlinie 2012
- Surviving Sepsis Campaign (SSC) Bundle SEP-1
- IPF-Therapiestandards (pirfenidon / nintedanib)

Formale Grundlagen: AION v1.0, Zenodo [10.5281/zenodo.19553130](https://zenodo.org/records/19553130)

---

Fragen zur Plattform oder zu einer Pilotinstallation: [info@iscad-it.de](mailto:info@iscad-it.de)
