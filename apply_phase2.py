#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATCH = HERE / "patch"

REQUIRED = ["lang/en.json", "lang/ja.json"]
INSTALL = [
    "style.css",
    "script.js",
    "data/homepage.json",
    "scripts/build_homepage.py",
    "tests/test_homepage.py",
]


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    missing = [str(target / p) for p in REQUIRED if not (target / p).is_file()]
    if missing:
        print("This does not look like the srin728.github.io repository.")
        for path in missing:
            print("  missing:", path)
        return 2

    for rel in INSTALL:
        src = PATCH / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print("installed", rel)

    result = subprocess.run(
        [sys.executable, str(target / "scripts" / "build_homepage.py"), "--root", str(target)],
        cwd=target,
    )
    if result.returncode:
        return result.returncode

    print("\nPhase 2 applied successfully.")
    print("Generated: index.html, ja.html")
    print("Run tests with:")
    print("  python -m unittest tests.test_homepage")
    print("Then inspect:")
    print("  git diff")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
