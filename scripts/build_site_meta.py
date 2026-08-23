#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape
from site_utils import latest_site_date

ROOT = Path(__file__).resolve().parents[1]

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def page_paths(root):
    paths = ["", "ja.html", "supplement.html", "supplement-talks.html", "supplement-updates.html", "blog.html"]
    manifest = root / "notes" / ".generated.json"
    if manifest.exists():
        try:
            entries = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            entries = []
        for name in entries:
            if name.endswith(".html") and not name.startswith("tag-"):
                paths.append("notes/" + name)
    return paths

def sitemap_xml(root):
    config = load_json(root / "data" / "homepage.json")
    base = str(config.get("site_url", "https://srin728.github.io/")).rstrip("/") + "/"
    lastmod = latest_site_date(root).isoformat()
    rows = []
    for rel in page_paths(root):
        rows.append(
            "  <url>\n"
            f"    <loc>{escape(base + rel)}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            "  </url>"
        )
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"

def robots_txt(root):
    config = load_json(root / "data" / "homepage.json")
    base = str(config.get("site_url", "https://srin728.github.io/")).rstrip("/") + "/"
    return f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n"

def outputs(root):
    return {root / "sitemap.xml": sitemap_xml(root), root / "robots.txt": robots_txt(root)}

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    stale = []
    for path, content in outputs(root).items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path.name)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
            print("generated", path.name)
    if stale:
        print("stale generated file(s): " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
