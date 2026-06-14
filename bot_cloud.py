"""
bot_cloud.py — Second Cerveau Bot Telegram (Railway)
Capture → Groq → Dropbox | Menus inline | Modification de fiches
"""
import io, os, re, sys, json, logging, tempfile, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)

from core import (
    formater_source, extraire_champ, slugifier,
    nettoyer_contenu, evaluer_qualite, extraire_url,
    analyser_contenu, chercher_fiches, geocoder_ville, get_meteo,
    appeler_groq_vision,
    _WMO_FR, LIMITE_EXTRACTION,
)
from dropbox_client import (
    DROPBOX_ROOT, DROPBOX_RAW, DROPBOX_BLOCNOTES, DROPBOX_TRAVAIL,
    DROPBOX_PROJET, DROPBOX_SETTINGS, DROPBOX_PLANNING, DROPBOX_CAPTURES_INDEX,
    uploader_fiche, uploader_raw,
    lister_fiches, lister_toutes_fiches, telecharger_fiche,
    modifier_tags_dropbox, ajouter_tag_dropbox, supprimer_tag_dropbox,
    modifier_titre_dropbox, charger_index_captures, enregistrer_capture,
    lire_fichier_dropbox, ajouter_blocnote, ajouter_travail,
    ajouter_projet, supprimer_taches, load_settings, save_settings,
    load_planning, save_planning,
)

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

TELEGRAM_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
DROPBOX_TOKEN      = os.environ.get("DROPBOX_ACCESS_TOKEN")
DROPBOX_APP_KEY    = os.environ.get("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET")
DROPBOX_REFRESH    = os.environ.get("DROPBOX_REFRESH_TOKEN")

# Limite taille fichiers entrants (Step I)
MAX_DOC_SIZE_MB  = 10
MAX_VOCAL_SECS   = 300  # 5 minutes

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

TRIGGERS_TRAVAIL   = {"travail"}
TRIGGERS_BLOCNOTES = {"blocnote", "bloc-note", "blocnotes", "bloc-notes"}
TRIGGERS_PROJET    = {"projet", "projets"}

# ── Auth filter (Step A) ───────────────────────────────────────────────────────

if TELEGRAM_CHAT_ID:
    _CHAT_FILTER = filters.Chat(int(TELEGRAM_CHAT_ID))
else:
    _CHAT_FILTER = filters.ALL
    log.warning("⚠️  TELEGRAM_CHAT_ID non défini — toutes les conversations sont acceptées.")

_START_TIME = datetime.now()

# ── Helpers ───────────────────────────────────────────────────────────────────

def cb(prefix: str, filename: str) -> str:
    """Construit une callback_data ≤ 64 octets."""
    return f"{prefix}:{filename}"[:64]


def erreur_msg(e: Exception) -> str:
    """Message d'erreur utilisateur propre — masque les détails techniques."""
    msg = str(e)
    msg = re.sub(r'https?://\S+', '[URL]', msg)
    return f"❌ {msg[:200]}"

# ── Extraction multimédia ─────────────────────────────────────────────────────

def extraire_image_bytes(data: bytes, mime: str = "image/jpeg") -> str:
    return appeler_groq_vision(
        data,
        "Décris cette image en détail. Si elle contient du texte, retranscris-le. "
        "Si c'est un graphique, explique les données.",
        mime,
    )


def extraire_pdf_bytes(data: bytes) -> str:
    import fitz
    doc = fitz.open(stream=data, filetype="pdf")
    return "\n".join(p.get_text() for p in doc)[:LIMITE_EXTRACTION]


def extraire_audio_tmp(data: bytes, ext: str = ".ogg") -> str:
    from groq import Groq
    from pathlib import Path as _Path
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante. Ajoutez-la dans le fichier .env")
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        client = Groq(api_key=api_key)
        with open(tmp_path, "rb") as f:
            t = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=(_Path(tmp_path).name, f),
            )
        return t.text[:LIMITE_EXTRACTION]
    finally:
        os.unlink(tmp_path)


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

# ── Calendrier helpers ────────────────────────────────────────────────────────

DROPBOX_CALENDAR = "/Applications/Joplin/calendar_events.json"
_CAL_TYPES = {"rdv", "anniversaire", "tache", "deadline"}


def _read_calendar_dropbox() -> list[dict]:
    from dropbox_client import lire_fichier_dropbox
    try:
        content = lire_fichier_dropbox(DROPBOX_CALENDAR)
        return json.loads(content) if content else []
    except Exception:
        return []


def _write_calendar_dropbox(events: list[dict]) -> None:
    import dropbox as _dbx_mod
    from brain_agent import get_dropbox
    dbx = get_dropbox()
    data = json.dumps(events, ensure_ascii=False, indent=2).encode("utf-8")
    dbx.files_upload(data, DROPBOX_CALENDAR, mode=_dbx_mod.files.WriteMode.overwrite)


def _upsert_calendar_event(event: dict) -> None:
    events = _read_calendar_dropbox()
    existing = next((e for e in events if e["id"] == event["id"]), None)
    if existing:
        existing.update(event)
    else:
        events.append(event)
    _write_calendar_dropbox(events)


async def _parse_event_from_text(text: str) -> dict | None:
    """Parse un texte libre en event structuré via Groq."""
    from groq import Groq
    today = datetime.now().strftime("%Y-%m-%d")
    client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Aujourd'hui : {today}. Timezone: Europe/Paris. "
                        "Tu extrais les informations d'un événement depuis un texte en français. "
                        "Réponds UNIQUEMENT en JSON valide avec les clés : "
                        "titre (string), type (rdv|anniversaire|tache|deadline), "
                        "date_debut (ISO 8601 : YYYY-MM-DD ou YYYY-MM-DDTHH:MM). "
                        "Si l'heure n'est pas précisée, utilise seulement la date (YYYY-MM-DD). "
                        "Résous les dates relatives (demain, lundi prochain, dans 3 jours…) par rapport à aujourd'hui."
                    )
                },
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        if data.get("type") not in _CAL_TYPES:
            data["type"] = "rdv"
        return data
    except Exception as e:
        log.error("Erreur parsing /rdv : %s", e)
        return None


# État temporaire pour les confirmations /rdv en attente
_pending_rdv: dict[int, dict] = {}  # chat_id → event dict


async def cmd_rdv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text(
            "Usage : `/rdv [description]`\nEx: `/rdv médecin demain à 14h`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("⏳ Analyse en cours…")
    parsed = await _parse_event_from_text(text)
    if not parsed:
        await update.message.reply_text("❌ Je n'ai pas réussi à analyser cet événement. Réessaie.")
        return

    _ICONS_BOT = {"rdv": "📅", "anniversaire": "🎂", "tache": "✅", "deadline": "⏰"}
    icon = _ICONS_BOT.get(parsed.get("type", "rdv"), "📅")
    date_str = parsed.get("date_debut", "?")

    event = {
        "id": str(__import__("uuid").uuid4()),
        "titre": parsed["titre"],
        "type": parsed.get("type", "rdv"),
        "date_debut": date_str,
        "date_fin": None,
        "description": None,
        "reminders": [],
        "deleted": False,
        "source": "telegram",
        "updated_at": datetime.now().isoformat(),
    }
    _pending_rdv[update.effective_chat.id] = event

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Oui", callback_data=f"cal:confirm:{event['id']}"),
        InlineKeyboardButton("✏️ Corriger", callback_data=f"cal:cancel_rdv"),
    ]])
    await update.message.reply_text(
        f"J'ai compris :\n{icon} *{event['titre']}* — `{date_str}`\n\nC'est bien ça ?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def cmd_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    events = _read_calendar_dropbox()
    today = datetime.now().date().isoformat()
    upcoming = sorted(
        [e for e in events if not e.get("deleted") and e.get("date_debut", "") >= today],
        key=lambda e: e["date_debut"]
    )[:10]

    if not upcoming:
        await update.message.reply_text("Aucun événement à venir. Utilise `/rdv` pour en ajouter.")
        return

    _ICONS_BOT = {"rdv": "📅", "anniversaire": "🎂", "tache": "✅", "deadline": "⏰"}
    for ev in upcoming:
        icon = _ICONS_BOT.get(ev.get("type", "rdv"), "📅")
        date_str = ev.get("date_debut", "?")
        titre = ev.get("titre", "?")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✏️ Éditer", callback_data=f"cal:edit:{ev['id']}"),
            InlineKeyboardButton("🗑️ Supprimer", callback_data=f"cal:del:{ev['id']}"),
        ]])
        await update.message.reply_text(
            f"{icon} *{titre}*\n📆 `{date_str}`",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


async def cb_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data  # ex: "cal:del:uuid", "cal:confirm:uuid", "cal:edit:uuid"

    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    event_id = parts[2] if len(parts) > 2 else ""

    # ── Confirmation /rdv ───────────────────────────────────────────────
    if action == "confirm":
        event = _pending_rdv.pop(query.message.chat.id, None)
        if not event or event["id"] != event_id:
            await query.edit_message_text("❌ Session expirée. Relance `/rdv`.")
            return
        _upsert_calendar_event(event)
        _ICONS_BOT = {"rdv": "📅", "anniversaire": "🎂", "tache": "✅", "deadline": "⏰"}
        icon = _ICONS_BOT.get(event["type"], "📅")
        await query.edit_message_text(
            f"✅ Enregistré !\n{icon} *{event['titre']}* — `{event['date_debut']}`",
            parse_mode="Markdown"
        )
        return

    if action == "cancel_rdv":
        _pending_rdv.pop(query.message.chat.id, None)
        await query.edit_message_text("❌ Annulé. Relance `/rdv` avec plus de précision.")
        return

    # ── Suppression ─────────────────────────────────────────────────────
    if action == "del":
        events = _read_calendar_dropbox()
        ev = next((e for e in events if e["id"] == event_id), None)
        if not ev:
            await query.edit_message_text("❌ Événement introuvable.")
            return
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Oui, supprimer", callback_data=f"cal:delok:{event_id}"),
            InlineKeyboardButton("Non", callback_data=f"cal:delno:{event_id}"),
        ]])
        await query.edit_message_text(
            f"Supprimer *{ev['titre']}* ?", parse_mode="Markdown", reply_markup=keyboard
        )
        return

    if action == "delok":
        events = _read_calendar_dropbox()
        for ev in events:
            if ev["id"] == event_id:
                ev["deleted"] = True
                ev["updated_at"] = datetime.now().isoformat()
        _write_calendar_dropbox(events)
        await query.edit_message_text("🗑️ Événement supprimé.")
        return

    if action == "delno":
        await query.edit_message_text("OK, annulé.")
        return

    # ── Édition ─────────────────────────────────────────────────────────
    if action == "edit":
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Titre", callback_data=f"cal:edittitle:{event_id}"),
            InlineKeyboardButton("Date/Heure", callback_data=f"cal:editdate:{event_id}"),
        ]])
        await query.edit_message_text("Que veux-tu modifier ?", reply_markup=keyboard)
        return

    if action == "edittitle":
        context.user_data["cal_edit"] = {"event_id": event_id, "field": "titre"}
        await query.edit_message_text("Envoie le nouveau titre :")
        return

    if action == "editdate":
        context.user_data["cal_edit"] = {"event_id": event_id, "field": "date"}
        await query.edit_message_text("Envoie la nouvelle date (ex: demain à 14h) :")
        return


# ── Handlers commandes ────────────────────────────────────────────────────────

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    total_secs = int((datetime.now() - _START_TIME).total_seconds())
    h, remainder = divmod(total_secs, 3600)
    m = remainder // 60
    await update.message.reply_text(f"🏓 Pong — uptime {h}h{m:02d}m")


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

    # ── Édition calendrier en attente ─────────────────────────────────
    cal_edit = context.user_data.pop("cal_edit", None)
    if cal_edit:
        events = _read_calendar_dropbox()
        ev = next((e for e in events if e["id"] == cal_edit["event_id"]), None)
        if ev:
            field = cal_edit["field"]
            if field == "titre":
                ev["titre"] = update.message.text.strip()
            elif field == "date":
                parsed = await _parse_event_from_text(update.message.text)
                if parsed:
                    ev["date_debut"] = parsed["date_debut"]
            ev["updated_at"] = datetime.now().isoformat()
            _write_calendar_dropbox(events)
            await update.message.reply_text(
                f"✅ Modifié : *{ev['titre']}* — `{ev['date_debut']}`",
                parse_mode="Markdown"
            )
        return

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


async def traiter_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    if doc.file_size and doc.file_size > MAX_DOC_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(
            f"❌ Fichier trop volumineux (max {MAX_DOC_SIZE_MB} Mo). Compresse le PDF avant d'envoyer."
        )
        return

    if ext not in {".pdf", ".txt", ".md"}:
        await update.message.reply_text("❌ Format non supporté. Envoie un PDF ou un fichier texte (.txt, .md).")
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
        return


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
        return


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

# ── post_init — enregistrement des commandes Telegram (Step J) ────────────────

async def post_init(application: Application) -> None:
    await application.bot.set_my_commands([
        ("start",     "Menu principal"),
        ("dernieres", "5 dernières fiches"),
        ("chercher",  "Rechercher dans les fiches"),
        ("travail",   "Voir les tâches"),
        ("blocnotes", "Voir le bloc-notes"),
        ("done",      "Cocher des tâches — ex: T1 B2"),
        ("ping",      "Uptime du bot"),
        ("help",      "Aide et commandes"),
        ("monid",     "Voir ton Chat ID"),
    ])
    log.info("✅ Commandes Telegram enregistrées")
    if TELEGRAM_CHAT_ID:
        try:
            await application.bot.send_message(
                chat_id=int(TELEGRAM_CHAT_ID),
                text=f"✅ Bot démarré — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            )
        except Exception as e:
            log.warning("Erreur notification démarrage : %s", e)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    import traceback as _tb
    tb = "".join(_tb.format_exception(
        type(context.error), context.error, context.error.__traceback__
    ))[-600:]
    log.error("Exception non gérée : %s", tb)
    if TELEGRAM_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=int(TELEGRAM_CHAT_ID),
                text=f"❌ Erreur bot :\n```\n{tb}\n```",
                parse_mode="Markdown",
            )
        except Exception:
            pass


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def _start_health_server() -> None:
    port = int(os.environ.get("HEALTH_PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("Health check actif sur port %d", port)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TELEGRAM_TOKEN:
        sys.exit("TELEGRAM_BOT_TOKEN manquant.")
    if not (DROPBOX_TOKEN or (DROPBOX_APP_KEY and DROPBOX_APP_SECRET and DROPBOX_REFRESH)):
        sys.exit("Token Dropbox manquant.")

    log.info("🤖 Bot démarré — Dropbox : %s", DROPBOX_ROOT)

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .get_updates_read_timeout(10)  # réduit la fenêtre de conflit au redémarrage Railway
        .build()
    )
    app.add_error_handler(error_handler)

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
    app.add_handler(CommandHandler("ping",      cmd_ping,      filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("rdv",       cmd_rdv,       filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("agenda",    cmd_agenda,    filters=_CHAT_FILTER))
    app.add_handler(CommandHandler("monid",     cmd_monid))  # pas de filtre : utile pour setup
    app.add_handler(CallbackQueryHandler(cb_calendar, pattern=r"^cal:"))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(_CHAT_FILTER & filters.TEXT & ~filters.COMMAND, traiter_texte))
    app.add_handler(MessageHandler(_CHAT_FILTER & filters.PHOTO,        traiter_photo))
    app.add_handler(MessageHandler(_CHAT_FILTER & filters.Document.ALL, traiter_document))
    app.add_handler(MessageHandler(_CHAT_FILTER & filters.VOICE,        traiter_vocal))

    _start_health_server()
    # Railway rolling deploy : le health server démarre d'abord → Railway SIGTERM l'ancien
    # container → PTB annule son getUpdates. On attend 5s pour éviter le Conflict.
    import time; time.sleep(5)
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
