# Ambient Brain — Plan 1 : Data Layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire `brain_agent.py` (sync Dropbox → GPT raffinement → vectorisation → clustering → scoring → note_du_jour) et `brain_server.py` (API FastAPI locale consommée par l'app Electron).

**Architecture:** L'agent tourne en script standalone, stocke tout dans `brain.db` (SQLite local). Le serveur FastAPI lit cette DB et expose des endpoints REST. Les deux communiquent via le fichier DB — pas de dépendance directe.

**Tech Stack:** Python 3.9+, SQLite3 (stdlib), OpenAI (`gpt-4.1` + `text-embedding-3-small`), Dropbox SDK, FastAPI, Uvicorn, NumPy, python-dotenv

---

## File Map

**Créés :**
- `requirements_brain.txt` — dépendances Python
- `brain_agent.py` — agent complet
- `brain_server.py` — API FastAPI
- `tests/__init__.py` — package tests
- `tests/test_brain_agent.py` — tests unitaires agent
- `tests/test_brain_server.py` — tests API

**Pas modifiés dans ce plan :** `core.py`, `bot_cloud.py`, `capture.py` (touchés en Plan 3)

---

### Task 1 : Setup + brain.db schema

**Files:**
- Create: `requirements_brain.txt`
- Create: `brain_agent.py`
- Create: `tests/__init__.py`
- Create: `tests/test_brain_agent.py`

- [ ] **Step 1: Créer requirements_brain.txt**

```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
openai>=1.0.0
dropbox>=12.0.0
numpy>=2.0.0
python-dotenv>=1.2.1
```

- [ ] **Step 2: Installer les dépendances**

```bash
pip install -r requirements_brain.txt
```

Expected : installation sans erreur.

- [ ] **Step 3: Créer tests/__init__.py (vide)**

```bash
touch tests/__init__.py
```

- [ ] **Step 4: Écrire le test qui échoue**

Créer `tests/test_brain_agent.py` :

```python
import sqlite3, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_init_db_creates_tables():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        from brain_agent import init_db
        init_db(db_path)
        conn   = sqlite3.connect(db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "notes" in tables
        assert "meta"  in tables
        conn.close()
    finally:
        os.unlink(db_path)
```

- [ ] **Step 5: Lancer le test — vérifier qu'il échoue**

```bash
pytest tests/test_brain_agent.py::test_init_db_creates_tables -v
```

Expected : FAIL — `ModuleNotFoundError: No module named 'brain_agent'`

- [ ] **Step 6: Créer brain_agent.py avec init_db**

```python
"""brain_agent.py — Agent de raffinement et vectorisation du Second Cerveau."""
import os, json, sqlite3, hashlib, logging
from datetime import datetime
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DB_PATH      = Path(__file__).parent / "brain.db"
DROPBOX_ROOT = "/Applications/Joplin"
DOMAINS      = [
    "Travail", "Apprentissage", "Projets perso",
    "Jeux vidéos", "Plantes", "Organisation TDAH",
]
CLUSTER_THRESHOLD = 0.82
CLUSTER_MIN_NOTES = 3

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


def init_db(db_path: str | Path = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
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
            embedding        BLOB
        );
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()


def get_db(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
```

- [ ] **Step 7: Lancer le test — vérifier qu'il passe**

```bash
pytest tests/test_brain_agent.py::test_init_db_creates_tables -v
```

Expected : PASS

- [ ] **Step 8: Commit**

```bash
git add requirements_brain.txt brain_agent.py tests/
git commit -m "feat: brain_agent scaffold + brain.db schema"
```

---

### Task 2 : Note ID + Dropbox sync

**Files:**
- Modify: `brain_agent.py`
- Modify: `tests/test_brain_agent.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/test_brain_agent.py` :

```python
def test_get_note_id_is_deterministic():
    from brain_agent import get_note_id
    id1 = get_note_id("/Applications/Joplin/NOTE_test.md")
    id2 = get_note_id("/Applications/Joplin/NOTE_test.md")
    assert id1 == id2
    assert len(id1) == 32


def test_get_note_id_differs_per_path():
    from brain_agent import get_note_id
    assert get_note_id("/a.md") != get_note_id("/b.md")
```

- [ ] **Step 2: Lancer les tests — vérifier qu'ils échouent**

```bash
pytest tests/test_brain_agent.py -k "note_id" -v
```

Expected : FAIL — `ImportError: cannot import name 'get_note_id'`

- [ ] **Step 3: Ajouter get_note_id, get_dropbox, sync_from_dropbox à brain_agent.py**

Ajouter après `get_db()` :

```python
def get_note_id(dropbox_path: str) -> str:
    return hashlib.md5(dropbox_path.encode()).hexdigest()


def get_dropbox():
    import dropbox
    token   = os.environ.get("DROPBOX_ACCESS_TOKEN")
    refresh = os.environ.get("DROPBOX_REFRESH_TOKEN")
    app_key = os.environ.get("DROPBOX_APP_KEY")
    app_sec = os.environ.get("DROPBOX_APP_SECRET")
    if token:
        return dropbox.Dropbox(token)
    return dropbox.Dropbox(
        oauth2_refresh_token=refresh,
        app_key=app_key,
        app_secret=app_sec,
    )


def sync_from_dropbox() -> list[dict]:
    """Télécharge toutes les fiches .md depuis Dropbox. Retourne liste de dicts."""
    import dropbox as dbx_mod
    dbx     = get_dropbox()
    exclure = {"blocnotes.md", "travail.md", "projet.md"}
    results = []
    try:
        res     = dbx.files_list_folder(DROPBOX_ROOT)
        entries = list(res.entries)
        while res.has_more:
            res      = dbx.files_list_folder_continue(res.cursor)
            entries += res.entries
        for e in entries:
            if (isinstance(e, dbx_mod.files.FileMetadata)
                    and e.name.endswith(".md")
                    and e.name not in exclure):
                _, dl = dbx.files_download(e.path_lower)
                results.append({
                    "path":     e.path_lower,
                    "name":     e.name,
                    "content":  dl.content.decode("utf-8", errors="ignore"),
                    "modified": e.server_modified.isoformat(),
                })
        log.info("Dropbox : %d fiches récupérées", len(results))
    except Exception as e:
        log.error("Erreur Dropbox sync : %s", e)
    return results
```

- [ ] **Step 4: Lancer les tests — vérifier qu'ils passent**

```bash
pytest tests/test_brain_agent.py -k "note_id" -v
```

Expected : PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add brain_agent.py tests/test_brain_agent.py
git commit -m "feat: Dropbox sync + note ID hash"
```

---

### Task 3 : GPT raffinement

**Files:**
- Modify: `brain_agent.py`
- Modify: `tests/test_brain_agent.py`

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_brain_agent.py` :

```python
import json
from unittest.mock import patch, MagicMock


def test_raffiner_note_returns_expected_keys():
    from brain_agent import raffiner_note
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps({
        "titre_court": "Tips Claude Code",
        "insight_cle": "Les hooks automatisent les actions post-outil.",
        "resume":      "Claude Code supporte des hooks configurables. Ils déclenchent des scripts shell.",
        "domaine":     "Apprentissage",
    })
    with patch("brain_agent.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = mock_resp
        result = raffiner_note("contenu de test", "fake-key")
    assert result["titre_court"] == "Tips Claude Code"
    assert result["domaine"]     == "Apprentissage"
    assert "insight_cle" in result
    assert "resume"      in result
```

- [ ] **Step 2: Lancer le test — vérifier qu'il échoue**

```bash
pytest tests/test_brain_agent.py::test_raffiner_note_returns_expected_keys -v
```

Expected : FAIL — `ImportError: cannot import name 'raffiner_note'`

- [ ] **Step 3: Ajouter raffiner_note à brain_agent.py**

Ajouter après `sync_from_dropbox()` :

```python
_PROMPT_RAFFINEMENT = """Tu analyses une fiche de connaissance capturée par un utilisateur TDAH.

Retourne UNIQUEMENT un JSON valide (sans bloc markdown) :
{{
  "titre_court": "<3-5 mots, très descriptif, en français correct>",
  "insight_cle": "<1 phrase qui capture l'essentiel, en français correct>",
  "resume": "<2 phrases résumant le contenu, en français correct>",
  "domaine": "<exactement un parmi : Travail | Apprentissage | Projets perso | Jeux vidéos | Plantes | Organisation TDAH>"
}}

Règles :
- Corrige les traductions approximatives — écris un français naturel
- Garde l'insight qui rend la note utile, ne résume pas au détriment du sens
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
    """Appelle GPT-4.1 pour raffiner une fiche. Retourne dict avec 4 clés."""
    from openai import OpenAI
    import re
    prompt = _PROMPT_RAFFINEMENT.format(contenu=contenu[:8000])
    r      = OpenAI(api_key=api_key).chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )
    raw  = r.choices[0].message.content.strip()
    raw  = re.sub(r"```(?:json)?\s*", "", raw).strip("`").strip()
    data = json.loads(raw)
    if data.get("domaine") not in DOMAINS:
        data["domaine"] = "Projets perso"
    return data
```

- [ ] **Step 4: Lancer le test — vérifier qu'il passe**

```bash
pytest tests/test_brain_agent.py::test_raffiner_note_returns_expected_keys -v
```

Expected : PASS

- [ ] **Step 5: Commit**

```bash
git add brain_agent.py tests/test_brain_agent.py
git commit -m "feat: GPT-4.1 raffinement des fiches"
```

---

### Task 4 : Vectorisation + similarité cosinus

**Files:**
- Modify: `brain_agent.py`
- Modify: `tests/test_brain_agent.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/test_brain_agent.py` :

```python
import numpy as np


def test_cosine_similarity_identical():
    from brain_agent import cosine_similarity
    v = np.array([1.0, 0.0, 0.0])
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    from brain_agent import cosine_similarity
    assert abs(cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0]))) < 1e-6


def test_vectoriser_returns_numpy_array():
    from brain_agent import vectoriser
    mock_resp = MagicMock()
    mock_resp.data[0].embedding = [0.1] * 1536
    with patch("brain_agent.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.embeddings.create.return_value = mock_resp
        result = vectoriser("texte test", "fake-key")
    assert isinstance(result, np.ndarray)
    assert result.shape == (1536,)
```

- [ ] **Step 2: Lancer les tests — vérifier qu'ils échouent**

```bash
pytest tests/test_brain_agent.py -k "cosine or vectoriser" -v
```

Expected : FAIL

- [ ] **Step 3: Ajouter cosine_similarity, vectoriser, embedding helpers**

Ajouter après `raffiner_note()` :

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def vectoriser(texte: str, api_key: str) -> np.ndarray:
    """Retourne un vecteur numpy float32 (1536,) via text-embedding-3-small."""
    from openai import OpenAI
    r = OpenAI(api_key=api_key).embeddings.create(
        model="text-embedding-3-small",
        input=texte[:8000],
    )
    return np.array(r.data[0].embedding, dtype=np.float32)


def embedding_to_bytes(v: np.ndarray) -> bytes:
    return v.tobytes()


def bytes_to_embedding(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)
```

- [ ] **Step 4: Lancer les tests — vérifier qu'ils passent**

```bash
pytest tests/test_brain_agent.py -k "cosine or vectoriser" -v
```

Expected : PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add brain_agent.py tests/test_brain_agent.py
git commit -m "feat: vectorisation + similarité cosinus"
```

---

### Task 5 : Score de pertinence

**Files:**
- Modify: `brain_agent.py`
- Modify: `tests/test_brain_agent.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/test_brain_agent.py` :

```python
from datetime import datetime, timedelta


def test_score_recent_beats_old():
    from brain_agent import calculer_score
    recent  = {"date_capture": datetime.now().isoformat(), "domaine": "Apprentissage"}
    vieux   = {"date_capture": (datetime.now() - timedelta(days=80)).isoformat(), "domaine": "Apprentissage"}
    domains = {"Apprentissage": 5}
    assert calculer_score(recent, domains) > calculer_score(vieux, domains)


def test_score_active_domain_beats_inactive():
    from brain_agent import calculer_score
    date   = datetime.now().isoformat()
    actif  = {"date_capture": date, "domaine": "Apprentissage"}
    inactif = {"date_capture": date, "domaine": "Plantes"}
    assert calculer_score(actif, {"Apprentissage": 10, "Plantes": 0}) > \
           calculer_score(inactif, {"Apprentissage": 10, "Plantes": 0})
```

- [ ] **Step 2: Lancer les tests — vérifier qu'ils échouent**

```bash
pytest tests/test_brain_agent.py -k "score" -v
```

Expected : FAIL

- [ ] **Step 3: Ajouter calculer_score**

Ajouter après `bytes_to_embedding()` :

```python
def calculer_score(note: dict, recent_domains: dict) -> float:
    """Score [0.0–1.0] = 50% fraîcheur + 50% activité du domaine (7 derniers jours)."""
    score = 0.0
    try:
        date_str = note.get("date_capture", "")
        if date_str:
            from datetime import timezone
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            age_jours = max(0, (datetime.now(timezone.utc) - date).days)
            score += max(0.0, 1.0 - age_jours / 90.0) * 0.5
    except Exception:
        pass
    freq   = recent_domains.get(note.get("domaine", ""), 0)
    score += min(freq / 10.0, 1.0) * 0.5
    return round(score, 4)
```

- [ ] **Step 4: Lancer les tests — vérifier qu'ils passent**

```bash
pytest tests/test_brain_agent.py -k "score" -v
```

Expected : PASS

- [ ] **Step 5: Commit**

```bash
git add brain_agent.py tests/test_brain_agent.py
git commit -m "feat: score de pertinence fraîcheur + domaine"
```

---

### Task 6 : Détection de clusters + méta-fiches

**Files:**
- Modify: `brain_agent.py`
- Modify: `tests/test_brain_agent.py`

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_brain_agent.py` :

```python
def test_detecter_clusters_groups_similar():
    from brain_agent import detecter_clusters
    v_base  = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v_near1 = np.array([0.99, 0.14, 0.0], dtype=np.float32)
    v_near2 = np.array([0.99, 0.0, 0.14], dtype=np.float32)
    v_far   = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    notes = [
        {"id": "a", "embedding": v_base,  "titre_court": "A", "insight_cle": "A", "domaine": "Apprentissage"},
        {"id": "b", "embedding": v_near1, "titre_court": "B", "insight_cle": "B", "domaine": "Apprentissage"},
        {"id": "c", "embedding": v_near2, "titre_court": "C", "insight_cle": "C", "domaine": "Apprentissage"},
        {"id": "d", "embedding": v_far,   "titre_court": "D", "insight_cle": "D", "domaine": "Plantes"},
    ]
    clusters = detecter_clusters(notes, threshold=0.95, min_notes=3)
    assert len(clusters) == 1
    ids = {n["id"] for n in clusters[0]}
    assert "a" in ids and "b" in ids and "c" in ids
    assert "d" not in ids
```

- [ ] **Step 2: Lancer le test — vérifier qu'il échoue**

```bash
pytest tests/test_brain_agent.py::test_detecter_clusters_groups_similar -v
```

Expected : FAIL

- [ ] **Step 3: Ajouter detecter_clusters et generer_meta_fiche**

Ajouter après `calculer_score()` :

```python
def detecter_clusters(
    notes: list[dict],
    threshold: float = CLUSTER_THRESHOLD,
    min_notes: int   = CLUSTER_MIN_NOTES,
) -> list[list[dict]]:
    """Groupe les notes similaires. Retourne liste de groupes (chacun ≥ min_notes)."""
    if len(notes) < min_notes:
        return []
    assigned, clusters = set(), []
    for i, ni in enumerate(notes):
        if ni["id"] in assigned:
            continue
        group = [ni]
        for nj in notes:
            if nj["id"] in assigned or nj["id"] == ni["id"]:
                continue
            if cosine_similarity(ni["embedding"], nj["embedding"]) >= threshold:
                group.append(nj)
        if len(group) >= min_notes:
            for n in group:
                assigned.add(n["id"])
            clusters.append(group)
    return clusters


def generer_meta_fiche(notes: list[dict], api_key: str) -> dict:
    """Synthèse GPT-4.1 d'un cluster de notes. Retourne dict avec titre, insight, resume, domaine, sources_ids."""
    from openai import OpenAI
    import re
    extraits = "\n\n".join(
        f"Note {i+1} — {n['titre_court']}:\n{n['insight_cle']}"
        for i, n in enumerate(notes[:8])
    )
    prompt = (
        "Crée une méta-fiche de synthèse à partir de ces notes sur le même sujet.\n"
        "Retourne UNIQUEMENT un JSON valide :\n"
        '{{"titre_court":"<4-6 mots>","insight_cle":"<2-3 phrases>","resume":"<paragraphe>","domaine":"<domaine commun>"}}\n\n'
        f"Notes :\n{extraits}"
    )
    r    = OpenAI(api_key=api_key).chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    raw  = re.sub(r"```(?:json)?\s*", "", r.choices[0].message.content.strip()).strip("`").strip()
    data = json.loads(raw)
    if data.get("domaine") not in DOMAINS:
        data["domaine"] = notes[0].get("domaine", "Projets perso")
    data["sources_ids"] = [n["id"] for n in notes]
    return data
```

- [ ] **Step 4: Lancer le test — vérifier qu'il passe**

```bash
pytest tests/test_brain_agent.py::test_detecter_clusters_groups_similar -v
```

Expected : PASS

- [ ] **Step 5: Commit**

```bash
git add brain_agent.py tests/test_brain_agent.py
git commit -m "feat: détection clusters + génération méta-fiches"
```

---

### Task 7 : Orchestration principale + note_du_jour Dropbox

**Files:**
- Modify: `brain_agent.py`

- [ ] **Step 1: Ajouter write_note_du_jour_dropbox et run_agent à brain_agent.py**

Ajouter après `generer_meta_fiche()` :

```python
DROPBOX_NOTE_DU_JOUR = "/second_cerveau/note_du_jour.json"


def write_note_du_jour_dropbox(note: dict) -> None:
    import dropbox as dbx_mod
    payload = {
        "titre_court": note.get("titre_court", ""),
        "insight_cle": note.get("insight_cle", ""),
        "domaine":     note.get("domaine", ""),
        "date":        datetime.now().strftime("%Y-%m-%d"),
    }
    get_dropbox().files_upload(
        json.dumps(payload, ensure_ascii=False, indent=2).encode(),
        DROPBOX_NOTE_DU_JOUR,
        mode=__import__("dropbox").files.WriteMode.overwrite,
    )
    log.info("Note du jour Dropbox : %s", payload["titre_court"])


def run_agent(db_path: str | Path = DB_PATH) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY manquante dans .env")

    init_db(db_path)
    conn = get_db(db_path)

    # 1. Sync Dropbox
    fiches_raw = sync_from_dropbox()
    if not fiches_raw:
        log.warning("Aucune fiche récupérée.")
        conn.close()
        return

    # 2. Raffiner les fiches non encore traitées
    for fiche in fiches_raw:
        note_id  = get_note_id(fiche["path"])
        existing = conn.execute(
            "SELECT date_traitement FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        if existing and existing["date_traitement"] == fiche["modified"]:
            continue  # Déjà à jour
        log.info("Traitement : %s", fiche["name"])
        try:
            import re as _re
            refined  = raffiner_note(fiche["content"], api_key)
            emb_txt  = f"{refined['titre_court']} {refined['insight_cle']} {refined['resume']}"
            embedding = vectoriser(emb_txt, api_key)
            tag_match = _re.search(r"\*\*TAGS\*\*\s*:\s*(.+)", fiche["content"])
            tags      = tag_match.group(1).strip() if tag_match else ""
            conn.execute("""
                INSERT OR REPLACE INTO notes
                  (id, dropbox_path, titre_court, insight_cle, resume, domaine,
                   tags, date_capture, date_traitement, score_pertinence,
                   est_meta_fiche, sources_ids, embedding)
                VALUES (?,?,?,?,?,?,?,?,?,0.0,0,NULL,?)
            """, (
                note_id, fiche["path"],
                refined["titre_court"], refined["insight_cle"], refined["resume"], refined["domaine"],
                tags, fiche["modified"], fiche["modified"],
                embedding_to_bytes(embedding),
            ))
            conn.commit()
        except Exception as e:
            log.error("Erreur %s : %s", fiche["name"], e)

    # 3. Détection de clusters → méta-fiches
    rows = conn.execute(
        "SELECT id, titre_court, insight_cle, domaine, embedding FROM notes WHERE est_meta_fiche = 0"
    ).fetchall()
    notes_emb = [
        {**dict(r), "embedding": bytes_to_embedding(r["embedding"])}
        for r in rows if r["embedding"]
    ]
    for cluster in detecter_clusters(notes_emb):
        meta_key = "meta_" + "_".join(sorted(n["id"] for n in cluster))
        meta_id  = hashlib.md5(meta_key.encode()).hexdigest()
        if conn.execute("SELECT 1 FROM notes WHERE id = ?", (meta_id,)).fetchone():
            continue
        try:
            meta    = generer_meta_fiche(cluster, api_key)
            emb     = vectoriser(f"{meta['titre_court']} {meta['insight_cle']}", api_key)
            now     = datetime.now().isoformat()
            conn.execute("""
                INSERT INTO notes
                  (id, dropbox_path, titre_court, insight_cle, resume, domaine,
                   tags, date_capture, date_traitement, score_pertinence,
                   est_meta_fiche, sources_ids, embedding)
                VALUES (?,?,?,?,?,?,?,?,?,0.0,1,?,?)
            """, (
                meta_id, f"meta/{meta_id}",
                meta["titre_court"], meta["insight_cle"], meta["resume"], meta["domaine"],
                "", now, now,
                json.dumps(meta["sources_ids"]),
                embedding_to_bytes(emb),
            ))
            conn.commit()
            log.info("Méta-fiche : %s (%d sources)", meta["titre_court"], len(cluster))
        except Exception as e:
            log.error("Erreur méta-fiche : %s", e)

    # 4. Scores de pertinence
    from collections import Counter
    recent_domains = dict(Counter(
        r["domaine"] for r in conn.execute(
            "SELECT domaine FROM notes WHERE date_capture >= date('now','-7 days')"
        ).fetchall()
    ))
    for row in conn.execute("SELECT id, domaine, date_capture FROM notes").fetchall():
        score = calculer_score(dict(row), recent_domains)
        conn.execute("UPDATE notes SET score_pertinence = ? WHERE id = ?", (score, row["id"]))
    conn.commit()

    # 5. Note du jour dans Dropbox
    top = conn.execute(
        "SELECT titre_court, insight_cle, domaine FROM notes "
        "WHERE est_meta_fiche = 0 ORDER BY score_pertinence DESC LIMIT 1"
    ).fetchone()
    if top:
        try:
            write_note_du_jour_dropbox(dict(top))
        except Exception as e:
            log.warning("Dropbox note_du_jour : %s", e)

    conn.close()
    log.info("Agent terminé. %d fiches traitées.", len(fiches_raw))


if __name__ == "__main__":
    run_agent()
```

- [ ] **Step 2: Smoke test manuel (nécessite .env valide)**

```bash
python brain_agent.py
```

Expected (avec vraies clés) : logs de sync + traitement + "Agent terminé."
Expected (sans clés) : `ValueError: OPENAI_API_KEY manquante`

- [ ] **Step 3: Lancer tous les tests pour vérifier qu'ils passent encore**

```bash
pytest tests/test_brain_agent.py -v
```

Expected : tous PASS

- [ ] **Step 4: Commit**

```bash
git add brain_agent.py
git commit -m "feat: orchestration brain_agent + note_du_jour Dropbox"
```

---

### Task 8 : brain_server.py — setup + /status

**Files:**
- Create: `brain_server.py`
- Create: `tests/test_brain_server.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `tests/test_brain_server.py` :

```python
import sys, os, sqlite3, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_DB = tempfile.mktemp(suffix=".db")

def _setup():
    conn = sqlite3.connect(TEST_DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY, dropbox_path TEXT, titre_court TEXT,
            insight_cle TEXT, resume TEXT, domaine TEXT, tags TEXT,
            date_capture TEXT, date_traitement TEXT,
            score_pertinence REAL DEFAULT 0.0,
            est_meta_fiche INTEGER DEFAULT 0,
            sources_ids TEXT, embedding BLOB
        );
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.commit()
    conn.close()

_setup()

import brain_server
brain_server.DB_PATH = TEST_DB

from fastapi.testclient import TestClient
client = TestClient(brain_server.app)


def test_status_keys():
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_notes" in data
    assert "meta_fiches_count" in data
    assert "last_sync" in data


def test_status_empty_db():
    resp = client.get("/status")
    data = resp.json()
    assert data["total_notes"]      == 0
    assert data["meta_fiches_count"] == 0
```

- [ ] **Step 2: Lancer les tests — vérifier qu'ils échouent**

```bash
pytest tests/test_brain_server.py -k "status" -v
```

Expected : FAIL — `ModuleNotFoundError: No module named 'brain_server'`

- [ ] **Step 3: Créer brain_server.py**

```python
"""brain_server.py — API FastAPI locale pour l'Electron Brain App."""
import os, json, sqlite3
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

DB_PATH = Path(__file__).parent / "brain.db"

app = FastAPI(title="Brain Server", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/status")
def status():
    conn  = get_db()
    total = conn.execute("SELECT COUNT(*) FROM notes WHERE est_meta_fiche = 0").fetchone()[0]
    meta  = conn.execute("SELECT COUNT(*) FROM notes WHERE est_meta_fiche = 1").fetchone()[0]
    last  = conn.execute("SELECT MAX(date_traitement) FROM notes").fetchone()[0]
    conn.close()
    return {"total_notes": total, "meta_fiches_count": meta, "last_sync": last}
```

- [ ] **Step 4: Lancer les tests — vérifier qu'ils passent**

```bash
pytest tests/test_brain_server.py -k "status" -v
```

Expected : PASS

- [ ] **Step 5: Commit**

```bash
git add brain_server.py tests/test_brain_server.py
git commit -m "feat: brain_server FastAPI + /status"
```

---

### Task 9 : /notes et /a-la-une

**Files:**
- Modify: `brain_server.py`
- Modify: `tests/test_brain_server.py`

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `tests/test_brain_server.py` :

```python
import hashlib, time


def _insert_note(domaine="Apprentissage", score=0.5, est_meta=0):
    nid  = hashlib.md5(f"{time.time()}".encode()).hexdigest()
    conn = sqlite3.connect(TEST_DB)
    conn.execute("""
        INSERT INTO notes
          (id, dropbox_path, titre_court, insight_cle, resume, domaine, tags,
           date_capture, date_traitement, score_pertinence, est_meta_fiche, sources_ids, embedding)
        VALUES (?,?,?,?,?,?,?,datetime('now'),datetime('now'),?,?,NULL,NULL)
    """, (nid, f"/test/{nid}.md", "Titre Test", "Insight.", "Résumé.", domaine, "", score, est_meta))
    conn.commit()
    conn.close()
    return nid


def test_get_notes_returns_list():
    _insert_note()
    resp = client.get("/notes")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_notes_filter_domaine():
    _insert_note(domaine="Plantes")
    resp = client.get("/notes?domaine=Plantes")
    assert resp.status_code == 200
    assert all(n["domaine"] == "Plantes" for n in resp.json())


def test_a_la_une_sorted_by_score():
    _insert_note(score=0.9)
    _insert_note(score=0.1)
    resp    = client.get("/a-la-une?limit=10")
    results = resp.json()
    assert resp.status_code == 200
    if len(results) >= 2:
        assert results[0]["score_pertinence"] >= results[1]["score_pertinence"]
```

- [ ] **Step 2: Lancer les tests — vérifier qu'ils échouent**

```bash
pytest tests/test_brain_server.py -k "notes or a_la_une" -v
```

Expected : FAIL — 404

- [ ] **Step 3: Ajouter /notes et /a-la-une à brain_server.py**

Ajouter après `/status` :

```python
_SELECT_FIELDS = (
    "id, dropbox_path, titre_court, insight_cle, resume, "
    "domaine, tags, date_capture, score_pertinence, est_meta_fiche, sources_ids"
)


@app.get("/notes")
def get_notes(
    domaine: Optional[str] = Query(None),
    limit:   int           = Query(20, ge=1, le=200),
):
    conn   = get_db()
    if domaine:
        rows = conn.execute(
            f"SELECT {_SELECT_FIELDS} FROM notes WHERE domaine = ? ORDER BY score_pertinence DESC LIMIT ?",
            (domaine, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT {_SELECT_FIELDS} FROM notes ORDER BY score_pertinence DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/a-la-une")
def get_a_la_une(limit: int = Query(5, ge=1, le=10)):
    conn = get_db()
    rows = conn.execute(
        f"SELECT {_SELECT_FIELDS} FROM notes ORDER BY score_pertinence DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Lancer tous les tests — vérifier qu'ils passent**

```bash
pytest tests/test_brain_server.py -v
```

Expected : tous PASS

- [ ] **Step 5: Commit**

```bash
git add brain_server.py tests/test_brain_server.py
git commit -m "feat: /notes et /a-la-une endpoints"
```

---

### Task 10 : /chat RAG endpoint

**Files:**
- Modify: `brain_server.py`
- Modify: `tests/test_brain_server.py`

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `tests/test_brain_server.py` :

```python
from unittest.mock import patch, MagicMock


def test_chat_returns_reponse_and_sources():
    mock_emb  = MagicMock()
    mock_emb.data[0].embedding = [0.0] * 1536
    mock_chat = MagicMock()
    mock_chat.choices[0].message.content = "Réponse de test."
    with patch("brain_server.OpenAI") as MockAI:
        inst = MockAI.return_value
        inst.embeddings.create.return_value = mock_emb
        inst.chat.completions.create.return_value = mock_chat
        resp = client.post("/chat", json={"query": "test question"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reponse" in data
    assert "sources" in data
```

- [ ] **Step 2: Lancer le test — vérifier qu'il échoue**

```bash
pytest tests/test_brain_server.py::test_chat_returns_reponse_and_sources -v
```

Expected : FAIL — 404

- [ ] **Step 3: Ajouter /chat à brain_server.py**

Ajouter après `/a-la-une` :

```python
@app.post("/chat")
def chat(body: dict):
    query = body.get("query", "").strip()
    if not query:
        return {"reponse": "", "sources": []}

    api_key  = os.environ.get("OPENAI_API_KEY", "")
    client_ai = OpenAI(api_key=api_key)

    emb_resp = client_ai.embeddings.create(
        model="text-embedding-3-small", input=query[:2000]
    )
    q_vec = np.array(emb_resp.data[0].embedding, dtype=np.float32)

    conn  = get_db()
    rows  = conn.execute(
        "SELECT id, titre_court, insight_cle, domaine, embedding FROM notes WHERE embedding IS NOT NULL"
    ).fetchall()
    conn.close()

    scored = []
    for row in rows:
        emb  = np.frombuffer(row["embedding"], dtype=np.float32)
        nq, ne = np.linalg.norm(q_vec), np.linalg.norm(emb)
        if nq > 0 and ne > 0:
            sim = float(np.dot(q_vec, emb) / (nq * ne))
            scored.append((sim, dict(row)))
    scored.sort(key=lambda x: x[0], reverse=True)
    top5 = [item[1] for item in scored[:5]]

    if not top5:
        return {"reponse": "Aucune note trouvée pour cette question.", "sources": []}

    contexte = "\n\n".join(
        f"**{n['titre_court']}** ({n['domaine']}) : {n['insight_cle']}"
        for n in top5
    )
    prompt = (
        f"Question : {query}\n\n"
        f"Notes pertinentes du Second Cerveau :\n{contexte}\n\n"
        "Réponds en français en citant les notes utiles. Sois concis."
    )
    r = client_ai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )
    return {
        "reponse": r.choices[0].message.content,
        "sources": [
            {"id": n["id"], "titre_court": n["titre_court"], "domaine": n["domaine"]}
            for n in top5
        ],
    }
```

- [ ] **Step 4: Lancer tous les tests**

```bash
pytest tests/ -v
```

Expected : tous PASS

- [ ] **Step 5: Commit**

```bash
git add brain_server.py tests/test_brain_server.py
git commit -m "feat: /chat RAG endpoint avec text-embedding-3-small"
```

---

### Task 11 : brain_start.bat + .gitignore

**Files:**
- Create: `brain_start.bat`
- Modify: `.gitignore`

- [ ] **Step 1: Ajouter brain.db au .gitignore**

Ajouter à `.gitignore` :

```
brain.db
```

- [ ] **Step 2: Créer brain_start.bat**

```batch
@echo off
title Second Cerveau — Brain System
cd /d "%~dp0"

echo [1/3] Agent de sync...
start "Brain Agent" /MIN python brain_agent.py

echo [2/3] Serveur API (attente 10s pour la premiere sync)...
timeout /t 10 /nobreak >nul
start "Brain Server" /MIN python -m uvicorn brain_server:app --host 127.0.0.1 --port 7842 --log-level warning

echo [3/3] Interface Electron (attente 3s)...
timeout /t 3 /nobreak >nul
cd brain_app
start "Brain App" npx electron .

echo Brain System demarre !
```

- [ ] **Step 3: Vérifier que le serveur démarre correctement**

```bash
python -m uvicorn brain_server:app --host 127.0.0.1 --port 7842
```

Ouvrir dans un navigateur : `http://127.0.0.1:7842/status`
Expected : `{"total_notes": 0, "meta_fiches_count": 0, "last_sync": null}`

- [ ] **Step 4: Commit**

```bash
git add brain_start.bat .gitignore
git commit -m "feat: brain_start.bat + gitignore brain.db"
```

---

**Plan 1 terminé.** Le data layer est complet et testable : `python brain_agent.py` sync + raffine les notes, `python -m uvicorn brain_server:app` expose l'API. Passer au Plan 2 (Electron UI).
