"""
bot_cloud.py — Second Cerveau Bot Telegram (Railway)
Capture → OpenAI → Dropbox | Menus inline | Modification de fiches
"""
import io, os, re, sys, logging, tempfile, unicodedata
from datetime import datetime

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

TRIGGERS_TRAVAIL   = {"travail"}
TRIGGERS_BLOCNOTES = {"blocnote", "bloc-note", "blocnotes", "bloc-notes"}

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
        exclure = {"blocnotes.md", "travail.md"}
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
        [InlineKeyboardButton("📄 Dernières fiches", callback_data="menu:dernieres")],
        [InlineKeyboardButton("✏️ Modifier une fiche", callback_data="menu:modifier")],
    ])

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

# ── Recap scheduler ───────────────────────────────────────────────────────────

async def envoyer_recap_matin(context) -> None:
    if not TELEGRAM_CHAT_ID:
        return
    travail   = lire_fichier_dropbox(DROPBOX_TRAVAIL).splitlines()
    blocnotes = lire_fichier_dropbox(DROPBOX_BLOCNOTES).splitlines()
    parties = ["☀️ *Bon matin !*\n"]
    if travail:
        parties.append("💼 *Travail :*\n" + "\n".join(f"  T{i+1} {t}" for i, t in enumerate(travail)))
    if blocnotes:
        parties.append("📝 *Bloc-notes :*\n" + "\n".join(f"  B{i+1} {b}" for i, b in enumerate(blocnotes)))
    if not travail and not blocnotes:
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
        "Tu peux aussi préfixer par *travail* ou *blocnote*.\n\n"
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

async def cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        travail   = lire_fichier_dropbox(DROPBOX_TRAVAIL).splitlines()
        blocnotes = lire_fichier_dropbox(DROPBOX_BLOCNOTES).splitlines()
        lignes = []
        if travail:
            lignes.append("💼 *Travail :*")
            lignes += [f"  T{i+1} {t}" for i, t in enumerate(travail)]
        if blocnotes:
            lignes.append("\n📝 *Bloc-notes :*")
            lignes += [f"  B{i+1} {b}" for i, b in enumerate(blocnotes)]
        if not lignes:
            await update.message.reply_text("✅ Aucune tâche en attente !")
            return
        lignes.append("\n_Réponds_ `/done T1 B2` _pour cocher_")
        await update.message.reply_text("\n".join(lignes), parse_mode="Markdown")
        return
    t_idx, b_idx = set(), set()
    for a in args:
        a = a.upper()
        try:
            if a.startswith("T"): t_idx.add(int(a[1:]))
            elif a.startswith("B"): b_idx.add(int(a[1:]))
        except ValueError:
            pass
    if not t_idx and not b_idx:
        await update.message.reply_text("❓ Format : `/done T1 T3 B2`", parse_mode="Markdown")
        return
    msg = await update.message.reply_text("⏳ Mise à jour…")
    total = 0
    if t_idx: total += supprimer_taches(DROPBOX_TRAVAIL, t_idx)
    if b_idx: total += supprimer_taches(DROPBOX_BLOCNOTES, b_idx)
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

async def traiter_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        context.user_data["pending_edit"] = {"filename": filename, "type": "title"}
        await query.edit_message_text(
            f"✏️ Envoie le nouveau titre pour `{filename}`\n"
            "_3 mots maximum, très descriptif_",
            parse_mode="Markdown",
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

    # Scheduler 8h 12h 18h 22h
    if TELEGRAM_CHAT_ID and app.job_queue:
        import datetime as dt
        from zoneinfo import ZoneInfo
        paris = ZoneInfo("Europe/Paris")
        for h in [8, 12, 18, 22]:
            app.job_queue.run_daily(envoyer_recap_matin, time=dt.time(h, 0, tzinfo=paris))
        log.info("⏰ Récaps à 8h 12h 18h 22h (Paris)")

    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("dernieres", cmd_dernieres))
    app.add_handler(CommandHandler("travail",   cmd_travail))
    app.add_handler(CommandHandler("blocnotes", cmd_blocnotes))
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
