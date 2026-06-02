# Ambient Brain — Plan 3 : Intégration bot_cloud.py

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Prérequis :** Plans 1 et 2 terminés. `brain_agent.py` écrit `/second_cerveau/note_du_jour.json` dans Dropbox.

**Goal:** Modifier `bot_cloud.py` pour lire `note_du_jour.json` depuis Dropbox et l'inclure dans le message météo du matin.

**Architecture:** `brain_agent.py` (local) écrit dans Dropbox. `bot_cloud.py` (Railway) lit depuis Dropbox. Aucune communication directe entre les deux — Dropbox est le seul canal.

**Tech Stack:** Python 3.9+, Dropbox SDK (déjà installé sur Railway)

---

## File Map

**Modifiés :**
- `bot_cloud.py` — ajout constante `DROPBOX_NOTE_DU_JOUR` + lecture dans `envoyer_meteo_matin`

**Non modifiés :** `brain_agent.py`, `core.py`, `capture.py`

---

### Task 1 : Intégrer la note du jour dans le message météo

**Files:**
- Modify: `bot_cloud.py:28-35` (section constantes Dropbox)
- Modify: `bot_cloud.py` — fonction `envoyer_meteo_matin`

- [ ] **Step 1: Ajouter la constante DROPBOX_NOTE_DU_JOUR dans bot_cloud.py**

Dans `bot_cloud.py`, dans le bloc des constantes Dropbox (autour de la ligne 33), ajouter après `DROPBOX_PLANNING` :

```python
DROPBOX_NOTE_DU_JOUR = "/second_cerveau/note_du_jour.json"
```

- [ ] **Step 2: Modifier envoyer_meteo_matin pour inclure la note du jour**

Remplacer la fonction `envoyer_meteo_matin` existante par :

```python
async def envoyer_meteo_matin(context) -> None:
    if not TELEGRAM_CHAT_ID:
        return
    # Météo
    try:
        cfg   = load_settings()
        texte = get_meteo(cfg["lat"], cfg["lon"], cfg["ville"])
    except Exception as e:
        log.warning("Erreur météo : %s", e)
        texte = f"🌡️ Météo indisponible ce matin ({type(e).__name__}: {e})"

    # Note du jour depuis Dropbox (écrite par brain_agent.py local)
    note_bloc = ""
    try:
        import dropbox as dbx_mod
        _, res = get_dropbox().files_download(DROPBOX_NOTE_DU_JOUR)
        note   = json.loads(res.content)
        emoji_domaine = {
            "Travail":           "💼",
            "Apprentissage":     "🧠",
            "Projets perso":     "🚀",
            "Jeux vidéos":       "🎮",
            "Plantes":           "🌱",
            "Organisation TDAH": "🧩",
        }.get(note.get("domaine", ""), "📌")
        note_bloc = (
            f"\n\n---\n"
            f"{emoji_domaine} *Note du jour — {note.get('domaine', '')}*\n"
            f"*{note.get('titre_court', '')}*\n"
            f"_{note.get('insight_cle', '')}_"
        )
    except dbx_mod.exceptions.ApiError:
        pass  # Fichier pas encore créé (brain_agent n'a pas encore tourné)
    except Exception as e:
        log.warning("Note du jour introuvable : %s", e)

    await context.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=texte + note_bloc,
        parse_mode="Markdown",
    )
```

- [ ] **Step 3: Vérifier que le code est syntaxiquement valide**

```bash
python -c "import bot_cloud; print('OK')"
```

Expected : `OK` (pas d'erreur de syntaxe)

- [ ] **Step 4: Commit et push → Railway redémarre**

```bash
git add bot_cloud.py
git commit -m "feat: note du jour dans le message météo matinal

brain_agent.py (local) écrit /second_cerveau/note_du_jour.json dans Dropbox.
bot_cloud.py (Railway) le lit et l'ajoute sous la météo chaque matin."
git push origin master
```

Expected : Railway redémarre. Le lendemain matin, le message météo inclut la note du jour.

- [ ] **Step 5: Test manuel de la note du jour (optionnel)**

Pour tester sans attendre le matin : depuis le bot Telegram, envoyer `/start` → `⚙️ Réglages météo` → reprogrammer à l'heure actuelle + 1 min. Le prochain envoi inclura la note du jour si `brain_agent.py` a déjà tourné et écrit le fichier.

---

**Plan 3 terminé — et avec lui, l'ensemble du système Ambient Brain Display.**

## Récapitulatif des 3 plans

| Plan | Ce qui est livré | Testé comment |
|---|---|---|
| Plan 1 — Data layer | `brain_agent.py` + `brain_server.py` + `brain.db` | pytest + curl |
| Plan 2 — Electron UI | `brain_app/` complète avec dark cosmos + Anime.js | Manuel (Electron) |
| Plan 3 — Intégration | `bot_cloud.py` note du jour | Push Railway + matin |

## Ordre d'exécution recommandé

1. Exécuter Plan 1 → vérifier `pytest tests/ -v` et `curl http://127.0.0.1:7842/status`
2. Exécuter Plan 2 → vérifier visuellement l'app sur l'écran portrait
3. Exécuter Plan 3 → push Railway, attendre le lendemain matin
