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
