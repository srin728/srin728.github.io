from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BlogStaticBuildTest(unittest.TestCase):
    def test_generated_blog_is_current(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_blog.py"), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_blog_does_not_fetch_markdown_at_runtime(self):
        script = (ROOT / "blog.js").read_text(encoding="utf-8")
        html = (ROOT / "blog.html").read_text(encoding="utf-8")
        self.assertNotIn("fetch(", script)
        self.assertNotIn("marked", html.lower())
        self.assertNotIn("dompurify", html.lower())

    def test_every_markdown_article_has_static_page(self):
        manifest_path = ROOT / "notes" / ".generated.json"
        manifest = set(json.loads(manifest_path.read_text(encoding="utf-8")))
        for source in (ROOT / "articles").glob("*.md"):
            target = f"{source.stem}.html"
            self.assertIn(target, manifest)
            self.assertTrue((ROOT / "notes" / target).exists())

    def test_math_source_survives_static_conversion(self):
        source = ROOT / "articles" / "study_notes.md"
        if not source.exists():
            self.skipTest("study_notes.md not present")
        generated = (ROOT / "notes" / "study_notes.html").read_text(encoding="utf-8")
        self.assertIn(r"\sum_", generated)
        self.assertIn("math-display", generated)


if __name__ == "__main__":
    unittest.main()
