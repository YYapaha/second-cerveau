# Second Cerveau — Guide de setup complet

> Système de capture automatique de connaissances. Tu tombes sur un truc intéressant → tu l'envoies → une fiche Markdown structurée est créée automatiquement.

---

## Ce que tu vas avoir à la fin

- Un script qui capture n'importe quoi (URL, texte, PDF, image, vocal)
- Un bot Telegram pour capturer depuis ton téléphone
- Un dossier `inbox/` magique : déposer un fichier = le capturer automatiquement
- Tes fiches organisées par type dans Obsidian
- **Coût : 0€** (Gemini API gratuit, tout le reste est local ou open source)

---

## Prérequis

| Outil | Version | Lien |
|---|---|---|
| Python | 3.9+ | https://www.python.org/downloads/ |
| Git | n'importe | https://git-scm.com |
| Obsidian | n'importe | https://obsidian.md |
| ffmpeg | n'importe | via `winget install Gyan.FFmpeg` (Windows) |

---

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/YYapaha/second-cerveau.git
cd second-cerveau
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

> Sur Windows, utilise `python -m pip` si `pip` n'est pas reconnu.

### 3. Configurer les clés API

Copie le template et remplis-le :

```bash
cp .env.example .env   # ou ouvre .env directement
```

Contenu de `.env` :

```
GEMINI_API_KEY=ta_cle_ici
TELEGRAM_BOT_TOKEN=ton_token_ici   # optionnel
```

**Obtenir une clé Gemini gratuite :**
1. Aller sur https://aistudio.google.com/apikey
2. Se connecter avec un compte Google
3. Cliquer "Create API key" → copier la clé

**Obtenir un token Telegram (optionnel) :**
1. Ouvrir Telegram → chercher `@BotFather`
2. Envoyer `/newbot` → suivre les instructions
3. Copier le token fourni

### 4. Installer ffmpeg (pour la transcription audio)

**Windows :**
```powershell
winget install Gyan.FFmpeg
```
Redémarre le terminal après l'installation.

**Mac :**
```bash
brew install ffmpeg
```

**Linux :**
```bash
sudo apt install ffmpeg
```

### 5. Ouvrir Obsidian sur le dossier des fiches

1. Ouvrir Obsidian
2. "Ouvrir un autre coffre" → "Ouvrir un dossier comme coffre"
3. Sélectionner le dossier `fiches/` dans ce repo

---

## Utilisation quotidienne

```bash
# Capturer une URL
python -X utf8 capture.py "https://..."

# Capturer un texte brut
python -X utf8 capture.py "mon idée ou note rapide"

# Capturer un fichier
python -X utf8 capture.py --file document.pdf

# Capturer depuis le presse-papier
python -X utf8 capture.py --clipboard

# Lancer le bot Telegram + watchdog d'un coup (Windows)
start.bat

# Rechercher dans ses fiches
python -X utf8 chercher.py "ma question"

# Réorganiser / renommer les fiches existantes
python -X utf8 reorganiser.py
```

---

## Structure des fiches générées

Chaque fiche est un `.md` rangé dans `fiches/TYPE/slug_titre.md` :

```
fiches/
├── Tutoriel/
├── Note/
├── Outil/
├── Recherche/
├── Code/
├── Réflexion/
├── Transcription/
├── Image/
└── Divers/
```

Chaque fiche contient :

```markdown
**SOURCE** · **DATE** · **TAGS** · **TYPE**
**POURQUOI_GARDER** · **IDEE_PRINCIPALE** · **POINTS_CLES**
**QUAND_RESSORTIR** · **RESUME_30_SEC** · **RESUME_COMPLET**
```

---

## Plugins Obsidian recommandés

| Plugin | Usage |
|---|---|
| **Dataview** | Tableau de bord dynamique sur tes fiches |
| **QuickAdd** | Créer une note en 2 touches |
| **Templater** | Templates pour notes manuelles |

**Exemple de requête Dataview** — colle ça dans une note `Index.md` :

```dataview
TABLE date, type, tags
FROM ""
SORT date DESC
```

---

## Étape future : héberger le bot Telegram sur Railway

> **Problème actuel :** le bot Telegram (`bot_telegram.py`) doit tourner en permanence sur ton PC pour recevoir les messages. Si le PC s'éteint, le bot ne répond plus.

### Solution : déployer sur Railway (gratuit jusqu'à ~500h/mois)

**Railway** est une plateforme cloud simple — tu pousses ton code, il tourne 24/7 sans que ton PC soit allumé.

#### Étapes prévues

1. **Créer un compte** sur https://railway.app (gratuit, connexion GitHub)

2. **Créer un `Procfile`** à la racine du repo :
   ```
   worker: python -X utf8 bot_telegram.py
   ```

3. **Configurer les variables d'environnement** dans Railway (onglet "Variables") :
   - `GEMINI_API_KEY` = ta clé
   - `TELEGRAM_BOT_TOKEN` = ton token

4. **Connecter le repo GitHub** → Railway détecte automatiquement Python et lance le bot

5. **Résultat** : ton bot répond depuis le cloud, PC éteint ou pas

> **Note :** seul `bot_telegram.py` a besoin d'être sur Railway. `capture.py`, `watchdog_capture.py` et Obsidian restent locaux — ils travaillent directement sur tes fichiers.

#### Ce que ça change

| Composant | Local | Railway |
|---|---|---|
| `capture.py` | ✅ reste local | — |
| `watchdog_capture.py` | ✅ reste local | — |
| Obsidian | ✅ reste local | — |
| `bot_telegram.py` | ❌ PC doit tourner | ✅ tourne 24/7 |

---

## Dépannage

| Erreur | Solution |
|---|---|
| `GEMINI_API_KEY manquante` | Vérifier le fichier `.env` |
| `[WinError 2]` lors d'un audio | ffmpeg non installé ou non dans le PATH |
| `FutureWarning google.generativeai` | Utiliser `google-genai` (déjà fait dans ce repo) |
| Emojis cassés sur Windows | Lancer avec `python -X utf8` ou `start.bat` |
| Bot Telegram muet | Vérifier que `python bot_telegram.py` tourne dans un terminal |
