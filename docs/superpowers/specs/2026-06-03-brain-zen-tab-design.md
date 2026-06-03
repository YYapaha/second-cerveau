# Brain — Onglet Zen (Batch 1)
**Date :** 2026-06-03
**Statut :** Approuvé

---

## Objectif

Ajouter un onglet "Zen" à l'app Electron Second Cerveau pour offrir un espace de détente interactive adapté au profil TDAH : activités fidget satisfaisantes avec animations fluides. Batch 1 = shell + 3 activités (Aim Trainer, Système Solaire, Bulle Respiratoire).

---

## Architecture

```
brain_app/
  zen.js                    ← shell : navigation, loadActivity(), bottom bar
  zen.css                   ← styles zen-view, bottom bar, HUD commun
  activities/
    aim.js                  ← aim trainer (canvas2D, modes, HUD, son)
    solar.js                ← système solaire (physique, drag, traînées)
    breath.js               ← bulle respiratoire (phases, animation)
  index.html                ← +#zen-view, +btn-zen dans modeswitch
  style.css                 ← import zen.css ou ajout inline
  renderer.js               ← mode 'zen', renderTopbar(), initZen()
```

---

## Shell (`zen.js`)

### Structure HTML dans `.panel`

Insérer juste avant `#blocs-section` :
```html
<div id="zen-view" class="hidden">
  <div id="zen-canvas-area"></div>
  <div id="zen-bottom-bar"></div>
</div>
```

### `initZen()`

Appelé une seule fois depuis l'IIFE de `renderer.js` après `initBlocsResize()`.

Construit le bottom bar et charge l'activité par défaut :
```javascript
const ACTIVITIES = [
  { id: 'aim',    icon: '🎯', label: 'Aim',     module: () => import('./activities/aim.js')    },
  { id: 'solar',  icon: '🪐', label: 'Solaire',  module: () => import('./activities/solar.js')  },
  { id: 'breath', icon: '🫁', label: 'Respir.',  module: () => import('./activities/breath.js') },
  { id: 'particles', icon: '✨', label: 'Particles', module: null },
  { id: 'bubbles',   icon: '🫧', label: 'Bulles',    module: null },
  { id: 'sliders',   icon: '🎚️', label: 'Tableau',   module: null },
  { id: 'fluid',     icon: '🌊', label: 'Fluide',    module: null },
  { id: 'ripple',    icon: '💧', label: 'Ondules',   module: null },
  { id: 'kaleido',   icon: '🔮', label: 'Kaleido',   module: null },
];
```

Le bottom bar génère un bouton par activité. Les activités sans `module` sont grises + `pointer-events:none`.

### `loadActivity(id)`

```javascript
let currentActivity = null;

async function loadActivity(id) {
  // Arrêter l'activité courante
  if (currentActivity?.stop) currentActivity.stop();
  currentActivity = null;

  // Vider le canvas area
  const area = document.getElementById('zen-canvas-area');
  area.innerHTML = '';

  // Mettre à jour l'état actif du bottom bar
  document.querySelectorAll('.zen-tab').forEach(b => b.classList.toggle('active', b.dataset.id === id));

  // Charger et démarrer la nouvelle activité
  const entry = ACTIVITIES.find(a => a.id === id);
  if (!entry?.module) return;
  const mod = await entry.module();
  currentActivity = mod.create(area);
  currentActivity.start();
}
```

### Intégration `renderer.js`

- Ajouter `'zen'` comme valeur possible de `state.mode`
- Dans `renderTopbar()` : ajouter `btn-zen` dans le modeswitch, même pattern que grille/constellation
- Dans `render()` : si `state.mode === 'zen'` → show `#zen-view`, hide `#grille-view` + `#constel-view` + `#blocs-section`. Sinon → hide `#zen-view` + stop activité courante via `currentActivity?.stop()`

---

## CSS (`zen.css`)

```css
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
}
#zen-bottom-bar::-webkit-scrollbar { display: none; }

.zen-tab {
  all: unset;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 6px 8px;
  border-radius: 10px;
  cursor: pointer;
  min-width: 44px;
  transition: background .15s var(--ease);
  opacity: 0.45;
}
.zen-tab.available { opacity: 1; }
.zen-tab.available:hover { background: var(--glass); }
.zen-tab.active { background: var(--glass); opacity: 1; }

.zen-tab-icon  { font-size: 18px; line-height: 1; }
.zen-tab-label {
  font-family: var(--font-mono);
  font-size: 7.5px;
  letter-spacing: 0.05em;
  color: var(--ink-4);
  text-transform: uppercase;
}
.zen-tab.active .zen-tab-label { color: oklch(0.85 0.11 90); }
```

---

## Activité 1 — Aim Trainer (`activities/aim.js`)

### Interface exportée

```javascript
export function create(container) {
  // ... initialisation ...
  return { start, stop };
}
```

### Canvas & HUD

Le `create()` injecte dans `container` :
```html
<canvas id="aim-canvas"></canvas>
<div id="aim-hud">
  <div class="hud-block"><span class="hud-label">SCORE</span><span class="hud-val" id="aim-score">0</span></div>
  <div class="hud-block"><span class="hud-label">STREAK</span><span class="hud-val" id="aim-streak">0</span></div>
  <div class="hud-block"><span class="hud-label">PRÉCISION</span><span class="hud-val" id="aim-acc">—</span></div>
  <div id="aim-timer-wrap"><svg id="aim-timer-svg" ...></svg><span id="aim-timer-val">—</span></div>
</div>
<div id="aim-mode-bar">
  <button id="btn-timed">⏱ 30 secondes</button>
  <button id="btn-endless">∞ Endless</button>
</div>
<div id="aim-results" class="hidden">...</div>
```

### Logique cibles

- Cible = cercle rayon 28px (canvas) ou 24px sur mobile
- Position aléatoire avec marge de 60px par rapport aux bords
- Durée de vie : 2500ms → la cible rapetisse progressivement sur les 800 dernières ms (signal visuel)
- Hit test : distance curseur–centre < rayon au `click` → `onHit()`, sinon sur `click` hors cible → `onMiss()`
- Apparition : `scale(0→1)` en 200ms avec `requestAnimationFrame`
- Disparition : particules (8 points explosant radiallement) + `scale(1→0)` 150ms

### Son (Web Audio API)

```javascript
function playPop(ctx) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain); gain.connect(ctx.destination);
  osc.frequency.setValueAtTime(880, ctx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(220, ctx.currentTime + 0.08);
  gain.gain.setValueAtTime(0.15, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1);
  osc.start(); osc.stop(ctx.currentTime + 0.1);
}
```

### Modes

**30s** : countdown visible dans le timer SVG circulaire. À 0 : afficher `#aim-results` (score, meilleur streak, précision, bouton "Rejouer").

**Endless** : pas de timer, stats s'accumulent, bouton "Reset" dans le HUD.

### Scores

- Hit : +10 pts × multiplier de streak (×1 jusqu'à ×3 à partir de 5 consécutifs)
- Miss : streak reset à 0
- Précision = hits / (hits + misses) × 100

---

## Activité 2 — Système Solaire (`activities/solar.js`)

### Interface

```javascript
export function create(container) { return { start, stop }; }
```

### Physique (Euler simplifié)

Chaque planète :
```javascript
{ x, y, vx, vy, mass, radius, color, trail: [] }
```

Chaque frame :
```javascript
const dx = sun.x - p.x, dy = sun.y - p.y;
const dist = Math.hypot(dx, dy);
const force = G * SUN_MASS * p.mass / (dist * dist);
const ax = force * dx / dist / p.mass;
const ay = force * dy / dist / p.mass;
p.vx += ax * dt; p.vy += ay * dt;
p.x  += p.vx * dt; p.y  += p.vy * dt;
p.trail.push({ x: p.x, y: p.y });
if (p.trail.length > 80) p.trail.shift();
```

### Drag & throw

- `mousedown` sur planète (distance < rayon+8) → `dragging = planet`, `lastMouse = [x,y,t]`
- `mousemove` → `planet.x = mouse.x, planet.y = mouse.y`, mémorise 3 derniers points avec timestamps
- `mouseup` → calcule vélocité = (dernière pos - avant-dernière pos) / dt × 0.6

### Planètes initiales

3 planètes avec orbites circulaires stables au démarrage :
- `vx = 0, vy = sqrt(G * SUN_MASS / r)` (vitesse orbitale circulaire)

### Escape & reset

Si `dist(planet, sun) > 1.5 * Math.max(canvas.width, canvas.height)` → reset cette planète à orbite aléatoire.

### Overlay gravité

3 boutons radio overlay en bas à gauche : `G_VALUES = { Faible: 80, Normale: 200, Forte: 500 }`.

---

## Activité 3 — Bulle Respiratoire (`activities/breath.js`)

### Interface

```javascript
export function create(container) { return { start, stop }; }
```

### Phases

```javascript
const RHYTHMS = {
  doux:   [4000, 4000, 4000, 2000],  // inspire, retiens, expire, retiens
  box:    [4000, 4000, 4000, 4000],
  rapide: [3000, 3000, 3000, 2000],
};
const PHASES = ['Inspire', 'Retiens', 'Expire', 'Retiens'];
const COLORS = ['oklch(0.72 0.13 255)', 'oklch(0.65 0.16 290)', 'oklch(0.72 0.14 150)', 'oklch(0.6 0.06 250)'];
```

Transitions via `requestAnimationFrame` + timestamps pour interpoler la taille du blob (linéaire sur la durée de chaque phase).

### Blob

Super-ellipse déformée via `n` points sur un cercle, chaque point animé indépendamment avec du bruit additif (`Math.sin(t * freq + offset)`) pour un aspect organique. Dessiné avec `ctx.bezierCurveTo`.

### Arc de progression

SVG ou canvas arc autour du blob se remplissant au fil de la phase courante.

### Selector rythme

3 boutons en bas du canvas : Doux / Box / Rapide.

---

## Fichiers modifiés/créés

| Fichier | Changement |
|---|---|
| `brain_app/index.html` | `#zen-view`, `btn-zen` dans modeswitch |
| `brain_app/zen.css` | Styles complets zen-view, bottom bar, HUD |
| `brain_app/zen.js` | Shell, navigation, `initZen()`, `loadActivity()` |
| `brain_app/activities/aim.js` | Aim trainer complet |
| `brain_app/activities/solar.js` | Système solaire |
| `brain_app/activities/breath.js` | Bulle respiratoire |
| `brain_app/renderer.js` | Mode 'zen', `renderTopbar()` étendu, appel `initZen()` |

---

## Hors scope (batch 2+)

Particules magnétiques, Bubble Wrap, Tableau de bord, Fluide, Ondulations, Kaleidoscope.
