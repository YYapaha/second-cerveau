const { app, BrowserWindow, screen, ipcMain, shell, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');
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

let IMG_IDLE;
let IMG_SYNCING;

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
  if (agentProc) return; // already running
  agentProc = spawn('python', ['brain_agent.py'], {
    cwd: PROJECT_ROOT,
    windowsHide: true,
    detached: false,
    env: { ...process.env },
    stdio: ['ignore', 'pipe', 'ignore'],
    shell: true, // required for Microsoft Store Python (app execution aliases)
  });

  const thisProc = agentProc; // capture reference

  readline.createInterface({ input: thisProc.stdout }).on('line', (line) => {
    if (line.includes('[SYNC_START]'))      { isSyncing = true;  syncFailed = false; updateTray(); }
    else if (line.includes('[SYNC_END]'))   { isSyncing = false; pollStatus(); }
    else if (line.includes('[SYNC_ERROR]')) { isSyncing = false; syncFailed = true;  updateTray(); }
  });

  thisProc.on('exit', () => { // only null out if still current proc
    if (agentProc === thisProc) { agentProc = null; isSyncing = false; updateTray(); }
  });
}

function killPort(port) {
  try {
    const out = execSync(`netstat -ano | findstr :${port} | findstr LISTENING`, { encoding: 'utf8', windowsHide: true });
    for (const line of out.trim().split('\n')) {
      const pid = line.trim().split(/\s+/).at(-1);
      if (pid && pid !== '0') execSync(`taskkill /F /PID ${pid}`, { windowsHide: true });
    }
  } catch {}
}

function spawnServer() {
  killPort(API_PORT); // tue tout processus encore en vie sur le port (zombie de session précédente)
  setTimeout(() => {
    serverProc = spawn(
      'python',
      ['-m', 'uvicorn', 'brain_server:app', '--host', '127.0.0.1', '--port', String(API_PORT), '--log-level', 'warning'],
      { cwd: PROJECT_ROOT, windowsHide: true, detached: false, env: { ...process.env }, stdio: 'ignore', shell: true }
    );
  }, 400); // laisse le port se libérer avant de respawner
}

function restartAgent() {
  isSyncing  = false;
  syncFailed = false;
  if (agentProc) {
    agentProc.once('exit', () => { agentProc = null; spawnAgent(); updateTray(); });
    try { agentProc.kill(); } catch {}
  } else {
    spawnAgent();
    updateTray();
  }
}

function killChildren() {
  // shell:true means the direct child is cmd.exe — use taskkill to terminate the full tree
  for (const proc of [agentProc, serverProc]) {
    if (!proc || !proc.pid) continue;
    try { spawn('taskkill', ['/F', '/T', '/PID', String(proc.pid)], { windowsHide: true, shell: false }); } catch {}
  }
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
  }).on('error', () => {}); // server not ready yet
}

// ─── Tray ─────────────────────────────────────────────────────────────────────

function buildContextMenu() {
  return Menu.buildFromTemplate([
    { label: 'Brain System', enabled: false },
    { type: 'separator' },
    { label: win?.isVisible() ? 'Masquer l\'app' : 'Ouvrir l\'app', click: toggleWindow },
    { type: 'separator' },
    { label: syncLabel(),                                    enabled: false },
    { label: `${statusCache.total_notes} notes indexées`,   enabled: false },
    { type: 'separator' },
    { label: '↺ Relancer l\'agent', click: restartAgent },
    { type: 'separator' },
    { label: '✕ Quitter', click: () => { app.isQuitting = true; app.quit(); } },
  ]);
}

function updateTray() {
  if (!tray) return;
  tray.setImage(isSyncing ? IMG_SYNCING : IMG_IDLE);
  const notesStr = (!isSyncing && !syncFailed && statusCache.last_sync)
    ? `${statusCache.total_notes} notes · `
    : '';
  tray.setToolTip(`Brain — ${notesStr}${syncLabel()}`);
  tray.setContextMenu(buildContextMenu());
}

function createTray() {
  tray = new Tray(IMG_IDLE);
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
  updateTray(); // refresh Ouvrir/Masquer label
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
  win.webContents.openDevTools({ mode: 'detach' }); // DEBUG — retirer après dev
  win.maximize();
  win.on('close', (e) => {
    if (!app.isQuitting) { e.preventDefault(); win.hide(); updateTray(); }
  });
}

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  IMG_IDLE    = nativeImage.createFromPath(path.join(ASSETS_DIR, 'logo-16.png'));
  IMG_SYNCING = nativeImage.createFromPath(path.join(ASSETS_DIR, 'logo-syncing-16.png'));

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

app.on('window-all-closed', () => { /* tray keeps app alive */ });

app.on('will-quit', killChildren);
