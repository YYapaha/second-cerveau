import sys
import re
import shutil
import unicodedata
import logging
from pathlib import Path

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


def chemin_sans_collision(dossier: Path, nom: str) -> Path:
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


def nouveau_nom_depuis_contenu(contenu: str) -> str:
    titre = extraire_champ(contenu, "TITRE")
    if titre:
        return f"{slugifier(titre)}.md"
    idee = extraire_champ(contenu, "IDEE_PRINCIPALE")
    if idee:
        return f"{slugifier(idee.split('.')[0])}.md"
    tags_brut = extraire_champ(contenu, "TAGS")
    match_tag = re.search(r"#([\w\-]+)", tags_brut) if tags_brut else None
    texte_slug = match_tag.group(1) if match_tag else "note_sans_titre"
    return f"{slugifier(texte_slug)}.md"


def reorganiser():
    if not FICHES_DIR.exists():
        log.error("Dossier fiches/ introuvable : %s", FICHES_DIR)
        sys.exit(1)

    # Fiches à la racine → déplacer + renommer
    fiches_racine = [f for f in FICHES_DIR.iterdir() if f.is_file() and f.suffix == ".md"]

    # Fiches déjà dans des sous-dossiers → renommer uniquement
    fiches_sous_dossiers = [
        f for f in FICHES_DIR.rglob("*.md")
        if f.parent != FICHES_DIR and f.is_file()
    ]

    total = len(fiches_racine) + len(fiches_sous_dossiers)
    if total == 0:
        log.info("Aucune fiche trouvée — rien à faire.")
        return

    log.info("=== Début réorganisation — %d fiche(s) ===", total)
    traitees = 0
    erreurs = 0

    # --- Fiches racine : déplacer dans sous-dossier + renommer ---
    for fiche in sorted(fiches_racine):
        try:
            contenu = fiche.read_text(encoding="utf-8", errors="ignore")
            type_brut = extraire_champ(contenu, "TYPE")
            dossier_nom = type_vers_dossier(type_brut) if type_brut else "Divers"
            nouveau_nom = nouveau_nom_depuis_contenu(contenu)
            dossier_cible = FICHES_DIR / dossier_nom
            dossier_cible.mkdir(parents=True, exist_ok=True)
            chemin_cible = chemin_sans_collision(dossier_cible, nouveau_nom)
            shutil.move(str(fiche), chemin_cible)
            log.info("DEPLACE+RENOMME  %s  →  %s/%s", fiche.name, dossier_nom, chemin_cible.name)
            traitees += 1
        except Exception as e:
            log.error("ERREUR  %s  :  %s", fiche.name, e)
            erreurs += 1

    # --- Fiches dans sous-dossiers : renommer uniquement ---
    for fiche in sorted(fiches_sous_dossiers):
        try:
            contenu = fiche.read_text(encoding="utf-8", errors="ignore")
            nouveau_nom = nouveau_nom_depuis_contenu(contenu)
            chemin_cible = chemin_sans_collision(fiche.parent, nouveau_nom)
            if chemin_cible == fiche:
                log.info("INCHANGE  %s", fiche.name)
                continue
            fiche.rename(chemin_cible)
            log.info("RENOMME  %s  →  %s", fiche.name, chemin_cible.name)
            traitees += 1
        except Exception as e:
            log.error("ERREUR  %s  :  %s", fiche.name, e)
            erreurs += 1

    log.info("=== Fin — %d traitée(s), %d erreur(s) ===", traitees, erreurs)
    print(f"\n✅ {traitees} fiche(s) traitée(s). Log : {LOG_FILE}")
    if erreurs:
        print(f"⚠️  {erreurs} erreur(s) — consulter {LOG_FILE}")


if __name__ == "__main__":
    reorganiser()
