# Ambient Brain — Plan 2 : Electron UI

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Prérequis :** Plan 1 terminé (brain_server.py tourne sur port 7842).

**Goal:** Construire l'application Electron qui s'affiche en permanence sur l'écran portrait (écran 3), présente les notes en cards dark cosmos, anime avec Anime.js v4, et gère le chat RAG.

**Architecture:** Electron avec 3 fichiers process : `main.js` (process principal, gère la fenêtre), `preload.js` (pont sécurisé), `renderer.js` (logique UI + Anime.js). Vanilla HTML/CSS/JS — pas de framework. L'app pointe vers `http://127.0.0.1:7842` pour toutes les données.

**Tech Stack:** Electron (latest), Anime.js v4, Inter font (Google Fonts), Vanilla JS ES modules, HTML5/CSS3

---

## File Map

**Créés :**
- `brain_app/package.json` — config Electron + dépendances
- `brain_app/main.js` — BrowserWindow, détection écran portrait
- `brain_app/preload.js` — expose API URL au renderer
- `brain_app/index.html` — structure HTML
- `brain_app/style.css` — dark cosmos design
- `brain_app/renderer.js` — fetch data, render cards, Anime.js animations, chat

---

### Task 1 : package.json + installation Electron

**Files:**
- Create: `brain_app/package.json`

- [ ] **Step 1: Créer le dossier brain_app et package.json**

```bash
mkdir brain_app
```

Créer `brain_app/package.json` :

```json
{
  "name": "brain-app",
  "version": "1.0.0",
  "description": "Second Cerveau — Ambient Brain Display",
  "main": "main.js",
  "scripts": {
    "start": "electron ."
  },
  "dependencies": {
    "animejs": "^4.0.0"
  },
  "devDependencies": {
    "electron": "^35.0.0"
  }
}
```

- [ ] **Step 2: Installer les dépendances**

```bash
cd brain_app && npm install
```

Expected : `node_modules/` créé, `animejs` et `electron` installés.

- [ ] **Step 3: Vérifier qu'Electron est installé**

```bash
cd brain_app && npx electron --version
```

Expected : `v35.x.x` (ou supérieur)

- [ ] **Step 4: Commit**

```bash
cd ..
git add brain_app/package.json brain_app/package-lock.json
echo "brain_app/node_modules/" >> .gitignore
git add .gitignore
git commit -m "feat: brain_app Electron setup"
```

---

### Task 2 : main.js — fenêtre sur l'écran portrait

**Files:**
- Create: `brain_app/main.js`

- [ ] **Step 1: Créer brain_app/main.js**

```javascript
const { app, BrowserWindow, screen } = require('electron');
const path = require('path');

function getTargetDisplay() {
  const displays = screen.getAllDisplays();
  // Utilise l'écran 3 (index 2) si disponible, sinon le dernier écran
  return displays.length >= 3 ? displays[2] : displays[displays.length - 1];
}

function createWindow() {
  const display = getTargetDisplay();
  const { x, y, width, height } = display.bounds;

  const win = new BrowserWindow({
    x, y, width, height,
    frame: false,
    backgroundColor: '#0a0a0f',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  win.loadFile('index.html');
  win.maximize();
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
```

- [ ] **Step 2: Vérifier que la fenêtre s'ouvre (test manuel)**

```bash
cd brain_app && npx electron .
```

Expected : une fenêtre noire s'ouvre sur l'écran cible. Fermer avec Alt+F4.

- [ ] **Step 3: Commit**

```bash
cd ..
git add brain_app/main.js
git commit -m "feat: Electron BrowserWindow sur écran portrait"
```

---

### Task 3 : preload.js + index.html

**Files:**
- Create: `brain_app/preload.js`
- Create: `brain_app/index.html`

- [ ] **Step 1: Créer brain_app/preload.js**

```javascript
const { contextBridge } = require('electron');

// Expose l'URL de l'API au renderer sans exposer Node.js
contextBridge.exposeInMainWorld('BRAIN_API_URL', 'http://127.0.0.1:7842');
```

- [ ] **Step 2: Créer brain_app/index.html**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; connect-src http://127.0.0.1:7842">
  <title>Second Cerveau</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>

  <!-- Fond : blobs aurora + dot grid -->
  <div class="aurora">
    <div class="blob blob-1"></div>
    <div class="blob blob-2"></div>
  </div>
  <div class="dot-grid"></div>

  <!-- Contenu principal -->
  <div class="app" id="app">

    <header class="app-header">
      <span class="logo">🧠 Second Cerveau</span>
      <span class="status-pill" id="status-pill">chargement…</span>
    </header>

    <!-- À la une -->
    <section class="section" id="section-featured">
      <h2 class="section-label">⭐ À la une</h2>
      <div class="cards-row" id="featured-cards"></div>
    </section>

    <!-- Barre de chat -->
    <div class="chat-bar">
      <input
        type="text"
        id="chat-input"
        class="chat-input"
        placeholder="🔍 Pose une question à tes notes…"
        autocomplete="off"
      />
      <div id="chat-response" class="chat-response hidden"></div>
    </div>

    <!-- Sections par domaine -->
    <div id="domains-container"></div>

  </div>

  <script type="module" src="renderer.js"></script>
</body>
</html>
```

- [ ] **Step 3: Vérifier que l'app charge sans erreur console**

```bash
cd brain_app && npx electron .
```

Ouvrir les DevTools (Ctrl+Shift+I) → onglet Console.
Expected : pas d'erreur rouge (les erreurs de connexion API sont normales si le serveur n'est pas démarré).

- [ ] **Step 4: Commit**

```bash
cd ..
git add brain_app/preload.js brain_app/index.html
git commit -m "feat: preload.js + index.html skeleton"
```

---

### Task 4 : style.css — dark cosmos complet

**Files:**
- Create: `brain_app/style.css`

- [ ] **Step 1: Créer brain_app/style.css**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:           #0a0a0f;
  --surface:      rgba(255,255,255,0.04);
  --border:       rgba(255,255,255,0.08);
  --border-hover: rgba(255,255,255,0.16);
  --text-primary: #e8e8f0;
  --text-dim:     #808090;
  --text-muted:   #505060;

  --c-travail:    #3b82f6;
  --c-apprenti:   #8b5cf6;
  --c-projets:    #10b981;
  --c-jeux:       #f59e0b;
  --c-plantes:    #22c55e;
  --c-tdah:       #f472b6;
  --c-meta:       #64748b;
}

html, body { height: 100%; overflow: hidden; background: var(--bg); }

body {
  font-family: 'Inter', -apple-system, sans-serif;
  color: var(--text-primary);
  font-size: 13px;
}

/* ── Dot grid ── */
.dot-grid {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background-image: radial-gradient(rgba(255,255,255,0.025) 1px, transparent 1px);
  background-size: 24px 24px;
}

/* ── Aurora blobs ── */
.aurora { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.blob {
  position: absolute; border-radius: 50%;
  filter: blur(90px); opacity: 0.12;
}
.blob-1 {
  width: 45%; height: 45%;
  background: radial-gradient(circle, #7c3aed, #2563eb);
  top: 5%; left: -10%;
}
.blob-2 {
  width: 40%; height: 40%;
  background: radial-gradient(circle, #f97316, #ec4899);
  bottom: 10%; right: -8%;
}

/* ── Layout ── */
.app {
  position: relative; z-index: 1;
  height: 100vh; overflow-y: auto;
  padding: 14px 14px 20px;
  display: flex; flex-direction: column; gap: 14px;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.1) transparent;
}
.app::-webkit-scrollbar { width: 4px; }
.app::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

/* ── Header ── */
.app-header {
  display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
}
.logo { font-size: 13px; font-weight: 600; letter-spacing: -0.01em; }
.status-pill {
  font-size: 10px; color: var(--text-muted);
  background: var(--surface); border: 1px solid var(--border);
  padding: 2px 8px; border-radius: 20px;
}

/* ── Section label ── */
.section-label {
  font-size: 10px; font-weight: 500; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.1em;
  margin-bottom: 8px;
}

/* ── Featured cards (horizontal scroll) ── */
.cards-row {
  display: flex; gap: 10px;
  overflow-x: auto; padding-bottom: 4px;
  scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.1) transparent;
}
.cards-row::-webkit-scrollbar { height: 3px; }
.cards-row::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

/* ── Card ── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  min-width: 170px; max-width: 190px;
  flex-shrink: 0;
  cursor: default;
  transition: border-color 0.25s, transform 0.25s;
  opacity: 0; /* Anime.js animera l'opacité */
}
.card:hover {
  border-color: var(--border-hover);
  transform: translateY(-2px);
}
.card.highlighted { border-color: rgba(139,92,246,0.5); }

.card-dot {
  width: 6px; height: 6px; border-radius: 50%;
  margin-bottom: 8px; flex-shrink: 0;
}
.card-title   { font-size: 12px; font-weight: 500; color: var(--text-primary); margin-bottom: 5px; line-height: 1.4; }
.card-insight { font-size: 11px; color: var(--text-dim); line-height: 1.5; }
.card-meta    { font-size: 10px; color: var(--text-muted); margin-top: 8px; }

/* Domain dot colors */
.card[data-domaine="Travail"]            .card-dot { background: var(--c-travail); }
.card[data-domaine="Apprentissage"]      .card-dot { background: var(--c-apprenti); }
.card[data-domaine="Projets perso"]      .card-dot { background: var(--c-projets); }
.card[data-domaine="Jeux vidéos"]        .card-dot { background: var(--c-jeux); }
.card[data-domaine="Plantes"]            .card-dot { background: var(--c-plantes); }
.card[data-domaine="Organisation TDAH"]  .card-dot { background: var(--c-tdah); }

/* ── Domain section ── */
.domain-section { display: flex; flex-direction: column; }
.domain-header {
  display: flex; align-items: center; justify-content: space-between;
  cursor: pointer; padding: 6px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 8px;
}
.domain-header-left { display: flex; align-items: center; gap: 6px; }
.domain-chevron { font-size: 10px; color: var(--text-muted); transition: transform 0.2s; }
.domain-chevron.collapsed { transform: rotate(-90deg); }
.domain-count { font-size: 10px; color: var(--text-muted); }
.domain-cards-list { display: flex; flex-direction: column; gap: 8px; }
.domain-cards-list.hidden { display: none; }

/* Domain card (full width, single line) */
.card.card-compact {
  min-width: unset; max-width: unset;
  width: 100%;
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 12px;
}
.card.card-compact .card-dot  { margin-bottom: 0; margin-top: 3px; }
.card.card-compact .card-body { flex: 1; min-width: 0; }
.card.card-compact .card-title   { font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card.card-compact .card-insight { display: none; }
.card.card-compact .card-meta   { margin-top: 2px; }

/* ── Chat bar ── */
.chat-bar { position: sticky; top: 0; z-index: 10; }
.chat-input {
  width: 100%;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 10px 14px;
  color: var(--text-primary);
  font-family: inherit; font-size: 12px;
  outline: none; transition: border-color 0.2s;
}
.chat-input::placeholder { color: var(--text-muted); }
.chat-input:focus { border-color: rgba(255,255,255,0.22); }
.chat-response {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  margin-top: 6px;
  font-size: 12px; color: #b0b0c0;
  line-height: 1.7; white-space: pre-wrap;
}
.hidden { display: none; }
```

- [ ] **Step 2: Relancer l'app et vérifier le fond dark cosmos**

```bash
cd brain_app && npx electron .
```

Expected : fond `#0a0a0f`, dot grid subtil visible, aucun contenu (renderer.js pas encore là).

- [ ] **Step 3: Commit**

```bash
cd ..
git add brain_app/style.css
git commit -m "feat: dark cosmos CSS — fond, dots, aurora, cards"
```

---

### Task 5 : renderer.js — fetch, render, animations Anime.js

**Files:**
- Create: `brain_app/renderer.js`

- [ ] **Step 1: Créer brain_app/renderer.js**

```javascript
import { animate, stagger, utils } from './node_modules/animejs/src/index.js';

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
      opacity:  [0, 1],
      translateY: ['16px', '0px'],
      delay:    stagger(80),
      duration: 500,
      ease:     'outQuart',
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
      opacity:     [0, 1],
      translateY:  ['10px', '0px'],
      delay:       stagger(30),
      duration:    350,
      ease:        'outCubic',
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
  const p   = document.createElement('div');
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
```

- [ ] **Step 2: Démarrer le serveur API dans un terminal séparé**

```bash
python -m uvicorn brain_server:app --host 127.0.0.1 --port 7842
```

- [ ] **Step 3: Lancer l'app Electron et vérifier le rendu**

```bash
cd brain_app && npx electron .
```

Expected :
- Fond dark cosmos avec blobs aurora animés et particules
- Status pill : "0 notes · 0 synthèses" (DB vide)
- Sections vides sans erreur console
- Barre de chat fonctionnelle (réponse "Aucune note trouvée" si DB vide)

- [ ] **Step 4: Commit**

```bash
cd ..
git add brain_app/renderer.js
git commit -m "feat: renderer.js — fetch notes, cards, Anime.js, chat RAG"
```

---

### Task 6 : Raccourci démarrage Windows

**Files:**
- Modify: `brain_start.bat`

- [ ] **Step 1: Mettre à jour brain_start.bat pour inclure brain_app**

Le fichier `brain_start.bat` créé en Plan 1 inclut déjà le démarrage de l'app Electron. Vérifier que le chemin `brain_app` est correct :

```batch
@echo off
title Second Cerveau — Brain System
cd /d "%~dp0"

echo [1/3] Agent de sync...
start "Brain Agent" /MIN python brain_agent.py

echo [2/3] Serveur API (attente 10s)...
timeout /t 10 /nobreak >nul
start "Brain Server" /MIN python -m uvicorn brain_server:app --host 127.0.0.1 --port 7842 --log-level warning

echo [3/3] Interface Electron (attente 3s)...
timeout /t 3 /nobreak >nul
cd brain_app
start "Brain App" npx electron .

echo Brain System demarre !
```

- [ ] **Step 2: Ajouter brain_start.bat au dossier Startup Windows**

```powershell
$startup = [Environment]::GetFolderPath("Startup")
$src     = "C:\Users\yapa\second_cerveau\brain_start.bat"
Copy-Item $src "$startup\brain_start.bat"
Write-Host "Raccourci ajouté : $startup\brain_start.bat"
```

Expected : le fichier est copié dans le dossier Startup. L'app démarrera au prochain login.

- [ ] **Step 3: Test manuel complet**

Double-cliquer sur `brain_start.bat` depuis l'explorateur.
Expected : 3 fenêtres minimisées s'ouvrent (Agent, Server, App Electron).

- [ ] **Step 4: Commit**

```bash
git add brain_start.bat
git commit -m "feat: brain_start.bat vérifié + instructions startup Windows"
```

---

**Plan 2 terminé.** L'app Electron s'affiche sur l'écran portrait avec le design dark cosmos, les animations Anime.js et le chat RAG. Passer au Plan 3 (intégration bot_cloud.py).
