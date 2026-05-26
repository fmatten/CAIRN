#!/usr/bin/env python3
"""
AION Clinical Blog — Static Site Builder
=========================================
Wandelt Markdown-Dateien in statische HTML-Seiten um.

Verwendung:
    python build.py              # Alle Posts bauen
    python build.py --watch      # Bauen + auf Änderungen warten (braucht watchdog)
    python build.py --post NAME  # Nur einen Post bauen (z.B. --post aion-2-0-1-release)

Abhängigkeiten installieren:
    pip install -r requirements.txt

Verzeichnisstruktur:
    blog/
    ├── build.py              ← dieses Skript
    ├── requirements.txt
    ├── _templates/
    │   ├── index.html        ← Vorlage für die Blog-Übersicht
    │   └── post.html         ← Vorlage für einzelne Beiträge
    ├── posts/
    │   ├── YYYY-MM-DD-slug.md  ← Markdown-Quellen
    │   └── ...
    └── [generiert]
        ├── index.html
        └── [slug]/index.html

Frontmatter-Format (YAML zwischen --- Trennern):
    ---
    title: "Titel des Beitrags"
    date: 2026-05-12
    category: release       # release | science | clinical | tutorial
    lang: de                # de | en | de,en
    author: Friedhelm Matten
    excerpt: "Kurzbeschreibung für die Übersicht (1-2 Sätze)"
    tags:
      - aion
      - release
      - pypi
    ---
"""

import os
import re
import sys
import time
import shutil
import argparse
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("FEHLER: PyYAML nicht gefunden. Bitte: pip install PyYAML")
    sys.exit(1)

try:
    import markdown
    from markdown.extensions.toc import TocExtension
except ImportError:
    print("FEHLER: markdown nicht gefunden. Bitte: pip install markdown")
    sys.exit(1)

# ─────────────────────────────────────────
# Konfiguration
# ─────────────────────────────────────────
BLOG_DIR      = Path(__file__).parent.resolve()
POSTS_DIR     = BLOG_DIR / "posts"
TEMPLATES_DIR = BLOG_DIR / "_templates"
OUTPUT_DIR    = BLOG_DIR   # Output direkt ins Blog-Verzeichnis

SITE_BASE_URL = "https://aion-clinical.eu"
BLOG_PATH     = "/blog"

CATEGORY_META = {
    "release":  {"de": "Release",      "en": "Release",     "color": "gold"},
    "science":  {"de": "Wissenschaft", "en": "Science",     "color": "aion"},
    "clinical": {"de": "Klinik",       "en": "Clinical",    "color": "cairn"},
    "tutorial": {"de": "Tutorial",     "en": "Tutorial",    "color": "purple"},
}

DE_MONTHS = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

EN_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


# ─────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────
def format_date_de(dt: datetime) -> str:
    return f"{dt.day}. {DE_MONTHS[dt.month]} {dt.year}"

def format_date_en(dt: datetime) -> str:
    return f"{EN_MONTHS[dt.month]} {dt.day}, {dt.year}"

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[äöüß]", lambda m: {"ä":"ae","ö":"oe","ü":"ue","ß":"ss"}[m.group()], text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")

def render(template: str, variables: dict) -> str:
    """Einfache {{VARIABLE}} Template-Substitution."""
    for key, value in variables.items():
        template = template.replace(f"{{{{{key}}}}}", str(value) if value is not None else "")
    return template


# ─────────────────────────────────────────
# Post parsen
# ─────────────────────────────────────────
def parse_post(path: Path) -> dict:
    """Liest eine Markdown-Datei mit YAML-Frontmatter."""
    raw = path.read_text(encoding="utf-8")

    # Frontmatter trennen
    meta = {}
    body_md = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError as e:
                print(f"  ⚠ YAML-Fehler in {path.name}: {e}")
            body_md = parts[2].strip()

    # Slug aus Dateiname ableiten
    stem = path.stem  # z.B. "2026-05-12-aion-release"
    slug_raw = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
    slug = meta.get("slug", slug_raw)

    # Datum aus Dateiname oder Frontmatter
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
    date = datetime.now()
    if date_match:
        date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
    if "date" in meta:
        d = meta["date"]
        if isinstance(d, str):
            date = datetime.strptime(d, "%Y-%m-%d")
        else:
            date = datetime(d.year, d.month, d.day)

    # Markdown → HTML (mit Erweiterungen)
    md_ext = [
        TocExtension(permalink=True, toc_depth="2-4"),
        "fenced_code",
        "tables",
        "footnotes",
        "attr_list",
        "def_list",
        "admonition",
        "meta",
    ]
    md_parser = markdown.Markdown(extensions=md_ext)
    body_html = md_parser.convert(body_md)
    toc_html  = md_parser.toc

    # Tags normalisieren
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    cat = meta.get("category", "science")
    cat_info = CATEGORY_META.get(cat, CATEGORY_META["science"])

    return {
        "slug":           slug,
        "title":          meta.get("title", stem),
        "date":           date,
        "date_iso":       date.strftime("%Y-%m-%d"),
        "date_de":        format_date_de(date),
        "date_en":        format_date_en(date),
        "category":       cat,
        "cat_label_de":   cat_info["de"],
        "cat_label_en":   cat_info["en"],
        "cat_color":      cat_info["color"],
        "lang":           meta.get("lang", "de"),
        "lang_label":     {"de": "DE", "en": "EN", "de,en": "DE · EN"}.get(meta.get("lang","de"), "DE"),
        "author":         meta.get("author", "Friedhelm Matten"),
        "excerpt":        meta.get("excerpt", ""),
        "tags":           tags,
        "body_html":      body_html,
        "toc_html":       toc_html,
        "source_path":    path,
    }


# ─────────────────────────────────────────
# Einzelnen Post generieren
# ─────────────────────────────────────────
def build_post(post: dict, template: str):
    post_dir = OUTPUT_DIR / post["slug"]
    post_dir.mkdir(parents=True, exist_ok=True)

    tags_html = "".join(
        f'<a href="{BLOG_PATH}/?tag={t}" class="post-tag">{t}</a>'
        for t in post["tags"]
    )

    html = render(template, {
        "TITLE":          post["title"],
        "DATE_DE":        post["date_de"],
        "DATE_EN":        post["date_en"],
        "DATE_ISO":       post["date_iso"],
        "CATEGORY":       post["category"],
        "CAT_LABEL_DE":   post["cat_label_de"],
        "CAT_LABEL_EN":   post["cat_label_en"],
        "LANG":           post["lang"],
        "LANG_LABEL":     post["lang_label"],
        "AUTHOR":         post["author"],
        "EXCERPT":        post["excerpt"],
        "BODY":           post["body_html"],
        "TOC":            post["toc_html"],
        "SLUG":           post["slug"],
        "TAGS_HTML":      tags_html,
        "BLOG_PATH":      BLOG_PATH,
        "SITE_BASE_URL":  SITE_BASE_URL,
    })

    out = post_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  ✓  {BLOG_PATH}/{post['slug']}/")


# ─────────────────────────────────────────
# Blog-Index generieren
# ─────────────────────────────────────────
def build_index(posts: list, template: str):
    cards = []
    for p in posts:
        tags_html = " ".join(f'<span class="post-tag">{t}</span>' for t in p["tags"])
        cards.append(f"""
      <article class="post-card" data-category="{p['category']}" data-lang="{p['lang']}">
        <div class="card-meta">
          <time datetime="{p['date_iso']}">
            <span class="de">{p['date_de']}</span>
            <span class="en">{p['date_en']}</span>
          </time>
          <span class="lang-badge">{p['lang_label']}</span>
        </div>
        <span class="cat-pill cat-{p['category']}">
          <span class="de">{p['cat_label_de']}</span>
          <span class="en">{p['cat_label_en']}</span>
        </span>
        <h2 class="card-title">
          <a href="{BLOG_PATH}/{p['slug']}/">{p['title']}</a>
        </h2>
        <p class="card-excerpt">{p['excerpt']}</p>
        <div class="card-footer">
          <span class="card-author">{p['author']}</span>
          <a class="card-read de" href="{BLOG_PATH}/{p['slug']}/">Beitrag lesen →</a>
          <a class="card-read en" href="{BLOG_PATH}/{p['slug']}/">Read post →</a>
        </div>
      </article>""")

    html = render(template, {
        "POSTS_HTML":    "\n".join(cards),
        "POST_COUNT":    len(posts),
        "BLOG_PATH":     BLOG_PATH,
        "SITE_BASE_URL": SITE_BASE_URL,
    })

    out = OUTPUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  ✓  {BLOG_PATH}/index.html")


# ─────────────────────────────────────────
# RSS-Feed generieren
# ─────────────────────────────────────────
def build_rss(posts: list):
    items = []
    for p in posts[:20]:
        items.append(f"""  <item>
    <title><![CDATA[{p['title']}]]></title>
    <link>{SITE_BASE_URL}{BLOG_PATH}/{p['slug']}/</link>
    <description><![CDATA[{p['excerpt']}]]></description>
    <pubDate>{p['date'].strftime('%a, %d %b %Y 00:00:00 +0000')}</pubDate>
    <guid>{SITE_BASE_URL}{BLOG_PATH}/{p['slug']}/</guid>
    <category>{p['category']}</category>
  </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>AION Clinical Blog</title>
  <link>{SITE_BASE_URL}{BLOG_PATH}/</link>
  <description>Release-Notes, Wissenschaft, Klinik-Praxis und Tutorials zu AION und CAIRN</description>
  <language>de</language>
  <atom:link href="{SITE_BASE_URL}{BLOG_PATH}/feed.xml" rel="self" type="application/rss+xml"/>
  <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
{chr(10).join(items)}
</channel>
</rss>"""

    (OUTPUT_DIR / "feed.xml").write_text(rss, encoding="utf-8")
    print(f"  ✓  {BLOG_PATH}/feed.xml")


# ─────────────────────────────────────────
# Hauptprogramm
# ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AION Clinical Blog Builder")
    parser.add_argument("--watch", action="store_true", help="Auf Änderungen warten und neu bauen")
    parser.add_argument("--post",  type=str, default=None, help="Nur einen Post bauen (slug)")
    args = parser.parse_args()

    print("╔══════════════════════════════════════╗")
    print("║  AION Clinical Blog — Build Script   ║")
    print("╚══════════════════════════════════════╝\n")

    # Templates laden
    if not TEMPLATES_DIR.exists():
        print(f"FEHLER: _templates/ nicht gefunden in {BLOG_DIR}")
        sys.exit(1)

    index_tpl = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    post_tpl  = (TEMPLATES_DIR / "post.html").read_text(encoding="utf-8")

    def run_build(only_slug=None):
        post_files = sorted(POSTS_DIR.glob("*.md"), reverse=True)
        all_posts  = []

        for f in post_files:
            try:
                post = parse_post(f)
                all_posts.append(post)
            except Exception as e:
                print(f"  ⚠ Fehler beim Parsen von {f.name}: {e}")

        if only_slug:
            targets = [p for p in all_posts if p["slug"] == only_slug]
            if not targets:
                print(f"Post '{only_slug}' nicht gefunden.")
                return
            print(f"Baue Post: {only_slug}")
            build_post(targets[0], post_tpl)
        else:
            print(f"Gefunden: {len(all_posts)} Posts\n")
            print("Baue Posts:")
            for p in all_posts:
                build_post(p, post_tpl)
            print("\nBaue Index:")
            build_index(all_posts, index_tpl)
            print("\nBaue RSS-Feed:")
            build_rss(all_posts)
            print(f"\n✓ Fertig — {len(all_posts)} Posts gebaut")

    run_build(args.post)

    if args.watch:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class Handler(FileSystemEventHandler):
                def on_modified(self, event):
                    if event.src_path.endswith(".md") or event.src_path.endswith(".html"):
                        print(f"\n↻ Änderung erkannt: {Path(event.src_path).name}")
                        run_build()

            observer = Observer()
            observer.schedule(Handler(), str(POSTS_DIR), recursive=False)
            observer.schedule(Handler(), str(TEMPLATES_DIR), recursive=False)
            observer.start()
            print("\n👁  Beobachte posts/ und _templates/ auf Änderungen … (Ctrl+C zum Beenden)")
            while True:
                time.sleep(1)
        except ImportError:
            print("\nHinweis: pip install watchdog für --watch Modus")
        except KeyboardInterrupt:
            observer.stop()
            observer.join()


if __name__ == "__main__":
    main()
