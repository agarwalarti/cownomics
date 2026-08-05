#!/usr/bin/env python3
"""
build.py — Cownomics static site builder

Usage:
    python3 build.py

What it does:
  1. Reads every .md file in /articles
  2. Converts each into a full HTML page using article-template.html
  3. Writes the result to /<slug>.html (site root, flat URLs)
  4. Regenerates the "Latest" article list on index.html from all articles,
     sorted newest first, written between the
     <!-- ARTICLES:START --> ... <!-- ARTICLES:END --> markers.

Markdown front matter format (top of each .md file):

    ---
    title: Leather–The Bane of Fashion
    date: 2025-01-05
    tag: Research
    description: A short one-line summary for search engines and social shares.
    slug: leather-the-bane-of-fashion
    cover_image: https://cownomics.com/images/leather.jpg
    cover_alt: Brown leather handbag
    ---

    Article body in plain markdown starts here.

Notes:
  - "slug" becomes the filename: <slug>.html, and the final URL is
    cownomics.com/<slug>.html
  - "tag" is for display/organization only — it is NOT part of the URL.
  - Run this script any time you add, edit, or remove a markdown file in
    /articles, then commit + push the changed/added HTML files.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

import markdown as md

ROOT = Path(__file__).parent
ARTICLES_DIR = ROOT / "articles"
TEMPLATE_PATH = ROOT / "article-template.html"
INDEX_PATH = ROOT / "index.html"
SITE_URL = "https://cownomics.com"

REQUIRED_FIELDS = ["title", "date", "tag", "description", "slug", "cover_image", "cover_alt"]


def parse_front_matter(text):
    """Very small, dependency-free front-matter parser (key: value pairs)."""
    if not text.startswith("---"):
        raise ValueError("Missing front matter (file must start with ---)")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Malformed front matter — need opening and closing ---")
    fm_block, body = parts[1], parts[2]

    fields = {}
    for line in fm_block.strip().splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()

    missing = [f for f in REQUIRED_FIELDS if f not in fields or not fields[f]]
    if missing:
        raise ValueError(f"Missing required front matter fields: {', '.join(missing)}")

    return fields, body.strip()


def format_date(raw_date):
    """Turns 2025-01-05 into '05 Jan 2025' for display."""
    dt = datetime.strptime(raw_date, "%Y-%m-%d")
    return dt.strftime("%d %b %Y"), dt


def build_article(md_path, template):
    raw = md_path.read_text(encoding="utf-8")
    fields, body_md = parse_front_matter(raw)
    body_html = md.markdown(body_md, extensions=["extra"])

    display_date, dt = format_date(fields["date"])
    slug = fields["slug"]
    canonical_url = f"{SITE_URL}/{slug}.html"

    html = template
    replacements = {
        "{{TITLE}}": fields["title"],
        "{{DESCRIPTION}}": fields["description"],
        "{{DATE}}": display_date,
        "{{TAG}}": fields["tag"],
        "{{COVER_IMAGE}}": fields["cover_image"],
        "{{COVER_ALT}}": fields["cover_alt"],
        "{{CANONICAL_URL}}": canonical_url,
        "{{BODY}}": body_html,
    }
    for key, value in replacements.items():
        html = html.replace(key, value)

    out_path = ROOT / f"{slug}.html"
    out_path.write_text(html, encoding="utf-8")

    return {
        "title": fields["title"],
        "tag": fields["tag"],
        "date_display": display_date,
        "date_sort": dt,
        "slug": slug,
    }


def rebuild_homepage_list(articles):
    articles_sorted = sorted(articles, key=lambda a: a["date_sort"], reverse=True)

    rows = []
    for a in articles_sorted:
        rows.append(
            "      <li class=\"article-row\">\n"
            f"        <span class=\"article-date\">{a['date_display']}</span>\n"
            f"        <a class=\"article-title\" href=\"/{a['slug']}.html\">{a['title']}</a>\n"
            f"        <span class=\"article-tag\">{a['tag']}</span>\n"
            "      </li>"
        )
    block = "\n\n".join(rows)

    index_html = INDEX_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(<!-- ARTICLES:START -->\n)(.*?)(\n<!-- ARTICLES:END -->)",
        re.DOTALL,
    )
    if not pattern.search(index_html):
        raise ValueError(
            "Could not find <!-- ARTICLES:START --> / <!-- ARTICLES:END --> "
            "markers in index.html"
        )
    new_index_html = pattern.sub(rf"\1{block}\3", index_html)
    INDEX_PATH.write_text(new_index_html, encoding="utf-8")


def main():
    if not ARTICLES_DIR.exists():
        print(f"No /articles folder found at {ARTICLES_DIR}. Nothing to build.")
        sys.exit(1)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    md_files = sorted(ARTICLES_DIR.glob("*.md"))

    if not md_files:
        print("No markdown files found in /articles.")
        sys.exit(0)

    articles = []
    for md_path in md_files:
        try:
            article = build_article(md_path, template)
            articles.append(article)
            print(f"Built {article['slug']}.html  ({article['title']})")
        except ValueError as e:
            print(f"Skipped {md_path.name}: {e}")

    if articles:
        rebuild_homepage_list(articles)
        print(f"\nHomepage article list updated with {len(articles)} article(s).")


if __name__ == "__main__":
    main()
