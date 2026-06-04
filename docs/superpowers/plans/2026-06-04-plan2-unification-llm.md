# Plan 2 — Unification LLM

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centraliser tous les appels LLM texte/vision dans `core.py` via Groq, et supprimer les imports OpenAI dispersés dans `bot_cloud.py`, `titrer_fiches.py` et `brain_agent.py`.

**Architecture:** Deux helpers génériques (`appeler_groq`, `appeler_groq_vision`) ajoutés à `core.py` suivent le même pattern de fallback que `analyser_contenu()`. Les 3 fichiers consommateurs importent depuis `core` au lieu d'instancier `OpenAI` directement. Seule exception : `vectoriser()` dans `brain_agent.py` reste avec OpenAI (Groq n'offre pas d'API embeddings).

**Tech Stack:** groq>=0.9.0 (déjà installé), meta-llama/llama-4-scout-17b-16e-instruct (vision), whisper-large-v3 (audio), llama-3.3-70b-versatile (texte)

---

## Fichiers touchés

| Fichier | Action |
|---|---|
| `core.py` | +`appeler_groq()`, +`appeler_groq_vision()` |
| `bot_cloud.py` | migrate image/audio, supprimer planning extraction |
| `titrer_fiches.py` | migrate `generer_titre()` |
| `brain_agent.py` | migrate `raffiner_note()` + `generer_meta_fiche()`, mettre à jour tests |
| `tests/test_brain_agent.py` | update mocks pour `core.appeler_groq` |

---

### Task 1 : core.py — `appeler_groq()` et `appeler_groq_vision()`

**Files:**
- Modify: `c:\Users\yapa\second_cerveau\core.py` (après `analyser_contenu()`, avant `construire_fiche_complete()`)

- [ ] **Étape 1 : Ajouter `appeler_groq()` après `analyser_contenu()`**

Insérer juste après la fonction `analyser_contenu()` (chercher le commentaire `# ── Construction de la fiche finale`), avant ce commentaire :

```python
def appeler_groq(messages: list[dict], max_tokens: int = 4096) -> str:
    """Appel générique Groq — même fallback que analyser_contenu()."""
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante. Ajoutez-la dans le fichier .env")
    model = os.environ.get("GROQ_MODEL", _GROQ_MODEL_PRIMARY)
    client = Groq(api_key=api_key)
    for m in [model, _GROQ_MODEL_FALLBACK]:
        try:
            r = client.chat.completions.create(model=m, messages=messages, max_tokens=max_tokens)
            return r.choices[0].message.content
        except Exception as e:
            if ("413" in str(e) or "rate_limit_exceeded" in str(e)) and m != _GROQ_MODEL_FALLBACK:
                print(f"⚠️  Contenu trop long pour {m}, bascule sur {_GROQ_MODEL_FALLBACK}...")
                continue
            raise


def appeler_groq_vision(image_bytes: bytes, prompt: str, mime: str = "image/jpeg") -> str:
    """Appel Groq vision (llama-4-scout). Pas de fallback — les images ont une taille fixe."""
    import base64
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante. Ajoutez-la dans le fichier .env")
    b64 = base64.b64encode(image_bytes).decode()
    client = Groq(api_key=api_key)
    r = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": [
            {"type": "text",      "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        max_tokens=1000,
    )
    return r.choices[0].message.content


```

- [ ] **Étape 2 : Vérifier parse**

```powershell
cd C:\Users\yapa\second_cerveau
python -c "import ast; ast.parse(open('core.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 3 : Vérifier importabilité**

```powershell
python -c "from core import appeler_groq, appeler_groq_vision; print('OK')"
```
Attendu : `OK`

- [ ] **Étape 4 : Commit**

```powershell
git add core.py
git commit -m "feat: appeler_groq() et appeler_groq_vision() dans core.py"
```

---

### Task 2 : bot_cloud.py — migrer `extraire_image_bytes()`

**Files:**
- Modify: `c:\Users\yapa\second_cerveau\bot_cloud.py`
  - Import `appeler_groq_vision` en haut
  - Réécrire `extraire_image_bytes()`

- [ ] **Étape 1 : Ajouter `appeler_groq_vision` à l'import depuis core**

Trouver le bloc `from core import (` (lignes 15-21). Ajouter `appeler_groq_vision` à la liste :

```python
from core import (
    formater_source, extraire_champ, slugifier, generer_nom_fichier,
    nettoyer_contenu, evaluer_qualite, extraire_url,
    analyser_contenu, construire_fiche_complete,
    chercher_fiches, geocoder_ville, get_meteo,
    appeler_groq_vision,
    _WMO_FR, LIMITE_EXTRACTION,
)
```

- [ ] **Étape 2 : Réécrire `extraire_image_bytes()`**

Trouver la fonction `extraire_image_bytes` (chercher `def extraire_image_bytes`). Remplacer son corps complet :

```python
def extraire_image_bytes(data: bytes, mime: str = "image/jpeg") -> str:
    return appeler_groq_vision(
        data,
        "Décris cette image en détail. Si elle contient du texte, retranscris-le. "
        "Si c'est un graphique, explique les données.",
        mime,
    )
```

- [ ] **Étape 3 : Vérifier parse**

```powershell
python -c "import ast; ast.parse(open('bot_cloud.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 4 : Commit**

```powershell
git add bot_cloud.py
git commit -m "feat: extraire_image_bytes() migré vers appeler_groq_vision()"
```

---

### Task 3 : bot_cloud.py — migrer `extraire_audio_tmp()`

**Files:**
- Modify: `c:\Users\yapa\second_cerveau\bot_cloud.py` — réécrire `extraire_audio_tmp()`

- [ ] **Étape 1 : Réécrire `extraire_audio_tmp()`**

Trouver `def extraire_audio_tmp`. Remplacer la fonction entière :

```python
def extraire_audio_tmp(data: bytes, ext: str = ".ogg") -> str:
    from groq import Groq
    from pathlib import Path as _Path
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante. Ajoutez-la dans le fichier .env")
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        client = Groq(api_key=api_key)
        with open(tmp_path, "rb") as f:
            t = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=(_Path(tmp_path).name, f),
            )
        return t.text[:LIMITE_EXTRACTION]
    finally:
        os.unlink(tmp_path)
```

- [ ] **Étape 2 : Vérifier parse**

```powershell
python -c "import ast; ast.parse(open('bot_cloud.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 3 : Commit**

```powershell
git add bot_cloud.py
git commit -m "feat: extraire_audio_tmp() migré vers Groq whisper-large-v3"
```

---

### Task 4 : bot_cloud.py — supprimer la planning extraction

**Files:**
- Modify: `c:\Users\yapa\second_cerveau\bot_cloud.py` — 8 suppressions ciblées

Note préliminaire : `_SHIFTS_FR` et `_JOURS_FR` sont CONSERVÉS — ils servent à `envoyer_rappel_planning()` et `planning:voir`.

- [ ] **Étape 1 : Supprimer `PROMPT_PLANNING`**

Trouver `PROMPT_PLANNING = """Tu analyses un screenshot de planning Excel IKEA.` et supprimer toute la constante jusqu'à son `"""` fermant (bloc d'environ 20 lignes).

- [ ] **Étape 2 : Supprimer `extraire_planning_image()`**

Trouver `def extraire_planning_image(data: bytes) -> dict:` et supprimer toute la fonction (environ 25 lignes incluant le commentaire docstring et le `return {"error": "extraction_failed"}`).

- [ ] **Étape 3 : Supprimer `kb_planning_confirm()`**

Trouver `def kb_planning_confirm() -> InlineKeyboardMarkup:` et supprimer les 6 lignes de cette fonction.

- [ ] **Étape 4 : Supprimer `_traiter_planning_bytes()` et `_traiter_planning_photo()`**

Trouver `async def _traiter_planning_bytes(` et supprimer jusqu'à la fin de la fonction. Ensuite trouver `async def _traiter_planning_photo(` et supprimer ses 4 lignes.

- [ ] **Étape 5 : Nettoyer `traiter_photo()`**

Dans `traiter_photo()`, supprimer les branches planning. La fonction doit devenir :

```python
async def traiter_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await update.message.reply_text("⏳ Analyse de la photo…")
    try:
        buf  = io.BytesIO()
        await (await update.message.photo[-1].get_file()).download_to_memory(buf)
        data = buf.getvalue()
        nom  = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        contenu = extraire_image_bytes(data)
        await _analyser_et_uploader(msg, contenu, f"telegram-photo:{nom}")
        uploader_raw(data, nom)
    except Exception as e:
        log.exception("Erreur photo")
        await msg.edit_text(erreur_msg(e))
```

- [ ] **Étape 6 : Nettoyer `traiter_document()`**

Dans `traiter_document()`, supprimer le bloc planning en tête de fonction (les 7 lignes `if ext in {".jpg", ...} and (...): ... return`). La fonction commence directement par le guard taille :

```python
async def traiter_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    ext = os.path.splitext(doc.file_name)[1].lower()

    if doc.file_size and doc.file_size > MAX_DOC_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(
            f"❌ Fichier trop volumineux (max {MAX_DOC_SIZE_MB} Mo). Compresse le PDF avant d'envoyer."
        )
        return
```

- [ ] **Étape 7 : Supprimer les callbacks planning dans `callback_handler()`**

Dans `callback_handler()`, supprimer les 4 blocs `if data == "planning:..."` suivants (garder `planning:voir`) :
- `if data == "planning:upload":` et son corps
- `if data == "planning:confirm":` et son corps
- `if data == "planning:cancel":` et son corps
- `if data == "planning:retry":` et son corps

- [ ] **Étape 8 : Supprimer le bouton "Uploader planning" dans `kb_menu_principal()`**

Dans `kb_menu_principal()`, supprimer la ligne :
```python
        [InlineKeyboardButton("📤 Uploader planning",  callback_data="planning:upload")],
```

- [ ] **Étape 9 : Vérifier parse**

```powershell
python -c "import ast; ast.parse(open('bot_cloud.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 10 : Vérifier qu'OpenAI n'est plus importé dans bot_cloud.py**

```powershell
python -c "
import ast, sys
tree = ast.parse(open('bot_cloud.py').read())
openai_imports = [
    ast.dump(n) for n in ast.walk(tree)
    if isinstance(n, (ast.Import, ast.ImportFrom))
    and 'openai' in ast.dump(n).lower()
]
if openai_imports:
    print('OPENAI ENCORE PRESENT:', openai_imports)
    sys.exit(1)
else:
    print('OK — aucun import openai')
"
```
Attendu : `OK — aucun import openai`

- [ ] **Étape 11 : Commit**

```powershell
git add bot_cloud.py
git commit -m "feat: suppression planning extraction OpenAI, nettoyage bot_cloud.py"
```

---

### Task 5 : titrer_fiches.py — migrer `generer_titre()`

**Files:**
- Modify: `c:\Users\yapa\second_cerveau\titrer_fiches.py`

- [ ] **Étape 1 : Supprimer l'import OpenAI et le client module-level**

Supprimer ces 2 lignes :
```python
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
```

- [ ] **Étape 2 : Réécrire `generer_titre()`**

Remplacer la fonction entière (la boucle retry devient inutile — `appeler_groq()` gère le fallback) :

```python
def generer_titre(idee: str, resume: str) -> str:
    from core import appeler_groq
    contexte = idee or resume or "Note sans contenu"
    prompt = (
        "Génère un titre de 5 à 7 mots maximum qui résume précisément ce contenu. "
        "Pas de ponctuation, pas de guillemets, pas de majuscules inutiles. "
        "Réponds UNIQUEMENT avec le titre, rien d'autre.\n\n"
        f"Contenu : {contexte[:500]}"
    )
    messages = [{"role": "user", "content": prompt}]
    return appeler_groq(messages, max_tokens=50).strip().strip('"').strip("'")
```

- [ ] **Étape 3 : Vérifier parse**

```powershell
python -c "import ast; ast.parse(open('titrer_fiches.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 4 : Vérifier qu'OpenAI n'est plus importé**

```powershell
python -c "
content = open('titrer_fiches.py').read()
if 'openai' in content.lower():
    print('OPENAI ENCORE PRESENT')
    exit(1)
print('OK')
"
```
Attendu : `OK`

- [ ] **Étape 5 : Commit**

```powershell
git add titrer_fiches.py
git commit -m "feat: titrer_fiches.py migré vers core.appeler_groq()"
```

---

### Task 6 : brain_agent.py — migrer `raffiner_note()` et `generer_meta_fiche()`, mettre à jour les tests

**Files:**
- Modify: `c:\Users\yapa\second_cerveau\brain_agent.py`
- Modify: `c:\Users\yapa\second_cerveau\tests\test_brain_agent.py`

- [ ] **Étape 1 : Réécrire `raffiner_note()` — drop `api_key`, utiliser `appeler_groq()`**

Remplacer la fonction entière (garder `_PROMPT_RAFFINEMENT` inchangé — c'est la constante module-level) :

```python
def raffiner_note(contenu: str) -> dict:
    """Raffine une fiche via Groq. Retourne dict avec 5 clés."""
    import re
    from core import appeler_groq
    prompt = _PROMPT_RAFFINEMENT.format(contenu=contenu[:8000])
    messages = [{"role": "user", "content": prompt}]
    raw = appeler_groq(messages, max_tokens=1200).strip()
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip("`").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("raffiner_note: réponse non parseable : %s — %s", raw[:200], e)
        raise
    if "contenu_riche" not in data or not isinstance(data["contenu_riche"], dict):
        data["contenu_riche"] = {"url_source": None, "points_cles": [], "pourquoi_garder": None, "quand_ressortir": None}
    cr = data["contenu_riche"]
    if not isinstance(cr.get("points_cles"), list):
        cr["points_cles"] = []
    return data
```

- [ ] **Étape 2 : Réécrire `generer_meta_fiche()` — drop `api_key`, utiliser `appeler_groq()`**

Remplacer la fonction entière :

```python
def generer_meta_fiche(notes: list[dict]) -> dict:
    """Synthèse d'un cluster via Groq. Retourne dict avec titre, insight, resume, domaine, sources_ids."""
    import re
    from core import appeler_groq
    extraits = "\n\n".join(
        f"Note {i+1} — {n['titre_court']}:\n{n['insight_cle']}"
        for i, n in enumerate(notes[:8])
    )
    prompt = (
        "Crée une méta-fiche de synthèse à partir de ces notes sur le même sujet.\n"
        "Retourne UNIQUEMENT un JSON valide :\n"
        '{{"titre_court":"<4-6 mots>","insight_cle":"<2-3 phrases>","resume":"<paragraphe>","domaine":"<domaine commun>"}}\n\n'
        f"Notes :\n{extraits}"
    )
    messages = [{"role": "user", "content": prompt}]
    raw = appeler_groq(messages, max_tokens=500).strip()
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip("`").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("generer_meta_fiche: réponse non parseable : %s — %s", raw[:200], e)
        raise
    if data.get("domaine") not in DOMAINS:
        data["domaine"] = notes[0].get("domaine", "Projets perso")
    data["sources_ids"] = [n["id"] for n in notes]
    return data
```

- [ ] **Étape 3 : Mettre à jour `run_agent()` — supprimer `api_key` des appels migrés**

Dans `run_agent()`, deux lignes changent (les autres restent avec `api_key` pour `vectoriser()`) :

```python
# Avant
refined   = raffiner_note(fiche["content"], api_key)
...
meta = generer_meta_fiche(cluster, api_key)

# Après
refined   = raffiner_note(fiche["content"])
...
meta = generer_meta_fiche(cluster)
```

Ajouter un commentaire explicatif sur `api_key` dans `run_agent()` :
```python
api_key = os.environ.get("OPENAI_API_KEY", "")
# api_key utilisé uniquement pour vectoriser() — Groq n'a pas d'API embeddings
```

- [ ] **Étape 4 : Vérifier parse de brain_agent.py**

```powershell
python -c "import ast; ast.parse(open('brain_agent.py').read()); print('OK')"
```
Attendu : `OK`

- [ ] **Étape 5 : Mettre à jour les tests dans `tests/test_brain_agent.py`**

Les deux tests `raffiner_note` patchent `brain_agent.OpenAI` et passent `api_key` — tout ça change. Remplacer les deux fonctions de test :

```python
def test_raffiner_note_returns_expected_keys():
    from brain_agent import raffiner_note
    import json
    from unittest.mock import patch
    mock_json = json.dumps({
        "titre_court": "Tips Claude Code",
        "insight_cle": "Les hooks automatisent les actions post-outil.",
        "resume":      "Claude Code supporte des hooks configurables. Ils déclenchent des scripts shell.",
        "domaine":     "Apprentissage",
    })
    with patch("core.appeler_groq", return_value=mock_json):
        result = raffiner_note("contenu de test")
    assert result["titre_court"] == "Tips Claude Code"
    assert result["domaine"]     == "Apprentissage"
    assert "insight_cle" in result
    assert "resume"      in result


def test_raffiner_note_returns_contenu_riche():
    from brain_agent import raffiner_note
    import json
    from unittest.mock import patch
    mock_out = {
        "titre_court": "Astuces Claude Code",
        "insight_cle": "Personnaliser pour maximiser.",
        "resume": "Un résumé.",
        "domaine": "Apprentissage",
        "contenu_riche": {
            "url_source": "https://github.com/test",
            "points_cles": ["Point 1", "Point 2"],
            "pourquoi_garder": "Utile.",
            "quand_ressortir": "Avant un projet."
        }
    }
    with patch("core.appeler_groq", return_value=json.dumps(mock_out)):
        result = raffiner_note("Contenu test")
    assert "contenu_riche" in result
    cr = result["contenu_riche"]
    assert isinstance(cr["points_cles"], list)
    assert cr["url_source"] == "https://github.com/test"
```

- [ ] **Étape 6 : Lancer les tests**

```powershell
cd C:\Users\yapa\second_cerveau
python -m pytest tests/test_brain_agent.py -v
```
Attendu : tous les tests passent (le nombre total reste identique).

- [ ] **Étape 7 : Commit**

```powershell
git add brain_agent.py tests/test_brain_agent.py
git commit -m "feat: brain_agent.py migré vers core.appeler_groq() (vectoriser() conservé OpenAI)"
```

---

## Checklist de vérification finale

Après toutes les tâches :

- [ ] `python -m pytest tests/ -v` → tous les tests passent
- [ ] `python -c "from core import appeler_groq, appeler_groq_vision; print('OK')"` → OK
- [ ] Grep OpenAI dans les 3 fichiers migrés ne retourne que `vectoriser()` dans `brain_agent.py` :
```powershell
Select-String -Path bot_cloud.py, titrer_fiches.py, brain_agent.py -Pattern "openai" -CaseSensitive:$false
```
Attendu : uniquement `brain_agent.py` (lignes `from openai import OpenAI` et `vectoriser`).
