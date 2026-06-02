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
                embedding        BLOB
            );
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        conn.commit()
    finally:
        conn.close()


def get_db(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


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
