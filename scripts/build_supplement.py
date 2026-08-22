#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

from site_utils import format_date_ja, latest_site_date

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def maybe_link(url: str, label: str) -> str:
    if not url:
        return esc(label)
    external = url.startswith(("http://", "https://"))
    attrs = ' target="_blank" rel="noopener noreferrer"' if external else ""
    return f'<a href="{esc(url)}"{attrs}>{esc(label)}</a>'


def render_coauthor_talks(items) -> str:
    if not items:
        return '<p class="empty">現在掲載準備中です。</p>'
    rows = []
    for item in sorted(items, key=lambda x: str(x.get("date", "")), reverse=True):
        title = maybe_link(str(item.get("url", "")), str(item.get("title", "Untitled talk")))
        speaker = esc(item.get("speaker", ""))
        event = esc(item.get("event", ""))
        date = esc(item.get("date", ""))
        location = esc(item.get("location", ""))
        meta = " · ".join(x for x in (speaker, event, date, location) if x)
        note = esc(item.get("note", ""))
        note_html = f'<p class="entry-note">{note}</p>' if note else ""
        rows.append(
            '<li class="entry">'
            f'<p class="entry-title">{title}</p>'
            f'<p class="entry-meta">{meta}</p>'
            f'{note_html}'
            '</li>'
        )
    return '<ul class="entry-list">\n' + "\n".join(rows) + "\n</ul>"


def render_updates(items) -> str:
    if not items:
        return '<p class="empty">現在掲載準備中です。</p>'
    rows = []
    for item in sorted(items, key=lambda x: str(x.get("date", "")), reverse=True):
        date = esc(item.get("date", ""))
        text = esc(item.get("text", ""))
        url = str(item.get("url", ""))
        link_text = str(item.get("link_text", "詳細"))
        link = " " + maybe_link(url, link_text) if url else ""
        rows.append(
            '<li class="entry">'
            f'<p class="entry-title">{text}{link}</p>'
            f'<p class="entry-meta">{date}</p>'
            '</li>'
        )
    return '<ul class="entry-list">\n' + "\n".join(rows) + "\n</ul>"


def build_page(data: dict, config: dict, updated_date) -> str:
    site_url = str(config.get("site_url", "https://srin728.github.io/")).rstrip("/") + "/"
    canonical = site_url + "supplement.html"
    title = str(data.get("title", "Supplement / 補足情報"))
    intro = str(data.get("intro", ""))
    updated = format_date_ja(updated_date)

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{esc(intro)}">
  <meta name="theme-color" content="#f8c112">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(intro)}">
  <meta property="og:url" content="{esc(canonical)}">
  <link rel="canonical" href="{esc(canonical)}">
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="supplement.css">
</head>
<body>
  <main class="page">
    <header class="hero">
      <h1>{esc(title)}</h1>
      <p>{esc(intro)}</p>
      <nav class="nav" aria-label="ページ内ナビゲーション">
        <a href="#coauthor-talks">共著者による発表</a>
        <a href="#updates">近況報告</a>
        <a href="ja.html">ホームへ戻る</a>
      </nav>
    </header>

    <section id="coauthor-talks">
      <h2>共著者による発表</h2>
      {render_coauthor_talks(data.get("coauthor_talks") or [])}
    </section>

    <section id="updates">
      <h2>近況報告</h2>
      {render_updates(data.get("updates") or [])}
    </section>

    <footer>
      <span>最終更新: {esc(updated)}</span>
    </footer>
  </main>
</body>
</html>
'''


def expected_output(root: Path) -> str:
    data = load_json(root / "data" / "supplemental.json")
    config = load_json(root / "data" / "homepage.json")
    return build_page(data, config, latest_site_date(root))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build supplemental static page")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--check", action="store_true", help="fail if supplement.html is stale")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    path = root / "supplement.html"
    content = expected_output(root)

    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            print("stale generated file: supplement.html", file=sys.stderr)
            print("run: python scripts/build_supplement.py", file=sys.stderr)
            return 1
        return 0

    path.write_text(content, encoding="utf-8", newline="\n")
    print("generated supplement.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
