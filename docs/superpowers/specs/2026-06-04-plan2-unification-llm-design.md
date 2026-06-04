# Plan 2 — Unification LLM

**Date :** 2026-06-04  
**Statut :** Approuvé pour implémentation  
**Contexte :** Deuxième plan de remboursement de dette technique du second cerveau. Fait suite au Plan 1 (Sécurité & stabilité).

---

## Objectif

Éliminer les appels OpenAI dispersés dans 3 fichiers. Centraliser toute génération de texte dans `core.py` via Groq. Seule exception : les embeddings dans `brain_agent.py` (Groq n'offre pas d'API embeddings).

---

## Architecture

```
core.py
  analyser_contenu()        ← existant (notes → fiche markdown)
  appeler_groq(messages)    ← NOUVEAU : text completion générique
  appeler_groq_vision()     ← NOUVEAU : image bytes → texte

bot_cloud.py   → core.appeler_groq_vision()   (description image)
               → Groq Whisper API             (transcription audio)
               → ❌ planning image extraction  supprimée

titrer_fiches.py → core.appeler_groq()        (génération titre)

brain_agent.py   → core.appeler_groq()        (raffiner_note, generer_meta_fiche)
                 → OpenAI text-embedding-3-small (vectoriser — inchangé)
```

---

## Changements `core.py`

### 1. `appeler_groq(messages, max_tokens=4096) -> str`

Même logique de fallback que `analyser_contenu()` : essaie `_GROQ_MODEL_PRIMARY`, bascule sur `_GROQ_MODEL_FALLBACK` sur erreur 413/rate_limit.

```python
def appeler_groq(messages: list[dict], max_tokens: int = 4096) -> str:
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante dans le fichier .env")
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
```

### 2. `appeler_groq_vision(image_bytes, prompt, mime="image/jpeg") -> str`

Modèle fixe : `meta-llama/llama-4-scout-17b-16e-instruct` (seul modèle vision disponible sur Groq). Pas de fallback TPM (images = taille fixe, pas de token overflow).

```python
def appeler_groq_vision(image_bytes: bytes, prompt: str, mime: str = "image/jpeg") -> str:
    import base64
    from groq import Groq
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante dans le fichier .env")
    b64 = base64.b64encode(image_bytes).decode()
    client = Groq(api_key=api_key)
    r = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        max_tokens=1000,
    )
    return r.choices[0].message.content
```

Ces 2 fonctions sont exportées : ajouter à l'import dans `core.py` et aux `__all__` si défini.

---

## Changements `bot_cloud.py`

### Suppressions (planning image extraction — non utilisé)

Les éléments suivants sont supprimés car ils dépendent de `extraire_planning_image()`. Les constantes de *display* (`_SHIFTS_FR`, `_JOURS_FR`) sont conservées — elles servent à `envoyer_rappel_planning()` et `planning:voir`.

| Élément | Localisation | Action |
|---|---|---|
| `PROMPT_PLANNING` | ligne ~69 | Supprimer |
| `extraire_planning_image()` | ligne ~306 | Supprimer |
| `_traiter_planning_bytes()` | ligne ~947 | Supprimer |
| `_traiter_planning_photo()` | ligne ~976 | Supprimer |
| `kb_planning_confirm()` | ligne ~517 | Supprimer |
| Branch planning dans `traiter_photo()` | lignes ~983-989 | Supprimer les 7 lignes |
| Branch planning dans `traiter_document()` | lignes ~1010-1016 | Supprimer les 7 lignes |
| Callbacks `planning:upload`, `planning:confirm`, `planning:retry`, `planning:cancel` dans `callback_handler` | lignes ~1314, 1324, 1336, 1341 | Supprimer chaque bloc `if data == "planning:..."` |
| Bouton "Uploader planning" dans `kb_menu_principal()` | ligne ~511 | Supprimer la ligne |

### Migration `extraire_image_bytes()`

```python
# Avant
def extraire_image_bytes(data: bytes, mime: str = "image/jpeg") -> str:
    import base64
    from openai import OpenAI
    b64 = base64.b64encode(data).decode()
    r = OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": "Décris cette image en détail..."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
        ]}],
        max_tokens=1000,
    )
    return r.choices[0].message.content

# Après
def extraire_image_bytes(data: bytes, mime: str = "image/jpeg") -> str:
    from core import appeler_groq_vision
    return appeler_groq_vision(
        data,
        "Décris cette image en détail. Si elle contient du texte, retranscris-le. "
        "Si c'est un graphique, explique les données.",
        mime,
    )
```

### Migration `extraire_audio_tmp()`

```python
# Avant — OpenAI whisper-1
def extraire_audio_tmp(data: bytes, ext: str = ".ogg") -> str:
    from openai import OpenAI
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        with open(tmp_path, "rb") as f:
            t = OpenAI(api_key=OPENAI_API_KEY).audio.transcriptions.create(
                model="whisper-1", file=f, language="fr"
            )
        return t.text[:LIMITE_EXTRACTION]
    finally:
        os.unlink(tmp_path)

# Après — Groq whisper-large-v3
def extraire_audio_tmp(data: bytes, ext: str = ".ogg") -> str:
    from groq import Groq
    from pathlib import Path as _Path
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY manquante dans le fichier .env")
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

### Import cleanup

Après migration, vérifier que `from openai import OpenAI` n'est plus utilisé dans `bot_cloud.py` et le supprimer. `OPENAI_API_KEY` (ligne 27) est déjà gracieux (`os.environ.get`) — le laisser en place (il ne crashe plus).

---

## Changements `titrer_fiches.py`

```python
# Supprimer
from openai import OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# generer_titre() avant — OpenAI avec retry manuel
def generer_titre(idee: str, resume: str) -> str:
    contexte = idee or resume or "Note sans contenu"
    prompt = (...)
    for tentative in range(4):
        try:
            response = client.chat.completions.create(model="gpt-4o-mini", ...)
            return response.choices[0].message.content.strip()...
        except Exception as e:
            if "rate_limit" in str(e).lower() and tentative < 3:
                time.sleep(15 * (tentative + 1))
            else:
                raise

# generer_titre() après — appeler_groq (fallback intégré dans core)
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

La boucle retry est supprimée — le fallback est géré dans `appeler_groq()`. `import time` reste — `time.sleep(1)` ligne 119 est encore utilisé dans `traiter_fiches()`.

---

## Changements `brain_agent.py`

### `raffiner_note(contenu)` — signature modifiée (drop `api_key`)

```python
# Avant
def raffiner_note(contenu: str, api_key: str) -> dict:
    prompt = _PROMPT_RAFFINEMENT.format(contenu=contenu[:8000])
    r = OpenAI(api_key=api_key).chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
    )
    raw = r.choices[0].message.content.strip()
    ...

# Après
def raffiner_note(contenu: str) -> dict:
    from core import appeler_groq
    prompt = _PROMPT_RAFFINEMENT.format(contenu=contenu[:8000])
    messages = [{"role": "user", "content": prompt}]
    raw = appeler_groq(messages, max_tokens=1200).strip()
    ...
```

### `generer_meta_fiche(notes)` — signature modifiée (drop `api_key`)

```python
# Avant
def generer_meta_fiche(notes: list[dict], api_key: str) -> dict:
    ...
    r = OpenAI(api_key=api_key).chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    raw = ...

# Après
def generer_meta_fiche(notes: list[dict]) -> dict:
    from core import appeler_groq
    ...
    messages = [{"role": "user", "content": prompt}]
    raw = appeler_groq(messages, max_tokens=500).strip()
    ...
```

### `vectoriser()` — inchangé (OpenAI embeddings)

```python
def vectoriser(texte: str, api_key: str) -> np.ndarray:
    """Retourne un vecteur numpy float32 (1536,) via text-embedding-3-small."""
    r = OpenAI(api_key=api_key).embeddings.create(
        model="text-embedding-3-small",
        input=texte[:8000],
    )
    return np.array(r.data[0].embedding, dtype=np.float32)
```

### `run_agent()` — mise à jour des appels

```python
# Avant
api_key = os.environ.get("OPENAI_API_KEY", "")
...
refined   = raffiner_note(fiche["content"], api_key)
...
embedding = vectoriser(emb_txt, api_key)  # OpenAI uniquement
...
meta = generer_meta_fiche(cluster, api_key)
emb  = vectoriser(..., api_key)

# Après
api_key = os.environ.get("OPENAI_API_KEY", "")  # conservé pour vectoriser()
...
refined   = raffiner_note(fiche["content"])      # api_key supprimé
...
embedding = vectoriser(emb_txt, api_key)          # inchangé
...
meta = generer_meta_fiche(cluster)               # api_key supprimé
emb  = vectoriser(..., api_key)                   # inchangé
```

Ajouter un commentaire sur `api_key` : `# Utilisé uniquement pour les embeddings OpenAI (Groq n'a pas d'API embeddings)`

---

## Fichiers modifiés

| Fichier | Changements |
|---|---|
| `core.py` | +`appeler_groq()`, +`appeler_groq_vision()` |
| `bot_cloud.py` | Migration image/audio, suppression planning extraction (~8 blocs) |
| `titrer_fiches.py` | Migration OpenAI → `core.appeler_groq()`, simplification retry |
| `brain_agent.py` | Migration 2 fonctions, `vectoriser()` inchangé |

Aucune nouvelle dépendance (`groq` déjà dans `requirements.txt`).
