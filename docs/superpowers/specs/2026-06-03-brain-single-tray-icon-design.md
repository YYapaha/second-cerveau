# Brain — Icône Tray Unique
**Date :** 2026-06-03
**Statut :** Approuvé

---

## Objectif

Remplacer les 3 icônes permanentes dans la barre des tâches Windows (agent Python, serveur uvicorn, app Electron) par une **unique icône dans le system tray**. Electron devient le superviseur unique qui spawne et gère les deux processus Python en arrière-plan.

Conçu pour être packagé plus tard en `.exe` via `electron-builder` (approche C) sans modification structurelle.

---

## Architecture & cycle de vie

`main.js` est le seul point d'entrée. Au démarrage :

1. Spawne `brain_agent.py` (chemin `../brain_agent.py`) avec `windowsHide: true`, `detached: false`
2. Attend 3s puis spawne `uvicorn brain_server:app --host 127.0.0.1 --port 7842 --log-level warning` de la même façon
3. Crée le `Tray` avec `logo-16.png`
4. Crée la `BrowserWindow` avec `skipTaskbar: true`
5. Démarre un polling `/status` toutes les 30s pour mettre à jour le tooltip

À la fermeture (clic "Quitter" dans le tray) :
1. `agent.kill()`
2. `server.kill()`
3. `app.quit()`

Les processus enfants sont `detached: false` → ils meurent si Electron quitte pour n'importe quelle raison.

`brain_start.bat` simplifié :
```bat
@echo off
cd /d "%~dp0brain_app"
start "" npx electron .
```

---

## Tray icon

### Assets

- Source : `Idées/assets/logo.svg` copié dans `brain_app/assets/logo.svg`
- `sharp` (npm) génère au build :
  - `brain_app/assets/logo-16.png` — état idle
  - `brain_app/assets/logo-32.png` — état idle (haute résolution)
  - `brain_app/assets/logo-syncing-16.png` — même SVG rendu à 50% d'opacité

### États

| État | Icône | Tooltip |
|---|---|---|
| Idle | `logo-16.png` | `Brain — 142 notes · sync il y a 12 min` |
| Syncing | `logo-syncing-16.png` | `Brain — Synchronisation en cours...` |
| Serveur pas prêt | `logo-syncing-16.png` | `Brain — Serveur en démarrage...` |
| Échec sync | `logo-16.png` | `Brain — Dernière sync : échec` |

### Menu contextuel (clic droit)

```
Brain System
─────────────────
● Ouvrir l'app          ← si fenêtre cachée
● Masquer l'app         ← si fenêtre visible
─────────────────
  Dernière sync : il y a 12 min
  142 notes indexées
─────────────────
↺ Relancer l'agent
─────────────────
✕ Quitter
```

Les items de statut (sync, notes) sont non-cliquables, mis à jour à chaque ouverture du menu et à chaque polling.

**Double-clic** sur l'icône tray = `toggleWindow()`.

---

## Fenêtre app

### Options BrowserWindow modifiées

```js
skipTaskbar: true,   // disparaît du taskbar Windows
show: true,          // démarre visible sur l'écran portrait
```

### toggleWindow()

```js
function toggleWindow() {
  if (win.isVisible()) {
    win.hide();
  } else {
    // Repositionner sur l'écran portrait avant de montrer
    const display = getTargetDisplay();
    win.setBounds(display.bounds);
    win.maximize();
    win.show();
    win.focus();
  }
}
```

### Interception close

```js
win.on('close', (e) => {
  e.preventDefault();
  win.hide();  // fermer la fenêtre = masquer, pas quitter
});
```

Seul "Quitter" dans le menu tray tue réellement les processus.

---

## Statut agent via stdout

`brain_agent.py` émet trois marqueurs stdout :

```python
print("[SYNC_START]", flush=True)   # début du cycle de sync
# ... traitement ...
print("[SYNC_END]", flush=True)     # fin du cycle OK
# en cas d'erreur :
print("[SYNC_ERROR]", flush=True)
```

`main.js` lit `agent.stdout` ligne par ligne avec `readline` (stdlib Node) :

- `[SYNC_START]` → icône passe en `logo-syncing-16.png`, tooltip "Synchronisation en cours..."
- `[SYNC_END]` → icône revient idle, polling `/status` déclenché immédiatement
- `[SYNC_ERROR]` → icône idle, tooltip "Dernière sync : échec"

Le polling `/status` toutes les 30s reste la source de vérité pour le tooltip (nb notes, heure). Les marqueurs stdout servent uniquement à l'animation de l'icône.

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `brain_app/main.js` | Spawn agent+serveur cachés, Tray, `skipTaskbar`, `toggleWindow`, polling `/status`, lecture stdout agent |
| `brain_app/package.json` | Ajout dépendance `sharp` |
| `brain_start.bat` | Simplifié : lance uniquement `electron .` |
| `brain_agent.py` | Ajout `print("[SYNC_START/END/ERROR]", flush=True)` aux bons endroits |

**Nouveau fichier :** `brain_app/build-assets.js` — script Node à lancer une fois (`node build-assets.js`) qui utilise `sharp` pour générer les PNGs depuis `logo.svg`. Les PNGs sont committés, pas regénérés au runtime.

**Nouveau dossier :** `brain_app/assets/` avec `logo.svg` + PNGs générés.

---

## Hors scope

- Packaging electron-builder (prévu approche C, après implémentation)
- Notifications Windows toast
- Relancer le serveur depuis le tray (le serveur est stable, l'agent est ce qui sync)
