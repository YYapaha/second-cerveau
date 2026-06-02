# Second Cerveau

Système de capture et d'organisation de connaissances pour cerveau TDAH.

Le bot Telegram tourne **24/7 sur Railway**. Tu lui envoies n'importe quoi (URL, PDF, image, vocal, texte), il génère une fiche Markdown structurée et la dépose dans Dropbox → synchronisée automatiquement dans Obsidian.

## Architecture actuelle

```
Telegram (téléphone)
      │
      ▼
Bot Railway — bot_cloud.py
      │  extraction + analyse GPT-4o-mini
      ▼
Dropbox API ──► /second_cerveau/fiches/TYPE/titre.md
                        │ sync automatique
                        ▼
                Dropbox local PC
                        │
                        ▼
                  Obsidian 🧠
```

---

## Ce que le bot sait faire

| Fonctionnalité | Comment |
|---|---|
| Capturer une URL | Envoyer le lien dans le chat |
| Capturer un PDF | Envoyer le fichier |
| Capturer une image | Envoyer la photo |
| Capturer un vocal | Envoyer un message vocal |
| Capturer du texte | Écrire directement |
| Voir la météo à la demande | Menu `/start` → 🌤️ Voir la météo |
| Météo automatique le matin | Configurée via ⚙️ Réglages météo |
| Changer la ville / l'heure | Menu `/start` → ⚙️ Réglages météo |
| Notes rapides | `blocnote ton texte` |
| Tâches professionnelles | `travail ta tâche` |
| Planning | Menu `/start` → 📅 Mon planning |
| Modifier le titre ou les tags d'une fiche | Menu après chaque capture |

---

## Capture locale (depuis le PC)

```powershell
# Capturer une URL
python -X utf8 capture.py "https://..."

# Capturer un texte brut
python -X utf8 capture.py "mon idée ou note rapide"

# Capturer un fichier
python -X utf8 capture.py --file document.pdf

# Capturer depuis le presse-papier
python -X utf8 capture.py --clipboard

# Rechercher dans ses fiches
python -X utf8 chercher.py "mot-clé"

# Réorganiser / renommer les fiches existantes
python -X utf8 reorganiser.py
```

---

## Format des fiches

Chaque fiche est rangée dans `fiches/TYPE/tag_titre.md` et contient :

```markdown
# Titre en 5 à 7 mots

[source]

## Résumé rapide
…

## Analyse complète
…

---
**POURQUOI_GARDER** : …
**IDEE_PRINCIPALE** : …
**POINTS_CLES** :
- …
**QUAND_RESSORTIR** : "Quand je ferai X, penser à Y"
**TYPE** : Note | Tutoriel | Outil | Réflexion
**TAGS** : #tag1 #tag2 #tag3
**DATE** : JJ/MM/AAAA HH:MM

---
**CONTENU_BRUT** :    ← texte intégral extrait (URL, PDF, texte)
…
```

---

## Navigation avec Obsidian

1. Ouvrir Obsidian → **"Ouvrir un autre coffre"** → **"Ouvrir un dossier comme coffre"**
2. Sélectionner le dossier Dropbox synchronisé : `Dropbox\second_cerveau\fiches\`
3. Recherche instantanée : `Ctrl+Shift+F`

### Requêtes Dataview utiles

```dataview
TABLE date, type, tags
FROM ""
SORT date DESC
```

```dataview
TABLE quand_ressortir
FROM ""
WHERE quand_ressortir != null
SORT date DESC
```

---

## Structure des dossiers

```
second_cerveau/
├── fiches/              # Fiches Markdown → ouvrir dans Obsidian
│   ├── Note/
│   ├── Tutoriel/
│   ├── Outil/
│   ├── Réflexion/
│   └── Divers/
├── raw/                 # Fichiers originaux (PDF, images, audio)
├── inbox/               # Dossier watché : déposer = capturer automatiquement
├── bot_cloud.py         # Bot Telegram Railway (production)
├── capture.py           # Script de capture local (PC)
├── watchdog_capture.py  # Surveillance du dossier inbox/
├── chercher.py          # Recherche en ligne de commande
├── reorganiser.py       # Renommage / réorganisation des fiches
└── .env                 # Clés API locales (ne jamais committer)
```

---

## En cas de problème

| Erreur | Solution |
|---|---|
| `OPENAI_API_KEY manquante` | Vérifier le fichier `.env` local ou les variables Railway |
| `[WinError 2]` lors d'un audio | ffmpeg non installé — `winget install Gyan.FFmpeg` |
| Emojis cassés sur Windows | Lancer avec `python -X utf8` |
| Météo indisponible | Vérifier les logs Railway (onglet Deployments) |
| Ville introuvable | Préciser le pays : `Lyon, FR` ou `Genève, CH` |
| Bot muet | Vérifier que Railway affiche "Active" dans le dashboard |
