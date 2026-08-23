#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> int:
    package_root = Path(__file__).resolve().parent
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    patch = package_root / "patch"

    required = [
        repo / ".github" / "workflows" / "build-static-pages.yml",
        repo / "scripts" / "build_homepage.py",
        repo / "scripts" / "build_blog.py",
        repo / "scripts" / "build_supplement.py",
        repo / "scripts" / "build_site_meta.py",
        repo / "scripts" / "site_utils.py",
    ]
    missing = [p for p in required if not p.exists()]
    if missing:
        print("This does not look like the current srin728.github.io repository.", file=sys.stderr)
        for p in missing:
            print(f"  missing: {p}", file=sys.stderr)
        return 1

    for src in patch.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(patch)
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"updated {rel}")

    print()
    print("CI fix applied.")
    print("Review with: git diff")
    print('Then commit and push: git add -A && git commit -m "Fix static build CI" && git push')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
