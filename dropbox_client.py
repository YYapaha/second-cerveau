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
