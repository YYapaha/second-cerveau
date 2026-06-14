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
