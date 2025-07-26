let currentLang = "ja";

// 初期読み込み時の言語設定
window.addEventListener("DOMContentLoaded", () => {
  loadLanguage(currentLang);
});

// 言語切り替え処理
function toggleLanguage() {
  const nextLang = currentLang === "ja" ? "en" : "ja";
  loadLanguage(nextLang);
}

// 言語ファイルの読み込みと画面更新
async function loadLanguage(lang) {
  try {
    const res = await fetch(`lang/${lang}.json`);
    if (!res.ok) throw new Error(`lang/${lang}.json の読み込み失敗 (${res.statusText})`);

    const dict = await res.json();

    // テキスト要素の置き換え
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.getAttribute("data-i18n");
      if (dict[key]) el.innerHTML = dict[key].replace(/\n/g, "<br>");
    });

    // 基本情報の更新
    ["name", "affiliation", "email", "address"].forEach(id => {
      const el = document.getElementById(id);
      if (el && dict[id]) el.innerText = dict[id];
    });

    // 言語切り替えボタンと非表示要素制御
    const langBtn = document.getElementById("lang-btn");
    if (langBtn) langBtn.innerText = lang === "ja" ? "English" : "日本語";

    const secretLink = document.getElementById("secret-link");
    if (secretLink) secretLink.style.display = lang === "ja" ? "block" : "none";

    currentLang = lang;

    // データリストの描画
    displayJsonData(dict["publications_list"], "publicationsList", "publications"); // 識別子を追加
    displayJsonData(dict["preprints_list"], "preprintsList", "preprints");       // 識別子を追加
    displayJsonData(dict["awards_list"], "awardsList", "awards");
    displayPresentations(dict);

  } catch (error) {
    console.error("言語ファイルの読み込みに失敗:", error);
  }
}

// プレゼンテーション一覧（カテゴリごとに ol reversed で表示）
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

  data.forEach(item => {
    if (grouped[item.type]) {
      grouped[item.type].push(item);
    }
  });

  for (const [typeKey, items] of Object.entries(grouped)) {
    if (items.length === 0) continue;

    const title = document.createElement("h3");
    title.textContent = categories[typeKey];
    container.appendChild(title);

    const ol = document.createElement("ol");
    ol.setAttribute("reversed", true);
    items.slice().reverse().forEach(item => {
      const li = document.createElement("li");

      const highlights = Array.isArray(item.highlightText)
        ? item.highlightText
        : item.highlightText ? [item.highlightText] : [];

      const authorHtml = highlightText(item.author || "", highlights);
      const titleHtml = highlightText(item.title || "", highlights);
      const linksHtml = generateLinksHtml(item.links, highlights);

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

// 一般的なデータリストの描画（ul）
function displayJsonData(dataArray, targetElementId, targetType) {
  const container = document.getElementById(targetElementId);
  if (!container || !Array.isArray(dataArray)) return;

  container.innerHTML = "";

  const ol = document.createElement("ol");
  ol.setAttribute("reversed", true);

  dataArray.forEach(item => {
    const li = document.createElement("li");

    const highlights = Array.isArray(item.highlightText)
      ? item.highlightText
      : item.highlightText ? [item.highlightText] : [];

    const authorHtml = highlightText(item.author || "", highlights);
    const titleHtml = highlightText(item.title || "", highlights);
    const linksHtml = generateLinksHtml(item.links, highlights);

    // awards_list 専用のリンク処理
    if (targetType === "awards" && item.links && item.links.url) {
      // awards_list のリンクは custom-button として別途生成
      const awardLinkHtml = `<a class="custom-button" href="${item.links.url}" target="_blank">${Link}</a>`;
      // 既存の linksHtml があればそれと結合、なければ awardLinkHtml のみ
      linksHtml = linksHtml ? `${linksHtml} ${awardLinkHtml}` : awardLinkHtml;
    }

    li.innerHTML = `
      ${authorHtml ? `${authorHtml}: ` : ""}
      ${titleHtml ? `${titleHtml}<br>` : ""}
      ${linksHtml}
    `;
    ol.appendChild(li);
  });

  container.appendChild(ol);
}

// ハイライト処理
function highlightText(text, highlights) {
  if (!text || !highlights?.length) return text;

  let result = text;
  highlights.forEach(term => {
    const regex = new RegExp(escapeRegExp(term), "gi");
    result = result.replace(regex, match => `<span class="highlight">${match}</span>`);
  });

  return result;
}

// DOI/arXivリンク生成
function generateLinksHtml(links, highlights) {
  if (!links) return "";

  const createLink = (link) => {
    const text = highlightText(link.text || "", highlights);
    const doi = link.doi_id ? ` <a class="custom-button" href="https://doi.org/${link.doi_id}" target="_blank">DOI</a>` : "";
    const arxiv = link.arxiv_id ? ` <a class="custom-button" href="https://arxiv.org/abs/${link.arxiv_id}" target="_blank">arXiv</a>` : "";
    return `${text}${doi}${arxiv}`;
  };

  if (Array.isArray(links)) {
    return links.map(createLink).join("<br>");
  } else if (typeof links === "object") {
    return createLink(links);
  }
  return "";
}

// 特殊文字をエスケープ
function escapeRegExp(text) {
  return text.replace(/[-\/\\^$*+?.()|[\]{}]/g, "\\$&");
}
