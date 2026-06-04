import os
import sys
import re
import shutil
import argparse
from pathlib import Path

# Force UTF-8 sur Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Ajoute ffmpeg de winget au PATH si présent
_FFMPEG_WINGET = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
for _pkg in _FFMPEG_WINGET.glob("Gyan.FFmpeg_*/*/bin"):
    if str(_pkg) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(_pkg) + os.pathsep + os.environ.get("PATH", "")
        break

from core import (
    formater_source, extraire_champ, slugifier, generer_nom_fichier,
    nettoyer_contenu, extraire_url, analyser_contenu, construire_fiche_complete,
    LIMITE_EXTRACTION, LIMITE_CONTENU_BRUT,
)

BASE_DIR   = Path(__file__).parent
FICHES_DIR = Path(os.environ["FICHES_DIR"]) if os.environ.get("FICHES_DIR") else BASE_DIR / "fiches"
RAW_DIR    = Path(os.environ["RAW_DIR"])    if os.environ.get("RAW_DIR")    else BASE_DIR / "raw"

EXTENSIONS_PDF    = {".pdf"}
EXTENSIONS_IMAGE  = {".png", ".jpg", ".jpeg", ".webp"}
EXTENSIONS_AUDIO  = {".mp3", ".wav", ".ogg", ".m4a"}
EXTENSIONS_TEXTE  = {".md", ".txt"}

# Types pour lesquels on stocke le contenu brut intégral dans la fiche
_TYPES_AVEC_CONTENU_BRUT = {"url", "pdf", "texte_fichier", "texte_brut"}

TYPES_MAP = {
    "recherche": "Note", "code": "Tutoriel", "transcription": "Note",
    "image": "Note", "divers": "Note", "reflexion": "Réflexion",
    "réflexion": "Réflexion", "outil": "Outil", "tutoriel": "Tutoriel", "note": "Note",
}

def normaliser_type(type_brut: str) -> str:
    type_brut = re.sub(r"[\[\]/|]", "", type_brut).strip()
    types_valides = {"Note", "Tutoriel", "Outil", "Réflexion"}
    for t in types_valides:
        if type_brut.lower() == t.lower():
            return t
    return TYPES_MAP.get(type_brut.lower(), "Note")


def detecter_type(entree: str) -> str:
    if entree.startswith("http://") or entree.startswith("https://"):
        return "url"
    p = Path(entree)
    if p.exists():
        ext = p.suffix.lower()
        if ext in EXTENSIONS_PDF:    return "pdf"
        if ext in EXTENSIONS_IMAGE:  return "image"
        if ext in EXTENSIONS_AUDIO:  return "audio"
        if ext in EXTENSIONS_TEXTE:  return "texte_fichier"
    return "texte_brut"


def extraire_pdf(chemin: str) -> str:
    print("⏳ Extraction du PDF en cours...")
    try:
        import fitz
        doc = fitz.open(chemin)
        texte = "\n".join(page.get_text() for page in doc)
        print("✅ PDF extrait")
        return texte[:LIMITE_EXTRACTION]
    except ImportError:
        raise ImportError("❌ PyMuPDF non installé. Décommentez 'PyMuPDF' dans requirements.txt.")
    except Exception as e:
        raise ValueError(f"❌ Impossible de lire le PDF. ({e})")


def extraire_image(chemin: str) -> str:
    import base64
    from openai import OpenAI
    print("⏳ Analyse de l'image par GPT-4o Vision...")
    ext = Path(chemin).suffix.lower().lstrip(".")
    if ext == "jpg":
        ext = "jpeg"
    with open(chemin, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Décris cette image en détail. Si elle contient du texte, retranscris-le intégralement. Si c'est un graphique, explique les données."},
            {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}},
        ]}],
    )
    print("✅ Image analysée")
    return response.choices[0].message.content


def extraire_audio(chemin: str) -> str:
    print("⏳ Transcription audio (Groq Whisper API)...")
    from groq import Groq
    from pathlib import Path as _Path
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("❌ GROQ_API_KEY manquante dans le fichier .env")
    client = Groq(api_key=api_key)
    with open(chemin, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(_Path(chemin).name, f),
        )
    print("✅ Audio transcrit")
    return result.text[:LIMITE_EXTRACTION]


def extraire_texte_fichier(chemin: str) -> str:
    print("📥 Lecture du fichier texte...")
    with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
        contenu = f.read()
    print("✅ Fichier lu")
    return contenu[:LIMITE_EXTRACTION]


def recuperer_contenu(entree: str, type_entree: str) -> str:
    extracteurs = {
        "url":          lambda x: (print("📥 Extraction de l'URL...") or None) or extraire_url(x),
        "pdf":          extraire_pdf,
        "image":        extraire_image,
        "audio":        extraire_audio,
        "texte_fichier": extraire_texte_fichier,
        "texte_brut":   lambda x: x[:LIMITE_EXTRACTION],
    }
    return extracteurs[type_entree](entree)


def sauvegarder_fiche(fiche_md: str, fichier_original: str = None, contenu_brut: str = None) -> Path:
    nom_fichier = generer_nom_fichier(fiche_md)
    FICHES_DIR.mkdir(parents=True, exist_ok=True)
    chemin_fiche = FICHES_DIR / nom_fichier
    with open(chemin_fiche, "w", encoding="utf-8") as f:
        f.write(construire_fiche_complete(fiche_md, contenu_brut))
    if fichier_original:
        RAW_DIR.mkdir(exist_ok=True)
        shutil.copy2(fichier_original, RAW_DIR / Path(fichier_original).name)
    print(f"💾 Fiche sauvegardée : {chemin_fiche}")
    return chemin_fiche


def lire_presse_papier() -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-command", "Get-Clipboard"],
            capture_output=True, text=True,
        )
        return result.stdout.strip()
    except Exception:
        raise RuntimeError("❌ Impossible de lire le presse-papier.")


def main():
    parser = argparse.ArgumentParser(
        description="Second Cerveau — capture universelle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Exemples :
  python capture.py "https://exemple.com/article"
  python capture.py "Mon texte brut à analyser"
  python capture.py --file document.pdf
  python capture.py --clipboard""",
    )
    parser.add_argument("entree", nargs="?", help="URL ou texte brut à capturer")
    parser.add_argument("--file", "-f", help="Chemin vers un fichier à traiter")
    parser.add_argument("--clipboard", "-c", action="store_true", help="Lire depuis le presse-papier")
    args = parser.parse_args()

    if args.clipboard:
        entree = lire_presse_papier()
        if not entree:
            print("❌ Le presse-papier est vide.")
            sys.exit(1)
        source = "presse-papier"
        fichier_original = None
    elif args.file:
        entree = args.file
        if not Path(entree).exists():
            print(f"❌ Fichier introuvable : {entree}")
            sys.exit(1)
        source = entree
        fichier_original = entree
    elif args.entree:
        entree = args.entree
        source = entree if entree.startswith("http") else "texte-brut"
        fichier_original = None
    else:
        parser.print_help()
        sys.exit(1)

    type_entree = detecter_type(entree)

    try:
        contenu_raw    = recuperer_contenu(entree, type_entree)
        contenu_propre, injections = nettoyer_contenu(contenu_raw)
        if injections:
            print("⚠️  Tentatives d'injection détectées et supprimées.")
        print("🧠 Analyse par l'IA en cours...")
        fiche_md    = analyser_contenu(contenu_propre, source)
        contenu_brut = contenu_propre if type_entree in _TYPES_AVEC_CONTENU_BRUT else None
        sauvegarder_fiche(fiche_md, fichier_original, contenu_brut=contenu_brut)
    except (ValueError, ImportError, RuntimeError) as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
