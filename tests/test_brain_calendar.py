# tests/test_brain_calendar.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime


def test_is_reminder_due_days():
    from brain_calendar import is_reminder_due
    now = datetime(2026, 6, 18, 13, 0)
    event_date = datetime(2026, 6, 19, 14, 0)
    assert is_reminder_due(event_date, "days", 1, None, now)


def test_is_reminder_not_due_too_early():
    from brain_calendar import is_reminder_due
    now = datetime(2026, 6, 17, 13, 0)
    event_date = datetime(2026, 6, 19, 14, 0)
    assert not is_reminder_due(event_date, "days", 1, None, now)


def test_is_reminder_due_hours():
    from brain_calendar import is_reminder_due
    now = datetime(2026, 6, 19, 13, 5)
    event_date = datetime(2026, 6, 19, 14, 0)
    assert is_reminder_due(event_date, "hours", 1, None, now)


def test_is_reminder_due_send_time():
    from brain_calendar import is_reminder_due
    now = datetime(2026, 6, 14, 9, 5)
    event_date = datetime(2026, 6, 14, 14, 0)
    assert is_reminder_due(event_date, "days", 0, "09:00", now)


def test_is_reminder_send_time_not_yet():
    from brain_calendar import is_reminder_due
    now = datetime(2026, 6, 14, 8, 55)
    event_date = datetime(2026, 6, 14, 14, 0)
    assert not is_reminder_due(event_date, "days", 0, "09:00", now)


def test_is_reminder_due_weeks():
    from brain_calendar import is_reminder_due
    now = datetime(2026, 6, 12, 10, 0)
    event_date = datetime(2026, 6, 19, 10, 0)
    assert is_reminder_due(event_date, "weeks", 1, None, now)


def test_format_message_rdv():
    from brain_calendar import format_reminder_message
    msg = format_reminder_message("RDV Médecin", "rdv", "2026-06-19T14:00", "days", 1)
    assert "📅" in msg
    assert "RDV Médecin" in msg
    assert "demain" in msg


def test_format_message_anniversaire():
    from brain_calendar import format_reminder_message
    msg = format_reminder_message("Fête maman", "anniversaire", "2026-06-19", "weeks", 1)
    assert "🎂" in msg
    assert "Fête maman" in msg
    assert "1 semaine" in msg


def test_format_message_deadline():
    from brain_calendar import format_reminder_message
    msg = format_reminder_message("Rendu projet", "deadline", "2026-06-23", "days", 0)
    assert "⏰" in msg
    assert "aujourd'hui" in msg


def test_format_message_tache():
    from brain_calendar import format_reminder_message
    msg = format_reminder_message("Appeler notaire", "tache", "2026-06-14", "days", 0)
    assert "✅" in msg
