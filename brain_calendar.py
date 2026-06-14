"""brain_calendar.py — Scheduler rappels + sync Dropbox pour calendar.db."""
import asyncio, json, logging, os, uuid as _uuid
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

from calendar_db import CAL_DB_PATH, init_calendar_db, get_cal_db

log = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DROPBOX_CALENDAR = "/Applications/Joplin/calendar_events.json"

_ICONS  = {"rdv": "📅", "anniversaire": "🎂", "tache": "✅", "deadline": "⏰"}
_LABELS = {"rdv": "Rappel", "anniversaire": "Anniversaire", "tache": "À faire aujourd'hui", "deadline": "Deadline"}


def is_reminder_due(
    event_date: datetime,
    offset_type: str,
    offset_value: int,
    send_time: str | None,
    now: datetime,
) -> bool:
    if offset_type == "minutes":
        trigger = event_date - timedelta(minutes=offset_value)
    elif offset_type == "hours":
        trigger = event_date - timedelta(hours=offset_value)
    elif offset_type == "days":
        trigger = event_date - timedelta(days=offset_value)
        if send_time:
            h, m = map(int, send_time.split(":"))
            trigger = trigger.replace(hour=h, minute=m, second=0, microsecond=0)
        else:
            trigger = trigger.replace(hour=0, minute=0, second=0, microsecond=0)
    elif offset_type == "weeks":
        trigger = event_date - timedelta(weeks=offset_value)
    else:
        return False
    return trigger <= now


def format_reminder_message(
    titre: str,
    event_type: str,
    date_debut: str,
    offset_type: str,
    offset_value: int,
) -> str:
    icon  = _ICONS.get(event_type, "📅")
    label = _LABELS.get(event_type, "Rappel")

    try:
        dt = datetime.fromisoformat(date_debut)
        date_str = dt.strftime("%d/%m à %Hh%M") if "T" in date_debut else dt.strftime("%d/%m")
    except ValueError:
        date_str = date_debut

    if offset_type == "days" and offset_value == 0:
        timing = "aujourd'hui"
    elif offset_type == "days" and offset_value == 1:
        timing = "demain"
    elif offset_type == "days":
        timing = f"dans {offset_value} jours"
    elif offset_type == "hours" and offset_value == 1:
        timing = "dans 1 heure"
    elif offset_type == "hours":
        timing = f"dans {offset_value}h"
    elif offset_type == "weeks" and offset_value == 1:
        timing = "dans 1 semaine"
    elif offset_type == "weeks":
        timing = f"dans {offset_value} semaines"
    else:
        timing = f"dans {offset_value} min"

    return f"{icon} *{label} :* {titre} — {timing} ({date_str})"


def send_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("TELEGRAM_TOKEN ou CHAT_ID manquant — rappel non envoyé")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        log.error("Erreur envoi Telegram : %s", e)


async def loop_reminders() -> None:
    """Vérifie les rappels toutes les heures."""
    while True:
        try:
            now = datetime.utcnow()
            conn = get_cal_db()
            rows = conn.execute(
                "SELECT r.id, r.offset_type, r.offset_value, r.send_time, "
                "e.titre, e.type, e.date_debut "
                "FROM reminders r JOIN events e ON r.event_id = e.id "
                "WHERE r.sent = 0"
            ).fetchall()
            for r in rows:
                try:
                    event_date = datetime.fromisoformat(r["date_debut"])
                except ValueError:
                    continue
                if is_reminder_due(event_date, r["offset_type"], r["offset_value"], r["send_time"], now):
                    msg = format_reminder_message(
                        r["titre"], r["type"], r["date_debut"], r["offset_type"], r["offset_value"]
                    )
                    send_telegram(msg)
                    conn.execute(
                        "UPDATE reminders SET sent=1, sent_at=? WHERE id=?",
                        (now.isoformat(), r["id"])
                    )
                    conn.commit()
                    log.info("Rappel envoyé : %s", r["titre"])
            conn.close()
        except Exception as e:
            log.error("Erreur boucle rappels : %s", e)
        await asyncio.sleep(3600)  # toutes les heures


def _read_dropbox_calendar() -> list[dict]:
    try:
        import dropbox as _dbx_mod
        from brain_agent import get_dropbox
        dbx = get_dropbox()
        _, dl = dbx.files_download(DROPBOX_CALENDAR)
        return json.loads(dl.content.decode("utf-8"))
    except Exception:
        return []


def _write_dropbox_calendar(events: list[dict]) -> None:
    try:
        import dropbox as _dbx_mod
        from brain_agent import get_dropbox
        dbx = get_dropbox()
        data = json.dumps(events, ensure_ascii=False, indent=2).encode("utf-8")
        dbx.files_upload(data, DROPBOX_CALENDAR, mode=_dbx_mod.files.WriteMode.overwrite)
    except Exception as e:
        log.error("Erreur écriture Dropbox calendar : %s", e)


async def loop_dropbox_sync() -> None:
    """Sync bidirectionnelle toutes les 5 minutes."""
    while True:
        try:
            remote_events = _read_dropbox_calendar()

            conn = get_cal_db()

            # Dropbox → calendar.db : upsert events non-supprimés, supprimer les deleted
            for ev in remote_events:
                if ev.get("deleted"):
                    conn.execute("DELETE FROM events WHERE id=?", (ev["id"],))
                    continue
                now_iso = datetime.utcnow().isoformat()
                conn.execute("""
                    INSERT INTO events (id,titre,type,date_debut,date_fin,description,source,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        titre=excluded.titre, type=excluded.type, date_debut=excluded.date_debut,
                        date_fin=excluded.date_fin, description=excluded.description,
                        updated_at=excluded.updated_at
                """, (
                    ev["id"], ev["titre"], ev["type"], ev["date_debut"],
                    ev.get("date_fin"), ev.get("description"),
                    ev.get("source", "telegram"), ev.get("updated_at", now_iso), ev.get("updated_at", now_iso)
                ))
                # Sync reminders : supprime les anciens, reinsère
                conn.execute("DELETE FROM reminders WHERE event_id=? AND sent=0", (ev["id"],))
                for rem in ev.get("reminders", []):
                    conn.execute(
                        "INSERT OR IGNORE INTO reminders (id,event_id,offset_type,offset_value,send_time) "
                        "VALUES (?,?,?,?,?)",
                        (str(_uuid.uuid4()), ev["id"], rem["offset_type"], rem["offset_value"], rem.get("send_time"))
                    )
            conn.commit()

            # calendar.db → Dropbox : export complet
            all_events = conn.execute(
                "SELECT e.*, "
                "(SELECT json_group_array(json_object('offset_type',r.offset_type,'offset_value',r.offset_value,'send_time',r.send_time)) "
                " FROM reminders r WHERE r.event_id=e.id) as reminders_json "
                "FROM events e ORDER BY e.date_debut"
            ).fetchall()
            conn.close()

            export = []
            for row in all_events:
                d = dict(row)
                try:
                    d["reminders"] = json.loads(d.pop("reminders_json") or "[]")
                except (ValueError, KeyError):
                    d["reminders"] = []
                d["deleted"] = False
                export.append(d)

            _write_dropbox_calendar(export)
            log.info("Sync Dropbox : %d events exportés", len(export))

        except Exception as e:
            log.error("Erreur sync Dropbox : %s", e)

        await asyncio.sleep(300)  # toutes les 5 minutes


async def main() -> None:
    init_calendar_db()
    log.info("brain_calendar démarré")
    await asyncio.gather(
        loop_reminders(),
        loop_dropbox_sync(),
    )


if __name__ == "__main__":
    asyncio.run(main())
