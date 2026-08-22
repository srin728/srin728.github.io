let currentLang = document.documentElement.lang === "ja" ? "ja" : "en";

window.addEventListener("DOMContentLoaded", () => {
  const menuButton = document.getElementById("menu-toggle");
  const langButton = document.getElementById("lang-btn");

  menuButton?.addEventListener("click", toggleSidebar);
  langButton?.addEventListener("click", toggleLanguage);

  updateSidebarState();
  loadLanguage(currentLang);
});

window.addEventListener("resize", updateSidebarState);

function isMobileLayout() {
  return window.matchMedia("(max-width: 768px)").matches;
}

function updateSidebarState() {
  const sidebar = document.getElementById("sidebar");
  const button = document.getElementById("menu-toggle");
  if (!sidebar || !button) return;

  if (isMobileLayout()) {
    sidebar.classList.add("collapsed");
    button.setAttribute("aria-expanded", "false");
  } else {
    sidebar.classList.remove("collapsed");
    button.setAttribute("aria-expanded", "true");
  }
}

function toggleSidebar() {
  if (!isMobileLayout()) return;

  const sidebar = document.getElementById("sidebar");
  const button = document.getElementById("menu-toggle");
  if (!sidebar || !button) return;

  const willOpen = sidebar.classList.contains("collapsed");
  sidebar.classList.toggle("collapsed", !willOpen);
  button.setAttribute("aria-expanded", String(willOpen));
}

function toggleLanguage() {
  loadLanguage(currentLang === "ja" ? "en" : "ja");
}

async function loadLanguage(lang) {
  const errorBox = document.getElementById("load-error");

  try {
    const res = await fetch(`lang/${lang}.json`);
    if (!res.ok) {
      throw new Error(`lang/${lang}.json: HTTP ${res.status}`);
    }

    const dict = await res.json();
    applyTranslations(dict);

    currentLang = lang;
    document.documentElement.lang = lang;

    const langBtn = document.getElementById("lang-btn");
    if (langBtn) {
      const targetLanguage = lang === "ja" ? "English" : "日本語";
      langBtn.textContent = targetLanguage;
      langBtn.setAttribute(
        "aria-label",
        lang === "ja" ? "Switch language to English" : "言語を日本語に切り替える"
      );
    }

    displayJsonData(dict.publications_list, "publicationsList");
    displayJsonData(dict.preprints_list, "preprintsList");
    displayJsonData(dict.awards_list, "awardsList");
    displayPresentations(dict);

    if (errorBox) {
      errorBox.hidden = true;
      errorBox.textContent = "";
    }

    if (typeof window.MathJax?.typesetPromise === "function") {
      await window.MathJax.typesetPromise();
    }
  } catch (error) {
    console.error("Failed to load language data:", error);
    if (errorBox) {
      errorBox.textContent = currentLang === "ja"
        ? "表示データの読み込みに失敗しました。ページを再読み込みしてください。"
        : "Some page data could not be loaded. Please reload the page.";
      errorBox.hidden = false;
    }
  }
}

function applyTranslations(dict) {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.dataset.i18n;
    if (!(key in dict)) return;

    const value = dict[key];
    el.replaceChildren();

    if (Array.isArray(value)) {
      const ul = document.createElement("ul");
      value.forEach(item => {
        const li = document.createElement("li");
        // Local translation files are trusted site content.  Some entries
        // intentionally contain a small link element.
        li.innerHTML = String(item);
        ul.appendChild(li);
      });
      el.appendChild(ul);
    } else {
      el.textContent = String(value ?? "");
    }
  });

  ["name", "affiliation", "email", "address"].forEach(id => {
    const el = document.getElementById(id);
    if (el && dict[id] != null) el.textContent = String(dict[id]);
  });
}

function displayPresentations(dict) {
  const data = dict.presentations_list;
  const container = document.getElementById("presentationList");
  if (!Array.isArray(data) || !container) return;

  container.replaceChildren();

  const categories = {
    international_non_refereed:
      dict.international_non_refereed_category_title || "International Talks",
    domestic_meeting:
      dict.domestic_meeting_category_title || "Domestic Talks (in Japanese)"
  };

  const grouped = Object.fromEntries(Object.keys(categories).map(key => [key, []]));
  data.forEach(item => {
    if (grouped[item.type]) grouped[item.type].push(item);
  });

  Object.entries(grouped).forEach(([typeKey, items]) => {
    if (!items.length) return;

    const heading = document.createElement("h3");
    heading.textContent = categories[typeKey];
    container.appendChild(heading);

    const ol = document.createElement("ol");
    ol.reversed = true;

    items.slice().reverse().forEach(item => {
      ol.appendChild(createDataListItem(item));
    });

    container.appendChild(ol);
  });
}

function displayJsonData(dataArray, targetId) {
  const container = document.getElementById(targetId);
  if (!container || !Array.isArray(dataArray)) return;

  container.replaceChildren();
  const ol = document.createElement("ol");
  ol.reversed = true;

  dataArray.forEach(item => {
    ol.appendChild(createDataListItem(item));
  });

  container.appendChild(ol);
}

function createDataListItem(item) {
  const highlights = Array.isArray(item.highlightText)
    ? item.highlightText
    : item.highlightText
      ? [item.highlightText]
      : [];

  const authorHtml = highlightText(item.author || "", highlights);
  const titleHtml = highlightText(item.title || "", highlights);
  const linksHtml = generateLinksHtml(item.links, highlights);

  const li = document.createElement("li");
  li.innerHTML = [
    authorHtml ? `${authorHtml}: ` : "",
    titleHtml,
    titleHtml && linksHtml ? "<br>" : "",
    linksHtml
  ].join("");

  return li;
}

function highlightText(text, highlights) {
  const source = String(text ?? "");
  const terms = [...new Set((highlights || []).filter(Boolean).map(String))]
    .sort((a, b) => b.length - a.length);

  if (!terms.length) return escapeHtml(source);

  const regex = new RegExp(`(${terms.map(escapeRegExp).join("|")})`, "gi");
  const normalized = new Set(terms.map(term => term.toLocaleLowerCase()));

  return source.split(regex).map(part => {
    const escaped = escapeHtml(part);
    return normalized.has(part.toLocaleLowerCase())
      ? `<span class="highlight">${escaped}</span>`
      : escaped;
  }).join("");
}

function generateLinksHtml(links, highlights) {
  if (!links) return "";
  const linkArray = Array.isArray(links) ? links : [links];

  return linkArray.map(link => {
    if (!link || typeof link !== "object") return "";

    const parts = [];
    if (link.text) parts.push(highlightText(link.text, highlights));

    if (link.doi_id) {
      parts.push(externalButton(`https://doi.org/${encodeURI(String(link.doi_id))}`, "DOI"));
    }
    if (link.arxiv_id) {
      parts.push(externalButton(`https://arxiv.org/abs/${encodeURIComponent(String(link.arxiv_id))}`, "arXiv"));
    }
    if (link.url) {
      parts.push(externalButton(String(link.url), link["link-text"] || "Link"));
    }

    return parts.join(" ");
  }).filter(Boolean).join("<br>");
}

function externalButton(href, label) {
  return `<a class="custom-button" href="${escapeAttribute(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(text) {
  return escapeHtml(text).replaceAll("`", "&#96;");
}

function escapeRegExp(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
