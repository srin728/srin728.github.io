#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = "notes"
MANIFEST_NAME = ".generated.json"


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def parse_front_matter(text: str) -> tuple[dict, str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        return {}, text

    meta = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [x.strip() for x in value[1:-1].split(",") if x.strip()]
        else:
            meta[key] = value
    return meta, text[match.end():]


def inline_markup(text: str) -> str:
    safe = esc(text)

    code_values = []
    def save_code(match):
        code_values.append(f"<code>{match.group(1)}</code>")
        return f"\x00CODE{len(code_values)-1}\x00"
    safe = re.sub(r"`([^`\n]+)`", save_code, safe)

    safe = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        r'<a href="\2">\1</a>',
        safe,
    )
    safe = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"__([^_\n]+)__", r"<strong>\1</strong>", safe)
    safe = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", safe)

    for i, value in enumerate(code_values):
        safe = safe.replace(f"\x00CODE{i}\x00", value)
    return safe


def markdown_to_html(source: str) -> str:
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    paragraph = []
    list_type = None
    in_code = False
    code_lang = ""
    code_lines = []
    in_math = False
    math_lines = []

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            text = " ".join(x.strip() for x in paragraph)
            out.append(f"<p>{inline_markup(text)}</p>")
            paragraph = []

    def close_list():
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    def flush_code():
        nonlocal code_lines, code_lang
        cls = f' class="language-{esc(code_lang)}"' if code_lang else ""
        out.append(f"<pre><code{cls}>{esc(chr(10).join(code_lines))}</code></pre>")
        code_lines = []
        code_lang = ""

    def flush_math():
        nonlocal math_lines
        out.append('<div class="math-display">$$\n' + esc("\n".join(math_lines)) + '\n$$</div>')
        math_lines = []

    for line in lines:
        stripped = line.strip()

        if in_code:
            if stripped.startswith("```"):
                in_code = False
                flush_code()
            else:
                code_lines.append(line)
            continue

        if in_math:
            if stripped == "$$":
                in_math = False
                flush_math()
            else:
                math_lines.append(line)
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            in_code = True
            code_lang = stripped[3:].strip()
            continue

        if stripped == "$$":
            flush_paragraph()
            close_list()
            in_math = True
            continue

        if not stripped:
            flush_paragraph()
            close_list()
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline_markup(heading.group(2).strip())}</h{level}>")
            continue

        quote = re.match(r"^\s*>\s?(.*)$", line)
        if quote:
            flush_paragraph()
            close_list()
            out.append(f"<blockquote><p>{inline_markup(quote.group(1))}</p></blockquote>")
            continue

        unordered = re.match(r"^\s*[-+*]\s+(.*)$", line)
        ordered = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if unordered or ordered:
            flush_paragraph()
            wanted = "ul" if unordered else "ol"
            if list_type != wanted:
                close_list()
                list_type = wanted
                out.append(f"<{list_type}>")
            text = (unordered or ordered).group(1)
            out.append(f"<li>{inline_markup(text)}</li>")
            continue

        paragraph.append(line)

    if in_code:
        flush_code()
    if in_math:
        flush_math()
    flush_paragraph()
    close_list()
    return "\n".join(out)


def tag_filename(tag: str) -> str:
    digest = hashlib.sha1(tag.encode("utf-8")).hexdigest()[:10]
    return f"tag-{digest}.html"


def load_articles(root: Path) -> list[dict]:
    article_dir = root / "articles"
    articles = []
    for path in sorted(article_dir.glob("*.md"), key=lambda x: x.name.casefold()):
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(raw)
        title = str(meta.get("title") or path.stem.replace("_", " ").title())
        tags = meta.get("tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)]
        articles.append({
            "source": path,
            "slug": path.stem,
            "title": title,
            "tags": [str(x) for x in tags if str(x).strip()],
            "body_html": markdown_to_html(body),
        })
    return articles


def sidebar_html(articles: list[dict], current_slug: str | None, depth: int) -> str:
    prefix = "../" if depth else ""
    article_links = []
    for article in articles:
        href = f"{article['slug']}.html" if depth else f"notes/{article['slug']}.html"
        current = ' aria-current="page"' if current_slug == article["slug"] else ""
        article_links.append(
            f'<li><a class="sidebar-link" href="{href}"{current}>{esc(article["title"])}</a></li>'
        )

    tags = sorted({tag for article in articles for tag in article["tags"]}, key=lambda x: x.casefold())
    tag_links = []
    for tag in tags:
        href = tag_filename(tag) if depth else f"notes/{tag_filename(tag)}"
        tag_links.append(f'<li><a class="sidebar-link" href="{href}">{esc(tag)}</a></li>')

    tag_block = "\n".join(tag_links) if tag_links else "<li>タグなし</li>"
    article_block = "\n".join(article_links) if article_links else "<li>記事はありません</li>"
    home = f"{prefix}index.html"
    blog = f"{prefix}blog.html"

    return f"""<aside class="sidebar" id="sidebar" aria-label="ブログナビゲーション">
      <h2>タグ</h2>
      <ul>
        <li><a class="sidebar-link" href="{blog}">すべて</a></li>
        {tag_block}
      </ul>

      <h2>記事一覧</h2>
      <ul>
        {article_block}
      </ul>

      <footer>
        <a href="{home}" class="no-underline">← ホームへ戻る</a>
      </footer>
    </aside>"""


def page_shell(
    *,
    title: str,
    content: str,
    articles: list[dict],
    current_slug: str | None,
    depth: int,
    canonical_rel: str,
) -> str:
    prefix = "../" if depth else ""
    css = f"{prefix}blog.css"
    js = f"{prefix}blog.js"
    canonical = "https://srin728.github.io/" + canonical_rel
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Rin Saito's notes on algorithms, optimization, and related topics.">
  <meta name="theme-color" content="#0c7bbb">
  <link rel="canonical" href="{esc(canonical)}">
  <title>{esc(title)} — Rin's Notes</title>
  <link rel="stylesheet" href="{css}">
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
  <script src="{js}" defer></script>
</head>
<body>
  <button id="hamburger" type="button" aria-controls="sidebar"
    aria-expanded="false" aria-label="メニューを開く">☰</button>

  <div class="container">
    {sidebar_html(articles, current_slug, depth)}
    <main class="content">
      {content}
    </main>
  </div>
</body>
</html>
"""


def render_article(article: dict, articles: list[dict], depth: int = 1) -> str:
    tags = " ".join(f'<span class="tag">{esc(tag)}</span>' for tag in article["tags"])
    content = f"""<article>
      <h1>{esc(article["title"])}</h1>
      <div class="tags">{tags}</div>
      {article["body_html"]}
    </article>"""
    return page_shell(
        title=article["title"],
        content=content,
        articles=articles,
        current_slug=article["slug"],
        depth=depth,
        canonical_rel="blog.html" if depth == 0 else f"notes/{article['slug']}.html",
    )


def render_tag_page(tag: str, articles: list[dict]) -> str:
    selected = [a for a in articles if tag in a["tags"]]
    rows = "\n".join(
        f'<li><a href="{a["slug"]}.html">{esc(a["title"])}</a></li>' for a in selected
    )
    content = f"""<section>
      <h1>Tag: {esc(tag)}</h1>
      <ul>{rows}</ul>
    </section>"""
    return page_shell(
        title=f"Tag: {tag}",
        content=content,
        articles=articles,
        current_slug=None,
        depth=1,
        canonical_rel=f"notes/{tag_filename(tag)}",
    )


def expected_outputs(root: Path) -> dict[Path, str]:
    articles = load_articles(root)
    outputs = {}
    generated = root / GENERATED_DIR

    if articles:
        first = articles[0]
        outputs[root / "blog.html"] = render_article(first, articles, depth=0)
    else:
        outputs[root / "blog.html"] = page_shell(
            title="Rin's Notes",
            content="<h1>Rin's Notes</h1><p>記事はまだありません。</p>",
            articles=[],
            current_slug=None,
            depth=0,
            canonical_rel="blog.html",
        )

    for article in articles:
        outputs[generated / f"{article['slug']}.html"] = render_article(article, articles, depth=1)

    tags = sorted({tag for article in articles for tag in article["tags"]}, key=lambda x: x.casefold())
    for tag in tags:
        outputs[generated / tag_filename(tag)] = render_tag_page(tag, articles)

    manifest = sorted(path.name for path in outputs if path.parent == generated)
    outputs[generated / MANIFEST_NAME] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    return outputs


def clean_stale(root: Path, expected: dict[Path, str]) -> None:
    generated = root / GENERATED_DIR
    manifest_path = generated / MANIFEST_NAME
    if not manifest_path.exists():
        return
    try:
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    wanted = {path.name for path in expected if path.parent == generated}
    for name in old:
        if name not in wanted:
            candidate = generated / name
            if candidate.is_file():
                candidate.unlink()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build static blog pages from articles/*.md")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--check", action="store_true", help="fail if generated blog pages are stale")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    outputs = expected_outputs(root)

    stale = []
    if not args.check:
        clean_stale(root, outputs)

    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(str(path.relative_to(root)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            print(f"generated {path.relative_to(root)}")

    if args.check:
        manifest_path = root / GENERATED_DIR / MANIFEST_NAME
        if manifest_path.exists():
            try:
                old = set(json.loads(manifest_path.read_text(encoding="utf-8")))
                wanted = {path.name for path in outputs if path.parent == root / GENERATED_DIR}
                extra = old - wanted
                stale.extend(str(Path(GENERATED_DIR) / x) for x in sorted(extra))
            except (json.JSONDecodeError, OSError):
                stale.append(str(manifest_path.relative_to(root)))
    if stale:
        print("stale generated blog file(s): " + ", ".join(stale), file=sys.stderr)
        print("run: python scripts/build_blog.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
