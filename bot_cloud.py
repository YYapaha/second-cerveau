"""
bot_cloud.py — Second Cerveau Bot Telegram (Railway)
Capture → OpenAI → Dropbox | Menus inline | Modification de fiches
"""
import io, os, re, sys, json, logging, tempfile, unicodedata
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)

from core import (
    formater_source, extraire_champ, slugifier, generer_nom_fichier,
    nettoyer_contenu, evaluer_qualite, extraire_url,
    analyser_contenu, construire_fiche_complete,
    chercher_fiches, geocoder_ville, get_meteo,
    _WMO_FR, LIMITE_EXTRACTION,
)

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY     = os.environ.get("OPENAI_API_KEY", "")
TELEGRAM_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
DROPBOX_TOKEN      = os.environ.get("DROPBOX_ACCESS_TOKEN")
DROPBOX_APP_KEY    = os.environ.get("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET")
DROPBOX_REFRESH    = os.environ.get("DROPBOX_REFRESH_TOKEN")

DROPBOX_ROOT           = "/Applications/Joplin"
DROPBOX_RAW            = "/second_cerveau/raw"
DROPBOX_BLOCNOTES      = f"{DROPBOX_ROOT}/blocnotes.md"
DROPBOX_TRAVAIL        = f"{DROPBOX_ROOT}/travail.md"
DROPBOX_PROJET         = f"{DROPBOX_ROOT}/projet.md"
DROPBOX_SETTINGS       = "/second_cerveau/settings.json"
DROPBOX_PLANNING       = "/second_cerveau/planning.json"
DROPBOX_CAPTURES_INDEX = "/second_cerveau/captures.json"

# Limite taille fichiers entrants (Step I)
MAX_DOC_SIZE_MB  = 10
MAX_VOCAL_SECS   = 300  # 5 minutes

_METEO_DEFAULTS = {"lat": 46.29, "lon": 7.54, "ville": "Sierre, CH", "heure": 7}

_SHIFTS_FR = {
    "AM":    ("🌅", "Matin"),
    "PM":    ("🌆", "Après-midi"),
    "OV":    ("🌄", "Ouverture"),
    "FV":    ("🌇", "Fermeture"),
    "DAM":   ("🌅", "Demi-matin"),
    "SAM":   ("🌅", "Split matin"),
    "DPM":   ("🌆", "Demi après-midi"),
    "SPM":   ("🌆", "Split après-midi"),
    "OFF":   ("🎉", "Congé"),
    "EXT":   ("⭐", "Extra"),
    "HOL":   ("🏖️", "Férié"),
    "OLOG":  ("📦", "Ouv. Logistique"),
    "SOLOG": ("📦", "Split Ouv. Log."),
}

_JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

PROMPT_PLANNING = """Tu analyses un screenshot de planning Excel IKEA.

== ÉTAPE 1 : Localise la ligne de Tristan ==
Dans la colonne B (noms), cherche la cellule qui contient exactement "Tristan Cailloux".
Sa ligne dans la section "Sales" contient "Shopkeeper HFB 01/02/03" en colonne A.
Les lignes voisines sont d'autres shopkeepers (Nora Benlahmr, Tania Pereira, Ana Ferreira, Kévin Palau) — NE LIS PAS ces lignes.

== ÉTAPE 2 : Lis les en-têtes ==
- Ligne "Week number" → numéro de semaine
- Ligne "Day" → MON, TUE, WED, THU, FRI, SAT, SUN pour chaque colonne
- Ligne "Date" → numéro du jour du mois pour chaque colonne

Aujourd'hui c'est le {today}. Déduis le mois et l'année exacts à partir de là.

== ÉTAPE 3 : Extrait les shifts de LA LIGNE DE TRISTAN uniquement ==
Pour chaque colonne jour visible, lis la cellule dans la ligne de Tristan.

Normalise les codes :
O.V/OV→OV | F.V/FV→FV | D.AM/D. AM→DAM | S.AM/S. AM→SAM
D.PM/D. PM→DPM | S.PM/S. PM→SPM | O Log→OLOG | S.O Log→SOLOG
HOL, EXT, OFF, AM, PM : inchangés. Case vide → null (ne pas inclure).

== Réponse ==
Réponds UNIQUEMENT avec un JSON valide (sans bloc markdown) :
{{"week": <semaine>, "tristan_row_raw": "<ce que tu lis mot pour mot dans la ligne de Tristan>", "days": {{"YYYY-MM-DD": "CODE", ...}}}}

Si Tristan est absent : {{"error": "not_found"}}"""

TRIGGERS_TRAVAIL   = {"travail"}
TRIGGERS_BLOCNOTES = {"blocnote", "bloc-note", "blocnotes", "bloc-notes"}
TRIGGERS_PROJET    = {"projet", "projets"}

# ── Auth filter (Step A) ───────────────────────────────────────────────────────

if TELEGRAM_CHAT_ID:
    _CHAT_FILTER = filters.Chat(int(TELEGRAM_CHAT_ID))
else:
    _CHAT_FILTER = filters.ALL
    log.warning("⚠️  TELEGRAM_CHAT_ID non défini — toutes les conversations sont acceptées.")

# ── Helpers ───────────────────────────────────────────────────────────────────

def cb(prefix: str, filename: str) -> str:
    """Construit une callback_data ≤ 64 octets."""
    return f"{prefix}:{filename}"[:64]


def erreur_msg(e: Exception) -> str:
    """Message d'erreur utilisateur propre — masque les détails techniques."""
    msg = str(e)
    msg = re.sub(r'https?://\S+', '[URL]', msg)
    return f"❌ {msg[:200]}"

# ── Dropbox ───────────────────────────────────────────────────────────────────

def get_dropbox():
    import dropbox
    if DROPBOX_TOKEN:
        return dropbox.Dropbox(DROPBOX_TOKEN)
    return dropbox.Dropbox(
        oauth2_refresh_token=DROPBOX_REFRESH,
        app_key=DROPBOX_APP_KEY,
        app_secret=DROPBOX_APP_SECRET,
    )


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
    dbx           = get_dropbox()
    contenu       = telecharger_fiche(path)
    nouveau_contenu = re.sub(r"^#\s+.+", f"# {nouveau_titre}", contenu, count=1, flags=re.MULTILINE)
    ancien_nom    = path.split("/")[-1]
    tag           = ancien_nom.split("_")[0]
    mots          = [m for m in slugifier(nouveau_titre).split("_") if m and m != tag.lower()][:3]
    nouveau_nom   = f"{tag}_{'_'.join(mots) or 'note'}.md"
    nouveau_path  = f"{DROPBOX_ROOT}/{nouveau_nom}"
    dbx.files_upload(nouveau_contenu.encode("utf-8"), nouveau_path, mode=dbx_mod.files.WriteMode.overwrite)
    if nouveau_path != path:
        dbx.files_delete_v2(path)
    return nouveau_path

# ── Index de déduplication (Step F) ───────────────────────────────────────────

def charger_index_captures() -> dict:
    import dropbox as dbx_mod
    try:
        _, res = get_dropbox().files_download(DROPBOX_CAPTURES_INDEX)
        return json.loads(res.content)
    except dbx_mod.exceptions.ApiError:
        return {}


def enregistrer_capture(url: str, fiche_nom: str) -> None:
    import dropbox as dbx_mod
    index       = charger_index_captures()
    index[url]  = {"fiche": fiche_nom, "date": datetime.now().strftime("%Y-%m-%d")}
    get_dropbox().files_upload(
        json.dumps(index, ensure_ascii=False, indent=2).encode(),
        DROPBOX_CAPTURES_INDEX,
        mode=dbx_mod.files.WriteMode.overwrite,
    )

# ── Extraction multimédia ─────────────────────────────────────────────────────

def extraire_image_bytes(data: bytes, mime: str = "image/jpeg") -> str:
    import base64
    from openai import OpenAI
    b64 = base64.b64encode(data).decode()
    r   = OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Décris cette image en détail. Si elle contient du texte, retranscris-le. Si c'est un graphique, explique les données."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        max_tokens=1000,
    )
    return r.choices[0].message.content


def extraire_pdf_bytes(data: bytes) -> str:
    import fitz
    doc = fitz.open(stream=data, filetype="pdf")
    return "\n".join(p.get_text() for p in doc)[:LIMITE_EXTRACTION]


def extraire_audio_tmp(data: bytes, ext: str = ".ogg") -> str:
    from openai import OpenAI
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            t = OpenAI(api_key=OPENAI_API_KEY).audio.transcriptions.create(
                model="whisper-1", file=f, language="fr"
            )
        return t.text[:LIMITE_EXTRACTION]
    finally:
        os.unlink(tmp_path)


def extraire_planning_image(data: bytes) -> dict:
    """Essaie gpt-4o-mini d'abord, bascule sur gpt-4o si le JSON est invalide (Step G)."""
    import base64
    from openai import OpenAI
    b64    = base64.b64encode(data).decode()
    prompt = PROMPT_PLANNING.format(today=datetime.now().strftime("%d/%m/%Y"))
    client = OpenAI(api_key=OPENAI_API_KEY)
    for model in ["gpt-4.1-mini", "gpt-4.1"]:
        try:
            r    = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                ]}],
                max_tokens=1000,
            )
            text   = re.sub(r"```(?:json)?\s*", "", r.choices[0].message.content.strip()).strip("`").strip()
            result = json.loads(text)
            log.info("Planning extrait via %s", model)
            return result
        except (json.JSONDecodeError, ValueError):
            if model == "gpt-4o":
                raise
            log.info("gpt-4o-mini insuffisant pour le planning → fallback gpt-4o")
    return {"error": "extraction_failed"}

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

# ── Settings ──────────────────────────────────────────────────────────────────

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

# ── Planning ──────────────────────────────────────────────────────────────────

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

# ── Schedulers ────────────────────────────────────────────────────────────────

async def envoyer_meteo_matin(context) -> None:
    import asyncio
    if not TELEGRAM_CHAT_ID:
        return
    cfg = load_settings()
    texte = None
    for attempt in range(3):
        try:
            texte = get_meteo(cfg["lat"], cfg["lon"], cfg["ville"])
            break
        except Exception as e:
            log.warning("Erreur météo (tentative %d/3) : %s", attempt + 1, e)
            if attempt < 2:
                await asyncio.sleep(15)
    if texte is None:
        texte = "🌡️ Météo indisponible ce matin — open-meteo ne répond pas."
    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=texte, parse_mode="Markdown")


def reprogrammer_meteo(app, heure: int) -> None:
    import datetime as dt
    from zoneinfo import ZoneInfo
    for job in app.job_queue.get_jobs_by_name("meteo_matin"):
        job.schedule_removal()
    app.job_queue.run_daily(
        envoyer_meteo_matin,
        time=dt.time(heure, 0, tzinfo=ZoneInfo("Europe/Paris")),
        name="meteo_matin",
    )


async def envoyer_recap_matin(context) -> None:
    if not TELEGRAM_CHAT_ID:
        return
    parties = []
    travail   = lire_fichier_dropbox(DROPBOX_TRAVAIL).splitlines()
    blocnotes = lire_fichier_dropbox(DROPBOX_BLOCNOTES).splitlines()
    projets   = lire_fichier_dropbox(DROPBOX_PROJET).splitlines()
    if travail:
        parties.append("💼 *Travail :*\n" + "\n".join(f"  {t}" for t in travail))
    if blocnotes:
        parties.append("📝 *Bloc-notes :*\n" + "\n".join(f"  {b}" for b in blocnotes))
    if projets:
        parties.append("🚀 *Projets :*\n" + "\n".join(f"  {p}" for p in projets))
    if not parties:
        parties.append("Aucune tâche en attente. Belle journée !")
    await context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text="\n\n".join(parties),
        parse_mode="Markdown",
    )


async def envoyer_rappel_planning(context) -> None:
    if not TELEGRAM_CHAT_ID:
        return
    demain = datetime.now() + timedelta(days=1)
    key    = demain.strftime("%Y-%m-%d")
    shift  = load_planning().get(key)
    if not shift:
        return
    emoji, label = _SHIFTS_FR.get(shift, ("📅", shift))
    jour     = _JOURS_FR[demain.weekday()]
    date_fmt = demain.strftime("%d/%m")
    await context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=f"📅 *Demain {jour} {date_fmt} :*\n\n{emoji} *{shift}* — {label}",
        parse_mode="Markdown",
    )

# ── Inline keyboards ──────────────────────────────────────────────────────────

def kb_menu_principal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Dernières fiches",   callback_data="menu:dernieres")],
        [InlineKeyboardButton("✏️ Modifier une fiche",  callback_data="menu:modifier")],
        [InlineKeyboardButton("🔍 Rechercher",          callback_data="menu:chercher")],
        [
            InlineKeyboardButton("💼 Travail",    callback_data="menu:travail"),
            InlineKeyboardButton("📝 Bloc-notes", callback_data="menu:blocnotes"),
            InlineKeyboardButton("🚀 Projets",    callback_data="menu:projets"),
        ],
        [InlineKeyboardButton("📅 Mon planning",    callback_data="menu:planning")],
        [InlineKeyboardButton("🌤️ Voir la météo",  callback_data="meteo:voir")],
        [InlineKeyboardButton("⚙️ Réglages météo", callback_data="menu:meteo")],
    ])


def kb_planning_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Uploader planning",  callback_data="planning:upload")],
        [InlineKeyboardButton("📅 Voir cette semaine", callback_data="planning:voir")],
        [InlineKeyboardButton("↩️ Retour",             callback_data="menu:accueil")],
    ])


def kb_planning_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmer et enregistrer", callback_data="planning:confirm")],
        [InlineKeyboardButton("🔄 Relancer l'extraction",   callback_data="planning:retry")],
        [InlineKeyboardButton("❌ Annuler",                  callback_data="planning:cancel")],
    ])


def kb_meteo_settings() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 Changer la ville",  callback_data="ms:ville")],
        [InlineKeyboardButton("⏰ Changer l'heure",   callback_data="ms:heure")],
        [InlineKeyboardButton("↩️ Retour",            callback_data="menu:accueil")],
    ])


def kb_meteo_heures(heure_actuelle: int) -> InlineKeyboardMarkup:
    heures = [5, 6, 7, 8, 9, 10]
    rangees = []
    for i in range(0, len(heures), 3):
        rangee = []
        for h in heures[i:i+3]:
            label = f"{'✅' if h == heure_actuelle else ''}{h}h".strip()
            rangee.append(InlineKeyboardButton(label, callback_data=f"ms:h:{h}"))
        rangees.append(rangee)
    rangees.append([InlineKeyboardButton("↩️ Retour", callback_data="menu:meteo")])
    return InlineKeyboardMarkup(rangees)


def kb_apres_capture(filename: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏷️ Tags",  callback_data=cb("edit_tags",  filename)),
        InlineKeyboardButton("✏️ Titre", callback_data=cb("edit_title", filename)),
        InlineKeyboardButton("❌ OK",    callback_data="ignore"),
    ]])


def kb_modifier_fiche(filename: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏷️ Modifier tags",  callback_data=cb("edit_tags",  filename)),
        InlineKeyboardButton("✏️ Modifier titre", callback_data=cb("edit_title", filename)),
        InlineKeyboardButton("↩️ Annuler",        callback_data="ignore"),
    ]])


def kb_tags_menu(filename: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Ajouter un tag",         callback_data=cb("ta", filename))],
        [InlineKeyboardButton("➖ Enlever un tag",         callback_data=cb("tr", filename))],
        [InlineKeyboardButton("🔄 Réécrire tous les tags", callback_data=cb("tw", filename))],
        [InlineKeyboardButton("↩️ Annuler",                callback_data="ignore")],
    ])


def kb_tags_liste(filename: str, tags: list[str]) -> InlineKeyboardMarkup:
    boutons = [
        [InlineKeyboardButton(f"❌ {tag}", callback_data=f"td:{filename}:{tag.lstrip('#')}"[:64])]
        for tag in tags
    ]
    boutons.append([InlineKeyboardButton("↩️ Annuler", callback_data="ignore")])
    return InlineKeyboardMarkup(boutons)


def kb_liste_fiches(fiches: list, prefix: str = "view") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📄 {f.name[:40]}", callback_data=cb(prefix, f.name))]
        for f in fiches
    ])


def kb_confirmer_capture() -> InlineKeyboardMarkup:
    """Keyboard affiché quand la qualité d'extraction est douteuse (Step E)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Analyser quand même", callback_data="capture:ok")],
        [InlineKeyboardButton("❌ Annuler",              callback_data="capture:cancel")],
    ])


def kb_dedup_capture() -> InlineKeyboardMarkup:
    """Keyboard affiché quand l'URL a déjà été capturée (Step F)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Recapturer quand même", callback_data="capture:url:recapture")],
        [InlineKeyboardButton("❌ Annuler",                callback_data="capture:cancel")],
    ])

# ── Capture flow helpers ───────────────────────────────────────────────────────

async def _confirmer_capture(msg, path: str) -> None:
    nom = path.split("/")[-1]
    await msg.edit_text(
        f"✅ *Capturé !*\n\n`{nom}`\n\n_Veux-tu modifier quelque chose ?_",
        parse_mode="Markdown",
        reply_markup=kb_apres_capture(nom),
    )


async def _analyser_et_uploader(msg, contenu: str, source: str, contenu_brut: str | None = None) -> None:
    """Appelle GPT, upload vers Dropbox et confirme. Enregistre dans l'index si URL."""
    fiche_md = analyser_contenu(contenu, source)
    path     = uploader_fiche(fiche_md, contenu_brut)
    nom      = path.split("/")[-1]
    if source.startswith("http://") or source.startswith("https://"):
        try:
            enregistrer_capture(source, nom)
        except Exception as e:
            log.warning("Impossible d'enregistrer dans l'index : %s", e)
    await _confirmer_capture(msg, path)


async def _capturer_url(msg, url: str, context) -> None:
    """Capture complète d'une URL : dédup → extract → qualité → analyse."""
    # Step F : dédup
    try:
        index = charger_index_captures()
        if url in index:
            info = index[url]
            context.user_data["pending_url"] = url
            await msg.edit_text(
                f"⚠️ *Déjà capturé* le {info.get('date', '?')} :\n`{info.get('fiche', '?')}`\n\n"
                "Veux-tu le recapturer quand même ?",
                parse_mode="Markdown",
                reply_markup=kb_dedup_capture(),
            )
            return
    except Exception:
        pass  # index inaccessible → on continue

    contenu_raw, msg = await _extraire_url_avec_msg(msg, url)
    if contenu_raw is None:
        return

    contenu_propre, injections = nettoyer_contenu(contenu_raw)
    ok, raison = evaluer_qualite(contenu_propre, injections)

    if not ok:
        # Step E : demande confirmation
        apercu = contenu_propre[:300].replace("*", "").replace("_", "").replace("`", "")
        context.user_data["pending_capture"] = {
            "contenu": contenu_propre,
            "source": url,
            "contenu_brut": contenu_propre,
        }
        await msg.edit_text(
            f"{raison}\n\n*Aperçu :*\n```\n{apercu}…\n```",
            parse_mode="Markdown",
            reply_markup=kb_confirmer_capture(),
        )
        return

    await _analyser_et_uploader(msg, contenu_propre, url, contenu_brut=contenu_propre)


async def _extraire_url_avec_msg(msg, url: str):
    """Extrait une URL et gère l'erreur. Retourne (contenu, msg) ou (None, msg)."""
    try:
        contenu = extraire_url(url)
        return contenu, msg
    except Exception as e:
        await msg.edit_text(erreur_msg(e))
        return None, msg

# ── Handlers commandes ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🧠 *Second Cerveau* — je capture et organise tes connaissances.\n\n"
        "Envoie-moi une URL, un texte, une photo, un PDF ou un vocal.\n"
        "Préfixe par *travail*, *blocnote* ou *projet* pour ajouter directement.\n\n"
        "Que veux-tu faire ?",
        parse_mode="Markdown",
        reply_markup=kb_menu_principal(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Step J — aide complète et découvrabilité."""
    texte = (
        "🧠 *Second Cerveau — Guide rapide*\n\n"
        "*Capturer du contenu :*\n"
        "• Envoie un lien → fiche web\n"
        "• Envoie un texte → fiche note\n"
        "• Envoie une photo → fiche image\n"
        "• Envoie un PDF → fiche document\n"
        "• Envoie un vocal → transcription + fiche\n\n"
        "*Ajouts rapides (texte ou vocal) :*\n"
        "• `travail <texte>` → ajoute une tâche\n"
        "• `blocnote <texte>` → ajoute une note\n"
        "• `projet <texte>` → ajoute un projet\n\n"
        "*Commandes :*\n"
        "• /start — Menu principal\n"
        "• /dernieres — 5 dernières fiches\n"
        "• /chercher mots — Rechercher dans les fiches\n"
        "• /travail — Voir les tâches\n"
        "• /blocnotes — Voir les notes\n"
        "• /done T1 B2 — Cocher des tâches\n"
        "• /monid — Voir ton Chat ID\n"
        "• /help — Ce message"
    )
    await update.message.reply_text(texte, parse_mode="Markdown")


async def cmd_dernieres(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg    = update.message or update.callback_query.message
    fiches = lister_fiches(5)
    if not fiches:
        await msg.reply_text("Aucune fiche dans Dropbox pour l'instant.")
        return
    lignes = ["📚 *5 dernières fiches :*\n"]
    for f in fiches:
        lignes.append(f"• `{f.name}` _{f.server_modified.strftime('%d/%m %H:%M')}_")
    await msg.reply_text(
        "\n".join(lignes),
        parse_mode="Markdown",
        reply_markup=kb_liste_fiches(fiches, prefix="edit_fiche"),
    )


async def cmd_travail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    taches = lire_fichier_dropbox(DROPBOX_TRAVAIL).splitlines()
    if not taches:
        await update.message.reply_text("💼 Aucune tâche travail en cours !")
        return
    lignes = ["💼 *Tâches travail :*\n"] + [f"  T{i+1} {t}" for i, t in enumerate(taches)]
    lignes.append("\n_Tape_ `/done T1 T3` _pour cocher des tâches_")
    await update.message.reply_text("\n".join(lignes), parse_mode="Markdown")


async def cmd_blocnotes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    notes = lire_fichier_dropbox(DROPBOX_BLOCNOTES).splitlines()
    if not notes:
        await update.message.reply_text("📝 Bloc-notes vide !")
        return
    lignes = ["📝 *Bloc-notes :*\n"] + [f"  B{i+1} {n}" for i, n in enumerate(notes)]
    lignes.append("\n_Tape_ `/done B1 B3` _pour cocher_")
    await update.message.reply_text("\n".join(lignes), parse_mode="Markdown")


async def cmd_projet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    notes = lire_fichier_dropbox(DROPBOX_PROJET).splitlines()
    if not notes:
        await update.message.reply_text("🚀 Aucun projet en cours !")
        return
    lignes = ["🚀 *Projets en cours :*\n"] + [f"  P{i+1} {n}" for i, n in enumerate(notes)]
    lignes.append("\n_Tape_ `/done P1 P3` _pour cocher_")
    await update.message.reply_text("\n".join(lignes), parse_mode="Markdown")


async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        travail   = lire_fichier_dropbox(DROPBOX_TRAVAIL).splitlines()
        blocnotes = lire_fichier_dropbox(DROPBOX_BLOCNOTES).splitlines()
        projets   = lire_fichier_dropbox(DROPBOX_PROJET).splitlines()
        lignes    = []
        if travail:
            lignes.append("💼 *Travail :*")
            lignes += [f"  T{i+1} {t}" for i, t in enumerate(travail)]
        if blocnotes:
            lignes.append("\n📝 *Bloc-notes :*")
            lignes += [f"  B{i+1} {b}" for i, b in enumerate(blocnotes)]
        if projets:
            lignes.append("\n🚀 *Projets :*")
            lignes += [f"  P{i+1} {p}" for i, p in enumerate(projets)]
        if not lignes:
            await update.message.reply_text("✅ Aucune tâche en attente !")
            return
        lignes.append("\n_Réponds_ `/done T1 B2 P3` _pour cocher_")
        await update.message.reply_text("\n".join(lignes), parse_mode="Markdown")
        return
    t_idx, b_idx, p_idx = set(), set(), set()
    for a in args:
        a = a.upper()
        try:
            if a.startswith("T"):   t_idx.add(int(a[1:]))
            elif a.startswith("B"): b_idx.add(int(a[1:]))
            elif a.startswith("P"): p_idx.add(int(a[1:]))
        except ValueError:
            pass
    if not t_idx and not b_idx and not p_idx:
        await update.message.reply_text("❓ Format : `/done T1 T3 B2 P1`", parse_mode="Markdown")
        return
    msg   = await update.message.reply_text("⏳ Mise à jour…")
    total = 0
    if t_idx: total += supprimer_taches(DROPBOX_TRAVAIL,   t_idx)
    if b_idx: total += supprimer_taches(DROPBOX_BLOCNOTES, b_idx)
    if p_idx: total += supprimer_taches(DROPBOX_PROJET,    p_idx)
    await msg.edit_text(f"✅ {total} tâche(s) cochée(s) !")


async def cmd_chercher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Step H — recherche plein texte depuis Telegram."""
    question = " ".join(context.args) if context.args else ""
    if not question:
        await update.message.reply_text(
            "🔍 *Rechercher dans tes fiches*\n\n"
            "Usage : `/chercher mots-clés`\n"
            "Exemple : `/chercher react native state`",
            parse_mode="Markdown",
        )
        return
    await _executer_recherche(update.message, question)


async def _executer_recherche(msg, question: str) -> None:
    """Télécharge toutes les fiches Dropbox et lance la recherche."""
    status = await msg.reply_text("🔍 Recherche en cours…")
    try:
        fiches = lister_toutes_fiches()
        fiches_textes = []
        for f in fiches:
            try:
                contenu = telecharger_fiche(f"{DROPBOX_ROOT}/{f.name}")
                fiches_textes.append((f.name, contenu))
            except Exception:
                pass

        resultats = chercher_fiches(question, fiches_textes, top_n=5)
        if not resultats:
            await status.edit_text(f"🔍 Aucune fiche trouvée pour « {question} ».")
            return

        lignes = [f"🔍 *Résultats pour « {question} » :*\n"]
        for i, r in enumerate(resultats, 1):
            lignes.append(f"*{i}.* `{r['fichier']}` — {r['pertinence']}%")
            if r["tags"]:
                lignes.append(f"   {r['tags']}")
            if r["idee"]:
                lignes.append(f"   _{r['idee'][:120].replace(chr(10), ' ')}_")
            lignes.append("")

        boutons = [
            [InlineKeyboardButton(f"✏️ {r['fichier'][:35]}", callback_data=cb("edit_fiche", r["fichier"]))]
            for r in resultats[:3]
        ]
        boutons.append([InlineKeyboardButton("↩️ Retour", callback_data="menu:accueil")])

        await status.edit_text(
            "\n".join(lignes),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(boutons),
        )
    except Exception as e:
        log.exception("Erreur recherche")
        await status.edit_text(erreur_msg(e))


async def cmd_monid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"🪪 Ton Chat ID : `{update.effective_chat.id}`",
        parse_mode="Markdown",
    )

# ── Handlers messages ─────────────────────────────────────────────────────────

async def traiter_texte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texte       = (update.message.text or "").strip()
    premier_mot = texte.split()[0].lower() if texte else ""

    # Mode édition en attente
    edit = context.user_data.get("pending_edit")
    if edit:
        del context.user_data["pending_edit"]
        if edit["type"] == "meteo_ville":
            msg = await update.message.reply_text("⏳ Recherche de la ville…")
            try:
                lat, lon, label = geocoder_ville(texte.strip())
                cfg = load_settings()
                cfg.update({"lat": lat, "lon": lon, "ville": label})
                save_settings(cfg)
                await msg.edit_text(
                    f"✅ Ville mise à jour : *{label}*\n📍 Coordonnées : {lat:.4f}, {lon:.4f}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                await msg.edit_text(erreur_msg(e))
            return
        if edit["type"] == "chercher_query":
            await _executer_recherche(update.message, texte.strip())
            return
        await _appliquer_edit(update, context, edit, texte)
        return

    # Routage travail / blocnote / projet
    if premier_mot in TRIGGERS_TRAVAIL:
        contenu = texte[len(premier_mot):].strip()
        if not contenu:
            await update.message.reply_text("💼 Écris quelque chose après `travail` !")
            return
        ajouter_travail(contenu)
        await update.message.reply_text(f"✅ *Tâche ajoutée :*\n`- {contenu}`", parse_mode="Markdown")
        return

    if premier_mot in TRIGGERS_BLOCNOTES:
        contenu = texte[len(premier_mot):].strip()
        if not contenu:
            await update.message.reply_text("📝 Écris quelque chose après `blocnote` !")
            return
        ajouter_blocnote(contenu)
        await update.message.reply_text(f"✅ *Bloc-notes ajouté :*\n`- {contenu}`", parse_mode="Markdown")
        return

    if premier_mot in TRIGGERS_PROJET:
        contenu = texte[len(premier_mot):].strip()
        if not contenu:
            await update.message.reply_text("🚀 Écris quelque chose après `projet` !")
            return
        ajouter_projet(contenu)
        await update.message.reply_text(f"✅ *Projet ajouté :*\n`- {contenu}`", parse_mode="Markdown")
        return

    # Capture normale
    msg = await update.message.reply_text("⏳ Traitement en cours…")
    try:
        if texte.startswith("http://") or texte.startswith("https://"):
            await _capturer_url(msg, texte, context)
        else:
            contenu_propre, _ = nettoyer_contenu(texte[:LIMITE_EXTRACTION])
            await _analyser_et_uploader(msg, contenu_propre, "telegram-note")
    except Exception as e:
        log.exception("Erreur texte")
        await msg.edit_text(erreur_msg(e))


async def _traiter_planning_bytes(update: Update, context: ContextTypes.DEFAULT_TYPE, data: bytes) -> None:
    msg = await update.message.reply_text("⏳ Extraction du planning via GPT…")
    try:
        result  = extraire_planning_image(data)
        if "error" in result:
            await msg.edit_text(
                "❌ Tristan introuvable dans ce screenshot.\n"
                "Vérifie que ta ligne *Tristan Cailloux* est bien visible, puis renvoie.",
                parse_mode="Markdown",
            )
            return
        days    = {k: v for k, v in result.get("days", {}).items() if v}
        semaine = result.get("week", "?")
        raw     = result.get("tristan_row_raw", "")
        context.user_data["pending_planning_data"] = {"week": semaine, "days": days}
        lignes  = [f"📋 *Vérifie le planning semaine {semaine} :*\n"]
        for d, c in sorted(days.items()):
            emoji, label = _SHIFTS_FR.get(c, ("📅", c))
            dt = datetime.strptime(d, "%Y-%m-%d")
            lignes.append(f"• {_JOURS_FR[dt.weekday()]} {dt.strftime('%d/%m')} : {emoji} *{c}* — {label}")
        if raw:
            lignes.append(f"\n_Ligne lue :_ `{raw[:120]}`")
        lignes.append("\n_Est-ce correct ?_")
        await msg.edit_text("\n".join(lignes), parse_mode="Markdown", reply_markup=kb_planning_confirm())
    except Exception as e:
        log.exception("Erreur planning")
        await msg.edit_text(erreur_msg(e))


async def _traiter_planning_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buf = io.BytesIO()
    await (await update.message.photo[-1].get_file()).download_to_memory(buf)
    await _traiter_planning_bytes(update, context, buf.getvalue())


async def traiter_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.pop("pending_planning_upload", False):
        await _traiter_planning_photo(update, context)
        return
    caption = (update.message.caption or "").strip().lower()
    if caption.startswith("planning"):
        await _traiter_planning_photo(update, context)
        return
    msg = await update.message.reply_text("⏳ Analyse de la photo…")
    try:
        buf  = io.BytesIO()
        await (await update.message.photo[-1].get_file()).download_to_memory(buf)
        data = buf.getvalue()
        nom  = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        contenu = extraire_image_bytes(data)
        await _analyser_et_uploader(msg, contenu, f"telegram-photo:{nom}")
        uploader_raw(data, nom)
    except Exception as e:
        log.exception("Erreur photo")
        await msg.edit_text(erreur_msg(e))


async def traiter_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    ext = os.path.splitext(doc.file_name)[1].lower()
    caption = (update.message.caption or "").strip().lower()

    # Planning via document image
    if ext in {".jpg", ".jpeg", ".png"} and (
        context.user_data.pop("pending_planning_upload", False) or caption.startswith("planning")
    ):
        buf = io.BytesIO()
        await (await doc.get_file()).download_to_memory(buf)
        await _traiter_planning_bytes(update, context, buf.getvalue())
        return

    # Step I — garde-fou taille
    if doc.file_size and doc.file_size > MAX_DOC_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(
            f"❌ Fichier trop volumineux (max {MAX_DOC_SIZE_MB} Mo). Compresse le PDF avant d'envoyer."
        )
        return

    if ext not in {".pdf", ".txt", ".md"}:
        await update.message.reply_text("❌ Format non supporté. Envoie un PDF, un fichier texte, ou une image planning.")
        return

    msg = await update.message.reply_text("⏳ Extraction du document…")
    try:
        buf  = io.BytesIO()
        await (await doc.get_file()).download_to_memory(buf)
        data = buf.getvalue()
        if ext == ".pdf":
            contenu_raw = extraire_pdf_bytes(data)
        else:
            contenu_raw = data.decode("utf-8", errors="ignore")[:LIMITE_EXTRACTION]
        contenu_propre, injections = nettoyer_contenu(contenu_raw)
        ok, raison = evaluer_qualite(contenu_propre, injections)
        if not ok:
            context.user_data["pending_capture"] = {
                "contenu": contenu_propre,
                "source": f"telegram-doc:{doc.file_name}",
                "contenu_brut": contenu_propre,
            }
            await msg.edit_text(
                f"{raison}\n\n_Veux-tu analyser quand même ?_",
                parse_mode="Markdown",
                reply_markup=kb_confirmer_capture(),
            )
            return
        await _analyser_et_uploader(msg, contenu_propre, f"telegram-doc:{doc.file_name}", contenu_brut=contenu_propre)
        if ext == ".pdf":
            uploader_raw(data, doc.file_name)
    except Exception as e:
        log.exception("Erreur document")
        await msg.edit_text(erreur_msg(e))


async def traiter_vocal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Step I — garde-fou durée
    if update.message.voice.duration > MAX_VOCAL_SECS:
        await update.message.reply_text(
            f"❌ Message vocal trop long (max {MAX_VOCAL_SECS // 60} min). Découpe-le en plusieurs parties."
        )
        return

    msg = await update.message.reply_text("⏳ Transcription audio…")
    try:
        buf          = io.BytesIO()
        await (await update.message.voice.get_file()).download_to_memory(buf)
        transcription = extraire_audio_tmp(buf.getvalue(), ".ogg").strip()
        premier_mot   = transcription.split()[0].lower() if transcription else ""

        if premier_mot in TRIGGERS_TRAVAIL:
            contenu = transcription[len(premier_mot):].strip()
            ajouter_travail(contenu)
            await msg.edit_text(f"✅ *Tâche travail :*\n`- {contenu}`", parse_mode="Markdown")
        elif premier_mot in TRIGGERS_BLOCNOTES:
            contenu = transcription[len(premier_mot):].strip()
            ajouter_blocnote(contenu)
            await msg.edit_text(f"✅ *Bloc-notes :*\n`- {contenu}`", parse_mode="Markdown")
        elif premier_mot in TRIGGERS_PROJET:
            contenu = transcription[len(premier_mot):].strip()
            ajouter_projet(contenu)
            await msg.edit_text(f"✅ *Projet ajouté :*\n`- {contenu}`", parse_mode="Markdown")
        else:
            await _analyser_et_uploader(msg, transcription, "telegram-vocal")
    except Exception as e:
        log.exception("Erreur vocal")
        await msg.edit_text(erreur_msg(e))

# ── Callbacks ─────────────────────────────────────────────────────────────────

async def _appliquer_edit(update: Update, context, edit: dict, valeur: str) -> None:
    path = f"{DROPBOX_ROOT}/{edit['filename']}"
    try:
        t = edit["type"]
        if t == "tags_add":
            nouveaux = ajouter_tag_dropbox(path, valeur.strip())
            await update.message.reply_text(f"✅ Tag ajouté. Tags actuels : `{nouveaux}`", parse_mode="Markdown")
        elif t == "tags_rewrite":
            tags = valeur.strip()
            if not tags.startswith("#"):
                tags = " ".join(f"#{w.lstrip('#')}" for w in tags.split())
            modifier_tags_dropbox(path, tags)
            await update.message.reply_text(f"✅ Tags réécrits : `{tags}`", parse_mode="Markdown")
        else:
            nouveau_path = modifier_titre_dropbox(path, valeur.strip())
            await update.message.reply_text(f"✅ Fiche renommée :\n`{nouveau_path.split('/')[-1]}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(erreur_msg(e))


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Step A — auth guard sur les callbacks
    if TELEGRAM_CHAT_ID and update.effective_chat.id != int(TELEGRAM_CHAT_ID):
        return

    query = update.callback_query
    await query.answer()
    data  = query.data

    if data == "ignore":
        await query.edit_message_reply_markup(reply_markup=None)
        return

    # ── Captures (Steps E & F) ──
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
        return

    # ── Menu principal ──
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

    # ── Édition de fiches ──
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

    # ── Planning ──
    if data == "menu:planning":
        await query.edit_message_text(
            "📅 *Mon planning*\n\nUploade ton screenshot chaque semaine pour recevoir un rappel à 22h la veille de chaque shift.",
            parse_mode="Markdown", reply_markup=kb_planning_menu(),
        )
        return

    if data == "planning:upload":
        context.user_data["pending_planning_upload"] = True
        await query.edit_message_text(
            "📤 Envoie le screenshot de ton planning.\n\n"
            "_💡 Pour une meilleure qualité, envoie-le comme_ *Fichier* _(pas comme photo)._\n"
            "_Tu peux aussi envoyer une photo avec la légende_ `planning` _n'importe quand._",
            parse_mode="Markdown",
        )
        return

    if data == "planning:confirm":
        pending = context.user_data.pop("pending_planning_data", None)
        if not pending:
            await query.edit_message_text("❌ Session expirée. Renvoie le screenshot.")
            return
        save_planning(pending["days"])
        await query.edit_message_text(
            f"✅ *Planning semaine {pending['week']} enregistré !*\n_{len(pending['days'])} jours sauvegardés._",
            parse_mode="Markdown", reply_markup=kb_planning_menu(),
        )
        return

    if data == "planning:cancel":
        context.user_data.pop("pending_planning_data", None)
        await query.edit_message_text("❌ Extraction annulée.", reply_markup=kb_planning_menu())
        return

    if data == "planning:retry":
        context.user_data.pop("pending_planning_data", None)
        context.user_data["pending_planning_upload"] = True
        await query.edit_message_text(
            "🔄 Renvoie le screenshot. *Essaie en l'envoyant comme Fichier* pour une meilleure qualité.",
            parse_mode="Markdown",
        )
        return

    if data == "planning:voir":
        planning = load_planning()
        debut    = datetime.now() - timedelta(days=datetime.now().weekday())
        lignes   = ["📅 *Semaine en cours :*\n"]
        trouvé   = False
        for i in range(7):
            d = (debut + timedelta(days=i)).strftime("%Y-%m-%d")
            if d in planning:
                trouvé = True
                c      = planning[d]
                emoji, label = _SHIFTS_FR.get(c, ("📅", c))
                dt = datetime.strptime(d, "%Y-%m-%d")
                lignes.append(f"• {_JOURS_FR[dt.weekday()]} {dt.strftime('%d/%m')} : {emoji} *{c}* — {label}")
        if not trouvé:
            lignes.append("_Aucune donnée pour cette semaine._\nUploade ton planning !")
        await query.edit_message_text(
            "\n".join(lignes), parse_mode="Markdown", reply_markup=kb_planning_menu(),
        )
        return

    # ── Météo ──
    if data == "menu:meteo":
        cfg = load_settings()
        await query.edit_message_text(
            f"⚙️ *Réglages météo*\n\n📍 Ville : *{cfg['ville']}*\n⏰ Heure : *{cfg['heure']}h00*",
            parse_mode="Markdown", reply_markup=kb_meteo_settings(),
        )
        return

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

# ── post_init — enregistrement des commandes Telegram (Step J) ────────────────

async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        ("start",     "Menu principal"),
        ("dernieres", "5 dernières fiches"),
        ("chercher",  "Rechercher dans les fiches"),
        ("travail",   "Voir les tâches"),
        ("blocnotes", "Voir le bloc-notes"),
        ("done",      "Cocher des tâches — ex: T1 B2"),
        ("help",      "Aide et commandes"),
        ("monid",     "Voir ton Chat ID"),
    ])
    log.info("✅ Commandes Telegram enregistrées")

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TELEGRAM_TOKEN:
        sys.exit("TELEGRAM_BOT_TOKEN manquant.")
    if not (DROPBOX_TOKEN or (DROPBOX_APP_KEY and DROPBOX_APP_SECRET and DROPBOX_REFRESH)):
        sys.exit("Token Dropbox manquant.")

    log.info("🤖 Bot démarré — Dropbox : %s", DROPBOX_ROOT)

    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    # Schedulers
    if TELEGRAM_CHAT_ID and app.job_queue:
        import datetime as dt
        from zoneinfo import ZoneInfo
        paris = ZoneInfo("Europe/Paris")
        cfg   = load_settings()
        app.job_queue.run_daily(
            envoyer_meteo_matin,
            time=dt.time(cfg["heure"], 0, tzinfo=paris),
            name="meteo_matin",
        )
        for h in [8, 12, 18, 22]:
            app.job_queue.run_daily(envoyer_recap_matin, time=dt.time(h, 0, tzinfo=paris))
        app.job_queue.run_daily(envoyer_rappel_planning, time=dt.time(22, 0, tzinfo=paris))
        log.info("⏰ Météo à %dh, récaps à 8h 12h 18h 22h, rappel planning à 22h (Paris)", cfg["heure"])

    # Handlers — Step A : _CHAT_FILTER sur tout sauf /monid
    app.add_handler(CommandHandler("start",     cmd_start,     filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("help",      cmd_help,      filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("dernieres", cmd_dernieres, filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("travail",   cmd_travail,   filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("blocnotes", cmd_blocnotes, filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("projet",    cmd_projet,    filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("projets",   cmd_projet,    filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("done",      cmd_done,      filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("chercher",  cmd_chercher,  filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("monid",     cmd_monid))  # pas de filtre : utile pour setup
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(_CHAT_FILTER & filters.TEXT & ~filters.COMMAND, traiter_texte))
    app.add_handler(MessageHandler(_CHAT_FILTER & filters.PHOTO,        traiter_photo))
    app.add_handler(MessageHandler(_CHAT_FILTER & filters.Document.ALL, traiter_document))
    app.add_handler(MessageHandler(_CHAT_FILTER & filters.VOICE,        traiter_vocal))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
