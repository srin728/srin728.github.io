# srin728.github.io — Phase 2 static homepage patch

This patch converts the academic homepage to build-time static HTML while restoring the pre-Phase-1 visual design.

## What changes

- `lang/en.json` and `lang/ja.json` remain the source of profile/publication/talk/award data.
- `scripts/build_homepage.py` generates:
  - `index.html` — English
  - `ja.html` — Japanese
- The language switch is now a normal HTML link. It works without JavaScript.
- Publications, preprints, talks, awards, biography, and research interests are present in the initial HTML.
- `script.js` only controls the mobile navigation menu.
- The original homepage palette is restored:
  - main orange: `#ea533a`
  - DOI/arXiv button red: `#e30f25`
  - body text: `#555`
  - original 150px sidebar / 220px content offset
- Mobile CSS is cleaned up without changing the desktop design.

## Apply

From the root of your cloned `srin728.github.io` repository, unzip this patch somewhere and run:

```bash
python /path/to/unzipped/apply_phase2.py .
```

If `apply_phase2.py` itself is copied into the repository root, use:

```bash
python apply_phase2.py .
```

Then check:

```bash
python -m unittest tests.test_homepage
git diff
```

When everything looks correct, commit and push.

## Future homepage updates

Edit `lang/en.json` and/or `lang/ja.json`, then regenerate the pages:

```bash
python scripts/build_homepage.py
```

You can verify that the generated HTML is up to date with:

```bash
python scripts/build_homepage.py --check
```

`data/homepage.json` contains site-level settings such as the last-updated text and Misc links.

## Important

The blog is not converted in this patch. `blog.html` still uses client-side Markdown rendering. This is intentionally left for a later step so that the homepage migration remains small and easy to verify.
