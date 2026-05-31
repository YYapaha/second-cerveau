"""
bot_cloud.py — Bot Telegram pour Railway
Capture → Gemini → Dropbox (pas de stockage local)
"""
import io
import os
import re
import sys
import logging
import tempfile
import unicodedata
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY     = os.environ["OPENAI_API_KEY"]
TELEGRAM_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
DROPBOX_TOKEN      = os.environ.get("DROPBOX_ACCESS_TOKEN")
DROPBOX_APP_KEY    = os.environ.get("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET")
DROPBOX_REFRESH    = os.environ.get("DROPBOX_REFRESH_TOKEN")
ENABLE_WHISPER     = os.environ.get("ENABLE_WHISPER", "false").lower() == "true"

DROPBOX_FICHES    = "/second_cerveau/fiches"
DROPBOX_RAW       = "/second_cerveau/raw"
DROPBOX_BLOCNOTES = "/second_cerveau/blocnotes.md"
DROPBOX_TRAVAIL   = "/second_cerveau/travail.md"

TRIGGERS_BLOCNOTES = {"blocnote", "bloc-note", "blocnotes", "bloc-notes"}
TRIGGERS_TRAVAIL   = {"travail"}

PROMPT_ANALYSE = """Analyse ce contenu et crée une fiche markdown avec EXACTEMENT ce format :

---
**TITRE** : (5 à 7 mots maximum, résume précisément le sujet, comme un titre de livre)
**SOURCE** : {source}
**DATE** : {date}
**TAGS** : #tag1 #tag2 #tag3 #tag4 #tag5
**TYPE** : [Tutoriel|Réflexion|Outil|Recherche|Code|Note|Transcription|Image]
**POURQUOI_GARDER** : (1 phrase qui me rappellera dans 6 mois pourquoi c'était utile)
**IDEE_PRINCIPALE** : (2-3 phrases)
**POINTS_CLES** :
- Point concret 1
- Point concret 2
- Point concret 3
**QUAND_RESSORTIR** : "Quand je ferai [tâche], je devrais penser à [ceci]"
**RESUME_30_SEC** : (résumé que je peux lire en 30 secondes maximum)
**RESUME_COMPLET** : (analyse détaillée)
---

Règles pour le TITRE : 5 à 7 mots max, pas de ponctuation, pas de guillemets.
Exemples : "React Server Components optimisation bundle", "Whisper transcription audio locale Python"

Contenu à analyser :
{contenu}"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def extraire_champ(fiche_md: str, champ: str) -> str:
    match = re.search(rf"\*\*{champ}\*\*\s*:\s*(.+?)(?=\n\*\*|\Z)", fiche_md, re.DOTALL)
    return match.group(1).strip() if match else ""


def slugifier(texte: str, max_len: int = 50) -> str:
    texte = unicodedata.normalize("NFKD", texte)
    texte = texte.encode("ascii", "ignore").decode("ascii")
    texte = texte.lower()
    texte = re.sub(r"[^\w\s-]", "", texte)
    texte = re.sub(r"[\s\-]+", "_", texte)
    texte = texte.strip("_")
    return texte[:max_len].rstrip("_") or "note"


def chemin_dropbox(fiche_md: str) -> str:
    """Construit le chemin Dropbox : /second_cerveau/fiches/TYPE/slug.md"""
    type_gemini = extraire_champ(fiche_md, "TYPE")
    type_gemini = re.sub(r"[\[\]/|]", "", type_gemini).strip()
    sous_dossier = re.sub(r"\s+", "_", type_gemini) if type_gemini else "Divers"

    titre = extraire_champ(fiche_md, "TITRE")
    if titre:
        slug = slugifier(titre)
    else:
        idee = extraire_champ(fiche_md, "IDEE_PRINCIPALE")
        slug = slugifier(idee.split(".")[0]) if idee else "note_sans_titre"

    return f"{DROPBOX_FICHES}/{sous_dossier}/{slug}.md"

# ── Dropbox ───────────────────────────────────────────────────────────────────

def get_dropbox():
    import dropbox
    if DROPBOX_TOKEN:
        return dropbox.Dropbox(DROPBOX_TOKEN)
    if DROPBOX_APP_KEY and DROPBOX_APP_SECRET and DROPBOX_REFRESH:
        return dropbox.Dropbox(
            oauth2_refresh_token=DROPBOX_REFRESH,
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET,
        )
    raise EnvironmentError(
        "Configure DROPBOX_ACCESS_TOKEN ou "
        "DROPBOX_APP_KEY + DROPBOX_APP_SECRET + DROPBOX_REFRESH_TOKEN"
    )


def uploader_fiche(fiche_md: str) -> str:
    """Upload la fiche Markdown vers Dropbox. Retourne le chemin Dropbox."""
    import dropbox as dbx_module
    dbx = get_dropbox()
    path = chemin_dropbox(fiche_md)
    data = fiche_md.encode("utf-8")
    dbx.files_upload(data, path, mode=dbx_module.files.WriteMode.overwrite)
    log.info("Fiche uploadée : %s", path)
    return path


def uploader_raw(data: bytes, nom_fichier: str) -> str:
    """Upload un fichier original (photo, PDF) dans /second_cerveau/raw/."""
    import dropbox as dbx_module
    dbx = get_dropbox()
    path = f"{DROPBOX_RAW}/{nom_fichier}"
    dbx.files_upload(data, path, mode=dbx_module.files.WriteMode.overwrite)
    log.info("Fichier raw uploadé : %s", path)
    return path


def lister_dernieres_fiches(n: int = 5) -> list[dict]:
    """Liste les n dernières fiches dans Dropbox (triées par date de modif)."""
    import dropbox
    dbx = get_dropbox()
    try:
        result = dbx.files_list_folder(DROPBOX_FICHES, recursive=True)
        fiches = [
            {"name": e.name, "modified": e.server_modified}
            for e in result.entries
            if isinstance(e, dropbox.files.FileMetadata) and e.name.endswith(".md")
        ]
        fiches.sort(key=lambda x: x["modified"], reverse=True)
        return fiches[:n]
    except Exception as e:
        log.warning("Impossible de lister les fiches Dropbox : %s", e)
        return []

# ── Extraction de contenu ─────────────────────────────────────────────────────

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
        downloaded = trafilatura.fetch_url(url)
        texte = trafilatura.extract(downloaded, output_format="markdown")
        if texte:
            return texte[:20000]
    except Exception:
        pass
    raise ValueError("Impossible d'extraire le contenu de cette URL.")


def extraire_image_bytes(data: bytes, mime: str = "image/jpeg") -> str:
    import base64
    from openai import OpenAI
    b64 = base64.b64encode(data).decode()
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Décris cette image en détail. Si elle contient du texte, retranscris-le. Si c'est un graphique, explique les données."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
    )
    return response.choices[0].message.content


def extraire_pdf_bytes(data: bytes) -> str:
    import fitz
    doc = fitz.open(stream=data, filetype="pdf")
    texte = "\n".join(page.get_text() for page in doc)
    return texte[:20000]


def extraire_audio_tmp(data: bytes, extension: str = ".ogg") -> str:
    if not ENABLE_WHISPER:
        raise RuntimeError(
            "Transcription audio désactivée sur Railway (ENABLE_WHISPER=false). "
            "Active-la via la variable d'environnement si ton plan le permet."
        )
    import whisper
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        model = whisper.load_model("tiny")
        result = model.transcribe(tmp_path)
        return result["text"][:20000]
    finally:
        os.unlink(tmp_path)


def analyser_contenu(contenu: str, source: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = PROMPT_ANALYSE.format(
        source=source,
        date=datetime.now().strftime("%Y-%m-%d"),
        contenu=contenu,
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

# ── Bloc-notes ───────────────────────────────────────────────────────────────

def ajouter_blocnote(contenu: str) -> None:
    import dropbox as dbx_module
    dbx = get_dropbox()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    nouvelle_ligne = f"- {contenu} — {now}\n"

    # Télécharger le fichier existant ou partir d'un fichier vide
    try:
        _, res = dbx.files_download(DROPBOX_BLOCNOTES)
        texte_actuel = res.content.decode("utf-8")
    except dbx_module.exceptions.ApiError:
        texte_actuel = "# Bloc-notes\n\n"

    nouveau_contenu = (texte_actuel + nouvelle_ligne).encode("utf-8")
    dbx.files_upload(nouveau_contenu, DROPBOX_BLOCNOTES, mode=dbx_module.files.WriteMode.overwrite)


# ── Travail ───────────────────────────────────────────────────────────────────

def ajouter_travail(contenu: str) -> None:
    import dropbox as dbx_module
    dbx = get_dropbox()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    nouvelle_ligne = f"- {contenu} — {now}\n"
    try:
        _, res = dbx.files_download(DROPBOX_TRAVAIL)
        texte_actuel = res.content.decode("utf-8")
    except dbx_module.exceptions.ApiError:
        texte_actuel = "# Travail\n\n"
    nouveau_contenu = (texte_actuel + nouvelle_ligne).encode("utf-8")
    dbx.files_upload(nouveau_contenu, DROPBOX_TRAVAIL, mode=dbx_module.files.WriteMode.overwrite)



def lire_fichier_dropbox(path: str) -> str:
    import dropbox as dbx_module
    dbx = get_dropbox()
    try:
        _, res = dbx.files_download(path)
        lignes = res.content.decode("utf-8").splitlines()
        return "\n".join(l for l in lignes if l.startswith("- "))
    except dbx_module.exceptions.ApiError:
        return ""


def supprimer_taches(path: str, indices: set[int]) -> int:
    """Supprime les tâches aux indices donnés (1-based). Retourne le nb supprimé."""
    import dropbox as dbx_module
    dbx = get_dropbox()
    try:
        _, res = dbx.files_download(path)
        contenu = res.content.decode("utf-8")
    except dbx_module.exceptions.ApiError:
        return 0

    toutes_lignes = contenu.splitlines(keepends=True)
    taches = [(i, l) for i, l in enumerate(toutes_lignes) if l.strip().startswith("- ")]
    a_supprimer = {taches[i - 1][0] for i in indices if 1 <= i <= len(taches)}
    nouvelles_lignes = [l for i, l in enumerate(toutes_lignes) if i not in a_supprimer]
    dbx.files_upload("".join(nouvelles_lignes).encode("utf-8"), path, mode=dbx_module.files.WriteMode.overwrite)
    return len(a_supprimer)


async def envoyer_recap_matin(context) -> None:
    if not TELEGRAM_CHAT_ID:
        log.warning("TELEGRAM_CHAT_ID non défini — recap ignoré.")
        return

    travail   = lire_fichier_dropbox(DROPBOX_TRAVAIL)
    blocnotes = lire_fichier_dropbox(DROPBOX_BLOCNOTES)

    parties = ["☀️ *Bon matin !*\n"]
    if travail:
        parties.append(f"💼 *Travail :*\n{travail}")
    if blocnotes:
        parties.append(f"📝 *Bloc-notes :*\n{blocnotes}")
    if not travail and not blocnotes:
        parties.append("Aucune tâche en attente. Belle journée !")

    await context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text="\n\n".join(parties),
        parse_mode="Markdown",
    )


# ── Handlers Telegram ─────────────────────────────────────────────────────────

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args  # ex: ["T1", "T3", "B2"]

    # Sans argument → afficher la liste numérotée
    if not args:
        travail   = lire_fichier_dropbox(DROPBOX_TRAVAIL).splitlines()
        blocnotes = lire_fichier_dropbox(DROPBOX_BLOCNOTES).splitlines()
        lignes = []
        if travail:
            lignes.append("💼 *Travail :*")
            for i, t in enumerate(travail, 1):
                lignes.append(f"  T{i} {t}")
        if blocnotes:
            lignes.append("\n📝 *Bloc-notes :*")
            for i, b in enumerate(blocnotes, 1):
                lignes.append(f"  B{i} {b}")
        if not lignes:
            await update.message.reply_text("✅ Aucune tâche en attente !")
            return
        lignes.append("\n_Réponds_ `/done T1 B2` _pour cocher des tâches_")
        await update.message.reply_text("\n".join(lignes), parse_mode="Markdown")
        return

    # Avec arguments → supprimer les tâches cochées
    t_indices = set()
    b_indices = set()
    for arg in args:
        arg = arg.upper()
        try:
            if arg.startswith("T"):
                t_indices.add(int(arg[1:]))
            elif arg.startswith("B"):
                b_indices.add(int(arg[1:]))
        except ValueError:
            pass

    if not t_indices and not b_indices:
        await update.message.reply_text("❓ Format : `/done T1 T3 B2`", parse_mode="Markdown")
        return

    msg = await update.message.reply_text("⏳ Mise à jour…")
    total = 0
    if t_indices:
        total += supprimer_taches(DROPBOX_TRAVAIL, t_indices)
    if b_indices:
        total += supprimer_taches(DROPBOX_BLOCNOTES, b_indices)
    await msg.edit_text(f"✅ {total} tâche(s) cochée(s) comme faite(s) !")


async def cmd_monid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🪪 Ton Chat ID : `{chat_id}`\n\n"
        "Utilise ce numéro pour configurer le bookmarklet navigateur.",
        parse_mode="Markdown",
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🧠 *Second Cerveau Cloud* — je capture tout pour toi !\n\n"
        "Envoie-moi :\n"
        "• Une URL → j'extrais l'article\n"
        "• Un texte → je crée une note\n"
        "• Une photo → j'analyse avec Gemini Vision\n"
        "• Un PDF → j'extrais le contenu\n"
        f"• Un vocal → {'transcription Whisper' if ENABLE_WHISPER else 'non disponible (plan cloud)'}\n\n"
        "Tout est sauvegardé dans ton Dropbox 📦\n"
        "Commandes : /help /dernieres",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📋 *Messages acceptés :*\n\n"
        "🔗 URL → extraction web\n"
        "📝 Texte → note directe\n"
        "📷 Photo → Gemini Vision\n"
        "📄 Document PDF → extraction texte\n"
        f"🎤 Vocal → {'Whisper local' if ENABLE_WHISPER else '❌ désactivé (CPU Railway)'}\n\n"
        "*/dernieres* → 5 dernières fiches Dropbox",
        parse_mode="Markdown",
    )


async def cmd_dernieres(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Récupération depuis Dropbox…")
    try:
        fiches = lister_dernieres_fiches(5)
        if not fiches:
            await msg.edit_text("Aucune fiche dans Dropbox pour l'instant.")
            return
        lignes = ["📚 *5 dernières fiches :*\n"]
        for f in fiches:
            date_str = f["modified"].strftime("%d/%m %H:%M")
            lignes.append(f"• `{f['name']}` _{date_str}_")
        await msg.edit_text("\n".join(lignes), parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Erreur Dropbox : {e}")


async def traiter_texte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texte = (update.message.text or "").strip()

    premier_mot = texte.split()[0].lower() if texte else ""

    # Détection travail
    if premier_mot in TRIGGERS_TRAVAIL:
        contenu_note = texte[len(premier_mot):].strip()
        if not contenu_note:
            await update.message.reply_text("💼 Écris quelque chose après `travail` !")
            return
        msg = await update.message.reply_text("💼 Ajout aux tâches travail…")
        try:
            ajouter_travail(contenu_note)
            await msg.edit_text(f"✅ Tâche ajoutée :\n`- {contenu_note}`", parse_mode="Markdown")
        except Exception as e:
            await msg.edit_text(f"❌ Erreur travail : {e}")
        return

    # Détection bloc-notes : "blocnote ...", "bloc-notes ..."
    if premier_mot in TRIGGERS_BLOCNOTES:
        contenu_note = texte[len(premier_mot):].strip()
        if not contenu_note:
            await update.message.reply_text("📝 Écris quelque chose après `blocnote` !")
            return
        msg = await update.message.reply_text("📝 Ajout au bloc-notes…")
        try:
            ajouter_blocnote(contenu_note)
            await msg.edit_text(f"✅ Ajouté au bloc-notes :\n`- {contenu_note}`", parse_mode="Markdown")
        except Exception as e:
            await msg.edit_text(f"❌ Erreur bloc-notes : {e}")
        return

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
        titre = extraire_champ(fiche_md, "TITRE") or extraire_champ(fiche_md, "IDEE_PRINCIPALE")[:80]
        await msg.edit_text(
            f"✅ *Capturé !*\n\n*{titre}*\n\n`{path.split('/')[-1]}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        log.exception("Erreur traitement texte")
        await msg.edit_text(f"❌ {e}")


async def traiter_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Analyse de la photo…")
    try:
        photo = update.message.photo[-1]
        fichier = await photo.get_file()
        buf = io.BytesIO()
        await fichier.download_to_memory(buf)
        data = buf.getvalue()
        nom = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

        contenu = extraire_image_bytes(data)
        fiche_md = analyser_contenu(contenu, f"telegram-photo:{nom}")
        path = uploader_fiche(fiche_md)
        uploader_raw(data, nom)
        titre = extraire_champ(fiche_md, "TITRE") or "Photo analysée"
        await msg.edit_text(
            f"✅ *Capturé !*\n\n*{titre}*\n\n`{path.split('/')[-1]}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        log.exception("Erreur traitement photo")
        await msg.edit_text(f"❌ {e}")


async def traiter_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Extraction du document…")
    try:
        doc = update.message.document
        ext = os.path.splitext(doc.file_name)[1].lower()

        if ext not in {".pdf", ".txt", ".md"}:
            await msg.edit_text("❌ Format non supporté. Envoie un PDF ou un fichier texte.")
            return

        fichier = await doc.get_file()
        buf = io.BytesIO()
        await fichier.download_to_memory(buf)
        data = buf.getvalue()

        if ext == ".pdf":
            contenu = extraire_pdf_bytes(data)
        else:
            contenu = data.decode("utf-8", errors="ignore")[:20000]

        fiche_md = analyser_contenu(contenu, f"telegram-doc:{doc.file_name}")
        path = uploader_fiche(fiche_md)
        if ext == ".pdf":
            uploader_raw(data, doc.file_name)
        titre = extraire_champ(fiche_md, "TITRE") or "Document analysé"
        await msg.edit_text(
            f"✅ *Capturé !*\n\n*{titre}*\n\n`{path.split('/')[-1]}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        log.exception("Erreur traitement document")
        await msg.edit_text(f"❌ {e}")


async def traiter_vocal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Transcription audio…")
    try:
        vocal = update.message.voice
        fichier = await vocal.get_file()
        buf = io.BytesIO()
        await fichier.download_to_memory(buf)

        transcription = extraire_audio_tmp(buf.getvalue(), ".ogg").strip()
        premier_mot = transcription.split()[0].lower() if transcription else ""

        # Routage selon le premier mot prononcé
        if premier_mot in TRIGGERS_TRAVAIL:
            contenu_note = transcription[len(premier_mot):].strip()
            ajouter_travail(contenu_note)
            await msg.edit_text(f"✅ *Tâche travail ajoutée :*\n`- {contenu_note}`", parse_mode="Markdown")

        elif premier_mot in TRIGGERS_BLOCNOTES:
            contenu_note = transcription[len(premier_mot):].strip()
            ajouter_blocnote(contenu_note)
            await msg.edit_text(f"✅ *Bloc-notes ajouté :*\n`- {contenu_note}`", parse_mode="Markdown")

        else:
            # Pas de préambule → fiche complète
            fiche_md = analyser_contenu(transcription, "telegram-vocal")
            path = uploader_fiche(fiche_md)
            titre = extraire_champ(fiche_md, "TITRE") or "Message vocal"
            await msg.edit_text(
                f"✅ *Capturé !*\n\n*{titre}*\n\n`{path.split('/')[-1]}`",
                parse_mode="Markdown",
            )

    except Exception as e:
        log.exception("Erreur traitement vocal")
        await msg.edit_text(f"❌ {e}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TELEGRAM_TOKEN:
        sys.exit("TELEGRAM_BOT_TOKEN manquant.")
    if not OPENAI_API_KEY:
        sys.exit("OPENAI_API_KEY manquante.")
    if not (DROPBOX_TOKEN or (DROPBOX_APP_KEY and DROPBOX_APP_SECRET and DROPBOX_REFRESH)):
        sys.exit("Token Dropbox manquant (DROPBOX_ACCESS_TOKEN ou APP_KEY+APP_SECRET+REFRESH_TOKEN).")

    log.info("🤖 Bot Cloud démarré — Dropbox : %s", DROPBOX_FICHES)

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Job quotidien 8h (heure de Paris)
    if TELEGRAM_CHAT_ID and app.job_queue:
        import datetime as dt
        from zoneinfo import ZoneInfo
        paris = ZoneInfo("Europe/Paris")
        for heure in [8, 12, 18, 22]:
            app.job_queue.run_daily(
                envoyer_recap_matin,
                time=dt.time(heure, 0, 0, tzinfo=paris),
            )
        log.info("⏰ Récaps programmés à 8h, 12h, 18h, 22h (Paris)")
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("monid", cmd_monid))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("dernieres", cmd_dernieres))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, traiter_texte))
    app.add_handler(MessageHandler(filters.PHOTO, traiter_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, traiter_document))
    app.add_handler(MessageHandler(filters.VOICE, traiter_vocal))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
