import sys
import re
from pathlib import Path
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FICHES_DIR = Path(__file__).parent / "fiches"


def extraire_champ(contenu: str, champ: str) -> str:
    match = re.search(rf"\*\*{champ}\*\*\s*:\s*(.+?)(?=\n\*\*|\Z)", contenu, re.DOTALL)
    return match.group(1).strip() if match else ""


def scorer(contenu: str, mots: list[str]) -> int:
    contenu_lower = contenu.lower()
    return sum(contenu_lower.count(mot) for mot in mots)


def chercher(question: str, top_n: int = 5) -> list[dict]:
    mots = [m.lower() for m in re.findall(r"\w+", question) if len(m) > 2]
    if not mots:
        return []

    fiches = list(FICHES_DIR.glob("*.md"))
    if not fiches:
        return []

    resultats = []
    for fiche in fiches:
        contenu = fiche.read_text(encoding="utf-8", errors="ignore")
        score = scorer(contenu, mots)
        if score > 0:
            resultats.append({
                "fichier": fiche.name,
                "score": score,
                "idee": extraire_champ(contenu, "IDEE_PRINCIPALE"),
                "tags": extraire_champ(contenu, "TAGS"),
                "quand": extraire_champ(contenu, "QUAND_RESSORTIR"),
                "resume": extraire_champ(contenu, "RESUME_30_SEC"),
            })

    resultats.sort(key=lambda x: x["score"], reverse=True)
    top = resultats[:top_n]

    # Convertir le score en pourcentage relatif au meilleur
    if top:
        max_score = top[0]["score"]
        for r in top:
            r["pertinence"] = round(r["score"] / max_score * 100)

    return top


def afficher(question: str, resultats: list[dict]) -> None:
    print(f'\n## Résultats pour : "{question}"\n')
    if not resultats:
        print("Aucune fiche trouvée pour cette recherche.")
        return

    for i, r in enumerate(resultats, 1):
        print(f"### Fiche {i} : {r['fichier']}")
        print(f"**Pertinence** : {r['pertinence']}%")
        if r["tags"]:
            print(f"**Tags** : {r['tags']}")
        if r["idee"]:
            print(f"**Idée principale** : {r['idee'][:200]}")
        if r["quand"]:
            print(f"**Quand ressortir** : {r['quand'][:150]}")
        print("---\n")


def main():
    if len(sys.argv) < 2:
        print("Usage : python chercher.py \"ma question\"")
        print("Exemple : python chercher.py \"comment gérer le state dans React\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    resultats = chercher(question)
    afficher(question, resultats)


if __name__ == "__main__":
    main()
