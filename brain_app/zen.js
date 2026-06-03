// zen.js — Shell de l'onglet Zen

const ACTIVITIES = [
  { id: 'aim',       icon: '🎯', label: 'Aim',      module: () => import('./activities/aim.js')    },
  { id: 'solar',     icon: '🪐', label: 'Solaire',   module: () => import('./activities/solar.js')  },
  { id: 'breath',    icon: '🫁', label: 'Respir.',   module: () => import('./activities/breath.js') },
  { id: 'particles', icon: '✨', label: 'Particles', module: null },
  { id: 'bubbles',   icon: '🫧', label: 'Bulles',    module: null },
  { id: 'sliders',   icon: '🎚️', label: 'Tableau',   module: null },
  { id: 'fluid',     icon: '🌊', label: 'Fluide',    module: null },
  { id: 'ripple',    icon: '💧', label: 'Ondules',   module: null },
  { id: 'kaleido',   icon: '🔮', label: 'Kaleido',   module: null },
];

let currentActivity = null;
let currentId = null;

async function loadActivity(id) {
  const entry = ACTIVITIES.find(a => a.id === id);
  if (!entry?.module) return;

  if (currentActivity?.stop) currentActivity.stop();
  currentActivity = null;

  const area = document.getElementById('zen-canvas-area');
  area.innerHTML = '';

  document.querySelectorAll('.zen-tab').forEach(b =>
    b.classList.toggle('active', b.dataset.id === id)
  );

  currentId = id;
  const mod = await entry.module();
  currentActivity = mod.create(area);
  currentActivity.start();
}

export function initZen() {
  const view = document.getElementById('zen-view');

  view.innerHTML = `
    <div id="zen-canvas-area"></div>
    <div id="zen-bottom-bar"></div>
  `;

  const bar = document.getElementById('zen-bottom-bar');
  ACTIVITIES.forEach(a => {
    const btn = document.createElement('button');
    btn.className = 'zen-tab' + (a.module ? ' available' : '');
    btn.dataset.id = a.id;
    btn.innerHTML = `<span class="zen-tab-icon">${a.icon}</span><span class="zen-tab-label">${a.label}</span>`;
    if (a.module) btn.addEventListener('click', () => loadActivity(a.id));
    bar.appendChild(btn);
  });
}

export function activateZen() {
  if (currentActivity) return;
  loadActivity(currentId || 'aim');
}

export function deactivateZen() {
  if (currentActivity?.stop) currentActivity.stop();
  currentActivity = null;
}
