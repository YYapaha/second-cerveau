"""calendar_db.py — Schéma et helpers pour calendar.db."""
import sqlite3
from pathlib import Path

CAL_DB_PATH = Path(__file__).parent / "calendar.db"


def init_calendar_db(db_path: str | Path = CAL_DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript("""
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS events (
                id          TEXT PRIMARY KEY,
                titre       TEXT NOT NULL,
                type        TEXT NOT NULL CHECK(type IN ('rdv','anniversaire','tache','deadline')),
                date_debut  TEXT NOT NULL,
                date_fin    TEXT,
                description TEXT,
                source      TEXT DEFAULT 'electron',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id           TEXT PRIMARY KEY,
                event_id     TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                offset_type  TEXT NOT NULL CHECK(offset_type IN ('minutes','hours','days','weeks')),
                offset_value INTEGER NOT NULL,
                send_time    TEXT,
                sent         INTEGER DEFAULT 0,
                sent_at      TEXT
            );
        """)
        conn.commit()
    finally:
        conn.close()


def get_cal_db(db_path: str | Path = CAL_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
