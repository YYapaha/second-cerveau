# Second Cerveau — Guide de setup complet

> Système de capture automatique de connaissances. Tu tombes sur un truc intéressant → tu l'envoies au bot Telegram (ou tu lances `capture.py`) → une fiche Markdown structurée est créée automatiquement dans Dropbox → visible dans Obsidian.

---

## Ce que tu vas avoir à la fin

- Un **bot Telegram 24/7 sur Railway** qui capture tout depuis ton téléphone
- Un script local `capture.py` pour capturer depuis le PC
- Un dossier `inbox/` magique : déposer un fichier = le capturer automatiquement
- Tes fiches organisées dans Obsidian, synchronisées via Dropbox
- Météo automatique chaque matin dans Telegram

**Coût estimé :** Railway gratuit (jusqu'à 500h/mois), OpenAI ~0,01€ par fiche.

---

## Prérequis

| Outil | Version | Lien |
|---|---|---|
| Python | 3.9+ | https://www.python.org/downloads/ |
| Git | n'importe | https://git-scm.com |
| Obsidian | n'importe | https://obsidian.md |
| ffmpeg | n'importe | `winget install Gyan.FFmpeg` (Windows) |

---

## Installation locale (capture depuis le PC)

### 1. Cloner le repo

```bash
git clone https://github.com/YYapaha/second-cerveau.git
cd second-cerveau
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

> Sur Windows : `python -m pip install -r requirements.txt`

### 3. Configurer les clés API

Crée un fichier `.env` à la racine :

```env
OPENAI_API_KEY=ta_cle_ici
TELEGRAM_BOT_TOKEN=ton_token_ici     # si tu utilises le bot local
DROPBOX_ACCESS_TOKEN=ton_token_ici   # pour la synchro Dropbox locale
```

**Obtenir une clé OpenAI :**
1. https://platform.openai.com/api-keys
2. "Create new secret key" → copier

**Obtenir un token Telegram (optionnel pour usage local) :**
1. Telegram → chercher `@BotFather` → `/newbot`
2. Copier le token fourni

### 4. Installer ffmpeg (pour la transcription audio)

**Windows :**
```powershell
winget install Gyan.FFmpeg
```
Redémarre le terminal après.

**Mac :**
```bash
brew install ffmpeg
```

**Linux :**
```bash
sudo apt install ffmpeg
```

### 5. Utiliser

```powershell
# Capturer une URL
python -X utf8 capture.py "https://..."

# Capturer un texte brut
python -X utf8 capture.py "mon idée"

# Capturer un fichier
python -X utf8 capture.py --file document.pdf

# Capturer depuis le presse-papier
python -X utf8 capture.py --clipboard

# Rechercher dans ses fiches
python -X utf8 chercher.py "mot-clé"
```

### 6. Ouvrir Obsidian sur le dossier des fiches

1. Obsidian → "Ouvrir un autre coffre" → "Ouvrir un dossier comme coffre"
2. Sélectionner `Dropbox\second_cerveau\fiches\` (ou le dossier `fiches/` local)

---

## Déploiement du bot sur Railway (production)

> Le bot Railway tourne déjà en production. Cette section est utile si tu dois le reconfigurer ou le redéployer from scratch.

Voir [README_DEPLOY.md](README_DEPLOY.md) pour le guide complet.

Variables d'environnement à configurer dans Railway :

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token BotFather |
| `TELEGRAM_CHAT_ID` | Ton chat ID Telegram |
| `OPENAI_API_KEY` | Clé API OpenAI |
| `DROPBOX_APP_KEY` | App key Dropbox |
| `DROPBOX_APP_SECRET` | App secret Dropbox |
| `DROPBOX_REFRESH_TOKEN` | Refresh token OAuth Dropbox |

---

## Format des fiches générées

Chaque fiche est un `.md` rangé dans `fiches/TYPE/TAG_titre.md` :

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
- Point 1
- Point 2
**QUAND_RESSORTIR** : "Quand je ferai X…"
**TYPE** : Note | Tutoriel | Outil | Réflexion
**TAGS** : #tag1 #tag2 #tag3
**DATE** : JJ/MM/AAAA HH:MM

---
**CONTENU_BRUT** :
(texte intégral extrait de la page, du PDF ou du fichier — jusqu'à 30 000 caractères)
```

---

## Plugins Obsidian recommandés

| Plugin | Usage |
|---|---|
| **Dataview** | Tableau de bord dynamique |
| **QuickAdd** | Créer une note en 2 touches |
| **Templater** | Templates pour notes manuelles |

```dataview
TABLE date, type, tags
FROM ""
SORT date DESC
```

---

## Dépannage

| Erreur | Solution |
|---|---|
| `OPENAI_API_KEY manquante` | Vérifier `.env` |
| `[WinError 2]` audio | ffmpeg non dans le PATH |
| Emojis cassés Windows | `python -X utf8 capture.py ...` |
| Bot muet | Vérifier Railway dashboard → "Active" |
| Météo indisponible | Logs Railway → onglet Deployments |
| Ville introuvable | Format `Lyon, FR` ou `Genève, CH` |
