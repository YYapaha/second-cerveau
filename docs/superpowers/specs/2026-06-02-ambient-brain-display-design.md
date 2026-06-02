# Ambient Brain Display — Design Spec
**Date :** 2026-06-02
**Statut :** Approuvé

---

## Objectif

Créer un système "vrai deuxième cerveau" composé d'un agent intelligent et d'une application Electron toujours visible sur l'écran portrait (3e écran), qui présente les notes Dropbox de façon visuelle et intelligente — sans jamais avoir à ouvrir un fichier .md.

---

## Architecture globale

```
Dropbox (notes brutes .md)
        ↓
  brain_agent.py          ← Python, tourne au démarrage + toutes les 2h
  ├─ Récupère toutes les fiches depuis Dropbox
  ├─ Raffine avec GPT-4.1 (qualité, traduction, insight clé)
  ├─ Classe dans un des 6 domaines de vie
  ├─ Génère des méta-fiches (synthèse si 3+ notes sur même sujet)
  ├─ Calcule un score de pertinence contextuelle
  ├─ Vectorise pour la recherche sémantique (text-embedding-3-small)
  └─ Stocke dans brain.db (SQLite local)
        ↓
  brain_server.py          ← FastAPI local (port 7842)
  ├─ GET /notes — liste filtrée et triée
  ├─ GET /notes/:id — détail d'une note
  ├─ GET /a-la-une — 3 notes pertinentes du moment
  ├─ POST /chat — requête en langage naturel, réponse RAG
  └─ GET /status — état de l'agent (dernière sync, nb notes)
        ↓
  Electron app (brain_app/)
  ├─ Fenêtre frameless, toujours visible sur écran 3 (portrait)
  ├─ Cards dark cosmos par domaine
  ├─ Section "À la une" en haut
  ├─ Barre de chat intelligent
  └─ Démarre automatiquement avec Windows
```

---

## Domaines de vie

**6 domaines de classification** (attribués par l'agent à chaque note) :

| Emoji | Domaine | Exemples de contenu |
|---|---|---|
| 💼 | Travail | IKEA, shifts, tâches pro, management |
| 🧠 | Apprentissage | Dev, IA, React Native, Claude Code, outils |
| 🚀 | Projets perso | Second Cerveau, side projects |
| 🎮 | Jeux vidéos | Tips, lore, guides, builds |
| 🌱 | Plantes | Soins, espèces, insights jardinage |
| 🧩 | Organisation TDAH | Méthodes, routines, astuces |

**2 sections d'affichage supplémentaires** (pas des domaines de classification) :

| Emoji | Section | Contenu |
|---|---|---|
| ⭐ | À la une | 3-5 notes à fort score de pertinence du moment, tous domaines confondus |
| 🔗 | Méta-fiches | Synthèses automatiques générées par l'agent (cluster 3+ notes) |

---

## Composant 1 — brain_agent.py

### Cycle d'exécution

1. Télécharge toutes les fiches `.md` depuis Dropbox (`/Applications/Joplin/`)
2. Pour chaque fiche non encore traitée (ou modifiée depuis la dernière sync) :
   - **Raffinement GPT-4.1** → titre court, résumé 2 phrases, insight clé 1 phrase
   - **Classification domaine** → parmi les 6 domaines, via GPT-4.1
   - **Vectorisation** → `text-embedding-3-small`, stocké dans `brain.db`
3. **Détection de clusters** : si 3+ notes partagent le même sujet (similarité cosinus > 0.82) → génère une méta-fiche de synthèse GPT-4.1
4. **Score de pertinence** calculé pour chaque note :
   - Fraîcheur (note récente = score +)
   - Fréquence du domaine dans les captures récentes (7 derniers jours)
   - Boost saisonnier basique (plantes au printemps/été, etc.)
5. Sauvegarde tout dans `brain.db`

### Schéma brain.db

```sql
notes (
  id TEXT PRIMARY KEY,        -- hash du chemin Dropbox
  dropbox_path TEXT,
  titre_court TEXT,           -- généré par GPT-4.1
  insight_cle TEXT,           -- 1 phrase, générée par GPT-4.1
  resume TEXT,                -- 2 phrases
  domaine TEXT,               -- l'un des 6 domaines
  tags TEXT,                  -- tags originaux de la fiche
  date_capture TEXT,
  date_traitement TEXT,
  score_pertinence REAL,
  est_meta_fiche INTEGER,     -- 1 si synthèse automatique
  sources_ids TEXT,           -- IDs sources si méta-fiche (JSON array)
  embedding BLOB              -- vecteur 1536 dimensions (text-embedding-3-small)
)
```

### Raffinement — prompt GPT-4.1

Le raffinement corrige les traductions approximatives et extrait vraiment l'essentiel. La fiche originale dans Dropbox n'est **jamais modifiée**.

---

## Composant 2 — brain_server.py (FastAPI)

API locale minimaliste, consommée uniquement par l'app Electron.

**Endpoints clés :**
- `GET /notes?domaine=Apprentissage&limit=20` — notes filtrées, triées par score
- `GET /a-la-une` — top 3-5 notes du moment
- `POST /chat` avec `{ "query": "..." }` — RAG : embedding de la query, top-k notes, réponse GPT-4.1-mini
- `GET /status` — `{ last_sync, total_notes, meta_fiches_count }`

---

## Composant 3 — Electron app (brain_app/)

### Stack

- **Electron** + **HTML/CSS/JS vanilla** (pas de framework — simplicité et performance)
- Fenêtre frameless, `alwaysOnTop: false`, positionnée sur l'écran 3 au démarrage
- Démarrage auto via le dossier Startup Windows (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`)

### Layout portrait

```
┌─────────────────────────┐
│ ⭐ À LA UNE             │  ← cards horizontales scrollables
│  [card]  [card]  [card] │     titre + insight clé + dot domaine
├─────────────────────────┤
│ 🔍 Pose une question... │  ← input chat, pleine largeur
├─────────────────────────┤
│ 💼 Travail          (4) │  ← sections repliables
│   [card] [card]         │
│ 🧠 Apprentissage   (12) │
│   [card] [card] [card]  │
│ 🚀 Projets          (3) │
│ 🎮 Jeux vidéos      (6) │
│ 🌱 Plantes          (8) │
│ 🧩 TDAH             (5) │
│ 🔗 Méta-fiches      (2) │
└─────────────────────────┘
```

### Design dark cosmos

- Fond `#0a0a0f` avec dot grid subtil (`rgba(255,255,255,0.03)`)
- 1-2 blobs aurora animés lentement en fond (gradient orange/violet/bleu)
- Cards : `background: rgba(255,255,255,0.04)`, `border: 1px solid rgba(255,255,255,0.08)`, `border-radius: 12px`, `backdrop-filter: blur(8px)`
- Dot coloré par domaine en haut à gauche de chaque card
- Typographie : **Inter** ou **Geist** — titre en blanc, insight en `#b0b0c0`, meta en `#606070`
- Hover : légère lueur colorée sur la card (couleur du domaine)
- Jamais de markdown brut affiché

### Chaque card affiche

- Titre court (3-5 mots, généré par GPT-4.1)
- Insight clé (1 phrase)
- Dot de domaine + date courte (ex : "il y a 3j")
- Icône de lien si des notes liées existent

### Chat RAG

- L'utilisateur tape une question en langage naturel
- La query est vectorisée, les 5 notes les plus proches remontent
- GPT-4.1-mini génère une réponse en citant les notes sources
- La réponse s'affiche sous la barre, les cards sources sont mises en évidence

---

## Composant 4 — Note du jour (Telegram)

Chaque matin avec la météo, le bot envoie également l'insight d'une note resurfacée. Courte : titre + insight clé + domaine. Zéro effort côté utilisateur.

**Intégration via Dropbox** (même pattern que `settings.json` et `planning.json`) :
- `brain_agent.py` (local) sélectionne la note du jour et écrit `/second_cerveau/note_du_jour.json` dans Dropbox à chaque cycle
- `bot_cloud.py` (Railway) lit ce fichier depuis Dropbox dans `envoyer_meteo_matin` et ajoute l'insight au message

`brain_agent.py` et `bot_cloud.py` ne communiquent jamais directement — Dropbox est le seul canal entre les deux.

---

## Ce qui ne change pas

- Les fiches Dropbox originales : **jamais modifiées**
- Le bot Telegram de capture : **inchangé**
- `core.py`, `capture.py`, `bot_cloud.py` : modifications minimales (juste l'ajout de la note du jour)

---

## Fichiers créés

| Fichier | Rôle |
|---|---|
| `brain_agent.py` | Agent de raffinement et vectorisation |
| `brain_server.py` | API FastAPI locale |
| `brain_app/main.js` | Process principal Electron |
| `brain_app/index.html` | Interface dark cosmos |
| `brain_app/style.css` | Design |
| `brain_app/renderer.js` | Logique UI + appels API |
| `brain.db` | Base SQLite locale (gitignorée) |
| `requirements_brain.txt` | Dépendances Python du brain |
| `brain_start.bat` | Lance agent + serveur au démarrage |

---

## Dépendances

**Python :** `fastapi`, `uvicorn`, `openai`, `dropbox`, `numpy`, `sqlite3` (stdlib)
**Node/Electron :** `electron`
**Windows :** raccourci `brain_start.bat` dans le dossier Startup

---

## Hors scope

- Modification des fiches depuis l'app (lecture seule)
- Synchronisation en temps réel (polling toutes les 2h suffit)
- Multi-utilisateur
- Version mobile
