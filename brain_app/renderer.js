import { animate, stagger } from './node_modules/animejs/dist/modules/index.js';

const API = window.BRAIN_API_URL || 'http://127.0.0.1:7842';

// ── Domain config ─────────────────────────────────────────────────────────────

const DOMAINS = {
  'Travail':           { key: 'travail',       label: 'Travail',       color: 'var(--d-travail)' },
  'Apprentissage':     { key: 'apprentissage', label: 'Apprentissage', color: 'var(--d-apprentissage)' },
  'Projets perso':     { key: 'projets',       label: 'Projets perso', color: 'var(--d-projets)' },
  'Jeux vidéos':       { key: 'jeux',          label: 'Jeux vidéos',   color: 'var(--d-jeux)' },
  'Plantes':           { key: 'plantes',       label: 'Plantes',       color: 'var(--d-plantes)' },
  'Organisation TDAH': { key: 'tdah',          label: 'Organisation',  color: 'var(--d-tdah)' },
};
const DOMAIN_ORDER = ['Travail', 'Apprentissage', 'Projets perso', 'Jeux vidéos', 'Plantes', 'Organisation TDAH'];
const META_DOM = { key: 'meta', label: 'Méta-fiches', color: 'var(--d-meta)' };

// ── SVG Icons ─────────────────────────────────────────────────────────────────

const ICONS = {
  logo: `<svg viewBox="0 0 64 64" fill="none" width="26" height="26">
    <circle cx="32" cy="32" r="9.5" stroke="currentColor" stroke-width="2.4"/>
    <circle cx="32" cy="32" r="2.6" fill="currentColor"/>
    <ellipse cx="32" cy="32" rx="22" ry="22" stroke="currentColor" stroke-width="1.4" opacity="0.28"/>
    <circle cx="51" cy="21" r="3.4" fill="currentColor"/>
    <circle cx="14" cy="44" r="2.6" fill="currentColor"/>
    <path d="M40.5 27 C45 23.5, 47.5 22.5, 51 21" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
    <path d="M24 38 C19.5 41, 16.5 42.5, 14 44" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
  </svg>`,
  star: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <path d="M12 3l2.4 5.6 6 .5-4.6 4 1.4 5.9L12 16.9 6.8 19l1.4-5.9L3.6 9.1l6-.5L12 3z" fill="currentColor"/>
  </svg>`,
  spark: `<svg viewBox="0 0 24 24" fill="none" width="17" height="17">
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  </svg>`,
  chev: `<svg viewBox="0 0 24 24" fill="none" width="14" height="14">
    <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  link: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <path d="M9 12h6M10 8H8a4 4 0 100 8h2M14 8h2a4 4 0 110 8h-2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
  </svg>`,
  clock: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-width="1.7"/>
    <path d="M12 7.5V12l3 2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
  </svg>`,
  grid: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <rect x="3.5" y="3.5" width="7" height="7" rx="1.6" stroke="currentColor" stroke-width="1.8"/>
    <rect x="13.5" y="3.5" width="7" height="7" rx="1.6" stroke="currentColor" stroke-width="1.8"/>
    <rect x="3.5" y="13.5" width="7" height="7" rx="1.6" stroke="currentColor" stroke-width="1.8"/>
    <rect x="13.5" y="13.5" width="7" height="7" rx="1.6" stroke="currentColor" stroke-width="1.8"/>
  </svg>`,
  nodes: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <circle cx="6" cy="6" r="2.6" stroke="currentColor" stroke-width="1.8"/>
    <circle cx="18" cy="9" r="2.6" stroke="currentColor" stroke-width="1.8"/>
    <circle cx="9" cy="18" r="2.6" stroke="currentColor" stroke-width="1.8"/>
    <path d="M8.1 7.2C12 8 14 8.2 15.6 8.4M7.4 8.3c.6 3 .9 5 1.1 7.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`,
  close: `<svg viewBox="0 0 24 24" fill="none" width="15" height="15">
    <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  </svg>`,
  arrow: `<svg viewBox="0 0 24 24" fill="none" width="15" height="15">
    <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  arrowLeft: `<svg viewBox="0 0 24 24" fill="none" width="15" height="15">
    <path d="M19 12H5M11 6l-6 6 6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
};

// ── State ─────────────────────────────────────────────────────────────────────

let state = {
  mode: 'grille',
  notes: [],
  featured: [],
  status: { total_notes: 0, meta_fiches_count: 0, last_sync: null },
  activeFilter: 'tous',
  sort: 'recent',
  linkedOnly: false,
  openNote: null,
  filteredList: [],
};

function getFiltered() {
  let list = state.notes.slice();
  if (state.activeFilter !== 'tous') list = list.filter(n => n.domaine === state.activeFilter);
  if (state.linkedOnly) list = list.filter(n => n.liens.length > 0);
  list.sort((a, b) => state.sort === 'recent' ? a._days - b._days : b._days - a._days);
  return list;
}

function setState(patch) {
  Object.assign(state, patch);
  const needsFilter = ['activeFilter', 'sort', 'linkedOnly', 'notes'].some(k => k in patch);
  if (needsFilter) state.filteredList = getFiltered();
  render();
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function daysAgo(dateStr) {
  if (!dateStr) return 999;
  return Math.max(0, Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000));
}

function relTime(days) {
  if (days <= 0) return "aujourd'hui";
  if (days === 1) return 'hier';
  if (days < 7) return `il y a ${days} j`;
  if (days < 30) return `il y a ${Math.round(days / 7)} sem`;
  return `il y a ${Math.round(days / 30)} mois`;
}

function relTimeFromDate(dateStr) {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "à l'instant";
  if (mins < 60) return `il y a ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `il y a ${hours}h`;
  return relTime(Math.floor(hours / 24));
}

function parseTags(raw) {
  if (!raw) return [];
  try { const p = JSON.parse(raw); return Array.isArray(p) ? p : []; }
  catch { return String(raw).split(',').map(t => t.trim()).filter(Boolean); }
}

function parseLiens(sourcesIds) {
  if (!sourcesIds) return [];
  try { const p = JSON.parse(sourcesIds); return Array.isArray(p) ? p.map(String) : []; }
  catch { return []; }
}

function domainConfig(domaine) {
  return DOMAINS[domaine] || { key: 'unknown', label: domaine || '?', color: 'var(--ink-3)' };
}

function mapNote(raw) {
  return {
    ...raw,
    id: String(raw.id),
    titre: raw.titre_court || '—',
    insight: raw.insight_cle || '',
    est_meta: Boolean(raw.est_meta_fiche),
    liens: parseLiens(raw.sources_ids),
    parsedTags: parseTags(raw.tags),
    _days: daysAgo(raw.date_capture),
  };
}

// ── Render: topbar ────────────────────────────────────────────────────────────

function renderTopbar() {
  document.getElementById('logo-slot').innerHTML = ICONS.logo;
  document.getElementById('star-icon').innerHTML = ICONS.star;
  document.getElementById('spark-icon').innerHTML = ICONS.spark;

  const btnG = document.getElementById('btn-grille');
  const btnC = document.getElementById('btn-constellation');
  btnG.innerHTML = `${ICONS.grid} Grille`;
  btnC.innerHTML = `${ICONS.nodes} Constellation`;
  btnG.classList.toggle('active', state.mode === 'grille');
  btnC.classList.toggle('active', state.mode === 'constellation');

  if (!btnG._bound) {
    btnG.addEventListener('click', () => setState({ mode: 'grille' }));
    btnC.addEventListener('click', () => setState({ mode: 'constellation' }));
    btnG._bound = true;
  }

  const { total_notes, meta_fiches_count } = state.status;
  document.getElementById('pill-stat').innerHTML =
    `<span class="dot"></span>${total_notes} notes · ${meta_fiches_count} synthèse${meta_fiches_count !== 1 ? 's' : ''}`;
}

// ── Render: featured cards ────────────────────────────────────────────────────

function renderFeatured() {
  const container = document.getElementById('featured-cards');
  if (!state.featured.length) { container.innerHTML = ''; return; }

  container.innerHTML = state.featured.map(n => {
    const dom = domainConfig(n.domaine);
    return `<div class="fcard" data-id="${n.id}" style="--accent:${dom.color}" tabindex="0" role="button">
      <div class="glow"></div>
      <div class="ftitle">${n.titre}</div>
      <div class="finsight">${n.insight}</div>
      <div class="fmeta">
        <span class="ddot"></span>
        <span class="metatime">${dom.label.toLowerCase()}</span>
        <span class="metatime" style="margin-left:auto">${relTime(n._days)}</span>
      </div>
    </div>`;
  }).join('');

  container.querySelectorAll('.fcard').forEach(el => {
    el.addEventListener('click', () => {
      const note = state.featured.find(n => n.id === el.dataset.id);
      if (note) openModal(note);
    });
  });

  animate(container.querySelectorAll('.fcard'), {
    opacity: [0, 1], translateY: ['10px', '0px'],
    delay: stagger(40), duration: 500, ease: 'outQuart',
  });
}

// ── Render: filters ───────────────────────────────────────────────────────────

function renderFilters() {
  const container = document.getElementById('filter-bar');
  const { activeFilter, sort, linkedOnly } = state;

  container.innerHTML = [
    `<button class="fpill${activeFilter === 'tous' ? ' active' : ''}" data-filter="tous">Tous</button>`,
    ...DOMAIN_ORDER.map(d => {
      const dom = domainConfig(d);
      return `<button class="fpill${activeFilter === d ? ' active' : ''}" data-filter="${d}" style="--accent:${dom.color}"><span class="ddot"></span>${dom.label}</button>`;
    }),
    `<span class="sep"></span>`,
    `<button class="fpill" id="btn-sort">${ICONS.clock}${sort === 'recent' ? 'Récents' : 'Anciens'}</button>`,
    `<button class="fpill toggle${linkedOnly ? ' active' : ''}" id="btn-linked">${ICONS.link}Liées</button>`,
  ].join('');

  container.querySelectorAll('[data-filter]').forEach(btn => {
    btn.addEventListener('click', () => setState({ activeFilter: btn.dataset.filter }));
  });
  document.getElementById('btn-sort').addEventListener('click', () =>
    setState({ sort: state.sort === 'recent' ? 'ancien' : 'recent' }));
  document.getElementById('btn-linked').addEventListener('click', () =>
    setState({ linkedOnly: !state.linkedOnly }));
}

// ── Render: sections ──────────────────────────────────────────────────────────

function renderSections() {
  const container = document.getElementById('sections-container');
  const { filteredList } = state;

  if (!filteredList.length) {
    container.innerHTML = `<div style="text-align:center;color:var(--ink-3);font-family:var(--font-mono);font-size:12px;padding:40px 0">aucune note ne correspond</div>`;
    return;
  }

  const regular = filteredList.filter(n => !n.est_meta);
  const meta = filteredList.filter(n => n.est_meta);
  const groups = {};
  DOMAIN_ORDER.forEach(d => { groups[d] = []; });
  regular.forEach(n => { if (groups[n.domaine]) groups[n.domaine].push(n); });

  let html = '';
  DOMAIN_ORDER.forEach(d => {
    if (!groups[d].length) return;
    html += buildSectionHtml(domainConfig(d), groups[d]);
  });
  if (meta.length) html += buildSectionHtml(META_DOM, meta);

  container.innerHTML = html;

  container.querySelectorAll('.shead').forEach(shead => {
    shead.addEventListener('click', () => {
      shead.classList.toggle('collapsed');
      shead.nextElementSibling?.classList.toggle('hidden');
    });
  });

  container.querySelectorAll('.ncard').forEach(el => {
    el.addEventListener('click', () => {
      const note = state.filteredList.find(n => n.id === el.dataset.id);
      if (note) openModal(note);
    });
  });

  const cards = container.querySelectorAll('.ncard');
  if (cards.length) {
    animate(cards, { opacity: [0, 1], translateY: ['8px', '0px'], delay: stagger(30), duration: 380, ease: 'outCubic' });
  }
}

function buildSectionHtml(dom, notes) {
  const count = String(notes.length).padStart(2, '0');
  return `<div class="section" style="--accent:${dom.color}">
    <div class="shead">
      <span class="ddot"></span>
      <span class="slabel">${dom.label}</span>
      <span class="scount">${count}</span>
      <span class="line"></span>
      <span class="chev">${ICONS.chev}</span>
    </div>
    <div class="cards">${notes.map(buildNoteCardHtml).join('')}</div>
  </div>`;
}

function buildNoteCardHtml(n) {
  const dom = domainConfig(n.domaine);
  const firstTag = n.parsedTags[0];
  const linked = n.liens.length;
  return `<button class="ncard" data-id="${n.id}" style="--accent:${dom.color}">
    <div class="row1">
      <span class="ddot"></span>
      <span class="ntitle">${n.titre}</span>
      ${n.est_meta ? `<span class="metachip" style="margin-left:auto">synthèse</span>` : ''}
    </div>
    <div class="ninsight">${n.insight}</div>
    <div class="nfoot">
      <span class="metatime">${relTime(n._days)}</span>
      ${firstTag ? `<span class="tag">#${firstTag}</span>` : ''}
      ${linked > 0 ? `<span class="meta-badge">${ICONS.link}<span class="metatime">${linked}</span></span>` : ''}
    </div>
  </button>`;
}

// ── Render: corner stats ──────────────────────────────────────────────────────

function renderCornerStats() {
  const { filteredList, status, activeFilter, sort, linkedOnly, mode } = state;
  const bl = document.getElementById('corner-bl');
  const br = document.getElementById('corner-br');
  const show = mode === 'grille';
  bl.classList.toggle('hidden', !show);
  br.classList.toggle('hidden', !show);
  if (!show) return;
  bl.innerHTML = `N: ${String(filteredList.length).padStart(2, '0')} (${status.total_notes})<br>S: ${status.meta_fiches_count} · sync ${relTimeFromDate(status.last_sync)}`;
  br.innerHTML = `${activeFilter === 'tous' ? 'all' : activeFilter}<br>${sort === 'recent' ? '↓ récents' : '↑ anciens'}${linkedOnly ? ' · liées' : ''}`;
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openModal(note) { setState({ openNote: note }); }
function closeModal()    { setState({ openNote: null }); }

function navModal(dir) {
  if (!state.openNote) return;
  const list = state.filteredList;
  const i = list.findIndex(n => n.id === state.openNote.id);
  const ni = (i + dir + list.length) % list.length;
  setState({ openNote: list[ni] });
}

document.addEventListener('keydown', e => {
  if (!state.openNote) return;
  if (e.key === 'Escape')     closeModal();
  if (e.key === 'ArrowRight') navModal(1);
  if (e.key === 'ArrowLeft')  navModal(-1);
});

function renderModal() {
  const panel = document.getElementById('panel');
  const existing = document.getElementById('modal-scrim');
  if (existing) existing.remove();
  if (!state.openNote) return;

  const note = state.openNote;
  const dom = domainConfig(note.domaine);
  const list = state.filteredList;
  const idx = Math.max(0, list.findIndex(n => n.id === note.id));
  const total = list.length;
  const scoreW = Math.round((note.score_pertinence || 0) * 100);

  const linkedNotes = note.liens
    .map(id => state.notes.find(n => n.id === id))
    .filter(Boolean);

  const tagsHtml = note.parsedTags.length
    ? `<div class="blocklabel">Tags</div><div class="tags">${note.parsedTags.map(t => `<span class="tagpill">#${t}</span>`).join('')}</div>`
    : '';

  const linkedLabel = note.est_meta ? 'Notes sources' : 'Notes liées';
  const linkedHtml = linkedNotes.length
    ? `<div class="blocklabel">${linkedLabel} · ${linkedNotes.length}</div>
       <div class="linked">${linkedNotes.map(l => {
         const ldom = domainConfig(l.domaine);
         return `<button class="lrow" data-linked="${l.id}" style="--accent:${ldom.color}"><span class="ddot"></span><span class="lt">${l.titre}</span>${ICONS.arrow}</button>`;
       }).join('')}</div>`
    : '';

  panel.insertAdjacentHTML('beforeend', `
    <div class="scrim" id="modal-scrim">
      <div class="modal" style="--accent:${dom.color}">
        <div class="mhead">
          <div class="au"><div class="a1"></div><div class="a2"></div><div class="a3"></div></div>
          <div class="grain"></div>
          <button class="navbtn prev" id="modal-prev">${ICONS.arrowLeft}</button>
          <button class="navbtn next" id="modal-next">${ICONS.arrow}</button>
          <button class="closebtn" id="modal-close">${ICONS.close}</button>
          <div class="htext">
            <div class="domrow"><span class="ddot"></span><span class="domlabel">${note.est_meta ? 'Synthèse · ' : ''}${dom.label}</span></div>
            <h2>${note.titre}</h2>
          </div>
        </div>
        <div class="mbody">
          <div class="insight-box"><div class="bar"></div><div class="it">${note.insight}</div></div>
          <div class="blocklabel">Résumé</div>
          <div class="resume">${note.resume || ''}</div>
          ${tagsHtml}
          ${linkedHtml}
          <div class="mfoot">
            <span class="metatime">${relTime(note._days)}</span>
            <span class="metatime">· ${String(idx + 1).padStart(2, '0')} / ${String(total).padStart(2, '0')}</span>
            <div class="scoremeter">
              <span class="metatime">pertinence</span>
              <div class="track"><div class="fill" style="width:${scoreW}%"></div></div>
              <span class="metatime">${(note.score_pertinence || 0).toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `);

  const scrim = document.getElementById('modal-scrim');
  scrim.addEventListener('click', e => { if (e.target === scrim) closeModal(); });
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-prev').addEventListener('click', () => navModal(-1));
  document.getElementById('modal-next').addEventListener('click', () => navModal(1));
  scrim.querySelectorAll('[data-linked]').forEach(btn => {
    btn.addEventListener('click', () => {
      const linked = state.notes.find(n => n.id === btn.dataset.linked);
      if (linked) setState({ openNote: linked });
    });
  });
}

// ── Chat RAG ──────────────────────────────────────────────────────────────────

function initChat() {
  const input = document.getElementById('chat-input');
  const responseEl = document.getElementById('chat-response');

  input.addEventListener('keydown', async e => {
    if (e.key !== 'Enter') return;
    const query = input.value.trim();
    if (!query) return;

    responseEl.classList.remove('hidden');
    responseEl.textContent = 'Recherche en cours…';

    try {
      const data = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      }).then(r => r.json());

      responseEl.textContent = data.reponse || '—';

      document.querySelectorAll('.ncard, .fcard').forEach(el => el.classList.remove('highlighted'));
      if (data.sources?.length) {
        const ids = new Set(data.sources.map(s => String(s.id)));
        document.querySelectorAll('[data-id]').forEach(el => {
          if (ids.has(el.dataset.id)) el.classList.add('highlighted');
        });
      }
    } catch {
      responseEl.textContent = 'Serveur non disponible.';
    }
  });
}

// ── Constellation placeholder (implemented in Task 4) ─────────────────────────

function renderConstellation() {
  const view = document.getElementById('constel-view');
  view.classList.remove('hidden');
  view.innerHTML = `<div style="display:grid;place-items:center;height:100%;color:var(--ink-3);font-family:var(--font-mono);font-size:12px">Constellation — Task 4</div>`;
}

// ── Render principal ──────────────────────────────────────────────────────────

function renderGrille() {
  document.getElementById('grille-view').classList.remove('hidden');
  document.getElementById('constel-view').classList.add('hidden');
  renderFeatured();
  renderFilters();
  renderSections();
  renderCornerStats();
}

function render() {
  renderTopbar();
  if (state.mode === 'grille') renderGrille();
  else {
    document.getElementById('grille-view').classList.add('hidden');
    renderConstellation();
    renderCornerStats();
  }
  renderModal();
}

// ── Data fetch ────────────────────────────────────────────────────────────────

async function loadData() {
  try {
    const [statusData, featuredRaw, notesRaw] = await Promise.all([
      fetch(`${API}/status`).then(r => r.json()),
      fetch(`${API}/a-la-une?limit=6`).then(r => r.json()),
      fetch(`${API}/notes?limit=200`).then(r => r.json()),
    ]);
    setState({
      status: statusData,
      notes: notesRaw.map(mapNote),
      featured: featuredRaw.map(mapNote),
    });
  } catch {
    document.getElementById('pill-stat').innerHTML =
      '<span class="dot" style="background:var(--d-projets)"></span>hors ligne';
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

(async () => {
  render();
  initChat();
  await loadData();
  animate('#topbar, #une-head, #featured-cards, #chat-bar, #filter-bar', {
    opacity: [0, 1], translateY: ['8px', '0px'],
    delay: stagger(30), duration: 500, ease: 'outQuart',
  });
})();
