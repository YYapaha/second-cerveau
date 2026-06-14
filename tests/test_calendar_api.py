# tests/test_calendar_api.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    cal_db = tmp_path / "calendar.db"
    monkeypatch.setattr("brain_server.CAL_DB_PATH", cal_db)
    from calendar_db import init_calendar_db
    init_calendar_db(cal_db)
    # Lazy import après le patch pour que CAL_DB_PATH soit correct
    import importlib, brain_server
    importlib.reload(brain_server)
    return TestClient(brain_server.app)


def test_list_events_empty(client):
    r = client.get("/calendar/events")
    assert r.status_code == 200
    assert r.json() == []


def test_create_event_minimal(client):
    r = client.post("/calendar/events", json={
        "titre": "RDV Médecin",
        "type": "rdv",
        "date_debut": "2026-06-19T14:00"
    })
    assert r.status_code == 201
    data = r.json()
    assert data["titre"] == "RDV Médecin"
    assert "id" in data


def test_create_event_invalid_type(client):
    r = client.post("/calendar/events", json={
        "titre": "Test",
        "type": "inconnu",
        "date_debut": "2026-06-19"
    })
    assert r.status_code == 422


def test_create_event_missing_titre(client):
    r = client.post("/calendar/events", json={
        "type": "rdv",
        "date_debut": "2026-06-19"
    })
    assert r.status_code == 422


def test_list_events_returns_created(client):
    client.post("/calendar/events", json={
        "titre": "Anniversaire maman",
        "type": "anniversaire",
        "date_debut": "2026-06-19"
    })
    r = client.get("/calendar/events")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["titre"] == "Anniversaire maman"


def test_list_events_filter_by_type(client):
    client.post("/calendar/events", json={"titre": "A", "type": "rdv", "date_debut": "2026-06-19"})
    client.post("/calendar/events", json={"titre": "B", "type": "tache", "date_debut": "2026-06-20"})
    r = client.get("/calendar/events?type=rdv")
    assert r.status_code == 200
    assert all(e["type"] == "rdv" for e in r.json())
