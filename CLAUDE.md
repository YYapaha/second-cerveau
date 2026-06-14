# Second Cerveau — Contexte pour Claude Code

## Ce qu'est ce projet

Système de capture automatique de connaissances pour un cerveau TDAH. Tout ce qui est intéressant (URL, PDF, image, vocal, texte) est envoyé via Telegram ou un script local, analysé par GPT-4o-mini, et transformé en fiche Markdown structurée stockée dans Dropbox.

Un **Ambient Brain Display** tourne en parallèle : une app Electron affiche les notes en permanence sur l'écran portrait (écran 3), alimentée par un agent Python local et une API FastAPI.

---

## Architecture globale

```
Dropbox (fiches .md)
    ↓
brain_agent.py          ← Python local, tourne au démarrage + flag --reprocess
├─ Sync Dropbox → GPT-4.1 → raffine (titre, insight, résumé, contenu_riche)
├─ Vectorise (text-embedding-3-small)
├─ Détecte clusters → méta-fiches
├─ Calcule scores de pertinence
└─ Stocke dans brain.db (SQLite)
    ↓
brain_server.py         ← FastAPI local port 7842
├─ GET  /status
├─ GET  /notes
├─ GET  /a-la-une
├─ POST /chat (RAG)
├─ DELETE /notes/{id}   ← supprime DB + Dropbox
└─ PATCH /notes/{id}    ← édition titre_court
    ↓
brain_app/              ← Electron 35, écran portrait, toujours visible
├─ main.js              ← BrowserWindow + IPC (openUrl via shell.openExternal)
├─ preload.js           ← expose BRAIN_API_URL + openUrl (via ipcRenderer)
├─ index.html           ← structure dark cosmos
├─ style.css            ← design system (oklch tokens, glassmorphism, aurora)
├─ renderer.js          ← grille, constellation, modal enrichie, delete animé, titre éditable
└─ logo.svg             ← logo synapse-node
```

---

## Bot Telegram (`bot_cloud.py`)

Hébergé sur **Railway** — chaque `git push master` redémarre automatiquement.

- Capture (URL, PDF, image, vocal, texte brut) → fiches Markdown dans Dropbox
- Météo automatique chaque matin à 7h00 (timeout 30s, retry 3×)
- Notes rapides (`blocnote`, `travail`, `projet`)
- Planning hebdomadaire
- Modification de fiches via menus inline Telegram
- Réglages météo configurables

---

## Démarrage de l'Ambient Brain Display

```bat
brain_start.bat          ← double-clic ou via raccourci Startup
```

Séquence :
1. Lance `brain_agent.py` (minimisé)
2. Attend 10s → Lance `brain_server.py` sur port 7842 (minimisé)
3. Attend 3s → Lance `brain_app/` (Electron, plein écran écran portrait)

**Raccourci Startup Windows :** `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Second Cerveau.lnk`
→ pointe vers `brain_start.bat` avec `WorkingDirectory = C:\Users\yapa\second_cerveau`

---

## Re-traitement des notes (prompt enrichi)

```bash
python brain_agent.py --reprocess
```

Re-traite toutes les notes **sauf domaine=Travail** avec le nouveau prompt GPT-4.1 (1200 tokens) qui extrait :
- `contenu_riche.url_source` — URL de la source
- `contenu_riche.points_cles` — liste de bullets actionnables
- `contenu_riche.pourquoi_garder` — valeur long terme
- `contenu_riche.quand_ressortir` — contexte d'utilisation
- `titre_court` — vrai titre de la source (pas reformulé)

⚠️ Nécessite `OPENAI_API_KEY` + Dropbox tokens dans `.env`.

---

## Variables d'environnement (`.env` local + Railway)

| Variable | Usage |
|---|---|
| `OPENAI_API_KEY` | GPT-4.1 (brain_agent) + GPT-4o-mini (bot) |
| `TELEGRAM_BOT_TOKEN` | Bot Telegram |
| `TELEGRAM_CHAT_ID` | Chat autorisé |
| `DROPBOX_APP_KEY` | Auth Dropbox |
| `DROPBOX_APP_SECRET` | Auth Dropbox |
| `DROPBOX_REFRESH_TOKEN` | Auth Dropbox (permanent) |

---

## État du chantier Ambient Brain Display

| Plan | Fichier | Statut |
|---|---|---|
| Plan 1 — Data layer | `docs/superpowers/plans/2026-06-02-brain-data-layer.md` | ✅ TERMINÉ — 23 tests verts |
| Plan 2 — Electron UI | `docs/superpowers/plans/2026-06-02-brain-electron-ui.md` | ✅ TERMINÉ |
| Plan 3 — UI Redesign | `docs/superpowers/plans/2026-06-03-brain-ui-redesign.md` | ✅ TERMINÉ — dark cosmos |
| Plan 4 — Enrichissement | `docs/superpowers/plans/2026-06-03-brain-notes-enrichissement.md` | ✅ TERMINÉ |
| Compact Notes Layout | `docs/superpowers/plans/2026-06-05-compact-notes-layout.md` | ✅ TERMINÉ — lignes ~27px |
| Domain Editing | `docs/superpowers/plans/2026-06-05-domain-editing.md` | ✅ TERMINÉ — 108 tests verts |
| Plan 3-bot — Intégration bot | `docs/superpowers/plans/2026-06-02-brain-integration.md` | ⏳ À FAIRE |
| Plan 5 — Note personnelle | *(spec à écrire)* | ⏳ FUTUR |

### Plan 3-bot (prochain)
Intégration `brain_agent.py` → `bot_cloud.py` via Dropbox :
- `brain_agent.py` écrit `note_du_jour.json` dans Dropbox à chaque cycle
- `bot_cloud.py` lit ce fichier et l'inclut dans le message météo matinal

### Plan 5 (futur)
Note personnelle par fiche avec sync Dropbox :
- Champ `note_personnelle` dans la DB + section `## Note personnelle` dans le `.md` Dropbox
- Édition depuis la modale Electron
- `brain_agent.py` préserve cette section lors du re-process

---

## Schema brain.db

```sql
notes (
  id               TEXT PRIMARY KEY,
  dropbox_path     TEXT,
  titre_court      TEXT,         -- généré par GPT-4.1 (ou édité manuellement)
  insight_cle      TEXT,         -- 1 phrase clé
  resume           TEXT,         -- 2-3 phrases
  domaine          TEXT,         -- Travail|Apprentissage|Projets perso|Jeux vidéos|Plantes|Organisation TDAH
  tags             TEXT,
  date_capture     TEXT,
  date_traitement  TEXT,
  score_pertinence REAL,
  est_meta_fiche   INTEGER,      -- 1 si synthèse automatique
  sources_ids      TEXT,         -- JSON array des IDs sources (méta-fiches)
  embedding        BLOB,         -- vecteur 1536 dim
  contenu_riche    TEXT,         -- JSON: {url_source, points_cles, pourquoi_garder, quand_ressortir}
  titre_modifie    INTEGER       -- 1 si titre édité manuellement (protégé lors de --reprocess)
)
```

---

## Fonctionnalités de l'app Electron

**Vue Grille :**
- Featured cards (À la une) — scroll horizontal, clic → modale
- Barre de chat RAG — question → réponse GPT + highlight des sources
- Filtres par domaine + tri récents/anciens + toggle "Liées"
- Sections repliables par domaine
- Stats de coin (N notes, dernière sync)

**Modale d'une note :**
- Aurora header teinté par domaine
- Lien source cliquable → ouvre navigateur par défaut (via IPC main.js)
- Titre éditable inline (Enter/Esc) → PATCH /notes/{id}
- Insight + Résumé + Points clés + Pourquoi garder + Quand ressortir
- Tags, notes liées/sources
- Jauge de pertinence
- Bouton suppression → animation Anime.js + DELETE /notes/{id} + Dropbox

**Vue Constellation :**
- Nodes par domaine disposés en anneau
- Edges Bézier entre notes liées
- Pan (glisser), hover → edges illuminés
- Clic sur node → modale

---

## Structure des fiches Dropbox

```markdown
# [Titre]

[URL source]

## Résumé rapide
…

## Analyse complète
…

---
**POURQUOI_GARDER** : …
**IDEE_PRINCIPALE** : …
**POINTS_CLES** :
- …
**QUAND_RESSORTIR** : "Quand je ferai X…"
**TYPE** : Note | Tutoriel | Outil | Réflexion
**TAGS** : #tag1 #tag2 #tag3
**DATE** : JJ/MM/AAAA HH:MM
---
**CONTENU_BRUT** :
(texte intégral — URL, PDF, texte uniquement)
```

---

## Fichiers importants

| Fichier | Rôle |
|---|---|
| `bot_cloud.py` | Bot Telegram Railway (production) |
| `core.py` | Noyau partagé (extraction web, météo, GPT) |
| `capture.py` | Script de capture local |
| `brain_agent.py` | Agent Brain (sync Dropbox → GPT → SQLite) |
| `brain_server.py` | API FastAPI locale port 7842 |
| `brain_start.bat` | Lance les 3 composants au démarrage |
| `brain_app/` | App Electron (UI portrait) |
| `brain.db` | SQLite locale (gitignorée) |
| `.env` | Tokens locaux (gitignorés) |
| `docs/superpowers/specs/` | Specs de design |
| `docs/superpowers/plans/` | Plans d'implémentation |

## Lecture rapide — démarrage de session

> Lire ces fichiers en priorité au début de chaque session pour avoir le contexte complet.

### Toujours lire

| Fichier | Pourquoi |
|---|---|
| `docs/superpowers/lessons-learned.md` | Bugs réels rencontrés + règles à ne pas répéter |

### Plans actifs (⏳ À FAIRE)

| Fichier plan | Fichier spec | But en une ligne |
|---|---|---|
| `docs/superpowers/plans/2026-06-04-plan1-securite-stabilite.md` | `docs/superpowers/specs/2026-06-04-plan1-securite-stabilite-design.md` | Sécuriser `bot_cloud.py` : OPENAI non-bloquante, /ping, /health, error handler |
| `docs/superpowers/plans/2026-06-04-plan2-unification-llm.md` | `docs/superpowers/specs/2026-06-04-plan2-unification-llm-design.md` | Centraliser tous les appels LLM dans `core.py` via Groq |
| `docs/superpowers/plans/2026-06-04-plan3-deduplication-refactoring.md` | `docs/superpowers/specs/2026-06-04-plan3-deduplication-refactoring-design.md` | Extraire couche Dropbox dans `dropbox_client.py`, dédupliquer helpers |
| `docs/superpowers/plans/2026-06-04-plan4-tests.md` | `docs/superpowers/specs/2026-06-04-plan4-tests-design.md` | Ajouter ~36 tests sur `core.py`, `dropbox_client.py`, pipeline |
| `docs/superpowers/plans/2026-06-02-brain-integration.md` | *(pas de spec séparée)* | Inclure `note_du_jour.json` dans le message météo Telegram |

### Travaux en cours non commités

| Fichier | État |
|---|---|
| `core.py` | Modifications non commitées (lié plan2/4 — vérifier avant de commencer) |
| `tests/test_core.py` | Tests non commités (idem) |

---

## Tests

```bash
python -m pytest tests/ -v   # 108 tests (brain_agent + brain_server + core + dropbox + pipeline)
```

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
