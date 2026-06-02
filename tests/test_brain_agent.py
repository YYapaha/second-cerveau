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


def test_get_note_id_is_deterministic():
    from brain_agent import get_note_id
    id1 = get_note_id("/Applications/Joplin/NOTE_test.md")
    id2 = get_note_id("/Applications/Joplin/NOTE_test.md")
    assert id1 == id2
    assert len(id1) == 32


def test_get_note_id_differs_per_path():
    from brain_agent import get_note_id
    assert get_note_id("/a.md") != get_note_id("/b.md")


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
