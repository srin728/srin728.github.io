#!/usr/bin/env python3
from pathlib import Path
import shutil, subprocess, sys
package = Path(__file__).resolve().parent
payload = package / "payload"
repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
for req in [repo/".git", repo/"data"/"supplemental.json", repo/"scripts"/"build_supplement.py", repo/"supplement.css"]:
    if not req.exists(): raise SystemExit(f"missing: {req}")
for src in payload.rglob("*"):
    if src.is_file():
        rel = src.relative_to(payload); dst = repo/rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,dst); print("updated", rel)
for cmd in [
    [sys.executable,"-m","py_compile","scripts/build_supplement.py"],
    [sys.executable,"scripts/build_supplement.py"],
    [sys.executable,"scripts/build_supplement.py","--check"],
]:
    print("+", " ".join(cmd)); subprocess.run(cmd,cwd=repo,check=True)
print("Applied and validated.")
