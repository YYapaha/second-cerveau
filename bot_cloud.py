"""
bot_cloud.py — Second Cerveau Bot Telegram (Railway)
Capture → OpenAI → Dropbox | Menus inline | Modification de fiches
"""
import io, os, re, sys, logging, tempfile, unicodedata
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY     = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
DROPBOX_TOKEN      = os.environ.get("DROPBOX_ACCESS_TOKEN")
DROPBOX_APP_KEY    = os.environ.get("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET")
DROPBOX_REFRESH    = os.environ.get("DROPBOX_REFRESH_TOKEN")

DROPBOX_ROOT      = "/Applications/Joplin"
DROPBOX_RAW       = "/second_cerveau/raw"
DROPBOX_BLOCNOTES = f"{DROPBOX_ROOT}/blocnotes.md"
DROPBOX_TRAVAIL   = f"{DROPBOX_ROOT}/travail.md"
DROPBOX_PROJET    = f"{DROPBOX_ROOT}/projet.md"
DROPBOX_SETTINGS  = "/second_cerveau/settings.json"
DROPBOX_PLANNING  = "/second_cerveau/planning.json"

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

Trouve la ligne de "Tristan Cailloux" (ou juste "Tristan").
Extrait le planning pour chaque colonne de jour visible.

La ligne "Date" indique le numéro du jour du mois.
La ligne "Day" indique MON, TUE, WED, THU, FRI, SAT ou SUN.
La ligne "Week number" indique le numéro de semaine.

Aujourd'hui c'est le {today}. Utilise ça pour déduire le mois et l'année exacts.

Normalise les codes de shift :
- O.V / OV → OV
- F.V / FV → FV
- D. AM / D.AM → DAM
- S. AM / S.AM → SAM
- D. PM / D.PM → DPM
- S. PM / S.PM → SPM
- O Log → OLOG
- S. O Log / S.O Log → SOLOG
- HOL, EXT, OFF, AM, PM : inchangés

Réponds UNIQUEMENT avec un JSON valide (sans bloc markdown) :
{{"week": <numéro_semaine>, "days": {{"YYYY-MM-DD": "CODE", ...}}}}

Si Tristan est absent du screenshot : {{"error": "not_found"}}"""

TRIGGERS_TRAVAIL   = {"travail"}
TRIGGERS_BLOCNOTES = {"blocnote", "bloc-note", "blocnotes", "bloc-notes"}
TRIGGERS_PROJET    = {"projet", "projets"}

PROMPT_ANALYSE = """Analyse ce contenu et crée une fiche markdown avec EXACTEMENT ce format :

# [Titre en 2 à 3 mots, trés descriptif et complet]

{source_md}

## Résumé rapide
[Résumé lisible en 30 secondes maximum]

## Analyse complète
[Analyse détaillée du contenu]

---
**POURQUOI_GARDER** : [1 phrase]
**IDEE_PRINCIPALE** : [7-8 phrases]
**POINTS_CLES** :
- Point concret 1
- Point concret 2
- Point concret 3
- Point concret 4
- Point concret 5

**QUAND_RESSORTIR** : "Quand je ferai [tâche], je devrais penser à [ceci]"
**TYPE** : [Note|Tutoriel|Outil|Réflexion]

**TAGS** : #tag1 #tag2 #tag3
**DATE** : {date_heure}

Règles : Titre 2-3 mots, TYPE parmi Note/Tutoriel/Outil/Réflexion, max 3 tags.

Contenu à analyser :
{contenu}"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def extraire_champ(fiche_md: str, champ: str) -> str:
    match = re.search(rf"\*\*{champ}\*\*\s*:\s*(.+?)(?=\n\*\*|\n##|\Z)", fiche_md, re.DOTALL)
    if match:
        return match.group(1).strip()
    if champ == "TITRE":
        match = re.search(r"^#\s+(.+)", fiche_md, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""

def slugifier(texte: str, max_len: int = 50) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = texte.lower()
    texte = re.sub(r"[^\w\s-]", "", texte)
    texte = re.sub(r"[\s\-]+", "_", texte)
    texte = texte.strip("_")
    return texte[:max_len].rstrip("_") or "note"

def formater_source(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        return f"[{source}]({source})"
    if source not in ("texte-brut", "presse-papier", "telegram-note", "telegram-vocal"):
        return f"*Source : {source}*"
    return ""

def generer_nom_fichier(fiche_md: str) -> str:
    tags_brut = extraire_champ(fiche_md, "TAGS")
    match_tag = re.search(r"#([\w\-]+)", tags_brut) if tags_brut else None
    tag = slugifier(match_tag.group(1)).upper() if match_tag else "DIVERS"
    titre = extraire_champ(fiche_md, "TITRE") or extraire_champ(fiche_md, "IDEE_PRINCIPALE").split(".")[0]
    mots = [m for m in slugifier(titre).split("_") if m and m != tag.lower()][:3]
    return f"{tag}_{'_'.join(mots) or 'note'}.md"

def cb(prefix: str, filename: str) -> str:
    """Construit une callback_data ≤ 64 octets."""
    return f"{prefix}:{filename}"[:64]

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

def uploader_fiche(fiche_md: str) -> str:
    import dropbox as dbx_mod
    dbx = get_dropbox()
    nom = generer_nom_fichier(fiche_md)
    path = f"{DROPBOX_ROOT}/{nom}"
    dbx.files_upload(fiche_md.encode("utf-8"), path, mode=dbx_mod.files.WriteMode.overwrite)
    return path

def uploader_raw(data: bytes, nom: str) -> None:
    import dropbox as dbx_mod
    dbx = get_dropbox()
    dbx.files_upload(data, f"{DROPBOX_RAW}/{nom}", mode=dbx_mod.files.WriteMode.overwrite)

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

def telecharger_fiche(path: str) -> str:
    _, res = get_dropbox().files_download(path)
    return res.content.decode("utf-8")

def modifier_tags_dropbox(path: str, nouveaux_tags: str) -> None:
    import dropbox as dbx_mod
    dbx = get_dropbox()
    contenu = telecharger_fiche(path)
    nouveau = re.sub(r"\*\*TAGS\*\*\s*:.*", f"**TAGS** : {nouveaux_tags}", contenu)
    dbx.files_upload(nouveau.encode("utf-8"), path, mode=dbx_mod.files.WriteMode.overwrite)

def ajouter_tag_dropbox(path: str, nouveau_tag: str) -> str:
    if not nouveau_tag.startswith("#"):
        nouveau_tag = f"#{nouveau_tag.lstrip('#')}"
    contenu = telecharger_fiche(path)
    tags_actuels = extraire_champ(contenu, "TAGS")
    nouveaux = f"{tags_actuels} {nouveau_tag}".strip()
    modifier_tags_dropbox(path, nouveaux)
    return nouveaux

def supprimer_tag_dropbox(path: str, tag: str) -> str:
    tag_clean = tag.lstrip("#").lower()
    contenu = telecharger_fiche(path)
    tags_actuels = extraire_champ(contenu, "TAGS")
    tags_liste = [t for t in tags_actuels.split() if t.lstrip("#").lower() != tag_clean]
    nouveaux = " ".join(tags_liste)
    modifier_tags_dropbox(path, nouveaux)
    return nouveaux

def modifier_titre_dropbox(path: str, nouveau_titre: str) -> str:
    import dropbox as dbx_mod
    dbx = get_dropbox()
    contenu = telecharger_fiche(path)
    # Mettre à jour le heading dans le contenu
    nouveau_contenu = re.sub(r"^#\s+.+", f"# {nouveau_titre}", contenu, count=1, flags=re.MULTILINE)
    # Garder le TAG du nom de fichier, changer seulement le titre
    ancien_nom = path.split("/")[-1]
    tag = ancien_nom.split("_")[0]
    mots = [m for m in slugifier(nouveau_titre).split("_") if m and m != tag.lower()][:3]
    nouveau_nom = f"{tag}_{'_'.join(mots) or 'note'}.md"
    nouveau_path = f"{DROPBOX_ROOT}/{nouveau_nom}"
    dbx.files_upload(nouveau_contenu.encode("utf-8"), nouveau_path, mode=dbx_mod.files.WriteMode.overwrite)
    if nouveau_path != path:
        dbx.files_delete_v2(path)
    return nouveau_path

# ── Extraction ────────────────────────────────────────────────────────────────

def extraire_url(url: str) -> str:
    import requests
    try:
        r = requests.get(f"https://r.jina.ai/{url}", headers={"Accept": "text/markdown"}, timeout=15)
        if r.status_code == 200 and r.text.strip():
            return r.text[:20000]
    except Exception:
        pass
    try:
        import trafilatura
        dl = trafilatura.fetch_url(url)
        texte = trafilatura.extract(dl, output_format="markdown")
        if texte:
            return texte[:20000]
    except Exception:
        pass
    raise ValueError("Impossible d'extraire le contenu de cette URL.")

def extraire_image_bytes(data: bytes, mime: str = "image/jpeg") -> str:
    import base64
    from openai import OpenAI
    b64 = base64.b64encode(data).decode()
    r = OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Décris cette image en détail. Si elle contient du texte, retranscris-le. Si c'est un graphique, explique les données."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
    )
    return r.choices[0].message.content

def extraire_pdf_bytes(data: bytes) -> str:
    import fitz
    doc = fitz.open(stream=data, filetype="pdf")
    return "\n".join(p.get_text() for p in doc)[:20000]

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
        return t.text[:20000]
    finally:
        os.unlink(tmp_path)

def analyser_contenu(contenu: str, source: str) -> str:
    from openai import OpenAI
    prompt = PROMPT_ANALYSE.format(
        source_md=formater_source(source),
        date_heure=datetime.now().strftime("%d/%m/%Y %H:%M"),
        contenu=contenu,
    )
    r = OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return r.choices[0].message.content

# ── Bloc-notes & Travail ──────────────────────────────────────────────────────

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
        texte = res.content.decode("utf-8")
    except dbx_mod.exceptions.ApiError:
        texte = f"# {header}\n\n"
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
    a_sup = {taches[i - 1][0] for i in indices if 1 <= i <= len(taches)}
    dbx.files_upload(
        "".join(l for i, l in enumerate(lignes) if i not in a_sup).encode("utf-8"),
        path, mode=dbx_mod.files.WriteMode.overwrite,
    )
    return len(a_sup)

# ── Inline keyboards ──────────────────────────────────────────────────────────

def kb_menu_principal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Dernières fiches",  callback_data="menu:dernieres")],
        [InlineKeyboardButton("✏️ Modifier une fiche", callback_data="menu:modifier")],
        [
            InlineKeyboardButton("💼 Travail",    callback_data="menu:travail"),
            InlineKeyboardButton("📝 Bloc-notes", callback_data="menu:blocnotes"),
            InlineKeyboardButton("🚀 Projets",    callback_data="menu:projets"),
        ],
        [InlineKeyboardButton("📅 Mon planning",    callback_data="menu:planning")],
        [InlineKeyboardButton("⚙️ Réglages météo", callback_data="menu:meteo")],
    ])

def kb_planning_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Uploader planning",  callback_data="planning:upload")],
        [InlineKeyboardButton("📅 Voir cette semaine", callback_data="planning:voir")],
        [InlineKeyboardButton("↩️ Retour",             callback_data="menu:accueil")],
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
        InlineKeyboardButton("🏷️ Tags",  callback_data=cb("edit_tags",   filename)),
        InlineKeyboardButton("✏️ Titre", callback_data=cb("edit_title",  filename)),
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
        [InlineKeyboardButton("➕ Ajouter un tag",      callback_data=cb("ta", filename))],
        [InlineKeyboardButton("➖ Enlever un tag",      callback_data=cb("tr", filename))],
        [InlineKeyboardButton("🔄 Réécrire tous les tags", callback_data=cb("tw", filename))],
        [InlineKeyboardButton("↩️ Annuler",             callback_data="ignore")],
    ])

def kb_tags_liste(filename: str, tags: list[str]) -> InlineKeyboardMarkup:
    boutons = [
        [InlineKeyboardButton(f"❌ {tag}", callback_data=f"td:{filename}:{tag.lstrip('#')}"[:64])]
        for tag in tags
    ]
    boutons.append([InlineKeyboardButton("↩️ Annuler", callback_data="ignore")])
    return InlineKeyboardMarkup(boutons)

def kb_liste_fiches(fiches: list, prefix: str = "view") -> InlineKeyboardMarkup:
    boutons = [
        [InlineKeyboardButton(f"📄 {f.name[:40]}", callback_data=cb(prefix, f.name))]
        for f in fiches
    ]
    return InlineKeyboardMarkup(boutons)

# ── Settings ──────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    import json
    import dropbox as dbx_mod
    try:
        _, res = get_dropbox().files_download(DROPBOX_SETTINGS)
        return {**_METEO_DEFAULTS, **json.loads(res.content)}
    except dbx_mod.exceptions.ApiError:
        return dict(_METEO_DEFAULTS)

def save_settings(s: dict) -> None:
    import json
    import dropbox as dbx_mod
    get_dropbox().files_upload(
        json.dumps(s, ensure_ascii=False, indent=2).encode(),
        DROPBOX_SETTINGS,
        mode=dbx_mod.files.WriteMode.overwrite,
    )

# ── Planning ──────────────────────────────────────────────────────────────────

def extraire_planning_image(data: bytes) -> dict:
    import base64, json
    from openai import OpenAI
    b64 = base64.b64encode(data).decode()
    prompt = PROMPT_PLANNING.format(today=datetime.now().strftime("%d/%m/%Y"))
    r = OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
        ]}],
        max_tokens=1000,
    )
    text = re.sub(r"```(?:json)?\s*", "", r.choices[0].message.content.strip()).strip("`").strip()
    return json.loads(text)

def load_planning() -> dict:
    import json
    import dropbox as dbx_mod
    try:
        _, res = get_dropbox().files_download(DROPBOX_PLANNING)
        return json.loads(res.content)
    except dbx_mod.exceptions.ApiError:
        return {}

def save_planning(days: dict) -> None:
    import json
    import dropbox as dbx_mod
    existing = load_planning()
    existing.update(days)
    get_dropbox().files_upload(
        json.dumps(existing, ensure_ascii=False, indent=2).encode(),
        DROPBOX_PLANNING,
        mode=dbx_mod.files.WriteMode.overwrite,
    )

async def envoyer_rappel_planning(context) -> None:
    if not TELEGRAM_CHAT_ID:
        return
    demain = datetime.now() + timedelta(days=1)
    key = demain.strftime("%Y-%m-%d")
    shift = load_planning().get(key)
    if not shift:
        return
    emoji, label = _SHIFTS_FR.get(shift, ("📅", shift))
    jour = _JOURS_FR[demain.weekday()]
    date_fmt = demain.strftime("%d/%m")
    await context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=f"📅 *Demain {jour} {date_fmt} :*\n\n{emoji} *{shift}* — {label}",
        parse_mode="Markdown",
    )

# ── Météo ─────────────────────────────────────────────────────────────────────

_WMO_FR = {
    0: ("☀️", "Ciel dégagé"),
    1: ("🌤️", "Peu nuageux"),
    2: ("⛅", "Partiellement nuageux"),
    3: ("☁️", "Couvert"),
    45: ("🌫️", "Brouillard"),
    48: ("🌫️", "Brouillard givrant"),
    51: ("🌦️", "Bruine légère"),
    53: ("🌦️", "Bruine modérée"),
    55: ("🌧️", "Bruine dense"),
    61: ("🌧️", "Pluie légère"),
    63: ("🌧️", "Pluie modérée"),
    65: ("🌧️", "Pluie forte"),
    71: ("🌨️", "Neige légère"),
    73: ("🌨️", "Neige modérée"),
    75: ("❄️", "Neige forte"),
    77: ("🌨️", "Grains de neige"),
    80: ("🌦️", "Averses légères"),
    81: ("🌧️", "Averses modérées"),
    82: ("⛈️", "Averses fortes"),
    85: ("🌨️", "Averses de neige"),
    86: ("❄️", "Averses de neige fortes"),
    95: ("⛈️", "Orage"),
    96: ("⛈️", "Orage avec grêle"),
    99: ("⛈️", "Orage violent avec grêle"),
}

def geocoder_ville(query: str) -> tuple:
    import requests
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": query, "count": 1, "language": "fr", "format": "json"},
        timeout=10,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise ValueError(f"Ville introuvable : {query}")
    res = results[0]
    nom   = res.get("name", query)
    pays  = res.get("country_code", "")
    label = f"{nom}, {pays}" if pays else nom
    return res["latitude"], res["longitude"], label

def get_meteo(lat: float, lon: float, ville: str) -> str:
    import requests
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=weathercode,temperature_2m_max,temperature_2m_min,"
        "precipitation_sum,windspeed_10m_max,uv_index_max"
        "&current_weather=true&timezone=Europe%2FParis"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    d = r.json()
    cur = d["current_weather"]
    day = {k: v[0] for k, v in d["daily"].items()}

    code = int(day["weathercode"])
    emoji, desc = _WMO_FR.get(code, ("🌡️", f"Code {code}"))
    t_cur = cur["temperature"]
    t_max = day["temperature_2m_max"]
    t_min = day["temperature_2m_min"]
    pluie = day["precipitation_sum"]
    vent  = day["windspeed_10m_max"]
    uv    = day["uv_index_max"]

    lignes = [
        f"🏔️ *Météo {ville} — {datetime.now().strftime('%d/%m/%Y')}*\n",
        f"{emoji} {desc}",
        f"🌡️ Maintenant : *{t_cur}°C*  •  Min {t_min}°C / Max {t_max}°C",
    ]
    if pluie > 0:
        lignes.append(f"🌧️ Précipitations : *{pluie} mm*")
    lignes.append(f"💨 Vent max : {vent} km/h")
    if uv >= 3:
        lignes.append(f"🕶️ UV : {uv}")
    return "\n".join(lignes)

async def envoyer_meteo_matin(context) -> None:
    if not TELEGRAM_CHAT_ID:
        return
    try:
        cfg = load_settings()
        texte = get_meteo(cfg["lat"], cfg["lon"], cfg["ville"])
    except Exception as e:
        log.warning("Erreur météo : %s", e)
        texte = "🌡️ Météo indisponible ce matin."
    await context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=texte,
        parse_mode="Markdown",
    )

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

# ── Recap scheduler ───────────────────────────────────────────────────────────

async def envoyer_recap_matin(context) -> None:
    if not TELEGRAM_CHAT_ID:
        return
    from zoneinfo import ZoneInfo
    h = datetime.now(ZoneInfo("Europe/Paris")).hour
    if 5 <= h < 12:
        salut = "☀️ *Bon matin !*"
    elif 12 <= h < 18:
        salut = "🌤️ *Bon après-midi !*"
    elif 18 <= h < 22:
        salut = "🌆 *Bonsoir !*"
    else:
        salut = "🌙 *Bonne nuit !*"

    travail   = lire_fichier_dropbox(DROPBOX_TRAVAIL).splitlines()
    blocnotes = lire_fichier_dropbox(DROPBOX_BLOCNOTES).splitlines()
    projets   = lire_fichier_dropbox(DROPBOX_PROJET).splitlines()
    parties = [salut + "\n"]
    if travail:
        parties.append("💼 *Travail :*\n" + "\n".join(f"  T{i+1} {t}" for i, t in enumerate(travail)))
    if blocnotes:
        parties.append("📝 *Bloc-notes :*\n" + "\n".join(f"  B{i+1} {b}" for i, b in enumerate(blocnotes)))
    if projets:
        parties.append("🚀 *Projets :*\n" + "\n".join(f"  P{i+1} {p}" for i, p in enumerate(projets)))
    if not travail and not blocnotes and not projets:
        parties.append("Aucune tâche en attente. Belle journée !")
    await context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text="\n\n".join(parties),
        parse_mode="Markdown",
    )

# ── Handlers ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🧠 *Second Cerveau* — je capture et organise tes connaissances.\n\n"
        "Envoie-moi une URL, un texte, une photo, un PDF ou un vocal.\n"
        "Préfixe par *travail*, *blocnote* ou *projet* pour ajouter directement.\n\n"
        "Que veux-tu faire ?",
        parse_mode="Markdown",
        reply_markup=kb_menu_principal(),
    )

async def cmd_dernieres(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message or update.callback_query.message
    fiches = lister_fiches(5)
    if not fiches:
        await msg.reply_text("Aucune fiche dans Dropbox pour l'instant.")
        return
    lignes = ["📚 *5 dernières fiches :*\n"]
    for f in fiches:
        date_str = f.server_modified.strftime("%d/%m %H:%M")
        lignes.append(f"• `{f.name}` _{date_str}_")
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
    lignes.append("\n_Tape_ `/done B1 B3` _pour cocher des notes_")
    await update.message.reply_text("\n".join(lignes), parse_mode="Markdown")

async def cmd_projet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    notes = lire_fichier_dropbox(DROPBOX_PROJET).splitlines()
    if not notes:
        await update.message.reply_text("🚀 Aucun projet en cours !")
        return
    lignes = ["🚀 *Projets en cours :*\n"] + [f"  P{i+1} {n}" for i, n in enumerate(notes)]
    lignes.append("\n_Tape_ `/done P1 P3` _pour cocher des projets_")
    await update.message.reply_text("\n".join(lignes), parse_mode="Markdown")

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        travail   = lire_fichier_dropbox(DROPBOX_TRAVAIL).splitlines()
        blocnotes = lire_fichier_dropbox(DROPBOX_BLOCNOTES).splitlines()
        projets   = lire_fichier_dropbox(DROPBOX_PROJET).splitlines()
        lignes = []
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
    msg = await update.message.reply_text("⏳ Mise à jour…")
    total = 0
    if t_idx: total += supprimer_taches(DROPBOX_TRAVAIL,   t_idx)
    if b_idx: total += supprimer_taches(DROPBOX_BLOCNOTES, b_idx)
    if p_idx: total += supprimer_taches(DROPBOX_PROJET,    p_idx)
    await msg.edit_text(f"✅ {total} tâche(s) cochée(s) !")

async def cmd_monid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"🪪 Ton Chat ID : `{update.effective_chat.id}`",
        parse_mode="Markdown",
    )

# ── Capture ───────────────────────────────────────────────────────────────────

async def _confirmer_capture(msg, path: str) -> None:
    nom = path.split("/")[-1]
    await msg.edit_text(
        f"✅ *Capturé !*\n\n`{nom}`\n\n_Veux-tu modifier quelque chose ?_",
        parse_mode="Markdown",
        reply_markup=kb_apres_capture(nom),
    )

async def traiter_texte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texte = (update.message.text or "").strip()
    premier_mot = texte.split()[0].lower() if texte else ""

    # ── Mode édition en attente ──
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
                    f"✅ Ville mise à jour : *{label}*\n"
                    f"📍 Coordonnées : {lat:.4f}, {lon:.4f}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                await msg.edit_text(f"❌ {e}")
            return
        await _appliquer_edit(update, context, edit, texte)
        return

    # ── Routage travail / blocnote ──
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

    # ── Capture normale ──
    msg = await update.message.reply_text("⏳ Traitement en cours…")
    try:
        if texte.startswith("http://") or texte.startswith("https://"):
            contenu = extraire_url(texte)
            source = texte
        else:
            contenu = texte[:20000]
            source = "telegram-note"
        fiche_md = analyser_contenu(contenu, source)
        path = uploader_fiche(fiche_md)
        await _confirmer_capture(msg, path)
    except Exception as e:
        log.exception("Erreur texte")
        await msg.edit_text(f"❌ {e}")

async def _traiter_planning_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Extraction du planning…")
    try:
        buf = io.BytesIO()
        await (await update.message.photo[-1].get_file()).download_to_memory(buf)
        result = extraire_planning_image(buf.getvalue())
        if "error" in result:
            await msg.edit_text("❌ Tristan introuvable dans ce screenshot. Vérifie que ta ligne est bien visible.")
            return
        days = result.get("days", {})
        semaine = result.get("week", "?")
        save_planning(days)
        lignes = [f"✅ *Planning semaine {semaine} enregistré !*\n"]
        for d, c in sorted(days.items()):
            emoji, label = _SHIFTS_FR.get(c, ("📅", c))
            dt = datetime.strptime(d, "%Y-%m-%d")
            lignes.append(f"• {_JOURS_FR[dt.weekday()]} {dt.strftime('%d/%m')} : {emoji} *{c}* — {label}")
        await msg.edit_text("\n".join(lignes), parse_mode="Markdown")
    except Exception as e:
        log.exception("Erreur planning photo")
        await msg.edit_text(f"❌ Erreur extraction planning : {e}")

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
        buf = io.BytesIO()
        await (await update.message.photo[-1].get_file()).download_to_memory(buf)
        data = buf.getvalue()
        nom = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        contenu = extraire_image_bytes(data)
        fiche_md = analyser_contenu(contenu, f"telegram-photo:{nom}")
        path = uploader_fiche(fiche_md)
        uploader_raw(data, nom)
        await _confirmer_capture(msg, path)
    except Exception as e:
        log.exception("Erreur photo")
        await msg.edit_text(f"❌ {e}")

async def traiter_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Extraction du document…")
    try:
        doc = update.message.document
        ext = os.path.splitext(doc.file_name)[1].lower()
        if ext not in {".pdf", ".txt", ".md"}:
            await msg.edit_text("❌ Format non supporté. Envoie un PDF ou un fichier texte.")
            return
        buf = io.BytesIO()
        await (await doc.get_file()).download_to_memory(buf)
        data = buf.getvalue()
        contenu = extraire_pdf_bytes(data) if ext == ".pdf" else data.decode("utf-8", errors="ignore")[:20000]
        fiche_md = analyser_contenu(contenu, f"telegram-doc:{doc.file_name}")
        path = uploader_fiche(fiche_md)
        if ext == ".pdf":
            uploader_raw(data, doc.file_name)
        await _confirmer_capture(msg, path)
    except Exception as e:
        log.exception("Erreur document")
        await msg.edit_text(f"❌ {e}")

async def traiter_vocal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Transcription audio…")
    try:
        buf = io.BytesIO()
        await (await update.message.voice.get_file()).download_to_memory(buf)
        transcription = extraire_audio_tmp(buf.getvalue(), ".ogg").strip()
        premier_mot = transcription.split()[0].lower() if transcription else ""

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
            fiche_md = analyser_contenu(transcription, "telegram-vocal")
            path = uploader_fiche(fiche_md)
            await _confirmer_capture(msg, path)
    except Exception as e:
        log.exception("Erreur vocal")
        await msg.edit_text(f"❌ {e}")

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
        else:  # title
            nouveau_path = modifier_titre_dropbox(path, valeur.strip())
            await update.message.reply_text(f"✅ Fiche renommée :\n`{nouveau_path.split('/')[-1]}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur modification : {e}")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "ignore":
        await query.edit_message_reply_markup(reply_markup=None)
        return

    if data == "menu:dernieres":
        fiches = lister_fiches(5)
        if not fiches:
            await query.edit_message_text("Aucune fiche pour l'instant.")
            return
        lignes = ["📚 *5 dernières fiches :*\n"]
        for f in fiches:
            lignes.append(f"• `{f.name}` _{f.server_modified.strftime('%d/%m %H:%M')}_")
        await query.edit_message_text(
            "\n".join(lignes),
            parse_mode="Markdown",
            reply_markup=kb_liste_fiches(fiches, prefix="edit_fiche"),
        )
        return

    if data == "menu:modifier":
        fiches = lister_fiches(5)
        if not fiches:
            await query.edit_message_text("Aucune fiche à modifier.")
            return
        await query.edit_message_text(
            "✏️ *Quelle fiche veux-tu modifier ?*",
            parse_mode="Markdown",
            reply_markup=kb_liste_fiches(fiches, prefix="edit_fiche"),
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

    if data.startswith("edit_fiche:"):
        filename = data[len("edit_fiche:"):]
        await query.edit_message_text(
            f"✏️ *{filename}*\n\nQue veux-tu modifier ?",
            parse_mode="Markdown",
            reply_markup=kb_modifier_fiche(filename),
        )
        return

    if data.startswith("edit_tags:"):
        filename = data[len("edit_tags:"):]
        path = f"{DROPBOX_ROOT}/{filename}"
        tags_actuels = extraire_champ(telecharger_fiche(path), "TAGS")
        await query.edit_message_text(
            f"🏷️ *Tags actuels :* `{tags_actuels or 'aucun'}`\n\nQue veux-tu faire ?",
            parse_mode="Markdown",
            reply_markup=kb_tags_menu(filename),
        )
        return

    if data.startswith("ta:"):  # ajouter tag
        filename = data[3:]
        context.user_data["pending_edit"] = {"filename": filename, "type": "tags_add"}
        await query.edit_message_text(
            "➕ Envoie le tag à ajouter _(ex : #python)_ :",
            parse_mode="Markdown",
        )
        return

    if data.startswith("tr:"):  # enlever tag — affiche la liste
        filename = data[3:]
        path = f"{DROPBOX_ROOT}/{filename}"
        tags_actuels = extraire_champ(telecharger_fiche(path), "TAGS")
        tags_liste = [t for t in tags_actuels.split() if t.startswith("#")]
        if not tags_liste:
            await query.edit_message_text("Aucun tag à supprimer.")
            return
        await query.edit_message_text(
            "➖ *Quel tag veux-tu enlever ?*",
            parse_mode="Markdown",
            reply_markup=kb_tags_liste(filename, tags_liste),
        )
        return

    if data.startswith("td:"):  # supprimer un tag précis
        _, filename, tag = data.split(":", 2)
        path = f"{DROPBOX_ROOT}/{filename}"
        restants = supprimer_tag_dropbox(path, tag)
        await query.edit_message_text(
            f"✅ Tag `#{tag}` supprimé.\nTags restants : `{restants or 'aucun'}`",
            parse_mode="Markdown",
        )
        return

    if data.startswith("tw:"):  # réécrire tous les tags
        filename = data[3:]
        context.user_data["pending_edit"] = {"filename": filename, "type": "tags_rewrite"}
        await query.edit_message_text(
            "🔄 Envoie les nouveaux tags _(ex : #react #python #api)_ :",
            parse_mode="Markdown",
        )
        return

    if data.startswith("edit_title:"):
        filename = data[len("edit_title:"):]
        path = f"{DROPBOX_ROOT}/{filename}"
        titre_actuel = extraire_champ(telecharger_fiche(path), "TITRE")
        context.user_data["pending_edit"] = {"filename": filename, "type": "title"}
        await query.edit_message_text(
            f"✏️ *Titre actuel :*\n`{titre_actuel}`\n\n"
            "Envoie le nouveau titre _(3 mots max, très descriptif)_ :",
            parse_mode="Markdown",
        )
        return

    if data == "menu:planning":
        await query.edit_message_text(
            "📅 *Mon planning*\n\nUploade ton screenshot chaque semaine pour recevoir un rappel à 22h la veille de chaque shift.",
            parse_mode="Markdown",
            reply_markup=kb_planning_menu(),
        )
        return

    if data == "planning:upload":
        context.user_data["pending_planning_upload"] = True
        await query.edit_message_text(
            "📤 Envoie le screenshot de ton planning.\n"
            "_Tu peux aussi envoyer une photo avec la légende_ `planning` _n'importe quand._",
            parse_mode="Markdown",
        )
        return

    if data == "planning:voir":
        planning = load_planning()
        debut = datetime.now() - timedelta(days=datetime.now().weekday())
        lignes = ["📅 *Semaine en cours :*\n"]
        trouvé = False
        for i in range(7):
            d = (debut + timedelta(days=i)).strftime("%Y-%m-%d")
            if d in planning:
                trouvé = True
                c = planning[d]
                emoji, label = _SHIFTS_FR.get(c, ("📅", c))
                dt = datetime.strptime(d, "%Y-%m-%d")
                lignes.append(f"• {_JOURS_FR[dt.weekday()]} {dt.strftime('%d/%m')} : {emoji} *{c}* — {label}")
        if not trouvé:
            lignes.append("_Aucune donnée pour cette semaine._\nUploade ton planning !")
        await query.edit_message_text(
            "\n".join(lignes),
            parse_mode="Markdown",
            reply_markup=kb_planning_menu(),
        )
        return

    if data == "menu:accueil":
        await query.edit_message_text(
            "🧠 *Second Cerveau* — Que veux-tu faire ?",
            parse_mode="Markdown",
            reply_markup=kb_menu_principal(),
        )
        return

    if data == "menu:meteo":
        cfg = load_settings()
        await query.edit_message_text(
            f"⚙️ *Réglages météo*\n\n"
            f"📍 Ville : *{cfg['ville']}*\n"
            f"⏰ Heure : *{cfg['heure']}h00*",
            parse_mode="Markdown",
            reply_markup=kb_meteo_settings(),
        )
        return

    if data == "ms:ville":
        context.user_data["pending_edit"] = {"type": "meteo_ville"}
        await query.edit_message_text(
            "📍 Envoie le nom de ta ville _(ex : Genève, CH)_ :",
            parse_mode="Markdown",
        )
        return

    if data == "ms:heure":
        cfg = load_settings()
        await query.edit_message_text(
            "⏰ *À quelle heure recevoir la météo ?*",
            parse_mode="Markdown",
            reply_markup=kb_meteo_heures(cfg["heure"]),
        )
        return

    if data.startswith("ms:h:"):
        heure = int(data[5:])
        cfg = load_settings()
        cfg["heure"] = heure
        save_settings(cfg)
        reprogrammer_meteo(context.application, heure)
        await query.edit_message_text(
            f"✅ Météo reprogrammée à *{heure}h00* chaque matin.",
            parse_mode="Markdown",
            reply_markup=kb_meteo_settings(),
        )
        return

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TELEGRAM_TOKEN:  sys.exit("TELEGRAM_BOT_TOKEN manquant.")
    if not OPENAI_API_KEY:  sys.exit("OPENAI_API_KEY manquante.")
    if not (DROPBOX_TOKEN or (DROPBOX_APP_KEY and DROPBOX_APP_SECRET and DROPBOX_REFRESH)):
        sys.exit("Token Dropbox manquant.")

    log.info("🤖 Bot démarré — Dropbox : %s", DROPBOX_ROOT)

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Schedulers
    if TELEGRAM_CHAT_ID and app.job_queue:
        import datetime as dt
        from zoneinfo import ZoneInfo
        paris = ZoneInfo("Europe/Paris")
        cfg = load_settings()
        app.job_queue.run_daily(
            envoyer_meteo_matin,
            time=dt.time(cfg["heure"], 0, tzinfo=paris),
            name="meteo_matin",
        )
        for h in [8, 12, 18, 22]:
            app.job_queue.run_daily(envoyer_recap_matin, time=dt.time(h, 0, tzinfo=paris))
        app.job_queue.run_daily(envoyer_rappel_planning, time=dt.time(22, 0, tzinfo=paris))
        log.info("⏰ Météo à %dh, récaps à 8h 12h 18h 22h, rappel planning à 22h (Paris)", cfg["heure"])

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("dernieres", cmd_dernieres))
    app.add_handler(CommandHandler("travail",   cmd_travail))
    app.add_handler(CommandHandler("blocnotes", cmd_blocnotes))
    app.add_handler(CommandHandler("projet",    cmd_projet))
    app.add_handler(CommandHandler("projets",   cmd_projet))
    app.add_handler(CommandHandler("done",      cmd_done))
    app.add_handler(CommandHandler("monid",     cmd_monid))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, traiter_texte))
    app.add_handler(MessageHandler(filters.PHOTO,        traiter_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, traiter_document))
    app.add_handler(MessageHandler(filters.VOICE,        traiter_vocal))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
