#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def highlight_text(text, highlights) -> str:
    source = str(text or "")
    terms = sorted({str(x) for x in (highlights or []) if x}, key=len, reverse=True)
    if not terms:
        return esc(source)
    pattern = re.compile("(" + "|".join(re.escape(x) for x in terms) + ")", re.IGNORECASE)
    wanted = {x.casefold() for x in terms}
    out = []
    for part in pattern.split(source):
        safe = esc(part)
        if part.casefold() in wanted:
            out.append(f'<span class="highlight">{safe}</span>')
        else:
            out.append(safe)
    return "".join(out)


def external_button(url: str, label: str) -> str:
    return (
        f'<a class="custom-button" href="{esc(url)}" target="_blank" '
        f'rel="noopener noreferrer">{esc(label)}</a>'
    )


def render_links(links, highlights) -> str:
    if not links:
        return ""
    items = links if isinstance(links, list) else [links]
    rows = []
    for link in items:
        if not isinstance(link, dict):
            continue
        parts = []
        if link.get("text"):
            parts.append(highlight_text(link["text"], highlights))
        if link.get("doi_id"):
            doi = str(link["doi_id"]).strip()
            parts.append(external_button("https://doi.org/" + quote(doi, safe="/._-()"), "DOI"))
        if link.get("arxiv_id"):
            aid = str(link["arxiv_id"]).strip()
            parts.append(external_button("https://arxiv.org/abs/" + quote(aid, safe="/._-"), "arXiv"))
        if link.get("url"):
            label = link.get("link-text") or link.get("link_text") or "Link"
            parts.append(external_button(str(link["url"]), str(label)))
        if parts:
            rows.append(" ".join(parts))
    return "<br>".join(rows)


def render_item(item: dict, *, inline_links: bool = False) -> str:
    highlights = item.get("highlightText") or []
    if not isinstance(highlights, list):
        highlights = [highlights]
    author = highlight_text(item.get("author", ""), highlights)
    title = highlight_text(item.get("title", ""), highlights)
    links = render_links(item.get("links"), highlights)

    body = ""
    if author:
        body += author + ": "
    body += title
    if links:
        body += (" " if inline_links else "<br>") + links
    return f"<li>{body}</li>"


def render_ordered_list(items, reverse_items: bool = False, *, inline_links: bool = False) -> str:
    rows = list(items or [])
    if reverse_items:
        rows.reverse()
    return (
        '<ol reversed>\n'
        + "\n".join(render_item(x, inline_links=inline_links) for x in rows)
        + "\n</ol>"
    )


def render_presentations(data: dict, lang: str) -> str:
    rows = data.get("presentations_list") or []
    categories = [
        (
            "international_non_refereed",
            data.get("international_non_refereed_category_title")
            or ("International Talks" if lang == "en" else "国際会議・研究集会等"),
        ),
        (
            "domestic_meeting",
            data.get("domestic_meeting_category_title")
            or ("Domestic Talks (in Japanese)" if lang == "en" else "国内研究会等"),
        ),
    ]
    known = {key for key, _ in categories}
    chunks = []
    for key, title in categories:
        items = [x for x in rows if x.get("type") == key]
        if items:
            chunks.append(f"<h3>{esc(title)}</h3>\n{render_ordered_list(items, reverse_items=True)}")
    unknown = [x for x in rows if x.get("type") not in known]
    if unknown:
        title = "Other Talks" if lang == "en" else "その他の発表"
        chunks.append(f"<h3>{title}</h3>\n{render_ordered_list(unknown, reverse_items=True)}")
    return "\n".join(chunks)


def render_biography(value) -> str:
    if isinstance(value, list):
        # Repository-controlled input. A small amount of inline HTML
        # (currently a grant link) is intentionally supported here.
        return "<ul>\n" + "\n".join(f"<li>{str(x)}</li>" for x in value) + "\n</ul>"
    return f"<p>{esc(value)}</p>"


def render_misc(config: dict) -> str:
    items = []
    for link in config.get("misc_links", []):
        items.append(
            f'<li><a href="{esc(link.get("url", ""))}" target="_blank" '
            f'rel="noopener noreferrer">{esc(link.get("label", "Link"))}</a></li>'
        )
    for note in config.get("misc_notes", []):
        items.append(f"<li>{esc(note)}</li>")
    return "<ul>\n" + "\n".join(items) + "\n</ul>"


def page_description(lang: str) -> str:
    if lang == "ja":
        return "斉藤凜の研究者ホームページ。研究分野、査読付き論文、研究発表、受賞歴を掲載しています。"
    return "Rin Saito's academic homepage: research interests, publications, talks, and awards."


def build_page(data: dict, config: dict, lang: str) -> str:
    is_ja = lang == "ja"
    other_href = "index.html" if is_ja else "ja.html"
    other_label = "English" if is_ja else "日本語"
    other_lang = "en" if is_ja else "ja"
    canonical = config.get("site_url", "https://srin728.github.io/")
    canonical = canonical.rstrip("/") + ("/ja.html" if is_ja else "/")
    home_en = config.get("site_url", "https://srin728.github.io/").rstrip("/") + "/"
    home_ja = config.get("site_url", "https://srin728.github.io/").rstrip("/") + "/ja.html"

    biography_title = data.get("biography", "C.V.")
    research_title = data.get("research_areas", "Research Interests")
    publications_title = data.get("publications", "Refereed Papers")
    preprints_title = data.get("preprints", "Preprints")
    presentations_title = data.get("presentations", "Talks")
    awards_title = data.get("awards", "Awards")
    misc_title = data.get("misc", "Misc")

    updated = config.get("last_updated_ja" if is_ja else "last_updated_en", "")
    updated_prefix = "最終更新: " if is_ja else "Last updated: "
    blog_url = config.get("blog_url", "blog.html")

    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{esc(page_description(lang))}">
  <meta name="theme-color" content="#ea533a">
  <meta name="google-site-verification" content="{esc(config.get('google_site_verification', ''))}">
  <link rel="canonical" href="{esc(canonical)}">
  <link rel="alternate" hreflang="en" href="{esc(home_en)}">
  <link rel="alternate" hreflang="ja" href="{esc(home_ja)}">
  <link rel="alternate" hreflang="x-default" href="{esc(home_en)}">
  <title>斉藤 凜 (Rin Saito)</title>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [["$", "$"], ["\\\\(", "\\\\)"]],
        displayMath: [["$$", "$$"], ["\\\\[", "\\\\]"]]
      }},
      options: {{
        skipHtmlTags: ["script", "noscript", "style", "textarea", "pre", "code"]
      }}
    }};
  </script>
  <script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <link rel="stylesheet" href="style.css">
  <script src="script.js" defer></script>
</head>
<body>
  <button class="menu-toggle" id="menu-toggle" type="button"
    aria-controls="sidebar" aria-expanded="true" aria-label="Toggle navigation">☰</button>

  <div class="container">
    <aside class="sidebar" id="sidebar" aria-label="Section navigation">
      <nav>
        <ul>
          <li><a href="#biography">{esc(biography_title)}</a></li>
          <li><a href="#research">{esc(research_title)}</a></li>
          <li><a href="#publications">{esc(publications_title)}</a></li>
          <li><a href="#preprints">{esc(preprints_title)}</a></li>
          <li><a href="#presentations">{esc(presentations_title)}</a></li>
          <li><a href="#awards">{esc(awards_title)}</a></li>
          <li><a href="#misc">{esc(misc_title)}</a></li>
        </ul>
      </nav>
    </aside>

    <main class="content" id="main-content">
      <h1>{esc(data.get('name', ''))}</h1>
      <p>{esc(data.get('affiliation', ''))}</p>
      <address class="contact">
        <p>{esc(data.get('email', ''))}</p>
        <p>{esc(data.get('address', ''))}</p>
      </address>

      <div id="language-switcher">
        <a class="language-button" href="{other_href}" hreflang="{other_lang}" lang="{other_lang}">{other_label}</a>
      </div>

      <section id="biography" class="section">
        <h2>{esc(biography_title)}</h2>
        {render_biography(data.get('biography_content', ''))}
      </section>

      <section id="research" class="section">
        <h2>{esc(research_title)}</h2>
        <p>{esc(data.get('research_areas_content', ''))}</p>
      </section>

      <section id="publications" class="section">
        <h2>{esc(publications_title)}</h2>
        {render_ordered_list(data.get('publications_list') or [])}
      </section>

      <section id="preprints" class="section">
        <h2>{esc(preprints_title)}</h2>
        {render_ordered_list(data.get('preprints_list') or [], inline_links=True)}
      </section>

      <section id="presentations" class="section">
        <h2>{esc(presentations_title)}</h2>
        {render_presentations(data, lang)}
      </section>

      <section id="awards" class="section">
        <h2>{esc(awards_title)}</h2>
        {render_ordered_list(data.get('awards_list') or [], inline_links=True)}
      </section>

      <section id="misc" class="section">
        <h2>{esc(misc_title)}</h2>
        {render_misc(config)}
      </section>
    </main>
  </div>

  <footer>
    <span>{updated_prefix}{esc(updated)} <a href="{esc(blog_url)}" class="no-underline" aria-label="Rin's Notes">🍙</a></span>
  </footer>
</body>
</html>
'''


def expected_outputs(root: Path) -> dict[Path, str]:
    en = load_json(root / "lang" / "en.json")
    ja = load_json(root / "lang" / "ja.json")
    config = load_json(root / "data" / "homepage.json")
    return {
        root / "index.html": build_page(en, config, "en"),
        root / "ja.html": build_page(ja, config, "ja"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the static academic homepage from lang/*.json")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--check", action="store_true", help="fail if generated pages are stale")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    outputs = expected_outputs(root)

    stale = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path.name)
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"generated {path.relative_to(root)}")

    if stale:
        print("stale generated file(s): " + ", ".join(stale), file=sys.stderr)
        print("run: python scripts/build_homepage.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
