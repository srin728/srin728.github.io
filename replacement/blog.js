const articleFiles = [
  "articles/introduction.md",
  "articles/study_notes.md"
];

let articles = [];
let currentTag = null;
let currentArticle = null;

function getTagFromURL() {
  return new URLSearchParams(window.location.search).get("tag");
}

function setTagToURL(tag) {
  const url = new URL(window.location.href);
  if (tag) url.searchParams.set("tag", tag);
  else url.searchParams.delete("tag");
  history.pushState({}, "", url);
}

function parseFrontMatter(md) {
  const normalized = md.replace(/\r\n?/g, "\n");
  const match = normalized.match(/^---\n([\s\S]*?)\n---(?:\n|$)/);
  if (!match) return { meta: {}, content: normalized };

  const meta = {};
  match[1].split("\n").forEach(line => {
    const separator = line.indexOf(":");
    if (separator < 0) return;

    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim();
    if (!key) return;

    meta[key] = value.startsWith("[") && value.endsWith("]")
      ? value.slice(1, -1).split(",").map(x => x.trim()).filter(Boolean)
      : value;
  });

  return { meta, content: normalized.slice(match[0].length) };
}

async function fetchText(file) {
  const response = await fetch(file);
  if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
  return response.text();
}

window.addEventListener("DOMContentLoaded", async () => {
  const articleList = document.getElementById("articleList");
  const tagList = document.getElementById("tagList");
  const content = document.getElementById("articleContent");
  const sidebar = document.getElementById("sidebar");
  const hamburger = document.getElementById("hamburger");

  if (!articleList || !tagList || !content || !sidebar || !hamburger) return;

  const closeSidebar = () => {
    sidebar.classList.remove("open");
    hamburger.setAttribute("aria-expanded", "false");
    hamburger.setAttribute("aria-label", "メニューを開く");
  };

  hamburger.addEventListener("click", event => {
    event.stopPropagation();
    const isOpen = sidebar.classList.toggle("open");
    hamburger.setAttribute("aria-expanded", String(isOpen));
    hamburger.setAttribute("aria-label", isOpen ? "メニューを閉じる" : "メニューを開く");
  });

  document.addEventListener("click", event => {
    if (!sidebar.contains(event.target) && !hamburger.contains(event.target)) {
      closeSidebar();
    }
  });

  document.addEventListener("keydown", event => {
    if (event.key === "Escape") closeSidebar();
  });

  try {
    articles = await Promise.all(articleFiles.map(async file => {
      const md = await fetchText(file);
      const { meta } = parseFrontMatter(md);
      return {
        title: meta.title || file,
        tags: Array.isArray(meta.tags) ? meta.tags : [],
        file
      };
    }));
  } catch (error) {
    console.error("記事一覧の読み込みに失敗しました:", error);
    content.textContent = "記事の読み込みに失敗しました。ページを再読み込みしてください。";
    return;
  }

  const allTags = [...new Set(articles.flatMap(article => article.tags))]
    .sort((a, b) => a.localeCompare(b, "ja"));

  currentTag = getTagFromURL();
  if (!allTags.includes(currentTag)) currentTag = null;

  function renderTags() {
    tagList.replaceChildren();
    createTagButton("すべて", null);
    allTags.forEach(tag => createTagButton(tag, tag));
  }

  function createTagButton(label, value) {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "sidebar-link";
    button.textContent = label;
    button.setAttribute("aria-pressed", String(value === currentTag));
    button.addEventListener("click", () => {
      currentTag = value;
      setTagToURL(value);
      renderTags();
      renderArticles();
      closeSidebar();
    });
    li.appendChild(button);
    tagList.appendChild(li);
  }

  function renderArticles() {
    articleList.replaceChildren();

    const filtered = currentTag === null
      ? articles
      : articles.filter(article => article.tags.includes(currentTag));

    filtered.forEach(article => {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sidebar-link";
      button.textContent = article.title;
      if (article.file === currentArticle) button.setAttribute("aria-current", "true");
      button.addEventListener("click", async () => {
        await loadArticle(article.file);
        renderArticles();
        closeSidebar();
      });
      li.appendChild(button);
      articleList.appendChild(li);
    });
  }

  async function loadArticle(file) {
    try {
      const md = await fetchText(file);
      const { meta, content: body } = parseFrontMatter(md);
      currentArticle = file;

      const fragment = document.createDocumentFragment();
      const heading = document.createElement("h1");
      heading.textContent = meta.title || "";
      fragment.appendChild(heading);

      const tags = document.createElement("div");
      tags.className = "tags";
      (Array.isArray(meta.tags) ? meta.tags : []).forEach(tagName => {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = tagName;
        tags.appendChild(tag);
      });
      fragment.appendChild(tags);

      const articleBody = document.createElement("div");
      if (window.marked && window.DOMPurify) {
        articleBody.innerHTML = window.DOMPurify.sanitize(window.marked.parse(body));
      } else {
        const pre = document.createElement("pre");
        pre.textContent = body;
        articleBody.appendChild(pre);
      }
      fragment.appendChild(articleBody);

      content.replaceChildren(fragment);
      document.title = meta.title ? `${meta.title} — Rin's Notes` : "Rin's Notes";

      if (typeof window.MathJax?.typesetPromise === "function") {
        await window.MathJax.typesetPromise([content]);
      }
    } catch (error) {
      console.error("記事の読み込みに失敗しました:", error);
      content.textContent = "記事の読み込みに失敗しました。";
    }
  }

  renderTags();
  renderArticles();

  const initial = articles.find(article =>
    currentTag === null || article.tags.includes(currentTag)
  );
  if (initial) {
    await loadArticle(initial.file);
    renderArticles();
  }

  window.addEventListener("popstate", () => {
    const tag = getTagFromURL();
    currentTag = allTags.includes(tag) ? tag : null;
    renderTags();
    renderArticles();
  });
});
