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

## 2026-06-06 — Optimistic update manquant : ancien nom revient après rename

**Symptôme :** Après un rename de domaine, l'ancien nom réapparaît au prochain clic. Les notes du domaine disparaissent de leur section. L'activeFilter pointe vers un nom qui n'existe plus.

**Causes racines (3) :**

1. `patchDomain` mettait à jour `DOMAINS`/`DOMAIN_ORDER` APRÈS le fetch (async). Tout `render()` pendant l'attente du serveur utilisait l'ancien état → flash du vieux nom.

2. `state.notes[i].domaine` n'était jamais mis à jour après un rename. `renderSections` groupait par `n.domaine` (ancien nom) → les notes disparaissaient de la nouvelle section.

3. `state.activeFilter` n'était pas mis à jour → le filtre pointait vers un nom supprimé de `DOMAIN_ORDER`.

**Fix appliqué — Optimistic update synchrone avant le fetch :**

```js
// AVANT le fetch : mise à jour de tout l'état en mémoire
DOMAIN_ORDER[idx] = newName;
DOMAINS[newName]  = { ...DOMAINS[oldName], label: newName };
delete DOMAINS[oldName];
setState({
  notes:        state.notes.map(n => n.domaine === oldName ? { ...n, domaine: newName } : n),
  activeFilter: state.activeFilter === oldName ? newName : state.activeFilter,
});
// Snapshot avant modification pour rollback propre sur erreur serveur
```

**Règle à retenir :**
> Toute opération async qui modifie un nom/clé utilisé dans `state` ET dans `DOMAINS`/`DOMAIN_ORDER` doit faire une mise à jour optimiste synchrone de TOUS ces états avant le fetch, avec rollback sur erreur. Ne jamais attendre le `await` pour mettre à jour le rendu.

---

## 2026-06-06 — `keyup` Space active le `<button>` parent même avec `stopPropagation` sur `keydown`

**Symptôme :** Après avoir bloqué `keydown` propagation, la barre Espace ferme encore l'input inline dans un button. Les clics gauche (sélectionner du texte) continuent aussi de fermer l'édition de manière intermittente.

**Cause racine :**
Les navigateurs activent un `<button>` via Space sur `keyup`, pas `keydown`. Bloquer `keydown` ne suffit pas. De plus, tout `render()` (déclenché par un événement qui bulle) détruit l'input puisqu'il est dans le DOM du button.

La seule solution robuste : **ne jamais injecter d'input interactif à l'intérieur d'un `<button>`**.

**Fix appliqué — Input flottant dans `document.body` :**

```js
// Récupérer la position du label
const rect = label.getBoundingClientRect();
const cs   = window.getComputedStyle(label);

// Input positionné en fixed sur document.body — hors du <button>
input.style.cssText = `position:fixed; left:${rect.left}px; top:${rect.top}px; ...`;
label.style.visibility = 'hidden'; // cache le label sans casser le layout
document.body.appendChild(input);  // HORS du <button>

// Cleanup: input.remove() + label.style.visibility = ''
```

**Règle à retenir :**
> Un `<input>` interactif ne doit jamais être injecté à l'intérieur d'un `<button>`. Les événements clavier et souris créent des effets de bord non-contrôlables (keyup Space, click, focus). Utiliser `getBoundingClientRect()` + `position:fixed` sur `document.body` comme pour un tooltip.

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
