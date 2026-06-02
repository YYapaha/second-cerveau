# Déploiement sur Railway

Le bot Telegram (`bot_cloud.py`) tourne sur Railway 24/7. Les fiches sont sauvegardées dans Dropbox, synchronisées automatiquement sur le PC et visibles dans Obsidian.

---

## Architecture

```
Telegram (téléphone)
      │
      ▼
Bot Railway — bot_cloud.py
      │  extraction (Jina / Trafilatura) + analyse GPT-4o-mini
      ▼
Dropbox API ──► /second_cerveau/fiches/TYPE/titre.md
                        │ sync automatique
                        ▼
                Dropbox local PC → Obsidian 🧠
```

---

## 1. Créer un token Dropbox permanent

1. Va sur https://www.dropbox.com/developers/apps
2. Clique **"Create app"** → **Scoped access** → **Full Dropbox** → nom : `second-cerveau-bot`
3. Onglet **Permissions** : activer `files.content.write` et `files.content.read`
4. Lancer le script OAuth pour obtenir un refresh token permanent :

```bash
pip install dropbox
python - <<'EOF'
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect

APP_KEY = "ton_app_key"
APP_SECRET = "ton_app_secret"

auth_flow = DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET, token_access_type='offline')
print("Ouvre cette URL :", auth_flow.start())
code = input("Colle le code ici : ").strip()
result = auth_flow.finish(code)
print("DROPBOX_REFRESH_TOKEN =", result.refresh_token)
EOF
```

---

## 2. Déployer sur Railway

### 2.1 Créer le projet

1. https://railway.app → connecte-toi avec GitHub
2. **New Project** → **Deploy from GitHub repo** → sélectionner `second-cerveau`
3. Railway détecte Python automatiquement via `railway.json`

### 2.2 Variables d'environnement

Dans Railway → ton projet → onglet **Variables** :

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token BotFather |
| `TELEGRAM_CHAT_ID` | Ton chat ID Telegram |
| `OPENAI_API_KEY` | Clé API OpenAI (pour GPT-4o-mini) |
| `DROPBOX_APP_KEY` | App key Dropbox |
| `DROPBOX_APP_SECRET` | App secret Dropbox |
| `DROPBOX_REFRESH_TOKEN` | Refresh token généré à l'étape 1 |
| `ENABLE_WHISPER` | `false` (laisser false, trop lourd sur le plan gratuit) |

### 2.3 Déployer

Railway lance automatiquement le build et démarre `python -X utf8 bot_cloud.py`.

Vérifie les logs dans **Deployments** → tu dois voir :
```
🤖 Bot Cloud démarré
⏰ Météo à Xh, récaps à 8h 12h 18h 22h (Paris)
```

---

## 3. Tester

1. Telegram → `/start` → le bot doit répondre avec le menu
2. Envoyer une URL → une fiche apparaît dans Dropbox sous `second_cerveau/fiches/`
3. Menu `/start` → 🌤️ Voir la météo → doit afficher la météo actuelle
4. Menu `/start` → ⚙️ Réglages météo → tester le changement de ville

---

## 4. Redéployer après une modification

Chaque `git push` sur `master` redémarre Railway automatiquement.

```bash
git add .
git commit -m "ma modification"
git push origin master
```

---

## 5. Activer la transcription audio (optionnel)

> ⚠️ Déconseillé sur le plan gratuit (512 Mo RAM).

1. Dans `requirements_railway.txt`, décommenter `openai-whisper`
2. Dans Railway Variables : `ENABLE_WHISPER=true`
3. Redéployer — le modèle Whisper `tiny` (~39 Mo) se télécharge au premier démarrage

---

## Fonctionnalités du bot

| Feature | Déclencheur |
|---|---|
| Capture URL | Envoyer un lien |
| Capture PDF | Envoyer un fichier |
| Capture image | Envoyer une photo |
| Capture vocal | Envoyer un vocal |
| Capture texte | Écrire directement |
| Note rapide | `blocnote ton texte` |
| Tâche pro | `travail ta tâche` |
| Planning | Menu → 📅 Mon planning |
| Météo à la demande | Menu → 🌤️ Voir la météo |
| Météo automatique matin | Configurée via ⚙️ Réglages météo |
| Modifier fiche (titre/tags) | Menu après chaque capture |
