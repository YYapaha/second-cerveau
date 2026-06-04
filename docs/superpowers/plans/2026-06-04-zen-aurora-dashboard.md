# Zen Aurora Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** CrÃ©er `brain_app/activities/dashboard.js` â€” un tableau de bord interactif (sliders + knobs + toggles) qui contrÃ´le en temps rÃ©el une aurora animÃ©e avec 3 blobs colorÃ©s.

**Architecture:** Module ES unique suivant le pattern `export function create(container) â†’ { start, stop }`. Canvas plein Ã©cran (sauf panel 160px bas). Panel injectÃ© en HTML inline avec styles en `style=""` attributs et CSS variables dÃ©jÃ  dÃ©finies dans le projet. Pas de fichier CSS externe.

**Tech Stack:** Vanilla JS ES modules, Canvas 2D API, `requestAnimationFrame`, `ResizeObserver`, SVG inline pour les knobs.

---

## Fichiers

| Fichier | Action |
|---|---|
| `brain_app/zen.js` | Modifier ligne 9 : `module: null` â†’ `module: () => import('./activities/dashboard.js')` |
| `brain_app/activities/dashboard.js` | CrÃ©er (nouveau module complet) |

---

## Task 1: Wire-up zen.js + squelette dashboard.js

**Files:**
- Modify: `brain_app/zen.js:9`
- Create: `brain_app/activities/dashboard.js`

- [x] **Step 1: Modifier zen.js â€” activer l'entrÃ©e sliders**

Dans [brain_app/zen.js](brain_app/zen.js), remplacer la ligne 9 :

```javascript
// Avant
{ id: 'sliders',   icon: 'ðŸŽšï¸', label: 'Tableau',   module: null },

// AprÃ¨s
{ id: 'sliders',   icon: 'ðŸŽšï¸', label: 'Tableau',   module: () => import('./activities/dashboard.js') },
```

- [x] **Step 2: CrÃ©er le squelette dashboard.js**

CrÃ©er `brain_app/activities/dashboard.js` avec ce contenu complet :

```javascript
// activities/dashboard.js â€” Tableau de bord Aurora

const PANEL_H = 160;

export function create(container) {
  const params = {
    hueShift: 0, speed: 1.0, blur: 70, intensity: 0.45,
    scale: 1.0, chaos: 0.3,
    b1: true, b2: true, b3: true, particles: false, lines: false,
  };

  container.innerHTML = `
    <canvas id="db-canvas" style="position:absolute;top:0;left:0;width:100%;height:calc(100% - ${PANEL_H}px)"></canvas>
    <div id="db-panel" style="
      position:absolute;bottom:0;left:0;right:0;height:${PANEL_H}px;
      display:flex;align-items:center;justify-content:center;gap:24px;padding:0 24px;
      background:rgba(255,255,255,0.04);border-top:1px solid rgba(255,255,255,0.085);
      backdrop-filter:blur(18px);
    ">
      <div id="db-sliders" style="display:flex;gap:12px;align-items:flex-end;height:120px;"></div>
      <div style="width:1px;height:80px;background:rgba(255,255,255,0.085);"></div>
      <div id="db-knobs" style="display:flex;gap:20px;align-items:center;"></div>
      <div style="width:1px;height:80px;background:rgba(255,255,255,0.085);"></div>
      <div id="db-toggles" style="display:flex;flex-direction:column;gap:8px;"></div>
    </div>
  `;

  const canvas = container.querySelector('#db-canvas');
  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight - PANEL_H;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);

  let rafId = null;

  function draw(now) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    rafId = requestAnimationFrame(draw);
  }

  function start() {
    resize();
    rafId = requestAnimationFrame(draw);
  }

  function stop() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    ro.disconnect();
    container.innerHTML = '';
  }

  return { start, stop };
}
```

- [x] **Step 3: VÃ©rifier dans le navigateur**

Ouvrir l'app, cliquer l'onglet **ðŸŽšï¸ Tableau**. Attendu :
- Canvas noir qui remplit la zone au-dessus du panel
- Panel translucide visible en bas (~160px) avec sÃ©parateurs verticaux
- Pas d'erreur console

- [x] **Step 4: Commit**

```bash
git add brain_app/zen.js brain_app/activities/dashboard.js
git commit -m "feat(zen): wire dashboard activity skeleton"
```

---

## Task 2: Aurora â€” 3 blobs animÃ©s

**Files:**
- Modify: `brain_app/activities/dashboard.js`

- [x] **Step 1: Ajouter les blobs et la boucle de rendu**

AprÃ¨s la dÃ©claration de `params`, ajouter les blobs et mettre Ã  jour la fonction `draw` :

```javascript
// AprÃ¨s const params = { ... };

const blobs = [
  { rx: 220, ry: 160, color: 'oklch(0.7 0.16 30)',   phaseX: 0,   phaseY: 0,   speedX: 0.4,  speedY: 0.3,  driftX: 200, driftY: 120 },
  { rx: 200, ry: 180, color: 'oklch(0.65 0.16 290)', phaseX: 2.1, phaseY: 1.4, speedX: 0.3,  speedY: 0.5,  driftX: 180, driftY: 140 },
  { rx: 240, ry: 150, color: 'oklch(0.66 0.15 245)', phaseX: 4.2, phaseY: 3.1, speedX: 0.5,  speedY: 0.25, driftX: 220, driftY: 100 },
];
const BLOB_KEYS = ['b1', 'b2', 'b3'];
```

Remplacer la fonction `draw` par :

```javascript
function draw(now) {
  const t = now * 0.001;
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  blobs.forEach((b, i) => {
    if (!params[BLOB_KEYS[i]]) return;
    const noise = (Math.random() - 0.5) * params.chaos * 40;
    const cx = W * 0.5 + Math.sin(t * b.speedX * params.speed + b.phaseX) * b.driftX + noise;
    const cy = H * 0.5 + Math.sin(t * b.speedY * params.speed + b.phaseY) * b.driftY + noise;
    const s = params.scale;

    ctx.filter = `blur(${params.blur}px) hue-rotate(${params.hueShift}deg)`;
    ctx.globalAlpha = params.intensity;

    const R = Math.max(b.rx, b.ry) * s;
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
    grad.addColorStop(0, b.color);
    grad.addColorStop(1, 'rgba(0,0,0,0)');

    ctx.beginPath();
    ctx.ellipse(cx, cy, b.rx * s, b.ry * s, 0, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();
  });

  ctx.filter = 'none';
  ctx.globalAlpha = 1;

  rafId = requestAnimationFrame(draw);
}
```

- [x] **Step 2: VÃ©rifier dans le navigateur**

Onglet **ðŸŽšï¸ Tableau**. Attendu :
- 3 blobs colorÃ©s (orange, violet, bleu) qui dÃ©rivent lentement
- L'aurora est floue et translucide, blobs qui se superposent
- `ctx.filter = 'none'` remet le filtre Ã  zÃ©ro (visible uniquement si on ajoute des particules aprÃ¨s)

- [x] **Step 3: Commit**

```bash
git add brain_app/activities/dashboard.js
git commit -m "feat(dashboard): aurora blobs animation"
```

---

## Task 3: Particules & lignes

**Files:**
- Modify: `brain_app/activities/dashboard.js`

- [x] **Step 1: Ajouter l'Ã©tat particules et les fonctions de rendu**

AprÃ¨s la dÃ©claration de `BLOB_KEYS`, ajouter :

```javascript
let pts = [];

function initParticles(W, H) {
  pts = Array.from({ length: 30 }, () => ({
    x: Math.random() * W,  y: Math.random() * H,
    vx: (Math.random() - 0.5) * 0.8, vy: (Math.random() - 0.5) * 0.8,
    r: 2 + Math.random() * 2,
  }));
}

function drawParticles() {
  const W = canvas.width, H = canvas.height;
  pts.forEach(p => {
    p.x += p.vx; p.y += p.vy;
    if (p.x < 0 || p.x > W) p.vx *= -1;
    if (p.y < 0 || p.y > H) p.vy *= -1;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.fill();
  });
  if (params.lines) {
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 80) {
          ctx.beginPath();
          ctx.strokeStyle = `rgba(255,255,255,${(1 - dist / 80).toFixed(3)})`;
          ctx.lineWidth = 0.5;
          ctx.moveTo(pts[i].x, pts[i].y);
          ctx.lineTo(pts[j].x, pts[j].y);
          ctx.stroke();
        }
      }
    }
  }
}
```

- [x] **Step 2: Brancher drawParticles dans la boucle draw**

Dans `draw()`, aprÃ¨s `ctx.globalAlpha = 1;`, ajouter :

```javascript
  if (params.particles) drawParticles();
```

- [x] **Step 3: Mettre Ã  jour resize pour rÃ©initialiser les particules**

Dans `resize()`, aprÃ¨s `canvas.height = ...`, ajouter :

```javascript
  if (params.particles && pts.length) initParticles(canvas.width, canvas.height);
```

- [x] **Step 4: VÃ©rifier dans le navigateur**

Dans la console du navigateur, taper :
```javascript
// (on peut pas accÃ©der Ã  params directement â€” vÃ©rification rapide)
// Le toggle sera cÃ¢blÃ© en Task 7, pour l'instant tester via la console
// Trouver l'activitÃ© courante : window._dbParams si on l'expose, sinon skip
```

Alternative : continuer vers Task 4 + 7 (toggles) pour tester les particules via le bouton âˆ´.

- [x] **Step 5: Commit**

```bash
git add brain_app/activities/dashboard.js
git commit -m "feat(dashboard): particles and lines overlay"
```

---

## Task 4: Sliders verticaux (4)

**Files:**
- Modify: `brain_app/activities/dashboard.js`

- [x] **Step 1: DÃ©finir la configuration des sliders**

Avant `export function create(...)`, ajouter en tÃªte de module (aprÃ¨s `const PANEL_H = 160;`) :

```javascript
const SLIDER_CONFIGS = [
  { param: 'hueShift',  label: 'HUE',      color: 'oklch(0.72 0.15 25)',  min: 0,   max: 360 },
  { param: 'speed',     label: 'VITESSE',   color: 'oklch(0.72 0.13 255)', min: 0.1, max: 3.0 },
  { param: 'blur',      label: 'BLUR',      color: 'oklch(0.65 0.16 290)', min: 20,  max: 120 },
  { param: 'intensity', label: 'INTENSITÃ‰', color: 'oklch(0.78 0.14 150)', min: 0.1, max: 1.0 },
];
```

- [x] **Step 2: Ajouter la fonction buildSliders**

Dans `create()`, aprÃ¨s les lignes `querySelector` (aprÃ¨s `const togglesEl = ...`), ajouter :

```javascript
  // --- Sliders ---
  SLIDER_CONFIGS.forEach(({ param, label, color, min, max }) => {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:6px;width:28px;height:100%;';

    const track = document.createElement('div');
    track.style.cssText = [
      'flex:1;width:6px;position:relative;',
      'background:rgba(255,255,255,0.08);border-radius:3px;',
      'border:1px solid rgba(255,255,255,0.085);cursor:ns-resize;',
    ].join('');

    const fill = document.createElement('div');
    fill.style.cssText = [
      'position:absolute;bottom:0;left:0;right:0;',
      `background:${color};border-radius:3px;pointer-events:none;`,
    ].join('');

    const thumb = document.createElement('div');
    thumb.style.cssText = [
      'position:absolute;left:50%;transform:translateX(-50%);',
      'width:12px;height:4px;background:white;border-radius:2px;pointer-events:none;',
    ].join('');

    track.appendChild(fill);
    track.appendChild(thumb);

    const lbl = document.createElement('span');
    lbl.textContent = label;
    lbl.style.cssText = [
      'font-size:8px;letter-spacing:0.08em;color:rgba(255,255,255,0.45);',
      "font-family:var(--font-mono,'JetBrains Mono',monospace);",
      'writing-mode:vertical-rl;transform:rotate(180deg);user-select:none;',
    ].join('');

    wrap.appendChild(track);
    wrap.appendChild(lbl);
    slidersEl.appendChild(wrap);

    function updateSlider() {
      const t = (params[param] - min) / (max - min);
      fill.style.height  = `${t * 100}%`;
      thumb.style.bottom = `calc(${t * 100}% - 2px)`;
    }

    track.addEventListener('mousedown', e => {
      e.preventDefault();
      function onMove(ev) {
        const rect = track.getBoundingClientRect();
        let t = 1 - (ev.clientY - rect.top) / rect.height;
        t = Math.max(0, Math.min(1, t));
        params[param] = min + t * (max - min);
        updateSlider();
      }
      onMove(e);
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', () => document.removeEventListener('mousemove', onMove), { once: true });
    });

    updateSlider();
  });
```

Note : `slidersEl` doit Ãªtre dÃ©clarÃ© aprÃ¨s `querySelector`. VÃ©rifier que ces lignes sont bien prÃ©sentes :
```javascript
const slidersEl = container.querySelector('#db-sliders');
const knobsEl   = container.querySelector('#db-knobs');
const togglesEl = container.querySelector('#db-toggles');
```

- [x] **Step 3: VÃ©rifier dans le navigateur**

Onglet **ðŸŽšï¸ Tableau**. Attendu :
- 4 sliders verticaux colorÃ©s dans le panel gauche
- Labels HUE, VITESSE, BLUR, INTENSITÃ‰ visibles en bas (mode vertical)
- Glisser HUE â†’ aurora change de teinte en temps rÃ©el
- Glisser VITESSE â†’ blobs s'accÃ©lÃ¨rent / ralentissent
- Glisser BLUR â†’ nettetÃ© des blobs varie
- Glisser INTENSITÃ‰ â†’ opacitÃ© des blobs varie

- [x] **Step 4: Commit**

```bash
git add brain_app/activities/dashboard.js
git commit -m "feat(dashboard): vertical sliders with live param binding"
```

---

## Task 5: Knobs rotatifs SVG (2)

**Files:**
- Modify: `brain_app/activities/dashboard.js`

- [x] **Step 1: DÃ©finir la configuration des knobs**

AprÃ¨s `SLIDER_CONFIGS`, ajouter en tÃªte de module :

```javascript
const KNOB_CONFIGS = [
  { param: 'scale', label: 'TAILLE', min: 0.5, max: 2.0 },
  { param: 'chaos', label: 'CHAOS',  min: 0,   max: 1   },
];
```

- [x] **Step 2: Ajouter les constantes SVG et la fonction buildKnobs**

Dans `create()`, aprÃ¨s le bloc `// --- Sliders ---`, ajouter :

```javascript
  // --- Knobs ---
  const KS = 52;   // taille SVG en px
  const KC = KS / 2;
  const KR = 17;   // rayon de l'arc

  function polarPt(angleDeg) {
    const rad = angleDeg * Math.PI / 180;
    return [KC + KR * Math.cos(rad), KC + KR * Math.sin(rad)];
  }

  function arcD(startDeg, endDeg) {
    const [sx, sy] = polarPt(startDeg);
    const [ex, ey] = polarPt(endDeg);
    const span = endDeg - startDeg;
    const large = span > 180 ? 1 : 0;
    return `M ${sx.toFixed(2)} ${sy.toFixed(2)} A ${KR} ${KR} 0 ${large} 1 ${ex.toFixed(2)} ${ey.toFixed(2)}`;
  }

  const NS = 'http://www.w3.org/2000/svg';

  KNOB_CONFIGS.forEach(({ param, label, min, max }) => {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:4px;cursor:grab;user-select:none;';

    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', KS);
    svg.setAttribute('height', KS);
    svg.setAttribute('viewBox', `0 0 ${KS} ${KS}`);

    // Arc fond
    const bgArc = document.createElementNS(NS, 'path');
    bgArc.setAttribute('d', arcD(-135, 135));
    bgArc.setAttribute('fill', 'none');
    bgArc.setAttribute('stroke', 'rgba(255,255,255,0.12)');
    bgArc.setAttribute('stroke-width', '3');
    bgArc.setAttribute('stroke-linecap', 'round');

    // Arc progression
    const fgArc = document.createElementNS(NS, 'path');
    fgArc.setAttribute('fill', 'none');
    fgArc.setAttribute('stroke', 'rgba(255,255,255,0.65)');
    fgArc.setAttribute('stroke-width', '3');
    fgArc.setAttribute('stroke-linecap', 'round');

    // Point indicateur
    const dot = document.createElementNS(NS, 'circle');
    dot.setAttribute('r', '3');
    dot.setAttribute('fill', 'white');

    svg.append(bgArc, fgArc, dot);

    const lbl = document.createElement('span');
    lbl.textContent = label;
    lbl.style.cssText = [
      'font-size:8px;letter-spacing:0.08em;color:rgba(255,255,255,0.45);',
      "font-family:var(--font-mono,'JetBrains Mono',monospace);user-select:none;",
    ].join('');

    wrap.append(svg, lbl);
    knobsEl.appendChild(wrap);

    function updateKnob() {
      const t = (params[param] - min) / (max - min);
      const angle = -135 + t * 270;
      const [dx, dy] = polarPt(angle);
      dot.setAttribute('cx', dx.toFixed(2));
      dot.setAttribute('cy', dy.toFixed(2));
      const span = angle - (-135);
      fgArc.setAttribute('d', span > 0.5 ? arcD(-135, angle) : `M ${KC} ${KC}`);
    }

    svg.addEventListener('mousedown', e => {
      e.preventDefault();
      const rect = svg.getBoundingClientRect();
      const kx = rect.left + rect.width / 2;
      const ky = rect.top + rect.height / 2;

      function onMove(ev) {
        const dx = ev.clientX - kx, dy = ev.clientY - ky;
        let angle = Math.atan2(dy, dx) * (180 / Math.PI);
        angle = Math.max(-135, Math.min(135, angle));
        const t = (angle + 135) / 270;
        params[param] = min + t * (max - min);
        updateKnob();
      }

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', () => document.removeEventListener('mousemove', onMove), { once: true });
    });

    updateKnob();
  });
```

- [x] **Step 3: VÃ©rifier dans le navigateur**

Onglet **ðŸŽšï¸ Tableau**. Attendu :
- 2 knobs SVG circulaires avec arc fond + arc progression + point blanc
- Labels TAILLE et CHAOS sous chaque knob
- Drag vers la droite â†’ arc progresse, blobs grandissent (TAILLE) ou deviennent plus chaotiques (CHAOS)
- L'arc progresse de -135Â° (gauche) jusqu'Ã  +135Â° (droite) en passant par 0Â° (haut-droite)

- [x] **Step 4: Commit**

```bash
git add brain_app/activities/dashboard.js
git commit -m "feat(dashboard): SVG rotary knobs for scale and chaos"
```

---

## Task 6: Toggles pill (5)

**Files:**
- Modify: `brain_app/activities/dashboard.js`

- [x] **Step 1: Ajouter le bloc toggles**

Dans `create()`, aprÃ¨s le bloc `// --- Knobs ---`, ajouter :

```javascript
  // --- Toggles ---
  const toggleRows = [
    [
      { param: 'b1', label: 'B1' },
      { param: 'b2', label: 'B2' },
      { param: 'b3', label: 'B3' },
    ],
    [
      { param: 'particles', label: 'âˆ´' },
      { param: 'lines',     label: 'â€”' },
    ],
  ];

  toggleRows.forEach(row => {
    const rowEl = document.createElement('div');
    rowEl.style.cssText = 'display:flex;gap:6px;';
    row.forEach(({ param, label }) => {
      const btn = document.createElement('button');
      btn.textContent = label;
      const activeStyle = 'background:rgba(255,255,255,0.15);color:rgba(255,255,255,0.9);';
      const inactiveStyle = 'background:transparent;color:rgba(255,255,255,0.35);';
      btn.style.cssText = [
        'padding:4px 10px;border-radius:999px;',
        'border:1px solid rgba(255,255,255,0.085);',
        params[param] ? activeStyle : inactiveStyle,
        "font-family:var(--font-mono,'JetBrains Mono',monospace);font-size:11px;",
        'cursor:pointer;transition:background 0.15s,color 0.15s;user-select:none;',
      ].join('');

      btn.addEventListener('click', () => {
        params[param] = !params[param];
        btn.style.background = params[param] ? 'rgba(255,255,255,0.15)' : 'transparent';
        btn.style.color = `rgba(255,255,255,${params[param] ? '0.9' : '0.35'})`;
        if (param === 'particles' && params.particles && !pts.length) {
          initParticles(canvas.width, canvas.height);
        }
      });

      rowEl.appendChild(btn);
    });
    togglesEl.appendChild(rowEl);
  });
```

- [x] **Step 2: VÃ©rifier dans le navigateur**

Onglet **ðŸŽšï¸ Tableau**. Attendu :
- Ligne 1 : boutons pill **B1**, **B2**, **B3** â€” initialement actifs (fond translucide blanc)
- Ligne 2 : boutons **âˆ´** et **â€”** â€” initialement inactifs
- Cliquer B1 â†’ blob orange disparaÃ®t
- Cliquer B2 â†’ blob violet disparaÃ®t
- Cliquer B3 â†’ blob bleu disparaÃ®t
- Cliquer âˆ´ â†’ 30 particules blanches apparaissent sur l'aurora
- Cliquer â€” (avec âˆ´ actif) â†’ lignes entre particules proches apparaissent
- Cliquer â€” sans âˆ´ actif â†’ rien de visible (lignes mais pas de particules)
- Re-cliquer un bouton actif â†’ revient Ã  l'Ã©tat inactif

- [x] **Step 3: Commit**

```bash
git add brain_app/activities/dashboard.js
git commit -m "feat(dashboard): blob + particles + lines toggles"
```

---

## Task 7: Test complet & polish

**Files:**
- Modify: `brain_app/activities/dashboard.js` (si corrections nÃ©cessaires)

- [x] **Step 1: Parcours complet du golden path**

Ouvrir l'app, aller sur **ðŸŽšï¸ Tableau**, tester dans l'ordre :

1. Drag HUE de 0 â†’ 360 : aurora change de couleur graduellement
2. Drag VITESSE min â†’ max : blobs ralentissent jusqu'Ã  l'arrÃªt puis s'accÃ©lÃ¨rent
3. Drag BLUR min â†’ max : blobs passent de nets Ã  trÃ¨s flous
4. Drag INTENSITÃ‰ min â†’ max : opacitÃ© de quasi-transparent Ã  plein
5. Drag TAILLE (knob) max â†’ blobs doublent de taille
6. Drag CHAOS (knob) max â†’ blobs tremblent de maniÃ¨re alÃ©atoire
7. Toggle B1/B2/B3 on/off : chaque blob apparaÃ®t/disparaÃ®t
8. Toggle âˆ´ : particules apparaissent
9. Toggle â€” (avec âˆ´ actif) : lignes apparaissent entre particules proches
10. Changer d'onglet (ex: Aim) puis revenir sur Tableau : aurora repart proprement

- [x] **Step 2: VÃ©rifier le cycle stop/start (pas de fuite mÃ©moire RAF)**

Cliquer Aim â†’ Tableau â†’ Aim â†’ Tableau 3 fois. Ouvrir DevTools â†’ Performance. Attendu : pas d'empilement de `requestAnimationFrame` calls entre les cycles.

- [x] **Step 3: Corriger tout bug identifiÃ© pendant les tests**

Si un slider ne rÃ©pond pas : vÃ©rifier `rect.getBoundingClientRect()` dans `onMove`, et que `e.preventDefault()` est bien appelÃ©.

Si le knob saute de position : l'atan2 cÃ´tÃ© mort (-135Â° / +135Â°) peut poser problÃ¨me si le curseur traverse le bas du cercle â€” comportement acceptable selon la spec, aucune correction nÃ©cessaire.

Si les particules ne s'initialisent pas Ã  la bonne taille aprÃ¨s resize : vÃ©rifier que `initParticles(canvas.width, canvas.height)` est appelÃ© Ã  la fois dans le toggle et dans `resize()`.

- [x] **Step 4: Commit final**

```bash
git add brain_app/activities/dashboard.js
git commit -m "feat(zen): complete aurora dashboard â€” sliders, knobs, toggles"
```

---

## Self-Review â€” Couverture spec

| Exigence spec | Task couverte |
|---|---|
| Canvas plein Ã©cran hors panel | Task 1 â€” `height: calc(100% - 160px)` |
| 3 blobs avec couleurs oklch | Task 2 â€” blobs array |
| `ctx.filter = blur + hue-rotate` | Task 2 â€” dans `draw()` |
| `ctx.filter = 'none'` aprÃ¨s blobs | Task 2 â€” reset explicite |
| params : hueShift, speed, blur, intensity, scale, chaos | Task 2 + 4 + 5 |
| params : b1, b2, b3, particles, lines | Task 3 + 6 |
| 30 particules avec rebond | Task 3 |
| Lignes opacitÃ© distance / 80 | Task 3 |
| 4 sliders verticaux avec couleurs track | Task 4 |
| Interaction slider : mousedown â†’ mousemove document | Task 4 |
| 2 knobs SVG avec arc progression | Task 5 |
| Interaction knob : atan2, -135Â°..+135Â° | Task 5 |
| 5 toggles pill avec transition couleur | Task 6 |
| Labels B1 Â· B2 Â· B3 Â· âˆ´ Â· â€” | Task 6 |
| CSS inline dans le module | Toutes tasks â€” `style=""` uniquement |
| CSS vars `var(--font-mono)` etc. | Tasks 4, 5, 6 |
| Pattern `create(container) â†’ { start, stop }` | Task 1 |
| zen.js : dÃ©commenter entrÃ©e sliders | Task 1 |

