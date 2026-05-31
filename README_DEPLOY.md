# Déploiement sur Railway

Le bot Telegram tourne sur Railway 24/7. Les fiches sont sauvegardées dans Dropbox, synchronisées automatiquement sur ton PC.

---

## 1. Créer un token Dropbox

1. Va sur https://www.dropbox.com/developers/apps
2. Clique **"Create app"**
3. Choisis : **Scoped access** → **Full Dropbox**
4. Donne un nom : `second-cerveau-bot`
5. Dans l'onglet **Permissions**, active :
   - `files.content.write`
   - `files.content.read`
6. Dans l'onglet **Settings** → **OAuth 2** → **Generated access token** → clique **Generate**
7. Copie le token (commence par `sl.`)

> ⚠️ Ce token expire après quelques heures. Pour un token permanent, utilise le flux OAuth avec `DROPBOX_APP_KEY` + `DROPBOX_APP_SECRET` + `DROPBOX_REFRESH_TOKEN` (voir section avancée en bas).

---

## 2. Déployer sur Railway

### 2.1 Créer le projet

1. Va sur https://railway.app → connecte-toi avec GitHub
2. **New Project** → **Deploy from GitHub repo**
3. Sélectionne ton repo `second-cerveau`
4. Railway détecte automatiquement Python via `railway.json`

### 2.2 Ajouter les variables d'environnement

Dans Railway → ton projet → onglet **Variables**, ajoute :

| Variable | Valeur |
|---|---|
| `TELEGRAM_BOT_TOKEN` | ton token BotFather |
| `GEMINI_API_KEY` | ta clé Gemini |
| `DROPBOX_ACCESS_TOKEN` | le token généré à l'étape 1 |
| `ENABLE_WHISPER` | `false` (laisser false sur le plan gratuit) |

### 2.3 Déployer

Railway lance automatiquement le build et démarre `python -X utf8 bot_cloud.py`.

Vérifie les logs dans l'onglet **Deployments** → tu dois voir :
```
🤖 Bot Cloud démarré — Dropbox : /second_cerveau/fiches
```

---

## 3. Tester

1. Ouvre Telegram → parle à ton bot
2. Envoie `/start` → il doit répondre
3. Envoie une URL → une fiche doit apparaître dans ton Dropbox sous `second_cerveau/fiches/`
4. Vérifie dans l'app Dropbox sur ton PC que la fiche est synchronisée dans `fiches/`

---

## 4. Synchroniser Dropbox → Obsidian

Dans Obsidian, pointe le coffre vers le dossier Dropbox synchronisé :
```
C:\Users\<toi>\Dropbox\second_cerveau\fiches\
```
Les nouvelles fiches créées par le bot cloud apparaissent automatiquement dans Obsidian dès la synchronisation.

---

## 5. Token Dropbox permanent (optionnel)

Si le token `sl.` expire, utilise le flux OAuth permanent :

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

Puis dans Railway, remplace `DROPBOX_ACCESS_TOKEN` par trois variables :
- `DROPBOX_APP_KEY`
- `DROPBOX_APP_SECRET`
- `DROPBOX_REFRESH_TOKEN`

---

## 6. Activer la transcription audio (optionnel)

> ⚠️ Déconseillé sur le plan gratuit Railway (512 Mo RAM, CPU limité).

1. Dans `requirements_railway.txt`, décommenter `openai-whisper>=20250625`
2. Dans Railway Variables, ajouter `ENABLE_WHISPER=true`
3. Redéployer

Le modèle Whisper `tiny` (~39 Mo) se télécharge au premier démarrage.

---

## Architecture résumée

```
Telegram (téléphone)
      │  message
      ▼
Bot Railway (bot_cloud.py)
      │  extrait + analyse Gemini
      ▼
Dropbox API ──► /second_cerveau/fiches/TYPE/titre.md
                        │
                        │ sync automatique
                        ▼
                Dropbox local PC
                        │
                        ▼
                  Obsidian 🧠
```
