# Second Cerveau

Système de capture et d'organisation de connaissances pour cerveau TDAH.

## Workflow quotidien (3 étapes)

1. **Je tombe sur un truc intéressant** → je le balance dans le système
2. **Le système analyse et range automatiquement**
3. **Plus tard, je cherche un mot-clé dans Obsidian** → je retrouve tout

## Commandes principales

```powershell
# Capturer une URL
python capture.py "https://..."

# Capturer un texte brut
python capture.py "mon texte..."

# Capturer un fichier
python capture.py --file document.pdf

# Capturer depuis le presse-papier
python capture.py --clipboard

# Lancer le bot Telegram (capture depuis le téléphone)
python bot_telegram.py

# Lancer le watchdog (dépôt automatique via inbox/)
python watchdog_capture.py

# Tout lancer d'un coup
start.bat
```

## Navigation avec Obsidian

1. Installer [Obsidian](https://obsidian.md) si ce n'est pas déjà fait.
2. Ouvrir Obsidian → **"Ouvrir un autre coffre"** → **"Ouvrir un dossier comme coffre"**
3. Sélectionner `C:\Users\<ton nom>\second_cerveau\fiches\`
4. La recherche instantanée (`Ctrl+Shift+F`), les tags et le graphe sont disponibles immédiatement.

### Plugins recommandés

| Plugin | Utilité |
|---|---|
| **Dataview** | Requêtes sur tes fiches comme une base de données |
| **Templater** | Templates pour créer des fiches manuelles rapidement |
| **QuickAdd** | Ajouter une note en 2 touches depuis n'importe où |
| **Graph Analysis** | Visualise les connexions entre tes fiches |

### Tableau de bord Dataview

Crée une note `Index.md` dans ton coffre avec ce contenu :

```dataview
TABLE date, type, tags, idee_principale
FROM ""
SORT date DESC
```

Pour filtrer par type :

```dataview
TABLE date, tags, pourquoi_garder
FROM ""
WHERE type = "Tutoriel"
SORT date DESC
```

Pour retrouver tes fiches "à ressortir" :

```dataview
TABLE quand_ressortir
FROM ""
WHERE quand_ressortir != null
SORT date DESC
```

## Structure des dossiers

```
second_cerveau/
├── fiches/              # Fiches markdown générées → ouvrir dans Obsidian
├── raw/                 # Fichiers originaux (PDF, images, audio)
├── inbox/               # Dossier watché : déposer = capturer automatiquement
├── capture.py           # Script de capture principal
├── bot_telegram.py      # Bot Telegram (capture depuis le téléphone)
├── watchdog_capture.py  # Surveillance du dossier inbox/
├── chercher.py          # Recherche en ligne de commande (STEP 8)
└── .env                 # Clés API (ne jamais committer)
```

## Format des fiches

Chaque fiche contient :

```
SOURCE · DATE · TAGS · TYPE
POURQUOI_GARDER · IDEE_PRINCIPALE · POINTS_CLES
QUAND_RESSORTIR · RESUME_30_SEC · RESUME_COMPLET
```

## En cas de problème

- Vérifier la clé API Gemini dans `.env`
- Vérifier Python 3.9+ : `python --version`
- Réinstaller les dépendances : `python -m pip install -r requirements.txt`
- Les logs s'affichent dans le terminal
