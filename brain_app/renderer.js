import { animate, stagger, utils } from './node_modules/animejs/dist/modules/index.js';

const API = window.BRAIN_API_URL || 'http://127.0.0.1:7842';

const DOMAIN_ORDER = [
  'Travail', 'Apprentissage', 'Projets perso',
  'Jeux vidéos', 'Plantes', 'Organisation TDAH',
];

const DOMAIN_EMOJI = {
  'Travail':            '💼',
  'Apprentissage':      '🧠',
  'Projets perso':      '🚀',
  'Jeux vidéos':        '🎮',
  'Plantes':            '🌱',
  'Organisation TDAH':  '🧩',
};

// ── Utils ────────────────────────────────────────────────────────────────────

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const d = Math.floor(diff / 86400000);
  if (d === 0) return "aujourd'hui";
  if (d === 1) return 'hier';
  if (d < 7)   return `il y a ${d}j`;
  return new Date(dateStr).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

// ── Card factory ─────────────────────────────────────────────────────────────

function makeCard(note, compact = false) {
  const div = document.createElement('div');
  div.className = compact ? 'card card-compact' : 'card';
  div.dataset.id      = note.id;
  div.dataset.domaine = note.domaine || '';

  if (compact) {
    div.innerHTML = `
      <div class="card-dot"></div>
      <div class="card-body">
        <div class="card-title">${note.titre_court || '—'}</div>
        <div class="card-meta">${timeAgo(note.date_capture)}</div>
      </div>
    `;
  } else {
    div.innerHTML = `
      <div class="card-dot"></div>
      <div class="card-title">${note.titre_court || '—'}</div>
      <div class="card-insight">${note.insight_cle || ''}</div>
      <div class="card-meta">${timeAgo(note.date_capture)}</div>
    `;
  }
  return div;
}

// ── Loaders ──────────────────────────────────────────────────────────────────

async function loadStatus() {
  try {
    const data = await fetch(`${API}/status`).then(r => r.json());
    document.getElementById('status-pill').textContent =
      `${data.total_notes} notes · ${data.meta_fiches_count} synthèses`;
  } catch {
    document.getElementById('status-pill').textContent = 'serveur hors ligne';
  }
}

async function loadFeatured() {
  try {
    const notes = await fetch(`${API}/a-la-une?limit=5`).then(r => r.json());
    const container = document.getElementById('featured-cards');
    container.innerHTML = '';
    notes.forEach(n => container.appendChild(makeCard(n)));
    animate(container.querySelectorAll('.card'), {
      opacity:    [0, 1],
      translateY: ['16px', '0px'],
      delay:      stagger(80),
      duration:   500,
      ease:       'outQuart',
    });
  } catch { /* serveur pas démarré */ }
}

async function loadDomains() {
  try {
    const notes = await fetch(`${API}/notes?limit=100`).then(r => r.json());
    const container = document.getElementById('domains-container');
    container.innerHTML = '';

    // Group by domain
    const groups = {};
    notes.forEach(n => {
      if (!groups[n.domaine]) groups[n.domaine] = [];
      groups[n.domaine].push(n);
    });

    DOMAIN_ORDER.forEach(domaine => {
      const group = groups[domaine];
      if (!group?.length) return;

      const section  = document.createElement('div');
      section.className = 'domain-section';

      const header   = document.createElement('div');
      header.className = 'domain-header';
      header.innerHTML = `
        <span class="domain-header-left">
          <span class="section-label">${DOMAIN_EMOJI[domaine]} ${domaine}</span>
        </span>
        <span>
          <span class="domain-count">${group.length}</span>
          <span class="domain-chevron">▾</span>
        </span>
      `;

      const cardsList = document.createElement('div');
      cardsList.className = 'domain-cards-list';
      group.slice(0, 6).forEach(n => cardsList.appendChild(makeCard(n, true)));

      let collapsed = false;
      header.addEventListener('click', () => {
        collapsed = !collapsed;
        cardsList.classList.toggle('hidden', collapsed);
        header.querySelector('.domain-chevron').classList.toggle('collapsed', collapsed);
      });

      section.appendChild(header);
      section.appendChild(cardsList);
      container.appendChild(section);
    });

    animate(container.querySelectorAll('.card'), {
      opacity:    [0, 1],
      translateY: ['10px', '0px'],
      delay:      stagger(30),
      duration:   350,
      ease:       'outCubic',
    });
  } catch { /* serveur pas démarré */ }
}

// ── Aurora animations ────────────────────────────────────────────────────────

animate('.blob-1', {
  translateX: ['0rem', '7rem', '-4rem', '0rem'],
  translateY: ['0rem', '-5rem', '4rem', '0rem'],
  scale:      [1, 1.25, 0.85, 1],
  duration:   16000,
  ease:       'inOut',
  loop:       true,
});

animate('.blob-2', {
  translateX: ['0rem', '-5rem', '6rem', '0rem'],
  translateY: ['0rem', '5rem', '-3rem', '0rem'],
  scale:      [1, 0.8, 1.2, 1],
  duration:   20000,
  ease:       'inOut',
  loop:       true,
});

// ── Particles flottantes ─────────────────────────────────────────────────────

for (let i = 0; i < 25; i++) {
  const p    = document.createElement('div');
  const top  = utils.random(0, 100);
  const left = utils.random(0, 100);
  p.style.cssText = `
    position: fixed; width: 1.5px; height: 1.5px; border-radius: 50%;
    background: rgba(255,255,255,0.12); pointer-events: none; z-index: 0;
    left: ${left}%; top: ${top}%;
  `;
  document.body.appendChild(p);
  animate(p, {
    translateX: `${utils.random(-60, 60)}px`,
    translateY: `${utils.random(-50, 50)}px`,
    opacity:    [0.12, 0, 0.12],
    delay:      utils.random(0, 6000),
    duration:   utils.random(5000, 10000),
    ease:       'inOut',
    loop:       true,
  });
}

// ── Chat ─────────────────────────────────────────────────────────────────────

document.getElementById('chat-input').addEventListener('keydown', async (e) => {
  if (e.key !== 'Enter') return;
  const query = e.target.value.trim();
  if (!query) return;

  const responseEl = document.getElementById('chat-response');
  responseEl.classList.remove('hidden');
  responseEl.textContent = '⏳ Recherche en cours…';

  try {
    const data = await fetch(`${API}/chat`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ query }),
    }).then(r => r.json());

    responseEl.textContent = data.reponse || '—';

    // Mettre en évidence les cards sources
    document.querySelectorAll('.card').forEach(card => {
      card.classList.remove('highlighted');
    });
    if (data.sources?.length) {
      const ids = new Set(data.sources.map(s => s.id));
      document.querySelectorAll('.card').forEach(card => {
        if (ids.has(card.dataset.id)) card.classList.add('highlighted');
      });
    }
  } catch {
    responseEl.textContent = '❌ Serveur non disponible.';
  }
});

// ── Init ─────────────────────────────────────────────────────────────────────

(async () => {
  await loadStatus();
  await loadFeatured();
  await loadDomains();
})();
