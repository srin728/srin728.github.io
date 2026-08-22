# Phase 2 continuation patch

This patch makes three changes:

1. `main` への push 時に GitHub Actions が自動で
   - `python scripts/build_homepage.py`
   - `python scripts/build_blog.py`
   - `python -m unittest discover -s tests`
   を実行します。
   生成 HTML に差分があれば、GitHub Actions が `Rebuild static pages [skip ci]` として自動コミットします。

2. Homepage のリンク配置
   - **Preprints**: arXiv 等のボタンをタイトルと同じ行に表示
   - **Awards**: Link ボタンをタイトルと同じ行に表示
   - Refereed Papers / Talks は従来どおり次の行に表示

3. Blog の static generation
   - `articles/*.md` を `scripts/build_blog.py` が静的 HTML に変換
   - `blog.js` から Markdown の `fetch()` / runtime rendering を削除
   - `blog.html` および `notes/*.html` は JavaScript 無効でも読めます
   - タグ別ページも自動生成されます
   - ブログの青系デザイン (`blog.css`) は変更しません

## 適用

リポジトリ直下で:

```bash
python apply_phase2_continuation.py .
```

適用スクリプトは必要ファイルを置き換えた後、その場で homepage/blog を生成し、テストを実行します。

その後:

```bash
git diff
git add .
git commit -m "Continue static site generation"
git push
```

最初の push 以降は、`lang/*.json` や `articles/*.md` を編集して push すれば、
GitHub Actions が生成 HTML を更新します。

## 注意

GitHub repository settings で Actions の `GITHUB_TOKEN` に write permission が禁止されている場合、
最後の自動コミットだけ失敗します。その場合は:

Settings → Actions → General → Workflow permissions

で `Read and write permissions` を有効にしてください。
