"""brain_agent.py — Agent de raffinement et vectorisation du Second Cerveau."""
import os, json, sqlite3, hashlib, logging
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

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
    import re
    prompt = _PROMPT_RAFFINEMENT.format(contenu=contenu[:8000])
    r      = OpenAI(api_key=api_key).chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )
    raw  = r.choices[0].message.content.strip()
    raw  = re.sub(r"```(?:json)?\s*", "", raw).strip("`").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("raffiner_note: réponse GPT non parseable : %s — %s", raw[:200], e)
        raise
    if data.get("domaine") not in DOMAINS:
        data["domaine"] = "Projets perso"
    return data


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def vectoriser(texte: str, api_key: str) -> np.ndarray:
    """Retourne un vecteur numpy float32 (1536,) via text-embedding-3-small."""
    r = OpenAI(api_key=api_key).embeddings.create(
        model="text-embedding-3-small",
        input=texte[:8000],
    )
    return np.array(r.data[0].embedding, dtype=np.float32)


def embedding_to_bytes(v: np.ndarray) -> bytes:
    return v.tobytes()


def bytes_to_embedding(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32).copy()


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


def detecter_clusters(
    notes: list[dict],
    threshold: float = CLUSTER_THRESHOLD,
    min_notes: int   = CLUSTER_MIN_NOTES,
) -> list[list[dict]]:
    """Groupe les notes similaires. Retourne liste de groupes (chacun >= min_notes)."""
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
    """Synthèse GPT-4.1 d'un cluster. Retourne dict avec titre, insight, resume, domaine, sources_ids."""
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
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("generer_meta_fiche: réponse GPT non parseable : %s — %s", raw[:200], e)
        raise
    if data.get("domaine") not in DOMAINS:
        data["domaine"] = notes[0].get("domaine", "Projets perso")
    data["sources_ids"] = [n["id"] for n in notes]
    return data
