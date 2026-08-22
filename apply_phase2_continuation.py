#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd):
    print("+", " ".join(str(x) for x in cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    if len(sys.argv) > 2:
        print("usage: python apply_phase2_continuation.py [repository-root]", file=sys.stderr)
        return 2

    package_root = Path(__file__).resolve().parent
    patch_root = package_root / "patch"
    repo = Path(sys.argv[1] if len(sys.argv) == 2 else ".").resolve()

    required = [
        repo / "lang" / "en.json",
        repo / "lang" / "ja.json",
        repo / "data" / "homepage.json",
        repo / "articles",
        repo / "style.css",
        repo / "blog.css",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        print("This does not look like the srin728.github.io repository.", file=sys.stderr)
        for path in missing:
            print(f"  missing: {path}", file=sys.stderr)
        return 1

    for src in patch_root.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(patch_root)
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"updated {rel}")

    run([sys.executable, "scripts/build_homepage.py"], repo)
    run([sys.executable, "scripts/build_blog.py"], repo)
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], repo)

    print()
    print("Phase 2 continuation applied successfully.")
    print("Review the result with: git diff")
    print("Then commit and push. Future pushes to main will rebuild static pages automatically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
