from __future__ import annotations

import json
import subprocess
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IdHrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.hash_hrefs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        href = attrs.get("href", "")
        if href.startswith("#") and len(href) > 1:
            self.hash_hrefs.append(href[1:])


class HomepageStaticBuildTest(unittest.TestCase):
    def test_generated_pages_are_current(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_homepage.py"), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_both_languages_are_static(self):
        en = (ROOT / "index.html").read_text(encoding="utf-8")
        ja = (ROOT / "ja.html").read_text(encoding="utf-8")
        en_data = json.loads((ROOT / "lang" / "en.json").read_text(encoding="utf-8"))
        ja_data = json.loads((ROOT / "lang" / "ja.json").read_text(encoding="utf-8"))

        self.assertIn(en_data["name"], en)
        self.assertIn(ja_data["name"], ja)
        self.assertIn(en_data["publications_list"][0]["title"], en)
        self.assertIn(ja_data["publications_list"][0]["title"], ja)
        self.assertIn('href="ja.html"', en)
        self.assertIn('href="index.html"', ja)
        self.assertNotIn("data-i18n", en)
        self.assertNotIn("data-i18n", ja)

    def test_javascript_does_not_fetch_language_or_content(self):
        script = (ROOT / "script.js").read_text(encoding="utf-8")
        self.assertNotIn("fetch(", script)
        self.assertNotIn("loadLanguage", script)
        self.assertNotIn("publicationsList", script)

    def test_original_palette_is_restored(self):
        css = (ROOT / "style.css").read_text(encoding="utf-8").lower()
        self.assertIn("#ea533a", css)
        self.assertIn("#e30f25", css)
        self.assertNotIn("#d14632", css)

    def test_internal_navigation_targets_exist(self):
        for name in ("index.html", "ja.html"):
            parser = IdHrefParser()
            parser.feed((ROOT / name).read_text(encoding="utf-8"))
            self.assertTrue(parser.hash_hrefs)
            self.assertTrue(set(parser.hash_hrefs).issubset(parser.ids))


if __name__ == "__main__":
    unittest.main()
