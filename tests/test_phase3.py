from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Phase3Test(unittest.TestCase):
    def test_supplement_is_current(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_supplement.py"), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_site_metadata_is_current(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_site_meta.py"), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_footer_date_is_not_manually_configured(self):
        config = json.loads((ROOT / "data" / "homepage.json").read_text(encoding="utf-8"))
        self.assertNotIn("last_updated_en", config)
        self.assertNotIn("last_updated_ja", config)

    def test_supplement_palette_and_sections(self):
        css = (ROOT / "supplement.css").read_text(encoding="utf-8").lower()
        html = (ROOT / "supplement.html").read_text(encoding="utf-8")
        self.assertIn("#f8c112", css)
        self.assertIn("#f6ae54", css)
        self.assertIn('id="coauthor-talks"', html)
        self.assertIn('id="updates"', html)
        self.assertIn("共著者による発表", html)
        self.assertIn("近況報告", html)
        self.assertNotIn("<script src=", html)

    def test_misc_links_to_supplement_in_same_tab(self):
        for name in ("index.html", "ja.html"):
            html = (ROOT / name).read_text(encoding="utf-8")
            match = re.search(r'<a href="supplement\.html"([^>]*)>Supplement / 補足情報</a>', html)
            self.assertIsNotNone(match, name)
            self.assertNotIn('target="_blank"', match.group(1))

    def test_structured_data_is_present(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('type="application/ld+json"', html)
        self.assertIn('"@type":"ProfilePage"', html)
        self.assertIn('"@type":"Person"', html)
        self.assertIn('"dateModified":', html)

    def test_sitemap_and_robots_include_new_page(self):
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("https://srin728.github.io/supplement.html", sitemap)
        self.assertIn("https://srin728.github.io/sitemap.xml", robots)

    def test_legacy_phase_files_are_removed(self):
        forbidden = [
            ROOT / "PHASE2_README.md",
            ROOT / "apply_phase2.py",
            ROOT / "apply_phase2_continuation.py",
            ROOT / "build_homepage.py",
            ROOT / "homepage.json",
            ROOT / "patch",
        ]
        for path in forbidden:
            self.assertFalse(path.exists(), str(path))


if __name__ == "__main__":
    unittest.main()
