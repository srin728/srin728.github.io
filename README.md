# srin728.github.io

Academic homepage and lightweight notes site for Rin Saito.

The repository uses small Python build scripts to generate static HTML.  
Generated HTML should normally **not** be edited directly.

## Source files

### Homepage

- `lang/en.json` — English profile, papers, talks, awards
- `lang/ja.json` — Japanese profile, papers, talks, awards
- `data/homepage.json` — site-level links/settings
- `style.css` — homepage design

Generate:

```bash
python scripts/build_homepage.py
```

This creates/updates:

- `index.html`
- `ja.html`

The footer date is calculated automatically from the latest Git commit that changed a meaningful site source file.

### Supplement page

`data/supplemental.json` contains:

- `coauthor_talks` — 共著者による発表
- `updates` — 近況報告

Generate:

```bash
python scripts/build_supplement.py
```

This creates `supplement.html`.  
The page uses `#f8c112` and `#f6ae54` as its main colors.

Example entry:

```json
{
  "coauthor_talks": [
    {
      "date": "2026-09-01",
      "speaker": "Coauthor Name",
      "title": "Talk title",
      "event": "Workshop name",
      "location": "Tokyo, Japan",
      "url": "https://example.com/",
      "note": "Optional note"
    }
  ],
  "updates": [
    {
      "date": "2026-09-10",
      "text": "Short update.",
      "url": "https://example.com/",
      "link_text": "詳細"
    }
  ]
}
```

### Notes / blog

Edit Markdown files in `articles/`.

Generate:

```bash
python scripts/build_blog.py
```

This creates `blog.html` and pages under `notes/`.

### SEO metadata

Generate:

```bash
python scripts/build_site_meta.py
```

This creates:

- `sitemap.xml`
- `robots.txt`

The homepage also contains Schema.org `ProfilePage` / `Person` structured data.

## Automatic build

A push to `main` runs `.github/workflows/build-static-pages.yml`.

The workflow:

1. builds the homepage;
2. builds the notes/blog;
3. builds the supplement page;
4. builds `sitemap.xml` and `robots.txt`;
5. runs the test suite;
6. commits generated files when necessary.

For the final step, GitHub Actions needs:

`Settings → Actions → General → Workflow permissions → Read and write permissions`

## Tests

```bash
python -m unittest discover -s tests
```

To check that generated files are current without rewriting them:

```bash
python scripts/build_homepage.py --check
python scripts/build_blog.py --check
python scripts/build_supplement.py --check
python scripts/build_site_meta.py --check
```
