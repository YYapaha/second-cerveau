"""
Script one-shot : ajoute un TITRE OpenAI aux fiches qui n'en ont pas, puis renomme.
"""
import os
import sys
import re
import time
import unicodedata
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(Path(__file__).parent / ".env")

from openai import OpenAI

BASE_DIR = Path(__file__).parent
FICHES_DIR = BASE_DIR / "fiches"

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


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


def generer_titre(idee: str, resume: str) -> str:
    contexte = idee or resume or "Note sans contenu"
    prompt = (
        "Génère un titre de 5 à 7 mots maximum qui résume précisément ce contenu. "
        "Pas de ponctuation, pas de guillemets, pas de majuscules inutiles. "
        "Réponds UNIQUEMENT avec le titre, rien d'autre.\n\n"
        f"Contenu : {contexte[:500]}"
    )
    for tentative in range(4):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip().strip('"').strip("'")
        except Exception as e:
            msg = str(e)
            attente = 15 * (tentative + 1)
            if "rate_limit" in msg.lower() and tentative < 3:
                print(f"     ⏳ Rate limit — attente {attente}s avant retry...")
                time.sleep(attente)
            else:
                raise


def chemin_sans_collision(dossier: Path, nom: str) -> Path:
    cible = dossier / nom
    if not cible.exists():
        return cible
    stem = Path(nom).stem
    compteur = 2
    while True:
        cible = dossier / f"{stem}_{compteur}.md"
        if not cible.exists():
            return cible
        compteur += 1


def traiter_fiches():
    fiches = [f for f in FICHES_DIR.rglob("*.md") if f.is_file()]
    sans_titre = [f for f in fiches if "**TITRE**" not in f.read_text(encoding="utf-8", errors="ignore")]

    if not sans_titre:
        print("✅ Toutes les fiches ont déjà un TITRE.")
        return

    print(f"🔍 {len(sans_titre)} fiche(s) sans TITRE trouvée(s)\n")

    for i, fiche in enumerate(sans_titre, 1):
        contenu = fiche.read_text(encoding="utf-8", errors="ignore")
        idee = extraire_champ(contenu, "IDEE_PRINCIPALE")
        resume = extraire_champ(contenu, "RESUME_30_SEC")

        try:
            titre = generer_titre(idee, resume)
        except Exception as e:
            print(f"  ❌ [{i}/{len(sans_titre)}] {fiche.name} — erreur Gemini : {e}")
            continue

        # Injecter le TITRE après le "---" d'ouverture
        if contenu.startswith("---"):
            nouveau_contenu = contenu.replace("---\n", f"---\n**TITRE** : {titre}\n", 1)
        else:
            nouveau_contenu = f"**TITRE** : {titre}\n{contenu}"

        # Renommer le fichier
        slug = slugifier(titre)
        nouveau_nom = f"{slug}.md"
        chemin_cible = chemin_sans_collision(fiche.parent, nouveau_nom)

        fiche.write_text(nouveau_contenu, encoding="utf-8")
        if chemin_cible != fiche:
            fiche.rename(chemin_cible)
            print(f"  ✅ [{i}/{len(sans_titre)}] {fiche.name}\n     → {chemin_cible.name}\n     Titre : {titre}")
        else:
            print(f"  ✅ [{i}/{len(sans_titre)}] {fiche.name} (nom inchangé)\n     Titre : {titre}")

        # Pause pour éviter le rate limit Gemini
        if i < len(sans_titre):
            time.sleep(1)

    print(f"\n✅ Terminé.")


if __name__ == "__main__":
    traiter_fiches()
