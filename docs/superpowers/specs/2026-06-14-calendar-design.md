# Spec — Calendrier avec rappels Telegram

**Date :** 2026-06-14
**Statut :** Approuvé — prêt pour implémentation

---

## Objectif

Ajouter un onglet Calendrier dans l'app Electron permettant de gérer des rendez-vous, anniversaires, tâches et deadlines, avec notifications Telegram configurables (rappels J-7, J-1, H-1, etc.) et une intégration bidirectionnelle avec le bot Telegram (ajout, consultation, édition, suppression depuis Telegram).

---

## Décisions de design

| Question | Choix |
|---|---|
| Intégration UI | 3ème onglet dédié (après Notes et Constellation) |
| Layout | Mini-grille mensuelle (gauche) + liste agenda (droite) |
| Telegram | Bidirectionnel : notifs + /rdv + /agenda + edit/delete |
| Rappels | Plusieurs par événement (ex: J-1 et H-1 simultanément) |
| Stockage | `calendar.db` SQLite séparé (côté local) |
| Architecture | Local pur + Dropbox bridge |

---

## Modèle de données — `calendar.db`

```sql
CREATE TABLE events (
  id           TEXT PRIMARY KEY,
  titre        TEXT NOT NULL,
  type         TEXT NOT NULL CHECK(type IN ('rdv','anniversaire','tache','deadline')),
  date_debut   TEXT NOT NULL,   -- ISO 8601 : "2026-06-19" ou "2026-06-19T14:00"
  date_fin     TEXT,            -- optionnel (multi-jours)
  description  TEXT,
  source       TEXT DEFAULT 'electron', -- 'electron' | 'telegram'
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);

CREATE TABLE reminders (
  id           TEXT PRIMARY KEY,
  event_id     TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  offset_type  TEXT NOT NULL CHECK(offset_type IN ('minutes','hours','days','weeks')),
  offset_value INTEGER NOT NULL,
  send_time    TEXT,            -- "HH:MM" optionnel — utilisé quand offset_value=0 (ex: "09:00" pour J-0 matin)
  sent         INTEGER DEFAULT 0,
  sent_at      TEXT
);

-- Convention J-0 matin : offset_type='days', offset_value=0, send_time='09:00'
-- Sans send_time : le rappel est envoyé dès la prochaine boucle horaire après le calcul
```

**Couleurs par type :**
- `rdv` → `#6366f1` (violet)
- `anniversaire` → `#ec4899` (rose)
- `tache` → `#f59e0b` (amber)
- `deadline` → `#ef4444` (rouge)

**Icônes :** `📅 🎂 ✅ ⏰`

---

## Architecture & flux de données

```
calendar.db (local SQLite)
    ↑↓
brain_server.py          ← 7 nouveaux endpoints /calendar/*
    ↑↓
brain_app/ (Electron)    ← nouvel onglet Calendrier (calendar.js)
    ↕
brain_calendar.py        ← process local (brain_start.bat)
    ├─ boucle 1 : check toutes les heures → reminders dus → POST Telegram API
    └─ boucle 2 : sync Dropbox toutes les 5 min → upsert calendar.db

Dropbox/calendar_events.json   ← fichier bridge
    ↑↓
bot_cloud.py (Railway)
    ├─ /rdv  → GPT parse → écrit dans Dropbox JSON
    ├─ /agenda → lit Dropbox JSON → liste avec boutons inline
    └─ callbacks : edit / delete → upsert / marque deleted=true dans Dropbox JSON
```

### Flux ajout depuis Telegram

1. User : `/rdv Médecin demain à 14h`
2. Bot parse via GPT-4o-mini (today=DATE passé en système) → `{titre, date_debut, type}`
3. Bot répond : *"J'ai compris : RDV Médecin le 15/06 à 14h. C'est bien ça ?"* `[Oui ✅]` `[Corriger]`
4. Confirmation → écrit l'event dans `Dropbox/calendar_events.json`
5. `brain_calendar.py` poll Dropbox toutes les 5 min → importe dans `calendar.db`
6. L'app Electron voit l'event au prochain refresh

### Flux envoi des rappels

1. `brain_calendar.py` tourne en boucle (check toutes les heures)
2. Requête : `SELECT r.*, e.* FROM reminders r JOIN events e ON r.event_id=e.id WHERE r.sent=0`
3. Pour chaque reminder : calcule `date_debut - offset` → si `≤ now` → envoie
4. Messages formatés selon le type :
   - `📅 Rappel : RDV Médecin demain à 14h`
   - `🎂 Anniversaire de maman dans 1 semaine !`
   - `✅ À faire aujourd'hui : Appeler le notaire`
   - `⏰ Deadline dans 24h : Rendu projet`
5. Marque `sent=1 + sent_at` dans `calendar.db`

### Fichier Dropbox bridge — `calendar_events.json`

```json
[
  {
    "id": "uuid4",
    "titre": "RDV Médecin",
    "type": "rdv",
    "date_debut": "2026-06-19T14:00",
    "date_fin": null,
    "description": null,
    "reminders": [
      {"offset_type": "days", "offset_value": 1},
      {"offset_type": "hours", "offset_value": 1}
    ],
    "deleted": false,
    "source": "telegram",
    "updated_at": "2026-06-14T10:30:00"
  }
]
```

La sync locale supprime de `calendar.db` les events marqués `deleted: true` et réécrit le JSON sans eux.

---

## Endpoints FastAPI — `brain_server.py`

| Méthode | Route | Description |
|---|---|---|
| GET | `/calendar/events` | Liste (params: `from`, `to`, `type`) |
| POST | `/calendar/events` | Créer un event |
| GET | `/calendar/events/{id}` | Détail + reminders |
| PATCH | `/calendar/events/{id}` | Modifier titre, date, type, description |
| DELETE | `/calendar/events/{id}` | Supprimer event + reminders (CASCADE) |
| POST | `/calendar/events/{id}/reminders` | Ajouter un reminder |
| DELETE | `/calendar/events/{id}/reminders/{rid}` | Supprimer un reminder |

---

## Nouveau process local — `brain_calendar.py`

Lancé au démarrage via `brain_start.bat` (4ème ligne : `start /min python brain_calendar.py`).

Pas de dépendance à `brain_server.py` — lit/écrit `calendar.db` directement.

**Sync bidirectionnelle :**
- **Dropbox → calendar.db** (toutes les 5 min) : importe les events créés/modifiés/supprimés via Telegram
- **calendar.db → Dropbox** (toutes les 5 min) : exporte tous les events locaux dans `calendar_events.json` pour que `/agenda` Telegram affiche aussi les events créés depuis l'app Electron

Le JSON Dropbox est donc un export complet de `calendar.db` à chaque sync, pas seulement les events Telegram.

Variables d'env requises (déjà dans `.env`) :
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN`

---

## Bot Telegram — `bot_cloud.py` (Railway)

### Nouvelles commandes

**`/rdv [texte libre]`**
- GPT-4o-mini parse le texte (prompt système : `today=DATE`, `timezone=Europe/Paris`)
- Retourne `{titre, type, date_debut, heure?}`
- Bot demande confirmation avec boutons `[Oui ✅]` `[Corriger ✏️]`
- Confirmation → upsert dans `calendar_events.json` Dropbox

**`/agenda`**
- Lit `calendar_events.json` Dropbox
- Affiche les N prochains events (triés par date)
- Chaque event a des boutons inline `[✏️ Éditer]` `[🗑️ Supprimer]`

### Callbacks inline

| Callback data | Action |
|---|---|
| `cal:del:{id}` | Confirmation "Supprimer ?" → `[Oui]` `[Non]` → marque `deleted:true` |
| `cal:edit:{id}` | Menu `[Titre]` `[Date/Heure]` `[Rappels]` |
| `cal:edit:{id}:titre` | Demande nouveau titre → GPT valide → upsert |
| `cal:edit:{id}:date` | Demande nouvelle date (langage naturel) → GPT parse → upsert |
| `cal:edit:{id}:rappels` | Boutons checkboxes `[S-1]` `[J-7]` `[J-3]` `[J-1]` `[H-2]` `[H-1]` `[J-0 matin]` |

---

## UI Electron — nouvel onglet Calendrier

### Fichiers touchés / créés

| Fichier | Changement |
|---|---|
| `brain_app/calendar.js` | Nouveau module — toute la logique calendrier |
| `brain_app/renderer.js` | Ajout de l'onglet + délégation à `calendar.js` |
| `brain_app/index.html` | Ajout du conteneur `#calendar-view` |
| `brain_app/style.css` | Styles calendrier (variables déjà disponibles) |

### Layout

```
┌─────────────────────────────────────────────┐
│  [Notes]  [Constellation]  [Calendrier ✦]   │  ← tabbar
├──────────────┬──────────────────────────────┤
│ + Ajouter    │  Prochains événements  [Tous] │
│              │  [📅 RDV] [🎂] [✅] [⏰]      │
│  < Juin 2026 >│                              │
│  L M M J V S D│ AUJOURD'HUI · 14 Juin        │
│  ...grille...│ ┌─────────────────────────┐  │
│  14● 19● 23● │ │📅 RDV Médecin 14h  ✏️🗑️│  │
│              │ │   🔔 J-1, H-1           │  │
│              │ └─────────────────────────┘  │
│              │ Dans 5 jours · 19 Juin        │
│              │ ┌─────────────────────────┐  │
│              │ │🎂 Anniversaire maman ✏️🗑️│  │
│              │ └─────────────────────────┘  │
└──────────────┴──────────────────────────────┘
```

### Modale ajout/édition

Champs : Titre · Type (select) · Date & heure · Description (optionnel) · Rappels (chips toggle)

Chips de rappels disponibles : `S-1` `J-7` `J-3` `J-1` `H-2` `H-1` `J-0 matin`

Actions ✏️/🗑️ visibles au hover sur chaque event.

---

## `brain_start.bat` — modification

```bat
start /min python brain_agent.py
timeout /t 10 /nobreak
start /min python brain_server.py
timeout /t 3 /nobreak
start /min python brain_calendar.py   ← NOUVEAU
timeout /t 2 /nobreak
start brain_app\node_modules\.bin\electron.cmd brain_app
```

---

## Fichiers nouveaux / modifiés

| Fichier | Type | Description |
|---|---|---|
| `calendar.db` | Nouveau | SQLite local (gitignorée) |
| `brain_calendar.py` | Nouveau | Scheduler local + sync Dropbox |
| `brain_app/calendar.js` | Nouveau | Module UI Electron |
| `brain_server.py` | Modifié | +7 endpoints /calendar/* |
| `bot_cloud.py` | Modifié | +/rdv, /agenda, callbacks cal:* |
| `brain_app/renderer.js` | Modifié | +onglet Calendrier |
| `brain_app/index.html` | Modifié | +#calendar-view |
| `brain_app/style.css` | Modifié | +styles calendrier |
| `brain_start.bat` | Modifié | +lancement brain_calendar.py |

---

## Hors scope (futur possible)

- Événements récurrents (ex: anniversaire chaque année)
- Synchronisation avec Google Calendar / iCal
- Notifications desktop (Electron notifications)
- Vue semaine ou jour
