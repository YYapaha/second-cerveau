import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from core import chercher_fiches, extraire_champ

FICHES_DIR = Path(__file__).parent / "fiches"


def chercher(question: str, top_n: int = 5) -> list[dict]:
    fiches = list(FICHES_DIR.rglob("*.md"))
    if not fiches:
        return []
    fiches_textes = [
        (f.name, f.read_text(encoding="utf-8", errors="ignore"))
        for f in fiches
    ]
    return chercher_fiches(question, fiches_textes, top_n)


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
    question  = " ".join(sys.argv[1:])
    resultats = chercher(question)
    afficher(question, resultats)


if __name__ == "__main__":
    main()
