import { animate, stagger } from './node_modules/animejs/dist/modules/index.js';
import { initZen, activateZen, deactivateZen } from './zen.js';

const API = window.BRAIN_API_URL || 'http://127.0.0.1:7842';

// ── Domain config ─────────────────────────────────────────────────────────────

const DOMAINS = {
  'Travail':           { key: 'travail',       label: 'Travail',       color: 'var(--d-travail)' },
  'Apprentissage':     { key: 'apprentissage', label: 'Apprentissage', color: 'var(--d-apprentissage)' },
  'Projets perso':     { key: 'projets',       label: 'Projets perso', color: 'var(--d-projets)' },
  'Jeux vidéos':       { key: 'jeux',          label: 'Jeux vidéos',   color: 'var(--d-jeux)' },
  'Plantes':           { key: 'plantes',       label: 'Plantes',       color: 'var(--d-plantes)' },
  'Organisation TDAH': { key: 'tdah',          label: 'Organisation',  color: 'var(--d-tdah)' },
  'À trier': { key: 'trier', label: 'À trier', color: 'var(--d-trier)' },
};
const DOMAIN_ORDER = ['Travail', 'Apprentissage', 'Projets perso', 'Jeux vidéos', 'Plantes', 'Organisation TDAH', 'À trier'];
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
  trier: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <path d="M3 6h18M7 12h10M11 18h2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
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
  trash: `<svg viewBox="0 0 24 24" fill="none" width="14" height="14">
    <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  externalLink: `<svg viewBox="0 0 24 24" fill="none" width="12" height="12">
    <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  refresh: `<svg viewBox="0 0 24 24" fill="none" width="14" height="14">
    <path d="M4 4v5h5M20 20v-5h-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M4 9a9 9 0 0115.36-3.36L20 9M4 15a9 9 0 0015.36 3.36L20 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
  </svg>`,
};

// ── State ─────────────────────────────────────────────────────────────────────

let state = {
  mode: 'grille',
  notes: [],
  blocs: [],                    // ← add
  checkedItems: new Set(),      // ← add
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
  const clean = t => t.trim().replace(/^#+/, '');
  try { const p = JSON.parse(raw); return Array.isArray(p) ? p.map(clean).filter(Boolean) : []; }
  catch { return String(raw).split(',').map(clean).filter(Boolean); }
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
  const cr = (() => {
    try { return JSON.parse(raw.contenu_riche || '{}'); }
    catch { return {}; }
  })();
  return {
    ...raw,
    id: String(raw.id),
    titre: raw.titre_court || '—',
    insight: raw.insight_cle || '',
    est_meta: Boolean(raw.est_meta_fiche),
    liens: parseLiens(raw.sources_ids),
    parsedTags: parseTags(raw.tags),
    _days: daysAgo(raw.date_capture),
    url_source:      cr.url_source      || null,
    points_cles:     Array.isArray(cr.points_cles) ? cr.points_cles : [],
    pourquoi_garder: cr.pourquoi_garder || null,
    quand_ressortir: cr.quand_ressortir || null,
    titre_modifie:   Boolean(raw.titre_modifie),
  };
}

// ── Render: topbar ────────────────────────────────────────────────────────────

function renderTopbar() {
  document.getElementById('logo-slot').innerHTML = ICONS.logo;
  const trierIconEl = document.getElementById('trier-icon');
  if (trierIconEl) trierIconEl.innerHTML = ICONS.trier;
  document.getElementById('spark-icon').innerHTML = ICONS.spark;

  const btnG = document.getElementById('btn-grille');
  const btnC = document.getElementById('btn-constellation');
  const btnZ = document.getElementById('btn-zen');
  btnG.innerHTML = `${ICONS.grid} Grille`;
  btnC.innerHTML = `${ICONS.nodes} Constellation`;
  btnZ.innerHTML = '🎮 Zen';
  btnG.classList.toggle('active', state.mode === 'grille');
  btnC.classList.toggle('active', state.mode === 'constellation');
  btnZ.classList.toggle('active', state.mode === 'zen');

  if (!btnG._bound) {
    btnG.addEventListener('click', () => setState({ mode: 'grille' }));
    btnC.addEventListener('click', () => setState({ mode: 'constellation' }));
    btnZ.addEventListener('click', () => setState({ mode: 'zen' }));
    btnG._bound = true;
  }

  const btnR = document.getElementById('btn-refresh');
  if (btnR) {
    btnR.innerHTML = ICONS.refresh;
    if (!btnR._bound) {
      btnR.addEventListener('click', () => loadData(false));
      btnR._bound = true;
    }
  }

  const { total_notes, meta_fiches_count } = state.status;
  document.getElementById('pill-stat').innerHTML =
    `<span class="dot"></span>${total_notes} notes · ${meta_fiches_count} synthèse${meta_fiches_count !== 1 ? 's' : ''}`;
}

// ── Render: section À trier ───────────────────────────────────────────────────

function renderATrier() {
  const container = document.getElementById('featured-cards');
  const head = document.getElementById('une-head');
  const trier = state.notes.filter(n => n.domaine === 'À trier');

  if (!trier.length) {
    container.innerHTML = '';
    head.classList.add('hidden');
    return;
  }

  head.classList.remove('hidden');
  container.innerHTML = trier.map(n => `
    <div class="fcard" data-id="${n.id}" style="--accent:var(--d-trier)" tabindex="0" role="button">
      <div class="glow"></div>
      <div class="ftitle">${n.titre}</div>
      <div class="finsight">${n.insight}</div>
      <div class="fmeta">
        <span class="ddot"></span>
        <span class="metatime">à trier</span>
        <span class="metatime" style="margin-left:auto">${relTime(n._days)}</span>
      </div>
    </div>`).join('');

  container.querySelectorAll('.fcard').forEach(el => {
    el.addEventListener('click', () => {
      const note = trier.find(n => n.id === el.dataset.id);
      if (note) openModal(note);
    });
  });

  if (!state._silent) {
    animate(container.querySelectorAll('.fcard'), {
      opacity: [0, 1], translateY: ['10px', '0px'],
      delay: stagger(40), duration: 500, ease: 'outQuart',
    });
  }
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
  if (cards.length && !state._silent) {
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

async function deleteNote(note) {
  const modalEl = document.querySelector('#modal-scrim .modal');
  const scrimEl = document.getElementById('modal-scrim');
  if (modalEl) await animate(modalEl, { scale: [1, 0.95], opacity: [1, 0], duration: 280, ease: 'outQuart' }).finished;
  if (scrimEl) await animate(scrimEl, { opacity: [1, 0], duration: 200, ease: 'outQuart' }).finished;

  const card = document.querySelector(`[data-id="${note.id}"]`);
  if (card) await animate(card, { translateX: [0, -12], opacity: [1, 0], duration: 220, ease: 'outCubic' }).finished;

  try {
    const resp = await fetch(`${API}/notes/${note.id}`, { method: 'DELETE' });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      alert(`Suppression impossible : ${err.detail || resp.status}`);
      render();
      return;
    }
  } catch {
    alert('Serveur non disponible.');
    render();
    return;
  }

  setState({
    openNote: null,
    notes:    state.notes.filter(n => n.id !== note.id),
  });
}

async function patchTitre(note, newTitre) {
  if (!newTitre.trim() || newTitre.trim() === note.titre) return;
  try {
    const resp = await fetch(`${API}/notes/${note.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ titre_court: newTitre.trim() }),
    });
    if (!resp.ok) return;
    const update = n => n.id === note.id ? { ...n, titre: newTitre.trim(), titre_modifie: true } : n;
    setState({
      notes:    state.notes.map(update),
      openNote: state.openNote?.id === note.id ? { ...state.openNote, titre: newTitre.trim() } : state.openNote,
    });
  } catch { /* silencieux */ }
}

async function patchDomaine(note, newDomaine) {
  if (newDomaine === note.domaine) return;
  try {
    const resp = await fetch(`${API}/notes/${note.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domaine: newDomaine }),
    });
    if (!resp.ok) return;
    const update = n => n.id === note.id ? { ...n, domaine: newDomaine } : n;
    setState({
      notes:    state.notes.map(update),
      openNote: state.openNote?.id === note.id
        ? { ...state.openNote, domaine: newDomaine }
        : state.openNote,
    });
  } catch { /* silencieux */ }
}

function renderModal() {
  const panel = document.getElementById('panel');
  const existing = document.getElementById('modal-scrim');
  if (existing) existing.remove();
  if (!state.openNote) return;

  const note  = state.openNote;
  const dom   = domainConfig(note.domaine);
  const list  = state.filteredList;
  const idx   = Math.max(0, list.findIndex(n => n.id === note.id));
  const total = list.length;
  const scoreW = Math.round((note.score_pertinence || 0) * 100);

  const linkedNotes = note.liens.map(id => state.notes.find(n => n.id === id)).filter(Boolean);
  const linkedLabel = note.est_meta ? 'Notes sources' : 'Notes liées';

  const tagsHtml = note.parsedTags.length
    ? `<div class="blocklabel">Tags</div><div class="tags">${note.parsedTags.map(t => `<span class="tagpill">#${t}</span>`).join('')}</div>`
    : '';

  const linkedHtml = linkedNotes.length
    ? `<div class="blocklabel">${linkedLabel} · ${linkedNotes.length}</div>
       <div class="linked">${linkedNotes.map(l => {
         const ldom = domainConfig(l.domaine);
         return `<button class="lrow" data-linked="${l.id}" style="--accent:${ldom.color}"><span class="ddot"></span><span class="lt">${l.titre}</span>${ICONS.arrow}</button>`;
       }).join('')}</div>`
    : '';

  const pointsHtml = note.points_cles.length
    ? `<div class="blocklabel">Points clés</div><ul class="points-cles">${note.points_cles.map(p => `<li>${p}</li>`).join('')}</ul>`
    : '';

  const pourquoiHtml = note.pourquoi_garder
    ? `<div class="blocklabel">Pourquoi garder</div><div class="resume">${note.pourquoi_garder}</div>`
    : '';

  const quandHtml = note.quand_ressortir
    ? `<div class="blocklabel">Quand ressortir</div><div class="resume">${note.quand_ressortir}</div>`
    : '';

  const sourceLinkHtml = note.url_source
    ? `<button class="source-link" id="modal-source-link">${ICONS.externalLink} Ouvrir la source</button>`
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
            <div class="domrow domain-changeable" id="modal-domrow">
              <span class="ddot"></span>
              <span class="domlabel">${note.est_meta ? 'Synthèse · ' : ''}${dom.label}</span>
              <span class="domain-edit-hint">✎</span>
            </div>
            ${sourceLinkHtml}
            <h2 id="modal-title" class="title-editable" contenteditable="true" spellcheck="false">${note.titre}</h2>
          </div>
        </div>
        <div class="mbody">
          <div class="domain-picker hidden" id="modal-domain-picker">
            ${DOMAIN_ORDER.map(d => {
              const dc = domainConfig(d);
              const isActive = d === note.domaine;
              return `<button class="dpill${isActive ? ' active' : ''}" data-domain="${d}" style="--accent:${dc.color}"><span class="ddot"></span>${dc.label}</button>`;
            }).join('')}
          </div>
          <div class="insight-box"><div class="bar"></div><div class="it">${note.insight}</div></div>
          <div class="blocklabel">Résumé</div>
          <div class="resume">${note.resume || ''}</div>
          ${pointsHtml}
          ${pourquoiHtml}
          ${quandHtml}
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
            <button class="deletebtn" id="modal-delete" title="Supprimer cette note">${ICONS.trash}</button>
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

  const domrow = document.getElementById('modal-domrow');
  const picker = document.getElementById('modal-domain-picker');

  domrow.addEventListener('click', (e) => {
    e.stopPropagation();
    const opening = picker.classList.contains('hidden');
    picker.classList.toggle('hidden');
    if (opening) {
      animate(picker.querySelectorAll('.dpill'), {
        opacity: [0, 1], translateY: ['-6px', '0px'],
        delay: stagger(28), duration: 200, ease: 'outCubic',
      });
    }
  });

  // Délégation : un seul listener sur le picker couvre tous les pills (y compris les spans enfants)
  picker.addEventListener('click', (e) => {
    e.stopPropagation();
    const pill = e.target.closest('.dpill');
    if (!pill) return;
    picker.classList.add('hidden');
    patchDomaine(note, pill.dataset.domain);
  });

  // Ferme le picker en cliquant ailleurs dans la modale — pas de zombie sur document
  const modal = document.querySelector('#modal-scrim .modal');
  modal.addEventListener('click', (e) => {
    if (picker.classList.contains('hidden')) return;
    if (!picker.contains(e.target) && !domrow.contains(e.target)) {
      picker.classList.add('hidden');
    }
  });

  const srcBtn = document.getElementById('modal-source-link');
  if (srcBtn && note.url_source) {
    srcBtn.addEventListener('click', () => window.openUrl(note.url_source));
  }

  document.getElementById('modal-delete').addEventListener('click', () => deleteNote(note));

  const titleEl = document.getElementById('modal-title');
  titleEl.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); titleEl.blur(); }
    if (e.key === 'Escape') { titleEl.textContent = note.titre; titleEl.blur(); }
  });
  titleEl.addEventListener('blur', () => patchTitre(note, titleEl.textContent.trim()));

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

// ── Constellation ─────────────────────────────────────────────────────────────

let constellationPan = { x: 0, y: 0 };
let constellationDrag = null;
let constellationHover = null;

function computeLayout(notes, w, h) {
  const cx = w / 2, cy = h / 2;
  const R = Math.min(w, h) * 0.26;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const byDom = {};
  notes.forEach(n => { (byDom[n.domaine] = byDom[n.domaine] || []).push(n); });
  const pos = {};

  DOMAIN_ORDER.forEach((dk, di) => {
    const ang = (di / DOMAIN_ORDER.length) * Math.PI * 2 - Math.PI / 2;
    const hx = cx + Math.cos(ang) * R;
    const hy = cy + Math.sin(ang) * R;
    const list = byDom[dk] || [];
    const nonMeta = list.filter(n => !n.est_meta);
    list.forEach((n, i) => {
      if (n.est_meta) {
        pos[n.id] = { x: cx + (i - 0.5) * 26, y: cy };
        return;
      }
      const k = nonMeta.length;
      const a2 = ang + (i - (k - 1) / 2) * 0.5;
      const rr = 64 + (i % 2) * 22;
      pos[n.id] = {
        x: clamp(hx + Math.cos(a2) * rr * 0.55, 96, w - 96),
        y: clamp(hy + Math.sin(a2) * rr,         84, h - 70),
      };
    });
  });

  const seen = new Set();
  const edges = [];
  notes.forEach(n => {
    (n.liens || []).forEach(tid => {
      if (!pos[n.id] || !pos[tid]) return;
      const key = [n.id, tid].sort().join('-');
      if (seen.has(key)) return;
      seen.add(key);
      edges.push({ a: n.id, b: tid, key, color: domainConfig(n.domaine).color });
    });
  });

  return { pos, edges };
}

function renderConstellation() {
  const view = document.getElementById('constel-view');
  view.classList.remove('hidden');

  const notes = state.filteredList;
  const panel = document.getElementById('panel');
  const w = panel.clientWidth  || window.innerWidth  || 800;
  const h = (panel.clientHeight || window.innerHeight || 900) - 60; // minus topbar
  const { pos, edges } = computeLayout(notes, w, h);
  const pan = constellationPan;
  const hov = constellationHover;

  const edgeSvg = edges.map(e => {
    const a = pos[e.a], b = pos[e.b];
    if (!a || !b) return '';
    const mx = (a.x + b.x) / 2;
    const my = (a.y + b.y) / 2 - 28;
    const lit = hov && (e.a === hov || e.b === hov);
    const accent = lit ? `style="--accent:${e.color}"` : '';
    return `<path class="edge${lit ? ' lit' : ''}" ${accent} d="M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}"/>`;
  }).join('');

  const nodesHtml = notes.map(n => {
    const p = pos[n.id];
    if (!p) return '';
    const dom = domainConfig(n.domaine);
    const isHov = hov === n.id;
    return `<div class="cnode${n.est_meta ? ' meta' : ''}${isHov ? ' active' : ''}"
      data-cid="${n.id}"
      style="left:${p.x}px;top:${p.y}px;--accent:${dom.color}">
      <div class="bubble"><span class="ddot"></span><span class="ct">${n.titre}</span></div>
    </div>`;
  }).join('');

  const legendHtml = DOMAIN_ORDER.map(d => {
    const dom = domainConfig(d);
    return `<div class="li" style="--accent:${dom.color}"><span class="ddot"></span><span>${dom.label}</span></div>`;
  }).join('');

  view.innerHTML = `
    <div class="constel" id="constel-inner">
      <span class="hint">glisser pour naviguer</span>
      <div class="world" id="constel-world" style="transform:translate(${pan.x}px,${pan.y}px)">
        <svg class="links">${edgeSvg}</svg>
        ${nodesHtml}
      </div>
      <div class="legend">${legendHtml}</div>
    </div>
  `;

  const inner = document.getElementById('constel-inner');

  inner.addEventListener('pointerdown', e => {
    constellationDrag = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  });
  inner.addEventListener('pointermove', e => {
    if (!constellationDrag) return;
    constellationPan = { x: e.clientX - constellationDrag.x, y: e.clientY - constellationDrag.y };
    document.getElementById('constel-world').style.transform =
      `translate(${constellationPan.x}px,${constellationPan.y}px)`;
  });
  inner.addEventListener('pointerup',    () => { constellationDrag = null; });
  inner.addEventListener('pointerleave', () => { constellationDrag = null; });

  view.querySelectorAll('.cnode').forEach(el => {
    el.addEventListener('mouseenter', () => {
      constellationHover = el.dataset.cid;
      renderConstellation();
    });
    el.addEventListener('mouseleave', () => {
      constellationHover = null;
      renderConstellation();
    });
    el.addEventListener('click', e => {
      e.stopPropagation();
      const note = state.filteredList.find(n => n.id === el.dataset.cid);
      if (note) openModal(note);
    });
  });
}

// ── Render principal ──────────────────────────────────────────────────────────

function renderGrille() {
  document.getElementById('grille-view').classList.remove('hidden');
  document.getElementById('constel-view').classList.add('hidden');
  renderATrier();
  renderFilters();
  renderSections();
  renderCornerStats();
}

function render() {
  renderTopbar();
  const isZen = state.mode === 'zen';

  document.getElementById('zen-view').classList.toggle('hidden', !isZen);
  document.getElementById('blocs-section').style.display = isZen ? 'none' : '';

  if (isZen) {
    document.getElementById('grille-view').classList.add('hidden');
    document.getElementById('constel-view').classList.add('hidden');
    activateZen();
    return;
  }

  deactivateZen();

  if (state.mode === 'grille') renderGrille();
  else {
    document.getElementById('grille-view').classList.add('hidden');
    renderConstellation();
    renderCornerStats();
  }
  renderModal();
  renderBlocs();
}

// ── Blocs resize ──────────────────────────────────────────────────────────────

function initBlocsResize() {
  const section = document.getElementById('blocs-section');
  const handle  = document.getElementById('blocs-resize-handle');
  if (!section || !handle) return;

  const saved = parseInt(localStorage.getItem('blocs-height'), 10);
  if (saved >= 80 && saved <= 400) section.style.height = saved + 'px';

  let startY = 0, startH = 0, dragging = false;

  handle.addEventListener('mousedown', e => {
    e.preventDefault();
    dragging = true;
    startY = e.clientY;
    startH = section.offsetHeight;
    document.body.style.cursor     = 'ns-resize';
    document.body.style.userSelect = 'none';
  });

  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    const newH = Math.max(80, Math.min(400, startH - (e.clientY - startY)));
    section.style.height = newH + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor     = '';
    document.body.style.userSelect = '';
    localStorage.setItem('blocs-height', section.offsetHeight);
  });
}

// ── Blocs actions ─────────────────────────────────────────────────────────────

async function checkItem(name, idx) {
  const key = `${name}:${idx}`;
  if (state.checkedItems.has(key)) return;
  state.checkedItems.add(key);
  renderBlocs();
  fetch(`${API}/blocs/${name}/${idx}`, { method: 'DELETE' }).catch(() => {});
}

async function addItem(name, texte) {
  if (!texte.trim()) return;
  await fetch(`${API}/blocs/${name}/item`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ texte: texte.trim() }),
  }).catch(() => {});
  const blocsRaw = await fetch(`${API}/blocs`).then(r => r.json()).catch(() => state.blocs);
  setState({ blocs: blocsRaw });
}

function renderBlocs() {
  const section = document.getElementById('blocs-section');
  if (!section) return;
  if (!state.blocs || state.blocs.length === 0) return;

  let grid = section.querySelector('.blocs-grid');
  if (!grid) {
    grid = document.createElement('div');
    grid.className = 'blocs-grid';
    section.appendChild(grid);
  }
  grid.innerHTML = state.blocs.map(renderBlocCol).join('');

  // Event delegation — clicks on items
  section.querySelectorAll('.bloc-item').forEach(el => {
    el.addEventListener('click', () => {
      checkItem(el.dataset.name, parseInt(el.dataset.idx, 10));
    });
  });

  // + button and input per column
  state.blocs.forEach(({ name }) => {
    const btn   = document.getElementById(`bloc-add-btn-${name}`);
    const input = document.getElementById(`bloc-add-input-${name}`);
    if (!btn || !input) return;

    btn.addEventListener('click', () => {
      btn.style.display = 'none';
      input.classList.remove('hidden');
      input.focus();
    });

    const confirm = async () => {
      const val = input.value;
      input.value = '';
      input.classList.add('hidden');
      btn.style.display = '';
      if (val.trim()) await addItem(name, val);
    };

    input.addEventListener('keydown', async e => {
      if (e.key === 'Enter')  { e.preventDefault(); await confirm(); }
      if (e.key === 'Escape') { input.value = ''; input.classList.add('hidden'); btn.style.display = ''; }
    });
    input.addEventListener('blur', confirm);
  });
}

function renderBlocCol({ name, titre, items }) {
  const uncheckedCount = items.filter(it => !state.checkedItems.has(`${name}:${it.idx}`)).length;
  return `
    <div class="bloc-col">
      <div class="bloc-col-header">${titre} <span style="opacity:.5">(${uncheckedCount})</span></div>
      <div class="bloc-items">
        ${items.map(it => renderBlocItem(name, it)).join('')}
      </div>
      <div class="bloc-add">
        <button class="bloc-add-btn" id="bloc-add-btn-${name}">+ ajouter</button>
        <input class="bloc-add-input hidden" id="bloc-add-input-${name}"
               type="text" placeholder="nouvel item…" maxlength="200">
      </div>
    </div>`;
}

function renderBlocItem(name, { idx, texte, date }) {
  const checked   = state.checkedItems.has(`${name}:${idx}`);
  const dateShort = date ? date.slice(0, 5) : '';
  return `
    <div class="bloc-item${checked ? ' checked' : ''}" data-name="${name}" data-idx="${idx}">
      <div class="bloc-check"></div>
      <div class="bloc-item-body">
        <div class="bloc-item-text">${texte}</div>
        ${dateShort ? `<div class="bloc-item-date">${dateShort}</div>` : ''}
      </div>
    </div>`;
}

// ── Data fetch ────────────────────────────────────────────────────────────────

let _loadingData = false;

async function loadData(silent = true) {
  if (_loadingData) return;
  _loadingData = true;

  const btnR = document.getElementById('btn-refresh');
  if (btnR) btnR.classList.add('spinning');

  const scrollEl = document.getElementById('grille-view');
  const savedScroll = scrollEl ? scrollEl.scrollTop : 0;

  try {
    const [statusData, notesRaw, blocsRaw] = await Promise.all([
      fetch(`${API}/status`).then(r => r.json()),
      fetch(`${API}/notes?limit=200`).then(r => r.json()),
      fetch(`${API}/blocs`).then(r => r.json()).catch(() => []),
    ]);
    state._silent = silent;
    setState({
      status: statusData,
      notes: notesRaw.map(mapNote),
      blocs: blocsRaw,
    });
    state._silent = false;

    if (silent && scrollEl) scrollEl.scrollTop = savedScroll;
  } catch {
    document.getElementById('pill-stat').innerHTML =
      '<span class="dot" style="background:var(--d-projets)"></span>hors ligne';
    setTimeout(() => loadData(true), 5000); // serveur pas encore prêt — réessayer dans 5s
  } finally {
    _loadingData = false;
    const btnR2 = document.getElementById('btn-refresh');
    if (btnR2) btnR2.classList.remove('spinning');
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

(async () => {
  render();
  initChat();
  initBlocsResize();
  initZen();
  await loadData(false); // premier chargement avec animations
  setInterval(() => loadData(true), 2 * 60 * 1000); // rafraîchir toutes les 2 min (silencieux)
  animate('#topbar, #une-head, #featured-cards, #chat-bar, #filter-bar', {
    opacity: [0, 1], translateY: ['8px', '0px'],
    delay: stagger(30), duration: 500, ease: 'outQuart',
  });
})();
