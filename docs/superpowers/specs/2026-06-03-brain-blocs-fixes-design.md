# Brain — Blocs Fixes (Travail / Projets / Bloc-notes)
**Date :** 2026-06-03
**Statut :** Approuvé

---

## Objectif

Afficher en permanence dans l'app les 3 fichiers Dropbox fixes (`travail.md`, `projet.md`, `blocnotes.md`) dans une section fixe en bas de l'écran, avec la possibilité de cocher chaque item (strikethrough immédiat + suppression Dropbox en arrière-plan).

---

## Format des fichiers Dropbox

```
# Travail
- analyse back to school ← 01/06/2026 13:22
- follow up affordability ← 02/06/2026 11:25
```

- Chemin Dropbox : `/Applications/Joplin/travail.md`, `projet.md`, `blocnotes.md`
- Ces fichiers sont **exclus** du cycle de l'agent (`exclure` dans `brain_agent.py`) — ils ne changent pas
- Items : lignes commençant par `- `, séparateur `←` (U+2190) entre texte et date
- Lignes sans date aussi acceptées

---

## Architecture & data flow

### `brain_server.py` — 2 nouveaux endpoints

#### `GET /blocs`

Lit les 3 fichiers Dropbox à la volée, les parse, retourne :

```json
[
  {
    "name": "travail",
    "titre": "Travail",
    "items": [
      {"idx": 0, "texte": "analyse back to school", "date": "01/06/2026 13:22"},
      {"idx": 1, "texte": "follow up affordability", "date": "02/06/2026 11:25"}
    ]
  },
  {
    "name": "projets",
    "titre": "Projets",
    "items": [...]
  },
  {
    "name": "blocnotes",
    "titre": "Bloc-notes",
    "items": []
  }
]
```

**Parsing :**
```python
import re
ITEM_RE = re.compile(r'^-\s+(.+?)\s*←\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})\s*$')
```
- Lignes qui ne matchent pas (titre `#`, lignes vides) → ignorées
- Lignes sans date (`- texte brut`) → acceptées avec `"date": null`
- L'index `idx` correspond à la position dans la liste des items parsés (pas dans le fichier brut)

**Mapping name → fichier Dropbox :**
```python
BLOCS = {
    "travail":   "/Applications/Joplin/travail.md",
    "projets":   "/Applications/Joplin/projet.md",
    "blocnotes": "/Applications/Joplin/blocnotes.md",
}
```

Si un fichier Dropbox est inaccessible → retourner le bloc avec `items: []` (pas d'erreur globale).

#### `DELETE /blocs/{name}/{idx}`

1. Valide que `name` est dans `BLOCS` → 404 sinon
2. Relit le fichier Dropbox (pas de cache, évite les conflits)
3. Reparse les items pour localiser la ligne à l'index `idx`
4. Retire cette ligne du texte brut
5. Réécrit le fichier sur Dropbox (`WriteMode.overwrite`)
6. Si `idx` hors limites (item déjà supprimé entre-temps) → retourne `{"deleted": false}` sans erreur
7. Retourne `{"deleted": true, "name": name, "idx": idx}`

---

### `renderer.js` — state & render

**State ajouté :**
```javascript
blocs: [],          // [{name, titre, items: [{idx, texte, date}]}]
checkedItems: new Set(), // clés "name:idx" — éphémère, pas persisté
```

**`loadData()` :** ajouter `/blocs` en parallèle avec les autres fetches :
```javascript
const [statusData, featuredRaw, notesRaw, blocsRaw] = await Promise.all([
  fetch(`${API}/status`).then(r => r.json()),
  fetch(`${API}/a-la-une?limit=6`).then(r => r.json()),
  fetch(`${API}/notes?limit=200`).then(r => r.json()),
  fetch(`${API}/blocs`).then(r => r.json()).catch(() => []),
]);
setState({ ..., blocs: blocsRaw });
```

`/blocs` échoue silencieusement (catch → `[]`), n'empêche pas le chargement des notes.

**`checkItem(name, idx)` :**
```javascript
async function checkItem(name, idx) {
  state.checkedItems.add(`${name}:${idx}`);
  render(); // strikethrough immédiat
  // suppression en arrière-plan — silencieuse si erreur
  fetch(`${API}/blocs/${name}/${idx}`, { method: 'DELETE' }).catch(() => {});
}
```

---

## UI

### Layout

Section fixe en bas de la fenêtre, sous `#notes-grid` :

```html
<section id="blocs-section">
  <div class="blocs-grid">
    <div class="bloc-col" id="bloc-travail">...</div>
    <div class="bloc-col" id="bloc-projets">...</div>
    <div class="bloc-col" id="bloc-blocnotes">...</div>
  </div>
</section>
```

### Rendu d'une colonne

```
┌──────────────────────────┐
│ TRAVAIL (2)              │  ← label + compteur items non-cochés
├──────────────────────────┤
│ ○  analyse back to       │  ← rond vide + texte 2 lignes max
│    school                │
│    01/06 13:22           │  ← date en gris discret
│                          │
│ ●  follow up ~~afford~~  │  ← coché : rond plein + strikethrough + opacité 0.4
│    02/06 11:25           │
└──────────────────────────┘
```

- Hauteur max section : `220px`, `overflow-y: auto` par colonne
- Colonnes égales : `grid-template-columns: 1fr 1fr 1fr`
- Séparateur vertical entre colonnes : `border-right: 1px solid rgba(255,255,255,0.06)`
- Fond section légèrement plus sombre : `background: rgba(255,255,255,0.02)`

### Comportement du rond

- Non coché : `○` cercle vide `2px` border, couleur `var(--ink-4)`
- Coché : `●` cercle plein, couleur `var(--accent)`, texte `text-decoration: line-through`, `opacity: 0.4`
- Le compteur dans le header (`TRAVAIL (2)`) ne compte que les items non-cochés

---

## CSS — nouvelles classes

```css
#blocs-section {
  flex-shrink: 0;
  border-top: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.02);
  padding: 12px 16px 16px;
}

.blocs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 0;
  max-height: 200px;
}

.bloc-col {
  padding: 0 12px;
  overflow-y: auto;
  border-right: 1px solid rgba(255,255,255,0.06);
}
.bloc-col:last-child { border-right: none; }

.bloc-col-header {
  font-size: 9px;
  font-family: var(--font-mono);
  color: var(--ink-4);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 8px;
}

.bloc-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  cursor: pointer;
  padding: 4px 0;
  user-select: none;
}
.bloc-item:hover .bloc-check { border-color: var(--accent); }

.bloc-check {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1.5px solid var(--ink-4);
  margin-top: 2px;
  transition: background .15s, border-color .15s;
}
.bloc-item.checked .bloc-check {
  background: var(--accent);
  border-color: var(--accent);
}

.bloc-item-text {
  font-size: 12px;
  line-height: 1.4;
  color: var(--ink-2);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.bloc-item.checked .bloc-item-text {
  text-decoration: line-through;
  opacity: 0.4;
}

.bloc-item-date {
  font-size: 10px;
  color: var(--ink-4);
  font-family: var(--font-mono);
  margin-top: 1px;
}
```

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `brain_server.py` | `GET /blocs` + `DELETE /blocs/{name}/{idx}` + constante `BLOCS` |
| `brain_app/renderer.js` | `blocs` + `checkedItems` dans state, `loadData()` étendu, `checkItem()`, `renderBlocs()` |
| `brain_app/style.css` | `.blocs-section`, `.blocs-grid`, `.bloc-col`, `.bloc-item`, `.bloc-check`, etc. |

---

## Ce qui ne change pas

- `brain_agent.py` : les 3 fichiers restent dans `exclure` — l'agent ne les traite pas
- `brain_app/index.html` : ajout minimal d'un `<section id="blocs-section">` à la fin du body

---

## Hors scope

- Ajout d'items depuis l'app (se fait via le bot Telegram)
- Persistance de l'état coché entre sessions (éphémère volontaire)
- Réorganisation / drag-and-drop des items
- Édition du texte d'un item
