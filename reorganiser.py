import sys
import re
import shutil
import unicodedata
import logging
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
FICHES_DIR = BASE_DIR / "fiches"
LOG_FILE = BASE_DIR / "reorganisation.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


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
    type_gemini = re.sub(r"[\[\]/|]", "", type_gemini).strip()
    dossier = re.sub(r"\s+", "_", type_gemini) if type_gemini else "Divers"
    return dossier or "Divers"


def extraire_horodatage(nom_fichier: str) -> str:
    """Extrait YYYY-MM-DD_HHMMSS du nom de fichier existant, ou génère un nouveau."""
    match = re.match(r"(\d{4}-\d{2}-\d{2}_\d{6})", nom_fichier)
    return match.group(1) if match else datetime.now().strftime("%Y-%m-%d_%H%M%S")


def chemin_sans_collision(dossier: Path, nom: str) -> Path:
    """Retourne un chemin libre en ajoutant un suffixe _2, _3... si nécessaire."""
    cible = dossier / nom
    if not cible.exists():
        return cible
    stem = Path(nom).stem
    suffix = Path(nom).suffix
    compteur = 2
    while True:
        cible = dossier / f"{stem}_{compteur}{suffix}"
        if not cible.exists():
            return cible
        compteur += 1


def reorganiser():
    if not FICHES_DIR.exists():
        log.error("Dossier fiches/ introuvable : %s", FICHES_DIR)
        sys.exit(1)

    # Uniquement les .md à la racine de fiches/ (pas les sous-dossiers)
    fiches = [f for f in FICHES_DIR.iterdir() if f.is_file() and f.suffix == ".md"]

    if not fiches:
        log.info("Aucune fiche à la racine de fiches/ — rien à faire.")
        return

    log.info("=== Début réorganisation — %d fiche(s) trouvée(s) ===", len(fiches))
    deplacees = 0
    erreurs = 0

    for fiche in sorted(fiches):
        try:
            contenu = fiche.read_text(encoding="utf-8", errors="ignore")

            type_brut = extraire_champ(contenu, "TYPE")
            idee = extraire_champ(contenu, "IDEE_PRINCIPALE")
            tags_brut = extraire_champ(contenu, "TAGS")

            # Sous-dossier
            dossier_nom = type_vers_dossier(type_brut) if type_brut else "Divers"

            # Slug depuis l'idée principale (première phrase), fallback premier tag
            if idee:
                texte_slug = idee.split(".")[0]
            elif tags_brut:
                match_tag = re.search(r"#([\w\-]+)", tags_brut)
                texte_slug = match_tag.group(1) if match_tag else "note_sans_titre"
            else:
                texte_slug = "note_sans_titre"

            slug = slugifier(texte_slug)
            horodatage = extraire_horodatage(fiche.name)
            nouveau_nom = f"{horodatage}_{slug}.md"

            dossier_cible = FICHES_DIR / dossier_nom
            dossier_cible.mkdir(parents=True, exist_ok=True)

            chemin_cible = chemin_sans_collision(dossier_cible, nouveau_nom)
            shutil.move(str(fiche), chemin_cible)

            log.info("DEPLACE  %s  →  %s/%s", fiche.name, dossier_nom, chemin_cible.name)
            deplacees += 1

        except Exception as e:
            log.error("ERREUR   %s  :  %s", fiche.name, e)
            erreurs += 1

    log.info("=== Fin réorganisation — %d déplacée(s), %d erreur(s) ===", deplacees, erreurs)
    print(f"\n✅ {deplacees} fiche(s) réorganisée(s). Log : {LOG_FILE}")
    if erreurs:
        print(f"⚠️  {erreurs} erreur(s) — consulter {LOG_FILE}")


if __name__ == "__main__":
    reorganiser()
