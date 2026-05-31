import os
import sys
import re
import logging
from pathlib import Path
from datetime import datetime

# Force UTF-8 sur Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from capture import recuperer_contenu, analyser_contenu, sauvegarder_fiche

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARNING,
)

FICHES_DIR = Path(__file__).parent / "fiches"
TMP_DIR = Path(__file__).parent / "tmp_telegram"


def extraire_idee_principale(fiche_md: str) -> str:
    match = re.search(r"\*\*IDEE_PRINCIPALE\*\*\s*:\s*(.+?)(?=\n\*\*|\Z)", fiche_md, re.DOTALL)
    if match:
        return match.group(1).strip()[:300]
    return "Fiche créée avec succès."


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🧠 *Second Cerveau* — je capture tout pour toi !\n\n"
        "Envoie-moi :\n"
        "• Une URL → j'extrais l'article\n"
        "• Un texte → je crée une note\n"
        "• Une photo → j'analyse l'image\n"
        "• Un PDF → j'extrais le contenu\n"
        "• Un message vocal → je transcris\n\n"
        "Commandes : /help /dernieres",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📋 *Types de messages acceptés :*\n\n"
        "🔗 URL → extraction web\n"
        "📝 Texte → note directe\n"
        "📷 Photo → analyse Gemini Vision\n"
        "📄 Document PDF → extraction texte\n"
        "🎤 Vocal → transcription Whisper\n\n"
        "*/dernieres* → voir les 5 dernières fiches",
        parse_mode="Markdown",
    )


async def cmd_dernieres(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    fiches = sorted(FICHES_DIR.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
    if not fiches:
        await update.message.reply_text("Aucune fiche pour l'instant.")
        return
    lignes = ["📚 *5 dernières fiches :*\n"]
    for fiche in fiches:
        contenu = fiche.read_text(encoding="utf-8", errors="ignore")
        idee = extraire_idee_principale(contenu)
        lignes.append(f"• `{fiche.name}`\n  {idee[:150]}…\n")
    await update.message.reply_text("\n".join(lignes), parse_mode="Markdown")


async def traiter_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Traitement en cours…")
    try:
        texte = update.message.text or update.message.caption or ""
        entree = texte.strip()
        source = entree if entree.startswith("http") else "telegram-texte"
        type_entree = "url" if entree.startswith("http://") or entree.startswith("https://") else "texte_brut"
        fichier_original = None

        contenu = recuperer_contenu(entree, type_entree)
        fiche_md = analyser_contenu(contenu, source)
        sauvegarder_fiche(fiche_md, fichier_original)
        idee = extraire_idee_principale(fiche_md)
        await msg.edit_text(f"✅ *Capturé !*\n\n{idee}", parse_mode="Markdown")

    except Exception as e:
        await msg.edit_text(f"❌ Erreur : {e}")


async def traiter_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Analyse de la photo…")
    TMP_DIR.mkdir(exist_ok=True)
    chemin_tmp = TMP_DIR / f"photo_{datetime.now().strftime('%H%M%S')}.jpg"
    try:
        photo = update.message.photo[-1]
        fichier = await photo.get_file()
        await fichier.download_to_drive(chemin_tmp)

        contenu = recuperer_contenu(str(chemin_tmp), "image")
        fiche_md = analyser_contenu(contenu, f"telegram-photo:{chemin_tmp.name}")
        sauvegarder_fiche(fiche_md, str(chemin_tmp))
        idee = extraire_idee_principale(fiche_md)
        await msg.edit_text(f"✅ *Capturé !*\n\n{idee}", parse_mode="Markdown")

    except Exception as e:
        await msg.edit_text(f"❌ Erreur : {e}")
    finally:
        if chemin_tmp.exists():
            chemin_tmp.unlink()


async def traiter_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Extraction du document…")
    TMP_DIR.mkdir(exist_ok=True)
    doc = update.message.document
    chemin_tmp = TMP_DIR / doc.file_name
    try:
        fichier = await doc.get_file()
        await fichier.download_to_drive(chemin_tmp)

        ext = chemin_tmp.suffix.lower()
        if ext == ".pdf":
            type_entree = "pdf"
        elif ext in {".md", ".txt"}:
            type_entree = "texte_fichier"
        else:
            await msg.edit_text("❌ Format non supporté. Envoie un PDF ou un fichier texte.")
            return

        contenu = recuperer_contenu(str(chemin_tmp), type_entree)
        fiche_md = analyser_contenu(contenu, f"telegram-doc:{doc.file_name}")
        sauvegarder_fiche(fiche_md, str(chemin_tmp))
        idee = extraire_idee_principale(fiche_md)
        await msg.edit_text(f"✅ *Capturé !*\n\n{idee}", parse_mode="Markdown")

    except Exception as e:
        await msg.edit_text(f"❌ Erreur : {e}")
    finally:
        if chemin_tmp.exists():
            chemin_tmp.unlink()


async def traiter_vocal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Transcription audio en cours…")
    TMP_DIR.mkdir(exist_ok=True)
    chemin_tmp = TMP_DIR / f"vocal_{datetime.now().strftime('%H%M%S')}.ogg"
    try:
        vocal = update.message.voice
        fichier = await vocal.get_file()
        await fichier.download_to_drive(chemin_tmp)

        contenu = recuperer_contenu(str(chemin_tmp), "audio")
        fiche_md = analyser_contenu(contenu, "telegram-vocal")
        sauvegarder_fiche(fiche_md)
        idee = extraire_idee_principale(fiche_md)
        await msg.edit_text(f"✅ *Capturé !*\n\n{idee}", parse_mode="Markdown")

    except Exception as e:
        await msg.edit_text(f"❌ Erreur : {e}")
    finally:
        if chemin_tmp.exists():
            chemin_tmp.unlink()


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token or token == "optionnel_colle_ton_token_ici":
        print("❌ Token Telegram manquant. Renseignez TELEGRAM_BOT_TOKEN dans le fichier .env")
        sys.exit(1)

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("dernieres", cmd_dernieres))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, traiter_message))
    app.add_handler(MessageHandler(filters.PHOTO, traiter_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, traiter_document))
    app.add_handler(MessageHandler(filters.VOICE, traiter_vocal))

    print("🤖 Bot Telegram démarré. Ctrl+C pour arrêter.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
