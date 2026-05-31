import os
import sys
import re
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Force UTF-8 sur Windows pour les emojis dans le terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Ajoute le bin ffmpeg de winget au PATH si présent et pas encore dedans
_FFMPEG_WINGET = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
for _pkg in _FFMPEG_WINGET.glob("Gyan.FFmpeg_*/*/bin"):
    if str(_pkg) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(_pkg) + os.pathsep + os.environ.get("PATH", "")
        break

BASE_DIR = Path(__file__).parent
FICHES_DIR = BASE_DIR / "fiches"
RAW_DIR = BASE_DIR / "raw"

EXTENSIONS_PDF = {".pdf"}
EXTENSIONS_IMAGE = {".png", ".jpg", ".jpeg", ".webp"}
EXTENSIONS_AUDIO = {".mp3", ".wav", ".ogg", ".m4a"}
EXTENSIONS_TEXTE = {".md", ".txt"}

PROMPT_ANALYSE = """Analyse ce contenu et crée une fiche markdown avec EXACTEMENT ce format :

---
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

Contenu à analyser :
{contenu}"""


def detecter_type(entree: str) -> str:
    if entree.startswith("http://") or entree.startswith("https://"):
        return "url"
    p = Path(entree)
    if p.exists():
        ext = p.suffix.lower()
        if ext in EXTENSIONS_PDF:
            return "pdf"
        if ext in EXTENSIONS_IMAGE:
            return "image"
        if ext in EXTENSIONS_AUDIO:
            return "audio"
        if ext in EXTENSIONS_TEXTE:
            return "texte_fichier"
    return "texte_brut"


def extraire_url(url: str) -> str:
    import requests
    print("📥 Extraction de l'URL...")
    try:
        resp = requests.get(
            f"https://r.jina.ai/{url}",
            headers={"Accept": "text/markdown"},
            timeout=15,
        )
        if resp.status_code == 200 and resp.text.strip():
            print("✅ Article extrait via Jina AI")
            return resp.text[:20000]
    except Exception:
        pass

    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        texte = trafilatura.extract(downloaded, output_format="markdown")
        if texte:
            print("✅ Article extrait via Trafilatura")
            return texte[:20000]
    except Exception:
        pass

    raise ValueError("❌ Impossible d'extraire le contenu de cette URL")


def extraire_pdf(chemin: str) -> str:
    print("⏳ Extraction du PDF en cours...")
    try:
        import fitz
        doc = fitz.open(chemin)
        texte = "\n".join(page.get_text() for page in doc)
        print("✅ PDF extrait avec succès")
        return texte[:20000]
    except ImportError:
        raise ImportError("❌ PyMuPDF non installé. Décommentez 'PyMuPDF' dans requirements.txt et relancez pip install.")
    except Exception as e:
        raise ValueError(f"❌ Impossible de lire le fichier PDF. Vérifiez qu'il n'est pas corrompu. ({e})")


def extraire_image(chemin: str) -> str:
    print("⏳ Analyse de l'image par Gemini Vision...")
    try:
        import PIL.Image
    except ImportError:
        raise ImportError("❌ Pillow non installé. Décommentez 'Pillow' dans requirements.txt et relancez pip install.")
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    image = PIL.Image.open(chemin)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            "Décris cette image en détail. Si elle contient du texte, retranscris-le intégralement. Si c'est un graphique, explique les données.",
            image,
        ],
    )
    print("✅ Image analysée")
    return response.text


def extraire_audio(chemin: str) -> str:
    print("⏳ Transcription audio en cours (Whisper local)...")
    try:
        import whisper
    except ImportError:
        raise ImportError("❌ openai-whisper non installé. Décommentez 'openai-whisper' dans requirements.txt et relancez pip install.")
    model = whisper.load_model("tiny")
    result = model.transcribe(chemin)
    print("✅ Audio transcrit")
    return result["text"][:20000]


def extraire_texte_fichier(chemin: str) -> str:
    print("📥 Lecture du fichier texte...")
    with open(chemin, "r", encoding="utf-8", errors="ignore") as f:
        contenu = f.read()
    print("✅ Fichier lu")
    return contenu[:20000]


def recuperer_contenu(entree: str, type_entree: str) -> str:
    extracteurs = {
        "url": extraire_url,
        "pdf": extraire_pdf,
        "image": extraire_image,
        "audio": extraire_audio,
        "texte_fichier": extraire_texte_fichier,
        "texte_brut": lambda x: x[:20000],
    }
    return extracteurs[type_entree](entree)


def analyser_contenu(contenu: str, source: str) -> str:
    from google import genai
    print("🧠 Analyse par l'IA en cours...")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "colle_ta_cle_ici":
        raise ValueError("❌ Clé API Gemini manquante. Renseignez GEMINI_API_KEY dans le fichier .env")
    client = genai.Client(api_key=api_key)
    prompt = PROMPT_ANALYSE.format(
        source=source,
        date=datetime.now().strftime("%Y-%m-%d"),
        contenu=contenu,
    )
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text
    except Exception as e:
        raise RuntimeError(f"❌ L'API Gemini est momentanément indisponible. Réessayez dans quelques minutes. ({e})")


def extraire_tag_principal(fiche_md: str) -> str:
    match = re.search(r"\*\*TAGS\*\*\s*:\s*(#[\w\-]+)", fiche_md)
    if match:
        return match.group(1).lstrip("#")
    return "divers"


def sauvegarder_fiche(fiche_md: str, fichier_original: str = None) -> Path:
    tag = extraire_tag_principal(fiche_md)
    horodatage = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    nom_fichier = f"{horodatage}_{tag}.md"
    chemin_fiche = FICHES_DIR / nom_fichier
    FICHES_DIR.mkdir(exist_ok=True)
    with open(chemin_fiche, "w", encoding="utf-8") as f:
        f.write(fiche_md)
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
            capture_output=True, text=True
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
        contenu = recuperer_contenu(entree, type_entree)
        fiche_md = analyser_contenu(contenu, source)
        sauvegarder_fiche(fiche_md, fichier_original)
    except (ValueError, ImportError, RuntimeError) as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
