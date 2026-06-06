# Lessons Learned — Second Cerveau

Bugs réels rencontrés, cause racine identifiée, fix appliqué. À lire avant de concevoir une nouvelle feature pour éviter les mêmes pièges.

---

## 2026-06-06 — dblclick impossible dans une barre de filtres qui se re-render

**Symptôme :** Double-cliquer sur un label de domaine dans la filter bar ne déclenche jamais l'input de renommage. Le bug affecte tous les domaines sans exception.

**Cause racine :**
`setState()` appelle `render()` inconditionnellement — même si la valeur n'a pas changé. `render()` appelle `renderFilters()` qui fait `container.innerHTML = ...`, détruisant et recréant tous les éléments DOM. Le navigateur (Chromium/Electron) détecte le double-clic en comparant les **références de nœuds DOM** entre les deux clicks. Comme le DOM est reconstruit après le premier click, le deuxième click tombe sur un **nouvel élément** — le navigateur ne reconnaît pas la séquence comme un double-clic et l'événement `dblclick` ne fire jamais.

**Séquence précise :**
```
click(1) sur .dlabel  →  bulle vers .fpill  →  setState({ activeFilter: X })
                      →  setState appelle render() toujours
                      →  renderFilters() reconstruit le DOM  →  .dlabel est un nouvel objet
click(2) sur NOUVEAU .dlabel  →  navigateur : pas le même nœud  →  dblclick : annulé
```

**Fix appliqué :**
Remplacer `dblclick` par un compteur de clicks au niveau module qui track le **nom de domaine** (string) plutôt qu'une référence d'élément. La string survit aux reconstructions DOM.

```js
let _labelClickTimer  = null;
let _labelClickDomain = null;

// Dans renderFilters(), sur chaque .dlabel :
label.addEventListener('click', e => {
  e.stopPropagation(); // évite le double setState
  const domainName = label.closest('.fpill')?.dataset.filter;

  if (_labelClickTimer && _labelClickDomain === domainName) {
    clearTimeout(_labelClickTimer);
    _labelClickTimer = null;
    _labelClickDomain = null;
    showRename(domainName); // requête le DOM courant, pas un élément capturé
    return;
  }

  _labelClickDomain = domainName;
  _labelClickTimer = setTimeout(() => {
    _labelClickTimer = null;
    _labelClickDomain = null;
  }, 300);
  setState({ activeFilter: domainName }); // setState manuel, propagation stoppée
});
```

**Règle à retenir :**
> Dans une UI qui re-render le DOM à chaque interaction, ne jamais utiliser `dblclick`. Utiliser un compteur de clicks au niveau module en trackant une clé stable (ID, nom) et non une référence d'élément.

**Fichiers concernés :** `brain_app/renderer.js` — fonctions `renderFilters()`, `showRename()`, variables `_labelClickTimer`, `_labelClickDomain`.

**Plan d'origine :** `docs/superpowers/plans/2026-06-05-domain-editing.md` — Task 7.

---

## 2026-06-06 — input inline dans un `<button>` : click et Espace ferment l'édition

**Symptôme :** Un clic gauche à l'intérieur de l'input de renommage ferme l'édition immédiatement. Appuyer sur Espace ferme aussi l'édition.

**Cause racine :**
L'`<input>` est un enfant d'un `<button>`. Dans Chromium/Electron :
- `click` sur l'input **bulle** vers le `<button>` parent, dont le listener appelle `setState` → `render()` → DOM reconstruit → input disparu.
- La barre **Espace** active un `<button>` HTML même si le focus est sur un élément enfant : Chromium fire un `click` sur le bouton → même destruction.

```
click ou Space sur <input>
  → bulle vers <button class="fpill">
  → setState({ activeFilter }) → render() → DOM reconstruit → input disparu
```

**Fix appliqué :**
Deux `stopPropagation` dans la fonction `showRename()` :

```js
input.addEventListener('click', e => e.stopPropagation()); // bloque la remontée du click
input.addEventListener('keydown', async e => {
  e.stopPropagation(); // bloque Espace (et autres touches) vers le <button>
  if (e.key === 'Enter')  { e.preventDefault(); await doConfirm(); }
  if (e.key === 'Escape') { doCancel(); }
});
```

**Règle à retenir :**
> Ne jamais injecter un `<input>` ou `<textarea>` à l'intérieur d'un `<button>` sans bloquer `click` et `keydown` avec `stopPropagation()`. Les deux remontent au bouton et déclenchent ses handlers natifs (click + activation Espace).

**Fichiers concernés :** `brain_app/renderer.js` — fonction `showRename()`.

---

## Template pour les prochaines entrées

```
## YYYY-MM-DD — [titre court du bug]

**Symptôme :** ce que l'utilisateur voit

**Cause racine :** mécanisme exact qui cause le bug

**Fix appliqué :** code ou explication concise

**Règle à retenir :** formulation générale réutilisable

**Fichiers concernés :** ...

**Plan d'origine :** ...
```
