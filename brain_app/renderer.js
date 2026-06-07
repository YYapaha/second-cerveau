import { animate, stagger } from './node_modules/animejs/dist/modules/index.js';
import { initZen, activateZen, deactivateZen } from './zen.js';
import { ICONS } from './icons.js';

const API = window.BRAIN_API_URL || 'http://127.0.0.1:7842';

// ── Domain config ─────────────────────────────────────────────────────────────

let DOMAINS = {
  'Travail':           { key: 'travail',       label: 'Travail',       color: 'var(--d-travail)' },
  'Apprentissage':     { key: 'apprentissage', label: 'Apprentissage', color: 'var(--d-apprentissage)' },
  'Projets perso':     { key: 'projets',       label: 'Projets perso', color: 'var(--d-projets)' },
  'Jeux vidéos':       { key: 'jeux',          label: 'Jeux vidéos',   color: 'var(--d-jeux)' },
  'Plantes':           { key: 'plantes',       label: 'Plantes',       color: 'var(--d-plantes)' },
  'Organisation TDAH': { key: 'tdah',          label: 'Organisation',  color: 'var(--d-tdah)' },
  'À trier': { key: 'trier', label: 'À trier', color: 'var(--d-trier)' },
};
let DOMAIN_ORDER = ['Travail', 'Apprentissage', 'Projets perso', 'Jeux vidéos', 'Plantes', 'Organisation TDAH', 'À trier'];
const META_DOM = { key: 'meta', label: 'Méta-fiches', color: 'var(--d-meta)' };

// Icons are imported from icons.js

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

async function loadDomains() {
  try {
    const data = await fetch(`${API}/domains`).then(r => r.json());
    DOMAIN_ORDER = data.map(d => d.name);
    DOMAINS = {};
    data.forEach(d => {
      DOMAINS[d.name] = { key: d.name.toLowerCase().replace(/\s+/g, '_'), label: d.name, color: d.color };
    });
  } catch {
    // keep fallback hardcoded values — server may not be ready yet
  }
}

// ── Color picker (shared, initialized once) ───────────────────────────────────

const _colorInput = (() => {
  const inp = document.createElement('input');
  inp.type = 'color';
  inp.id = '_domain-color-input';
  inp.style.cssText = 'position:fixed;opacity:0;width:1px;height:1px;pointer-events:none;';
  document.body.appendChild(inp);
  return inp;
})();
let _colorTarget = null;
let _labelClickTimer = null;
let _labelClickDomain = null;

_colorInput.addEventListener('change', async () => {
  if (!_colorTarget) return;
  const target = _colorTarget;
  _colorTarget = null;
  _colorInput.style.pointerEvents = 'none';
  await patchDomain(target, { color: _colorInput.value });
});

function showRename(domainName) {
  const pill  = document.querySelector(`.fpill[data-filter="${CSS.escape(domainName)}"]`);
  const label = pill?.querySelector('.dlabel');
  if (!label || label.dataset.locked) return;

  const original = DOMAINS[domainName]?.label || domainName;
  const rect = label.getBoundingClientRect();
  const cs   = window.getComputedStyle(label);

  // Input flottant dans document.body — HORS du <button> pour éviter tout bubbling
  const input = document.createElement('input');
  input.className = 'dlabel-input';
  input.value = original;
  input.style.cssText = [
    'position:fixed',
    `left:${rect.left}px`,
    `top:${rect.top}px`,
    `width:${Math.max(80, rect.width + 40)}px`,
    `height:${rect.height || 18}px`,
    `font:${cs.font}`,
    `letter-spacing:${cs.letterSpacing}`,
    `color:${cs.color}`,
    'background:rgba(12,12,24,0.95)',
    'border:none',
    'border-bottom:1px solid var(--stroke-hi)',
    'outline:none',
    'padding:0 3px',
    'z-index:9999',
    'border-radius:2px',
  ].join(';');

  label.style.visibility = 'hidden';
  document.body.appendChild(input);
  input.focus();
  input.select();

  const cleanup = () => {
    if (input.isConnected) input.remove();
    if (label.isConnected) label.style.visibility = '';
  };

  const doConfirm = async () => {
    if (!input.isConnected) return;
    const newName = input.value.trim();
    cleanup();
    if (newName && newName !== original) await patchDomain(domainName, { name: newName });
  };

  input.addEventListener('keydown', async e => {
    if (e.key === 'Enter')  { e.preventDefault(); await doConfirm(); }
    if (e.key === 'Escape') { e.preventDefault(); cleanup(); }
  });
  input.addEventListener('blur', doConfirm);
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
    url_source:        cr.url_source        || null,
    contenu_essentiel: cr.contenu_essentiel || null,
    points_cles:       Array.isArray(cr.points_cles) ? cr.points_cles : [],
    pourquoi_garder:   cr.pourquoi_garder   || null,
    quand_ressortir:   cr.quand_ressortir   || null,
    titre_modifie:     Boolean(raw.titre_modifie),
  };
}

// ── Render: topbar ────────────────────────────────────────────────────────────

function renderTopbar() {
  document.getElementById('logo-slot').innerHTML = ICONS.logo;
  document.getElementById('spark-icon').innerHTML = ICONS.spark;

  const btnG = document.getElementById('btn-grille');
  const btnC = document.getElementById('btn-constellation');
  const btnZ = document.getElementById('btn-zen');
  btnG.innerHTML = `${ICONS.grid} Grille`;
  btnC.innerHTML = `${ICONS.nodes} Constellation`;
  btnZ.innerHTML = `${ICONS.zen} Zen`;
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
    btnR.setAttribute('aria-label', 'Rafraîchir les notes');
    if (!btnR._bound) {
      btnR.addEventListener('click', () => {
        if (window.syncBrain) window.syncBrain();
        else loadData(false);
      });
      btnR._bound = true;
    }
  }

  const { total_notes, meta_fiches_count } = state.status;
  document.getElementById('pill-stat').innerHTML =
    `<span class="dot"></span>${total_notes} notes · ${meta_fiches_count} synthèse${meta_fiches_count !== 1 ? 's' : ''}`;
}

// ── Render: statusbar ─────────────────────────────────────────────────────────

function renderStatusbar() {
  const sb = document.getElementById('statusbar');
  if (!sb) return;
  const { filteredList, status, activeFilter, sort, linkedOnly } = state;
  const syncStr = relTimeFromDate(status.last_sync);
  sb.innerHTML = `
    <span class="s"><span class="ic"></span>${String(filteredList.length).padStart(2,'0')} affichées / ${status.total_notes}</span>
    <span class="s">${status.meta_fiches_count} synthèse</span>
    <span class="s">sync ${syncStr}</span>
    <span class="right">
      <span class="s">${activeFilter === 'tous' ? 'tous domaines' : domainConfig(activeFilter).label}</span>
      <span class="s">${sort === 'recent' ? '↓ récents' : '↑ anciens'}${linkedOnly ? ' · liées' : ''}</span>
    </span>`;
}

// ── Render: filters ───────────────────────────────────────────────────────────

function renderFilters() {
  const container = document.getElementById('filter-bar');
  const { activeFilter, sort, linkedOnly } = state;

  container.innerHTML = [
    `<button class="fpill${activeFilter === 'tous' ? ' active' : ''}" data-filter="tous">Tous</button>`,
    ...DOMAIN_ORDER.map(d => {
      const dom = domainConfig(d);
      return `<button class="fpill${activeFilter === d ? ' active' : ''}" data-filter="${d}" style="--accent:${dom.color}"><span class="ddot" data-domain="${d}"></span><span class="dlabel"${d === 'À trier' ? ' data-locked="true"' : ''}>${dom.label}</span></button>`;
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

  container.querySelectorAll('.ddot[data-domain]').forEach(dot => {
    dot.addEventListener('click', e => {
      e.stopPropagation();
      _colorTarget = dot.dataset.domain;
      _colorInput.value = DOMAINS[_colorTarget]?.color?.startsWith('#')
        ? DOMAINS[_colorTarget].color
        : '#888888';
      const rect = dot.getBoundingClientRect();
      _colorInput.style.left = rect.left + 'px';
      _colorInput.style.top  = rect.bottom + 'px';
      _colorInput.style.pointerEvents = 'auto';
      _colorInput.click();
    });
  });

  // Double-click rename: tracked by domain name (survives DOM rebuild between clicks)
  container.querySelectorAll('.dlabel:not([data-locked])').forEach(label => {
    label.addEventListener('click', e => {
      e.stopPropagation(); // prevent bubble to .fpill so setState isn't called twice
      const domainName = label.closest('.fpill')?.dataset.filter;
      if (!domainName) return;

      if (_labelClickTimer && _labelClickDomain === domainName) {
        clearTimeout(_labelClickTimer);
        _labelClickTimer = null;
        _labelClickDomain = null;
        showRename(domainName);
        return;
      }

      _labelClickDomain = domainName;
      _labelClickTimer = setTimeout(() => {
        _labelClickTimer = null;
        _labelClickDomain = null;
      }, 300);
      setState({ activeFilter: domainName });
    });
  });
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
  // À trier en tête si des notes non classées existent
  if (groups['À trier']?.length) {
    html += buildSectionHtml(domainConfig('À trier'), groups['À trier']);
  }
  // Autres domaines dans l'ordre habituel (sans répéter À trier)
  DOMAIN_ORDER.filter(d => d !== 'À trier').forEach(d => {
    if (!groups[d]?.length) return;
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
    animate(cards, { opacity: [0, 1], translateY: ['8px', '0px'], delay: stagger(15), duration: 300, ease: 'outCubic' });
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
  const tags = n.parsedTags.slice(0, 2).map(t => `<span class="tag">#${t}</span>`).join('');
  const linked = n.liens.length;
  return `<button class="ncard" data-id="${n.id}" style="--accent:${dom.color}">
    <div class="row1">
      <span class="ddot"></span>
      <span class="ntitle">${n.titre}</span>
      ${n.est_meta ? `<span class="metachip">synthèse</span>` : ''}
    </div>
    <div class="ninsight">${n.insight}</div>
    <div class="nfoot">
      <div class="tags-inline">${tags}</div>
      <div class="nmeta">
        ${linked > 0 ? `<span class="links">${ICONS.link}${linked}</span>` : ''}
        <span class="metatime">${relTime(n._days)}</span>
      </div>
    </div>
  </button>`;
}

function buildNoteRowHtml(n) {
  const dom = domainConfig(n.domaine);
  const firstTag = n.parsedTags[0];
  return `<button class="nrow" data-id="${n.id}" style="--accent:${dom.color}">
    <div class="nrow-bar"></div>
    <span class="nrow-title">${n.titre}</span>
    ${firstTag ? `<span class="nrow-tag">#${firstTag}</span>` : ''}
    <span class="nrow-time">${relTime(n._days)}</span>
  </button>`;
}


// ── Modal ─────────────────────────────────────────────────────────────────────

function openModal(note) { setState({ openNote: note }); }
async function closeModal() {
  const scrim = document.getElementById('modal-scrim');
  if (!scrim || scrim._closing) return;
  scrim._closing = true;
  const modal = scrim.querySelector('.modal');
  if (modal) await animate(modal, { opacity: [1, 0], translateY: [0, 10], scale: [1, 0.97], duration: 180, ease: 'inQuart' }).finished;
  await animate(scrim, { opacity: [1, 0], duration: 130, ease: 'inQuart' }).finished;
  setState({ openNote: null });
}

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
  if (!newDomaine || newDomaine === note.domaine) return;

  const savedDomaine = note.domaine;
  const update = (d, n) => n.id === note.id ? { ...n, domaine: d } : n;

  // Optimistic update
  setState({
    notes:    state.notes.map(update.bind(null, newDomaine)),
    openNote: state.openNote?.id === note.id
      ? { ...state.openNote, domaine: newDomaine }
      : state.openNote,
  });

  try {
    const resp = await fetch(`${API}/notes/${note.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domaine: newDomaine }),
    });
    if (!resp.ok) {
      // Rollback
      setState({
        notes:    state.notes.map(update.bind(null, savedDomaine)),
        openNote: state.openNote?.id === note.id
          ? { ...state.openNote, domaine: savedDomaine }
          : state.openNote,
      });
      const domrow = document.getElementById('modal-domrow');
      if (domrow) { domrow.style.outline = '1px solid red'; setTimeout(() => { domrow.style.outline = ''; }, 1000); }
    }
  } catch {
    // Rollback on network error
    setState({
      notes:    state.notes.map(update.bind(null, savedDomaine)),
      openNote: state.openNote?.id === note.id
        ? { ...state.openNote, domaine: savedDomaine }
        : state.openNote,
    });
  }
}

async function patchDomain(currentName, updates) {
  const isRename     = !!(updates.name && updates.name !== currentName);
  const resolvedName = isRename ? updates.name : currentName;
  const savedIdx     = DOMAIN_ORDER.indexOf(currentName);
  const savedEntry   = DOMAINS[currentName] ? { ...DOMAINS[currentName] } : null;
  const savedNotes   = state.notes;
  const savedActive  = state.activeFilter;
  const resolvedColor = updates.color ?? savedEntry?.color;

  // ── Mise à jour optimiste synchrone (avant le fetch) ──────────────────
  if (isRename) {
    if (savedIdx >= 0) DOMAIN_ORDER[savedIdx] = resolvedName;
    DOMAINS[resolvedName] = { ...savedEntry, label: resolvedName, color: resolvedColor };
    delete DOMAINS[currentName];
    setState({
      notes:        state.notes.map(n => n.domaine === currentName ? { ...n, domaine: resolvedName } : n),
      activeFilter: state.activeFilter === currentName ? resolvedName : state.activeFilter,
    });
  } else if (updates.color) {
    if (DOMAINS[currentName]) DOMAINS[currentName].color = resolvedColor;
    render();
  }

  // ── Persistance serveur ────────────────────────────────────────────────
  try {
    const resp = await fetch(`${API}/domains/${encodeURIComponent(currentName)}`, {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(updates),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    // Succès — l'état optimiste est correct, rien à faire
  } catch {
    // Rollback : restaurer l'état avant la modification
    if (isRename) {
      if (savedIdx >= 0) DOMAIN_ORDER[savedIdx] = currentName;
      if (savedEntry) DOMAINS[currentName] = savedEntry;
      delete DOMAINS[resolvedName];
      setState({ notes: savedNotes, activeFilter: savedActive });
    } else if (updates.color && savedEntry) {
      DOMAINS[currentName] = savedEntry;
      render();
    }
    const errPill = document.querySelector(`.fpill[data-filter="${CSS.escape(currentName)}"]`);
    if (errPill) { errPill.style.outline = '1px solid red'; setTimeout(() => { errPill.style.outline = ''; }, 1000); }
  }
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

  const contenuEssentielHtml = note.contenu_essentiel
    ? `<div class="blocklabel">Contenu essentiel</div><div class="resume">${note.contenu_essentiel.replace(/\n/g, '<br>')}</div>`
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
          <div class="domain-picker hidden" id="modal-domain-picker"></div>
          <div class="insight-box"><div class="bar"></div><div class="it">${note.insight}</div></div>
          <div class="blocklabel">Résumé</div>
          <div class="resume">${note.resume || ''}</div>
          ${contenuEssentielHtml}
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

  // Création programmatique des pills — évite tout problème d'encodage HTML
  DOMAIN_ORDER.forEach(d => {
    const dc = domainConfig(d);
    const btn = document.createElement('button');
    btn.className = 'dpill' + (d === note.domaine ? ' active' : '');
    btn.dataset.domain = d;
    btn.style.setProperty('--accent', dc.color);
    const dot = document.createElement('span');
    dot.className = 'ddot';
    btn.appendChild(dot);
    btn.appendChild(document.createTextNode(dc.label));
    picker.appendChild(btn);
  });

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

  // Délégation — un seul listener couvre tous les pills y compris leurs spans enfants
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

      document.querySelectorAll('.ncard').forEach(el => el.classList.remove('highlighted'));
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

// ── Constellation (force-directed) ────────────────────────────────────────────

let constellationPan = { x: 0, y: 0 };

function _constelSaveState() {
  localStorage.setItem('constel-pan', JSON.stringify(constellationPan));
  const view = document.getElementById('constel-view');
  if (!view) return;
  const positions = {};
  view.querySelectorAll('.cnode').forEach(el => {
    positions[el.dataset.cid] = { x: parseFloat(el.style.left), y: parseFloat(el.style.top) };
  });
  localStorage.setItem('constel-positions', JSON.stringify(positions));
}

function _constelUpdateEdges(view, id, newX, newY) {
  const svg = view.querySelector('svg.links');
  if (!svg) return;
  svg.querySelectorAll(`.edge[data-ea="${id}"]`).forEach(path => {
    const bEl = view.querySelector(`[data-cid="${path.dataset.eb}"]`);
    if (!bEl) return;
    const bx = parseFloat(bEl.style.left), by = parseFloat(bEl.style.top);
    const mx = (newX + bx) / 2, my = (newY + by) / 2 - 36;
    path.setAttribute('d', `M ${newX} ${newY} Q ${mx} ${my} ${bx} ${by}`);
  });
  svg.querySelectorAll(`.edge[data-eb="${id}"]`).forEach(path => {
    const aEl = view.querySelector(`[data-cid="${path.dataset.ea}"]`);
    if (!aEl) return;
    const ax = parseFloat(aEl.style.left), ay = parseFloat(aEl.style.top);
    const mx = (ax + newX) / 2, my = (ay + newY) / 2 - 36;
    path.setAttribute('d', `M ${ax} ${ay} Q ${mx} ${my} ${newX} ${newY}`);
  });
}

function renderConstellation() {
  const view = document.getElementById('constel-view');
  view.classList.remove('hidden');
  view.innerHTML = '';

  const notes = state.filteredList;
  const panel = document.getElementById('panel');
  const W = panel.clientWidth  || window.innerWidth  || 1080;
  const H = (panel.clientHeight || window.innerHeight || 1920) - 60;

  const domKeys = DOMAIN_ORDER.filter(dk => notes.some(n => n.domaine === dk));
  const cx = W / 2, cy = H / 2, Rx = W * 0.30, Ry = H * 0.33;

  const half = n => ({ w: Math.min(150, 64 + n.titre.length * 3.4), h: 24 });

  const hubs = {};
  domKeys.forEach((dk, di) => {
    const ang = (di / domKeys.length) * Math.PI * 2 - Math.PI / 2;
    hubs[dk] = { x: cx + Math.cos(ang) * Rx, y: cy + Math.sin(ang) * Ry };
  });

  const nodeData = notes.map(n => {
    const h = n.est_meta ? { x: cx, y: cy } : (hubs[n.domaine] || { x: cx, y: cy });
    return { n, x: h.x + (Math.random() - 0.5) * 80, y: h.y + (Math.random() - 0.5) * 80, hub: h, hs: half(n) };
  });

  // Build edges (deduplicated)
  const idOf = {};
  nodeData.forEach(nd => { idOf[nd.n.id] = nd; });
  const edges = [];
  const seen = new Set();
  notes.forEach(n => {
    (n.liens || []).forEach(tid => {
      if (!idOf[tid]) return;
      const key = [n.id, tid].sort().join('-');
      if (seen.has(key)) return;
      seen.add(key);
      edges.push([idOf[n.id], idOf[tid], n]);
    });
  });

  // Load saved positions — use them if they cover all current notes
  const savedPositions = JSON.parse(localStorage.getItem('constel-positions') || 'null');
  const allSaved = savedPositions && notes.every(n => savedPositions[n.id]);

  if (allSaved) {
    nodeData.forEach(nd => {
      nd.x = savedPositions[nd.n.id].x;
      nd.y = savedPositions[nd.n.id].y;
    });
  } else {
    // Force simulation: 220 iterations
    for (let it = 0; it < 220; it++) {
      nodeData.forEach(a => {
        a.x += (a.hub.x - a.x) * (a.n.est_meta ? 0.010 : 0.015);
        a.y += (a.hub.y - a.y) * (a.n.est_meta ? 0.010 : 0.015);
      });
      edges.forEach(([a, b]) => {
        const dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.hypot(dx, dy) || 1;
        const f = (d - 240) * 0.005;
        const ux = dx / d, uy = dy / d;
        a.x += ux * f; a.y += uy * f; b.x -= ux * f; b.y -= uy * f;
      });
      for (let i = 0; i < nodeData.length; i++) {
        for (let j = i + 1; j < nodeData.length; j++) {
          const a = nodeData[i], b = nodeData[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const ox = (a.hs.w + b.hs.w + 32) - Math.abs(dx);
          const oy = (a.hs.h + b.hs.h + 26) - Math.abs(dy);
          if (ox > 0 && oy > 0) {
            if (ox < oy) { const s = (dx >= 0 ? 1 : -1) * ox / 2; a.x -= s; b.x += s; }
            else { const s = (dy >= 0 ? 1 : -1) * oy / 2; a.y -= s; b.y += s; }
          }
        }
      }
      nodeData.forEach(a => {
        a.x = Math.max(a.hs.w + 18, Math.min(W - a.hs.w - 18, a.x));
        a.y = Math.max(a.hs.h + 96, Math.min(H - a.hs.h - 64, a.y));
      });
    }
  }

  const pos = {};
  nodeData.forEach(nd => { pos[nd.n.id] = { x: nd.x, y: nd.y }; });

  // Load saved pan
  const savedPan = JSON.parse(localStorage.getItem('constel-pan') || 'null');
  if (savedPan) constellationPan = savedPan;

  // Build SVG edges
  const edgeSvg = edges.map(([a, b, n]) => {
    const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2 - 36;
    return `<path class="edge" data-ea="${n.id}" data-eb="${b.n.id}" style="--accent:${domainConfig(n.domaine).color}" d="M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}"/>`;
  }).join('');

  // Hub labels
  const hubLabels = domKeys.map(dk => {
    const items = nodeData.filter(nd => nd.n.domaine === dk && !nd.n.est_meta);
    if (!items.length) return '';
    const d = domainConfig(dk);
    const minY = Math.min(...items.map(nd => nd.y));
    const avgX = items.reduce((s, nd) => s + nd.x, 0) / items.length;
    return `<div class="hub" style="--accent:${d.color};left:${avgX}px;top:${minY - 50}px">
      <div class="hlabel"><span class="ddot"></span>${d.label}</div></div>`;
  }).join('');

  // Node bubbles
  const nodesHtml = notes.map(n => {
    const p = pos[n.id]; if (!p) return '';
    const d = domainConfig(n.domaine);
    return `<div class="cnode${n.est_meta ? ' meta' : ''}" data-cid="${n.id}" style="left:${p.x}px;top:${p.y}px;--accent:${d.color}">
      <div class="bubble"><span class="ddot"></span><span class="ct">${n.titre}</span></div></div>`;
  }).join('');

  const legendHtml = DOMAIN_ORDER.filter(dk => notes.some(n => n.domaine === dk)).map(dk => {
    const d = domainConfig(dk);
    return `<div class="li" style="--accent:${d.color}"><span class="ddot"></span><span>${d.label}</span></div>`;
  }).join('');

  view.innerHTML = `
    <div class="constel" id="constel-inner">
      <span class="hint">glisser pour naviguer · déplacer les bulles</span>
      <div class="world" id="constel-world" style="transform:translate(${constellationPan.x}px,${constellationPan.y}px)">
        <svg class="links">${edgeSvg}</svg>
        ${hubLabels}
        ${nodesHtml}
      </div>
      <div class="legend">${legendHtml}</div>
    </div>`;

  // Persist force-directed positions immediately so layout is stable on next load
  if (!allSaved) _constelSaveState();

  const inner = document.getElementById('constel-inner');
  let panDrag  = null;   // { offsetX, offsetY }
  let nodeDrag = null;   // { id, startX, startY, origX, origY }
  let dragMoved = false;

  // ── Node drag ──────────────────────────────────────────────────────────────
  view.querySelectorAll('.cnode').forEach(el => {
    el.addEventListener('pointerdown', e => {
      e.stopPropagation(); // prevent pan from starting
      dragMoved = false;
      nodeDrag = {
        id: el.dataset.cid,
        startX: e.clientX, startY: e.clientY,
        origX: parseFloat(el.style.left), origY: parseFloat(el.style.top),
      };
      el.setPointerCapture(e.pointerId);
    });

    el.addEventListener('pointermove', e => {
      if (!nodeDrag || nodeDrag.id !== el.dataset.cid) return;
      const dx = e.clientX - nodeDrag.startX;
      const dy = e.clientY - nodeDrag.startY;
      if (Math.abs(dx) + Math.abs(dy) > 4) dragMoved = true;
      const newX = nodeDrag.origX + dx;
      const newY = nodeDrag.origY + dy;
      el.style.left = newX + 'px';
      el.style.top  = newY + 'px';
      _constelUpdateEdges(view, el.dataset.cid, newX, newY);
    });

    el.addEventListener('pointerup', () => {
      if (!nodeDrag || nodeDrag.id !== el.dataset.cid) return;
      nodeDrag = null;
      _constelSaveState();
    });

    el.addEventListener('pointercancel', () => { nodeDrag = null; });

    el.addEventListener('mouseenter', () => {
      const id = el.dataset.cid;
      view.querySelectorAll(`.edge[data-ea="${id}"], .edge[data-eb="${id}"]`)
        .forEach(p => p.classList.add('lit'));
    });
    el.addEventListener('mouseleave', () => {
      view.querySelectorAll('.edge.lit').forEach(p => p.classList.remove('lit'));
    });

    el.addEventListener('click', e => {
      if (dragMoved) { dragMoved = false; return; }
      const note = state.filteredList.find(n => n.id === el.dataset.cid);
      if (note) openModal(note);
    });
  });

  // ── Pan drag (background only) ─────────────────────────────────────────────
  inner.addEventListener('pointerdown', e => {
    if (nodeDrag) return;
    dragMoved = false;
    // Fix: always read current constellationPan, never a stale closure variable
    panDrag = { offsetX: e.clientX - constellationPan.x, offsetY: e.clientY - constellationPan.y };
  });

  inner.addEventListener('pointermove', e => {
    if (!panDrag || nodeDrag) return;
    const newX = e.clientX - panDrag.offsetX;
    const newY = e.clientY - panDrag.offsetY;
    if (Math.abs(newX - constellationPan.x) + Math.abs(newY - constellationPan.y) > 4) dragMoved = true;
    constellationPan = { x: newX, y: newY };
    document.getElementById('constel-world').style.transform = `translate(${newX}px,${newY}px)`;
  });

  inner.addEventListener('pointerup', () => {
    if (panDrag) _constelSaveState();
    panDrag = null;
  });

  inner.addEventListener('pointerleave', () => {
    panDrag = null;
    view.querySelectorAll('.edge.lit').forEach(p => p.classList.remove('lit'));
  });
}

// ── Render principal ──────────────────────────────────────────────────────────

function renderGrille() {
  document.getElementById('grille-view').classList.remove('hidden');
  document.getElementById('constel-view').classList.add('hidden');
  renderFilters();
  renderSections();
  renderStatusbar();
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

  const sb = document.getElementById('statusbar');
  if (sb) sb.classList.toggle('hidden', state.mode !== 'grille');

  if (state.mode === 'grille') renderGrille();
  else {
    document.getElementById('grille-view').classList.add('hidden');
    renderConstellation();
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

const BLOC_COLORS = {
  travail:   'var(--d-travail)',
  projets:   'var(--d-projets)',
  blocnotes: 'var(--d-meta)',
};

function renderBlocCol({ name, titre, items }) {
  const uncheckedCount = items.filter(it => !state.checkedItems.has(`${name}:${it.idx}`)).length;
  const dotColor = BLOC_COLORS[name] || 'var(--ink-4)';
  return `
    <div class="bloc-col">
      <div class="bloc-col-header"><span class="ddot" style="--accent:${dotColor}"></span>${titre} <span style="opacity:.5">(${uncheckedCount})</span></div>
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
    await loadDomains(); // re-sync domain names/colors from DB (handles rename + first-load timing)
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
  await loadDomains();
  await loadData(false); // premier chargement avec animations
  setInterval(() => loadData(true), 2 * 60 * 1000); // rafraîchir toutes les 2 min (silencieux)
  animate('#topbar, #chat-bar, #filter-bar', {
    opacity: [0, 1], translateY: ['8px', '0px'],
    delay: stagger(30), duration: 500, ease: 'outQuart',
  });

  // Écoute les événements de sync de brain_agent.py via IPC
  if (window.onSyncState) {
    window.onSyncState((state) => {
      const btnR = document.getElementById('btn-refresh');
      if (state === 'start') {
        if (btnR) btnR.classList.add('spinning');
      } else {
        if (btnR) btnR.classList.remove('spinning');
        if (state === 'end') loadData(false);
      }
    });
  }
})();
