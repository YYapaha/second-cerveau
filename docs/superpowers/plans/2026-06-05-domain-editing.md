# Domain Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Statut : ✅ TERMINÉ — 2026-06-06 — 108 tests verts**

**Goal:** Allow renaming domains and changing their dot color directly from the Electron UI, persisted in a SQLite `domains` table.

**Architecture:** New `domains(name, color, position)` table seeded at `init_db()`. Two new API endpoints (`GET /domains`, `PATCH /domains/{name}`) replace hardcoded lists. Frontend loads domains dynamically at startup; filter pills get inline rename (double-click label) and color picker (click dot).

**Bug post-implémentation résolu :** le `dblclick` ne se déclenchait jamais car `setState` appelle `render()` inconditionnellement, reconstruisant le DOM entre les deux clicks d'un double-clic. Remplacé par un compteur de clicks manuel (`_labelClickTimer` / `_labelClickDomain`) au niveau module, qui track le nom de domaine (string) plutôt qu'une référence d'élément. Voir `docs/superpowers/lessons-learned.md`.

**Tech Stack:** Python + FastAPI + SQLite, vanilla JS + anime.js, Electron.

---

## File Map

| File | Change |
|------|--------|
| `brain_agent.py` | Add `domains` table + seed in `init_db()` |
| `brain_server.py` | Add `GET /domains`, `PATCH /domains/{name}`; update `patch_note()` validation |
| `tests/test_brain_agent.py` | Add 2 migration tests |
| `tests/test_brain_server.py` | Update `_setup()` to use `init_db()`; add domain endpoint tests |
| `brain_app/renderer.js` | Dynamic domain loading; color picker; inline rename |

---

## Task 1: DB Migration — `domains` table

**Files:**
- Modify: `brain_agent.py:29-66`
- Test: `tests/test_brain_agent.py`

- [ ] **Step 1: Write the failing tests**

Add at bottom of `tests/test_brain_agent.py`:

```python
def test_init_db_creates_domains_table():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        from brain_agent import init_db
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "domains" in tables
        rows = conn.execute(
            "SELECT name, color, position FROM domains ORDER BY position"
        ).fetchall()
        assert len(rows) == 7
        assert rows[0][0] == "Travail"
        assert rows[6][0] == "À trier"
        assert all(r[1].startswith("#") for r in rows)
        conn.close()
    finally:
        os.unlink(db_path)


def test_init_db_domains_idempotent():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        from brain_agent import init_db
        init_db(db_path)
        init_db(db_path)  # second call must not duplicate
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
        assert count == 7
        conn.close()
    finally:
        os.unlink(db_path)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
cd c:\Users\yapa\second_cerveau
python -m pytest tests/test_brain_agent.py::test_init_db_creates_domains_table tests/test_brain_agent.py::test_init_db_domains_idempotent -v
```

Expected: FAIL — `domains` table doesn't exist yet.

- [ ] **Step 3: Add `domains` table to `init_db()` in `brain_agent.py`**

In `brain_agent.py`, find the `conn.executescript("""...""")` block inside `init_db()` (around line 32) and add the `domains` table to it. Then add the seed block right after the existing `ALTER TABLE` migration loop:

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
            CREATE TABLE IF NOT EXISTS domains (
                name     TEXT PRIMARY KEY,
                color    TEXT NOT NULL,
                position INTEGER NOT NULL
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
        # Seed domains if empty
        if not conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0]:
            conn.executemany(
                "INSERT INTO domains (name, color, position) VALUES (?,?,?)",
                [
                    ("Travail",           "#d4b96a", 0),
                    ("Apprentissage",     "#7aa0d4", 1),
                    ("Projets perso",     "#d47a6a", 2),
                    ("Jeux vidéos",       "#c87ad4", 3),
                    ("Plantes",           "#7ac88a", 4),
                    ("Organisation TDAH", "#7ac8c8", 5),
                    ("À trier",           "#c8b87a", 6),
                ]
            )
            conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to confirm they pass**

```
python -m pytest tests/test_brain_agent.py::test_init_db_creates_domains_table tests/test_brain_agent.py::test_init_db_domains_idempotent -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite to check no regressions**

```
python -m pytest tests/ -v
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```
git add brain_agent.py tests/test_brain_agent.py
git commit -m "feat: add domains table to DB with seed data"
```

---

## Task 2: `GET /domains` endpoint

**Files:**
- Modify: `brain_server.py`
- Test: `tests/test_brain_server.py`

- [ ] **Step 1: Update `_setup()` in `test_brain_server.py` to use `init_db()`**

Replace the existing `_setup()` function (lines 8-23) with:

```python
def _setup():
    from brain_agent import init_db
    init_db(TEST_DB)
```

This gives the test DB all tables including `domains` with the 7 seeded rows.

- [ ] **Step 2: Write the failing test**

Add at bottom of `tests/test_brain_server.py`:

```python
# /domains tests
def test_get_domains_returns_7_sorted():
    resp = client.get("/domains")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 7
    positions = [d["position"] for d in data]
    assert positions == sorted(positions)
    assert data[0]["name"] == "Travail"
    assert all("name" in d and "color" in d and "position" in d for d in data)
    assert all(d["color"].startswith("#") for d in data)
```

- [ ] **Step 3: Run test to confirm it fails**

```
python -m pytest tests/test_brain_server.py::test_get_domains_returns_7_sorted -v
```

Expected: FAIL — endpoint doesn't exist yet (404).

- [ ] **Step 4: Add `GET /domains` to `brain_server.py`**

Add this route after the `@app.get("/status")` block (before `@app.get("/notes")`):

```python
@app.get("/domains")
def get_domains():
    conn = get_db()
    rows = conn.execute(
        "SELECT name, color, position FROM domains ORDER BY position"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 5: Run test to confirm it passes**

```
python -m pytest tests/test_brain_server.py::test_get_domains_returns_7_sorted -v
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

```
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```
git add brain_server.py tests/test_brain_server.py
git commit -m "feat: add GET /domains endpoint"
```

---

## Task 3: `PATCH /domains/{name}` endpoint

**Files:**
- Modify: `brain_server.py`
- Test: `tests/test_brain_server.py`

- [ ] **Step 1: Write the failing tests**

Add at bottom of `tests/test_brain_server.py` (after `test_get_domains_returns_7_sorted`):

```python
def test_patch_domain_color_only():
    resp = client.patch("/domains/Apprentissage", json={"color": "#ff0000"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Apprentissage"
    assert data["color"] == "#ff0000"
    conn = sqlite3.connect(TEST_DB)
    row = conn.execute("SELECT color FROM domains WHERE name='Apprentissage'").fetchone()
    assert row[0] == "#ff0000"
    conn.close()


def test_patch_domain_rename_cascades_notes():
    nid = _insert_note(domaine="Jeux vidéos")
    resp = client.patch("/domains/Jeux vidéos", json={"name": "Jeux vidéos modifié"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Jeux vidéos modifié"
    conn = sqlite3.connect(TEST_DB)
    assert conn.execute(
        "SELECT name FROM domains WHERE name='Jeux vidéos modifié'"
    ).fetchone() is not None
    assert conn.execute(
        "SELECT name FROM domains WHERE name='Jeux vidéos'"
    ).fetchone() is None
    assert conn.execute(
        "SELECT domaine FROM notes WHERE id=?", (nid,)
    ).fetchone()[0] == "Jeux vidéos modifié"
    conn.close()


def test_patch_domain_name_and_color():
    resp = client.patch("/domains/Organisation TDAH", json={"name": "TDAH", "color": "#aabbcc"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "TDAH"
    assert data["color"] == "#aabbcc"


def test_patch_domain_no_fields_422():
    resp = client.patch("/domains/Plantes", json={})
    assert resp.status_code == 422


def test_patch_domain_empty_name_422():
    resp = client.patch("/domains/Plantes", json={"name": ""})
    assert resp.status_code == 422


def test_patch_domain_a_trier_rename_400():
    resp = client.patch("/domains/À trier", json={"name": "Autre"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "cannot_rename_default_domain"


def test_patch_domain_duplicate_name_409():
    resp = client.patch("/domains/Plantes", json={"name": "Apprentissage"})
    assert resp.status_code == 409


def test_patch_domain_unknown_404():
    resp = client.patch("/domains/Inexistant", json={"color": "#ff0000"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to confirm they all fail**

```
python -m pytest tests/test_brain_server.py::test_patch_domain_color_only tests/test_brain_server.py::test_patch_domain_rename_cascades_notes tests/test_brain_server.py::test_patch_domain_name_and_color tests/test_brain_server.py::test_patch_domain_no_fields_422 tests/test_brain_server.py::test_patch_domain_empty_name_422 tests/test_brain_server.py::test_patch_domain_a_trier_rename_400 tests/test_brain_server.py::test_patch_domain_duplicate_name_409 tests/test_brain_server.py::test_patch_domain_unknown_404 -v
```

Expected: all FAIL (404 — endpoint not found).

- [ ] **Step 3: Add `PATCH /domains/{name}` to `brain_server.py`**

Add after `@app.get("/domains")`:

```python
@app.patch("/domains/{name}")
def patch_domain(name: str, body: dict):
    new_name  = body.get("name", "").strip() if "name" in body else None
    new_color = body.get("color", "").strip() if "color" in body else None

    if new_name is None and new_color is None:
        raise HTTPException(status_code=422, detail="name ou color requis")
    if new_name is not None and new_name == "":
        raise HTTPException(status_code=422, detail="name ne peut pas être vide")

    conn = get_db()
    row = conn.execute("SELECT name, color, position FROM domains WHERE name = ?", (name,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="domaine inconnu")

    if new_name is not None and new_name != name:
        if name == "À trier":
            conn.close()
            raise HTTPException(status_code=400, detail=None, headers=None)
        conflict = conn.execute("SELECT name FROM domains WHERE name = ?", (new_name,)).fetchone()
        if conflict:
            conn.close()
            raise HTTPException(status_code=409, detail="ce nom existe déjà")

    try:
        if new_name is not None and new_name != name:
            conn.execute("UPDATE domains SET name = ? WHERE name = ?", (new_name, name))
            conn.execute("UPDATE notes SET domaine = ? WHERE domaine = ?", (new_name, name))
        if new_color is not None:
            effective_name = new_name if (new_name and new_name != name) else name
            conn.execute("UPDATE domains SET color = ? WHERE name = ?", (new_color, effective_name))
        conn.commit()
        final = conn.execute(
            "SELECT name, color, position FROM domains WHERE name = ?",
            (new_name if (new_name and new_name != name) else name,)
        ).fetchone()
        conn.close()
        return dict(final)
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
```

Note: the 400 for "À trier" needs to return `{"error": "cannot_rename_default_domain"}`. Replace that raise with:

```python
        from fastapi.responses import JSONResponse
        conn.close()
        return JSONResponse(status_code=400, content={"error": "cannot_rename_default_domain"})
```

Full corrected version of the `if name == "À trier"` block:

```python
    if new_name is not None and new_name != name:
        if name == "À trier":
            conn.close()
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=400, content={"error": "cannot_rename_default_domain"})
        conflict = conn.execute("SELECT name FROM domains WHERE name = ?", (new_name,)).fetchone()
        if conflict:
            conn.close()
            raise HTTPException(status_code=409, detail="ce nom existe déjà")
```

- [ ] **Step 4: Run tests to confirm they all pass**

```
python -m pytest tests/test_brain_server.py::test_patch_domain_color_only tests/test_brain_server.py::test_patch_domain_rename_cascades_notes tests/test_brain_server.py::test_patch_domain_name_and_color tests/test_brain_server.py::test_patch_domain_no_fields_422 tests/test_brain_server.py::test_patch_domain_empty_name_422 tests/test_brain_server.py::test_patch_domain_a_trier_rename_400 tests/test_brain_server.py::test_patch_domain_duplicate_name_409 tests/test_brain_server.py::test_patch_domain_unknown_404 -v
```

Expected: all PASS.

- [ ] **Step 5: Run full test suite**

```
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```
git add brain_server.py tests/test_brain_server.py
git commit -m "feat: add PATCH /domains/{name} endpoint with cascade rename"
```

---

## Task 4: Update `patch_note()` to validate against DB

**Files:**
- Modify: `brain_server.py:13,219`
- Test: `tests/test_brain_server.py`

Context: `patch_note()` currently validates `domaine` against `VALID_DOMAINS` (the static Python list). After domain renames, the DB is authoritative. We need to query it instead.

- [ ] **Step 1: Write the failing test**

Add at bottom of `tests/test_brain_server.py`:

```python
def test_patch_note_with_renamed_domain_valid():
    """After a rename, patching a note to the new name must succeed."""
    # "Jeux vidéos modifié" was created in test_patch_domain_rename_cascades_notes
    nid = _insert_note(domaine="Apprentissage")
    resp = client.patch(f"/notes/{nid}", json={"domaine": "Jeux vidéos modifié"})
    assert resp.status_code == 200
    conn = sqlite3.connect(TEST_DB)
    assert conn.execute("SELECT domaine FROM notes WHERE id=?", (nid,)).fetchone()[0] == "Jeux vidéos modifié"
    conn.close()
```

- [ ] **Step 2: Run test to confirm it fails**

```
python -m pytest tests/test_brain_server.py::test_patch_note_with_renamed_domain_valid -v
```

Expected: FAIL — "Jeux vidéos modifié" is not in the hardcoded `VALID_DOMAINS` list → 422.

- [ ] **Step 3: Update the import and validation in `brain_server.py`**

Change line 13 — remove `DOMAINS as VALID_DOMAINS` from the import:

```python
from brain_agent import init_db as _init_db, get_dropbox
```

In `patch_note()` (around line 219), replace:

```python
    if domaine and domaine not in VALID_DOMAINS:
        raise HTTPException(status_code=422, detail=f"domaine invalide : {domaine}")
```

with:

```python
    if domaine:
        conn_v = get_db()
        valid  = {r["name"] for r in conn_v.execute("SELECT name FROM domains").fetchall()}
        conn_v.close()
        if domaine not in valid:
            raise HTTPException(status_code=422, detail=f"domaine invalide : {domaine}")
```

- [ ] **Step 4: Run the new test to confirm it passes**

```
python -m pytest tests/test_brain_server.py::test_patch_note_with_renamed_domain_valid -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite**

```
python -m pytest tests/ -v
```

Expected: all tests pass (existing `test_patch_note_domaine_invalide_422` still passes because "DomaineInconnu" is not in the DB).

- [ ] **Step 6: Commit**

```
git add brain_server.py tests/test_brain_server.py
git commit -m "feat: validate patch_note domain against DB instead of hardcoded list"
```

---

## Task 5: Frontend — dynamic domain loading

**Files:**
- Modify: `brain_app/renderer.js:8-18, 995-1001`

- [ ] **Step 1: Change `const DOMAINS` and `const DOMAIN_ORDER` to `let`**

In `renderer.js`, replace lines 8-17:

```js
let DOMAINS = {
  'Travail':           { key: 'travail',       label: 'Travail',       color: 'var(--d-travail)' },
  'Apprentissage':     { key: 'apprentissage', label: 'Apprentissage', color: 'var(--d-apprentissage)' },
  'Projets perso':     { key: 'projets',       label: 'Projets perso', color: 'var(--d-projets)' },
  'Jeux vidéos':       { key: 'jeux',          label: 'Jeux vidéos',   color: 'var(--d-jeux)' },
  'Plantes':           { key: 'plantes',       label: 'Plantes',       color: 'var(--d-plantes)' },
  'Organisation TDAH': { key: 'tdah',          label: 'Organisation',  color: 'var(--d-tdah)' },
  'À trier': { key: 'trier', label: 'À trier', color: 'var(--d-trier)' },
};
let DOMAIN_ORDER = ['Travail', 'Apprentissage', 'Projets perso', 'Jeux vidéos', 'Plantes', 'Organisation TDAH', 'À trier'];
```

- [ ] **Step 2: Add `loadDomains()` function**

Add after the `domainConfig()` function (around line 155):

```js
async function loadDomains() {
  try {
    const data = await fetch(`${API}/domains`).then(r => r.json());
    DOMAIN_ORDER = data.map(d => d.name);
    DOMAINS = {};
    data.forEach(d => {
      DOMAINS[d.name] = { key: d.name.toLowerCase().replace(/\s+/g, '_'), label: d.name, color: d.color };
    });
  } catch {
    // keep fallback hardcoded values — server may not be ready yet
  }
}
```

- [ ] **Step 3: Call `loadDomains()` before `loadData()` in the init IIFE**

In the IIFE at the bottom (around line 995-1001), replace:

```js
(async () => {
  render();
  initChat();
  initBlocsResize();
  initZen();
  await loadData(false);
```

with:

```js
(async () => {
  render();
  initChat();
  initBlocsResize();
  initZen();
  await loadDomains();
  await loadData(false);
```

- [ ] **Step 4: Start the Electron app and verify domains load**

```
cd c:\Users\yapa\second_cerveau
python brain_server.py &
# then open the Electron app or run:
# npx electron brain_app/main.js
```

Open the app. Filter pills should show domain names with hex-based colors (dots may look slightly different in color from the CSS-var version — that's expected and correct).

- [ ] **Step 5: Commit**

```
git add brain_app/renderer.js
git commit -m "feat: load domains dynamically from API at startup"
```

---

## Task 6: Frontend — color picker on filter pill dots

**Files:**
- Modify: `brain_app/renderer.js` — `renderFilters()`, new `patchDomain()` function

- [ ] **Step 1: Add `patchDomain()` helper function**

Add after the existing `patchDomaine()` function (around line 444):

```js
async function patchDomain(currentName, updates) {
  const pill = document.querySelector(`.fpill[data-filter="${CSS.escape(currentName)}"]`);
  const dot  = pill?.querySelector('.ddot');
  if (dot) animate(dot, { opacity: [0.4, 1], duration: 400, ease: 'outCubic' });

  try {
    const resp = await fetch(`${API}/domains/${encodeURIComponent(currentName)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!resp.ok) {
      if (pill) { pill.style.outline = '1px solid red'; setTimeout(() => { pill.style.outline = ''; }, 800); }
      return;
    }
    const updated = await resp.json();
    const oldName = currentName;
    if (updates.name && updates.name !== oldName) {
      const idx = DOMAIN_ORDER.indexOf(oldName);
      if (idx >= 0) DOMAIN_ORDER[idx] = updated.name;
      DOMAINS[updated.name] = { ...DOMAINS[oldName], label: updated.name, color: updated.color || DOMAINS[oldName].color };
      delete DOMAINS[oldName];
    } else {
      if (DOMAINS[oldName]) DOMAINS[oldName].color = updated.color;
    }
    render();
  } catch {
    if (pill) { pill.style.outline = '1px solid red'; setTimeout(() => { pill.style.outline = ''; }, 800); }
  }
}
```

- [ ] **Step 2: Update `renderFilters()` to add `data-domain` on dots and wrap label in a span**

In `renderFilters()` (around line 234), change the domain pill template from:

```js
return `<button class="fpill${activeFilter === d ? ' active' : ''}" data-filter="${d}" style="--accent:${dom.color}"><span class="ddot"></span>${dom.label}</button>`;
```

to:

```js
return `<button class="fpill${activeFilter === d ? ' active' : ''}" data-filter="${d}" style="--accent:${dom.color}"><span class="ddot" data-domain="${d}"></span><span class="dlabel"${d === 'À trier' ? ' data-locked="true"' : ''}>${dom.label}</span></button>`;
```

- [ ] **Step 3: Create shared color input once at module level**

Add this block right after the `loadDomains()` function definition (around line 165, before `renderFilters`):

```js
// ── Color picker (shared, initialized once) ───────────────────────────────────

const _colorInput = (() => {
  const inp = document.createElement('input');
  inp.type = 'color';
  inp.id = '_domain-color-input';
  inp.style.cssText = 'position:fixed;opacity:0;width:1px;height:1px;pointer-events:none;';
  document.body.appendChild(inp);
  return inp;
})();
let _colorTarget = null;

_colorInput.addEventListener('change', async () => {
  if (!_colorTarget) return;
  const target = _colorTarget;
  _colorTarget = null;
  _colorInput.style.pointerEvents = 'none';
  await patchDomain(target, { color: _colorInput.value });
});
```

- [ ] **Step 4: Add dot click wiring in `renderFilters()`**

After the existing event delegation block in `renderFilters()` (after `container.querySelectorAll('[data-filter]').forEach...`), add only the dot click listeners (the input and its `change` listener are already set up above):

```js
  container.querySelectorAll('.ddot[data-domain]').forEach(dot => {
    dot.addEventListener('click', e => {
      e.stopPropagation();
      _colorTarget = dot.dataset.domain;
      _colorInput.value = DOMAINS[_colorTarget]?.color?.startsWith('#')
        ? DOMAINS[_colorTarget].color
        : '#888888';
      const rect = dot.getBoundingClientRect();
      _colorInput.style.left = rect.left + 'px';
      _colorInput.style.top  = rect.bottom + 'px';
      _colorInput.style.pointerEvents = 'auto';
      _colorInput.click();
    });
  });
```

- [ ] **Step 4: Verify in the app**

Start the server and open the Electron app. Click a domain dot in the filter bar — a system color picker should appear. Choose a color — the dot updates immediately and the server persists it. Verify with `GET /domains` in a browser.

- [ ] **Step 5: Commit**

```
git add brain_app/renderer.js
git commit -m "feat: color picker on domain dots in filter bar"
```

---

## Task 7: Frontend — inline rename on filter pill labels

**Files:**
- Modify: `brain_app/renderer.js` — `renderFilters()`

- [ ] **Step 1: Add double-click rename event wiring in `renderFilters()`**

After the color picker block added in Task 6, add:

```js
  container.querySelectorAll('.dlabel').forEach(label => {
    if (label.dataset.locked) return;
    label.addEventListener('dblclick', e => {
      e.stopPropagation();
      const pill = label.closest('.fpill');
      const domainName = pill?.dataset.filter;
      if (!domainName) return;

      const original = label.textContent;
      const input = document.createElement('input');
      input.className = 'dlabel-input';
      input.value = original;
      input.style.cssText = `
        background: transparent; border: none; border-bottom: 1px solid var(--stroke-hi);
        color: inherit; font: inherit; width: ${Math.max(60, original.length * 8)}px;
        outline: none; padding: 0;
      `;
      label.replaceWith(input);
      input.focus();
      input.select();

      const confirm = async () => {
        if (!input.isConnected) return;  // guard: blur fires after Enter already removed the input
        const newName = input.value.trim();
        const span = document.createElement('span');
        span.className = 'dlabel';
        span.textContent = newName || original;
        input.replaceWith(span);
        if (newName && newName !== original) {
          await patchDomain(domainName, { name: newName });
        }
      };

      const cancel = () => {
        const span = document.createElement('span');
        span.className = 'dlabel';
        span.textContent = original;
        if (input.isConnected) input.replaceWith(span);
      };

      input.addEventListener('keydown', async e => {
        if (e.key === 'Enter')  { e.preventDefault(); await confirm(); }
        if (e.key === 'Escape') { cancel(); }
      });
      input.addEventListener('blur', confirm);
    });
  });
```

- [ ] **Step 2: Verify in the app**

Open the app. Double-click a domain label (e.g. "Plantes") in the filter bar — it becomes an editable input. Type a new name, press Enter — the pill updates and the server persists it. Verify the server response with `GET /domains`.

Try double-clicking "À trier" — nothing should happen (locked).

Try pressing Escape — the label reverts to the original name.

- [ ] **Step 3: Run full test suite one final time**

```
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Final commit**

```
git add brain_app/renderer.js
git commit -m "feat: inline rename for domain labels in filter bar"
```
