# Plan 3 — Déduplication & Refactoring

**Date :** 2026-06-04  
**Statut :** Approuvé pour implémentation  
**Contexte :** Troisième plan de remboursement de dette technique du second cerveau. Fait suite au Plan 1 (Sécurité & stabilité) et au Plan 2 (Unification LLM).

---

## Objectif

Approche C :
1. **Déduplication** — supprimer `extraire_champ()` et `slugifier()` locaux dans `reorganiser.py` et `titrer_fiches.py`, importer depuis `core`
2. **Extraction Dropbox** — créer `dropbox_client.py` avec tout le code I/O Dropbox (~267 lignes extraites de `bot_cloud.py`)
3. **Refactoring callback_handler** — décomposer la fonction plate de 267 lignes en 5 sub-dispatchers

Résultat : `bot_cloud.py` tombe de ~1381 lignes à ~1114 lignes ; `dropbox_client.py` devient mockable à 100 % pour le Plan 4 (Tests).

---

## Section 1 — Déduplication `extraire_champ` / `slugifier`

### Fichiers touchés

| Fichier | Lignes à supprimer | Import à ajouter |
|---|---|---|
| `reorganiser.py` | `extraire_champ` (26-28), `slugifier` (31-38) | `from core import extraire_champ, slugifier` |
| `titrer_fiches.py` | `extraire_champ` (21-23), `slugifier` (26-33) | `from core import extraire_champ, slugifier` |

### `reorganiser.py` — détail

**Supprimer lignes 26-28 :**
```python
def extraire_champ(contenu: str, champ: str) -> str:
    match = re.search(rf"\*\*{champ}\*\*\s*:\s*(.+?)(?=\n\*\*|\Z)", contenu, re.DOTALL)
    return match.group(1).strip() if match else ""
```

**Supprimer lignes 31-38 :**
```python
def slugifier(texte: str, max_len: int = 50) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = texte.lower()
    texte = re.sub(r"[^\w\s-]", "", texte)
    texte = re.sub(r"[\s\-]+", "_", texte)
    texte = texte.strip("_")
    return texte[:max_len].rstrip("_") or "note_sans_titre"
```

**Ajouter après les imports :**
```python
from core import extraire_champ, slugifier
```

**`unicodedata` (ligne 4) :** vérifier si encore utilisé ailleurs dans `reorganiser.py` avant de supprimer. Si non utilisé → supprimer l'import.

### `titrer_fiches.py` — détail

**Supprimer lignes 21-23 :**
```python
def extraire_champ(contenu: str, champ: str) -> str:
    match = re.search(rf"\*\*{champ}\*\*\s*:\s*(.+?)(?=\n\*\*|\Z)", contenu, re.DOTALL)
    return match.group(1).strip() if match else ""
```

**Supprimer lignes 26-33 :**
```python
def slugifier(texte: str, max_len: int = 50) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = texte.lower()
    texte = re.sub(r"[^\w\s-]", "", texte)
    texte = re.sub(r"[\s\-]+", "_", texte)
    texte = texte.strip("_")
    return texte[:max_len].rstrip("_") or "note_sans_titre"
```

**Ajouter dans les imports :**
```python
from core import extraire_champ, slugifier, appeler_groq
```
(remplace le `from core import appeler_groq` existant à la ligne 37)

**`unicodedata` (ligne 8) :** supprimer si non utilisé ailleurs dans `titrer_fiches.py`.

---

## Section 2 — Nouveau fichier `dropbox_client.py`

### Structure du fichier

```python
"""
dropbox_client.py — Couche I/O Dropbox du second cerveau.
Toutes les fonctions qui lisent/écrivent sur Dropbox sont ici.
Aucune dépendance Telegram — mockable pour les tests.
"""
import os, json, logging
from datetime import datetime

from core import extraire_champ, slugifier, generer_nom_fichier, construire_fiche_complete

log = logging.getLogger(__name__)

# ── Chemins Dropbox ──────────────────────────────────────────────────────────
DROPBOX_ROOT           = "/Applications/Joplin"
DROPBOX_RAW            = "/second_cerveau/raw"
DROPBOX_BLOCNOTES      = f"{DROPBOX_ROOT}/blocnotes.md"
DROPBOX_TRAVAIL        = f"{DROPBOX_ROOT}/travail.md"
DROPBOX_PROJET         = f"{DROPBOX_ROOT}/projet.md"
DROPBOX_SETTINGS       = "/second_cerveau/settings.json"
DROPBOX_PLANNING       = "/second_cerveau/planning.json"
DROPBOX_CAPTURES_INDEX = "/second_cerveau/captures.json"

_METEO_DEFAULTS = {"lat": 46.29, "lon": 7.54, "ville": "Sierre, CH", "heure": 7}

# ── Auth ─────────────────────────────────────────────────────────────────────
def get_dropbox(): ...

# ── Fiches ───────────────────────────────────────────────────────────────────
def uploader_fiche(fiche_md, contenu_brut=None) -> str: ...
def uploader_raw(data, nom) -> None: ...
def lister_fiches(n=5) -> list: ...
def lister_toutes_fiches(max_n=50) -> list: ...
def telecharger_fiche(path) -> str: ...
def modifier_tags_dropbox(path, nouveaux_tags) -> None: ...
def ajouter_tag_dropbox(path, nouveau_tag) -> str: ...
def supprimer_tag_dropbox(path, tag) -> str: ...
def modifier_titre_dropbox(path, nouveau_titre) -> str: ...

# ── Index déduplication ───────────────────────────────────────────────────────
def charger_index_captures() -> dict: ...
def enregistrer_capture(url, fiche_nom) -> None: ...

# ── Bloc-notes / Travail / Projets ────────────────────────────────────────────
def lire_fichier_dropbox(path) -> str: ...
def _ajouter_ligne(path, header, contenu) -> None: ...
def ajouter_blocnote(c) -> None: ...
def ajouter_travail(c) -> None: ...
def ajouter_projet(c) -> None: ...
def supprimer_taches(path, indices) -> int: ...

# ── Settings ─────────────────────────────────────────────────────────────────
def load_settings() -> dict: ...
def save_settings(s) -> None: ...

# ── Planning ─────────────────────────────────────────────────────────────────
def load_planning() -> dict: ...
def save_planning(days) -> None: ...
```

### Fonctions déplacées (code source exact — copier tel quel)

Le code de chaque fonction est identique à celui dans `bot_cloud.py` lignes 98-362. Aucune modification de comportement.

### Changements `bot_cloud.py`

**Supprimer :**
- Lignes 36-43 (constantes DROPBOX_ROOT … DROPBOX_CAPTURES_INDEX)
- Ligne 49 (`_METEO_DEFAULTS`)
- Lignes 96-362 (toutes les fonctions Dropbox)

**Remplacer par :**
```python
from dropbox_client import (
    DROPBOX_ROOT, DROPBOX_RAW, DROPBOX_BLOCNOTES, DROPBOX_TRAVAIL,
    DROPBOX_PROJET, DROPBOX_SETTINGS, DROPBOX_PLANNING, DROPBOX_CAPTURES_INDEX,
    get_dropbox, uploader_fiche, uploader_raw,
    lister_fiches, lister_toutes_fiches, telecharger_fiche,
    modifier_tags_dropbox, ajouter_tag_dropbox, supprimer_tag_dropbox,
    modifier_titre_dropbox, charger_index_captures, enregistrer_capture,
    lire_fichier_dropbox, _ajouter_ligne, ajouter_blocnote, ajouter_travail,
    ajouter_projet, supprimer_taches, load_settings, save_settings,
    load_planning, save_planning,
)
```

**Import `from core import ...` (ligne 15-22) — retirer `generer_nom_fichier` et `construire_fiche_complete`** (désormais utilisés uniquement par `dropbox_client.py`, qui les importe lui-même) :
```python
from core import (
    formater_source, extraire_champ, slugifier,
    nettoyer_contenu, evaluer_qualite, extraire_url,
    analyser_contenu, chercher_fiches, geocoder_ville, get_meteo,
    appeler_groq_vision,
    _WMO_FR, LIMITE_EXTRACTION,
)
```

**`unicodedata` dans `import io, os, re, sys, json, logging, tempfile, threading, unicodedata` (ligne 5) :** vérifier s'il est encore utilisé dans le reste de `bot_cloud.py` après extraction. Si non → supprimer.

---

## Section 3 — Refactoring `callback_handler`

### Avant (267 lignes plates, lignes 998-1265)

17 blocs `if/elif` dans une seule fonction.

### Après : dispatcher + 5 sub-dispatchers

**Dispatcher principal (≈ 20 lignes) :**

```python
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if TELEGRAM_CHAT_ID and update.effective_chat.id != int(TELEGRAM_CHAT_ID):
        return
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "ignore":
        await query.edit_message_reply_markup(reply_markup=None)
    elif data.startswith("capture:"):
        await _cb_capture(update, context, query, data)
    elif data.startswith("menu:"):
        await _cb_menu(update, context, query, data)
    elif data.startswith(("edit_fiche:", "edit_tags:", "edit_title:", "ta:", "tr:", "td:", "tw:")):
        await _cb_fiche(update, context, query, data)
    elif data.startswith("planning:"):
        await _cb_planning(update, context, query, data)
    elif data.startswith("ms:") or data == "meteo:voir":
        await _cb_meteo(update, context, query, data)
```

**Signature commune des sub-dispatchers :**
```python
async def _cb_XXX(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query,        # update.callback_query (déjà answered)
    data: str,
) -> None:
```

**Sub-dispatchers et leur contenu :**

| Fonction | Préfixes / valeurs | Lignes source |
|---|---|---|
| `_cb_capture` | `capture:cancel`, `capture:ok`, `capture:url:recapture` | 1012-1051 |
| `_cb_menu` | `menu:dernieres`, `menu:modifier`, `menu:chercher`, `menu:travail`, `menu:blocnotes`, `menu:projets`, `menu:accueil`, `menu:planning`, `menu:meteo` | 1053-1119, 1189-1195, 1218-1224 |
| `_cb_fiche` | `edit_fiche:*`, `edit_tags:*`, `edit_title:*`, `ta:*`, `tr:*`, `td:*`, `tw:*` | 1121-1187 |
| `_cb_planning` | `planning:voir` | 1197-1215 |
| `_cb_meteo` | `ms:ville`, `ms:heure`, `ms:h:*`, `meteo:voir` | 1226-1264 |

> Note : `menu:planning` et `menu:meteo` (qui affichent juste un clavier de sous-menu) restent dans `_cb_menu` car ils n'accèdent pas aux données — ils naviguent seulement.

**Code source de chaque sub-dispatcher :** copier le contenu des blocs `if data == ...` correspondants, sans modification de logique. Retirer les `return` terminaux (remplacés par la structure `elif` du dispatcher).

**Position dans le fichier :** les 5 sub-dispatchers sont définis juste avant `callback_handler`, dans l'ordre : `_cb_capture`, `_cb_menu`, `_cb_fiche`, `_cb_planning`, `_cb_meteo`.

---

## Fichiers modifiés / créés

| Fichier | Action | Changement net |
|---|---|---|
| `reorganiser.py` | Modifier | -13 lignes (2 fonctions supprimées) |
| `titrer_fiches.py` | Modifier | -13 lignes (2 fonctions supprimées) |
| `dropbox_client.py` | **Créer** | +~270 lignes |
| `bot_cloud.py` | Modifier | -267 lignes (Dropbox) + -245 lignes (callback inline) + import update |

**Dépendances :** aucune nouvelle. `dropbox` et `core` déjà présents.

**Tests :** `reorganiser.py` et `titrer_fiches.py` n'ont pas de tests — pas de fichiers test à mettre à jour pour la Section 1. `bot_cloud.py` n'a pas de tests — les 33 tests existants dans `tests/` ne sont pas affectés.

---

## Vérification après chaque section

```powershell
cd C:\Users\yapa\second_cerveau
python -c "import ast; ast.parse(open('reorganiser.py').read()); print('reorganiser OK')"
python -c "import ast; ast.parse(open('titrer_fiches.py').read()); print('titrer_fiches OK')"
python -c "import ast; ast.parse(open('dropbox_client.py').read()); print('dropbox_client OK')"
python -c "import ast; ast.parse(open('bot_cloud.py').read()); print('bot_cloud OK')"
pytest tests/ -q
```

Attendu : 4 × `OK` + `33 passed`.
