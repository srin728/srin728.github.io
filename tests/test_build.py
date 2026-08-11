from pathlib import Path
import importlib.util
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / 'scripts' / 'build.py'
spec = importlib.util.spec_from_file_location('pcdb_build', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class BuildHelpersTest(unittest.TestCase):
    def test_nested_braces_and_tags(self):
        text = r'''@inproceedings{Key2026,
          author = {Garc{\\'i}a, Ana and Bob Example},
          title = {A {Parameterized} Result for $k$-Path},
          year = {2026},
          keywords = {kernelization; FPT algorithms, graph algorithms},
          doi = {10.1/example}
        }'''
        entries = mod.parse_bibtex(text)
        self.assertEqual(len(entries), 1)
        f = entries[0]['fields']
        self.assertEqual(mod.latex_to_text(f['title']), 'A Parameterized Result for $k$-Path')
        self.assertEqual(mod.split_tags(f['keywords']), ['kernelization', 'FPT algorithms', 'graph algorithms'])
        self.assertEqual(mod.split_authors(f['author'])[1], 'Bob Example')

    def test_doi_normalization_removes_tex_escape(self):
        self.assertEqual(mod.normalize_doi(r'10.1007/978-3-031-38906-1\_8'), '10.1007/978-3-031-38906-1_8')
        self.assertEqual(mod.normalize_doi(r'10.1007/978-3-031-38906-1/\_8'), '10.1007/978-3-031-38906-1_8')
        self.assertEqual(mod.normalize_url(r'https://doi.org/10.1007/978-3-031-38906-1/\_8'), 'https://doi.org/10.1007/978-3-031-38906-1_8')

    def test_survey_paths_are_recognized(self):
        self.assertTrue(mod.is_survey_bib(mod.BIB_DIR / 'survey' / 'survey.bib'))
        self.assertTrue(mod.is_survey_bib(mod.BIB_DIR / 'survey.bib'))
        self.assertFalse(mod.is_survey_bib(mod.BIB_DIR / 'SODA' / 'SODA_2026.bib'))

    def test_dblp_author_suffix_is_removed_from_display(self):
        self.assertEqual(mod.split_authors('Lu Liu 0030 and Alice Example'), ['Lu Liu', 'Alice Example'])
        self.assertEqual(mod.split_authors('Liu 0030, Lu'), ['Lu Liu'])
        self.assertEqual(mod.normalize_dblp_author_name('Author 123'), 'Author 123')

    def test_safe_bib_filename(self):
        self.assertEqual(mod.safe_bib_filename('Liu2026'), 'Liu2026.bib')
        self.assertEqual(mod.safe_bib_filename('Key:with/slash'), 'Key_with_slash.bib')

    def test_first_page_number(self):
        self.assertEqual(mod.first_page_number('3--27'), 3)
        self.assertEqual(mod.first_page_number('S41--S50'), 41)
        self.assertIsNone(mod.first_page_number(''))

    def test_preferred_paper_url_prioritizes_doi(self):
        self.assertEqual(mod.preferred_paper_url('10.1000/example', 'https://dblp.org/example'), 'https://doi.org/10.1000/example')
        self.assertEqual(mod.preferred_paper_url('', 'https://dblp.org/example'), 'https://dblp.org/example')

    def test_crossref_test_prefix_falls_back_to_url(self):
        doi = '10.5555/3326943.3327068'
        url = 'https://dblp.org/rec/conf/nips/BensonK18'
        self.assertEqual(mod.doi_resolver_url(doi), '')
        self.assertEqual(mod.preferred_paper_url(doi, url), url)

    def test_coverage_status_aliases(self):
        self.assertEqual(mod.normalize_coverage_status('surveyed'), 'complete')
        self.assertEqual(mod.normalize_coverage_status('in progress'), 'partial')
        self.assertEqual(mod.normalize_coverage_status('todo'), 'planned')
        self.assertIsNone(mod.normalize_coverage_status('mystery'))

    def test_coverage_override(self):
        coverage = {('SODA', '2025'): {'conference': 'SODA', 'year': '2025', 'status': 'complete', 'source': 'bib'}}
        mod.apply_coverage_overrides(coverage, {'SODA': {'2025': 'partial'}, 'STOC': {'2026': 'planned'}})
        self.assertEqual(coverage[('SODA', '2025')]['status'], 'partial')
        self.assertEqual(coverage[('STOC', '2026')]['status'], 'planned')

    def test_missing_conference_definitions(self):
        self.assertEqual(mod.missing_conference_definitions(['SODA', 'LICS'], {'SODA': 'SODA'}), ['LICS'])


if __name__ == '__main__':
    unittest.main()
