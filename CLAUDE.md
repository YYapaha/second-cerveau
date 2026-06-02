# Second Cerveau — Contexte pour Claude Code

## Ce qu'est ce projet

Système de capture automatique de connaissances pour un cerveau TDAH. Tout ce qui est intéressant (URL, PDF, image, vocal, texte) est envoyé via Telegram ou un script local, analysé par GPT-4o-mini, et transformé en fiche Markdown structurée stockée dans Dropbox.

## Architecture

- **Bot Telegram** (`bot_cloud.py`) hébergé sur Railway — reçoit les messages, génère les fiches, les envoie dans Dropbox. Chaque `git push` sur `master` redémarre Railway automatiquement.
- **Dropbox** — stockage cloud des fiches, synchronisé automatiquement sur le PC
- **Obsidian** — interface de navigation, pointe sur le dossier Dropbox synchronisé
- **capture.py** — script local pour capturer depuis le PC (URL, PDF, image, audio, texte)

## Ce que fait `bot_cloud.py`

- Capture de contenu (URL, PDF, image, vocal, texte brut)
- Génération de fiches Markdown via GPT-4o-mini
- Sauvegarde dans Dropbox (`/second_cerveau/fiches/TYPE/`)
- Météo automatique chaque matin + bouton "Voir la météo" à la demande
- Notes rapides (`blocnote`, `travail`, `projet`)
- Planning hebdomadaire (upload CSV/photo → extraction GPT)
- Modification de fiches (titre, tags) via menus inline Telegram
- Réglages météo : ville, heure, configurables depuis Telegram

## Ce que fait `capture.py`

- Extraction web : Jina Reader en priorité, Trafilatura en fallback (`favor_recall=True`)
- Nettoyage anti-injection avant envoi à GPT
- Analyse GPT-4o-mini avec message système d'isolation
- Génération de fiche Markdown
- Injection de `CONTENU_BRUT` directement dans la fiche (texte intégral, jusqu'à 30 000 chars) — pour URL, PDF, texte

## Structure des fiches

Les fiches sont dans `fiches/TYPE/TAG_titre.md` (TYPE = Note, Tutoriel, Outil, Réflexion, Divers).

Format exact :

```markdown
# [Titre en 5-7 mots]

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
**QUAND_RESSORTIR** : "Quand je ferai X…"
**TYPE** : Note | Tutoriel | Outil | Réflexion
**TAGS** : #tag1 #tag2 #tag3
**DATE** : JJ/MM/AAAA HH:MM

---
**CONTENU_BRUT** :
(texte intégral extrait — URL, PDF, texte uniquement)
```

## Ton rôle quand on te le demande

**Raffiner les fiches existantes** dans le dossier `fiches/`.

1. **Améliorer le TITRE** — précis, 5-7 mots, compréhensible hors contexte
2. **Enrichir les POINTS_CLES** — concrets, actionnables
3. **Affiner QUAND_RESSORTIR** — vrai déclencheur futur
4. **Compléter RESUME_COMPLET** si trop court
5. **Corriger les TAGS** — techniques, spécifiques, 5 max
6. **Vérifier POURQUOI_GARDER** — doit parler dans 6 mois

### Ce qu'il ne faut PAS faire
- Ne pas changer le format des champs
- Ne pas déplacer les fichiers
- Ne pas fusionner des fiches
- Ne pas inventer du contenu absent de la fiche originale

## Chantier en cours — Ambient Brain Display

Un système "vrai deuxième cerveau" avec interface Electron sur l'écran portrait.

**Spec :** `docs/superpowers/specs/2026-06-02-ambient-brain-display-design.md`

**Plans d'implémentation en 3 parties :**

| Plan | Fichier | Statut |
|---|---|---|
| Plan 1 — Data layer | `docs/superpowers/plans/2026-06-02-brain-data-layer.md` | ✅ TERMINÉ (17 tests verts) |
| Plan 2 — Electron UI | `docs/superpowers/plans/2026-06-02-brain-electron-ui.md` | ⏳ À FAIRE (prochain) |
| Plan 3 — Intégration bot | `docs/superpowers/plans/2026-06-02-brain-integration.md` | ⏳ À FAIRE (après Plan 2) |

**Pour reprendre :** lire le plan suivant + lancer `/superpowers:subagent-driven-development`

**Nouveaux fichiers créés (Plan 1) :**
- `brain_agent.py` — agent Python local (sync Dropbox → GPT → SQLite)
- `brain_server.py` — API FastAPI locale port 7842
- `brain.db` — base SQLite locale (gitignorée)
- `brain_start.bat` — lance agent + serveur + Electron
- `requirements_brain.txt` — dépendances Python brain
- `tests/test_brain_agent.py` + `tests/test_brain_server.py`

## Fichiers importants

| Fichier | Rôle |
|---|---|
| `bot_cloud.py` | Bot Telegram Railway (production) |
| `core.py` | Noyau partagé (extraction, analyse GPT, météo, recherche) |
| `capture.py` | Script de capture local |
| `chercher.py` | Recherche plein texte dans les fiches |
| `brain_agent.py` | Agent Ambient Brain (nouveau) |
| `brain_server.py` | API FastAPI locale (nouveau) |
| `blocnotes.md` (Dropbox) | Notes rapides |
| `travail.md` (Dropbox) | Tâches professionnelles |

## Variables d'environnement (Railway)

| Variable | Usage |
|---|---|
| `OPENAI_API_KEY` | GPT-4o-mini (analyse + vision) |
| `TELEGRAM_BOT_TOKEN` | Bot Telegram |
| `TELEGRAM_CHAT_ID` | Chat autorisé |
| `DROPBOX_APP_KEY` | Auth Dropbox |
| `DROPBOX_APP_SECRET` | Auth Dropbox |
| `DROPBOX_REFRESH_TOKEN` | Auth Dropbox (permanent) |
