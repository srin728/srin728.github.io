let currentLang = "ja";

// イベント設定
window.addEventListener("DOMContentLoaded", () => {
  loadLanguage(currentLang);
  updateSidebarState();
});
window.addEventListener("resize", updateSidebarState);

// サイドバーの状態を更新
function updateSidebarState() {
  const sidebar = document.querySelector(".sidebar");
  sidebar.classList.toggle("collapsed", window.innerWidth <= 768);
}

// 言語切り替え
function toggleLanguage() {
  const nextLang = currentLang === "ja" ? "en" : "ja";
  loadLanguage(nextLang);
}

// 言語ファイルを読み込んで反映
async function loadLanguage(lang) {
  try {
    const res = await fetch(`lang/${lang}.json`);
    if (!res.ok) throw new Error(`lang/${lang}.json の読み込み失敗 (${res.statusText})`);
    const dict = await res.json();

    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.getAttribute("data-i18n");
      if (Array.isArray(dict[key])) {
        el.innerHTML = `<ul>${dict[key].map(item => `<li>${item}</li>`).join("")}</ul>`;
      } else {
        el.innerHTML = dict[key]?.replace(/\n/g, "<br>") || "";
      }
    });

    ["name", "affiliation", "email", "address"].forEach(id => {
      const el = document.getElementById(id);
      if (el && dict[id]) el.innerText = dict[id];
    });

    const langBtn = document.getElementById("lang-btn");
    if (langBtn) langBtn.innerText = lang === "ja" ? "English" : "日本語";

    const secretLink = document.getElementById("secret-link");
    if (secretLink) secretLink.style.display = lang === "ja" ? "block" : "none";

    currentLang = lang;

    displayJsonData(dict["publications_list"], "publicationsList", "publications");
    displayJsonData(dict["preprints_list"], "preprintsList", "preprints");
    displayJsonData(dict["awards_list"], "awardsList", "awards");
    displayPresentations(dict);
  } catch (error) {
    console.error("言語ファイルの読み込みに失敗:", error);
  }
}

// プレゼンテーション表示
function displayPresentations(dict) {
  const data = dict["presentations_list"];
  const container = document.getElementById("presentationList");
  if (!data || !container) return;

  container.innerHTML = "";

  const categories = {
    international_non_refereed: dict["international_non_refereed_category_title"] || "International Talks",
    domestic_meeting: dict["domestic_meeting_category_title"] || "Domestic Talks (in Japanese)"
  };

  const grouped = Object.fromEntries(Object.keys(categories).map(key => [key, []]));
  data.forEach(item => grouped[item.type]?.push(item));

  for (const [typeKey, items] of Object.entries(grouped)) {
    if (!items.length) continue;

    container.insertAdjacentHTML("beforeend", `<h3>${categories[typeKey]}</h3>`);
    const ol = document.createElement("ol");
    ol.setAttribute("reversed", true);

    items.slice().reverse().forEach(item => {
      const highlights = Array.isArray(item.highlightText) ? item.highlightText : item.highlightText ? [item.highlightText] : [];
      const authorHtml = highlightText(item.author || "", highlights);
      const titleHtml = highlightText(item.title || "", highlights);
      const linksHtml = generateLinksHtml(item.links, highlights);

      const li = document.createElement("li");
      li.innerHTML = `
        ${authorHtml ? `${authorHtml}: ` : ""}
        ${titleHtml ? `${titleHtml}<br>` : ""}
        ${linksHtml}
      `;
      ol.appendChild(li);
    });

    container.appendChild(ol);
  }
}

// 一般データリストの表示
function displayJsonData(dataArray, targetId, type) {
  const container = document.getElementById(targetId);
  if (!container || !Array.isArray(dataArray)) return;

  container.innerHTML = "";
  const ol = document.createElement("ol");
  ol.setAttribute("reversed", true);

  dataArray.forEach(item => {
    const highlights = Array.isArray(item.highlightText) ? item.highlightText : item.highlightText ? [item.highlightText] : [];
    const authorHtml = highlightText(item.author || "", highlights);
    const titleHtml = highlightText(item.title || "", highlights);
    const linksHtml = generateLinksHtml(item.links, highlights);

    let titleWithCustomLink = titleHtml;
    if (type === "awards" && Array.isArray(item.links)) {
      const linkObj = item.links.find(link => link.url);
      if (linkObj) {
        titleWithCustomLink += ` <a class="custom-button" href="${linkObj.url}" target="_blank">${linkObj.text || "Link"}</a>`;
      }
    }

    const li = document.createElement("li");
    li.innerHTML = `
      ${authorHtml ? `${authorHtml}: ` : ""}
      ${titleWithCustomLink}<br>
      ${linksHtml}
    `;
    ol.appendChild(li);
  });

  container.appendChild(ol);
}

// テキスト中のハイライト処理
function highlightText(text, highlights) {
  if (!text || !highlights?.length) return text;
  highlights.forEach(term => {
    const regex = new RegExp(escapeRegExp(term), "gi");
    text = text.replace(regex, match => `<span class="highlight">${match}</span>`);
  });
  return text;
}

// リンクのHTML生成（DOI, arXiv対応）
function generateLinksHtml(links, highlights) {
  if (!links) return "";

  const createLink = (link) => {
    const text = highlightText(link.text || "", highlights);
    const doi = link.doi_id ? ` <a class="custom-button" href="https://doi.org/${link.doi_id}" target="_blank">DOI</a>` : "";
    const arxiv = link.arxiv_id ? ` <a class="custom-button" href="https://arxiv.org/abs/${link.arxiv_id}" target="_blank">arXiv</a>` : "";
    return `${text}${doi}${arxiv}`;
  };

  return Array.isArray(links)
    ? links.map(createLink).join("<br>")
    : typeof links === "object"
      ? createLink(links)
      : "";
}

// 正規表現用エスケープ
function escapeRegExp(text) {
  return text.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&");
}

// モバイル用メニュー切り替え
function toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  sidebar.classList.toggle('collapsed', window.innerWidth <= 768 && !sidebar.classList.contains('collapsed'));
}
