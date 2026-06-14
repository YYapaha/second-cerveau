# tests/test_calendar_db.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from calendar_db import init_calendar_db, get_cal_db


@pytest.fixture
def db_path(tmp_path):
    p = tmp_path / "test_calendar.db"
    init_calendar_db(p)
    return p


def test_tables_created(db_path):
    conn = get_cal_db(db_path)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "events" in tables
    assert "reminders" in tables


def test_idempotent(db_path):
    # Appeler deux fois ne doit pas lever d'exception
    init_calendar_db(db_path)


def test_create_event(db_path):
    conn = get_cal_db(db_path)
    conn.execute(
        "INSERT INTO events (id,titre,type,date_debut,source,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("id1", "RDV Médecin", "rdv", "2026-06-19T14:00", "electron",
         "2026-06-14T10:00", "2026-06-14T10:00")
    )
    conn.commit()
    row = conn.execute("SELECT * FROM events WHERE id=?", ("id1",)).fetchone()
    assert row["titre"] == "RDV Médecin"
    assert row["type"] == "rdv"
    conn.close()


def test_reminder_cascade_delete(db_path):
    conn = get_cal_db(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        "INSERT INTO events (id,titre,type,date_debut,source,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("ev1", "Test", "rdv", "2026-06-19", "electron", "2026-06-14", "2026-06-14")
    )
    conn.execute(
        "INSERT INTO reminders (id,event_id,offset_type,offset_value) VALUES (?,?,?,?)",
        ("r1", "ev1", "days", 1)
    )
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM events WHERE id=?", ("ev1",))
    conn.commit()
    count = conn.execute(
        "SELECT COUNT(*) FROM reminders WHERE event_id=?", ("ev1",)
    ).fetchone()[0]
    conn.close()
    assert count == 0


def test_send_time_column_exists(db_path):
    conn = get_cal_db(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(reminders)").fetchall()}
    conn.close()
    assert "send_time" in cols
