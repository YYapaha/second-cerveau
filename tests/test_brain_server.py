import sys, os, sqlite3, tempfile, hashlib, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_DB = tempfile.mktemp(suffix=".db")


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


_setup()

import brain_server
brain_server.DB_PATH = TEST_DB

from fastapi.testclient import TestClient
client = TestClient(brain_server.app)


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


# /status tests
def test_status_keys():
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_notes" in data
    assert "meta_fiches_count" in data
    assert "last_sync" in data


def test_status_empty_db_counts():
    resp = client.get("/status")
    data = resp.json()
    assert isinstance(data["total_notes"], int)
    assert isinstance(data["meta_fiches_count"], int)


# /notes tests
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


# /a-la-une tests
def test_a_la_une_sorted_by_score():
    _insert_note(score=0.95)
    _insert_note(score=0.05)
    resp    = client.get("/a-la-une?limit=10")
    results = resp.json()
    assert resp.status_code == 200
    if len(results) >= 2:
        assert results[0]["score_pertinence"] >= results[1]["score_pertinence"]


# /chat tests
def test_chat_returns_reponse_and_sources():
    from unittest.mock import patch, MagicMock
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


def test_chat_empty_query_returns_empty():
    resp = client.post("/chat", json={"query": ""})
    assert resp.status_code == 200
    assert resp.json()["reponse"] == ""
    assert resp.json()["sources"] == []


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
