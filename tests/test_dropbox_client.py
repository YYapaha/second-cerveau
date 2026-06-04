import sys, json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

import dropbox as _dbx_real  # pour exceptions.ApiError


def make_mock_dbx(download_content: bytes = b"{}"):
    """Retourne un MagicMock configuré comme client Dropbox."""
    dbx = MagicMock()
    dl  = MagicMock()
    dl.content = download_content
    dbx.files_download.return_value = (None, dl)
    return dbx


def make_api_error():
    """Construit un dropbox.exceptions.ApiError minimal."""
    try:
        return _dbx_real.exceptions.ApiError(
            "req-1", MagicMock(), "An error occurred", "en"
        )
    except Exception:
        err = object.__new__(_dbx_real.exceptions.ApiError)
        Exception.__init__(err, "ApiError de test")
        return err


# ── Tags ─────────────────────────────────────────────────────────────────────

from dropbox_client import ajouter_tag_dropbox, supprimer_tag_dropbox

def test_ajouter_tag_prefixe_diese():
    fiche = "**TAGS** : #python\n**TITRE** : test"
    dbx   = make_mock_dbx(fiche.encode())
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = ajouter_tag_dropbox("/test/fiche.md", "api")
    assert "#api" in result

def test_ajouter_tag_ne_double_pas_diese():
    fiche = "**TAGS** : #python\n**TITRE** : test"
    dbx   = make_mock_dbx(fiche.encode())
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = ajouter_tag_dropbox("/test/fiche.md", "#api")
    assert result.count("#api") == 1

def test_supprimer_tag_retire_le_bon():
    fiche = "**TAGS** : #python #api #web\n**TITRE** : test"
    dbx   = make_mock_dbx(fiche.encode())
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = supprimer_tag_dropbox("/test/fiche.md", "api")
    assert "#api" not in result
    assert "#python" in result
    assert "#web" in result

def test_supprimer_tag_insensible_casse():
    fiche = "**TAGS** : #Python #api\n**TITRE** : test"
    dbx   = make_mock_dbx(fiche.encode())
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = supprimer_tag_dropbox("/test/fiche.md", "PYTHON")
    assert "#Python" not in result

def test_supprimer_tag_absent_ne_plante_pas():
    fiche = "**TAGS** : #python\n**TITRE** : test"
    dbx   = make_mock_dbx(fiche.encode())
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = supprimer_tag_dropbox("/test/fiche.md", "inexistant")
    assert "#python" in result

# ── Captures index ────────────────────────────────────────────────────────────

from dropbox_client import charger_index_captures, enregistrer_capture

def test_charger_index_api_error_retourne_dict_vide():
    dbx = MagicMock()
    dbx.files_download.side_effect = make_api_error()
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = charger_index_captures()
    assert result == {}

def test_enregistrer_capture_ajoute_entree():
    existing = json.dumps({"https://old.com": {"fiche": "OLD.md", "date": "2026-01-01"}})
    dbx      = make_mock_dbx(existing.encode())
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        enregistrer_capture("https://new.com", "NEW.md")
    uploaded = json.loads(dbx.files_upload.call_args[0][0].decode())
    assert "https://new.com" in uploaded
    assert uploaded["https://new.com"]["fiche"] == "NEW.md"
    assert "https://old.com" in uploaded  # ancien entrée conservée

# ── Bloc-notes / tâches ───────────────────────────────────────────────────────

from dropbox_client import lire_fichier_dropbox, supprimer_taches, DROPBOX_TRAVAIL

def test_lire_fichier_dropbox_filtre_lignes():
    contenu = b"# Titre\n- tache 1\nligne normale\n- tache 2\n"
    dbx     = make_mock_dbx(contenu)
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = lire_fichier_dropbox(DROPBOX_TRAVAIL)
    lignes = result.splitlines()
    assert all(l.startswith("- ") for l in lignes)
    assert len(lignes) == 2

def test_lire_fichier_api_error_retourne_vide():
    dbx = MagicMock()
    dbx.files_download.side_effect = make_api_error()
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = lire_fichier_dropbox(DROPBOX_TRAVAIL)
    assert result == ""

def test_supprimer_taches_retire_bonne_ligne():
    contenu = b"# Travail\n- tache A\n- tache B\n- tache C\n"
    dbx     = make_mock_dbx(contenu)
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        n = supprimer_taches(DROPBOX_TRAVAIL, {2})  # indice 1-based → tache B
    assert n == 1
    uploaded = dbx.files_upload.call_args[0][0].decode()
    assert "tache A" in uploaded
    assert "tache B" not in uploaded
    assert "tache C" in uploaded

# ── Settings / Planning ───────────────────────────────────────────────────────

from dropbox_client import (
    load_settings, save_settings, load_planning, save_planning, _METEO_DEFAULTS
)

def test_load_settings_api_error_retourne_defaults():
    dbx = MagicMock()
    dbx.files_download.side_effect = make_api_error()
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = load_settings()
    assert result == _METEO_DEFAULTS

def test_load_settings_merge_avec_defaults():
    stored = json.dumps({"heure": 8})  # seulement heure renseignée
    dbx    = make_mock_dbx(stored.encode())
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        result = load_settings()
    assert result["heure"] == 8
    assert "lat" in result   # depuis _METEO_DEFAULTS

def test_load_planning_api_error_retourne_dict_vide():
    dbx = MagicMock()
    dbx.files_download.side_effect = make_api_error()
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        assert load_planning() == {}

def test_save_planning_merge_avec_existant():
    existing = json.dumps({"2026-06-01": "Repos"})
    dbx      = make_mock_dbx(existing.encode())
    with patch("dropbox_client.get_dropbox", return_value=dbx):
        save_planning({"2026-06-04": "Matin"})
    uploaded = json.loads(dbx.files_upload.call_args[0][0].decode())
    assert uploaded["2026-06-01"] == "Repos"   # ancien conservé
    assert uploaded["2026-06-04"] == "Matin"   # nouveau ajouté
