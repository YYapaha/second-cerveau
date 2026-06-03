"""brain_server.py — API FastAPI locale pour l'Electron Brain App."""
import os, json, sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from brain_agent import init_db as _init_db, get_dropbox

DB_PATH = Path(__file__).parent / "brain.db"


@asynccontextmanager
async def lifespan(app):
    _init_db()  # Crée les tables si elles n'existent pas encore
    yield

app = FastAPI(title="Brain Server", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


_SELECT_FIELDS = (
    "id, dropbox_path, titre_court, insight_cle, resume, "
    "domaine, tags, date_capture, score_pertinence, est_meta_fiche, "
    "sources_ids, contenu_riche, titre_modifie"
)


@app.get("/status")
def status():
    conn  = get_db()
    total = conn.execute("SELECT COUNT(*) FROM notes WHERE est_meta_fiche = 0").fetchone()[0]
    meta  = conn.execute("SELECT COUNT(*) FROM notes WHERE est_meta_fiche = 1").fetchone()[0]
    last  = conn.execute("SELECT MAX(date_traitement) FROM notes").fetchone()[0]
    conn.close()
    return {"total_notes": total, "meta_fiches_count": meta, "last_sync": last}


@app.get("/notes")
def get_notes(
    domaine: Optional[str] = Query(None),
    limit:   int           = Query(20, ge=1, le=200),
):
    conn = get_db()
    if domaine:
        rows = conn.execute(
            f"SELECT {_SELECT_FIELDS} FROM notes WHERE domaine = ? ORDER BY score_pertinence DESC LIMIT ?",
            (domaine, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT {_SELECT_FIELDS} FROM notes ORDER BY score_pertinence DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/a-la-une")
def get_a_la_une(limit: int = Query(5, ge=1, le=10)):
    conn = get_db()
    rows = conn.execute(
        f"SELECT {_SELECT_FIELDS} FROM notes WHERE est_meta_fiche = 0 ORDER BY score_pertinence DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.delete("/notes/{note_id}")
def delete_note(note_id: str):
    from fastapi import HTTPException
    conn = get_db()
    row = conn.execute(
        "SELECT dropbox_path, est_meta_fiche FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Note introuvable")

    if not row["est_meta_fiche"] and row["dropbox_path"]:
        try:
            get_dropbox().files_delete_v2(row["dropbox_path"])
        except Exception as e:
            conn.close()
            raise HTTPException(status_code=502, detail=f"Erreur Dropbox : {e}")

    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return {"deleted": note_id}


@app.patch("/notes/{note_id}")
def patch_note(note_id: str, body: dict):
    from fastapi import HTTPException
    titre = body.get("titre_court", "").strip()
    if not titre:
        raise HTTPException(status_code=422, detail="titre_court requis")
    conn = get_db()
    conn.execute(
        "UPDATE notes SET titre_court = ?, titre_modifie = 1 WHERE id = ?",
        (titre, note_id)
    )
    conn.commit()
    conn.close()
    return {"updated": note_id, "titre_court": titre}


@app.post("/chat")
def chat(body: dict):
    query = body.get("query", "").strip()
    if not query:
        return {"reponse": "", "sources": []}

    api_key   = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"reponse": "❌ OPENAI_API_KEY manquante — configure la variable d'environnement.", "sources": []}
    client_ai = OpenAI(api_key=api_key)

    emb_resp = client_ai.embeddings.create(
        model="text-embedding-3-small", input=query[:2000]
    )
    q_vec = np.array(emb_resp.data[0].embedding, dtype=np.float32)

    conn  = get_db()
    rows  = conn.execute(
        "SELECT id, titre_court, insight_cle, domaine, embedding FROM notes WHERE embedding IS NOT NULL"
    ).fetchall()
    conn.close()

    scored = []
    for row in rows:
        emb  = np.frombuffer(row["embedding"], dtype=np.float32).copy()
        nq, ne = np.linalg.norm(q_vec), np.linalg.norm(emb)
        if nq > 0 and ne > 0:
            sim = float(np.dot(q_vec, emb) / (nq * ne))
            scored.append((sim, dict(row)))
    scored.sort(key=lambda x: x[0], reverse=True)
    top5 = [item[1] for item in scored[:5]]

    if not top5:
        return {"reponse": "Aucune note trouvée pour cette question.", "sources": []}

    contexte = "\n\n".join(
        f"**{n['titre_court']}** ({n['domaine']}) : {n['insight_cle']}"
        for n in top5
    )
    prompt = (
        f"Question : {query}\n\n"
        f"Notes pertinentes du Second Cerveau :\n{contexte}\n\n"
        "Réponds en français en citant les notes utiles. Sois concis."
    )
    r = client_ai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )
    return {
        "reponse": r.choices[0].message.content,
        "sources": [
            {"id": n["id"], "titre_court": n["titre_court"], "domaine": n["domaine"]}
            for n in top5
        ],
    }
