# AION Clinical Blog

Statisches Blog-System für aion-clinical.eu.  
Markdown-Dateien → Python Build-Script → fertige HTML-Dateien.

---

## Schnellstart

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. Blog bauen
python build.py

# 3. Lokal testen (optional)
cd ..
python -m http.server 8000
# → http://localhost:8000/blog/
```

---

## Neuen Beitrag schreiben

1. Neue Datei in `posts/` anlegen: `YYYY-MM-DD-mein-titel.md`
2. Frontmatter am Anfang der Datei ausfüllen (siehe Format unten)
3. Inhalt in Markdown schreiben
4. `python build.py` ausführen
5. `blog/index.html` und `blog/mein-titel/index.html` auf den Server hochladen

### Frontmatter-Format

```yaml
---
title: "Titel des Beitrags"
date: 2026-05-12
category: release        # release | science | clinical | tutorial
lang: de                 # de | en | de,en
author: Friedhelm Matten
excerpt: "Kurzbeschreibung (1-2 Sätze, erscheint in der Übersicht)"
tags:
  - aion
  - release
---
```

### Kategorien

| Wert | Deutsch | Englisch | Farbe |
|---|---|---|---|
| `release` | Release | Release | Gold |
| `science` | Wissenschaft | Science | Blau |
| `clinical` | Klinik | Clinical | Grün |
| `tutorial` | Tutorial | Tutorial | Lila |

---

## Markdown-Features

### Code-Blöcke (mit Syntax-Highlighting)

````markdown
```python
from aion_clinical import ClinicalDataStore
store = ClinicalDataStore.from_fhir_bundle("data.json")
```
````

Unterstützte Sprachen: `python`, `bash`, `yaml`, `json`, `sql`, und viele mehr (via highlight.js).

### Tabellen

```markdown
| Spalte 1 | Spalte 2 |
|---|---|
| Wert A | Wert B |
```

### Hinweisboxen (Admonitions)

```markdown
!!! note "Hinweis"
    Dieser Text erscheint in einer blauen Box.

!!! warning "Achtung"
    Dieser Text erscheint in einer goldenen Warnbox.

!!! tip "Tipp"
    Dieser Text erscheint in einer grünen Box.
```

### Interne Links

```markdown
[Mehr zu AION](/aion/)
[Alle Publikationen](/#publications)
```

---

## Verzeichnisstruktur

```
blog/
├── build.py              ← Build-Script (hier ausführen)
├── requirements.txt      ← Python-Abhängigkeiten
├── README.md             ← Diese Datei
├── _templates/
│   ├── index.html        ← Vorlage für Blog-Übersicht
│   └── post.html         ← Vorlage für einzelne Beiträge
├── posts/
│   ├── 2026-05-12-aion-clinical-2-0-1-release.md
│   ├── 2026-05-09-aion-skalierungsschicht.md
│   └── 2026-04-20-cairn-fhir-r4-tutorial.md
└── [generiert — nicht manuell bearbeiten]
    ├── index.html
    ├── feed.xml
    ├── aion-clinical-2-0-1-release/
    │   └── index.html
    ├── aion-skalierungsschicht/
    │   └── index.html
    └── cairn-fhir-r4-tutorial/
        └── index.html
```

---

## Deployment

Nach `python build.py` die folgenden Dateien auf den Server hochladen:

```
blog/index.html
blog/feed.xml
blog/[slug]/index.html    ← für jeden Post
```

Die `posts/`, `_templates/` und `build.py` Dateien bleiben lokal — sie müssen **nicht** auf den Server.

### Empfohlene Server-Konfiguration (nginx)

```nginx
location /blog/ {
    root /var/www/aion-clinical.eu;
    try_files $uri $uri/ $uri/index.html =404;
}
```

---

## Watch-Modus (automatisches Neu-Bauen)

```bash
pip install watchdog
python build.py --watch
```

Änderungen in `posts/*.md` oder `_templates/*.html` lösen automatisch einen Rebuild aus.

---

© 2026 ISCaD GmbH · Wedemark · EUPL-1.2
