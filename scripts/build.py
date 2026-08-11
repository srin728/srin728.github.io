#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
DATA_DIR = ROOT / "data"
BIB_DIR = ROOT / "bib"
OUT = ROOT / "_site"


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def is_escaped(text: str, pos: int) -> bool:
    slashes = 0
    i = pos - 1
    while i >= 0 and text[i] == "\\":
        slashes += 1
        i -= 1
    return slashes % 2 == 1


def find_matching(text: str, start: int, opener: str, closer: str) -> int:
    depth = 0
    in_quote = False
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '"' and not is_escaped(text, i):
            in_quote = not in_quote
        if in_quote:
            continue
        if ch == opener and not is_escaped(text, i):
            depth += 1
        elif ch == closer and not is_escaped(text, i):
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"Unbalanced BibTeX entry starting at offset {start}")


def split_top_level(text: str, separator: str = ',') -> list[str]:
    parts = []
    start = 0
    brace = paren = 0
    in_quote = False
    for i, ch in enumerate(text):
        if ch == '"' and not is_escaped(text, i):
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if ch == '{' and not is_escaped(text, i):
            brace += 1
        elif ch == '}' and not is_escaped(text, i):
            brace -= 1
        elif ch == '(' and not is_escaped(text, i):
            paren += 1
        elif ch == ')' and not is_escaped(text, i):
            paren -= 1
        elif ch == separator and brace == 0 and paren == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def split_assignment(text: str) -> tuple[str, str] | None:
    brace = paren = 0
    in_quote = False
    for i, ch in enumerate(text):
        if ch == '"' and not is_escaped(text, i):
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if ch == '{' and not is_escaped(text, i): brace += 1
        elif ch == '}' and not is_escaped(text, i): brace -= 1
        elif ch == '(' and not is_escaped(text, i): paren += 1
        elif ch == ')' and not is_escaped(text, i): paren -= 1
        elif ch == '=' and brace == 0 and paren == 0:
            return text[:i].strip(), text[i+1:].strip()
    return None


def unwrap(value: str) -> str:
    value = value.strip().rstrip(',').strip()
    if len(value) >= 2 and value[0] == '{' and value[-1] == '}':
        try:
            if find_matching(value, 0, '{', '}') == len(value) - 1:
                return value[1:-1].strip()
        except ValueError:
            pass
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1].strip()
    return value


def parse_bibtex(text: str) -> list[dict]:
    entries = []
    i = 0
    while True:
        at = text.find('@', i)
        if at < 0:
            break
        m = re.match(r'@\s*([A-Za-z]+)\s*([\{\(])', text[at:])
        if not m:
            i = at + 1
            continue
        kind = m.group(1).lower()
        opener = m.group(2)
        closer = '}' if opener == '{' else ')'
        start = at + m.end() - 1
        end = find_matching(text, start, opener, closer)
        raw = text[at:end+1].strip()
        body = text[start+1:end].strip()
        i = end + 1
        if kind in {'comment', 'string', 'preamble'}:
            continue
        chunks = split_top_level(body)
        if not chunks:
            continue
        key = chunks[0].strip()
        fields = {}
        for chunk in chunks[1:]:
            assignment = split_assignment(chunk)
            if assignment:
                name, value = assignment
                fields[name.lower()] = unwrap(value)
        entries.append({'type': kind, 'key': key, 'fields': fields, 'raw': raw})
    return entries


ACCENTS = {
    "'": {'a':'á','e':'é','i':'í','o':'ó','u':'ú','y':'ý','A':'Á','E':'É','I':'Í','O':'Ó','U':'Ú','Y':'Ý','c':'ć','C':'Ć','n':'ń','N':'Ń'},
    '`': {'a':'à','e':'è','i':'ì','o':'ò','u':'ù','A':'À','E':'È','I':'Ì','O':'Ò','U':'Ù'},
    '"': {'a':'ä','e':'ë','i':'ï','o':'ö','u':'ü','y':'ÿ','A':'Ä','E':'Ë','I':'Ï','O':'Ö','U':'Ü'},
    '^': {'a':'â','e':'ê','i':'î','o':'ô','u':'û','A':'Â','E':'Ê','I':'Î','O':'Ô','U':'Û'},
    '~': {'a':'ã','n':'ñ','o':'õ','A':'Ã','N':'Ñ','O':'Õ'},
}

SPECIAL = {
    r'\\&': '&', r'\\%': '%', r'\\_': '_', r'\\#': '#',
    r'\\ss': 'ß', r'\\ae': 'æ', r'\\AE': 'Æ', r'\\oe': 'œ', r'\\OE': 'Œ',
    r'\\o': 'ø', r'\\O': 'Ø', r'\\l': 'ł', r'\\L': 'Ł',
    r'\\textendash': '–', r'\\textemdash': '—', r'\\LaTeX': 'LaTeX', r'\\TeX': 'TeX',
}


URL_ESCAPES = {
    r'\_': '_',
    r'\%': '%',
    r'\#': '#',
    r'\&': '&',
    r'\$': '$',
    r'\(': '(',
    r'\)': ')',
    r'\:': ':',
}


def latex_to_text(value: str) -> str:
    s = value
    for token, repl in SPECIAL.items():
        s = s.replace(token, repl)
    # Common accent commands, allowing optional braces around the letter.
    for accent, table in ACCENTS.items():
        for letter, repl in table.items():
            patterns = [
                rf"\\{re.escape(accent)}\{{{re.escape(letter)}\}}",
                rf"\{{\\{re.escape(accent)}{re.escape(letter)}\}}",
                rf"\\{re.escape(accent)}{re.escape(letter)}",
            ]
            for pattern in patterns:
                s = re.sub(pattern, repl, s)
    # Preserve the content of common formatting commands.
    s = re.sub(r'\\(?:emph|textit|textbf|texttt|textsc|mathrm|mathbf|mathit)\s*\{([^{}]*)\}', r'\1', s)
    s = s.replace('~', ' ')
    # Braces are grouping in titles/names; remove the remaining simple ones for display.
    s = s.replace('{', '').replace('}', '')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def normalize_doi(value: str) -> str:
    r"""Return a DOI suffix suitable for display and https://doi.org links.

    BibTeX exported from TeX-oriented sources sometimes escapes URL-safe
    characters (especially ``_``) as ``\_``.  Some collections also contain
    the malformed ``/\_`` sequence where the slash is not part of the DOI.
    Normalize these cases here so maintainers do not need to edit the .bib
    files by hand.
    """
    s = value.strip()
    s = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', s, flags=re.IGNORECASE)

    # Known malformed form seen in exported BibTeX, e.g.
    # 10.1007/978-3-031-38906-1/\_8 -> 10.1007/978-3-031-38906-1_8
    s = s.replace(r'/\_', '_')
    for token, repl in URL_ESCAPES.items():
        s = s.replace(token, repl)

    # Braces may be used only for TeX grouping in URL-like fields.
    s = s.replace('{', '').replace('}', '').strip()
    return s


def extract_markdown_link_target(value: str) -> str:
    """Return the URL from a Markdown-style ``[label](target)`` value.

    A few hand-maintained BibTeX files contain Markdown copied from rendered
    text instead of a plain URL.  Keep accepting those files so the title link
    does not become a literal ``[https://...](https://...)`` href.
    """
    s = value.strip()
    if not s.startswith('['):
        return s

    sep = s.find('](')
    if sep <= 1 or not s.endswith(')'):
        return s

    label = s[1:sep].strip()
    target = s[sep + 2:-1].strip()
    return target or label


def normalize_url(value: str) -> str:
    r"""Normalize URL fields copied from TeX, DBLP, or Markdown.

    Supported cleanup includes TeX escapes such as ``\_`` and ``\(``, and
    accidental Markdown link syntax such as ``[https://a](https://a)``.
    """
    s = extract_markdown_link_target(value)
    if not s:
        return ''

    # Detect DOI URLs before the generic TeX-unescape pass.  This preserves
    # normalize_doi's special repair for the malformed ``/\_`` sequence.
    doi_match = re.match(r'^https?://(?:dx\.)?doi\.org/(.+)$', s, flags=re.IGNORECASE)
    if doi_match:
        doi = normalize_doi(doi_match.group(1))
        return f"https://doi.org/{doi}" if doi else ''

    for token, repl in URL_ESCAPES.items():
        s = s.replace(token, repl)
    return s.replace('{', '').replace('}', '').strip()



NON_RESOLVING_DOI_PREFIXES = (
    # Crossref documents 10.5555 as a test prefix.  Values under this prefix
    # are sometimes used as publisher/database identifiers (notably by ACM
    # DL), but doi.org resolution is not reliable enough to use as the site's
    # primary link.  Prefer the BibTeX url field when it is available.
    "10.5555/",
)


def doi_resolver_url(doi: str) -> str:
    """Return a doi.org URL only for DOI prefixes we treat as resolvable."""
    normalized = (doi or '').strip()
    if not normalized:
        return ''
    lowered = normalized.casefold()
    if any(lowered.startswith(prefix) for prefix in NON_RESOLVING_DOI_PREFIXES):
        return ''
    return f"https://doi.org/{normalized}"


def preferred_paper_url(doi: str, url: str) -> str:
    """Return the best external paper URL.

    A normal DOI is preferred over ``url``.  For known non-resolving/test DOI
    prefixes such as 10.5555, the BibTeX ``url`` is preferred instead so that
    title clicks do not lead to a broken doi.org resolution.
    """
    return doi_resolver_url(doi) or url

def is_survey_bib(path: Path) -> bool:
    """Recognize either bib/survey/*.bib or bib/survey.bib as survey data."""
    return path.parent.name.casefold() == 'survey' or (
        path.parent == BIB_DIR and path.stem.casefold() == 'survey'
    )


def normalize_dblp_author_name(name: str) -> str:
    """Remove DBLP homonym-disambiguation suffixes from displayed names.

    DBLP may append a four-digit identifier to an author's name, for example
    ``Lu Liu 0030``.  It is useful inside DBLP's data model but should not be
    shown as part of the human-readable author name on this site.
    """
    return re.sub(r'\s+\d{4}$', '', name).strip()


def split_authors(author_field: str) -> list[str]:
    # Adequate for normal BibTeX author lists; corporate authors in braces remain one item.
    raw = re.split(r'\s+and\s+', author_field.strip()) if author_field else []
    result = []
    for name in raw:
        name = latex_to_text(name.strip())
        if name.count(',') == 1:
            last, first = [x.strip() for x in name.split(',', 1)]
            if first and last:
                name = f"{first} {last}"
        name = normalize_dblp_author_name(name)
        result.append(name)
    return [x for x in result if x]


def safe_bib_filename(key: str) -> str:
    """Return a portable download filename for one BibTeX entry."""
    name = re.sub(r'[^A-Za-z0-9._-]+', '_', key).strip('._-')
    return f"{name or 'paper'}.bib"


def split_tags(value: str) -> list[str]:
    if not value:
        return []
    items = [latex_to_text(x).strip() for x in re.split(r'[;,]', value)]
    seen = set()
    out = []
    for item in items:
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def first_page_number(value: str) -> int | None:
    """Extract the first numeric page component for proceedings-order sorting."""
    if not value:
        return None
    text = latex_to_text(value)
    match = re.search(r'\d+', text)
    return int(match.group(0)) if match else None


def git_show_text(revision: str, path: str) -> str | None:
    """Read one repository file at a Git revision; return None if absent."""
    try:
        cp = subprocess.run(
            ['git', '-C', str(ROOT), 'show', f'{revision}:{path}'],
            check=False, capture_output=True, text=True, timeout=10,
        )
        return cp.stdout if cp.returncode == 0 else None
    except Exception:
        return None


def bib_entry_map(text: str | None) -> dict[str, str]:
    if text is None:
        return {}
    try:
        return {entry['key']: entry['raw'].strip() for entry in parse_bibtex(text)}
    except Exception:
        return {}


def describe_bib_path(path_text: str) -> str:
    """Return a concise collection label such as ``SODA 2025``."""
    path = Path(path_text)
    parts = path.parts
    if len(parts) >= 2 and parts[0].casefold() == 'bib':
        if (len(parts) >= 2 and parts[1].casefold() == 'survey') or path.stem.casefold() == 'survey':
            m = re.search(r'(19|20)\d{2}', path.name)
            return f"Surveys {m.group(0)}" if m else 'Surveys'
        conference = parts[1] if len(parts) >= 3 else path.stem
        m = re.search(r'(19|20)\d{2}', path.name)
        return f"{conference} {m.group(0)}" if m else conference
    return path.stem


def git_bib_update_events(limit: int = 30) -> list[dict]:
    """Build recent bibliography updates from Git commits touching ``bib/``.

    File mtimes are unreliable in CI/checkouts.  Git history records the actual
    maintenance events, so the home-page update feed is derived from commits
    whenever a full repository history is available.  Entry-key and raw-entry
    comparisons provide useful added/removed/metadata-change counts.
    """
    try:
        probe = subprocess.run(
            ['git', '-C', str(ROOT), 'rev-parse', '--is-inside-work-tree'],
            check=False, capture_output=True, text=True, timeout=5,
        )
        if probe.returncode != 0 or probe.stdout.strip() != 'true':
            return []
        cp = subprocess.run(
            ['git', '-C', str(ROOT), 'log', '--date=short', '--format=%H%x09%ad%x09%s', '--', 'bib'],
            check=False, capture_output=True, text=True, timeout=15,
        )
        if cp.returncode != 0:
            return []
    except Exception:
        return []

    events = []
    for line in cp.stdout.splitlines():
        if len(events) >= limit:
            break
        parts = line.split('\t', 2)
        if len(parts) < 2:
            continue
        commit, date = parts[:2]
        subject = parts[2].strip() if len(parts) > 2 else ''
        try:
            changed = subprocess.run(
                ['git', '-C', str(ROOT), 'diff-tree', '--root', '--no-commit-id', '--name-only', '-r', commit, '--', 'bib'],
                check=False, capture_output=True, text=True, timeout=10,
            )
            files = [x.strip() for x in changed.stdout.splitlines() if x.strip().lower().endswith('.bib')]
            if not files:
                continue
            parents = subprocess.run(
                ['git', '-C', str(ROOT), 'rev-list', '--parents', '-n', '1', commit],
                check=False, capture_output=True, text=True, timeout=5,
            ).stdout.strip().split()
            parent = parents[1] if len(parents) > 1 else None
        except Exception:
            continue

        added = removed = modified = 0
        labels = []
        targets = []
        for file_path in files:
            label = describe_bib_path(file_path)
            labels.append(label)
            path_obj = Path(file_path)
            parts_obj = path_obj.parts
            if len(parts_obj) >= 2 and parts_obj[0].casefold() == 'bib':
                if parts_obj[1].casefold() == 'survey' or path_obj.stem.casefold() == 'survey':
                    targets.append({'collection': 'survey', 'label': label})
                elif len(parts_obj) >= 3:
                    year_match = re.search(r'(19|20)\d{2}', path_obj.name)
                    targets.append({
                        'collection': 'conference',
                        'conference': parts_obj[1],
                        'year': year_match.group(0) if year_match else '',
                        'label': label,
                    })
            new_entries = bib_entry_map(git_show_text(commit, file_path))
            old_entries = bib_entry_map(git_show_text(parent, file_path)) if parent else {}
            new_keys = set(new_entries)
            old_keys = set(old_entries)
            added += len(new_keys - old_keys)
            removed += len(old_keys - new_keys)
            modified += sum(new_entries[k] != old_entries[k] for k in new_keys & old_keys)

        labels = list(dict.fromkeys(labels))
        targets = list({(t.get('collection',''), t.get('conference',''), t.get('year','')): t for t in targets}.values())
        if len(labels) == 1:
            title = f"Bibliography update: {labels[0]}"
        else:
            title = f"Bibliography update: {len(labels)} collections"

        changes = []
        if added:
            changes.append(f"+{added} entr{'y' if added == 1 else 'ies'}")
        if removed:
            changes.append(f"-{removed} entr{'y' if removed == 1 else 'ies'}")
        if modified:
            changes.append(f"{modified} metadata change{'s' if modified != 1 else ''}")
        if not changes:
            changes.append(f"{len(files)} BibTeX file{'s' if len(files) != 1 else ''} changed")

        shown_labels = ', '.join(labels[:6]) + (f" +{len(labels)-6} more" if len(labels) > 6 else '')
        text_parts = ['; '.join(changes), shown_labels]
        if subject:
            text_parts.append(subject)
        events.append({
            'date': date,
            'title': title,
            'text': ' · '.join(x for x in text_parts if x),
            'commit': commit[:7],
            'kind': 'git',
            'targets': targets,
        })
    return events


def git_date(path: Path) -> str:
    try:
        rel = path.relative_to(ROOT)
        cp = subprocess.run(
            ['git', '-C', str(ROOT), 'log', '-1', '--format=%cs', '--', str(rel)],
            check=False, capture_output=True, text=True, timeout=5,
        )
        date = cp.stdout.strip()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
            return date
    except Exception:
        pass
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).date().isoformat()


def infer_year(path: Path, fields: dict) -> str:
    raw = latex_to_text(fields.get('year', '')).strip()
    m = re.search(r'(19|20)\d{2}', raw)
    if m:
        return m.group(0)
    m = re.search(r'_(19|20)\d{2}(?:[^0-9]|$)', path.stem + '_')
    return m.group(0).strip('_') if m else 'Unknown'


COVERAGE_STATUSES = {'complete', 'partial', 'planned'}


def parse_bib_file(path: Path) -> list[dict]:
    """Parse one BibTeX file and report a useful line on malformed input."""
    text = path.read_text(encoding='utf-8-sig')
    try:
        return parse_bibtex(text)
    except Exception as exc:
        offset = None
        match = re.search(r'offset\s+(\d+)', str(exc))
        if match:
            offset = int(match.group(1))
        if offset is not None:
            line_no = text.count('\n', 0, min(offset, len(text))) + 1
            line_text = text.splitlines()[line_no - 1].strip() if text.splitlines() else ''
            detail = f"entry starting at line {line_no}"
            if line_text:
                detail += f": {line_text[:180]}"
        else:
            detail = str(exc)
        raise RuntimeError(f"Failed to parse {path.relative_to(ROOT)} ({detail})") from exc


def normal_bib_files() -> list[Path]:
    return sorted(p for p in BIB_DIR.glob('*/*.bib') if not is_survey_bib(p))


def all_bib_files() -> list[Path]:
    return sorted({*BIB_DIR.glob('*/*.bib'), *(p for p in BIB_DIR.glob('*.bib') if is_survey_bib(p))})


def missing_conference_definitions(conferences, conference_names: dict) -> list[str]:
    return sorted({str(c) for c in conferences if c and c not in conference_names}, key=str.casefold)


def normalize_coverage_status(value) -> str | None:
    status = str(value or '').strip().casefold().replace('-', '_').replace(' ', '_')
    aliases = {
        'done': 'complete', 'surveyed': 'complete', 'completed': 'complete',
        'in_progress': 'partial', 'incomplete': 'partial',
        'todo': 'planned', 'not_surveyed': 'planned', 'not_yet_surveyed': 'planned',
    }
    status = aliases.get(status, status)
    return status if status in COVERAGE_STATUSES else None


def apply_coverage_overrides(coverage: dict[tuple[str, str], dict], overrides: dict) -> None:
    """Apply data/coverage.json overrides using {conference: {year: status}}."""
    if not isinstance(overrides, dict):
        return
    for conference, years in overrides.items():
        if not isinstance(years, dict):
            continue
        for year, raw_status in years.items():
            status = normalize_coverage_status(raw_status)
            if not status:
                print(f"WARNING: ignoring unknown coverage status {raw_status!r} for {conference} {year}", file=sys.stderr)
                continue
            key = (str(conference), str(year))
            item = coverage.setdefault(key, {'conference': str(conference), 'year': str(year), 'source': 'override'})
            item['status'] = status
            item['source'] = 'override' if item.get('source') != 'bib' else 'bib+override'


def coverage_sort_key(item: dict):
    year = str(item.get('year', ''))
    return (str(item.get('conference', '')).casefold(), -(int(year) if year.isdigit() else -1), year)


def version_output_assets(out_dir: Path) -> None:
    """Add content hashes to CSS/JS references so Pages serves fresh code."""
    index = out_dir / 'index.html'
    if not index.exists():
        return
    html = index.read_text(encoding='utf-8')
    for relative in ('assets/styles.css', 'assets/app.js'):
        asset = out_dir / relative
        if not asset.exists():
            continue
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
        html = html.replace(relative, f'{relative}?v={digest}')
    index.write_text(html, encoding='utf-8')


def build():
    config = load_json(DATA_DIR / 'site.config.json', {})
    conference_names = load_json(DATA_DIR / 'conferences.json', {})
    news = load_json(DATA_DIR / 'news.json', [])
    coverage_overrides = load_json(DATA_DIR / 'coverage.json', {})

    papers = []
    surveys = []
    source_updates = []
    entry_downloads = []
    coverage = {}
    bib_files = all_bib_files()
    conference_folders = sorted({p.parent.name for p in bib_files if not is_survey_bib(p)}, key=str.casefold)
    defined_sources = set(conference_folders) | (set(coverage_overrides) if isinstance(coverage_overrides, dict) else set())
    missing_conferences = missing_conference_definitions(defined_sources, conference_names)
    if missing_conferences:
        print('WARNING: conference folders missing from data/conferences.json: ' + ', '.join(missing_conferences), file=sys.stderr)

    for path in bib_files:
        is_survey = is_survey_bib(path)
        conference = '' if is_survey else path.parent.name
        collection = 'survey' if is_survey else 'conference'
        entries = parse_bib_file(path)

        year_counts = Counter()
        for entry_index, entry in enumerate(entries):
            f = entry['fields']
            year = infer_year(path, f)
            year_counts[year] += 1
            authors = split_authors(f.get('author', ''))
            tags = split_tags(';'.join(x for x in (f.get('tags', ''), f.get('keywords', '')) if x))
            paper_id = hashlib.sha1(f"{collection}\0{conference}\0{year}\0{entry['key']}".encode()).hexdigest()[:12]
            doi = normalize_doi(f.get('doi', ''))
            url = normalize_url(f.get('url', ''))
            primary_url = preferred_paper_url(doi, url)
            record = {
                'id': paper_id,
                'key': entry['key'],
                'type': entry['type'],
                'title': latex_to_text(f.get('title', entry['key'])),
                'authors': authors,
                'authorText': ', '.join(authors),
                'year': year,
                'conference': conference,
                'conferenceName': conference_names.get(conference, conference) if conference else '',
                'collection': collection,
                'booktitle': latex_to_text(f.get('booktitle', '')),
                'pages': latex_to_text(f.get('pages', '')),
                'pageStart': first_page_number(f.get('pages', '')),
                'sourceOrder': entry_index,
                'sourceBib': str(path.relative_to(ROOT)).replace('\\', '/'),
                'doi': doi,
                'url': url,
                'primaryUrl': primary_url,
                'tags': tags,
                'sourcePath': f'bib-entry/{paper_id}.bib',
                'sourceFileName': safe_bib_filename(entry['key']),
            }
            entry_downloads.append((paper_id, entry['raw']))
            if config.get('includeRawBibTeX', False):
                record['bibtex'] = entry['raw']
            (surveys if is_survey else papers).append(record)

        if not is_survey:
            covered_years = set(year_counts)
            if not covered_years:
                inferred = infer_year(path, {})
                if inferred != 'Unknown':
                    covered_years.add(inferred)
            for covered_year in covered_years:
                coverage[(conference, covered_year)] = {
                    'conference': conference,
                    'year': covered_year,
                    'status': 'complete',
                    'source': 'bib',
                }

        changed = git_date(path)
        if year_counts:
            for year, count in year_counts.items():
                source_updates.append({
                    'date': changed,
                    'conference': conference,
                    'collection': collection,
                    'year': year,
                    'paperCount': count,
                    'file': str(path.relative_to(ROOT)).replace('\\', '/'),
                })
        else:
            source_updates.append({
                'date': changed,
                'conference': conference,
                'collection': collection,
                'year': '',
                'paperCount': 0,
                'file': str(path.relative_to(ROOT)).replace('\\', '/'),
            })

    apply_coverage_overrides(coverage, coverage_overrides)

    papers.sort(key=lambda p: (-(int(p['year']) if p['year'].isdigit() else -1), p['conference'].casefold(), p['title'].casefold()))
    surveys.sort(key=lambda p: (-(int(p['year']) if p['year'].isdigit() else -1), p['title'].casefold()))

    year_counts = Counter(p['year'] for p in papers)
    year_conferences = defaultdict(set)
    conference_counts = Counter(p['conference'] for p in papers)
    tag_counts = Counter()
    for p in papers:
        year_conferences[p['year']].add(p['conference'])
        for t in p['tags']:
            tag_counts[t] += 1
    for p in surveys:
        for t in p['tags']:
            tag_counts[t] += 1

    coverage_year_conferences = defaultdict(set)
    coverage_conference_years = defaultdict(set)
    complete_by_year = Counter()
    partial_by_year = Counter()
    complete_by_conference = Counter()
    partial_by_conference = Counter()
    for (conference, year), item in coverage.items():
        status = item.get('status', 'complete')
        coverage_year_conferences[year].add(conference)
        coverage_conference_years[conference].add(year)
        if status == 'complete':
            complete_by_year[year] += 1
            complete_by_conference[conference] += 1
        elif status == 'partial':
            partial_by_year[year] += 1
            partial_by_conference[conference] += 1

    all_year_values = set(year_counts) | set(coverage_year_conferences)
    all_conference_values = set(conference_counts) | set(coverage_conference_years)
    years = sorted(all_year_values, key=lambda y: (str(y).isdigit(), int(y) if str(y).isdigit() else -1), reverse=True)
    conferences = sorted(all_conference_values, key=lambda c: c.casefold())
    tags = sorted(tag_counts, key=lambda t: (-tag_counts[t], t.casefold()))

    coverage_records = []
    for (conference, year), item in coverage.items():
        record = dict(item)
        record['count'] = sum(1 for p in papers if p['conference'] == conference and p['year'] == year)
        coverage_records.append(record)
    coverage_records.sort(key=coverage_sort_key)

    payload = {
        'generatedAt': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'site': {
            'siteTitle': config.get('siteTitle', 'Parameterized Complexity Conference Papers'),
            'shortTitle': config.get('shortTitle', 'PC Papers'),
            'siteSubtitle': config.get('siteSubtitle', ''),
            'contactUrl': config.get('contactUrl', ''),
            'repositoryUrl': config.get('repositoryUrl', ''),
            'homeRecentPapers': config.get('homeRecentPapers', 12),
            'homeRecentUpdates': config.get('homeRecentUpdates', 8),
        },
        'conferenceNames': conference_names,
        'news': news,
        'sourceUpdates': git_bib_update_events(max(20, int(config.get('homeRecentUpdates', 8)) * 4))
            or sorted(source_updates, key=lambda x: (x['date'], x.get('file', '')), reverse=True),
        'coverage': coverage_records,
        'facets': {
            'paperCount': len(papers),
            'surveyCount': len(surveys),
            'yearCount': len(years),
            'conferenceCount': len(conferences),
            'tagCount': len(tag_counts),
            'years': [
                {'value': y, 'count': year_counts[y], 'conferences': len(year_conferences[y]),
                 'coveredConferences': len(coverage_year_conferences[y]),
                 'complete': complete_by_year[y], 'partial': partial_by_year[y]}
                for y in years
            ],
            'conferences': [
                {'value': c, 'label': conference_names.get(c, c), 'count': conference_counts[c],
                 'coveredYears': len(coverage_conference_years[c]),
                 'complete': complete_by_conference[c], 'partial': partial_by_conference[c]}
                for c in conferences
            ],
            'tags': [{'value': t, 'count': tag_counts[t]} for t in tags],
        },
        'papers': papers,
        'surveys': surveys,
    }

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE_DIR, OUT)
    version_output_assets(OUT)
    (OUT / 'data').mkdir(parents=True, exist_ok=True)
    (OUT / 'data' / 'publications.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    # Generate one downloadable BibTeX file per paper.  The public paper card
    # links here instead of linking to the conference-wide source .bib file.
    entry_dir = OUT / 'bib-entry'
    entry_dir.mkdir(parents=True, exist_ok=True)
    for paper_id, raw_bibtex in entry_downloads:
        (entry_dir / f'{paper_id}.bib').write_text(raw_bibtex.rstrip() + '\n', encoding='utf-8')

    # Keep the original source files in the built site for provenance/archive
    # purposes, but paper cards no longer download these multi-entry files.
    if BIB_DIR.exists():
        shutil.copytree(BIB_DIR, OUT / 'bib', dirs_exist_ok=True)
    # Prevent Jekyll processing when GitHub Pages receives the built directory.
    (OUT / '.nojekyll').write_text('', encoding='utf-8')
    print(f"Built {len(papers)} conference papers and {len(surveys)} survey papers from {len(bib_files)} BibTeX files into {OUT}")


if __name__ == '__main__':
    build()
