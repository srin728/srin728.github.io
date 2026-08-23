#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from site_utils import format_date_ja, latest_site_date

ROOT = Path(__file__).resolve().parents[1]

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def esc(x):
    return html.escape(str(x or ""), quote=True)

def link(url, label):
    if not url:
        return esc(label)
    attrs = ' target="_blank" rel="noopener noreferrer"' if url.startswith(("http://", "https://")) else ""
    return f'<a href="{esc(url)}"{attrs}>{esc(label)}</a>'

def render_author(author):
    raw = str(author or "")
    prefix = "*" if raw.startswith("*") else ""
    name = raw[1:] if prefix else raw
    safe = esc(name)
    if name in {"Rin Saito", "斉藤 凜"}:
        safe = f'<span class="highlight">{safe}</span>'
    return prefix + safe

def authors(item):
    xs = item.get("authors") or []
    rendered = ", ".join(render_author(x) for x in xs) if xs else render_author(item.get("speaker", ""))
    if item.get("affiliation"):
        rendered += f' ({esc(item["affiliation"])})'
    return rendered

def talks_html(items):
    ordered = sorted(items, key=lambda x: str(x.get("sort_date") or x.get("date") or ""), reverse=True)
    if not ordered:
        return '<p class="empty">現在掲載準備中です。</p>'
    rows = []
    for item in ordered:
        a = authors(item)
        t = link(str(item.get("url", "")), str(item.get("title", "Untitled talk")))
        first = f"{a}: {t}" if a else t
        venue = ", ".join(
            esc(x) for x in (
                item.get("event", ""),
                item.get("location", ""),
                item.get("date_text") or item.get("date", "")
            ) if x
        )
        if venue and venue[-1] not in ".。":
            venue += "."
        note = esc(item.get("note", ""))
        body = first + (f"<br>{venue}" if venue else "")
        if note:
            body += f'<br><span class="talk-note">{note}</span>'
        rows.append(f"<li>{body}</li>")
    return '<ol reversed>\n' + "\n".join(rows) + '\n</ol>'

def updates_html(items):
    ordered = sorted(items, key=lambda x: str(x.get("date", "")), reverse=True)
    if not ordered:
        return '<p class="empty">現在掲載準備中です。</p>'
    rows = []
    for item in ordered:
        text = esc(item.get("text", ""))
        url = str(item.get("url", ""))
        if url:
            text += " " + link(url, str(item.get("link_text", "詳細")))
        date = esc(item.get("date", ""))
        suffix = f' <span class="news-date">({date})</span>' if date else ""
        rows.append(f"<li>{text}{suffix}</li>")
    return '<ul class="news-list">\n' + "\n".join(rows) + '\n</ul>'

def nav():
    return (
        '<nav class="nav" aria-label="補足情報ナビゲーション">'
        '<a href="supplement-talks.html">共著者による発表</a>'
        '<a href="supplement-updates.html">近況報告</a>'
        '<a href="ja.html">ホームへ戻る</a>'
        '</nav>'
    )

def page(page_title, heading, intro, canonical, content, updated):
    return "\n".join([
        '<!DOCTYPE html>', '<html lang="ja">', '<head>',
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'  <meta name="description" content="{esc(intro)}">',
        '  <meta name="theme-color" content="#f8c112">',
        '  <meta property="og:type" content="website">',
        f'  <meta property="og:title" content="{esc(page_title)}">',
        f'  <meta property="og:description" content="{esc(intro)}">',
        f'  <meta property="og:url" content="{esc(canonical)}">',
        f'  <link rel="canonical" href="{esc(canonical)}">',
        f'  <title>{esc(page_title)}</title>',
        '  <link rel="stylesheet" href="supplement.css">',
        '</head>', '<body>', '  <main class="page">',
        '    <header class="hero">', f'      <h1>{esc(heading)}</h1>', f'      <p>{esc(intro)}</p>', f'      {nav()}', '    </header>', '',
        f'    {content}', '', '    <footer>', f'      <span>最終更新: {esc(updated)}</span>', '    </footer>', '  </main>', '</body>', '</html>', ''
    ])

def expected_outputs(root):
    data = load_json(root / "data" / "supplemental.json")
    config = load_json(root / "data" / "homepage.json")
    base = str(config.get("site_url", "https://srin728.github.io/")).rstrip("/") + "/"
    title = str(data.get("title", "Supplement / 補足情報"))
    intro = str(data.get("intro", ""))
    updated = format_date_ja(latest_site_date(root))
    landing = '<section class="landing"><h2>補足情報</h2><p>上のボタンから表示する内容を選択してください。</p></section>'
    note = str(data.get("coauthor_talks_note", ""))
    note_html = f'<p class="section-note">{esc(note)}</p>' if note else ""
    talk_body = '<section id="coauthor-talks"><h2>共著者による発表</h2>' + note_html + talks_html(data.get("coauthor_talks") or []) + '</section>'
    update_body = '<section id="updates"><h2>近況報告</h2>' + updates_html(data.get("updates") or []) + '</section>'
    return {
        root / "supplement.html": page(title, title, intro, base + "supplement.html", landing, updated),
        root / "supplement-talks.html": page("共著者による発表 | " + title, "共著者による発表", "共著者による研究発表を掲載しています。", base + "supplement-talks.html", talk_body, updated),
        root / "supplement-updates.html": page("近況報告 | " + title, "近況報告", "研究活動に関する近況報告を掲載しています。", base + "supplement-updates.html", update_body, updated),
    }

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    stale = []
    for path, content in expected_outputs(root).items():
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
