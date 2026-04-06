// ===== 記事 =====
const articleFiles = [
    "articles/introduction.md",
    "articles/study_notes.md"
];

let articles = [];
let currentTag = null;

// ===== URL =====
function getTagFromURL() {
    return new URLSearchParams(window.location.search).get("tag");
}

function setTagToURL(tag) {
    const url = new URL(window.location);
    tag ? url.searchParams.set("tag", tag) : url.searchParams.delete("tag");
    history.pushState({}, "", url);
}

// ===== front matter =====
function parseFrontMatter(md) {
    const match = md.match(/^---\n([\s\S]*?)\n---/);
    if (!match) return { meta: {}, content: md };

    const meta = {};
    match[1].split("\n").forEach(line => {
        const [k, v] = line.split(":").map(s => s.trim());
        if (!k) return;
        meta[k] = v.startsWith("[")
            ? v.replace(/[\[\]]/g, "").split(",").map(x => x.trim())
            : v;
    });

    return { meta, content: md.slice(match[0].length) };
}

// ===== 初期化 =====
window.addEventListener("DOMContentLoaded", async () => {

    const list = document.getElementById("articleList");
    const tagList = document.getElementById("tagList");
    const content = document.getElementById("articleContent");
    const sidebar = document.getElementById("sidebar");
    const hamburger = document.getElementById("hamburger");

    // ===== ハンバーガー制御 =====
    hamburger.onclick = () => {
        sidebar.classList.toggle("open");
    };

    // 外側クリックで閉じる
    document.addEventListener("click", (e) => {
        if (!sidebar.contains(e.target) && !hamburger.contains(e.target)) {
            sidebar.classList.remove("open");
        }
    });

    // ===== 記事ロード =====
    const promises = articleFiles.map(file =>
        fetch(file)
            .then(r => r.text())
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

    const allTags = new Set();
    articles.forEach(a => a.tags.forEach(t => allTags.add(t)));

    currentTag = getTagFromURL();
    if (!allTags.has(currentTag)) currentTag = null;

    function renderTags() {
        tagList.innerHTML = "";
        createTag("すべて", null);
        allTags.forEach(t => createTag(t, t));
    }

    function createTag(label, value) {
        const li = document.createElement("li");
        const a = document.createElement("a");

        a.textContent = label;
        a.href = "#";
        a.onclick = () => {
            currentTag = value;
            setTagToURL(value);
            renderArticles();
            highlightTag();
            sidebar.classList.remove("open"); // モバイルで閉じる
        };

        li.appendChild(a);
        tagList.appendChild(li);
    }

    function highlightTag() {
        tagList.querySelectorAll("a").forEach(a => {
            const t = a.textContent === "すべて" ? null : a.textContent;
            a.style.fontWeight = (t === currentTag) ? "bold" : "normal";
        });
    }

    function renderArticles() {
        list.innerHTML = "";

        const filtered = currentTag === null
            ? articles
            : articles.filter(a => a.tags.includes(currentTag));

        filtered.forEach(a => {
            const li = document.createElement("li");
            const link = document.createElement("a");

            link.textContent = a.title;
            link.href = "#";
            link.onclick = () => {
                loadArticle(a.file);
                sidebar.classList.remove("open");
            };

            li.appendChild(link);
            list.appendChild(li);
        });
    }

    function loadArticle(file) {
        fetch(file)
            .then(r => r.text())
            .then(md => {
                const { meta, content: body } = parseFrontMatter(md);

                const tags = (meta.tags || [])
                    .map(t => `<span class="tag">${t}</span>`)
                    .join(" ");

                content.innerHTML = `
                    <h1>${meta.title || ""}</h1>
                    <div class="tags">${tags}</div>
                    ${marked.parse(body)}
                `;

                if (window.MathJax) MathJax.typesetPromise();
            });
    }

    renderTags();
    renderArticles();
    highlightTag();

    const initial = articles.find(a =>
        currentTag === null || a.tags.includes(currentTag)
    );
    if (initial) loadArticle(initial.file);

    window.addEventListener("popstate", () => {
        currentTag = getTagFromURL();
        renderArticles();
        highlightTag();
    });
});
