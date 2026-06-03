# Brain Notes Enrichissement — Plan 4

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Prérequis :** Plans 1-3 terminés. `brain_server.py` tourne sur port 7842. `brain_app/` est l'app Electron avec renderer.js, style.css, index.html, preload.js.

**Goal:** Enrichir les notes avec `contenu_riche` (points clés, URL source, pourquoi garder, quand ressortir), afficher ce contenu dans la modale Electron, permettre la suppression synchronisée DB+Dropbox avec animation, et l'édition du titre inline.

**Architecture:** Cinq fichiers modifiés en séquence : `brain_agent.py` (schéma + prompt + reprocess) → `brain_server.py` (SELECT + DELETE Dropbox + PATCH titre) → `preload.js` (openUrl) → `style.css` (nouveaux styles) → `renderer.js` (modal enrichie + suppression animée + titre éditable).

**Tech Stack:** Python/SQLite, FastAPI, Electron 35, Anime.js v4, Dropbox SDK Python

**Spec de référence :** `docs/superpowers/specs/2026-06-03-brain-notes-enrichissement.md`

---

## File Map

**Modifiés :**
- `brain_agent.py` — `init_db` + `_PROMPT_RAFFINEMENT` + `raffiner_note` + `run_agent` + `__main__`
- `brain_server.py` — `_SELECT_FIELDS` + import `get_dropbox` + endpoint DELETE + endpoint PATCH
- `brain_app/preload.js` — import `shell`, expose `openUrl`
- `brain_app/style.css` — `.source-link`, `.points-cles`, `.deletebtn`, `.title-input`
- `brain_app/renderer.js` — `mapNote`, `ICONS`, `renderModal`, `deleteNote`, `patchTitre`

**Tests modifiés :**
- `tests/test_brain_agent.py` — 2 nouveaux tests
- `tests/test_brain_server.py` — `_setup`, `_insert_note` mis à jour + 3 nouveaux tests

---

### Task 1 : brain_agent.py — schéma DB + nouveau prompt + flag --reprocess

**Files:**
- Modify: `brain_agent.py`
- Test: `tests/test_brain_agent.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_brain_agent.py` :

```python
def test_init_db_has_new_columns():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        from brain_agent import init_db
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(notes)").fetchall()}
        assert "contenu_riche"  in cols
        assert "titre_modifie"  in cols
        conn.close()
    finally:
        os.unlink(db_path)


def test_raffiner_note_returns_contenu_riche():
    from brain_agent import raffiner_note
    from unittest.mock import patch, MagicMock
    mock_out = {
        "titre_court": "Astuces Claude Code",
        "insight_cle": "Personnaliser pour maximiser.",
        "resume": "Un résumé.",
        "domaine": "Apprentissage",
        "contenu_riche": {
            "url_source": "https://github.com/test",
            "points_cles": ["Point 1", "Point 2"],
            "pourquoi_garder": "Utile.",
            "quand_ressortir": "Avant un projet."
        }
    }
    with patch("brain_agent.OpenAI") as mock_cls:
        inst = MagicMock()
        mock_cls.return_value = inst
        inst.chat.completions.create.return_value.choices[0].message.content = json.dumps(mock_out)
        result = raffiner_note("Contenu test", "fake-key")
    assert "contenu_riche" in result
    cr = result["contenu_riche"]
    assert isinstance(cr["points_cles"], list)
    assert cr["url_source"] == "https://github.com/test"
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd C:\Users\yapa\second_cerveau
python -m pytest tests/test_brain_agent.py::test_init_db_has_new_columns tests/test_brain_agent.py::test_raffiner_note_returns_contenu_riche -v
```

Expected : 2 FAILED

- [ ] **Step 3 : Mettre à jour `init_db` dans brain_agent.py**

Remplacer la fonction `init_db` (lignes 29-55) par :

```python
def init_db(db_path: str | Path = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id               TEXT PRIMARY KEY,
                dropbox_path     TEXT NOT NULL,
                titre_court      TEXT,
                insight_cle      TEXT,
                resume           TEXT,
                domaine          TEXT,
                tags             TEXT,
                date_capture     TEXT,
                date_traitement  TEXT,
                score_pertinence REAL    DEFAULT 0.0,
                est_meta_fiche   INTEGER DEFAULT 0,
                sources_ids      TEXT,
                embedding        BLOB,
                contenu_riche    TEXT,
                titre_modifie    INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        # Migration pour les DB existantes
        for col, definition in [
            ("contenu_riche", "TEXT"),
            ("titre_modifie", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE notes ADD COLUMN {col} {definition}")
                conn.commit()
            except Exception:
                pass  # colonne déjà présente
    finally:
        conn.close()
```

- [ ] **Step 4 : Mettre à jour `_PROMPT_RAFFINEMENT` et `raffiner_note`**

Remplacer `_PROMPT_RAFFINEMENT` (lignes 112-134) par :

```python
_PROMPT_RAFFINEMENT = """Tu analyses une fiche de connaissance capturée par un utilisateur TDAH.

Retourne UNIQUEMENT un JSON valide (sans bloc markdown) :
{{
  "titre_court": "<vrai titre de la source si présent dans la fiche (ligne # TITLE ou titre principal), sinon 5-8 mots descriptifs en français>",
  "insight_cle": "<1 phrase actionnable qui capture l'essentiel, en français>",
  "resume": "<2-3 phrases résumant le contenu, en français>",
  "domaine": "<exactement un parmi : Travail | Apprentissage | Projets perso | Jeux vidéos | Plantes | Organisation TDAH>",
  "contenu_riche": {{
    "url_source": "<première URL http(s) trouvée dans la fiche, ou null>",
    "points_cles": ["<bullet 1>", "<bullet 2>", "..."],
    "pourquoi_garder": "<1-2 phrases sur la valeur long terme, ou null>",
    "quand_ressortir": "<1 phrase sur le contexte d'utilisation, ou null>"
  }}
}}

Règles :
- Si la fiche contient déjà des sections POINTS_CLES / POURQUOI_GARDER / QUAND_RESSORTIR → les extraire TELS QUELS sans reformuler
- Si ces sections sont absentes → les générer à partir du contenu
- points_cles : liste de 3 à 7 bullets actionnables en français correct
- Corrige les traductions approximatives
- Claude Code, VS Code, React, IA, Python, dev → Apprentissage
- IKEA, shifts, management → Travail
- Plantes, jardinage → Plantes
- Jeux → Jeux vidéos
- Organisation, TDAH, routines → Organisation TDAH
- Sinon → Projets perso

=== FICHE À ANALYSER ===
{contenu}
=== FIN DE LA FICHE ==="""


def raffiner_note(contenu: str, api_key: str) -> dict:
    """Appelle GPT-4.1 pour raffiner une fiche. Retourne dict avec 5 clés."""
    import re
    prompt = _PROMPT_RAFFINEMENT.format(contenu=contenu[:8000])
    r = OpenAI(api_key=api_key).chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
    )
    raw = r.choices[0].message.content.strip()
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip("`").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("raffiner_note: réponse GPT non parseable : %s — %s", raw[:200], e)
        raise
    # Normaliser contenu_riche
    if "contenu_riche" not in data or not isinstance(data["contenu_riche"], dict):
        data["contenu_riche"] = {"url_source": None, "points_cles": [], "pourquoi_garder": None, "quand_ressortir": None}
    cr = data["contenu_riche"]
    if not isinstance(cr.get("points_cles"), list):
        cr["points_cles"] = []
    return data
```

- [ ] **Step 5 : Mettre à jour `run_agent` pour écrire `contenu_riche` et respecter `titre_modifie`**

Remplacer le bloc `# 2. Raffiner les fiches non encore traitées` dans `run_agent` (lignes 289-319) par :

```python
        # 2. Raffiner les fiches non encore traitées
        for fiche in fiches_raw:
            note_id  = get_note_id(fiche["path"])
            existing = conn.execute(
                "SELECT date_traitement, domaine, titre_modifie, titre_court FROM notes WHERE id = ?",
                (note_id,)
            ).fetchone()

            if reprocess:
                # Sauter les notes Travail déjà classifiées
                if existing and existing["domaine"] == "Travail":
                    continue
            else:
                if existing and existing["date_traitement"] == fiche["modified"]:
                    continue

            log.info("Traitement : %s", fiche["name"])
            try:
                import re as _re
                refined   = raffiner_note(fiche["content"], api_key)
                emb_txt   = f"{refined['titre_court']} {refined['insight_cle']} {refined['resume']}"
                embedding = vectoriser(emb_txt, api_key)
                tag_match = _re.search(r"\*\*TAGS\*\*\s*:\s*(.+)", fiche["content"])
                tags      = tag_match.group(1).strip() if tag_match else ""

                # Préserver le titre si édité manuellement
                titre_modifie  = existing["titre_modifie"] if existing else 0
                titre_final    = existing["titre_court"] if titre_modifie else refined["titre_court"]
                contenu_riche  = json.dumps(refined.get("contenu_riche", {}), ensure_ascii=False)

                conn.execute("""
                    INSERT OR REPLACE INTO notes
                      (id, dropbox_path, titre_court, insight_cle, resume, domaine,
                       tags, date_capture, date_traitement, score_pertinence,
                       est_meta_fiche, sources_ids, embedding, contenu_riche, titre_modifie)
                    VALUES (?,?,?,?,?,?,?,?,?,0.0,0,NULL,?,?,?)
                """, (
                    note_id, fiche["path"],
                    titre_final, refined["insight_cle"], refined["resume"], refined["domaine"],
                    tags, fiche["modified"], fiche["modified"],
                    embedding_to_bytes(embedding),
                    contenu_riche,
                    titre_modifie,
                ))
                conn.commit()
            except Exception as e:
                log.error("Erreur %s : %s", fiche["name"], e)
```

- [ ] **Step 6 : Ajouter le flag `--reprocess` dans `__main__`**

Remplacer le bloc `if __name__ == "__main__":` (lignes 384-385) par :

```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Brain Agent — raffinement et vectorisation")
    parser.add_argument("--reprocess", action="store_true",
                        help="Re-traiter toutes les notes sauf domaine=Travail")
    args = parser.parse_args()
    run_agent(reprocess=args.reprocess)
```

Et mettre à jour la signature de `run_agent` :

```python
def run_agent(db_path: str | Path = DB_PATH, reprocess: bool = False) -> None:
```

- [ ] **Step 7 : Vérifier que les tests passent**

```bash
cd C:\Users\yapa\second_cerveau
python -m pytest tests/test_brain_agent.py -v
```

Expected : tous PASSED (17 existants + 2 nouveaux = 19)

- [ ] **Step 8 : Commit**

```bash
git add brain_agent.py tests/test_brain_agent.py
git commit -m "feat: brain_agent — contenu_riche, prompt enrichi 1200 tokens, flag --reprocess"
```

---

### Task 2 : brain_server.py — contenu_riche + DELETE Dropbox + PATCH titre

**Files:**
- Modify: `brain_server.py`
- Modify: `tests/test_brain_server.py`

- [ ] **Step 1 : Mettre à jour `_setup` et `_insert_note` dans test_brain_server.py**

Remplacer la fonction `_setup` et `_insert_note` :

```python
def _setup():
    conn = sqlite3.connect(TEST_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY, dropbox_path TEXT NOT NULL,
            titre_court TEXT, insight_cle TEXT, resume TEXT,
            domaine TEXT, tags TEXT, date_capture TEXT, date_traitement TEXT,
            score_pertinence REAL DEFAULT 0.0,
            est_meta_fiche INTEGER DEFAULT 0,
            sources_ids TEXT, embedding BLOB,
            contenu_riche TEXT, titre_modifie INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.commit()
    conn.close()


def _insert_note(domaine="Apprentissage", score=0.5, est_meta=0, contenu_riche=None):
    nid  = hashlib.md5(f"{time.time()}".encode()).hexdigest()
    conn = sqlite3.connect(TEST_DB)
    conn.execute("""
        INSERT INTO notes
          (id, dropbox_path, titre_court, insight_cle, resume, domaine, tags,
           date_capture, date_traitement, score_pertinence, est_meta_fiche,
           sources_ids, embedding, contenu_riche, titre_modifie)
        VALUES (?,?,?,?,?,?,?,datetime('now'),datetime('now'),?,?,NULL,NULL,?,0)
    """, (nid, f"/test/{nid}.md", "Titre Test", "Insight.", "Résumé.",
          domaine, "", score, est_meta,
          contenu_riche or '{}'))
    conn.commit()
    conn.close()
    return nid
```

- [ ] **Step 2 : Écrire les tests qui échouent**

Ajouter à `tests/test_brain_server.py` :

```python
from unittest.mock import patch, MagicMock


def test_contenu_riche_in_notes_response():
    cr = '{"url_source":"https://example.com","points_cles":["p1"],"pourquoi_garder":"ok","quand_ressortir":"now"}'
    _insert_note(contenu_riche=cr)
    resp = client.get("/notes?limit=200")
    assert resp.status_code == 200
    notes = resp.json()
    assert any(n.get("contenu_riche") for n in notes)


def test_delete_note_removes_from_db():
    nid = _insert_note()
    with patch("brain_server.get_dropbox") as mock_dbx:
        mock_dbx.return_value.files_delete_v2 = MagicMock()
        resp = client.delete(f"/notes/{nid}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == nid
    conn = sqlite3.connect(TEST_DB)
    assert conn.execute("SELECT id FROM notes WHERE id = ?", (nid,)).fetchone() is None
    conn.close()


def test_delete_meta_skips_dropbox():
    nid = _insert_note(est_meta=1)
    with patch("brain_server.get_dropbox") as mock_dbx:
        resp = client.delete(f"/notes/{nid}")
    assert resp.status_code == 200
    mock_dbx.assert_not_called()


def test_patch_note_titre():
    nid = _insert_note()
    resp = client.patch(f"/notes/{nid}", json={"titre_court": "Nouveau Titre"})
    assert resp.status_code == 200
    conn = sqlite3.connect(TEST_DB)
    row = conn.execute(
        "SELECT titre_court, titre_modifie FROM notes WHERE id = ?", (nid,)
    ).fetchone()
    assert row[0] == "Nouveau Titre"
    assert row[1] == 1
    conn.close()
```

- [ ] **Step 3 : Vérifier que les tests échouent**

```bash
python -m pytest tests/test_brain_server.py::test_contenu_riche_in_notes_response tests/test_brain_server.py::test_delete_note_removes_from_db tests/test_brain_server.py::test_delete_meta_skips_dropbox tests/test_brain_server.py::test_patch_note_titre -v
```

Expected : 4 FAILED

- [ ] **Step 4 : Mettre à jour brain_server.py**

En haut du fichier, ajouter `get_dropbox` à l'import :

```python
from brain_agent import init_db as _init_db, get_dropbox
```

Mettre à jour `_SELECT_FIELDS` :

```python
_SELECT_FIELDS = (
    "id, dropbox_path, titre_court, insight_cle, resume, "
    "domaine, tags, date_capture, score_pertinence, est_meta_fiche, "
    "sources_ids, contenu_riche, titre_modifie"
)
```

Ajouter les deux endpoints après `get_a_la_une` :

```python
@app.delete("/notes/{note_id}")
def delete_note(note_id: str):
    from fastapi import HTTPException
    conn = get_db()
    row = conn.execute(
        "SELECT dropbox_path, est_meta_fiche FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Note introuvable")

    if not row["est_meta_fiche"] and row["dropbox_path"]:
        try:
            get_dropbox().files_delete_v2(row["dropbox_path"])
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=502, detail=f"Erreur Dropbox : {e}")

    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return {"deleted": note_id}


@app.patch("/notes/{note_id}")
def patch_note(note_id: str, body: dict):
    from fastapi import HTTPException
    titre = body.get("titre_court", "").strip()
    if not titre:
        raise HTTPException(status_code=422, detail="titre_court requis")
    conn = get_db()
    conn.execute(
        "UPDATE notes SET titre_court = ?, titre_modifie = 1 WHERE id = ?",
        (titre, note_id)
    )
    conn.commit()
    conn.close()
    return {"updated": note_id, "titre_court": titre}
```

- [ ] **Step 5 : Vérifier que les tests passent**

```bash
python -m pytest tests/test_brain_server.py -v
```

Expected : tous PASSED (7 existants + 4 nouveaux = 11)

- [ ] **Step 6 : Commit**

```bash
git add brain_server.py tests/test_brain_server.py
git commit -m "feat: brain_server — contenu_riche, DELETE /notes Dropbox, PATCH titre"
```

---

### Task 3 : brain_app/preload.js — expose openUrl

**Files:**
- Modify: `brain_app/preload.js`

- [ ] **Step 1 : Réécrire brain_app/preload.js**

```javascript
const { contextBridge, shell } = require('electron');

contextBridge.exposeInMainWorld('BRAIN_API_URL', 'http://127.0.0.1:7842');
contextBridge.exposeInMainWorld('openUrl', (url) => {
  if (/^https?:\/\//.test(url)) shell.openExternal(url);
});
```

- [ ] **Step 2 : Vérifier la syntaxe**

```bash
node -e "require('./brain_app/preload.js')" 2>&1 || echo "syntax error"
```

Note : va échouer car `require('electron')` n'existe pas hors Electron — c'est normal. Vérifier juste qu'il n'y a pas d'erreur de syntaxe JS. Expected : `Error: Cannot find module 'electron'` (acceptable).

- [ ] **Step 3 : Commit**

```bash
cd C:\Users\yapa\second_cerveau
git add brain_app/preload.js
git commit -m "feat: preload.js — expose openUrl via shell.openExternal"
```

---

### Task 4 : brain_app/style.css — nouveaux styles

**Files:**
- Modify: `brain_app/style.css`

- [ ] **Step 1 : Ajouter les nouveaux styles à la fin de style.css (avant `.hidden`)**

Trouver la ligne `.hidden { display: none !important; }` et insérer AVANT :

```css
/* ============================================================
   Source link, Points clés, Suppression, Titre éditable
   ============================================================ */
.source-link {
  display: inline-flex; align-items: center; gap: 5px;
  font-family: var(--font-mono); font-size: 10.5px;
  color: var(--ink-3); cursor: pointer; margin-bottom: 6px;
  background: none; border: none; padding: 0;
  transition: color .2s var(--ease); text-decoration: none;
}
.source-link:hover { color: var(--ink-2); }

.points-cles {
  list-style: none; padding: 0; margin: 0;
  display: flex; flex-direction: column; gap: 6px;
}
.points-cles li {
  display: flex; gap: 8px;
  font-size: 13px; line-height: 1.5; color: var(--ink-2);
}
.points-cles li::before { content: "•"; color: var(--accent); flex: 0 0 auto; }

.deletebtn {
  background: none; border: none; cursor: pointer;
  color: var(--ink-4); padding: 4px; border-radius: var(--r-sm);
  transition: color .2s var(--ease), background .2s var(--ease);
  display: flex; align-items: center; margin-left: 8px;
}
.deletebtn:hover {
  color: oklch(0.65 0.2 25);
  background: color-mix(in oklch, oklch(0.65 0.2 25) 12%, transparent);
}
.deletebtn svg { width: 14px; height: 14px; }

.title-editable {
  background: none; border: none; border-bottom: 1px solid var(--stroke);
  color: #fff; font-size: 23px; font-weight: 700; letter-spacing: -0.02em;
  font-family: var(--font-ui); width: 100%; padding: 2px 0;
  outline: none; cursor: text;
}
.title-editable:focus { border-bottom-color: var(--accent); }
```

- [ ] **Step 2 : Commit**

```bash
cd C:\Users\yapa\second_cerveau
git add brain_app/style.css
git commit -m "feat: style.css — source-link, points-cles, deletebtn, title-editable"
```

---

### Task 5 : brain_app/renderer.js — modal enrichie + suppression animée + titre éditable

**Files:**
- Modify: `brain_app/renderer.js`

- [ ] **Step 1 : Mettre à jour `mapNote` pour parser `contenu_riche`**

Remplacer la fonction `mapNote` existante par :

```javascript
function mapNote(raw) {
  const cr = (() => {
    try { return JSON.parse(raw.contenu_riche || '{}'); }
    catch { return {}; }
  })();
  return {
    ...raw,
    id: String(raw.id),
    titre: raw.titre_court || '—',
    insight: raw.insight_cle || '',
    est_meta: Boolean(raw.est_meta_fiche),
    liens: parseLiens(raw.sources_ids),
    parsedTags: parseTags(raw.tags),
    _days: daysAgo(raw.date_capture),
    url_source:     cr.url_source     || null,
    points_cles:    Array.isArray(cr.points_cles) ? cr.points_cles : [],
    pourquoi_garder: cr.pourquoi_garder || null,
    quand_ressortir: cr.quand_ressortir || null,
    titre_modifie:  Boolean(raw.titre_modifie),
  };
}
```

- [ ] **Step 2 : Ajouter les icônes `trash` et `externalLink` dans `ICONS`**

Ajouter dans l'objet `ICONS` (après `arrowLeft`) :

```javascript
  trash: `<svg viewBox="0 0 24 24" fill="none" width="14" height="14">
    <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  externalLink: `<svg viewBox="0 0 24 24" fill="none" width="12" height="12">
    <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
```

- [ ] **Step 3 : Ajouter `deleteNote` et `patchTitre` avant `renderModal`**

```javascript
async function deleteNote(note) {
  // 1. Animer modal out
  const modalEl = document.querySelector('#modal-scrim .modal');
  const scrimEl = document.getElementById('modal-scrim');
  if (modalEl) await animate(modalEl, { scale: [1, 0.95], opacity: [1, 0], duration: 280, ease: 'outQuart' }).finished;
  if (scrimEl) await animate(scrimEl, { opacity: [1, 0], duration: 200, ease: 'outQuart' }).finished;

  // 2. Animer la card dans la grille
  const card = document.querySelector(`[data-id="${note.id}"]`);
  if (card) await animate(card, { translateX: [0, -12], opacity: [1, 0], duration: 220, ease: 'outCubic' }).finished;

  // 3. Appel API DELETE
  try {
    const resp = await fetch(`${API}/notes/${note.id}`, { method: 'DELETE' });
    if (!resp.ok) {
      const err = await resp.json();
      alert(`Suppression impossible : ${err.detail || resp.status}`);
      render();
      return;
    }
  } catch {
    alert('Serveur non disponible.');
    render();
    return;
  }

  // 4. Mettre à jour le state
  setState({
    openNote: null,
    notes:    state.notes.filter(n => n.id !== note.id),
    featured: state.featured.filter(n => n.id !== note.id),
  });
}

async function patchTitre(note, newTitre) {
  if (!newTitre.trim() || newTitre === note.titre) return;
  try {
    const resp = await fetch(`${API}/notes/${note.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ titre_court: newTitre.trim() }),
    });
    if (!resp.ok) return;
    // Mettre à jour le state localement
    const update = n => n.id === note.id ? { ...n, titre: newTitre.trim(), titre_modifie: true } : n;
    setState({
      notes:    state.notes.map(update),
      featured: state.featured.map(update),
      openNote: state.openNote?.id === note.id ? { ...state.openNote, titre: newTitre.trim() } : state.openNote,
    });
  } catch { /* silencieux */ }
}
```

- [ ] **Step 4 : Remplacer `renderModal` par la version enrichie**

Remplacer la fonction `renderModal()` complète par :

```javascript
function renderModal() {
  const panel = document.getElementById('panel');
  const existing = document.getElementById('modal-scrim');
  if (existing) existing.remove();
  if (!state.openNote) return;

  const note = state.openNote;
  const dom  = domainConfig(note.domaine);
  const list = state.filteredList;
  const idx  = Math.max(0, list.findIndex(n => n.id === note.id));
  const total = list.length;
  const scoreW = Math.round((note.score_pertinence || 0) * 100);

  const linkedNotes = note.liens.map(id => state.notes.find(n => n.id === id)).filter(Boolean);
  const linkedLabel = note.est_meta ? 'Notes sources' : 'Notes liées';

  const tagsHtml = note.parsedTags.length
    ? `<div class="blocklabel">Tags</div><div class="tags">${note.parsedTags.map(t => `<span class="tagpill">#${t}</span>`).join('')}</div>`
    : '';

  const linkedHtml = linkedNotes.length
    ? `<div class="blocklabel">${linkedLabel} · ${linkedNotes.length}</div>
       <div class="linked">${linkedNotes.map(l => {
         const ldom = domainConfig(l.domaine);
         return `<button class="lrow" data-linked="${l.id}" style="--accent:${ldom.color}"><span class="ddot"></span><span class="lt">${l.titre}</span>${ICONS.arrow}</button>`;
       }).join('')}</div>`
    : '';

  const pointsHtml = note.points_cles.length
    ? `<div class="blocklabel">Points clés</div>
       <ul class="points-cles">${note.points_cles.map(p => `<li>${p}</li>`).join('')}</ul>`
    : '';

  const pourquoiHtml = note.pourquoi_garder
    ? `<div class="blocklabel">Pourquoi garder</div><div class="resume">${note.pourquoi_garder}</div>`
    : '';

  const quandHtml = note.quand_ressortir
    ? `<div class="blocklabel">Quand ressortir</div><div class="resume">${note.quand_ressortir}</div>`
    : '';

  const sourceLinkHtml = note.url_source
    ? `<button class="source-link" id="modal-source-link">${ICONS.externalLink} Ouvrir la source</button>`
    : '';

  panel.insertAdjacentHTML('beforeend', `
    <div class="scrim" id="modal-scrim">
      <div class="modal" style="--accent:${dom.color}">
        <div class="mhead">
          <div class="au"><div class="a1"></div><div class="a2"></div><div class="a3"></div></div>
          <div class="grain"></div>
          <button class="navbtn prev" id="modal-prev">${ICONS.arrowLeft}</button>
          <button class="navbtn next" id="modal-next">${ICONS.arrow}</button>
          <button class="closebtn" id="modal-close">${ICONS.close}</button>
          <div class="htext">
            <div class="domrow"><span class="ddot"></span><span class="domlabel">${note.est_meta ? 'Synthèse · ' : ''}${dom.label}</span></div>
            ${sourceLinkHtml}
            <h2 id="modal-title" class="title-editable" contenteditable="true" spellcheck="false">${note.titre}</h2>
          </div>
        </div>
        <div class="mbody">
          <div class="insight-box"><div class="bar"></div><div class="it">${note.insight}</div></div>
          <div class="blocklabel">Résumé</div>
          <div class="resume">${note.resume || ''}</div>
          ${pointsHtml}
          ${pourquoiHtml}
          ${quandHtml}
          ${tagsHtml}
          ${linkedHtml}
          <div class="mfoot">
            <span class="metatime">${relTime(note._days)}</span>
            <span class="metatime">· ${String(idx + 1).padStart(2, '0')} / ${String(total).padStart(2, '0')}</span>
            <div class="scoremeter">
              <span class="metatime">pertinence</span>
              <div class="track"><div class="fill" style="width:${scoreW}%"></div></div>
              <span class="metatime">${(note.score_pertinence || 0).toFixed(2)}</span>
            </div>
            <button class="deletebtn" id="modal-delete" title="Supprimer cette note">${ICONS.trash}</button>
          </div>
        </div>
      </div>
    </div>
  `);

  const scrim = document.getElementById('modal-scrim');

  // Fermeture
  scrim.addEventListener('click', e => { if (e.target === scrim) closeModal(); });
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-prev').addEventListener('click', () => navModal(-1));
  document.getElementById('modal-next').addEventListener('click', () => navModal(1));

  // URL source
  const srcBtn = document.getElementById('modal-source-link');
  if (srcBtn && note.url_source) {
    srcBtn.addEventListener('click', () => window.openUrl(note.url_source));
  }

  // Suppression
  document.getElementById('modal-delete').addEventListener('click', () => deleteNote(note));

  // Titre éditable — save on blur ou Enter
  const titleEl = document.getElementById('modal-title');
  titleEl.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); titleEl.blur(); }
    if (e.key === 'Escape') { titleEl.textContent = note.titre; titleEl.blur(); }
  });
  titleEl.addEventListener('blur', () => patchTitre(note, titleEl.textContent.trim()));

  // Navigation notes liées
  scrim.querySelectorAll('[data-linked]').forEach(btn => {
    btn.addEventListener('click', () => {
      const linked = state.notes.find(n => n.id === btn.dataset.linked);
      if (linked) setState({ openNote: linked });
    });
  });
}
```

- [ ] **Step 5 : Lancer le serveur et tester manuellement**

Dans un terminal :
```bash
cd C:\Users\yapa\second_cerveau
python -m uvicorn brain_server:app --host 127.0.0.1 --port 7842
```

Dans un autre :
```bash
cd C:\Users\yapa\second_cerveau\brain_app
npx electron .
```

Expected :
- Clic sur une card → modale s'ouvre
- Si la note a des `points_cles` → section "Points clés" avec bullets
- Si `url_source` → bouton "↗ Ouvrir la source" → ouvre dans le navigateur
- Titre cliquable → devient éditable → Enter/blur → sauvegarde (vérifie dans DevTools Network : PATCH /notes/{id})
- Icône 🗑️ → animation modale + card → note disparaît
- Erreur Dropbox → alert "Suppression impossible"

- [ ] **Step 6 : Vérifier les tests existants**

```bash
cd C:\Users\yapa\second_cerveau
python -m pytest tests/ -v
```

Expected : 21 passed (19 agent + 11 server - chevauchement possible = vérifier que rien ne régresse)

- [ ] **Step 7 : Commit**

```bash
cd C:\Users\yapa\second_cerveau
git add brain_app/renderer.js
git commit -m "feat: renderer.js — modal enrichie, suppression Dropbox animée, titre éditable"
```

---

**Plan 4 terminé.** Lancer ensuite `python brain_agent.py --reprocess` pour re-traiter les notes existantes avec le nouveau prompt.

## Self-Review

**Spec coverage :**
- ✅ `contenu_riche TEXT` + `titre_modifie INTEGER` — Task 1 `init_db`
- ✅ Nouveau prompt GPT-4.1, `max_tokens=1200`, extraction POINTS_CLES — Task 1 `_PROMPT_RAFFINEMENT`
- ✅ Flag `--reprocess` (skip domaine Travail) — Task 1 `__main__`
- ✅ `titre_modifie` protège le titre sur re-process — Task 1 `run_agent`
- ✅ `contenu_riche` dans `_SELECT_FIELDS` — Task 2
- ✅ `DELETE /notes/{id}` → Dropbox d'abord puis DB, méta-fiche skip Dropbox — Task 2
- ✅ `PATCH /notes/{id}` → `titre_court` + `titre_modifie=1` — Task 2
- ✅ `openUrl` via `shell.openExternal` — Task 3
- ✅ `.source-link`, `.points-cles`, `.deletebtn`, `.title-editable` — Task 4
- ✅ `mapNote` parse `contenu_riche` — Task 5
- ✅ `deleteNote` avec animation Anime.js (modal + card) — Task 5
- ✅ `patchTitre` PATCH API + state update — Task 5
- ✅ `renderModal` : source link, points clés, pourquoi garder, quand ressortir, titre éditable, bouton delete — Task 5

**Placeholder scan :** Aucun.

**Type consistency :**
- `note.id` → `String` partout via `mapNote` ✅
- `note.points_cles` → toujours `Array` (normalisé dans `raffiner_note` et `mapNote`) ✅
- `deleteNote(note)` → reçoit un objet note mappé ✅
- `patchTitre(note, newTitre)` → reçoit l'objet note + string ✅
