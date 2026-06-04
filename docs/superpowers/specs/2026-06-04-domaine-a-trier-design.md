# Spec : Domaine "À trier" + changement de domaine depuis la modale

**Date :** 2026-06-04  
**Scope :** `brain_agent.py`, `brain_server.py`, `brain_app/renderer.js`, `brain_app/index.html`, `brain_app/style.css`

---

## Problème

Quand le LLM ne reconnaît pas clairement le domaine d'une note capturée, la note tombe silencieusement en "Projets perso" (fallback dur dans `brain_agent.py`). Aucun moyen visible de savoir qu'une note est mal classée, et aucun moyen de changer son domaine depuis l'app Electron.

---

## Objectifs

1. Créer un domaine **"À trier"** qui sert de fallback LLM et de catégorie de triage manuel.
2. Remplacer la section **"À la une"** par une section **"À trier"** en haut de la vue Grille — visible quand des notes l'attendent, masquée sinon.
3. Permettre de **changer le domaine d'une note** depuis la modale, en cliquant sur le label domaine dans le header.

---

## Approche retenue

**Approche A — Minimal** : aucune migration de données, aucun nouvel endpoint API. Les notes existantes en "Projets perso" restent intactes ; seules les futures notes ambiguës atterrissent en "À trier".

---

## Design détaillé

### 1. `brain_agent.py`

**`DOMAINS` list (ligne 18) :**
```python
DOMAINS = [
    "Travail", "Apprentissage", "Projets perso",
    "Jeux vidéos", "Plantes", "Organisation TDAH", "À trier",
]
```

**Fallback domaine (ligne 166-167) :**
```python
# Avant
if domaine not in DOMAINS:
    domaine = "Projets perso"

# Après
if domaine not in DOMAINS:
    domaine = "À trier"
```

**Prompt LLM `PROMPT_ANALYSE` (ligne 130) :**  
Ajouter `"À trier"` comme 7e valeur dans l'énumération des domaines valides. Le LLM peut l'utiliser lui-même quand le contenu est ambigu.

```
"domaine": "<exactement un parmi : Travail | Apprentissage | Projets perso | Jeux vidéos | Plantes | Organisation TDAH | À trier>",
```

**`generer_meta_fiche()` (ligne 304-305) :**  
Inchangé — le fallback des méta-fiches hérite du domaine de la première note source, pas "À trier".

---

### 2. `brain_server.py`

**`PATCH /notes/:id` étendu :**

Actuellement n'accepte que `titre_court`. Le endpoint est étendu pour accepter aussi `domaine`.

Importer `DOMAINS` depuis `brain_agent` (déjà importé dans le fichier) plutôt que de redéfinir une liste séparée — source unique de vérité.

```python
from brain_agent import init_db as _init_db, get_dropbox, DOMAINS as VALID_DOMAINS

@app.patch("/notes/{note_id}")
def patch_note(note_id: str, body: dict):
    titre  = body.get("titre_court", "").strip()
    domaine = body.get("domaine", "").strip()

    if not titre and not domaine:
        raise HTTPException(status_code=422, detail="titre_court ou domaine requis")
    if domaine and domaine not in VALID_DOMAINS:
        raise HTTPException(status_code=422, detail=f"domaine invalide : {domaine}")

    conn = get_db()
    if titre:
        conn.execute(
            "UPDATE notes SET titre_court = ?, titre_modifie = 1 WHERE id = ?",
            (titre, note_id)
        )
    if domaine:
        conn.execute(
            "UPDATE notes SET domaine = ? WHERE id = ?",
            (domaine, note_id)
        )
    conn.commit()
    conn.close()
    return {"updated": note_id, "titre_court": titre or None, "domaine": domaine or None}
```

Pas de nouvel endpoint. La section "À trier" côté frontend filtre depuis `state.notes` (déjà chargé).

---

### 3. `brain_app/style.css`

Ajouter dans les design tokens (`:root`) :
```css
--d-trier: oklch(0.75 0.08 55);
```
Couleur : ambre neutre/désaturé — distinctif sans être criard, signale l'état "en attente".

---

### 4. `brain_app/renderer.js`

#### 4a. `DOMAINS` constant
```javascript
'À trier': { key: 'trier', label: 'À trier', color: 'var(--d-trier)' },
```
Ajouté en fin de `DOMAIN_ORDER` :
```javascript
const DOMAIN_ORDER = ['Travail', 'Apprentissage', 'Projets perso', 'Jeux vidéos', 'Plantes', 'Organisation TDAH', 'À trier'];
```

#### 4b. State : suppression de `featured`
- Supprimer `featured: []` du state initial.
- Supprimer l'appel `/a-la-une` dans `loadData()`.
- Supprimer `featured: featuredRaw.map(mapNote)` du `setState()` dans `loadData()`.
- **`deleteNote()`** : supprimer la ligne `featured: state.featured.filter(...)` — référence orpheline.
- **`patchTitre()`** : supprimer la ligne `featured: state.featured.map(...)` — référence orpheline.

#### 4c. `renderATrier()` remplace `renderFeatured()`
```
renderATrier() :
  trier = state.notes.filter(n => n.domaine === 'À trier')
  
  si trier.length === 0 :
    → masquer #une-head et vider #featured-cards, return
  
  sinon :
    → afficher #une-head
    → construire les fcards avec --accent: var(--d-trier)
    → binder les clics → openModal()
    → animer (stagger) si !state._silent
```

La section se masque automatiquement quand il n'y a plus de notes "À trier" — elle disparaît au fur et à mesure qu'on reclasse.

**Double affichage assumé :** les notes "À trier" apparaissent à la fois dans cette section du haut (zone d'appel à l'action) ET dans la liste principale sous leur section de domaine. C'est identique au comportement des notes normales dans les anciennes fcards "À la une". Le filtre "À trier" dans la filter bar permet aussi de les isoler.

#### 4d. Picker de domaine dans la modale

**Structure HTML insérée dans le header de la modale :**
```html
<div class="domrow" id="modal-domrow" style="cursor:pointer">
  <span class="ddot"></span>
  <span class="domlabel">${dom.label}</span>
  <span class="domain-edit-hint">✎</span>
</div>
<div class="domain-picker hidden" id="modal-domain-picker">
  <!-- pills pour chaque domaine de DOMAIN_ORDER -->
</div>
```

**Comportement :**
- Clic sur `.domrow` → toggle `.hidden` sur `#modal-domain-picker`
- Clic sur une pill → `patchDomaine(note, newDomaine)` + ferme le picker
- Clic en dehors du picker → ferme le picker (listener `mousedown` sur `document`, ignoré si la cible est dans `#modal-domain-picker` ou `#modal-domrow`)
- Le domaine actif est mis en surbrillance (`active` class)

#### 4e. `patchDomaine(note, newDomaine)`
```
patchDomaine(note, newDomaine) :
  si newDomaine === note.domaine → return (no-op)
  
  PATCH /notes/:id { domaine: newDomaine }
  
  si succès :
    update = n => n.id === note.id ? { ...n, domaine: newDomaine } : n
    setState({
      notes:    state.notes.map(update),
      openNote: { ...state.openNote, domaine: newDomaine }
    })
    → setState() re-render la modale avec le nouveau domaine
```

---

### 5. `brain_app/index.html`

Mettre à jour le label "À la une" → "À trier" et remplacer l'icône étoile par une icône de tri :
```html
<!-- Avant -->
<span class="star" id="star-icon"></span>
<span class="uppercase-label" style="color:var(--d-une)">À la une</span>

<!-- Après -->
<span class="trier-icon" id="trier-icon"></span>
<span class="uppercase-label" style="color:var(--d-trier)">À trier</span>
```

L'icône SVG de tri est injectée par `renderTopbar()` (ou une nouvelle fonction `renderATrier()`), comme c'est déjà le cas pour `star-icon` et `spark-icon`.

---

## Flux de données

```
Capture Telegram → brain_agent.py
  LLM produit domaine inconnu → fallback "À trier"
  Note stockée en DB avec domaine = "À trier"

App Electron (toutes les 2 min ou refresh manuel)
  loadData() → GET /notes?limit=200
  state.notes inclut les notes "À trier"

renderATrier()
  filtre state.notes → affiche section en haut si non vide

Utilisateur ouvre une note "À trier"
  Clique sur le label domaine dans la modale
  → picker s'ouvre avec les 7 domaines
  Clique "Apprentissage"
  → PATCH /notes/:id { domaine: "Apprentissage" }
  → setState() → re-render modale + section "À trier" (la note disparaît)
```

---

## Ce qui n'est PAS dans ce scope

- Migration des notes existantes en "Projets perso" vers "À trier"
- Changement du titre et du domaine dans un seul appel PATCH simultané (les deux champs sont indépendants dans l'UI)
- Tests automatisés pour les nouveaux cas (`test_server.py` à créer séparément)

---

## Checklist d'implémentation

- [ ] `brain_agent.py` : DOMAINS + fallback + prompt
- [ ] `brain_server.py` : PATCH étendu + VALID_DOMAINS
- [ ] `style.css` : `--d-trier`
- [ ] `renderer.js` : DOMAINS/DOMAIN_ORDER + state + renderATrier + patchDomaine + picker modale
- [ ] `index.html` : label + icône
