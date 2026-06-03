# Brain Notes — Enrichissement du contenu
**Date :** 2026-06-03  
**Statut :** Approuvé

---

## Objectif

Enrichir le contenu extrait des fiches Dropbox pour afficher dans la modale de l'app Electron : points clés actionnables, contexte d'usage, lien vers la source cliquable. Ajouter la suppression d'une note depuis l'app avec animation.

---

## Problème actuel

Le prompt `raffiner_note` dans `brain_agent.py` compresse chaque fiche en 4 champs très courts (`titre_court` 3-5 mots, `insight_cle` 1 phrase, `resume` 2 phrases, `domaine`). `max_tokens=400`.

Les fiches Joplin ont souvent des sections structurées riches (`POINTS_CLES`, `POURQUOI_GARDER`, `QUAND_RESSORTIR`, `IDEE_PRINCIPALE`) générées lors de la capture Telegram — ces sections sont ignorées par le prompt actuel.

Résultat : l'app perd le contenu le plus utile et reformule generiquement ce qui était déjà bien structuré.

---

## Architecture

### Couche données — `brain.db`

**Nouvelle colonne** (migration auto dans `init_db`) :

```sql
ALTER TABLE notes ADD COLUMN contenu_riche TEXT;
```

`contenu_riche` est un JSON TEXT avec cette structure :

```json
{
  "url_source": "https://...",
  "points_cles": ["bullet 1", "bullet 2", "bullet 3"],
  "pourquoi_garder": "texte ou null",
  "quand_ressortir": "texte ou null"
}
```

Les champs existants (`titre_court`, `insight_cle`, `resume`, `domaine`, `tags`, `score_pertinence`, `embedding`) restent inchangés — ils servent toujours pour les cards, le RAG et le score.

---

### `brain_agent.py`

#### Migration `init_db()`

```python
try:
    conn.execute("ALTER TABLE notes ADD COLUMN contenu_riche TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass  # colonne déjà présente
```

#### Nouveau prompt `_PROMPT_RAFFINEMENT`

`max_tokens` : 400 → 1200.

Instructions clés :
- `titre_court` : utiliser le vrai titre de la source s'il est dans la fiche (ex : ligne `# TITLE`), sinon 5-8 mots descriptifs en français
- Si `POINTS_CLES` / `POURQUOI_GARDER` / `QUAND_RESSORTIR` existent dans la fiche → les extraire **tels quels**, ne pas reformuler
- Si ces sections sont absentes → les générer à partir du contenu
- `url_source` : extraire le premier lien `http(s)` trouvé dans la fiche, ou `null`
- `points_cles` : liste de 3-7 bullets actionnables
- `pourquoi_garder` : 1-2 phrases sur la valeur long terme de la note
- `quand_ressortir` : 1 phrase sur le contexte d'utilisation

Sortie JSON :

```json
{
  "titre_court": "...",
  "insight_cle": "...",
  "resume": "...",
  "domaine": "...",
  "contenu_riche": {
    "url_source": "https://... ou null",
    "points_cles": ["...", "..."],
    "pourquoi_garder": "...",
    "quand_ressortir": "..."
  }
}
```

#### Flag `--reprocess`

```bash
python brain_agent.py --reprocess
```

Comportement : ignore `date_traitement` pour toutes les notes dont `domaine != 'Travail'`. Les notes Travail (planning) ne sont **pas touchées**. Écrase `titre_court`, `insight_cle`, `resume`, `contenu_riche` avec les valeurs du nouveau prompt.

---

### `brain_server.py`

#### `_SELECT_FIELDS`

Ajouter `contenu_riche` à la liste des champs retournés par `/notes`, `/a-la-une`.

#### Nouvel endpoint DELETE

```python
@app.delete("/notes/{note_id}")
def delete_note(note_id: str):
    conn = get_db()
    conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()
    return {"deleted": note_id}
```

Supprime uniquement de `brain.db`. Dropbox et Joplin sont **inchangés**. Si la note supprimée est source d'une méta-fiche, la méta-fiche reste (lien mort affiché silencieusement).

---

### `brain_app/preload.js`

Ajouter l'import `shell` et exposer `openUrl` :

```javascript
const { contextBridge, shell } = require('electron');

contextBridge.exposeInMainWorld('BRAIN_API_URL', 'http://127.0.0.1:7842');
contextBridge.exposeInMainWorld('openUrl', (url) => {
  if (/^https?:\/\//.test(url)) shell.openExternal(url);
});
```

Validation : seules les URLs `http://` et `https://` sont autorisées.

---

### `brain_app/renderer.js`

#### `mapNote()` — parse `contenu_riche`

```javascript
const cr = (() => {
  try { return JSON.parse(raw.contenu_riche || '{}'); }
  catch { return {}; }
})();
return {
  ...raw,
  id: String(raw.id),
  titre: raw.titre_court || '—',
  insight: raw.insight_cle || '',
  est_meta: Boolean(raw.est_meta_fiche),
  liens: parseLiens(raw.sources_ids),
  parsedTags: parseTags(raw.tags),
  _days: daysAgo(raw.date_capture),
  url_source: cr.url_source || null,
  points_cles: Array.isArray(cr.points_cles) ? cr.points_cles : [],
  pourquoi_garder: cr.pourquoi_garder || null,
  quand_ressortir: cr.quand_ressortir || null,
};
```

#### `ICONS` — ajout de `trash` et `externalLink`

SVG inline monoline `currentColor`.

#### `renderModal()` — sections enrichies

Structure après `resume` :

```
[insight-box]
RÉSUMÉ
[resume text]

POINTS CLÉS          ← si points_cles.length > 0
• bullet 1
• bullet 2
...

POURQUOI GARDER      ← si pourquoi_garder
[texte]

QUAND RESSORTIR      ← si quand_ressortir
[texte]

TAGS
[pills]

[date] [index] [pertinence]  [🗑️ icône poubelle]
```

Lien source sous le titre dans `mhead` :
```html
<a class="source-link" onclick="window.openUrl('${url}')">↗ Ouvrir la source</a>
```
Visible uniquement si `note.url_source` est non-null.

#### `deleteNote(note)` — animation + suppression

```javascript
async function deleteNote(note) {
  // 1. Animer modale out
  await animate('#modal-scrim .modal', {
    scale: [1, 0.95], opacity: [1, 0], duration: 280, ease: 'outQuart'
  }).finished;
  await animate('#modal-scrim', {
    opacity: [1, 0], duration: 200, ease: 'outQuart'
  }).finished;

  // 2. Animer card out dans la grille
  const card = document.querySelector(`[data-id="${note.id}"]`);
  if (card) {
    await animate(card, {
      translateX: [0, -12], opacity: [1, 0], duration: 220, ease: 'outCubic'
    }).finished;
  }

  // 3. Appel API DELETE
  await fetch(`${API}/notes/${note.id}`, { method: 'DELETE' });

  // 4. Mettre à jour le state (pas de reload complet)
  setState({
    openNote: null,
    notes: state.notes.filter(n => n.id !== note.id),
    featured: state.featured.filter(n => n.id !== note.id),
  });
}
```

Durée totale : ~500ms. Pas de confirmation (Dropbox intact).

---

### `brain_app/style.css`

3 ajouts :

```css
/* Lien source dans la modale */
.source-link {
  display: inline-flex; align-items: center; gap: 5px;
  font-family: var(--font-mono); font-size: 10.5px;
  color: var(--ink-3); cursor: pointer; margin-bottom: 4px;
  transition: color .2s var(--ease);
}
.source-link:hover { color: var(--ink-2); }

/* Points clés */
.points-cles { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.points-cles li { display: flex; gap: 8px; font-size: 13px; line-height: 1.5; color: var(--ink-2); }
.points-cles li::before { content: "•"; color: var(--accent); flex: 0 0 auto; }

/* Bouton suppression */
.deletebtn {
  margin-left: auto; background: none; border: none; cursor: pointer;
  color: var(--ink-4); padding: 4px; border-radius: var(--r-sm);
  transition: color .2s var(--ease), background .2s var(--ease);
  display: flex; align-items: center;
}
.deletebtn:hover { color: oklch(0.65 0.2 25); background: color-mix(in oklch, oklch(0.65 0.2 25) 12%, transparent); }
.deletebtn svg { width: 14px; height: 14px; }
```

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `brain_agent.py` | Migration `init_db`, nouveau prompt, `max_tokens=1200`, flag `--reprocess` |
| `brain_server.py` | `_SELECT_FIELDS` + `contenu_riche`, endpoint `DELETE /notes/{id}` |
| `brain_app/preload.js` | Import `shell`, expose `openUrl` |
| `brain_app/renderer.js` | `mapNote`, `renderModal`, `deleteNote`, icônes |
| `brain_app/style.css` | `.source-link`, `.points-cles`, `.deletebtn` |

## Hors scope

- Suppression depuis Dropbox/Joplin
- Confirmation avant suppression
- Édition du contenu depuis l'app
- Support de plusieurs URLs par fiche
