# Brain — Icône Tray Unique Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer les 3 icônes Windows par une unique icône dans le system tray — Electron orchestre les deux processus Python en arrière-plan.

**Architecture:** `main.js` spawne `brain_agent.py` et `uvicorn` comme enfants cachés (`windowsHide: true`). Un `Tray` Electron affiche le statut en temps réel via lecture stdout de l'agent et polling `/status` toutes les 30s. La fenêtre app passe en `skipTaskbar: true` et disparaît du taskbar.

**Tech Stack:** Electron 35, Node.js `child_process` + `readline` + `http` (stdlib), `sharp` (npm) pour générer les PNGs tray depuis le SVG.

---

## Task 1 : Générer les assets PNG pour le tray

**Files:**
- Create: `brain_app/assets/logo.svg`
- Create: `brain_app/assets/logo-16.png` (généré)
- Create: `brain_app/assets/logo-32.png` (généré)
- Create: `brain_app/assets/logo-syncing-16.png` (généré)
- Create: `brain_app/build-assets.js`
- Modify: `brain_app/package.json`

- [ ] **Step 1 : Créer le dossier assets et copier le SVG**

```powershell
New-Item -ItemType Directory -Path "C:\Users\yapa\second_cerveau\brain_app\assets" -Force
Copy-Item "C:\Users\yapa\second_cerveau\Idées\assets\logo.svg" "C:\Users\yapa\second_cerveau\brain_app\assets\logo.svg"
```

Vérifie que le fichier est présent :
```powershell
Get-Item "C:\Users\yapa\second_cerveau\brain_app\assets\logo.svg"
```
Expected: le fichier existe, taille ~800 octets.

- [ ] **Step 2 : Ajouter `sharp` à package.json**

Modifier `brain_app/package.json` :

```json
{
  "name": "brain-app",
  "version": "1.0.0",
  "description": "Second Cerveau — Ambient Brain Display",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build-assets": "node build-assets.js"
  },
  "dependencies": {
    "animejs": "^4.0.0",
    "sharp": "^0.34.0"
  },
  "devDependencies": {
    "electron": "^35.0.0"
  }
}
```

- [ ] **Step 3 : Créer `brain_app/build-assets.js`**

```javascript
const sharp = require('sharp');
const path = require('path');
const fs = require('fs');

const ASSETS = __dirname;
const SVG_SRC = path.join(ASSETS, 'logo.svg');

async function main() {
  const svgRaw = fs.readFileSync(SVG_SRC, 'utf8');
  // currentColor ne se résout pas sans contexte CSS — forcer blanc pour l'icône tray
  const svg = svgRaw.replace(/currentColor/g, 'white');
  const svgBuf = Buffer.from(svg);
  // Version syncing : 50% opacité via attribut SVG
  const svgSync = Buffer.from(svg.replace('<svg ', '<svg opacity="0.5" '));

  await sharp(svgBuf).resize(16, 16).png().toFile(path.join(ASSETS, 'logo-16.png'));
  console.log('✓ logo-16.png');
  await sharp(svgBuf).resize(32, 32).png().toFile(path.join(ASSETS, 'logo-32.png'));
  console.log('✓ logo-32.png');
  await sharp(svgSync).resize(16, 16).png().toFile(path.join(ASSETS, 'logo-syncing-16.png'));
  console.log('✓ logo-syncing-16.png');
}

main().catch(err => { console.error(err); process.exit(1); });
```

- [ ] **Step 4 : Installer les dépendances et générer les PNGs**

```powershell
cd "C:\Users\yapa\second_cerveau\brain_app"
npm install
node build-assets.js
```

Expected :
```
✓ logo-16.png
✓ logo-32.png
✓ logo-syncing-16.png
```

Vérifie les 3 fichiers :
```powershell
Get-ChildItem "C:\Users\yapa\second_cerveau\brain_app\assets\" | Select-Object Name, Length
```
Expected: 4 fichiers (logo.svg + 3 PNG), les PNG font entre 200 et 1000 octets chacun.

- [ ] **Step 5 : Commit**

```powershell
cd "C:\Users\yapa\second_cerveau"
git add brain_app/assets/ brain_app/build-assets.js brain_app/package.json brain_app/package-lock.json
git commit -m "feat: add tray icon assets (SVG + generated PNGs)"
```

---

## Task 2 : Ajouter les marqueurs stdout à brain_agent.py

**Files:**
- Modify: `brain_agent.py:298-421`

- [ ] **Step 1 : Ajouter `[SYNC_START]` au début de `run_agent()`**

Dans `brain_agent.py` lignes 298-304, remplacer :

```python
def run_agent(db_path: str | Path = DB_PATH, reprocess: bool = False) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY manquante dans .env")

    init_db(db_path)
    conn = get_db(db_path)
```

par :

```python
def run_agent(db_path: str | Path = DB_PATH, reprocess: bool = False) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY manquante dans .env")

    print("[SYNC_START]", flush=True)
    init_db(db_path)
    conn = get_db(db_path)
```

Seule la ligne `print("[SYNC_START]", flush=True)` est ajoutée entre l'api_key check et `init_db`.

- [ ] **Step 2 : Ajouter `[SYNC_END]` et transformer `finally` en `except/finally`**

Dans `brain_agent.py`, les deux dernières lignes du bloc `try` (lignes 418-419) sont :

```python
        log.info("Agent terminé. %d fiches traitées.", len(fiches_raw))
    finally:
        conn.close()
```

Les remplacer par :

```python
        log.info("Agent terminé. %d fiches traitées.", len(fiches_raw))
        print("[SYNC_END]", flush=True)
    except Exception:
        print("[SYNC_ERROR]", flush=True)
        raise
    finally:
        conn.close()
```

Tout le code entre le `try:` (ligne 305) et `log.info(...)` (ligne 418) reste strictement inchangé.

- [ ] **Step 3 : Vérifier manuellement que les marqueurs apparaissent**

```powershell
cd "C:\Users\yapa\second_cerveau"
python brain_agent.py 2>&1 | Select-String -Pattern "\[SYNC"
```

Expected (les 3 lignes dans l'ordre) :
```
[SYNC_START]
[SYNC_END]
```
(ou `[SYNC_ERROR]` si Dropbox est indisponible — les deux cas sont OK)

- [ ] **Step 4 : Commit**

```powershell
git add brain_agent.py
git commit -m "feat: emit SYNC_START/END/ERROR markers to stdout"
```

---

## Task 3 : Réécrire main.js — orchestrateur + tray

**Files:**
- Modify: `brain_app/main.js`

- [ ] **Step 1 : Remplacer entièrement `brain_app/main.js`**

```javascript
const { app, BrowserWindow, screen, ipcMain, shell, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const readline = require('readline');
const http = require('http');

const PROJECT_ROOT = path.join(__dirname, '..');
const ASSETS_DIR   = path.join(__dirname, 'assets');
const API_PORT     = 7842;

let win        = null;
let tray       = null;
let agentProc  = null;
let serverProc = null;
let statusCache = { last_sync: null, total_notes: 0 };
let isSyncing  = false;
let syncFailed = false;

// ─── Utilities ────────────────────────────────────────────────────────────────

function getTargetDisplay() {
  const displays = screen.getAllDisplays();
  return displays.find(d => d.bounds.height > d.bounds.width) || displays[displays.length - 1];
}

function icon(name) {
  return nativeImage.createFromPath(path.join(ASSETS_DIR, name));
}

function syncLabel() {
  if (isSyncing) return 'Synchronisation en cours...';
  if (syncFailed) return 'Dernière sync : échec';
  if (!statusCache.last_sync) return 'Serveur en démarrage...';
  const mins = Math.floor((Date.now() - new Date(statusCache.last_sync)) / 60000);
  if (mins < 1)  return 'sync à l\'instant';
  if (mins < 60) return `sync il y a ${mins} min`;
  return `sync il y a ${Math.floor(mins / 60)}h`;
}

// ─── Process management ───────────────────────────────────────────────────────

function spawnAgent() {
  if (agentProc) return; // déjà en cours
  agentProc = spawn('python', ['brain_agent.py'], {
    cwd: PROJECT_ROOT,
    windowsHide: true,
    detached: false,
    env: { ...process.env },
  });

  readline.createInterface({ input: agentProc.stdout }).on('line', (line) => {
    if (line.includes('[SYNC_START]'))      { isSyncing = true;  syncFailed = false; updateTray(); }
    else if (line.includes('[SYNC_END]'))   { isSyncing = false; pollStatus(); }
    else if (line.includes('[SYNC_ERROR]')) { isSyncing = false; syncFailed = true;  updateTray(); }
  });

  agentProc.on('exit', () => { agentProc = null; isSyncing = false; updateTray(); });
}

function spawnServer() {
  serverProc = spawn(
    'python',
    ['-m', 'uvicorn', 'brain_server:app', '--host', '127.0.0.1', '--port', String(API_PORT), '--log-level', 'warning'],
    { cwd: PROJECT_ROOT, windowsHide: true, detached: false, env: { ...process.env } }
  );
}

function restartAgent() {
  if (agentProc) { try { agentProc.kill(); } catch {} agentProc = null; }
  isSyncing  = false;
  syncFailed = false;
  spawnAgent();
  updateTray();
}

function killChildren() {
  if (agentProc)  { try { agentProc.kill();  } catch {} }
  if (serverProc) { try { serverProc.kill(); } catch {} }
}

// ─── Status polling ───────────────────────────────────────────────────────────

function pollStatus() {
  http.get(`http://127.0.0.1:${API_PORT}/status`, (res) => {
    let raw = '';
    res.on('data', c => raw += c);
    res.on('end', () => {
      try {
        const data = JSON.parse(raw);
        statusCache = { last_sync: data.last_sync ?? null, total_notes: data.total_notes || 0 };
        updateTray();
      } catch {}
    });
  }).on('error', () => {}); // serveur pas encore prêt
}

// ─── Tray ─────────────────────────────────────────────────────────────────────

function buildContextMenu() {
  return Menu.buildFromTemplate([
    { label: 'Brain System', enabled: false },
    { type: 'separator' },
    { label: win?.isVisible() ? 'Masquer l\'app' : 'Ouvrir l\'app', click: toggleWindow },
    { type: 'separator' },
    { label: syncLabel(),                          enabled: false },
    { label: `${statusCache.total_notes} notes indexées`, enabled: false },
    { type: 'separator' },
    { label: '↺ Relancer l\'agent', click: restartAgent },
    { type: 'separator' },
    { label: '✕ Quitter', click: () => { app.isQuitting = true; app.quit(); } },
  ]);
}

function updateTray() {
  if (!tray) return;
  tray.setImage(icon(isSyncing ? 'logo-syncing-16.png' : 'logo-16.png'));
  tray.setToolTip(`Brain — ${syncLabel()}`);
  tray.setContextMenu(buildContextMenu());
}

function createTray() {
  tray = new Tray(icon('logo-16.png'));
  tray.setToolTip('Brain — Démarrage...');
  tray.on('double-click', toggleWindow);
  updateTray();
}

// ─── Window ───────────────────────────────────────────────────────────────────

function toggleWindow() {
  if (!win) return;
  if (win.isVisible()) {
    win.hide();
  } else {
    const display = getTargetDisplay();
    win.setBounds(display.bounds);
    win.maximize();
    win.show();
    win.focus();
  }
  updateTray(); // rafraîchit le label Ouvrir/Masquer
}

function createWindow() {
  const { x, y, width, height } = getTargetDisplay().bounds;
  win = new BrowserWindow({
    x, y, width, height,
    frame: false,
    backgroundColor: '#0a0a0f',
    skipTaskbar: true,
    show: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });
  win.loadFile('index.html');
  win.maximize();
  win.on('close', (e) => {
    if (!app.isQuitting) { e.preventDefault(); win.hide(); updateTray(); }
  });
}

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  spawnAgent();
  setTimeout(spawnServer, 3000);

  createWindow();
  createTray();

  ipcMain.on('open-url', (_, url) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
  });

  pollStatus();
  setInterval(pollStatus, 30_000);
  setInterval(() => { if (!agentProc) spawnAgent(); }, 2 * 60 * 60 * 1000);
});

app.on('window-all-closed', () => { /* tray maintient l'app en vie */ });

app.on('will-quit', killChildren);
```

- [ ] **Step 2 : Lancer l'app et vérifier les comportements de base**

```powershell
cd "C:\Users\yapa\second_cerveau\brain_app"
npx electron .
```

Checklist manuelle :
- [ ] Aucune icône dans la barre des tâches Windows (taskbar)
- [ ] Une icône tray apparaît en bas à droite (zone de notification)
- [ ] L'app est visible sur l'écran portrait
- [ ] Clic droit sur l'icône tray → menu contextuel s'affiche avec "Brain System", statut, "Relancer l'agent", "Quitter"
- [ ] Double-clic sur l'icône tray → l'app se masque, re-double-clic → elle réapparaît
- [ ] "✕ Quitter" dans le menu → l'app se ferme complètement
- [ ] Clic sur le ✕ de la fenêtre (si accessible) → la fenêtre se masque, l'app reste en tray

- [ ] **Step 3 : Commit**

```powershell
cd "C:\Users\yapa\second_cerveau"
git add brain_app/main.js
git commit -m "feat: electron orchestrates processes and shows single tray icon"
```

---

## Task 4 : Simplifier brain_start.bat

**Files:**
- Modify: `brain_start.bat`

- [ ] **Step 1 : Remplacer `brain_start.bat`**

```bat
@echo off
title Second Cerveau — Brain System
cd /d "%~dp0brain_app"
start "" npx electron .
```

- [ ] **Step 2 : Vérifier le démarrage via le bat**

Double-cliquer sur `brain_start.bat` depuis l'explorateur Windows (ou depuis le raccourci Startup).

Checklist manuelle :
- [ ] Une seule fenêtre cmd s'ouvre brièvement puis se ferme
- [ ] L'app Electron démarre (visible sur l'écran portrait)
- [ ] L'icône tray apparaît
- [ ] Après ~5s, le tooltip tray indique "Serveur en démarrage..." puis passe au statut normal une fois le serveur prêt

- [ ] **Step 3 : Commit**

```powershell
cd "C:\Users\yapa\second_cerveau"
git add brain_start.bat
git commit -m "feat: brain_start.bat launches only electron, processes spawned internally"
```

---

## Notes pour la migration vers electron-builder (Approche C — future)

Les changements de ce plan sont déjà compatibles. Pour packager plus tard :
1. Ajouter `electron-builder` en devDependency
2. Ajouter une section `"build"` dans `package.json` avec `"icon": "assets/logo.ico"` (convertir le SVG en .ico 256px)
3. Changer les chemins de spawn : utiliser `process.execPath` et un chemin relatif au répertoire ressources packagé
4. Runner `npx electron-builder --win portable`
