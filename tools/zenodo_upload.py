#!/usr/bin/env python3
"""
CAIRN — Zenodo Upload Script
=============================
Creates a new version of the CAIRN Zenodo record and uploads all release files.

Usage:
    export ZENODO_TOKEN=your_token_here
    python3 tools/zenodo_upload.py

    # or pass token directly:
    python3 tools/zenodo_upload.py --token your_token_here

    # dry-run (no actual upload):
    python3 tools/zenodo_upload.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

# ── Configuration ──────────────────────────────────────────────────────────────

# Zenodo-Deposit-ID, von der Schritt 2 (`actions/newversion`) die neue Fassung
# ableitet. Sie muss die Fassung benennen, von der abgeleitet werden soll -- das ist
# die aktuelle (letzte). Ob die Legacy-API eine ueberholte Fassung zurueckweist,
# ist hier NICHT gemessen; unabhaengig davon ist die alte Nummer nicht gemeint.
#
# Berichtigt 29.08.2026: hier stand "19483182". Das ist die ALT-Fassung 1.0.0 vom
# 09.04.2026 (`relations.version` Index 0, `is_last: false`), gemessen 24.08.2026 --
# Befund B-1 in leitstand/eingang/BERICHT-2026-08-24-erklaerheft-cairn-mobdev.md.
# Massgeblich ist Fassung 1.0.4 vom 25.05.2026: Record 20375036, DOI
# 10.5281/zenodo.20375036; Konzept-Kennung 19483181 (Konzept-DOI
# 10.5281/zenodo.19483181), die stets auf die letzte Fassung aufloest.
RECORD_ID       = "20375036"         # Zenodo deposit ID for CAIRN (Fassung 1.0.4, aktuell)
ZENODO_BASE_URL = "https://zenodo.org/api"
REPO_ROOT       = Path(__file__).parent.parent

# Metadata from .zenodo.json -- zugleich die EINZIGE Quelle der Fassungsnummer.
ZENODO_JSON = REPO_ROOT / ".zenodo.json"


def _fassung() -> str:
    """Fassung aus .zenodo.json lesen, nicht fest verdrahten.

    Bis 29.08.2026 stand "1.0.1" an DREI Stellen im Ausgabetext (Kopfzeile,
    Dry-Run, Erfolgsmeldung), unabhaengig von .zenodo.json. Genau diese Drift
    gehoert zur Vorgeschichte des Fehlstands, den dieses Skript reparieren
    soll: Der Record 20375036 weist 1.0.4 aus und traegt ein 1.0.1-Archiv.
    Eine Anzeige, die die deponierte Fassung nur BEHAUPTET, ist genau die
    Stelle, an der ein Bediener den Fehler nicht sieht.

    Faellt bewusst auf "?" zurueck statt zu scheitern -- eine kaputte Anzeige
    darf keinen Upload verhindern, und "?" ist ehrlicher als eine Zahl, die
    nirgendwoher stammt.
    """
    try:
        return json.loads(ZENODO_JSON.read_text(encoding="utf-8"))["version"]
    except Exception:
        return "?"


VERSION = _fassung()

# Files to upload. Der Name wird aus VERSION gebildet, damit er nicht erneut
# hinter der Fassung zurueckbleiben kann. Das Zip entsteht per
#     git archive --format=zip --prefix=cairn-<VERSION>/ -o dist/cairn-<VERSION>-source.zip v<VERSION>
# AUS DEM TAG, nicht aus dem Arbeitsbaum. dist/ ist in .gitignore.
UPLOAD_FILES = [
    REPO_ROOT / "dist" / f"cairn-{VERSION}-source.zip",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def check_response(r: requests.Response, action: str) -> dict:
    if not r.ok:
        print(f"  ✗ {action} fehlgeschlagen: {r.status_code} — {r.text[:300]}")
        sys.exit(1)
    print(f"  ✓ {action}")
    return r.json()


# ── Main Upload Logic ──────────────────────────────────────────────────────────

def run(token: str, dry_run: bool = False) -> None:
    print("\n" + "═" * 60)
    print(f"  CAIRN Zenodo Upload — v{VERSION}")
    print(f"  Record ID : {RECORD_ID}")
    print(f"  Dry-run   : {dry_run}")
    print("═" * 60)

    # ── Dry-run: file check only, no API calls needed ─────────────────────────
    if dry_run:
        print("\n[DRY-RUN] Dateien prüfen ...")
        all_ok = True
        total_bytes = 0
        for f in UPLOAD_FILES:
            if f.exists():
                size_kb = f.stat().st_size // 1024
                total_bytes += f.stat().st_size
                print(f"  ✓ {f.name:<45} {size_kb:>6} KB")
            else:
                print(f"  ✗ FEHLT: {f}")
                all_ok = False

        print(f"\n[DRY-RUN] Metadaten ({ZENODO_JSON.name}) ...")
        if ZENODO_JSON.exists():
            meta = json.load(open(ZENODO_JSON))
            print(f"  ✓ version          : {meta.get('version')}")
            print(f"  ✓ publication_date : {meta.get('publication_date')}")
            print(f"  ✓ creators         : {meta['creators'][0]['name']}")
            print(f"  ✓ keywords         : {len(meta.get('keywords', []))} Einträge")
        else:
            print(f"  ✗ {ZENODO_JSON} fehlt")
            all_ok = False

        print(f"\n[DRY-RUN] Ziel ...")
        print(f"  → Zenodo Record : https://zenodo.org/deposit/{RECORD_ID}")
        print(f"  → Neue Version  : v{VERSION}")
        print(f"  → Gesamtgröße   : {total_bytes // 1024} KB")
        print(f"\n[DRY-RUN] {'✅ Bereit für Upload.' if all_ok else '❌ Bitte fehlende Dateien ergänzen.'}")
        print("  Starte echten Upload mit: python3 tools/zenodo_upload.py --token TOKEN")
        return

    headers = get_headers(token)
    headers_no_ct = {k: v for k, v in headers.items() if k != "Content-Type"}

    # ── Step 1: Verify existing record ────────────────────────────────────────
    print("\n[1] Bestehenden Record prüfen ...")
    r = requests.get(f"{ZENODO_BASE_URL}/records/{RECORD_ID}", headers=headers_no_ct)
    if r.status_code == 404:
        # Try deposits endpoint (for unpublished drafts)
        r = requests.get(f"{ZENODO_BASE_URL}/deposit/depositions/{RECORD_ID}", headers=headers_no_ct)
    check_response(r, f"Record {RECORD_ID} gefunden")
    record = r.json()
    print(f"     Titel  : {record.get('title', record.get('metadata', {}).get('title', '?'))}")
    print(f"     Status : {record.get('state', record.get('status', '?'))}")

    # ── Step 2: Create new version ─────────────────────────────────────────────
    print("\n[2] Neue Version erstellen ...")
    r = requests.post(
        f"{ZENODO_BASE_URL}/deposit/depositions/{RECORD_ID}/actions/newversion",
        headers=headers_no_ct,
    )
    new_version = check_response(r, "Neue Version erstellt")
    new_id = new_version["id"]
    bucket_url = new_version["links"]["bucket"]
    print(f"     Neue Deposit-ID : {new_id}")

    # ── Step 3: Delete old files ───────────────────────────────────────────────
    print("\n[3] Alte Dateien entfernen ...")
    r = requests.get(f"{ZENODO_BASE_URL}/deposit/depositions/{new_id}/files", headers=headers_no_ct)
    old_files = check_response(r, "Dateiliste abgerufen")
    for f in old_files:
        rd = requests.delete(
            f"{ZENODO_BASE_URL}/deposit/depositions/{new_id}/files/{f['id']}",
            headers=headers_no_ct,
        )
        if rd.ok:
            print(f"  ✓ Gelöscht: {f['filename']}")
        else:
            print(f"  ⚠ Konnte nicht löschen: {f['filename']}")

    # ── Step 4: Upload new files ───────────────────────────────────────────────
    print("\n[4] Neue Dateien hochladen ...")
    for filepath in UPLOAD_FILES:
        if not filepath.exists():
            print(f"  ⚠ Datei nicht gefunden, übersprungen: {filepath}")
            continue
        size_kb = filepath.stat().st_size // 1024
        print(f"  → {filepath.name} ({size_kb} KB) ...")
        with open(filepath, "rb") as fh:
            ru = requests.put(
                f"{bucket_url}/{filepath.name}",
                data=fh,
                headers=headers_no_ct,
            )
        if ru.ok:
            print(f"  ✓ Hochgeladen: {filepath.name}")
        else:
            print(f"  ✗ Fehler beim Upload: {ru.status_code} — {ru.text[:200]}")
            sys.exit(1)

    # ── Step 5: Update metadata ────────────────────────────────────────────────
    #
    # WARNUNG -- DAS LIZENZFELD IST UEBER DIESE API NACHWEISLICH NICHT SCHREIBBAR.
    # Gemessen 09.08.2026 (Befund B-3 in
    # leitstand/eingang/BERICHT-2026-08-09-en-abnahme-zenodo-mobdev.md): Die
    # Legacy-Deposit-API (`actions/edit` -> PUT -> `actions/publish`) NIMMT das
    # Lizenzfeld AN und antwortet HTTP 200/202, SCHREIBT es aber NICHT -- stiller
    # Rueckfall auf den Altwert. Im selben Aufruf wurde die Beschreibung
    # erfolgreich geaendert: Ein Teilerfolg verdeckt hier den Fehlschlag des
    # anderen Teils, der PUT sieht von aussen vollstaendig gelungen aus.
    # check_response() unten prueft nur den Statuscode und kann das nicht bemerken.
    #
    # Folge fuer jeden Lauf: Nach dem Publish den RECORD lesen, nicht die Antwort
    # dieses Aufrufs -- ein Erfolgscode ist eine Aussage ueber die Uebermittlung,
    # nicht ueber die Wirkung. Weicht das Lizenzfeld vom Sollwert in .zenodo.json
    # ab, ist es in der Zenodo-Weboberflaeche zu stellen (FM-Handgriff, Regel 6);
    # der zweite API-Weg (RDM) ist am selben Tag ebenfalls gescheitert (verwarf
    # Pflichtfelder, Publish 400). Sollwert ist die Dual-Lizenz
    # AGPL-3.0-only OR LicenseRef-ISCaD-Commercial; Zenodos license-Feld nimmt
    # eine Kennung -- agpl-3.0-only (Vokabular-Kennung, HTTP 200; die frueher
    # gefuehrte Schreibweise apgl-v3 existiert im Vokabular nicht, HTTP 404),
    # die kommerzielle Haelfte steht in notes.
    print("\n[5] Metadaten aktualisieren ...")
    with open(ZENODO_JSON) as f:
        zenodo_meta = json.load(f)

    metadata = {
        "metadata": {
            "title":            zenodo_meta["title"],
            "description":      zenodo_meta["description"],
            "version":          zenodo_meta["version"],
            "upload_type":      zenodo_meta["upload_type"],
            "publication_date": zenodo_meta["publication_date"],
            "license":          zenodo_meta["license"],
            "keywords":         zenodo_meta["keywords"],
            "creators":         zenodo_meta["creators"],
            "related_identifiers": zenodo_meta["related_identifiers"],
            "notes":            zenodo_meta["notes"],
        }
    }

    r = requests.put(
        f"{ZENODO_BASE_URL}/deposit/depositions/{new_id}",
        json=metadata,
        headers=headers,
    )
    check_response(r, "Metadaten aktualisiert")

    # ── Step 6: Publish ────────────────────────────────────────────────────────
    print("\n[6] Veröffentlichen ...")
    r = requests.post(
        f"{ZENODO_BASE_URL}/deposit/depositions/{new_id}/actions/publish",
        headers=headers_no_ct,
    )
    result = check_response(r, "Veröffentlicht!")
    doi = result.get("doi", result.get("metadata", {}).get("doi", "?"))
    url = result.get("links", {}).get("html", f"https://zenodo.org/records/{new_id}")

    print("\n" + "═" * 60)
    print(f"  ✅ CAIRN v{VERSION} auf Zenodo veröffentlicht!")
    print(f"  DOI : {doi}")
    print(f"  URL : {url}")
    print("═" * 60 + "\n")


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CAIRN Zenodo Upload")
    parser.add_argument("--token",   help="Zenodo API Token (alternativ: ZENODO_TOKEN env var)")
    parser.add_argument("--dry-run", action="store_true", help="Kein Upload, nur Prüfung")
    args = parser.parse_args()

    token = args.token or os.environ.get("ZENODO_TOKEN", "")
    if not token:
        # Try reading from temp file
        try:
            token = Path("/tmp/.zt").read_text().strip()
            print("Token aus /tmp/.zt gelesen.")
        except FileNotFoundError:
            if args.dry_run:
                token = "dry-run-no-token"  # dry-run needs no real token
            else:
                print("Fehler: Kein Zenodo-Token gefunden.")
                print("Setze ZENODO_TOKEN oder übergib --token TOKEN")
                sys.exit(1)

    run(token=token, dry_run=args.dry_run)
