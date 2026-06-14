"""brain_server.py — API FastAPI locale pour l'Electron Brain App."""
import os, json, sqlite3, re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import dropbox as dbx_mod
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from brain_agent import init_db as _init_db, get_dropbox

DB_PATH = Path(__file__).parent / "brain.db"

from calendar_db import CAL_DB_PATH as _CAL_DB_PATH, init_calendar_db, get_cal_db as _get_cal_db
import uuid as _uuid

# CAL_DB_PATH is a module-level variable so tests can monkeypatch it.
# We only set it here if not already set (e.g. by monkeypatch before a reload).
if "CAL_DB_PATH" not in dir():
    CAL_DB_PATH = _CAL_DB_PATH


def get_cal_db():
    import brain_server as _self
    return _get_cal_db(_self.CAL_DB_PATH)


@asynccontextmanager
async def lifespan(app):
    _init_db()  # Crée les tables si elles n'existent pas encore
    import brain_server as _self
    init_calendar_db(_self.CAL_DB_PATH)
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

# ── Blocs fixes ───────────────────────────────────────────────────────────────

_ITEM_RE = re.compile(r'^-\s+(.+?)\s*←\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})\s*$')

BLOCS = {
    "travail":   "/Applications/Joplin/travail.md",
    "projets":   "/Applications/Joplin/projet.md",
    "blocnotes": "/Applications/Joplin/blocnotes.md",
}

_TITRES = {
    "travail":   "Travail",
    "projets":   "Projets",
    "blocnotes": "Bloc-notes",
}


def _parse_bloc(content: str) -> list[dict]:
    items, idx = [], 0
    for line in content.splitlines():
        line = line.rstrip()
        if not line.startswith("- "):
            continue
        m = _ITEM_RE.match(line)
        if m:
            items.append({"idx": idx, "texte": m.group(1), "date": m.group(2)})
        else:
            text = line[2:].strip()
            if text:
                items.append({"idx": idx, "texte": text, "date": None})
        idx += 1
    return items


@app.get("/blocs")
def get_blocs():
    result = []
    dbx = get_dropbox()
    for name, path in BLOCS.items():
        items = []
        try:
            _, dl = dbx.files_download(path)
            items = _parse_bloc(dl.content.decode("utf-8", errors="replace"))
        except Exception:
            pass
        result.append({"name": name, "titre": _TITRES[name], "items": items})
    return result


@app.post("/blocs/{name}/item")
def add_bloc_item(name: str, body: dict):
    if name not in BLOCS:
        raise HTTPException(status_code=404, detail="Bloc inconnu")
    texte = (body.get("texte") or "").strip()
    if not texte:
        raise HTTPException(status_code=422, detail="texte requis")
    if "\n" in texte or "\r" in texte:
        raise HTTPException(status_code=422, detail="texte ne peut pas contenir de saut de ligne")
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    new_line = f"- {texte} ← {date_str}\n"
    dbx  = get_dropbox()
    path = BLOCS[name]
    try:
        _, dl = dbx.files_download(path)
        content = dl.content.decode("utf-8", errors="replace")
    except Exception as e:
        if 'not_found' not in str(e).lower():
            raise HTTPException(status_code=502, detail=f"Erreur Dropbox : {e}")
        content = f"# {_TITRES[name]}\n"
    if not content.endswith("\n"):
        content += "\n"
    content += new_line
    dbx.files_upload(content.encode("utf-8"), path, mode=dbx_mod.files.WriteMode.overwrite)
    return {"added": True, "texte": texte, "date": date_str}


@app.delete("/blocs/{name}/{idx}")
def delete_bloc_item(name: str, idx: int):
    if name not in BLOCS:
        raise HTTPException(status_code=404, detail="Bloc inconnu")
    dbx  = get_dropbox()
    path = BLOCS[name]
    try:
        _, dl = dbx.files_download(path)
        content = dl.content.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur Dropbox : {e}")
    lines = content.splitlines(keepends=True)
    item_idx, line_to_remove = 0, None
    for i, line in enumerate(lines):
        if line.startswith("- "):
            if item_idx == idx:
                line_to_remove = i
                break
            item_idx += 1
    if line_to_remove is None:
        return {"deleted": False}
    lines.pop(line_to_remove)
    dbx.files_upload("".join(lines).encode("utf-8"), path, mode=dbx_mod.files.WriteMode.overwrite)
    return {"deleted": True, "name": name, "idx": idx}


@app.get("/status")
def status():
    conn  = get_db()
    total = conn.execute("SELECT COUNT(*) FROM notes WHERE est_meta_fiche = 0").fetchone()[0]
    meta  = conn.execute("SELECT COUNT(*) FROM notes WHERE est_meta_fiche = 1").fetchone()[0]
    last  = conn.execute("SELECT MAX(date_traitement) FROM notes").fetchone()[0]
    conn.close()
    return {"total_notes": total, "meta_fiches_count": meta, "last_sync": last}


@app.get("/domains")
def get_domains():
    conn = get_db()
    rows = conn.execute(
        "SELECT name, color, position FROM domains ORDER BY position"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.patch("/domains/{name}")
def patch_domain(name: str, body: dict):
    new_name  = body.get("name", "").strip() if "name" in body else None
    new_color = body.get("color", "").strip() if "color" in body else None

    if new_name is None and new_color is None:
        raise HTTPException(status_code=422, detail="name ou color requis")
    if new_name is not None and new_name == "":
        raise HTTPException(status_code=422, detail="name ne peut pas être vide")

    conn = get_db()
    row = conn.execute("SELECT name, color, position FROM domains WHERE name = ?", (name,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="domaine inconnu")

    if new_name is not None and new_name != name:
        if name == "À trier":
            conn.close()
            return JSONResponse(status_code=400, content={"error": "cannot_rename_default_domain"})
        conflict = conn.execute("SELECT name FROM domains WHERE name = ?", (new_name,)).fetchone()
        if conflict:
            conn.close()
            raise HTTPException(status_code=409, detail="ce nom existe déjà")

    try:
        if new_name is not None and new_name != name:
            conn.execute("UPDATE domains SET name = ? WHERE name = ?", (new_name, name))
            conn.execute("UPDATE notes SET domaine = ? WHERE domaine = ?", (new_name, name))
        if new_color is not None:
            effective_name = new_name if (new_name and new_name != name) else name
            conn.execute("UPDATE domains SET color = ? WHERE name = ?", (new_color, effective_name))
        conn.commit()
        final = conn.execute(
            "SELECT name, color, position FROM domains WHERE name = ?",
            (new_name if (new_name and new_name != name) else name,)
        ).fetchone()
        conn.close()
        return dict(final)
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/a-la-une")  # inutilisé — le frontend filtre state.notes directement
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
            # Si le fichier n'existe déjà plus sur Dropbox, on peut supprimer de la DB
            if 'not_found' not in str(e).lower():
                conn.close()
                raise HTTPException(status_code=502, detail=f"Erreur Dropbox : {e}")

    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return {"deleted": note_id}


@app.patch("/notes/{note_id}")
def patch_note(note_id: str, body: dict):
    titre   = body.get("titre_court", "").strip()
    domaine = body.get("domaine", "").strip()

    if not titre and not domaine:
        raise HTTPException(status_code=422, detail="titre_court ou domaine requis")
    if domaine:
        conn_v = get_db()
        valid  = {r["name"] for r in conn_v.execute("SELECT name FROM domains").fetchall()}
        conn_v.close()
        if domaine not in valid:
            raise HTTPException(status_code=422, detail=f"domaine invalide : {domaine}")

    conn = get_db()
    if titre:
        conn.execute(
            "UPDATE notes SET titre_court = ?, titre_modifie = 1 WHERE id = ?",
            (titre, note_id)
        )
    if domaine:
        conn.execute(
            "UPDATE notes SET domaine = ? WHERE id = ?",
            (domaine, note_id)
        )
    conn.commit()
    conn.close()
    return {"updated": note_id, "titre_court": titre or None, "domaine": domaine or None}


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


# ── Calendrier ────────────────────────────────────────────────────────────────

_VALID_TYPES = {"rdv", "anniversaire", "tache", "deadline"}


@app.get("/calendar/events")
def list_calendar_events(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date:   Optional[str] = Query(None, alias="to"),
    type:      Optional[str] = Query(None),
):
    conn = get_cal_db()
    query = "SELECT e.*, GROUP_CONCAT(r.id) as reminder_ids FROM events e LEFT JOIN reminders r ON r.event_id = e.id"
    params: list = []
    conditions = []
    if from_date:
        conditions.append("e.date_debut >= ?")
        params.append(from_date)
    if to_date:
        conditions.append("e.date_debut <= ?")
        params.append(to_date)
    if type:
        conditions.append("e.type = ?")
        params.append(type)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY e.id ORDER BY e.date_debut"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/calendar/events", status_code=201)
def create_calendar_event(body: dict):
    titre = (body.get("titre") or "").strip()
    type_ = (body.get("type") or "").strip()
    date_debut = (body.get("date_debut") or "").strip()

    if not titre:
        raise HTTPException(status_code=422, detail="titre requis")
    if type_ not in _VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"type invalide — valeurs: {sorted(_VALID_TYPES)}")
    if not date_debut:
        raise HTTPException(status_code=422, detail="date_debut requis")

    now = datetime.utcnow().isoformat()
    event_id = str(_uuid.uuid4())
    conn = get_cal_db()
    conn.execute(
        "INSERT INTO events (id,titre,type,date_debut,date_fin,description,source,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (event_id, titre, type_, date_debut,
         body.get("date_fin"), body.get("description"),
         body.get("source", "electron"), now, now)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    conn.close()
    return dict(row)


@app.get("/calendar/events/{event_id}")
def get_calendar_event(event_id: str):
    conn = get_cal_db()
    row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="événement introuvable")
    reminders = conn.execute(
        "SELECT * FROM reminders WHERE event_id=? ORDER BY offset_type, offset_value",
        (event_id,)
    ).fetchall()
    conn.close()
    return {**dict(row), "reminders": [dict(r) for r in reminders]}


@app.patch("/calendar/events/{event_id}")
def patch_calendar_event(event_id: str, body: dict):
    conn = get_cal_db()
    row = conn.execute("SELECT id FROM events WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="événement introuvable")

    allowed = {"titre", "type", "date_debut", "date_fin", "description"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=422, detail="aucun champ modifiable fourni")
    if "type" in updates and updates["type"] not in _VALID_TYPES:
        raise HTTPException(status_code=422, detail="type invalide")

    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    conn.execute(
        f"UPDATE events SET {set_clause} WHERE id=?",
        [*updates.values(), event_id]
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.delete("/calendar/events/{event_id}", status_code=204)
def delete_calendar_event(event_id: str):
    conn = get_cal_db()
    row = conn.execute("SELECT id FROM events WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="événement introuvable")
    conn.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()


_VALID_OFFSET_TYPES = {"minutes", "hours", "days", "weeks"}


@app.post("/calendar/events/{event_id}/reminders", status_code=201)
def add_reminder(event_id: str, body: dict):
    conn = get_cal_db()
    row = conn.execute("SELECT id FROM events WHERE id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="événement introuvable")

    offset_type = body.get("offset_type", "")
    if offset_type not in _VALID_OFFSET_TYPES:
        conn.close()
        raise HTTPException(status_code=422, detail="offset_type invalide")
    if "offset_value" not in body:
        conn.close()
        raise HTTPException(status_code=422, detail="offset_value requis")

    rid = str(_uuid.uuid4())
    conn.execute(
        "INSERT INTO reminders (id,event_id,offset_type,offset_value,send_time) VALUES (?,?,?,?,?)",
        (rid, event_id, offset_type, int(body["offset_value"]), body.get("send_time"))
    )
    conn.commit()
    reminder = conn.execute("SELECT * FROM reminders WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(reminder)


@app.delete("/calendar/events/{event_id}/reminders/{reminder_id}", status_code=204)
def delete_reminder(event_id: str, reminder_id: str):
    conn = get_cal_db()
    row = conn.execute(
        "SELECT id FROM reminders WHERE id=? AND event_id=?", (reminder_id, event_id)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="reminder introuvable")
    conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
    conn.commit()
    conn.close()
