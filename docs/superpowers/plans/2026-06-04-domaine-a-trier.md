# Domaine "À trier" + Changement de domaine depuis la modale — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un 7e domaine "À trier" comme fallback LLM, remplacer la section "À la une" par une section de triage en haut de l'app, et permettre de changer le domaine d'une note en cliquant sur son label dans la modale.

**Architecture:** Backend : `brain_agent.py` (DOMAINS + fallback + prompt), `core.py` (PROMPT_ANALYSE), `brain_server.py` (PATCH étendu). Frontend : `renderer.js` (suppression de `state.featured`, `renderATrier()`, `patchDomaine()`, picker modal), `style.css` (token + picker styles), `index.html` (label + icône). La section "À trier" filtre `state.notes` côté client — aucun nouvel endpoint API.

**Tech Stack:** Python 3.11 / FastAPI / SQLite (backend), Vanilla JS ESM / animejs (frontend), pytest / httpx / FastAPI TestClient (tests)

---

## Fichiers touchés

| Fichier | Action |
|---------|--------|
| `brain_agent.py` | Modifier : DOMAINS list, fallback, _PROMPT_RAFFINEMENT |
| `core.py` | Modifier : PROMPT_ANALYSE (domaine enum ligne 76) |
| `brain_server.py` | Modifier : import DOMAINS, PATCH endpoint |
| `brain_app/style.css` | Modifier : token `--d-trier` + styles picker |
| `brain_app/renderer.js` | Modifier : DOMAINS, state, renderATrier, patchDomaine, picker modal |
| `brain_app/index.html` | Modifier : label + icône |
| `tests/test_brain_agent.py` | Modifier : 2 assertions fallback |
| `tests/test_brain_server.py` | Modifier : test PATCH existant + 5 nouveaux tests |

---

## Task 1 — brain_agent.py + core.py : domaine "À trier"

**Files:**
- Modify: `brain_agent.py:18-21` (DOMAINS), `brain_agent.py:130` (_PROMPT_RAFFINEMENT), `brain_agent.py:165-167` (fallback)
- Modify: `core.py:76` (PROMPT_ANALYSE)
- Test: `tests/test_brain_agent.py:216-227`

- [ ] **Étape 1 : Repérer les tests existants qui vont casser**

  ```bash
  cd c:\Users\yapa\second_cerveau
  python -m pytest tests/test_brain_agent.py::test_parser_note_domaine_invalide_fallback tests/test_brain_agent.py::test_parser_note_domaine_absent_fallback -v
  ```

  Ces deux tests assertent `== "Projets perso"`. Ils passent en vert maintenant — ils doivent casser après la modification.

- [ ] **Étape 2 : Mettre à jour les deux tests pour asserter "À trier"**

  Dans `tests/test_brain_agent.py`, remplacer :

  ```python
  # ligne ~220
  assert result["domaine"] == "Projets perso"

  # ligne ~227
  assert result["domaine"] == "Projets perso"
  ```

  par :

  ```python
  # ligne ~220
  assert result["domaine"] == "À trier"

  # ligne ~227
  assert result["domaine"] == "À trier"
  ```

- [ ] **Étape 3 : Vérifier que les tests cassent maintenant**

  ```bash
  python -m pytest tests/test_brain_agent.py::test_parser_note_domaine_invalide_fallback tests/test_brain_agent.py::test_parser_note_domaine_absent_fallback -v
  ```

  Attendu : 2 × FAIL — `assert 'Projets perso' == 'À trier'`

- [ ] **Étape 4 : Ajouter "À trier" à la liste DOMAINS dans brain_agent.py**

  Remplacer les lignes 18-21 :

  ```python
  DOMAINS      = [
      "Travail", "Apprentissage", "Projets perso",
      "Jeux vidéos", "Plantes", "Organisation TDAH",
  ]
  ```

  par :

  ```python
  DOMAINS      = [
      "Travail", "Apprentissage", "Projets perso",
      "Jeux vidéos", "Plantes", "Organisation TDAH", "À trier",
  ]
  ```

- [ ] **Étape 5 : Mettre à jour le fallback dans parser_note() (brain_agent.py lignes 165-167)**

  Remplacer :

  ```python
      domaine = extraire_champ(contenu, "DOMAINE")
      if domaine not in DOMAINS:
          domaine = "Projets perso"
  ```

  par :

  ```python
      domaine = extraire_champ(contenu, "DOMAINE")
      if domaine not in DOMAINS:
          domaine = "À trier"
  ```

- [ ] **Étape 6 : Mettre à jour _PROMPT_RAFFINEMENT dans brain_agent.py (ligne 130)**

  Remplacer :

  ```
    "domaine": "<exactement un parmi : Travail | Apprentissage | Projets perso | Jeux vidéos | Plantes | Organisation TDAH>",
  ```

  par :

  ```
    "domaine": "<exactement un parmi : Travail | Apprentissage | Projets perso | Jeux vidéos | Plantes | Organisation TDAH | À trier>",
  ```

- [ ] **Étape 7 : Mettre à jour PROMPT_ANALYSE dans core.py (ligne 76)**

  Remplacer :

  ```
  **DOMAINE** : [Travail|Apprentissage|Projets perso|Jeux vidéos|Plantes|Organisation TDAH]
  ```

  par :

  ```
  **DOMAINE** : [Travail|Apprentissage|Projets perso|Jeux vidéos|Plantes|Organisation TDAH|À trier]
  ```

- [ ] **Étape 8 : Vérifier que les tests passent**

  ```bash
  python -m pytest tests/test_brain_agent.py -v
  ```

  Attendu : tous verts.

- [ ] **Étape 9 : Lancer la suite complète**

  ```bash
  python -m pytest -v
  ```

  Attendu : toujours 71 tests verts (ou 71+ si des tests ont été ajoutés).

- [ ] **Étape 10 : Commit**

  ```bash
  git add brain_agent.py core.py tests/test_brain_agent.py
  git commit -m "feat: ajout domaine A trier — DOMAINS, fallback parser_note, prompts LLM"
  ```

---

## Task 2 — brain_server.py : PATCH étendu pour domaine

**Files:**
- Modify: `brain_server.py` (import + endpoint PATCH)
- Test: `tests/test_brain_server.py`

- [ ] **Étape 1 : Écrire les nouveaux tests (TDD)**

  Ajouter après `test_patch_note_titre` dans `tests/test_brain_server.py` :

  ```python
  def test_patch_note_domaine_valide():
      nid = _insert_note(domaine="Apprentissage")
      resp = client.patch(f"/notes/{nid}", json={"domaine": "Travail"})
      assert resp.status_code == 200
      conn = sqlite3.connect(TEST_DB)
      row = conn.execute("SELECT domaine FROM notes WHERE id = ?", (nid,)).fetchone()
      assert row[0] == "Travail"
      conn.close()


  def test_patch_note_domaine_a_trier():
      nid = _insert_note(domaine="Apprentissage")
      resp = client.patch(f"/notes/{nid}", json={"domaine": "À trier"})
      assert resp.status_code == 200
      conn = sqlite3.connect(TEST_DB)
      row = conn.execute("SELECT domaine FROM notes WHERE id = ?", (nid,)).fetchone()
      assert row[0] == "À trier"
      conn.close()


  def test_patch_note_domaine_invalide_422():
      nid = _insert_note()
      resp = client.patch(f"/notes/{nid}", json={"domaine": "DomaineInconnu"})
      assert resp.status_code == 422


  def test_patch_note_ni_titre_ni_domaine_422():
      nid = _insert_note()
      resp = client.patch(f"/notes/{nid}", json={})
      assert resp.status_code == 422


  def test_patch_note_titre_et_domaine_ensemble():
      nid = _insert_note(domaine="Plantes")
      resp = client.patch(
          f"/notes/{nid}", json={"titre_court": "Nouveau Titre", "domaine": "Travail"}
      )
      assert resp.status_code == 200
      conn = sqlite3.connect(TEST_DB)
      row = conn.execute(
          "SELECT titre_court, domaine, titre_modifie FROM notes WHERE id = ?", (nid,)
      ).fetchone()
      assert row[0] == "Nouveau Titre"
      assert row[1] == "Travail"
      assert row[2] == 1
      conn.close()
  ```

- [ ] **Étape 2 : Vérifier que les nouveaux tests cassent**

  ```bash
  python -m pytest tests/test_brain_server.py::test_patch_note_domaine_valide tests/test_brain_server.py::test_patch_note_domaine_a_trier tests/test_brain_server.py::test_patch_note_domaine_invalide_422 tests/test_brain_server.py::test_patch_note_ni_titre_ni_domaine_422 tests/test_brain_server.py::test_patch_note_titre_et_domaine_ensemble -v
  ```

  Attendu : les 4 nouveaux tests → FAIL (le 422 sur body vide peut passer, les autres non).

  Note : `test_patch_note_ni_titre_ni_domaine_422` peut déjà passer si le comportement actuel renvoie 422 pour un titre vide — ce n'est pas grave, l'important est que les tests de domaine cassent.

- [ ] **Étape 3 : Mettre à jour l'import dans brain_server.py**

  Remplacer la ligne d'import :

  ```python
  from brain_agent import init_db as _init_db, get_dropbox
  ```

  par :

  ```python
  from brain_agent import init_db as _init_db, get_dropbox, DOMAINS as VALID_DOMAINS
  ```

- [ ] **Étape 4 : Remplacer l'endpoint PATCH dans brain_server.py**

  Remplacer la fonction `patch_note` entière :

  ```python
  @app.patch("/notes/{note_id}")
  def patch_note(note_id: str, body: dict):
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

  par :

  ```python
  @app.patch("/notes/{note_id}")
  def patch_note(note_id: str, body: dict):
      titre   = body.get("titre_court", "").strip()
      domaine = body.get("domaine", "").strip()

      if not titre and not domaine:
          raise HTTPException(status_code=422, detail="titre_court ou domaine requis")
      if domaine and domaine not in VALID_DOMAINS:
          raise HTTPException(status_code=422, detail=f"domaine invalide : {domaine}")

      conn = get_db()
      if titre:
          conn.execute(
              "UPDATE notes SET titre_court = ?, titre_modifie = 1 WHERE id = ?",
              (titre, note_id)
          )
      if domaine:
          conn.execute(
              "UPDATE notes SET domaine = ? WHERE id = ?",
              (domaine, note_id)
          )
      conn.commit()
      conn.close()
      return {"updated": note_id, "titre_court": titre or None, "domaine": domaine or None}
  ```

- [ ] **Étape 5 : Vérifier que tous les tests passent**

  ```bash
  python -m pytest tests/test_brain_server.py -v
  ```

  Attendu : tous verts, y compris le test existant `test_patch_note_titre`.

- [ ] **Étape 6 : Suite complète**

  ```bash
  python -m pytest -v
  ```

  Attendu : 76+ tests verts (71 existants + 5 nouveaux).

- [ ] **Étape 7 : Commit**

  ```bash
  git add brain_server.py tests/test_brain_server.py
  git commit -m "feat: PATCH /notes/:id accepte domaine — validation via DOMAINS importé"
  ```

---

## Task 3 — style.css : token --d-trier + styles picker modal

**Files:**
- Modify: `brain_app/style.css`

- [ ] **Étape 1 : Ajouter le token --d-trier dans :root**

  Dans le bloc `:root` (après `--d-meta` vers la ligne 25), ajouter :

  ```css
  --d-trier: oklch(0.75 0.08 55);
  ```

- [ ] **Étape 2 : Ajouter les styles du picker de domaine**

  Après la règle `.modeswitch svg { ... }` (vers la ligne 107), ajouter :

  ```css
  .domain-changeable { cursor: pointer; display: inline-flex; align-items: center; gap: 7px; }
  .domain-changeable .domlabel { transition: color .2s; }
  .domain-changeable:hover .domlabel { color: var(--ink-2); }
  .domain-edit-hint { font-size: 10px; color: var(--ink-3); opacity: 0; transition: opacity .2s; margin-left: 2px; }
  .domain-changeable:hover .domain-edit-hint { opacity: 1; }
  .domain-picker { display: flex; flex-wrap: wrap; gap: 6px;
    background: rgba(10,10,18,0.97); border: 1px solid var(--stroke-hi);
    border-radius: 12px; padding: 10px; margin-top: 8px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.55); }
  .domain-picker.hidden { display: none; }
  .dpill { all: unset; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 10px; border-radius: var(--r-pill);
    background: var(--glass); border: 1px solid var(--stroke);
    font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.04em;
    color: var(--ink-2); transition: all .2s var(--ease); }
  .dpill:hover { background: var(--glass-2); border-color: var(--accent); color: var(--ink); }
  .dpill.active { background: color-mix(in oklch, var(--accent) 18%, transparent);
    border-color: var(--accent); color: var(--ink); }
  ```

- [ ] **Étape 3 : Commit**

  ```bash
  git add brain_app/style.css
  git commit -m "style: token --d-trier + styles picker domaine modal"
  ```

---

## Task 4 — renderer.js : suppression de featured + renderATrier

**Files:**
- Modify: `brain_app/renderer.js`

Pas de tests automatiques pour cette tâche — vérification manuelle en lançant l'app.

- [ ] **Étape 1 : Ajouter "À trier" à DOMAINS et DOMAIN_ORDER**

  Dans la constante `DOMAINS` (vers la ligne 8), ajouter en dernière entrée :

  ```javascript
  'À trier': { key: 'trier', label: 'À trier', color: 'var(--d-trier)' },
  ```

  Dans `DOMAIN_ORDER` (ligne 16), ajouter en fin de tableau :

  ```javascript
  const DOMAIN_ORDER = ['Travail', 'Apprentissage', 'Projets perso', 'Jeux vidéos', 'Plantes', 'Organisation TDAH', 'À trier'];
  ```

- [ ] **Étape 2 : Ajouter l'icône "trier" dans ICONS**

  Après l'icône `star`, ajouter :

  ```javascript
  trier: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <path d="M3 6h18M7 12h10M11 18h2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
  </svg>`,
  ```

- [ ] **Étape 3 : Supprimer featured du state initial**

  Dans l'objet `state` (vers la ligne 78), supprimer la ligne :

  ```javascript
  featured: [],
  ```

- [ ] **Étape 4 : Nettoyer deleteNote — supprimer la référence à state.featured**

  Dans `deleteNote()`, remplacer :

  ```javascript
    setState({
      openNote: null,
      notes:    state.notes.filter(n => n.id !== note.id),
      featured: state.featured.filter(n => n.id !== note.id),
    });
  ```

  par :

  ```javascript
    setState({
      openNote: null,
      notes:    state.notes.filter(n => n.id !== note.id),
    });
  ```

- [ ] **Étape 5 : Nettoyer patchTitre — supprimer la référence à state.featured**

  Dans `patchTitre()`, remplacer :

  ```javascript
      const update = n => n.id === note.id ? { ...n, titre: newTitre.trim(), titre_modifie: true } : n;
      setState({
        notes:    state.notes.map(update),
        featured: state.featured.map(update),
        openNote: state.openNote?.id === note.id ? { ...state.openNote, titre: newTitre.trim() } : state.openNote,
      });
  ```

  par :

  ```javascript
      const update = n => n.id === note.id ? { ...n, titre: newTitre.trim(), titre_modifie: true } : n;
      setState({
        notes:    state.notes.map(update),
        openNote: state.openNote?.id === note.id ? { ...state.openNote, titre: newTitre.trim() } : state.openNote,
      });
  ```

- [ ] **Étape 6 : Supprimer l'appel /a-la-une dans loadData et le setState correspondant**

  Dans `loadData()`, remplacer :

  ```javascript
    const [statusData, featuredRaw, notesRaw, blocsRaw] = await Promise.all([
      fetch(`${API}/status`).then(r => r.json()),
      fetch(`${API}/a-la-une?limit=6`).then(r => r.json()),
      fetch(`${API}/notes?limit=200`).then(r => r.json()),
      fetch(`${API}/blocs`).then(r => r.json()).catch(() => []),
    ]);
    state._silent = silent;
    setState({
      status: statusData,
      notes: notesRaw.map(mapNote),
      featured: featuredRaw.map(mapNote),
      blocs: blocsRaw,
    });
  ```

  par :

  ```javascript
    const [statusData, notesRaw, blocsRaw] = await Promise.all([
      fetch(`${API}/status`).then(r => r.json()),
      fetch(`${API}/notes?limit=200`).then(r => r.json()),
      fetch(`${API}/blocs`).then(r => r.json()).catch(() => []),
    ]);
    state._silent = silent;
    setState({
      status: statusData,
      notes: notesRaw.map(mapNote),
      blocs: blocsRaw,
    });
  ```

- [ ] **Étape 7 : Remplacer renderFeatured par renderATrier**

  Supprimer entièrement la fonction `renderFeatured()` et la remplacer par :

  ```javascript
  // ── Render: section À trier ───────────────────────────────────────────────────

  function renderATrier() {
    const container = document.getElementById('featured-cards');
    const head = document.getElementById('une-head');
    const trier = state.notes.filter(n => n.domaine === 'À trier');

    if (!trier.length) {
      container.innerHTML = '';
      head.classList.add('hidden');
      return;
    }

    head.classList.remove('hidden');
    container.innerHTML = trier.map(n => `
      <div class="fcard" data-id="${n.id}" style="--accent:var(--d-trier)" tabindex="0" role="button">
        <div class="glow"></div>
        <div class="ftitle">${n.titre}</div>
        <div class="finsight">${n.insight}</div>
        <div class="fmeta">
          <span class="ddot"></span>
          <span class="metatime">à trier</span>
          <span class="metatime" style="margin-left:auto">${relTime(n._days)}</span>
        </div>
      </div>`).join('');

    container.querySelectorAll('.fcard').forEach(el => {
      el.addEventListener('click', () => {
        const note = trier.find(n => n.id === el.dataset.id);
        if (note) openModal(note);
      });
    });

    if (!state._silent) {
      animate(container.querySelectorAll('.fcard'), {
        opacity: [0, 1], translateY: ['10px', '0px'],
        delay: stagger(40), duration: 500, ease: 'outQuart',
      });
    }
  }
  ```

- [ ] **Étape 8 : Mettre à jour renderGrille pour appeler renderATrier**

  Dans `renderGrille()`, remplacer :

  ```javascript
  function renderGrille() {
    document.getElementById('grille-view').classList.remove('hidden');
    document.getElementById('constel-view').classList.add('hidden');
    renderFeatured();
    renderFilters();
    renderSections();
    renderCornerStats();
  }
  ```

  par :

  ```javascript
  function renderGrille() {
    document.getElementById('grille-view').classList.remove('hidden');
    document.getElementById('constel-view').classList.add('hidden');
    renderATrier();
    renderFilters();
    renderSections();
    renderCornerStats();
  }
  ```

- [ ] **Étape 9 : Mettre à jour renderTopbar — injecter l'icône trier au lieu de star**

  Dans `renderTopbar()`, remplacer :

  ```javascript
  document.getElementById('star-icon').innerHTML = ICONS.star;
  ```

  par :

  ```javascript
  const trierIconEl = document.getElementById('trier-icon');
  if (trierIconEl) trierIconEl.innerHTML = ICONS.trier;
  ```

- [ ] **Étape 10 : Commit**

  ```bash
  git add brain_app/renderer.js
  git commit -m "feat: renderATrier remplace renderFeatured, suppression state.featured"
  ```

---

## Task 5 — renderer.js : patchDomaine + picker modal

**Files:**
- Modify: `brain_app/renderer.js`

- [ ] **Étape 1 : Ajouter la fonction patchDomaine**

  Après la fonction `patchTitre()`, ajouter :

  ```javascript
  async function patchDomaine(note, newDomaine) {
    if (newDomaine === note.domaine) return;
    try {
      const resp = await fetch(`${API}/notes/${note.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domaine: newDomaine }),
      });
      if (!resp.ok) return;
      const update = n => n.id === note.id ? { ...n, domaine: newDomaine } : n;
      setState({
        notes:    state.notes.map(update),
        openNote: state.openNote?.id === note.id
          ? { ...state.openNote, domaine: newDomaine }
          : state.openNote,
      });
    } catch { /* silencieux */ }
  }
  ```

- [ ] **Étape 2 : Modifier renderModal — rendre le domrow cliquable**

  Dans `renderModal()`, remplacer le bloc `.domrow` et `.htext` :

  ```javascript
          <div class="htext">
            <div class="domrow"><span class="ddot"></span><span class="domlabel">${note.est_meta ? 'Synthèse · ' : ''}${dom.label}</span></div>
            ${sourceLinkHtml}
            <h2 id="modal-title" class="title-editable" contenteditable="true" spellcheck="false">${note.titre}</h2>
          </div>
  ```

  par :

  ```javascript
          <div class="htext">
            <div class="domrow domain-changeable" id="modal-domrow">
              <span class="ddot"></span>
              <span class="domlabel">${note.est_meta ? 'Synthèse · ' : ''}${dom.label}</span>
              <span class="domain-edit-hint">✎</span>
            </div>
            <div class="domain-picker hidden" id="modal-domain-picker">
              ${DOMAIN_ORDER.map(d => {
                const dc = domainConfig(d);
                const isActive = d === note.domaine;
                return `<button class="dpill${isActive ? ' active' : ''}" data-domain="${d}" style="--accent:${dc.color}"><span class="ddot"></span>${dc.label}</button>`;
              }).join('')}
            </div>
            ${sourceLinkHtml}
            <h2 id="modal-title" class="title-editable" contenteditable="true" spellcheck="false">${note.titre}</h2>
          </div>
  ```

- [ ] **Étape 3 : Binder les événements du picker dans renderModal**

  Dans la section d'événements de `renderModal()`, après le binding de `modal-close`, ajouter :

  ```javascript
  const domrow = document.getElementById('modal-domrow');
  const picker = document.getElementById('modal-domain-picker');

  domrow.addEventListener('click', (e) => {
    e.stopPropagation();
    picker.classList.toggle('hidden');
  });

  picker.querySelectorAll('.dpill').forEach(pill => {
    pill.addEventListener('click', (e) => {
      e.stopPropagation();
      picker.classList.add('hidden');
      patchDomaine(note, pill.dataset.domain);
    });
  });

  const onDocClick = (e) => {
    if (!document.getElementById('modal-domain-picker')) {
      document.removeEventListener('mousedown', onDocClick);
      return;
    }
    if (!picker.contains(e.target) && !domrow.contains(e.target)) {
      picker.classList.add('hidden');
    }
  };
  document.addEventListener('mousedown', onDocClick);
  ```

- [ ] **Étape 4 : Commit**

  ```bash
  git add brain_app/renderer.js
  git commit -m "feat: patchDomaine + picker clic-sur-domaine dans la modale"
  ```

---

## Task 6 — index.html : label "À trier" + icône

**Files:**
- Modify: `brain_app/index.html`

- [ ] **Étape 1 : Remplacer le label et l'id de l'icône dans une-head**

  Remplacer :

  ```html
        <div class="une-head" id="une-head">
          <span class="star" id="star-icon"></span>
          <span class="uppercase-label" style="color:var(--d-une)">À la une</span>
        </div>
  ```

  par :

  ```html
        <div class="une-head" id="une-head">
          <span class="trier-icon" id="trier-icon"></span>
          <span class="uppercase-label" style="color:var(--d-trier)">À trier</span>
        </div>
  ```

- [ ] **Étape 2 : Commit**

  ```bash
  git add brain_app/index.html
  git commit -m "feat: section A trier remplace A la une dans index.html"
  ```

---

## Task 7 — Vérification manuelle

- [ ] **Étape 1 : Lancer la suite de tests complète une dernière fois**

  ```bash
  cd c:\Users\yapa\second_cerveau
  python -m pytest -v
  ```

  Attendu : 76+ tests verts.

- [ ] **Étape 2 : Lancer l'app Electron**

  ```bash
  cd brain_app
  npm start
  ```

  Vérifier :
  - La section "À trier" est masquée si aucune note n'a ce domaine
  - Le filtre "À trier" apparaît bien dans la filter bar
  - La section "À trier" apparaît dans la liste principale quand des notes l'ont comme domaine
  - Ouvrir une note → cliquer sur le label domaine → le picker s'ouvre
  - Cliquer une pill → le domaine change dans le header, la modale se re-render
  - Changer le domaine d'une note "À trier" → elle disparaît de la section "À trier" en haut

- [ ] **Étape 3 : Tester les cas limites**

  - Cliquer ailleurs que sur le picker → picker se ferme
  - Cliquer sur le domaine actif dans le picker → no-op (domaine inchangé)
  - Fermer la modale pendant que le picker est ouvert → pas de listener zombie (rouvrir la modale fonctionne normalement)
