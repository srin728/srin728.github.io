from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HomepageRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.blog = (ROOT / "blog.html").read_text(encoding="utf-8")
        cls.en = json.loads((ROOT / "lang" / "en.json").read_text(encoding="utf-8"))
        cls.ja = json.loads((ROOT / "lang" / "ja.json").read_text(encoding="utf-8"))

    def test_default_document_language_matches_default_content(self):
        self.assertRegex(self.index, r'<html\s+lang="en"')

    def test_internal_navigation_targets_exist(self):
        ids = set(re.findall(r'\bid="([^"]+)"', self.index))
        anchors = re.findall(r'href="#([^"]+)"', self.index)
        self.assertTrue(anchors)
        self.assertEqual([], [anchor for anchor in anchors if anchor not in ids])

    def test_i18n_keys_exist_in_both_languages(self):
        keys = set(re.findall(r'data-i18n="([^"]+)"', self.index))
        missing_en = sorted(key for key in keys if key not in self.en)
        missing_ja = sorted(key for key in keys if key not in self.ja)
        self.assertEqual([], missing_en)
        self.assertEqual([], missing_ja)

    def test_maxmin_reconfiguration_arxiv_link(self):
        title = "On (In)approximability of MaxMin Independent Set Reconfiguration"
        for data in (self.en, self.ja):
            paper = next(item for item in data["publications_list"] if item["title"] == title)
            self.assertEqual("2604.26714", paper["links"][0]["arxiv_id"])

    def test_presentation_title_has_no_orphan_opening_quote(self):
        bad_prefix = "“Reconfiguration of vertex-disjoint shortest paths on split graphs"
        for data in (self.en, self.ja):
            self.assertFalse(any(
                item.get("title", "").startswith(bad_prefix)
                for item in data["presentations_list"]
            ))

    def test_blog_hamburger_is_a_button(self):
        self.assertRegex(self.blog, r'<button\s+[^>]*id="hamburger"')
        self.assertIn('aria-controls="sidebar"', self.blog)


if __name__ == "__main__":
    unittest.main()
