(() => {
  'use strict';

  const app = document.getElementById('app');
  const loading = document.getElementById('loading');
  const nav = document.getElementById('site-nav');
  const navToggle = document.getElementById('nav-toggle');
  const brandTitle = document.getElementById('brand-title');

  const backToTop = document.createElement('button');
  backToTop.type = 'button';
  backToTop.className = 'back-to-top';
  backToTop.setAttribute('aria-label', 'Back to top');
  backToTop.setAttribute('title', 'Back to top');
  backToTop.innerHTML = '<span aria-hidden="true">↑</span>';
  document.body.appendChild(backToTop);

  // Keep the button in the visible bottom-right corner even while a mobile
  // browser is pinch-zoomed or the visual viewport is panned. We do not
  // disable zoom; instead we compensate for the difference between the
  // layout viewport and the visual viewport when the API is available.
  let topButtonFrame = 0;
  function positionBackToTop() {
    if (topButtonFrame) return;
    topButtonFrame = requestAnimationFrame(() => {
      topButtonFrame = 0;
      const vv = window.visualViewport;
      if (!vv || window.matchMedia('(min-width: 561px)').matches) {
        backToTop.style.removeProperty('--top-button-right');
        backToTop.style.removeProperty('--top-button-bottom');
        return;
      }

      // At normal scale, native fixed positioning is preferable because it
      // also honors safe-area insets. Only compensate when pinch zoom/pan
      // creates a visual viewport smaller or offset from the layout viewport.
      if (Math.abs(vv.scale - 1) < 0.01 && Math.abs(vv.offsetLeft) < 0.5 && Math.abs(vv.offsetTop) < 0.5) {
        backToTop.style.removeProperty('--top-button-right');
        backToTop.style.removeProperty('--top-button-bottom');
        return;
      }

      const layoutWidth = document.documentElement.clientWidth;
      const layoutHeight = document.documentElement.clientHeight;
      const margin = 12;
      const rightGap = Math.max(margin, layoutWidth - (vv.offsetLeft + vv.width) + margin);
      const bottomGap = Math.max(margin, layoutHeight - (vv.offsetTop + vv.height) + margin);
      backToTop.style.setProperty('--top-button-right', `${rightGap}px`);
      backToTop.style.setProperty('--top-button-bottom', `${bottomGap}px`);
    });
  }

  positionBackToTop();
  window.addEventListener('resize', positionBackToTop, { passive: true });
  window.addEventListener('orientationchange', positionBackToTop, { passive: true });
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', positionBackToTop, { passive: true });
    window.visualViewport.addEventListener('scroll', positionBackToTop, { passive: true });
  }

  const state = { data: null };

  const esc = (value = '') => String(value)
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

  const enc = (value = '') => encodeURIComponent(String(value));

  function externalLink(url, label) {
    if (!url) return '';
    return `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`;
  }

  function route() {
    const raw = location.hash.replace(/^#/, '') || 'home';
    const [path, queryString = ''] = raw.split('?');
    const parts = path.split('/').filter(Boolean).map(decodeURIComponent);
    return { page: parts[0] || 'home', arg: parts[1] || '', params: new URLSearchParams(queryString) };
  }

  function setCurrentNav(page) {
    [...nav.querySelectorAll('a')].forEach(a => {
      const target = a.getAttribute('href').replace('#', '');
      if (target === page || (page === 'year' && target === 'years') || (page === 'conference' && target === 'conferences') || (page === 'tag' && target === 'tags')) {
        a.setAttribute('aria-current', 'page');
      } else {
        a.removeAttribute('aria-current');
      }
    });
  }

  function comparePageOrder(a, b) {
    const aHasPage = a.pageStart !== null && a.pageStart !== undefined && Number.isFinite(Number(a.pageStart));
    const bHasPage = b.pageStart !== null && b.pageStart !== undefined && Number.isFinite(Number(b.pageStart));
    if (aHasPage !== bHasPage) return aHasPage ? -1 : 1;
    if (aHasPage && Number(a.pageStart) !== Number(b.pageStart)) return Number(a.pageStart) - Number(b.pageStart);

    // If page metadata is absent or tied, preserve the source BibTeX order as
    // much as possible. This also gives deterministic ordering for entries
    // without a pages field.
    const byFile = String(a.sourceBib || '').localeCompare(String(b.sourceBib || ''));
    if (byFile) return byFile;
    const bySource = Number(a.sourceOrder ?? Number.MAX_SAFE_INTEGER) - Number(b.sourceOrder ?? Number.MAX_SAFE_INTEGER);
    if (bySource) return bySource;
    return a.title.localeCompare(b.title);
  }

  function sortPapers(papers) {
    return [...papers].sort((a, b) => {
      const byYear = Number(b.year) - Number(a.year);
      if (byYear) return byYear;
      const byCollection = (a.collection === 'survey' ? 1 : 0) - (b.collection === 'survey' ? 1 : 0);
      if (byCollection) return byCollection;
      const byConference = String(a.conference || '').localeCompare(String(b.conference || ''));
      if (byConference) return byConference;
      return comparePageOrder(a, b);
    });
  }

  function sortPapersByPage(papers) {
    return [...papers].sort(comparePageOrder);
  }

  function allRecords() {
    return [...(state.data.papers || []), ...(state.data.surveys || [])];
  }

  function coverageRecords() {
    return state.data.coverage || [];
  }

  function coverageRecord(conference, year) {
    return coverageRecords().find(item => item.conference === conference && String(item.year) === String(year));
  }

  function coverageStatusLabel(status) {
    return ({ complete: 'Surveyed', partial: 'Partial', planned: 'Planned' })[status] || '';
  }

  function coverageBadge(status) {
    const label = coverageStatusLabel(status);
    return label ? `<span class="coverage-badge coverage-${esc(status)}">${esc(label)}</span>` : '';
  }

  function coverageEmptyMessage(status) {
    if (status === 'complete') return 'Surveyed; no included papers are recorded for this conference-year.';
    if (status === 'partial') return 'This conference-year is marked as partially surveyed.';
    if (status === 'planned') return 'This conference-year is listed for future surveying.';
    return 'No included papers are recorded for this conference-year.';
  }

  function updateTargetLinks(update) {
    let targets = Array.isArray(update.targets) ? update.targets : [];
    if (!targets.length && update.collection === 'survey') {
      targets = [{ collection: 'survey', label: 'Surveys' }];
    } else if (!targets.length && update.conference) {
      targets = [{
        collection: 'conference', conference: update.conference, year: update.year || '',
        label: `${update.conference}${update.year ? ` ${update.year}` : ''}`
      }];
    }
    const seen = new Set();
    const links = targets.map(target => {
      const key = `${target.collection || ''}|${target.conference || ''}|${target.year || ''}`;
      if (seen.has(key)) return '';
      seen.add(key);
      if (target.collection === 'survey') {
        return `<a class="update-target" href="#surveys">${esc(target.label || 'Surveys')}</a>`;
      }
      if (!target.conference) return '';
      const href = `#conference/${enc(target.conference)}${target.year ? `?jump=${enc(target.year)}` : ''}`;
      const label = target.label || `${target.conference}${target.year ? ` ${target.year}` : ''}`;
      return `<a class="update-target" href="${href}">${esc(label)}</a>`;
    }).filter(Boolean);
    return links.length ? `<div class="update-target-list">${links.join('')}</div>` : '';
  }

  function sortSearchPapers(papers, mode) {
    const list = [...papers];
    if (mode === 'title') {
      return list.sort((a, b) => a.title.localeCompare(b.title) || Number(b.year) - Number(a.year) || comparePageOrder(a, b));
    }
    if (mode === 'year-asc') {
      return list.sort((a, b) => Number(a.year) - Number(b.year)
        || String(a.conference || '').localeCompare(String(b.conference || ''))
        || comparePageOrder(a, b));
    }
    if (mode === 'conference') {
      return list.sort((a, b) => String(a.conference || 'Survey').localeCompare(String(b.conference || 'Survey'))
        || Number(b.year) - Number(a.year)
        || comparePageOrder(a, b));
    }
    return sortPapers(list);
  }

  const NON_RESOLVING_DOI_PREFIXES = ['10.5555/'];

  function doiResolverUrl(doi) {
    const value = String(doi || '').trim();
    if (!value) return '';
    const lowered = value.toLowerCase();
    if (NON_RESOLVING_DOI_PREFIXES.some(prefix => lowered.startsWith(prefix))) return '';
    return `https://doi.org/${value}`;
  }

  function paperPrimaryUrl(p) {
    // Prefer a normal, resolvable DOI.  Some bibliographic databases put
    // DOI-shaped test identifiers such as 10.5555/... in the doi field; for
    // those, use the BibTeX url instead of sending the user to doi.org.
    const doiUrl = doiResolverUrl(p.doi);
    if (doiUrl) return doiUrl;
    if (p.url) return p.url;
    return '';
  }

  function paperCard(p) {
    const primary = paperPrimaryUrl(p);
    const title = primary ? `<a href="${esc(primary)}" target="_blank" rel="noopener noreferrer">${esc(p.title)}</a>` : esc(p.title);
    const tags = (p.tags || []).map(t => `<a class="tag" href="#tag/${enc(t)}">${esc(t)}</a>`).join('');
    const doiUrl = doiResolverUrl(p.doi);
    const doi = doiUrl ? externalLink(doiUrl, 'DOI') : '';
    const source = p.sourcePath ? `<a href="${esc(p.sourcePath)}" download="${esc(p.sourceFileName || 'paper.bib')}">Source .bib</a>` : '';
    const raw = p.bibtex ? `<button type="button" class="copy-bib" data-bib-id="${esc(p.id)}">Copy BibTeX</button>` : '';
    const actions = [doi, source, raw].filter(Boolean).join('');
    const bibliographicMeta = p.collection === 'survey'
      ? `<span>Survey</span><span>${esc(p.year)}</span>`
      : `<span><a href="#conference/${enc(p.conference)}">${esc(p.conference)}</a></span><span><a href="#year/${enc(p.year)}">${esc(p.year)}</a></span>`;

    return `<article class="paper-card">
      <h3 class="paper-title">${title}</h3>
      <p class="paper-authors">${esc(p.authorText || 'Unknown author')}</p>
      <div class="paper-meta">
        ${bibliographicMeta}
        ${p.pages ? `<span>pp. ${esc(p.pages)}</span>` : ''}
        <span>${esc(p.key)}</span>
      </div>
      ${tags ? `<div class="tag-list" aria-label="Tags">${tags}</div>` : ''}
      ${actions ? `<div class="paper-actions">${actions}</div>` : ''}
    </article>`;
  }

  function paperList(papers) {
    if (!papers.length) return '<div class="empty-state">No papers match this view.</div>';
    return `<div class="paper-list">${papers.map(paperCard).join('')}</div>`;
  }

  function breadcrumbs(items) {
    return `<nav class="breadcrumbs" aria-label="Breadcrumb">${items.map((item, i) =>
      i === items.length - 1 ? esc(item.label) : `<a href="${esc(item.href)}">${esc(item.label)}</a> / `
    ).join('')}</nav>`;
  }

  function stats() {
    const f = state.data.facets;
    return `<div class="stats-grid">
      <div class="stat-card"><span class="stat-value">${f.paperCount}</span><span class="stat-label">conference papers</span></div>
      <div class="stat-card"><span class="stat-value">${f.yearCount}</span><span class="stat-label">years</span></div>
      <div class="stat-card"><span class="stat-value">${f.conferenceCount}</span><span class="stat-label">conferences</span></div>
      <div class="stat-card"><span class="stat-value">${f.tagCount}</span><span class="stat-label">tags</span></div>
    </div>`;
  }

  function renderHome() {
    const { site, papers, surveys = [], news, sourceUpdates, facets } = state.data;
    const latestPapers = sortPapers(papers).slice(0, site.homeRecentPapers || 12);
    const updates = [
      ...(news || []).map(n => ({...n, kind: 'news'})),
      ...(sourceUpdates || []).map(u => ({
        date: u.date,
        title: u.title || (u.collection === 'survey'
          ? `Survey bibliography update${u.year ? `: ${u.year}` : ''}`
          : `Bibliography update: ${u.conference} ${u.year || ''}`.trim()),
        text: u.text || `${u.paperCount} entr${u.paperCount === 1 ? 'y' : 'ies'} currently in ${u.file}.`,
        kind: u.kind || 'source',
        targets: u.targets || [] ,
        collection: u.collection || '', conference: u.conference || '', year: u.year || ''
      }))
    ].sort((a,b) => String(b.date).localeCompare(String(a.date))).slice(0, site.homeRecentUpdates || 8);

    const years = facets.years.slice(0, 6).map(y => `<a class="nav-card" href="#year/${enc(y.value)}"><strong>${esc(y.value)}</strong><span>${y.count} papers · ${y.coveredConferences ?? y.conferences} covered conferences</span></a>`).join('');
    const conferences = facets.conferences.slice(0, 8).map(c => `<a class="nav-card" href="#conference/${enc(c.value)}"><strong>${esc(c.value)}</strong><span>${esc(c.label || c.value)} · ${c.count} papers · ${c.coveredYears || 0} covered years</span></a>`).join('');

    app.innerHTML = `
      <section class="hero">
        <p class="eyebrow">Conference-paper bibliography</p>
        <h1>${esc(site.siteTitle)}</h1>
        <p class="hero-subtitle">${esc(site.siteSubtitle)}</p>
        <div class="notice" aria-label="Scope notice">
          <ul>
            <li><strong>The main database contains conference papers only.</strong> Survey papers are maintained separately and are excluded from the year and conference counts.</li>
            <li>The database is intended primarily for <strong>tracking research trends</strong> in parameterized complexity.</li>
            <li>If you notice a missing paper or incorrect metadata, <strong>please contact the maintainers.</strong></li>
          </ul>
        </div>
        <form class="search-hero" id="home-search">
          <input name="q" type="search" autocomplete="off" placeholder="Search titles, authors, tags, conferences…" aria-label="Search bibliography">
          <button class="button" type="submit">Search</button>
        </form>
        ${stats()}
      </section>

      <section class="section">
        <div class="section-heading"><div><p class="eyebrow">Browse</p><h2>Recent years</h2></div><a href="#years">All years</a></div>
        <div class="card-grid">${years || '<div class="empty-state">Add BibTeX files to begin.</div>'}</div>
      </section>

      <section class="section">
        <div class="section-heading"><div><p class="eyebrow">Browse</p><h2>Conferences</h2></div><a href="#conferences">All conferences</a></div>
        <div class="card-grid">${conferences || '<div class="empty-state">No conferences yet.</div>'}</div>
      </section>

      <section class="section">
        <div class="section-heading"><div><p class="eyebrow">Separate collection</p><h2>Surveys</h2></div><a href="#surveys">Browse surveys</a></div>
        <a class="nav-card survey-card" href="#surveys"><strong>${surveys.length} survey paper${surveys.length === 1 ? '' : 's'}</strong><span>Kept separate from the conference and year views.</span></a>
      </section>

      <section class="section">
        <div class="section-heading"><div><p class="eyebrow">News</p><h2>Latest updates</h2></div></div>
        <div class="news-list">${updates.length ? updates.map(u => `<article class="news-item"><time>${esc(u.date)}</time><h3>${esc(u.title)}</h3><p>${esc(u.text || '')}</p>${updateTargetLinks(u)}</article>`).join('') : '<div class="empty-state">No updates yet.</div>'}</div>
      </section>

      <section class="section">
        <div class="section-heading"><div><p class="eyebrow">By publication year</p><h2>Papers from recent years</h2></div><a href="#search">Open search</a></div>
        ${paperList(latestPapers)}
      </section>`;

    document.getElementById('home-search')?.addEventListener('submit', e => {
      e.preventDefault();
      const q = new FormData(e.currentTarget).get('q')?.toString().trim() || '';
      location.hash = `#search?q=${enc(q)}`;
    });
  }

  function renderYears() {
    const { facets } = state.data;
    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'Years'}])}
      <section class="page-intro"><p class="eyebrow">Browse</p><h1>By year</h1><p>Select a year to see papers grouped by conference.</p></section>
      <div class="card-grid">${facets.years.map(y => `<a class="nav-card" href="#year/${enc(y.value)}"><strong>${esc(y.value)}</strong><span>${y.count} papers · ${y.coveredConferences ?? y.conferences} covered conferences</span></a>`).join('') || '<div class="empty-state">No years yet.</div>'}</div>`;
  }

  function safeDomId(value = '') {
    return String(value).replace(/[^A-Za-z0-9_-]+/g, '-');
  }

  function bindJumpLinks() {
    document.querySelectorAll('[data-jump-target]').forEach(control => {
      control.addEventListener('click', () => {
        const target = document.getElementById(control.dataset.jumpTarget);
        if (target) {
          if (target instanceof HTMLDetailsElement) target.open = true;
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  function renderYear(year) {
    const papers = state.data.papers.filter(p => String(p.year) === String(year));
    const coverage = coverageRecords().filter(item => String(item.year) === String(year));
    const groups = new Map();
    coverage.forEach(item => { if (!groups.has(item.conference)) groups.set(item.conference, []); });
    papers.forEach(p => { if (!groups.has(p.conference)) groups.set(p.conference, []); groups.get(p.conference).push(p); });
    const entries = [...groups.entries()].sort(([a],[b]) => a.localeCompare(b));
    const jumps = entries.filter(([, list]) => list.length > 0).map(([conf, list]) => {
      const targetId = `year-${safeDomId(year)}-conference-${safeDomId(conf)}`;
      return `<button type="button" class="jump-chip" data-jump-target="${esc(targetId)}"><strong>${esc(conf)}</strong><span>${list.length}</span></button>`;
    }).join('');
    const body = entries.map(([conf, list]) => {
      const targetId = `year-${safeDomId(year)}-conference-${safeDomId(conf)}`;
      const coverageItem = coverageRecord(conf, year);
      const status = coverageItem?.status || '';
      return `
      <details class="subgroup collapsible-subgroup jump-target" id="${esc(targetId)}" open>
        <summary class="subgroup-heading collapsible-heading"><span class="subgroup-title"><a href="#conference/${enc(conf)}">${esc(conf)}</a> ${coverageBadge(status)}</span><span class="group-count">${list.length} paper${list.length === 1 ? '' : 's'}</span></summary>
        <div class="collapsible-content">${list.length ? paperList(sortPapersByPage(list)) : `<div class="coverage-empty">${esc(coverageEmptyMessage(status))}</div>`}</div>
      </details>`;
    }).join('');
    const covered = coverage.length;
    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'Years',href:'#years'},{label:year}])}
      <section class="page-intro"><p class="eyebrow">Year</p><h1>${esc(year)}</h1><p>${papers.length} conference papers · ${covered} conference${covered === 1 ? '' : 's'} tracked for coverage.</p></section>
      ${jumps ? `<section class="jump-panel" aria-label="Jump to conference"><div class="jump-panel-heading"><h2>Jump to conference</h2><p>Only conferences with at least one included paper are shown here.</p></div><div class="jump-chip-list">${jumps}</div></section>` : ''}
      ${body || '<div class="empty-state">No papers or coverage records for this year.</div>'}`;
    bindJumpLinks();
  }

  function renderConferences() {
    const { facets } = state.data;
    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'Conferences'}])}
      <section class="page-intro"><p class="eyebrow">Browse</p><h1>By conference</h1><p>Select a conference to see its papers grouped by year.</p></section>
      <div class="card-grid">${facets.conferences.map(c => `<a class="nav-card" href="#conference/${enc(c.value)}"><strong>${esc(c.value)}</strong><span>${esc(c.label || c.value)} · ${c.count} papers · ${c.coveredYears || 0} covered years</span></a>`).join('') || '<div class="empty-state">No conferences yet.</div>'}</div>`;
  }

  function renderSurveys() {
    const surveys = sortPapers(state.data.surveys || []);
    const groups = new Map();
    surveys.forEach(p => { if (!groups.has(p.year)) groups.set(p.year, []); groups.get(p.year).push(p); });
    const body = [...groups.entries()].sort(([a], [b]) => Number(b) - Number(a)).map(([year, list]) => `
      <section class="subgroup">
        <div class="subgroup-heading"><h3>${esc(year)}</h3><span class="group-count">${list.length} paper${list.length === 1 ? '' : 's'}</span></div>
        ${paperList(sortPapers(list))}
      </section>`).join('');
    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'Surveys'}])}
      <section class="page-intro"><p class="eyebrow">Separate collection</p><h1>Surveys</h1><p>Survey papers are listed separately and do not contribute to the Years or Conferences views or their counts.</p></section>
      ${body || '<div class="empty-state">No survey papers yet. Add BibTeX files under <code>bib/survey/</code> or use <code>bib/survey.bib</code>.</div>'}`;
  }

  function renderConference(conference, params = new URLSearchParams()) {
    const papers = state.data.papers.filter(p => p.conference === conference);
    const coverage = coverageRecords().filter(item => item.conference === conference);
    const label = state.data.conferenceNames[conference] || conference;
    const groups = new Map();
    coverage.forEach(item => { if (!groups.has(String(item.year))) groups.set(String(item.year), []); });
    papers.forEach(p => { if (!groups.has(String(p.year))) groups.set(String(p.year), []); groups.get(String(p.year)).push(p); });
    const entries = [...groups.entries()].sort(([a],[b]) => Number(b)-Number(a));
    const maxCount = Math.max(1, ...entries.map(([, list]) => list.length));
    const chart = entries.map(([year, list]) => {
      const targetId = `conference-${safeDomId(conference)}-year-${safeDomId(year)}`;
      const width = list.length ? Math.max(7, Math.round((list.length / maxCount) * 100)) : 0;
      return `<button type="button" class="year-bar-row" data-jump-target="${esc(targetId)}" aria-label="Jump to ${esc(year)}, ${list.length} papers">
        <span class="year-bar-label">${esc(year)}</span>
        <span class="year-bar-track"><span class="year-bar-fill" style="width:${width}%"></span></span>
        <span class="year-bar-count">${list.length}</span>
      </button>`;
    }).join('');
    const body = entries.map(([year, list]) => {
      const targetId = `conference-${safeDomId(conference)}-year-${safeDomId(year)}`;
      const coverageItem = coverageRecord(conference, year);
      const status = coverageItem?.status || '';
      return `
      <details class="subgroup collapsible-subgroup jump-target" id="${esc(targetId)}" open>
        <summary class="subgroup-heading collapsible-heading"><span class="subgroup-title"><a href="#year/${enc(year)}">${esc(year)}</a> ${coverageBadge(status)}</span><span class="group-count">${list.length} paper${list.length === 1 ? '' : 's'}</span></summary>
        <div class="collapsible-content">${list.length ? paperList(sortPapersByPage(list)) : `<div class="coverage-empty">${esc(coverageEmptyMessage(status))}</div>`}</div>
      </details>`;
    }).join('');
    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'Conferences',href:'#conferences'},{label:conference}])}
      <section class="page-intro"><p class="eyebrow">Conference</p><h1>${esc(conference)}</h1><p>${esc(label)} · ${papers.length} papers · ${coverage.length} years tracked for coverage.</p></section>
      ${chart ? `<section class="jump-panel conference-chart" aria-label="Papers by year"><div class="jump-panel-heading"><h2>Papers by year</h2><p>Click a bar to jump to that year; zero-paper surveyed years are retained.</p></div><div class="year-bar-chart">${chart}</div></section>` : ''}
      ${body || '<div class="empty-state">No papers or coverage records for this conference.</div>'}`;
    bindJumpLinks();
    const jumpYear = params.get('jump');
    if (jumpYear) {
      requestAnimationFrame(() => {
        const target = document.getElementById(`conference-${safeDomId(conference)}-year-${safeDomId(jumpYear)}`);
        if (target) {
          if (target instanceof HTMLDetailsElement) target.open = true;
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    }
  }

  function renderCoverage() {
    const coverage = coverageRecords();
    const groups = new Map();
    coverage.forEach(item => {
      if (!groups.has(item.conference)) groups.set(item.conference, []);
      groups.get(item.conference).push(item);
    });
    const body = [...groups.entries()].sort(([a],[b]) => a.localeCompare(b)).map(([conference, items]) => {
      const sorted = [...items].sort((a,b) => Number(b.year) - Number(a.year));
      const complete = sorted.filter(item => item.status === 'complete').length;
      const partial = sorted.filter(item => item.status === 'partial').length;
      const years = sorted.map(item => {
        const href = `#conference/${enc(conference)}?jump=${enc(item.year)}`;
        return `<a class="coverage-year-chip" href="${href}"><strong>${esc(item.year)}</strong>${coverageBadge(item.status)}<span>${item.count} paper${item.count === 1 ? '' : 's'}</span></a>`;
      }).join('');
      return `<details class="coverage-conference">
        <summary><span><strong>${esc(conference)}</strong> · ${esc(state.data.conferenceNames[conference] || conference)}</span><span>${sorted.length} years · ${complete} surveyed${partial ? ` · ${partial} partial` : ''}</span></summary>
        <div class="coverage-year-list">${years}</div>
      </details>`;
    }).join('');
    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'Coverage'}])}
      <section class="page-intro"><p class="eyebrow">Data quality</p><h1>Survey coverage</h1><p>An existing <code>bib/CONF/CONF_YEAR.bib</code> file is treated as surveyed by default, including an empty file representing zero included papers. Use <code>data/coverage.json</code> to override a conference-year as <strong>partial</strong> or <strong>planned</strong>.</p></section>
      <div class="coverage-legend">${coverageBadge('complete')} ${coverageBadge('partial')} ${coverageBadge('planned')}</div>
      <div class="coverage-list">${body || '<div class="empty-state">No coverage records yet.</div>'}</div>`;
  }

  function renderTags() {
    const tags = state.data.facets.tags;
    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'Tags'}])}
      <section class="page-intro"><p class="eyebrow">Browse</p><h1>Tags</h1><p>Tags come from the BibTeX <code>keywords</code> or <code>tags</code> field.</p></section>
      <div class="tag-cloud">${tags.map(t => `<a class="tag" href="#tag/${enc(t.value)}">${esc(t.value)} <span class="tag-count">${t.count}</span></a>`).join('') || '<div class="empty-state">No tags yet.</div>'}</div>`;
  }

  function renderTag(tag) {
    const papers = allRecords().filter(p => (p.tags || []).some(t => t.toLowerCase() === tag.toLowerCase()));
    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'Tags',href:'#tags'},{label:tag}])}
      <section class="page-intro"><p class="eyebrow">Tag</p><h1>${esc(tag)}</h1><p>${papers.length} matching papers.</p></section>
      ${paperList(sortPapers(papers))}`;
  }

  function searchableText(p) {
    return [p.title, p.authorText, p.conference, p.conferenceName, p.collection === 'survey' ? 'survey' : '', p.year, p.key, ...(p.tags || [])].join(' ').toLowerCase();
  }

  function filterCheckboxGroup(name, label, items, selectedValues) {
    const selected = new Set(selectedValues.map(String));
    const options = items.map(item => {
      const value = String(item.value);
      const checked = selected.has(value) ? ' checked' : '';
      const accessibleLabel = item.label && item.label !== value ? `${value}: ${item.label}` : value;
      const searchable = `${value} ${item.label || ''}`.toLowerCase();
      return `<label class="filter-option" title="${esc(accessibleLabel)}" data-filter-text="${esc(searchable)}">
        <input type="checkbox" name="${esc(name)}" value="${esc(value)}"${checked}>
        <span class="filter-option-text">${esc(value)}</span>
        <span class="filter-option-count">${esc(item.count)}</span>
      </label>`;
    }).join('');

    return `<details class="filter-group" data-filter-group="${esc(name)}">
      <summary><span>${esc(label)}</span><span class="filter-selected-count" data-selected-count="${esc(name)}">${selected.size ? `${selected.size} selected` : 'All'}</span></summary>
      <div class="filter-group-body">
        <input class="filter-search-input" type="search" autocomplete="off" placeholder="Search ${esc(label.toLowerCase())}…" aria-label="Search ${esc(label)} options" data-filter-search="${esc(name)}">
        <div class="filter-options">${options || '<span class="filter-empty">No options</span>'}</div>
        <div class="filter-no-match" hidden>No matching options.</div>
      </div>
    </details>`;
  }

  function renderSearch(params) {
    const { facets } = state.data;
    const initial = {
      q: params.get('q') || '',
      years: params.getAll('year'),
      conferences: params.getAll('conference'),
      tags: params.getAll('tag'),
      sort: params.get('sort') || 'year-desc'
    };

    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'Search'}])}
      <section class="page-intro"><p class="eyebrow">Find papers</p><h1>Search</h1><p>Free-text and tag search include the separate survey collection. Year and conference filters apply only to conference papers. Within each checkbox group, selections are combined with OR; different groups are combined with AND.</p></section>
      <form class="search-panel" id="search-form">
        <div class="search-query-row">
          <label class="search-query-label" for="search-q">Search text</label>
          <input id="search-q" name="q" type="search" autocomplete="off" value="${esc(initial.q)}" placeholder="Title, author, tag, key…">
        </div>
        <div class="filter-grid">
          ${filterCheckboxGroup('conference', 'Conference', facets.conferences, initial.conferences)}
          ${filterCheckboxGroup('year', 'Year', facets.years, initial.years)}
          ${filterCheckboxGroup('tag', 'Tag', facets.tags, initial.tags)}
        </div>
      </form>
      <div class="results-bar"><span id="result-count"></span><div class="results-controls"><label for="search-sort">Sort</label><select id="search-sort" name="sort" form="search-form"><option value="year-desc"${initial.sort === 'year-desc' ? ' selected' : ''}>Year: newest / proceedings order</option><option value="year-asc"${initial.sort === 'year-asc' ? ' selected' : ''}>Year: oldest / proceedings order</option><option value="conference"${initial.sort === 'conference' ? ' selected' : ''}>Conference / year / page</option><option value="title"${initial.sort === 'title' ? ' selected' : ''}>Title A–Z</option></select><button class="clear-button" id="clear-search" type="button">Clear filters</button></div></div>
      <div id="search-results"></div>`;

    const form = document.getElementById('search-form');
    const resultCount = document.getElementById('result-count');
    const results = document.getElementById('search-results');

    function update(pushHash = true) {
      const fd = new FormData(form);
      const rawQ = (fd.get('q') || '').toString().trim();
      const q = rawQ.toLowerCase();
      const years = fd.getAll('year').map(String);
      const conferences = fd.getAll('conference').map(String);
      const tags = fd.getAll('tag').map(String);
      const sortMode = (fd.get('sort') || 'year-desc').toString();
      const filtered = sortSearchPapers(allRecords().filter(p => {
        if (q && !searchableText(p).includes(q)) return false;
        if (years.length && (p.collection === 'survey' || !years.includes(String(p.year)))) return false;
        if (conferences.length && (p.collection === 'survey' || !conferences.includes(p.conference))) return false;
        if (tags.length && !tags.some(tag => (p.tags || []).includes(tag))) return false;
        return true;
      }), sortMode);
      resultCount.textContent = `${filtered.length} result${filtered.length === 1 ? '' : 's'}`;
      results.innerHTML = paperList(filtered);
      bindCopyButtons();
      if (pushHash) {
        const out = new URLSearchParams();
        if (rawQ) out.set('q', rawQ);
        years.forEach(year => out.append('year', year));
        conferences.forEach(conference => out.append('conference', conference));
        tags.forEach(tag => out.append('tag', tag));
        if (sortMode !== 'year-desc') out.set('sort', sortMode);
        history.replaceState(null, '', `#search${out.toString() ? `?${out}` : ''}`);
      }
    }

    function updateSelectedCounts() {
      ['conference', 'year', 'tag'].forEach(name => {
        const count = form.querySelectorAll(`input[name="${name}"]:checked`).length;
        const badge = form.querySelector(`[data-selected-count="${name}"]`);
        if (badge) badge.textContent = count ? `${count} selected` : 'All';
      });
    }

    function filterOptions(input) {
      const groupName = input.dataset.filterSearch;
      const group = form.querySelector(`[data-filter-group="${groupName}"]`);
      if (!group) return;
      const q = input.value.trim().toLowerCase();
      let visible = 0;
      group.querySelectorAll('.filter-option').forEach(option => {
        const show = !q || (option.dataset.filterText || '').includes(q);
        option.hidden = !show;
        if (show) visible += 1;
      });
      const empty = group.querySelector('.filter-no-match');
      if (empty) empty.hidden = visible !== 0;
    }

    document.getElementById('search-sort')?.addEventListener('change', () => update(true));

    form.querySelectorAll('.filter-search-input').forEach(input => {
      input.addEventListener('input', e => {
        e.stopPropagation();
        filterOptions(input);
      });
    });
    form.addEventListener('input', e => {
      if (e.target.classList.contains('filter-search-input')) return;
      update(true);
    });
    form.addEventListener('change', e => {
      if (e.target.matches('input[type="checkbox"]')) updateSelectedCounts();
      update(true);
    });
    document.getElementById('clear-search').addEventListener('click', () => {
      form.reset();
      form.querySelectorAll('.filter-search-input').forEach(input => filterOptions(input));
      updateSelectedCounts();
      update(true);
    });
    updateSelectedCounts();
    update(false);
  }

  function renderAbout() {
    const { site, generatedAt } = state.data;
    const contact = site.contactUrl ? `<p>${externalLink(site.contactUrl, 'Contact / report an omission')}</p>` : '<p>Set <code>contactUrl</code> in <code>data/site.config.json</code> to add a public contact link.</p>';
    app.innerHTML = `${breadcrumbs([{label:'Home',href:'#home'},{label:'About'}])}
      <section class="page-intro"><p class="eyebrow">About</p><h1>Scope and maintenance</h1><p>This is a curated conference bibliography for research substantially related to parameterized complexity.</p></section>
      <div class="about-grid">
        <article class="about-card"><h3>Scope</h3><p>The main bibliography contains papers accepted to international conferences. Survey papers may be maintained in a separate collection; they are excluded from the Years and Conferences views and counts. The site is designed for overviewing research activity and trends, not for replacing publisher pages, DBLP, or archival repositories.</p>${contact}</article>
        <article class="about-card"><h3>Coverage</h3><p>Coverage is tracked separately from paper counts so that a surveyed conference-year with zero included papers is distinguishable from a year that has not been surveyed. Existing conference-year BibTeX files count as surveyed unless overridden in <code>data/coverage.json</code>.</p><p><a href="#coverage">Open coverage view</a></p></article>
        <article class="about-card"><h3>Metadata</h3><p>Entries are generated from BibTeX files. Tags are curator-supplied through <code>keywords</code> or <code>tags</code>. Paper text and abstracts are not copied into this site by default.</p></article>
        <article class="about-card"><h3>Copyright and links</h3><p>The site stores bibliographic metadata and links to external paper pages. Copyright in linked papers remains with the respective authors and/or publishers. Reuse of third-party metadata should follow the terms of its original source.</p></article>
        <article class="about-card"><h3>LLM disclosure</h3><p>This website was developed with assistance from a generative AI / large language model. LLM-assisted collection or classification may also be used during maintenance, but maintainers should verify inclusion decisions and bibliographic metadata.</p></article>
      </div>
      <p class="section" style="color:var(--muted);font-size:13px">Database generated: ${esc(generatedAt)}.</p>`;
  }

  function bindCopyButtons() {
    document.querySelectorAll('.copy-bib').forEach(btn => {
      btn.addEventListener('click', async () => {
        const paper = allRecords().find(p => p.id === btn.dataset.bibId);
        if (!paper?.bibtex) return;
        try {
          await navigator.clipboard.writeText(paper.bibtex);
          const old = btn.textContent; btn.textContent = 'Copied';
          setTimeout(() => { btn.textContent = old; }, 1200);
        } catch (_) {
          window.prompt('Copy BibTeX:', paper.bibtex);
        }
      });
    });
  }

  function render() {
    const r = route();
    setCurrentNav(r.page);
    nav.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
    switch (r.page) {
      case 'home': renderHome(); break;
      case 'years': renderYears(); break;
      case 'year': renderYear(r.arg); break;
      case 'conferences': renderConferences(); break;
      case 'conference': renderConference(r.arg, r.params); break;
      case 'surveys': renderSurveys(); break;
      case 'coverage': renderCoverage(); break;
      case 'tags': renderTags(); break;
      case 'tag': renderTag(r.arg); break;
      case 'search': renderSearch(r.params); break;
      case 'about': renderAbout(); break;
      default: location.hash = '#home'; return;
    }
    bindCopyButtons();
    window.scrollTo({top: 0, behavior: 'instant'});
  }

  navToggle.addEventListener('click', () => {
    const open = nav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(open));
  });

  backToTop.addEventListener('click', () => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  });


  window.addEventListener('hashchange', render);

  fetch('data/publications.json', {cache: 'no-cache'})
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
    .then(data => {
      state.data = data;
      document.title = data.site.siteTitle;
      brandTitle.textContent = data.site.shortTitle || data.site.siteTitle;
      loading.hidden = true;
      app.hidden = false;
      render();
    })
    .catch(err => {
      loading.innerHTML = `<strong>Could not load the generated bibliography.</strong><br><small>${esc(err.message)}. Run <code>python scripts/build.py</code> before publishing.</small>`;
    });
})();
