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
