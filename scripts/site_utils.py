#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MEANINGFUL_SOURCE_PATHS = (
    "lang",
    "data",
    "articles",
    "style.css",
    "script.js",
    "blog.css",
    "blog.js",
    "supplement.css",
    "scripts/build_homepage.py",
    "scripts/build_blog.py",
    "scripts/build_supplement.py",
    "scripts/build_site_meta.py",
    "scripts/site_utils.py",
)

_MONTHS_EN = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _parse_iso_date(value: str) -> date | None:
    value = value.strip()
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def latest_site_date(root: Path) -> date:
    """Return the latest meaningful site-update date.

    Priority:
    1. SITE_LAST_UPDATED=YYYY-MM-DD, useful for reproducible builds.
    2. The latest Git commit that touched a source file rather than a generated page.
    3. Today's date in Asia/Tokyo when Git metadata is unavailable.
    """
    override = os.environ.get("SITE_LAST_UPDATED")
    if override:
        parsed = _parse_iso_date(override)
        if parsed is None:
            raise ValueError("SITE_LAST_UPDATED must use YYYY-MM-DD")
        return parsed

    cmd = [
        "git", "log", "-1", "--format=%cs", "--",
        *MEANINGFUL_SOURCE_PATHS,
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            parsed = _parse_iso_date(result.stdout.strip())
            if parsed is not None:
                return parsed
    except OSError:
        pass

    return datetime.now(ZoneInfo("Asia/Tokyo")).date()


def format_date_en(value: date) -> str:
    return f"{_MONTHS_EN[value.month - 1]} {value.day}, {value.year}"


def format_date_ja(value: date) -> str:
    return f"{value.year}年{value.month}月{value.day}日"
