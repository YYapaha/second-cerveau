# Brain Blocs Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher les 3 fichiers Dropbox fixes (travail/projets/blocnotes) dans une section permanente en bas de l'app, avec ajout et suppression d'items synchro Dropbox.

**Architecture:** Deux nouveaux endpoints FastAPI (`GET /blocs`, `POST /blocs/{name}/item`, `DELETE /blocs/{name}/{idx}`) lisent/écrivent directement les `.md` Dropbox. Le renderer charge `/blocs` en parallèle avec `/notes`, affiche 3 colonnes en bas de l'écran, et gère cocher (strikethrough + DELETE en arrière-plan) et ajouter (POST + reload).

**Tech Stack:** FastAPI, Dropbox SDK Python, HTML/CSS/JS vanilla, Electron.

---

## File structure

| Fichier | Changement |
|---|---|
| `brain_server.py` | Constantes `BLOCS`/`_TITRES`/`_ITEM_RE`, helper `_parse_bloc()`, 3 nouveaux endpoints |
| `tests/test_brain_server.py` | Tests des 3 nouveaux endpoints (mock Dropbox) |
| `brain_app/index.html` | `<section id="blocs-section">` dans `.panel` |
| `brain_app/style.css` | Classes `.blocs-section`, `.blocs-grid`, `.bloc-col`, `.bloc-item`, `.bloc-check`, `.bloc-add` |
| `brain_app/renderer.js` | State `blocs`/`checkedItems`, `loadData()` étendu, `renderBlocs()`, `checkItem()`, `addItem()`, appel dans `render()` |

---

## Task 1 : Endpoints serveur blocs

**Files:**
- Modify: `brain_server.py`
- Test: `tests/test_brain_server.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_brain_server.py` :

```python
# ── /blocs tests ──────────────────────────────────────────────────────────────

from unittest.mock import patch, MagicMock

_TRAVAIL_CONTENT = "# Travail\n- task zero ← 01/06/2026 10:00\n- task one ← 02/06/2026 11:00\n"
_EMPTY_CONTENT   = "# Bloc-notes\n"


def _mock_dbx(content_map: dict):
    """content_map: {dropbox_path: bytes_content}"""
    mock = MagicMock()
    def _download(path):
        dl = MagicMock()
        dl.content = content_map.get(path, b"# Vide\n")
        return (None, dl)
    mock.files_download.side_effect = _download
    return mock


def test_get_blocs_returns_3_blocs():
    dbx = _mock_dbx({"/Applications/Joplin/travail.md": _TRAVAIL_CONTENT.encode()})
    with patch("brain_server.get_dropbox", return_value=dbx):
        r = client.get("/blocs")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 3
    assert {b["name"] for b in data} == {"travail", "projets", "blocnotes"}


def test_get_blocs_parses_items():
    dbx = _mock_dbx({"/Applications/Joplin/travail.md": _TRAVAIL_CONTENT.encode()})
    with patch("brain_server.get_dropbox", return_value=dbx):
        r = client.get("/blocs")
    travail = next(b for b in r.json() if b["name"] == "travail")
    assert len(travail["items"]) == 2
    assert travail["items"][0]["texte"] == "task zero"
    assert travail["items"][0]["date"] == "01/06/2026 10:00"
    assert travail["items"][0]["idx"] == 0


def test_get_blocs_dropbox_error_returns_empty_items():
    dbx = MagicMock()
    dbx.files_download.side_effect = Exception("réseau")
    with patch("brain_server.get_dropbox", return_value=dbx):
        r = client.get("/blocs")
    assert r.status_code == 200
    for bloc in r.json():
        assert bloc["items"] == []


def test_delete_bloc_item_removes_line():
    dbx = _mock_dbx({"/Applications/Joplin/travail.md": _TRAVAIL_CONTENT.encode()})
    with patch("brain_server.get_dropbox", return_value=dbx):
        r = client.delete("/blocs/travail/0")
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    uploaded = dbx.files_upload.call_args[0][0].decode("utf-8")
    assert "task zero" not in uploaded
    assert "task one" in uploaded


def test_delete_bloc_item_out_of_range_returns_false():
    dbx = _mock_dbx({"/Applications/Joplin/travail.md": _TRAVAIL_CONTENT.encode()})
    with patch("brain_server.get_dropbox", return_value=dbx):
        r = client.delete("/blocs/travail/99")
    assert r.status_code == 200
    assert r.json()["deleted"] is False
    dbx.files_upload.assert_not_called()


def test_delete_bloc_unknown_name_404():
    with patch("brain_server.get_dropbox", return_value=MagicMock()):
        r = client.delete("/blocs/inconnu/0")
    assert r.status_code == 404


def test_add_bloc_item_appends_line():
    dbx = _mock_dbx({"/Applications/Joplin/travail.md": _TRAVAIL_CONTENT.encode()})
    with patch("brain_server.get_dropbox", return_value=dbx):
        r = client.post("/blocs/travail/item", json={"texte": "nouvelle tâche"})
    assert r.status_code == 200
    assert r.json()["added"] is True
    assert r.json()["texte"] == "nouvelle tâche"
    uploaded = dbx.files_upload.call_args[0][0].decode("utf-8")
    assert "nouvelle tâche" in uploaded
    assert "←" in uploaded  # ← separator


def test_add_bloc_item_empty_texte_422():
    with patch("brain_server.get_dropbox", return_value=MagicMock()):
        r = client.post("/blocs/travail/item", json={"texte": "  "})
    assert r.status_code == 422


def test_add_bloc_unknown_name_404():
    with patch("brain_server.get_dropbox", return_value=MagicMock()):
        r = client.post("/blocs/inconnu/item", json={"texte": "test"})
    assert r.status_code == 404
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```powershell
cd "C:\Users\yapa\second_cerveau"
python -m pytest tests/test_brain_server.py -k "blocs" -v
```

Expected: tous FAILED avec `AttributeError` ou `404` (endpoints inexistants).

- [ ] **Step 3 : Implémenter les endpoints dans `brain_server.py`**

Ajouter après les imports existants (ligne 5, après `from typing import Optional`) :

```python
import re
from datetime import datetime
```

Ajouter après la définition de `_SELECT_FIELDS` (après la ligne `"sources_ids, contenu_riche, titre_modifie"`) :

```python
# ── Blocs fixes ───────────────────────────────────────────────────────────────

_ITEM_RE = re.compile(r'^-\s+(.+?)\s*←\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})\s*$')

BLOCS = {
    "travail":   "/Applications/Joplin/travail.md",
    "projets":   "/Applications/Joplin/projet.md",
    "blocnotes": "/Applications/Joplin/blocnotes.md",
}

_TITRES = {
    "travail":   "Travail",
    "projets":   "Projets",
    "blocnotes": "Bloc-notes",
}


def _parse_bloc(content: str) -> list[dict]:
    items, idx = [], 0
    for line in content.splitlines():
        line = line.rstrip()
        if not line.startswith("- "):
            continue
        m = _ITEM_RE.match(line)
        if m:
            items.append({"idx": idx, "texte": m.group(1), "date": m.group(2)})
        else:
            text = line[2:].strip()
            if text:
                items.append({"idx": idx, "texte": text, "date": None})
        idx += 1
    return items


@app.get("/blocs")
def get_blocs():
    result = []
    for name, path in BLOCS.items():
        items = []
        try:
            _, dl = get_dropbox().files_download(path)
            items = _parse_bloc(dl.content.decode("utf-8", errors="replace"))
        except Exception:
            pass
        result.append({"name": name, "titre": _TITRES[name], "items": items})
    return result


@app.post("/blocs/{name}/item")
def add_bloc_item(name: str, body: dict):
    from fastapi import HTTPException
    import dropbox as dbx_mod
    if name not in BLOCS:
        raise HTTPException(status_code=404, detail="Bloc inconnu")
    texte = (body.get("texte") or "").strip()
    if not texte:
        raise HTTPException(status_code=422, detail="texte requis")
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    new_line = f"- {texte} ← {date_str}\n"
    dbx  = get_dropbox()
    path = BLOCS[name]
    try:
        _, dl = dbx.files_download(path)
        content = dl.content.decode("utf-8", errors="replace")
    except Exception:
        content = f"# {_TITRES[name]}\n"
    if not content.endswith("\n"):
        content += "\n"
    content += new_line
    dbx.files_upload(content.encode("utf-8"), path, mode=dbx_mod.files.WriteMode.overwrite)
    return {"added": True, "texte": texte, "date": date_str}


@app.delete("/blocs/{name}/{idx}")
def delete_bloc_item(name: str, idx: int):
    from fastapi import HTTPException
    import dropbox as dbx_mod
    if name not in BLOCS:
        raise HTTPException(status_code=404, detail="Bloc inconnu")
    dbx  = get_dropbox()
    path = BLOCS[name]
    try:
        _, dl = dbx.files_download(path)
        content = dl.content.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Dropbox : {e}")
    lines = content.splitlines(keepends=True)
    item_idx, line_to_remove = 0, None
    for i, line in enumerate(lines):
        if line.lstrip().startswith("- "):
            if item_idx == idx:
                line_to_remove = i
                break
            item_idx += 1
    if line_to_remove is None:
        return {"deleted": False}
    lines.pop(line_to_remove)
    dbx.files_upload("".join(lines).encode("utf-8"), path, mode=dbx_mod.files.WriteMode.overwrite)
    return {"deleted": True, "name": name, "idx": idx}
```

- [ ] **Step 4 : Vérifier que les tests passent**

```powershell
cd "C:\Users\yapa\second_cerveau"
python -m pytest tests/test_brain_server.py -k "blocs" -v
```

Expected: 9 tests PASSED.

- [ ] **Step 5 : Suite de tests complète**

```powershell
python -m pytest tests/ -q
```

Expected: tous les tests passent (aucune régression).

- [ ] **Step 6 : Commit**

```powershell
git add brain_server.py tests/test_brain_server.py
git commit -m "feat: add GET/POST/DELETE /blocs endpoints for fixed Dropbox files"
```

---

## Task 2 : HTML + CSS

**Files:**
- Modify: `brain_app/index.html`
- Modify: `brain_app/style.css`

- [ ] **Step 1 : Ajouter `#blocs-section` dans `index.html`**

Dans `brain_app/index.html`, ajouter juste avant `</div><!-- /panel -->` (ligne 69) :

```html
      <!-- Blocs fixes (Travail / Projets / Bloc-notes) -->
      <section id="blocs-section"></section>
```

Résultat — la fin du `.panel` :
```html
      <!-- Blocs fixes (Travail / Projets / Bloc-notes) -->
      <section id="blocs-section"></section>

      <!-- Stats de coin (grille uniquement) -->
      <div class="corner bl" id="corner-bl"></div>
      <div class="corner br" id="corner-br"></div>

    </div><!-- /panel -->
```

- [ ] **Step 2 : Ajouter les styles dans `style.css`**

Ajouter à la fin de `brain_app/style.css` :

```css
/* ============================================================
   Blocs fixes
   ============================================================ */
#blocs-section {
  flex-shrink: 0;
  border-top: 1px solid var(--stroke);
  background: rgba(255,255,255,0.015);
  padding: 10px 16px 14px;
  position: relative;
  z-index: 2;
}

.blocs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  max-height: 200px;
}

.bloc-col {
  padding: 0 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.bloc-col:not(:last-child) {
  border-right: 1px solid rgba(255,255,255,0.06);
}
.bloc-col:first-child { padding-left: 0; }
.bloc-col:last-child  { padding-right: 0; }

.bloc-col-header {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-4);
  margin-bottom: 8px;
  flex-shrink: 0;
}

.bloc-items {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.bloc-item {
  display: flex;
  gap: 7px;
  align-items: flex-start;
  cursor: pointer;
  padding: 3px 4px;
  border-radius: var(--r-sm);
  transition: background .15s var(--ease);
  user-select: none;
}
.bloc-item:hover { background: var(--glass); }
.bloc-item:hover .bloc-check { border-color: var(--d-une); }

.bloc-check {
  flex-shrink: 0;
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 1.5px solid var(--ink-4);
  margin-top: 3px;
  transition: background .15s var(--ease), border-color .15s var(--ease);
}
.bloc-item.checked .bloc-check {
  background: var(--ink-4);
  border-color: var(--ink-4);
}

.bloc-item-body { min-width: 0; }

.bloc-item-text {
  font-size: 11.5px;
  line-height: 1.4;
  color: var(--ink-2);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.bloc-item.checked .bloc-item-text {
  text-decoration: line-through;
  opacity: 0.35;
}

.bloc-item-date {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--ink-4);
  margin-top: 1px;
}

/* Bouton + et input ajout */
.bloc-add {
  flex-shrink: 0;
  margin-top: 6px;
}

.bloc-add-btn {
  all: unset;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--ink-4);
  padding: 2px 6px;
  border-radius: var(--r-sm);
  transition: color .15s var(--ease), background .15s var(--ease);
}
.bloc-add-btn:hover { color: var(--ink-2); background: var(--glass); }

.bloc-add-input {
  width: 100%;
  background: var(--glass);
  border: 1px solid var(--stroke);
  border-radius: var(--r-sm);
  color: var(--ink);
  font-family: var(--font-ui);
  font-size: 11.5px;
  padding: 4px 8px;
  outline: none;
  transition: border-color .15s var(--ease);
}
.bloc-add-input:focus { border-color: var(--stroke-hi); }
.bloc-add-input.hidden { display: none; }
```

- [ ] **Step 3 : Vérifier visuellement**

Lancer l'app : `cd brain_app && npx electron .`

La section blocs doit apparaître en bas (vide pour l'instant — le renderer n'est pas encore branché). Vérifier :
- La section est visible avec un séparateur en haut
- 3 colonnes sont présentes (vides)

- [ ] **Step 4 : Commit**

```powershell
cd "C:\Users\yapa\second_cerveau"
git add brain_app/index.html brain_app/style.css
git commit -m "feat: add blocs-section HTML structure and CSS"
```

---

## Task 3 : Renderer — state, rendu et interactions

**Files:**
- Modify: `brain_app/renderer.js`

- [ ] **Step 1 : Ajouter `blocs` et `checkedItems` au state initial**

Dans `renderer.js`, le state initial est autour de la ligne 77. Ajouter les deux clés :

```javascript
let state = {
  mode: 'grille',
  notes: [],
  featured: [],
  blocs: [],                    // ← ajouter
  checkedItems: new Set(),      // ← ajouter
  status: { total_notes: 0, meta_fiches_count: 0, last_sync: null },
  activeFilter: 'tous',
  sort: 'recent',
  linkedOnly: false,
  openNote: null,
  filteredList: [],
};
```

- [ ] **Step 2 : Étendre `loadData()` pour inclure `/blocs`**

Remplacer la fonction `loadData()` existante (lignes 717-734) :

```javascript
async function loadData() {
  try {
    const [statusData, featuredRaw, notesRaw, blocsRaw] = await Promise.all([
      fetch(`${API}/status`).then(r => r.json()),
      fetch(`${API}/a-la-une?limit=6`).then(r => r.json()),
      fetch(`${API}/notes?limit=200`).then(r => r.json()),
      fetch(`${API}/blocs`).then(r => r.json()).catch(() => []),
    ]);
    setState({
      status: statusData,
      notes: notesRaw.map(mapNote),
      featured: featuredRaw.map(mapNote),
      blocs: blocsRaw,
    });
  } catch {
    document.getElementById('pill-stat').innerHTML =
      '<span class="dot" style="background:var(--d-projets)"></span>hors ligne';
    setTimeout(loadData, 5000);
  }
}
```

Note : `/blocs` échoue silencieusement (`.catch(() => [])`) — ne bloque pas le chargement des notes.

- [ ] **Step 3 : Ajouter `checkItem()` et `addItem()`**

Ajouter avant la fonction `loadData()` (ligne 715) :

```javascript
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
```

- [ ] **Step 4 : Ajouter `renderBlocs()`**

Ajouter juste après les fonctions `checkItem` et `addItem` :

```javascript
function renderBlocs() {
  const section = document.getElementById('blocs-section');
  if (!section) return;
  if (!state.blocs || state.blocs.length === 0) return;

  section.innerHTML = `<div class="blocs-grid">${state.blocs.map(renderBlocCol).join('')}</div>`;

  // Event delegation — clics sur items
  section.querySelectorAll('.bloc-item').forEach(el => {
    el.addEventListener('click', () => {
      checkItem(el.dataset.name, parseInt(el.dataset.idx, 10));
    });
  });

  // Boutons + et inputs par colonne
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
      if (e.key === 'Enter')  await confirm();
      if (e.key === 'Escape') { input.value = ''; input.classList.add('hidden'); btn.style.display = ''; }
    });
    input.addEventListener('blur', confirm);
  });
}

function renderBlocCol({ name, titre, items }) {
  const uncheckedCount = items.filter(it => !state.checkedItems.has(`${name}:${it.idx}`)).length;
  return `
    <div class="bloc-col">
      <div class="bloc-col-header">${titre} <span style="opacity:.5">(${uncheckedCount})</span></div>
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
  const checked  = state.checkedItems.has(`${name}:${idx}`);
  const dateShort = date ? date.slice(0, 5) : '';  // "DD/MM"
  return `
    <div class="bloc-item${checked ? ' checked' : ''}" data-name="${name}" data-idx="${idx}">
      <div class="bloc-check"></div>
      <div class="bloc-item-body">
        <div class="bloc-item-text">${texte}</div>
        ${dateShort ? `<div class="bloc-item-date">${dateShort}</div>` : ''}
      </div>
    </div>`;
}
```

- [ ] **Step 5 : Appeler `renderBlocs()` depuis `render()`**

La fonction `render()` est à la ligne 704. Ajouter l'appel en fin de fonction :

```javascript
function render() {
  renderTopbar();
  if (state.mode === 'grille') renderGrille();
  else {
    document.getElementById('grille-view').classList.add('hidden');
    renderConstellation();
    renderCornerStats();
  }
  renderModal();
  renderBlocs();  // ← ajouter cette ligne
}
```

- [ ] **Step 6 : Vérifier manuellement**

Lancer l'app (`brain_start.bat` ou `npx electron .` dans `brain_app/`). Attendre ~15s le démarrage du serveur, puis vérifier :

- [ ] La section blocs apparaît en bas avec 3 colonnes
- [ ] Les items des fichiers Dropbox sont listés avec leur date
- [ ] Cliquer un item → strikethrough immédiat
- [ ] L'item coché reste visible en session mais ne réapparaît pas au prochain démarrage
- [ ] Cliquer `+ ajouter` → input apparaît, Entrée → item ajouté + reload, Escape → annule
- [ ] Si un bloc est vide → colonne vide avec juste le `+ ajouter`

- [ ] **Step 7 : Tests complets**

```powershell
cd "C:\Users\yapa\second_cerveau"
python -m pytest tests/ -q
```

Expected: 23+ tests PASSED, 0 FAILED.

- [ ] **Step 8 : Commit**

```powershell
git add brain_app/renderer.js
git commit -m "feat: render blocs fixes section with check/add from app"
```
