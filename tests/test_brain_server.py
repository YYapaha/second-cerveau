import sys, os, sqlite3, tempfile, hashlib, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

TEST_DB = tempfile.mktemp(suffix=".db")


def _setup():
    from brain_agent import init_db
    init_db(TEST_DB)


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


# ── /blocs tests ──────────────────────────────────────────────────────────────

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
    assert "←" in uploaded


def test_add_bloc_item_empty_texte_422():
    with patch("brain_server.get_dropbox", return_value=MagicMock()):
        r = client.post("/blocs/travail/item", json={"texte": "  "})
    assert r.status_code == 422


def test_add_bloc_unknown_name_404():
    with patch("brain_server.get_dropbox", return_value=MagicMock()):
        r = client.post("/blocs/inconnu/item", json={"texte": "test"})
    assert r.status_code == 404


def test_add_bloc_item_newline_in_texte_422():
    with patch("brain_server.get_dropbox", return_value=MagicMock()):
        r = client.post("/blocs/travail/item", json={"texte": "task\ninjected"})
    assert r.status_code == 422


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


def test_patch_note_with_renamed_domain_valid():
    """After a rename, patching a note to the new name must succeed."""
    # "Jeux vidéos modifié" was created in test_patch_domain_rename_cascades_notes
    nid = _insert_note(domaine="Apprentissage")
    resp = client.patch(f"/notes/{nid}", json={"domaine": "Jeux vidéos modifié"})
    assert resp.status_code == 200
    conn = sqlite3.connect(TEST_DB)
    assert conn.execute("SELECT domaine FROM notes WHERE id=?", (nid,)).fetchone()[0] == "Jeux vidéos modifié"
    conn.close()
