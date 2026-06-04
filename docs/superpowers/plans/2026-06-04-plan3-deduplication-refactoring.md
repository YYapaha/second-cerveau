# Plan 3 — Déduplication & Refactoring

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Supprimer les fonctions dupliquées `extraire_champ`/`slugifier`, extraire toute la couche Dropbox dans `dropbox_client.py`, et décomposer `callback_handler` en sub-dispatchers.

**Architecture:** Refactoring pur sans changement de comportement — 3 tâches indépendantes qui peuvent être vérifiées par `ast.parse` + `pytest tests/ -q` (33 tests existants). Aucune nouvelle dépendance.

**Tech Stack:** Python 3.11, python-telegram-bot 20.x, dropbox SDK, pytest

---

## Fichiers modifiés / créés

| Fichier | Action |
|---|---|
| `reorganiser.py` | Supprimer 2 fonctions locales, ajouter import core |
| `titrer_fiches.py` | Supprimer 2 fonctions locales, consolider import core |
| `dropbox_client.py` | **Créer** — couche I/O Dropbox (~270 lignes) |
| `bot_cloud.py` | Retirer code Dropbox + constantes de chemin, refactorer callback_handler |

---

## Task 1 — Déduplication `extraire_champ` / `slugifier`

**Files:**
- Modify: `reorganiser.py:1-38`
- Modify: `titrer_fiches.py:1-46`

Ces deux fichiers définissent localement `extraire_champ()` et `slugifier()`, des fonctions déjà présentes dans `core.py`. On les supprime et on importe depuis `core`.

### `reorganiser.py`

- [ ] **Étape 1 : Retirer les 2 fonctions locales et `unicodedata`**

Ouvrir `reorganiser.py`. Supprimer les lignes 4, 26-28, 31-38 (et la ligne vide entre les deux fonctions). Le fichier passe de :

```python
import sys
import re
import shutil
import unicodedata
import logging
from pathlib import Path
...

def extraire_champ(contenu: str, champ: str) -> str:
    match = re.search(rf"\*\*{champ}\*\*\s*:\s*(.+?)(?=\n\*\*|\Z)", contenu, re.DOTALL)
    return match.group(1).strip() if match else ""


def slugifier(texte: str, max_len: int = 50) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = texte.lower()
    texte = re.sub(r"[^\w\s-]", "", texte)
    texte = re.sub(r"[\s\-]+", "_", texte)
    texte = texte.strip("_")
    return texte[:max_len].rstrip("_") or "note_sans_titre"


def type_vers_dossier(type_gemini: str) -> str:
```

À :

```python
import sys
import re
import shutil
import logging
from pathlib import Path
from core import extraire_champ, slugifier
...

def type_vers_dossier(type_gemini: str) -> str:
```

- [ ] **Étape 2 : Vérifier la syntaxe**

```powershell
cd C:\Users\yapa\second_cerveau
python -c "import ast; ast.parse(open('reorganiser.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 3 : Commit**

```powershell
git add reorganiser.py
git commit -m "refactor: importer extraire_champ/slugifier depuis core dans reorganiser.py"
```

### `titrer_fiches.py`

- [ ] **Étape 4 : Retirer les 2 fonctions locales, `unicodedata`, consolider l'import core**

Ouvrir `titrer_fiches.py`. Le début du fichier passe de :

```python
import os
import sys
import re
import time
import unicodedata
from pathlib import Path
from dotenv import load_dotenv
...

def extraire_champ(contenu: str, champ: str) -> str:
    match = re.search(rf"\*\*{champ}\*\*\s*:\s*(.+?)(?=\n\*\*|\Z)", contenu, re.DOTALL)
    return match.group(1).strip() if match else ""


def slugifier(texte: str, max_len: int = 50) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = texte.lower()
    texte = re.sub(r"[^\w\s-]", "", texte)
    texte = re.sub(r"[\s\-]+", "_", texte)
    texte = texte.strip("_")
    return texte[:max_len].rstrip("_") or "note_sans_titre"


def generer_titre(idee: str, resume: str) -> str:
    from core import appeler_groq
```

À :

```python
import os
import sys
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from core import extraire_champ, slugifier, appeler_groq
...

def generer_titre(idee: str, resume: str) -> str:
```

> Note : retirer le `from core import appeler_groq` à l'intérieur de `generer_titre()` — il est désormais au niveau module.

- [ ] **Étape 5 : Vérifier la syntaxe**

```powershell
python -c "import ast; ast.parse(open('titrer_fiches.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 6 : Lancer la suite de tests pour vérifier qu'il n'y a pas de régression**

```powershell
pytest tests/ -q
```
Attendu : `33 passed`

- [ ] **Étape 7 : Commit**

```powershell
git add titrer_fiches.py
git commit -m "refactor: importer extraire_champ/slugifier depuis core dans titrer_fiches.py"
```

---

## Task 2 — Créer `dropbox_client.py` et mettre à jour `bot_cloud.py`

**Files:**
- Create: `dropbox_client.py`
- Modify: `bot_cloud.py:5` (import), `bot_cloud.py:15-22` (import core), `bot_cloud.py:36-43` (constantes), `bot_cloud.py:49` (_METEO_DEFAULTS), `bot_cloud.py:96-362` (fonctions Dropbox)

### Étape 1 — Créer `dropbox_client.py`

- [ ] **Créer le fichier `dropbox_client.py` avec le contenu suivant :**

```python
"""
dropbox_client.py — Couche I/O Dropbox du second cerveau.
Toutes les fonctions qui lisent/écrivent sur Dropbox sont ici.
Aucune dépendance Telegram — mockable pour les tests.
"""
import os, re, json, logging
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

def get_dropbox():
    import dropbox
    token = os.environ.get("DROPBOX_ACCESS_TOKEN")
    if token:
        return dropbox.Dropbox(token)
    return dropbox.Dropbox(
        oauth2_refresh_token=os.environ.get("DROPBOX_REFRESH_TOKEN"),
        app_key=os.environ.get("DROPBOX_APP_KEY"),
        app_secret=os.environ.get("DROPBOX_APP_SECRET"),
    )

# ── Fiches ───────────────────────────────────────────────────────────────────

def uploader_fiche(fiche_md: str, contenu_brut: str | None = None) -> str:
    import dropbox as dbx_mod
    dbx = get_dropbox()
    contenu_final = construire_fiche_complete(fiche_md, contenu_brut)
    nom  = generer_nom_fichier(fiche_md)
    path = f"{DROPBOX_ROOT}/{nom}"
    dbx.files_upload(contenu_final.encode("utf-8"), path, mode=dbx_mod.files.WriteMode.overwrite)
    return path


def uploader_raw(data: bytes, nom: str) -> None:
    import dropbox as dbx_mod
    get_dropbox().files_upload(data, f"{DROPBOX_RAW}/{nom}", mode=dbx_mod.files.WriteMode.overwrite)


def lister_fiches(n: int = 5) -> list:
    import dropbox
    dbx = get_dropbox()
    try:
        res = dbx.files_list_folder(DROPBOX_ROOT)
        exclure = {"blocnotes.md", "travail.md", "projet.md"}
        fiches = [
            e for e in res.entries
            if isinstance(e, dropbox.files.FileMetadata)
            and e.name.endswith(".md")
            and e.name not in exclure
        ]
        fiches.sort(key=lambda x: x.server_modified, reverse=True)
        return fiches[:n]
    except Exception as e:
        log.warning("Erreur listage Dropbox : %s", e)
        return []


def lister_toutes_fiches(max_n: int = 50) -> list:
    """Liste toutes les fiches .md de Dropbox (pour la recherche)."""
    import dropbox
    dbx = get_dropbox()
    try:
        exclure = {"blocnotes.md", "travail.md", "projet.md"}
        res     = dbx.files_list_folder(DROPBOX_ROOT)
        fiches  = [
            e for e in res.entries
            if isinstance(e, dropbox.files.FileMetadata)
            and e.name.endswith(".md")
            and e.name not in exclure
        ]
        while res.has_more and len(fiches) < max_n:
            res = dbx.files_list_folder_continue(res.cursor)
            fiches += [
                e for e in res.entries
                if isinstance(e, dropbox.files.FileMetadata)
                and e.name.endswith(".md")
                and e.name not in exclure
            ]
        fiches.sort(key=lambda x: x.server_modified, reverse=True)
        return fiches[:max_n]
    except Exception as e:
        log.warning("Erreur listage Dropbox (toutes) : %s", e)
        return []


def telecharger_fiche(path: str) -> str:
    _, res = get_dropbox().files_download(path)
    return res.content.decode("utf-8")


def modifier_tags_dropbox(path: str, nouveaux_tags: str) -> None:
    import dropbox as dbx_mod
    dbx     = get_dropbox()
    contenu = telecharger_fiche(path)
    nouveau = re.sub(r"\*\*TAGS\*\*\s*:.*", f"**TAGS** : {nouveaux_tags}", contenu)
    dbx.files_upload(nouveau.encode("utf-8"), path, mode=dbx_mod.files.WriteMode.overwrite)


def ajouter_tag_dropbox(path: str, nouveau_tag: str) -> str:
    if not nouveau_tag.startswith("#"):
        nouveau_tag = f"#{nouveau_tag.lstrip('#')}"
    contenu      = telecharger_fiche(path)
    tags_actuels = extraire_champ(contenu, "TAGS")
    nouveaux     = f"{tags_actuels} {nouveau_tag}".strip()
    modifier_tags_dropbox(path, nouveaux)
    return nouveaux


def supprimer_tag_dropbox(path: str, tag: str) -> str:
    tag_clean    = tag.lstrip("#").lower()
    contenu      = telecharger_fiche(path)
    tags_actuels = extraire_champ(contenu, "TAGS")
    tags_liste   = [t for t in tags_actuels.split() if t.lstrip("#").lower() != tag_clean]
    nouveaux     = " ".join(tags_liste)
    modifier_tags_dropbox(path, nouveaux)
    return nouveaux


def modifier_titre_dropbox(path: str, nouveau_titre: str) -> str:
    import dropbox as dbx_mod
    dbx             = get_dropbox()
    contenu         = telecharger_fiche(path)
    nouveau_contenu = re.sub(r"^#\s+.+", f"# {nouveau_titre}", contenu, count=1, flags=re.MULTILINE)
    ancien_nom      = path.split("/")[-1]
    tag             = ancien_nom.split("_")[0]
    mots            = [m for m in slugifier(nouveau_titre).split("_") if m and m != tag.lower()][:3]
    nouveau_nom     = f"{tag}_{'_'.join(mots) or 'note'}.md"
    nouveau_path    = f"{DROPBOX_ROOT}/{nouveau_nom}"
    dbx.files_upload(nouveau_contenu.encode("utf-8"), nouveau_path, mode=dbx_mod.files.WriteMode.overwrite)
    if nouveau_path != path:
        dbx.files_delete_v2(path)
    return nouveau_path

# ── Index de déduplication ────────────────────────────────────────────────────

def charger_index_captures() -> dict:
    import dropbox as dbx_mod
    try:
        _, res = get_dropbox().files_download(DROPBOX_CAPTURES_INDEX)
        return json.loads(res.content)
    except dbx_mod.exceptions.ApiError:
        return {}


def enregistrer_capture(url: str, fiche_nom: str) -> None:
    import dropbox as dbx_mod
    index      = charger_index_captures()
    index[url] = {"fiche": fiche_nom, "date": datetime.now().strftime("%Y-%m-%d")}
    get_dropbox().files_upload(
        json.dumps(index, ensure_ascii=False, indent=2).encode(),
        DROPBOX_CAPTURES_INDEX,
        mode=dbx_mod.files.WriteMode.overwrite,
    )

# ── Bloc-notes / Travail / Projets ────────────────────────────────────────────

def lire_fichier_dropbox(path: str) -> str:
    import dropbox as dbx_mod
    try:
        _, res = get_dropbox().files_download(path)
        return "\n".join(l for l in res.content.decode("utf-8").splitlines() if l.startswith("- "))
    except dbx_mod.exceptions.ApiError:
        return ""


def _ajouter_ligne(path: str, header: str, contenu: str) -> None:
    import dropbox as dbx_mod
    dbx = get_dropbox()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    try:
        _, res = dbx.files_download(path)
        texte  = res.content.decode("utf-8")
    except dbx_mod.exceptions.ApiError:
        texte  = f"# {header}\n\n"
    dbx.files_upload(
        (texte + f"- {contenu} — {now}\n").encode("utf-8"),
        path, mode=dbx_mod.files.WriteMode.overwrite,
    )


def ajouter_blocnote(c: str): _ajouter_ligne(DROPBOX_BLOCNOTES, "Bloc-notes", c)
def ajouter_travail(c: str):  _ajouter_ligne(DROPBOX_TRAVAIL,   "Travail",    c)
def ajouter_projet(c: str):   _ajouter_ligne(DROPBOX_PROJET,    "Projets",    c)


def supprimer_taches(path: str, indices: set) -> int:
    import dropbox as dbx_mod
    dbx = get_dropbox()
    try:
        _, res = dbx.files_download(path)
        lignes = res.content.decode("utf-8").splitlines(keepends=True)
    except dbx_mod.exceptions.ApiError:
        return 0
    taches = [(i, l) for i, l in enumerate(lignes) if l.strip().startswith("- ")]
    a_sup  = {taches[i - 1][0] for i in indices if 1 <= i <= len(taches)}
    dbx.files_upload(
        "".join(l for i, l in enumerate(lignes) if i not in a_sup).encode("utf-8"),
        path, mode=dbx_mod.files.WriteMode.overwrite,
    )
    return len(a_sup)

# ── Settings ─────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    import dropbox as dbx_mod
    try:
        _, res = get_dropbox().files_download(DROPBOX_SETTINGS)
        return {**_METEO_DEFAULTS, **json.loads(res.content)}
    except dbx_mod.exceptions.ApiError:
        return dict(_METEO_DEFAULTS)


def save_settings(s: dict) -> None:
    import dropbox as dbx_mod
    get_dropbox().files_upload(
        json.dumps(s, ensure_ascii=False, indent=2).encode(),
        DROPBOX_SETTINGS,
        mode=dbx_mod.files.WriteMode.overwrite,
    )

# ── Planning ─────────────────────────────────────────────────────────────────

def load_planning() -> dict:
    import dropbox as dbx_mod
    try:
        _, res = get_dropbox().files_download(DROPBOX_PLANNING)
        return json.loads(res.content)
    except dbx_mod.exceptions.ApiError:
        return {}


def save_planning(days: dict) -> None:
    import dropbox as dbx_mod
    existing = load_planning()
    existing.update(days)
    get_dropbox().files_upload(
        json.dumps(existing, ensure_ascii=False, indent=2).encode(),
        DROPBOX_PLANNING,
        mode=dbx_mod.files.WriteMode.overwrite,
    )
```

- [ ] **Étape 2 : Vérifier la syntaxe de `dropbox_client.py`**

```powershell
python -c "import ast; ast.parse(open('dropbox_client.py').read()); print('OK')"
```
Attendu : `OK`

### Étape 3-6 — Mettre à jour `bot_cloud.py`

- [ ] **Étape 3 : Mettre à jour la ligne d'import stdlib (ligne 5)**

Remplacer :
```python
import io, os, re, sys, json, logging, tempfile, threading, unicodedata
```
Par :
```python
import io, os, re, sys, json, logging, tempfile, threading
```
(`unicodedata` n'est plus utilisé directement dans bot_cloud.py après le déplacement des fonctions Dropbox)

- [ ] **Étape 4 : Mettre à jour l'import depuis `core` (lignes 15-22)**

Remplacer :
```python
from core import (
    formater_source, extraire_champ, slugifier, generer_nom_fichier,
    nettoyer_contenu, evaluer_qualite, extraire_url,
    analyser_contenu, construire_fiche_complete,
    chercher_fiches, geocoder_ville, get_meteo,
    appeler_groq_vision,
    _WMO_FR, LIMITE_EXTRACTION,
)
```
Par :
```python
from core import (
    formater_source, extraire_champ, slugifier,
    nettoyer_contenu, evaluer_qualite, extraire_url,
    analyser_contenu, chercher_fiches, geocoder_ville, get_meteo,
    appeler_groq_vision,
    _WMO_FR, LIMITE_EXTRACTION,
)
```
(`generer_nom_fichier` et `construire_fiche_complete` sont désormais importés par `dropbox_client.py`, pas directement par `bot_cloud.py`)

- [ ] **Étape 5 : Ajouter l'import depuis `dropbox_client` juste après l'import `core`**

Après le bloc `from core import (...)`, ajouter :
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

- [ ] **Étape 6 : Supprimer les constantes et fonctions Dropbox de `bot_cloud.py`**

Supprimer exactement ces blocs (en vérifiant que les lignes correspondent) :

**Bloc 1 — constantes Dropbox (lignes 36-43 + ligne vide après) :**
```python
DROPBOX_ROOT           = "/Applications/Joplin"
DROPBOX_RAW            = "/second_cerveau/raw"
DROPBOX_BLOCNOTES      = f"{DROPBOX_ROOT}/blocnotes.md"
DROPBOX_TRAVAIL        = f"{DROPBOX_ROOT}/travail.md"
DROPBOX_PROJET         = f"{DROPBOX_ROOT}/projet.md"
DROPBOX_SETTINGS       = "/second_cerveau/settings.json"
DROPBOX_PLANNING       = "/second_cerveau/planning.json"
DROPBOX_CAPTURES_INDEX = "/second_cerveau/captures.json"
```

**Bloc 2 — `_METEO_DEFAULTS` (ligne 49) :**
```python
_METEO_DEFAULTS = {"lat": 46.29, "lon": 7.54, "ville": "Sierre, CH", "heure": 7}
```

**Bloc 3 — toutes les fonctions Dropbox (lignes 96-362) :** supprimer depuis `# ── Dropbox ─` jusqu'à (inclus) `save_planning()`. S'arrêter avant `# ── Schedulers ─`.

> Vérification : la section `# ── Schedulers ─` doit rester en place. La première ligne après les suppressions doit être le commentaire schedulers.

- [ ] **Étape 7 : Vérifier la syntaxe de `bot_cloud.py`**

```powershell
python -c "import ast; ast.parse(open('bot_cloud.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 8 : Lancer les tests**

```powershell
pytest tests/ -q
```
Attendu : `33 passed`

- [ ] **Étape 9 : Commit**

```powershell
git add dropbox_client.py bot_cloud.py
git commit -m "refactor: extraire couche Dropbox dans dropbox_client.py"
```

---

## Task 3 — Refactoring `callback_handler` en sub-dispatchers

**Files:**
- Modify: `bot_cloud.py` — section callbacks (actuellement lignes ~976-1265)

`callback_handler` est une fonction de 267 lignes avec 17 blocs `if` plats. On la remplace par un dispatcher de ~20 lignes + 5 sous-fonctions thématiques.

- [ ] **Étape 1 : Ajouter les 5 sub-dispatchers juste avant `callback_handler`**

Localiser la ligne `# ── Callbacks ─` dans `bot_cloud.py`. Juste avant `async def callback_handler(...)`, insérer les 5 fonctions suivantes (dans cet ordre) :

```python
async def _cb_capture(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query, data: str
) -> None:
    if data == "capture:cancel":
        context.user_data.pop("pending_capture", None)
        context.user_data.pop("pending_url", None)
        await query.edit_message_text("❌ Capture annulée.")
        return

    if data == "capture:ok":
        pending = context.user_data.pop("pending_capture", None)
        if not pending:
            await query.edit_message_text("❌ Session expirée. Renvoie le contenu.")
            return
        await query.edit_message_text("⏳ Analyse en cours…")
        try:
            await _analyser_et_uploader(
                query.message,
                pending["contenu"],
                pending["source"],
                contenu_brut=pending.get("contenu_brut"),
            )
        except Exception as e:
            log.exception("Erreur capture:ok")
            await query.message.edit_text(erreur_msg(e))
        return

    if data == "capture:url:recapture":
        url = context.user_data.pop("pending_url", None)
        if not url:
            await query.edit_message_text("❌ Session expirée. Renvoie l'URL.")
            return
        await query.edit_message_text("⏳ Extraction en cours…")
        contenu_raw, _ = await _extraire_url_avec_msg(query.message, url)
        if contenu_raw is None:
            return
        contenu_propre, _ = nettoyer_contenu(contenu_raw)
        try:
            await _analyser_et_uploader(query.message, contenu_propre, url, contenu_brut=contenu_propre)
        except Exception as e:
            log.exception("Erreur recapture")
            await query.message.edit_text(erreur_msg(e))


async def _cb_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query, data: str
) -> None:
    if data == "menu:dernieres":
        fiches = lister_fiches(5)
        if not fiches:
            await query.edit_message_text("Aucune fiche pour l'instant.")
            return
        lignes = ["📚 *5 dernières fiches :*\n"]
        for f in fiches:
            lignes.append(f"• `{f.name}` _{f.server_modified.strftime('%d/%m %H:%M')}_")
        await query.edit_message_text(
            "\n".join(lignes), parse_mode="Markdown",
            reply_markup=kb_liste_fiches(fiches, prefix="edit_fiche"),
        )
        return

    if data == "menu:modifier":
        fiches = lister_fiches(5)
        if not fiches:
            await query.edit_message_text("Aucune fiche à modifier.")
            return
        await query.edit_message_text(
            "✏️ *Quelle fiche veux-tu modifier ?*", parse_mode="Markdown",
            reply_markup=kb_liste_fiches(fiches, prefix="edit_fiche"),
        )
        return

    if data == "menu:chercher":
        context.user_data["pending_edit"] = {"type": "chercher_query"}
        await query.edit_message_text(
            "🔍 Envoie les mots-clés à rechercher :\n_(ou tape_ `/chercher mots-clés` _directement)_",
            parse_mode="Markdown",
        )
        return

    if data == "menu:travail":
        taches = lire_fichier_dropbox(DROPBOX_TRAVAIL).splitlines()
        if not taches:
            await query.edit_message_text("💼 Aucune tâche travail en cours !", reply_markup=kb_menu_principal())
        else:
            lignes = ["💼 *Tâches travail :*\n"] + [f"  T{i+1} {t}" for i, t in enumerate(taches)]
            await query.edit_message_text("\n".join(lignes), parse_mode="Markdown", reply_markup=kb_menu_principal())
        return

    if data == "menu:blocnotes":
        notes = lire_fichier_dropbox(DROPBOX_BLOCNOTES).splitlines()
        if not notes:
            await query.edit_message_text("📝 Bloc-notes vide !", reply_markup=kb_menu_principal())
        else:
            lignes = ["📝 *Bloc-notes :*\n"] + [f"  B{i+1} {n}" for i, n in enumerate(notes)]
            await query.edit_message_text("\n".join(lignes), parse_mode="Markdown", reply_markup=kb_menu_principal())
        return

    if data == "menu:projets":
        notes = lire_fichier_dropbox(DROPBOX_PROJET).splitlines()
        if not notes:
            await query.edit_message_text("🚀 Aucun projet en cours !", reply_markup=kb_menu_principal())
        else:
            lignes = ["🚀 *Projets en cours :*\n"] + [f"  P{i+1} {n}" for i, n in enumerate(notes)]
            await query.edit_message_text("\n".join(lignes), parse_mode="Markdown", reply_markup=kb_menu_principal())
        return

    if data == "menu:accueil":
        await query.edit_message_text(
            "🧠 *Second Cerveau* — Que veux-tu faire ?", parse_mode="Markdown",
            reply_markup=kb_menu_principal(),
        )
        return

    if data == "menu:planning":
        await query.edit_message_text(
            "📅 *Mon planning*",
            parse_mode="Markdown", reply_markup=kb_planning_menu(),
        )
        return

    if data == "menu:meteo":
        cfg = load_settings()
        await query.edit_message_text(
            f"⚙️ *Réglages météo*\n\n📍 Ville : *{cfg['ville']}*\n⏰ Heure : *{cfg['heure']}h00*",
            parse_mode="Markdown", reply_markup=kb_meteo_settings(),
        )
        return


async def _cb_fiche(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query, data: str
) -> None:
    if data.startswith("edit_fiche:"):
        filename = data[len("edit_fiche:"):]
        await query.edit_message_text(
            f"✏️ *{filename}*\n\nQue veux-tu modifier ?", parse_mode="Markdown",
            reply_markup=kb_modifier_fiche(filename),
        )
        return

    if data.startswith("edit_tags:"):
        filename     = data[len("edit_tags:"):]
        path         = f"{DROPBOX_ROOT}/{filename}"
        tags_actuels = extraire_champ(telecharger_fiche(path), "TAGS")
        await query.edit_message_text(
            f"🏷️ *Tags actuels :* `{tags_actuels or 'aucun'}`\n\nQue veux-tu faire ?",
            parse_mode="Markdown", reply_markup=kb_tags_menu(filename),
        )
        return

    if data.startswith("ta:"):
        filename = data[3:]
        context.user_data["pending_edit"] = {"filename": filename, "type": "tags_add"}
        await query.edit_message_text("➕ Envoie le tag à ajouter _(ex : #python)_ :", parse_mode="Markdown")
        return

    if data.startswith("tr:"):
        filename     = data[3:]
        path         = f"{DROPBOX_ROOT}/{filename}"
        tags_actuels = extraire_champ(telecharger_fiche(path), "TAGS")
        tags_liste   = [t for t in tags_actuels.split() if t.startswith("#")]
        if not tags_liste:
            await query.edit_message_text("Aucun tag à supprimer.")
            return
        await query.edit_message_text(
            "➖ *Quel tag veux-tu enlever ?*", parse_mode="Markdown",
            reply_markup=kb_tags_liste(filename, tags_liste),
        )
        return

    if data.startswith("td:"):
        _, filename, tag = data.split(":", 2)
        path     = f"{DROPBOX_ROOT}/{filename}"
        restants = supprimer_tag_dropbox(path, tag)
        await query.edit_message_text(
            f"✅ Tag `#{tag}` supprimé.\nTags restants : `{restants or 'aucun'}`",
            parse_mode="Markdown",
        )
        return

    if data.startswith("tw:"):
        filename = data[3:]
        context.user_data["pending_edit"] = {"filename": filename, "type": "tags_rewrite"}
        await query.edit_message_text(
            "🔄 Envoie les nouveaux tags _(ex : #react #python #api)_ :", parse_mode="Markdown",
        )
        return

    if data.startswith("edit_title:"):
        filename     = data[len("edit_title:"):]
        path         = f"{DROPBOX_ROOT}/{filename}"
        titre_actuel = extraire_champ(telecharger_fiche(path), "TITRE")
        context.user_data["pending_edit"] = {"filename": filename, "type": "title"}
        await query.edit_message_text(
            f"✏️ *Titre actuel :*\n`{titre_actuel}`\n\nEnvoie le nouveau titre _(2-3 mots, très descriptif)_ :",
            parse_mode="Markdown",
        )
        return


async def _cb_planning(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query, data: str
) -> None:
    if data == "planning:voir":
        planning = load_planning()
        debut    = datetime.now() - timedelta(days=datetime.now().weekday())
        lignes   = ["📅 *Semaine en cours :*\n"]
        trouve   = False
        for i in range(7):
            d = (debut + timedelta(days=i)).strftime("%Y-%m-%d")
            if d in planning:
                trouve = True
                c      = planning[d]
                emoji, label = _SHIFTS_FR.get(c, ("📅", c))
                dt = datetime.strptime(d, "%Y-%m-%d")
                lignes.append(f"• {_JOURS_FR[dt.weekday()]} {dt.strftime('%d/%m')} : {emoji} *{c}* — {label}")
        if not trouve:
            lignes.append("_Aucune donnée pour cette semaine._\nUploade ton planning !")
        await query.edit_message_text(
            "\n".join(lignes), parse_mode="Markdown", reply_markup=kb_planning_menu(),
        )


async def _cb_meteo(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query, data: str
) -> None:
    if data == "ms:ville":
        context.user_data["pending_edit"] = {"type": "meteo_ville"}
        await query.edit_message_text(
            "📍 Envoie le nom de ta ville _(ex : Genève, CH)_ :", parse_mode="Markdown",
        )
        return

    if data == "ms:heure":
        cfg = load_settings()
        await query.edit_message_text(
            "⏰ *À quelle heure recevoir la météo ?*", parse_mode="Markdown",
            reply_markup=kb_meteo_heures(cfg["heure"]),
        )
        return

    if data.startswith("ms:h:"):
        heure = int(data[5:])
        cfg   = load_settings()
        cfg["heure"] = heure
        save_settings(cfg)
        reprogrammer_meteo(context.application, heure)
        await query.edit_message_text(
            f"✅ Météo reprogrammée à *{heure}h00* chaque matin.", parse_mode="Markdown",
            reply_markup=kb_meteo_settings(),
        )
        return

    if data == "meteo:voir":
        cfg = load_settings()
        try:
            texte = get_meteo(cfg["lat"], cfg["lon"], cfg["ville"])
        except Exception as e:
            log.warning("Erreur météo (bouton) : %s", e)
            texte = erreur_msg(e)
        await query.edit_message_text(
            texte, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("↩️ Retour", callback_data="menu:accueil")]]),
        )
        return
```

> Note : dans `_cb_planning`, la variable locale `trouvé` (avec accent) a été renommée en `trouve` pour éviter tout problème d'encodage dans certains éditeurs. Le comportement est identique.

- [ ] **Étape 2 : Remplacer le corps de `callback_handler` par le dispatcher**

Localiser `async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:`. Remplacer tout son contenu (garde la signature, remplace le corps) par :

```python
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if TELEGRAM_CHAT_ID and update.effective_chat.id != int(TELEGRAM_CHAT_ID):
        return

    query = update.callback_query
    await query.answer()
    data  = query.data

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

- [ ] **Étape 3 : Vérifier la syntaxe de `bot_cloud.py`**

```powershell
python -c "import ast; ast.parse(open('bot_cloud.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 4 : Lancer les tests**

```powershell
pytest tests/ -q
```
Attendu : `33 passed`

- [ ] **Étape 5 : Commit**

```powershell
git add bot_cloud.py
git commit -m "refactor: decomposer callback_handler en 5 sub-dispatchers"
```

---

## Checklist de vérification finale

```powershell
cd C:\Users\yapa\second_cerveau
python -c "import ast; ast.parse(open('reorganiser.py').read()); print('reorganiser OK')"
python -c "import ast; ast.parse(open('titrer_fiches.py').read()); print('titrer_fiches OK')"
python -c "import ast; ast.parse(open('dropbox_client.py').read()); print('dropbox_client OK')"
python -c "import ast; ast.parse(open('bot_cloud.py').read()); print('bot_cloud OK')"
pytest tests/ -q
```

Attendu : 4 × `OK` + `33 passed`.
