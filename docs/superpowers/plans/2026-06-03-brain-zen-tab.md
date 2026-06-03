# Brain Zen Tab Batch 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un onglet "Zen" avec barre du bas et 3 activités interactives (Aim Trainer, Système Solaire, Bulle Respiratoire) à l'app Electron Second Cerveau.

**Architecture:** `zen.js` gère le shell (bottom bar, chargement dynamique des activités). Chaque activité est un module ES dans `activities/` exportant `create(container) → {start, stop}`. `renderer.js` ajoute le mode 'zen' et délègue le cycle de vie à `zen.js` via `activateZen()` / `deactivateZen()`.

**Tech Stack:** Canvas2D, ES modules dynamiques (`import()`), Web Audio API, ResizeObserver, requestAnimationFrame.

---

## File structure

| Fichier | Rôle |
|---|---|
| `brain_app/index.html` | +`#zen-view`, +`btn-zen` dans modeswitch |
| `brain_app/zen.css` | Styles zen-view, bottom bar, onglets |
| `brain_app/zen.js` | Shell : `initZen`, `activateZen`, `deactivateZen`, `loadActivity` |
| `brain_app/activities/aim.js` | Aim trainer complet |
| `brain_app/activities/solar.js` | Système solaire |
| `brain_app/activities/breath.js` | Bulle respiratoire |
| `brain_app/renderer.js` | Import zen.js, mode 'zen', renderTopbar étendu, render() étendu, appel initZen |

---

## Task 1 : Shell Zen

**Files:**
- Modify: `brain_app/index.html`
- Create: `brain_app/zen.css`
- Create: `brain_app/zen.js`
- Modify: `brain_app/renderer.js`

- [ ] **Step 1 : Modifier `index.html` — ajouter le bouton Zen et le zen-view**

Dans `brain_app/index.html`, dans la div `.modeswitch` (après le `<button id="btn-constellation">`), ajouter :
```html
          <button id="btn-zen"></button>
```

Juste avant `<section id="blocs-section">` (ligne 65), ajouter :
```html
      <!-- Onglet Zen -->
      <div id="zen-view" class="hidden"></div>
```

- [ ] **Step 2 : Créer `brain_app/zen.css`**

```css
/* ============================================================
   Onglet Zen
   ============================================================ */
#zen-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
  z-index: 1;
}

#zen-canvas-area {
  flex: 1;
  min-height: 0;
  position: relative;
  overflow: hidden;
  background: #09090f;
}

#zen-bottom-bar {
  flex-shrink: 0;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  border-top: 1px solid var(--stroke);
  background: rgba(255,255,255,0.02);
  overflow-x: auto;
  padding: 0 8px;
  gap: 4px;
}
#zen-bottom-bar::-webkit-scrollbar { display: none; }

.zen-tab {
  all: unset;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 6px 10px;
  border-radius: 10px;
  cursor: pointer;
  min-width: 48px;
  opacity: 0.35;
  transition: background .15s var(--ease), opacity .15s var(--ease);
  flex-shrink: 0;
}
.zen-tab.available { opacity: 1; cursor: pointer; }
.zen-tab.available:hover { background: var(--glass); }
.zen-tab.active { background: var(--glass); opacity: 1; }

.zen-tab-icon  { font-size: 18px; line-height: 1; pointer-events: none; }
.zen-tab-label {
  font-family: var(--font-mono);
  font-size: 7.5px;
  letter-spacing: 0.05em;
  color: var(--ink-4);
  text-transform: uppercase;
  pointer-events: none;
}
.zen-tab.active .zen-tab-label { color: oklch(0.85 0.11 90); }
```

- [ ] **Step 3 : Ajouter le lien `zen.css` dans `index.html`**

Dans `<head>`, après `<link rel="stylesheet" href="style.css">` :
```html
  <link rel="stylesheet" href="zen.css">
```

- [ ] **Step 4 : Créer `brain_app/zen.js`**

```javascript
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

  // Stop and clear current activity
  if (currentActivity?.stop) currentActivity.stop();
  currentActivity = null;

  const area = document.getElementById('zen-canvas-area');
  area.innerHTML = '';

  // Update bottom bar active state
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

  // Build structure
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
  if (currentActivity) return; // already running, keep current
  loadActivity(currentId || 'aim');
}

export function deactivateZen() {
  if (currentActivity?.stop) currentActivity.stop();
  currentActivity = null;
}
```

- [ ] **Step 5 : Modifier `renderer.js` — imports, mode zen, renderTopbar, render, initZen**

**5a.** En haut de `renderer.js`, après la ligne `import { animate, stagger } from ...`, ajouter :
```javascript
import { initZen, activateZen, deactivateZen } from './zen.js';
```

**5b.** Remplacer la fonction `renderTopbar()` existante. La version actuelle se trouve autour de la ligne 173. Trouver le bloc qui ajoute les écouteurs de boutons (`btnG.addEventListener` et `btnC.addEventListener`) et ajouter le bouton zen. Remplacer les lignes du `if (!btnG._init)` block par :

```javascript
  if (!btnG._init) {
    btnG._init = true;
    btnG.addEventListener('click', () => setState({ mode: 'grille' }));
    btnC.addEventListener('click', () => setState({ mode: 'constellation' }));
    document.getElementById('btn-zen').addEventListener('click', () => setState({ mode: 'zen' }));
  }
  btnG.classList.toggle('active', state.mode === 'grille');
  btnC.classList.toggle('active', state.mode === 'constellation');
  document.getElementById('btn-zen').classList.toggle('active', state.mode === 'zen');
```

Le bouton zen a besoin d'un label. Ajouter dans `renderTopbar()` la ligne qui initialise son innerHTML, juste après la ligne qui fait `btnC.innerHTML = ...` :
```javascript
  document.getElementById('btn-zen').innerHTML = '🎮 Zen';
```

**5c.** Remplacer la fonction `render()` entière (lignes 706-716) :

```javascript
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
```

**5d.** Dans l'IIFE (bas du fichier), ajouter `initZen()` après `initBlocsResize()` :

```javascript
(async () => {
  render();
  initChat();
  initBlocsResize();
  initZen();           // ← ajouter
  await loadData();
  setInterval(loadData, 2 * 60 * 1000);
  animate('#topbar, #une-head, #featured-cards, #chat-bar, #filter-bar', {
    opacity: [0, 1], translateY: ['8px', '0px'],
    delay: stagger(30), duration: 500, ease: 'outQuart',
  });
})();
```

- [ ] **Step 6 : Vérifier les tests Python (aucune régression)**

```powershell
cd "C:\Users\yapa\second_cerveau"
python -m pytest tests/ -q
```

Expected: 33 passed.

- [ ] **Step 7 : Vérifier visuellement**

Lancer l'app (`brain_start.bat`). Vérifier :
- [ ] Bouton "🎮 Zen" apparaît dans la topbar
- [ ] Clic Zen → grille disparaît, blocs section disparaît, zone noire apparaît
- [ ] Bottom bar visible en bas avec 9 icônes (aim, solar, breath actives, 6 grises)
- [ ] Clic Grille → revient à la grille normalement

- [ ] **Step 8 : Commit**

```powershell
git add brain_app/index.html brain_app/zen.css brain_app/zen.js brain_app/renderer.js
git commit -m "feat: add Zen tab shell with bottom navigation bar"
```

---

## Task 2 : Aim Trainer

**Files:**
- Create: `brain_app/activities/aim.js`

- [ ] **Step 1 : Créer le dossier `brain_app/activities/`**

```powershell
New-Item -ItemType Directory -Path "C:\Users\yapa\second_cerveau\brain_app\activities" -Force
```

- [ ] **Step 2 : Créer `brain_app/activities/aim.js`**

```javascript
// activities/aim.js — Aim Trainer

export function create(container) {
  container.innerHTML = `
    <canvas id="aim-canvas" style="position:absolute;inset:0;width:100%;height:100%;cursor:crosshair"></canvas>
    <div id="aim-hud" style="position:absolute;top:0;left:0;right:0;display:flex;align-items:center;gap:20px;padding:10px 16px;background:rgba(0,0,0,0.45);border-bottom:1px solid rgba(255,255,255,0.06);font-family:monospace">
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-size:8px;letter-spacing:.1em;color:#4a4a5a">SCORE</span>
        <span id="aim-score" style="font-size:18px;font-weight:700;color:#f4f4f7">0</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-size:8px;letter-spacing:.1em;color:#4a4a5a">STREAK</span>
        <span id="aim-streak" style="font-size:18px;font-weight:700;color:#f4f4f7">0</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-size:8px;letter-spacing:.1em;color:#4a4a5a">PRÉCISION</span>
        <span id="aim-acc" style="font-size:18px;font-weight:700;color:#f4f4f7">—</span>
      </div>
      <div style="margin-left:auto;display:flex;flex-direction:column;align-items:center;gap:2px">
        <span style="font-size:8px;letter-spacing:.1em;color:#4a4a5a">TEMPS</span>
        <span id="aim-timer" style="font-size:18px;font-weight:700;color:oklch(0.85 0.11 90)">—</span>
      </div>
    </div>
    <div id="aim-mode-bar" style="position:absolute;bottom:20px;left:50%;transform:translateX(-50%);display:flex;gap:10px">
      <button id="btn-timed" style="font-family:monospace;font-size:11px;padding:10px 18px;border-radius:8px;background:oklch(0.72 0.15 25 / 0.2);color:oklch(0.82 0.14 25);border:1px solid oklch(0.72 0.15 25 / 0.4);cursor:pointer;transition:background .15s">⏱ 30 secondes</button>
      <button id="btn-endless" style="font-family:monospace;font-size:11px;padding:10px 18px;border-radius:8px;background:rgba(255,255,255,0.05);color:#6a6a7c;border:1px solid rgba(255,255,255,0.1);cursor:pointer;transition:background .15s">∞ Endless</button>
    </div>
    <div id="aim-results" style="display:none;position:absolute;inset:0;background:rgba(8,8,12,0.92);flex-direction:column;align-items:center;justify-content:center;gap:16px;font-family:monospace">
      <div style="font-size:28px;font-weight:700;color:#f4f4f7">Résultats</div>
      <div id="aim-res-score" style="font-size:20px;color:oklch(0.85 0.11 90)"></div>
      <div id="aim-res-streak" style="font-size:14px;color:#a6a6b6"></div>
      <div id="aim-res-acc"    style="font-size:14px;color:#a6a6b6"></div>
      <button id="btn-replay" style="margin-top:12px;font-family:monospace;font-size:11px;padding:10px 24px;border-radius:8px;background:oklch(0.72 0.15 25 / 0.2);color:oklch(0.82 0.14 25);border:1px solid oklch(0.72 0.15 25 / 0.4);cursor:pointer">↺ Rejouer</button>
    </div>
  `;

  const canvas   = container.querySelector('#aim-canvas');
  const ctx      = canvas.getContext('2d');
  const scoreEl  = container.querySelector('#aim-score');
  const streakEl = container.querySelector('#aim-streak');
  const accEl    = container.querySelector('#aim-acc');
  const timerEl  = container.querySelector('#aim-timer');
  const modeBar  = container.querySelector('#aim-mode-bar');
  const resultsEl = container.querySelector('#aim-results');

  let audioCtx = null;
  let target = null;
  let hits = 0, misses = 0, streak = 0, bestStreak = 0, score = 0;
  let mode = null;
  let timeLeft = 30;
  let timerInterval = null;
  let running = false;
  let rafId = null;

  function getAudio() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    return audioCtx;
  }

  function resize() {
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);
  resize();

  function playPop() {
    try {
      const ac = getAudio();
      const osc = ac.createOscillator();
      const gain = ac.createGain();
      osc.connect(gain); gain.connect(ac.destination);
      osc.frequency.setValueAtTime(900, ac.currentTime);
      osc.frequency.exponentialRampToValueAtTime(200, ac.currentTime + 0.08);
      gain.gain.setValueAtTime(0.12, ac.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.1);
      osc.start(); osc.stop(ac.currentTime + 0.1);
    } catch {}
  }

  function updateHUD() {
    scoreEl.textContent  = score;
    streakEl.textContent = streak >= 3 ? `🔥${streak}` : streak;
    const total = hits + misses;
    accEl.textContent    = total > 0 ? Math.round(hits / total * 100) + '%' : '—';
    timerEl.textContent  = mode === 'timed' ? timeLeft + 's' : '∞';
  }

  function spawnTarget() {
    const pad = 80, r = 28;
    const hudH = 52;
    target = {
      x: pad + Math.random() * (canvas.width  - pad * 2),
      y: hudH + pad + Math.random() * (canvas.height - hudH - pad * 2),
      r, scale: 0,
      bornAt: performance.now(),
      lifetime: 2500,
      dying: false,
      particles: [],
    };
  }

  function onHit() {
    if (!target || !running || target.dying) return;
    playPop();
    hits++; streak++;
    if (streak > bestStreak) bestStreak = streak;
    const mult = streak >= 5 ? 3 : streak >= 3 ? 2 : 1;
    score += 10 * mult;
    for (let i = 0; i < 8; i++) {
      const a = (Math.PI * 2 / 8) * i;
      target.particles.push({ x: target.x, y: target.y, vx: Math.cos(a) * 4, vy: Math.sin(a) * 4, life: 1 });
    }
    target.dying = true;
    setTimeout(() => { target = null; if (running) spawnTarget(); }, 200);
    updateHUD();
  }

  function onMiss() {
    if (!running) return;
    misses++; streak = 0;
    updateHUD();
  }

  function draw(now) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (target) {
      const age = now - target.bornAt;

      if (age > target.lifetime && !target.dying) {
        target = null;
        if (running) spawnTarget();
        rafId = requestAnimationFrame(draw);
        return;
      }

      if (!target.dying) {
        const t = Math.min(1, age / 200);
        target.scale = t * t; // ease in
        const remaining = target.lifetime - age;
        if (remaining < 800) target.scale *= remaining / 800;
        target.scale = Math.max(0.25, target.scale);
      } else {
        target.scale = Math.max(0, target.scale - 0.1);
      }

      // Draw target
      ctx.save();
      ctx.translate(target.x, target.y);
      ctx.scale(target.scale, target.scale);

      ctx.beginPath();
      ctx.arc(0, 0, target.r, 0, Math.PI * 2);
      ctx.strokeStyle = 'oklch(0.72 0.15 25 / 0.9)';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, target.r * 0.55, 0, Math.PI * 2);
      ctx.strokeStyle = 'oklch(0.72 0.15 25 / 0.5)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, 5, 0, Math.PI * 2);
      ctx.fillStyle = 'oklch(0.72 0.15 25)';
      ctx.fill();

      ctx.restore();

      // Particles
      for (const p of target.particles) {
        p.x += p.vx; p.y += p.vy; p.vx *= 0.9; p.vy *= 0.9; p.life -= 0.06;
        if (p.life > 0) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3 * p.life, 0, Math.PI * 2);
          ctx.fillStyle = `oklch(0.72 0.15 25 / ${p.life.toFixed(2)})`;
          ctx.fill();
        }
      }
      target.particles = target.particles.filter(p => p.life > 0);
    }

    rafId = requestAnimationFrame(draw);
  }

  function showResults() {
    resultsEl.style.display = 'flex';
    resultsEl.querySelector('#aim-res-score').textContent  = `Score : ${score}`;
    resultsEl.querySelector('#aim-res-streak').textContent = `Meilleur streak : 🔥${bestStreak}`;
    const total = hits + misses;
    resultsEl.querySelector('#aim-res-acc').textContent    = `Précision : ${total > 0 ? Math.round(hits / total * 100) : 0}%`;
  }

  function startMode(m) {
    mode = m;
    hits = misses = streak = bestStreak = score = timeLeft = 0;
    timeLeft = 30;
    running  = true;
    modeBar.style.display  = 'none';
    resultsEl.style.display = 'none';
    updateHUD();
    spawnTarget();
    if (m === 'timed') {
      timerInterval = setInterval(() => {
        timeLeft--;
        updateHUD();
        if (timeLeft <= 0) {
          clearInterval(timerInterval);
          timerInterval = null;
          running = false;
          target  = null;
          showResults();
        }
      }, 1000);
    }
  }

  canvas.addEventListener('click', e => {
    if (!running || !target) return;
    const rect = canvas.getBoundingClientRect();
    const dx = e.clientX - rect.left - target.x;
    const dy = e.clientY - rect.top  - target.y;
    if (Math.hypot(dx, dy) <= target.r * target.scale) onHit();
    else onMiss();
  });

  container.querySelector('#btn-timed').addEventListener('click',   () => startMode('timed'));
  container.querySelector('#btn-endless').addEventListener('click', () => startMode('endless'));
  container.querySelector('#btn-replay').addEventListener('click',  () => {
    resultsEl.style.display = 'none';
    modeBar.style.display   = 'flex';
    running = false;
    target  = null;
    updateHUD();
  });

  function start() {
    resize();
    rafId = requestAnimationFrame(draw);
  }

  function stop() {
    running = false;
    if (timerInterval) clearInterval(timerInterval);
    if (rafId) cancelAnimationFrame(rafId);
    ro.disconnect();
    if (audioCtx && audioCtx.state !== 'closed') audioCtx.close().catch(() => {});
    container.innerHTML = '';
  }

  return { start, stop };
}
```

- [ ] **Step 3 : Vérifier visuellement**

Lancer l'app, aller dans l'onglet Zen, cliquer "🎯" :
- [ ] Aim trainer s'affiche avec HUD (score, streak, précision, temps)
- [ ] Boutons "⏱ 30 secondes" et "∞ Endless" visibles au centre
- [ ] Clic "30 secondes" → cible orange pulsante apparaît, timer commence à 30
- [ ] Clic sur la cible → pop, particules, score augmente, streak
- [ ] Fin des 30s → écran résultats avec score/streak/précision
- [ ] "↺ Rejouer" → revient aux boutons de mode
- [ ] Mode Endless → pas de timer, cibles en continu

- [ ] **Step 4 : Tests Python (aucune régression)**

```powershell
cd "C:\Users\yapa\second_cerveau"
python -m pytest tests/ -q
```

Expected: 33 passed.

- [ ] **Step 5 : Commit**

```powershell
git add brain_app/activities/aim.js
git commit -m "feat: add Aim Trainer activity (30s + endless modes, score/streak/accuracy)"
```

---

## Task 3 : Système Solaire

**Files:**
- Create: `brain_app/activities/solar.js`

- [ ] **Step 1 : Créer `brain_app/activities/solar.js`**

```javascript
// activities/solar.js — Système solaire interactif

export function create(container) {
  container.innerHTML = `
    <canvas id="solar-canvas" style="position:absolute;inset:0;width:100%;height:100%;cursor:default"></canvas>
    <div id="solar-gravity" style="position:absolute;bottom:20px;left:16px;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:10px 14px;font-family:monospace">
      <div style="font-size:8px;letter-spacing:.1em;color:#3a3a4a;margin-bottom:8px">GRAVITÉ</div>
      <label style="display:flex;align-items:center;gap:7px;font-size:10px;color:#4a4a5a;cursor:pointer;margin-bottom:4px">
        <input type="radio" name="grav" value="0"> Faible
      </label>
      <label style="display:flex;align-items:center;gap:7px;font-size:10px;color:#a6a6b6;cursor:pointer;margin-bottom:4px">
        <input type="radio" name="grav" value="1" checked> Normale
      </label>
      <label style="display:flex;align-items:center;gap:7px;font-size:10px;color:#4a4a5a;cursor:pointer">
        <input type="radio" name="grav" value="2"> Forte
      </label>
    </div>
    <div style="position:absolute;top:12px;left:50%;transform:translateX(-50%);font-family:monospace;font-size:9px;color:#2a2a3a;letter-spacing:.1em">
      ATTRAPE LES PLANÈTES ET LANCE-LES
    </div>
  `;

  const canvas = container.querySelector('#solar-canvas');
  const ctx    = canvas.getContext('2d');

  const G_VALUES = [60, 200, 500];
  let G = G_VALUES[1];
  const SUN_MASS = 1e6;

  let rafId = null;
  let lastTime = 0;

  const sun = { x: 0, y: 0, r: 18 };

  function resize() {
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight;
    sun.x = canvas.width  / 2;
    sun.y = canvas.height / 2;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);

  const PLANET_COLORS = [
    'oklch(0.72 0.15 25)',
    'oklch(0.72 0.13 255)',
    'oklch(0.78 0.14 150)',
  ];

  function makeOrbit(orbitR, color) {
    const angle = Math.random() * Math.PI * 2;
    const speed = Math.sqrt(G * SUN_MASS / Math.max(orbitR, 40));
    return {
      x:     sun.x + Math.cos(angle) * orbitR,
      y:     sun.y + Math.sin(angle) * orbitR,
      vx:   -Math.sin(angle) * speed,
      vy:    Math.cos(angle) * speed,
      r: 9,
      color,
      trail: [],
    };
  }

  let planets = [];

  function initPlanets() {
    resize();
    planets = [100, 165, 235].map((r, i) => makeOrbit(r, PLANET_COLORS[i]));
  }

  let dragging = null;
  let dragHistory = [];

  canvas.addEventListener('mousedown', e => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    for (const p of planets) {
      if (Math.hypot(mx - p.x, my - p.y) < p.r + 10) {
        dragging = p;
        dragHistory = [[mx, my, performance.now()]];
        canvas.style.cursor = 'grabbing';
        break;
      }
    }
  });

  canvas.addEventListener('mousemove', e => {
    if (!dragging) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    dragging.x = mx; dragging.y = my;
    dragHistory.push([mx, my, performance.now()]);
    if (dragHistory.length > 6) dragHistory.shift();
  });

  canvas.addEventListener('mouseup', () => {
    if (!dragging) return;
    if (dragHistory.length >= 2) {
      const [x1, y1, t1] = dragHistory[0];
      const [x2, y2, t2] = dragHistory[dragHistory.length - 1];
      const dt = Math.max((t2 - t1) / 1000, 0.01);
      dragging.vx = (x2 - x1) / dt * 0.55;
      dragging.vy = (y2 - y1) / dt * 0.55;
    }
    dragging = null;
    dragHistory = [];
    canvas.style.cursor = 'default';
  });

  container.querySelectorAll('input[name="grav"]').forEach(r => {
    r.addEventListener('change', () => {
      G = G_VALUES[parseInt(r.value)];
    });
  });

  function update(dt) {
    const maxEscape = Math.max(canvas.width, canvas.height) * 1.6;
    for (const p of planets) {
      if (p === dragging) continue;
      const dx = sun.x - p.x;
      const dy = sun.y - p.y;
      const dist = Math.max(sun.r + p.r, Math.hypot(dx, dy));
      const force = G * SUN_MASS / (dist * dist);
      p.vx += force * (dx / dist) * dt;
      p.vy += force * (dy / dist) * dt;
      p.x  += p.vx * dt;
      p.y  += p.vy * dt;
      p.trail.push({ x: p.x, y: p.y });
      if (p.trail.length > 90) p.trail.shift();

      // Reset escaped planet
      if (Math.hypot(p.x - sun.x, p.y - sun.y) > maxEscape) {
        const fresh = makeOrbit(80 + Math.random() * 180, p.color);
        Object.assign(p, { x: fresh.x, y: fresh.y, vx: fresh.vx, vy: fresh.vy, trail: [] });
      }
    }
  }

  function drawSun() {
    const grad = ctx.createRadialGradient(sun.x, sun.y, 0, sun.x, sun.y, sun.r * 3);
    grad.addColorStop(0,   'oklch(0.95 0.1 90 / 0.9)');
    grad.addColorStop(0.35,'oklch(0.85 0.14 70 / 0.5)');
    grad.addColorStop(1,   'transparent');
    ctx.beginPath();
    ctx.arc(sun.x, sun.y, sun.r * 3, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.beginPath();
    ctx.arc(sun.x, sun.y, sun.r, 0, Math.PI * 2);
    ctx.fillStyle = 'oklch(0.94 0.1 90)';
    ctx.fill();
  }

  function drawPlanet(p) {
    // Trail
    if (p.trail.length > 1) {
      for (let i = 1; i < p.trail.length; i++) {
        const alpha = (i / p.trail.length) * 0.35;
        ctx.beginPath();
        ctx.moveTo(p.trail[i-1].x, p.trail[i-1].y);
        ctx.lineTo(p.trail[i].x,   p.trail[i].y);
        ctx.strokeStyle = p.color.replace(')', ` / ${alpha.toFixed(2)})`);
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
    // Glow
    const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 2.2);
    glow.addColorStop(0,   p.color.replace(')', ' / 0.4)'));
    glow.addColorStop(1,   'transparent');
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r * 2.2, 0, Math.PI * 2);
    ctx.fillStyle = glow;
    ctx.fill();
    // Body
    const body = ctx.createRadialGradient(p.x - p.r*0.3, p.y - p.r*0.3, 0, p.x, p.y, p.r);
    body.addColorStop(0, p.color.replace(')', ' / 0.95)'));
    body.addColorStop(1, p.color.replace(')', ' / 0.65)'));
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = body;
    ctx.fill();
  }

  function draw(now) {
    const dt = Math.min((now - lastTime) / 1000, 0.05);
    lastTime = now;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    update(dt);
    drawSun();
    planets.forEach(drawPlanet);

    rafId = requestAnimationFrame(draw);
  }

  function start() {
    initPlanets();
    lastTime = performance.now();
    rafId = requestAnimationFrame(draw);
  }

  function stop() {
    if (rafId) cancelAnimationFrame(rafId);
    ro.disconnect();
    container.innerHTML = '';
  }

  return { start, stop };
}
```

- [ ] **Step 2 : Vérifier visuellement**

Aller dans Zen → cliquer "🪐" :
- [ ] Soleil doré au centre avec glow, 3 planètes en orbite
- [ ] Traînées colorées derrière les planètes
- [ ] Cliquer+glisser une planète → suit le curseur
- [ ] Relâcher avec mouvement → planète part avec la vélocité du lancer
- [ ] Radio "Forte" → orbites déstabilisées, planètes spiralent vers le soleil
- [ ] Planète hors écran → réapparaît avec nouvelle orbite aléatoire

- [ ] **Step 3 : Tests Python**

```powershell
python -m pytest tests/ -q
```

Expected: 33 passed.

- [ ] **Step 4 : Commit**

```powershell
git add brain_app/activities/solar.js
git commit -m "feat: add Solar System activity with gravitational physics and drag/throw"
```

---

## Task 4 : Bulle Respiratoire

**Files:**
- Create: `brain_app/activities/breath.js`

- [ ] **Step 1 : Créer `brain_app/activities/breath.js`**

```javascript
// activities/breath.js — Bulle respiratoire guidée

export function create(container) {
  container.innerHTML = `
    <canvas id="breath-canvas" style="position:absolute;inset:0;width:100%;height:100%"></canvas>
    <div id="breath-label" style="position:absolute;bottom:32%;left:50%;transform:translateX(-50%);font-family:monospace;font-size:20px;font-weight:600;letter-spacing:.15em;pointer-events:none;transition:color .5s"></div>
    <div id="breath-rhythm" style="position:absolute;bottom:18px;left:50%;transform:translateX(-50%);display:flex;gap:8px">
      <button data-r="0" style="font-family:monospace;font-size:10px;padding:7px 14px;border-radius:8px;cursor:pointer;transition:all .15s;background:rgba(255,255,255,0.09);color:#f4f4f7;border:1px solid rgba(255,255,255,0.15)">Doux</button>
      <button data-r="1" style="font-family:monospace;font-size:10px;padding:7px 14px;border-radius:8px;cursor:pointer;transition:all .15s;background:rgba(255,255,255,0.04);color:#4a4a5a;border:1px solid rgba(255,255,255,0.07)">Box</button>
      <button data-r="2" style="font-family:monospace;font-size:10px;padding:7px 14px;border-radius:8px;cursor:pointer;transition:all .15s;background:rgba(255,255,255,0.04);color:#4a4a5a;border:1px solid rgba(255,255,255,0.07)">Rapide</button>
    </div>
  `;

  const canvas   = container.querySelector('#breath-canvas');
  const ctx      = canvas.getContext('2d');
  const labelEl  = container.querySelector('#breath-label');

  const RHYTHMS = [
    [4000, 4000, 4000, 2000],
    [4000, 4000, 4000, 4000],
    [3000, 3000, 3000, 2000],
  ];
  const PHASE_LABELS = ['Inspire', 'Retiens', 'Expire', 'Retiens'];
  const PHASE_COLORS = [
    'oklch(0.72 0.13 255)',
    'oklch(0.65 0.16 290)',
    'oklch(0.72 0.14 150)',
    'oklch(0.60 0.06 250)',
  ];
  // Scale at end of each phase (0=small, 1=big)
  const SIZE_END = [1.0, 1.0, 0.38, 0.38];

  let rhythm     = 0;
  let phase      = 0;
  let phaseStart = 0;
  let blobScale  = 0.38;
  let rafId      = null;

  function resize() {
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);
  resize();

  function easeInOut(t) { return t < 0.5 ? 2*t*t : -1 + (4 - 2*t)*t; }

  function drawBlob(cx, cy, r, t) {
    const N = 14;
    ctx.beginPath();
    for (let i = 0; i <= N; i++) {
      const a = (Math.PI * 2 / N) * i;
      const noise = 1
        + 0.07 * Math.sin(a * 3 + t * 0.7)
        + 0.04 * Math.sin(a * 5 - t * 1.1)
        + 0.025 * Math.sin(a * 7 + t * 1.6);
      const pr = r * noise;
      const x = cx + Math.cos(a) * pr;
      const y = cy + Math.sin(a) * pr;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
  }

  function draw(now) {
    const durations = RHYTHMS[rhythm];
    const elapsed   = now - phaseStart;
    const duration  = durations[phase];

    if (elapsed >= duration) {
      phase      = (phase + 1) % 4;
      phaseStart = now;
    }

    const progress = Math.min(1, elapsed / duration);
    const prevSize = SIZE_END[(phase - 1 + 4) % 4];
    const nextSize = SIZE_END[phase];
    blobScale = prevSize + (nextSize - prevSize) * easeInOut(progress);

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const cx     = canvas.width  / 2;
    const cy     = canvas.height * 0.42;
    const baseR  = Math.min(canvas.width, canvas.height) * 0.20;
    const r      = baseR * blobScale;
    const color  = PHASE_COLORS[phase];
    const t      = now / 1000;

    // Draw blob glow
    drawBlob(cx, cy, r * 1.35, t);
    const glowGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 1.35);
    glowGrad.addColorStop(0,   color.replace(')', ' / 0.15)'));
    glowGrad.addColorStop(1,   'transparent');
    ctx.fillStyle = glowGrad;
    ctx.fill();

    // Draw blob body
    drawBlob(cx, cy, r, t);
    const bodyGrad = ctx.createRadialGradient(cx - r*0.25, cy - r*0.25, 0, cx, cy, r);
    bodyGrad.addColorStop(0,   color.replace(')', ' / 0.75)'));
    bodyGrad.addColorStop(0.7, color.replace(')', ' / 0.40)'));
    bodyGrad.addColorStop(1,   color.replace(')', ' / 0.15)'));
    ctx.fillStyle = bodyGrad;
    ctx.fill();

    // Progress arc (ring around blob)
    const arcR = r * 1.28;
    // Background ring
    ctx.beginPath();
    ctx.arc(cx, cy, arcR, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 3;
    ctx.stroke();
    // Progress fill
    if (progress > 0.005) {
      ctx.beginPath();
      ctx.arc(cx, cy, arcR, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * progress);
      ctx.strokeStyle = color.replace(')', ' / 0.55)');
      ctx.lineWidth = 3;
      ctx.stroke();
    }

    // Label
    labelEl.textContent = PHASE_LABELS[phase];
    labelEl.style.color = color;

    rafId = requestAnimationFrame(draw);
  }

  container.querySelectorAll('[data-r]').forEach(btn => {
    btn.addEventListener('click', () => {
      rhythm     = parseInt(btn.dataset.r);
      phase      = 0;
      phaseStart = performance.now();
      container.querySelectorAll('[data-r]').forEach(b => {
        const active = b === btn;
        b.style.background   = active ? 'rgba(255,255,255,0.09)' : 'rgba(255,255,255,0.04)';
        b.style.color        = active ? '#f4f4f7' : '#4a4a5a';
        b.style.borderColor  = active ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.07)';
      });
    });
  });

  function start() {
    resize();
    phaseStart = performance.now();
    rafId = requestAnimationFrame(draw);
  }

  function stop() {
    if (rafId) cancelAnimationFrame(rafId);
    ro.disconnect();
    container.innerHTML = '';
  }

  return { start, stop };
}
```

- [ ] **Step 2 : Vérifier visuellement**

Aller dans Zen → cliquer "🫁" :
- [ ] Blob organique de couleur bleue visible et animé
- [ ] Le blob grandit pendant "Inspire" (4s), reste grand pendant "Retiens" (4s), rétrécit pendant "Expire" (4s)
- [ ] Arc de progression circulaire autour du blob
- [ ] Texte change : "Inspire" → "Retiens" → "Expire" → "Retiens"
- [ ] Couleur change par phase (bleu → violet → vert → gris)
- [ ] Boutons Doux/Box/Rapide changent le rythme

- [ ] **Step 3 : Tests Python**

```powershell
python -m pytest tests/ -q
```

Expected: 33 passed.

- [ ] **Step 4 : Commit**

```powershell
git add brain_app/activities/breath.js
git commit -m "feat: add Breathing Bubble activity with guided breathing phases"
```

---

## Task 5 : Push final

- [ ] **Step 1 : Vérification complète — naviguer entre les 3 activités**

Lancer l'app, aller dans Zen :
- [ ] Passer de Aim → Solar → Breath → Aim : chaque transition propre, pas de canvas fantôme, pas de RAF qui continue en arrière-plan
- [ ] Revenir en mode Grille → les notes sont toujours là, les blocs blocs fixes réapparaissent
- [ ] Revenir en Zen → reprend l'activité aim (par défaut)

- [ ] **Step 2 : Push**

```powershell
cd "C:\Users\yapa\second_cerveau"
git push origin master
```
