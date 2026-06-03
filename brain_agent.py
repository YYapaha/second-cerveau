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
                embedding        BLOB,
                contenu_riche    TEXT,
                titre_modifie    INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        # Migration pour les DB existantes
        for col, definition in [
            ("contenu_riche", "TEXT"),
            ("titre_modifie", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE notes ADD COLUMN {col} {definition}")
                conn.commit()
            except Exception:
                pass  # colonne déjà présente
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
  "titre_court": "<vrai titre de la source si présent dans la fiche (ligne # TITLE ou titre principal), sinon 5-8 mots descriptifs en français>",
  "insight_cle": "<1 phrase actionnable qui capture l'essentiel, en français>",
  "resume": "<2-3 phrases résumant le contenu, en français>",
  "domaine": "<exactement un parmi : Travail | Apprentissage | Projets perso | Jeux vidéos | Plantes | Organisation TDAH>",
  "contenu_riche": {{
    "url_source": "<première URL http(s) trouvée dans la fiche, ou null>",
    "points_cles": ["<bullet 1>", "<bullet 2>", "..."],
    "pourquoi_garder": "<1-2 phrases sur la valeur long terme, ou null>",
    "quand_ressortir": "<1 phrase sur le contexte d'utilisation, ou null>"
  }}
}}

Règles :
- Si la fiche contient déjà des sections POINTS_CLES / POURQUOI_GARDER / QUAND_RESSORTIR → les extraire TELS QUELS sans reformuler
- Si ces sections sont absentes → les générer à partir du contenu
- points_cles : liste de 3 à 7 bullets actionnables en français correct
- Corrige les traductions approximatives
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
    """Appelle GPT-4.1 pour raffiner une fiche. Retourne dict avec 5 clés."""
    import re
    prompt = _PROMPT_RAFFINEMENT.format(contenu=contenu[:8000])
    r = OpenAI(api_key=api_key).chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
    )
    raw = r.choices[0].message.content.strip()
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip("`").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("raffiner_note: réponse GPT non parseable : %s — %s", raw[:200], e)
        raise
    # Normaliser contenu_riche
    if "contenu_riche" not in data or not isinstance(data["contenu_riche"], dict):
        data["contenu_riche"] = {"url_source": None, "points_cles": [], "pourquoi_garder": None, "quand_ressortir": None}
    cr = data["contenu_riche"]
    if not isinstance(cr.get("points_cles"), list):
        cr["points_cles"] = []
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
        mode=dbx_mod.files.WriteMode.overwrite,
    )
    log.info("Note du jour Dropbox : %s", payload["titre_court"])


def run_agent(db_path: str | Path = DB_PATH, reprocess: bool = False) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY manquante dans .env")

    init_db(db_path)
    conn = get_db(db_path)
    try:
        # 1. Sync Dropbox
        fiches_raw = sync_from_dropbox()
        if not fiches_raw:
            log.warning("Aucune fiche récupérée.")
            return

        # 2. Raffiner les fiches non encore traitées
        for fiche in fiches_raw:
            note_id  = get_note_id(fiche["path"])
            existing = conn.execute(
                "SELECT date_traitement, domaine, titre_modifie, titre_court FROM notes WHERE id = ?",
                (note_id,)
            ).fetchone()

            if reprocess:
                # Sauter les notes Travail déjà classifiées
                if existing and existing["domaine"] == "Travail":
                    continue
            else:
                if existing and existing["date_traitement"] == fiche["modified"]:
                    continue

            log.info("Traitement : %s", fiche["name"])
            try:
                import re as _re
                refined   = raffiner_note(fiche["content"], api_key)
                emb_txt   = f"{refined['titre_court']} {refined['insight_cle']} {refined['resume']}"
                embedding = vectoriser(emb_txt, api_key)
                tag_match = _re.search(r"\*\*TAGS\*\*\s*:\s*(.+)", fiche["content"])
                tags      = tag_match.group(1).strip() if tag_match else ""

                # Préserver le titre si édité manuellement
                titre_modifie  = existing["titre_modifie"] if existing else 0
                titre_final    = existing["titre_court"] if titre_modifie else refined["titre_court"]
                contenu_riche  = json.dumps(refined.get("contenu_riche", {}), ensure_ascii=False)

                conn.execute("""
                    INSERT OR REPLACE INTO notes
                      (id, dropbox_path, titre_court, insight_cle, resume, domaine,
                       tags, date_capture, date_traitement, score_pertinence,
                       est_meta_fiche, sources_ids, embedding, contenu_riche, titre_modifie)
                    VALUES (?,?,?,?,?,?,?,?,?,0.0,0,NULL,?,?,?)
                """, (
                    note_id, fiche["path"],
                    titre_final, refined["insight_cle"], refined["resume"], refined["domaine"],
                    tags, fiche["modified"], fiche["modified"],
                    embedding_to_bytes(embedding),
                    contenu_riche,
                    titre_modifie,
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
                meta = generer_meta_fiche(cluster, api_key)
                emb  = vectoriser(f"{meta['titre_court']} {meta['insight_cle']}", api_key)
                now  = datetime.now().isoformat()
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

        log.info("Agent terminé. %d fiches traitées.", len(fiches_raw))
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Brain Agent — raffinement et vectorisation")
    parser.add_argument("--reprocess", action="store_true",
                        help="Re-traiter toutes les notes sauf domaine=Travail")
    args = parser.parse_args()
    run_agent(reprocess=args.reprocess)
