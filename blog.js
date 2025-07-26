const articles = [
    { title: "自己紹介", file: "articles/introduction.md" },
    { title: "勉強メモ", file: "articles/study_notes.md" },
    // { title: "誤植リスト", file: "articles/errata.md" },
    // { title: "出張の記録", file: "articles/travel_log.md" },
    // { title: "コメント付き論文リスト", file: "articles/commented_papers.md" }
];

window.addEventListener("DOMContentLoaded", () => {
    const list = document.getElementById("articleList");
    const content = document.getElementById("articleContent");

    articles.forEach((article, index) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.textContent = article.title;
        a.href = "#";
        a.onclick = () => {
            loadArticle(article.file);
        };
        li.appendChild(a);
        list.appendChild(li);
    });

    // 初回読み込み時に一番上の記事を自動表示
    loadArticle(articles[0].file);

    function loadArticle(file) {
        fetch(file)
            .then(response => response.text())
            .then(md => {
                const html = marked.parse(md);
                content.innerHTML = html;
                if (window.MathJax) MathJax.typesetPromise();
            });
    }
});


