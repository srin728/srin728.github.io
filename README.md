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

This creates `sitemap.xml` and `robots.txt`.

## Automatic build

A push to `main` runs `.github/workflows/build-static-pages.yml`.

The workflow:

1. checks the Python syntax of the active generators;
2. builds the homepage;
3. builds the notes/blog;
4. builds the supplement page;
5. builds `sitemap.xml` and `robots.txt`;
6. verifies generated files with `--check`;
7. commits generated files when necessary.

For the final step, GitHub Actions needs:

`Settings → Actions → General → Workflow permissions → Read and write permissions`

## Local validation

The repository no longer requires a `tests/` directory.

```bash
python -m py_compile \
  scripts/build_homepage.py \
  scripts/build_blog.py \
  scripts/build_supplement.py \
  scripts/build_site_meta.py \
  scripts/site_utils.py

python scripts/build_homepage.py
python scripts/build_blog.py
python scripts/build_supplement.py
python scripts/build_site_meta.py

python scripts/build_homepage.py --check
python scripts/build_blog.py --check
python scripts/build_supplement.py --check
python scripts/build_site_meta.py --check
```
