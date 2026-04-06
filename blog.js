// ===== 記事ファイル一覧（ここだけ管理すればOK）=====
const articleFiles = [
    "articles/introduction.md",
    "articles/study_notes.md"
];

let articles = [];
let currentTag = null;

// ===== URL操作 =====
function getTagFromURL() {
    const params = new URLSearchParams(window.location.search);
    return params.get("tag");
}

function setTagToURL(tag) {
    const url = new URL(window.location);

    if (tag === null) {
        url.searchParams.delete("tag");
    } else {
        url.searchParams.set("tag", tag);
    }

    history.pushState({}, "", url);
}

// ===== front matter パーサ =====
function parseFrontMatter(md) {
    const match = md.match(/^---\n([\s\S]*?)\n---/);
    if (!match) return { meta: {}, content: md };

    const metaText = match[1];
    const content = md.slice(match[0].length);

    const meta = {};

    metaText.split("\n").forEach(line => {
        const [key, value] = line.split(":").map(s => s.trim());
        if (!key) return;

        if (value.startsWith("[")) {
            meta[key] = value
                .replace(/[\[\]]/g, "")
                .split(",")
                .map(v => v.trim());
        } else {
            meta[key] = value;
        }
    });

    return { meta, content };
}

// ===== 初期化 =====
window.addEventListener("DOMContentLoaded", async () => {

    const list = document.getElementById("articleList");
    const tagList = document.getElementById("tagList");
    const content = document.getElementById("articleContent");

    // ===== 全記事読み込み =====
    const promises = articleFiles.map(file =>
        fetch(file)
            .then(res => res.text())
            .then(md => {
                const { meta } = parseFrontMatter(md);
                return {
                    title: meta.title || file,
                    tags: meta.tags || [],
                    file
                };
            })
    );

    articles = await Promise.all(promises);

    // ===== タグ集合 =====
    const allTags = new Set();
    articles.forEach(a => a.tags.forEach(tag => allTags.add(tag)));

    // ===== URLからタグ取得 =====
    currentTag = getTagFromURL();
    if (!allTags.has(currentTag)) currentTag = null;

    // ===== タグ描画 =====
    function renderTags() {
        tagList.innerHTML = "";

        createTag("すべて", null);

        allTags.forEach(tag => {
            createTag(tag, tag);
        });
    }

    function createTag(label, tagValue) {
        const li = document.createElement("li");
        const a = document.createElement("a");

        a.textContent = label;
        a.href = "#";

        a.onclick = () => {
            currentTag = tagValue;
            setTagToURL(tagValue);
            renderArticles();
            highlightTag();
        };

        li.appendChild(a);
        tagList.appendChild(li);
    }

    function highlightTag() {
        const links = tagList.querySelectorAll("a");

        links.forEach(link => {
            const tag = link.textContent === "すべて" ? null : link.textContent;
            link.style.fontWeight = (tag === currentTag) ? "bold" : "normal";
        });
    }

    // ===== 記事一覧 =====
    function renderArticles() {
        list.innerHTML = "";

        const filtered = currentTag === null
            ? articles
            : articles.filter(a => a.tags.includes(currentTag));

        filtered.forEach(article => {
            const li = document.createElement("li");
            const a = document.createElement("a");

            a.textContent = article.title;
            a.href = "#";
            a.onclick = () => loadArticle(article.file);

            li.appendChild(a);
            list.appendChild(li);
        });
    }

    // ===== 記事表示 =====
    function loadArticle(file) {
        fetch(file)
            .then(res => res.text())
            .then(md => {
                const { meta, content: body } = parseFrontMatter(md);

                const tagHTML = (meta.tags || [])
                    .map(tag => `<span class="tag">${tag}</span>`)
                    .join(" ");

                content.innerHTML = `
                    <h1>${meta.title || ""}</h1>
                    <div class="tags">${tagHTML}</div>
                    ${marked.parse(body)}
                `;

                if (window.MathJax) MathJax.typesetPromise();
            });
    }

    // ===== 初期描画 =====
    renderTags();
    renderArticles();
    highlightTag();

    // 初期記事
    const initial = articles.find(a =>
        currentTag === null || a.tags.includes(currentTag)
    );
    if (initial) loadArticle(initial.file);

    // 戻るボタン対応
    window.addEventListener("popstate", () => {
        currentTag = getTagFromURL();
        renderArticles();
        highlightTag();
    });

});
