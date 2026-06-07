# Spec — Constellation : drag, clic, persistance

**Date :** 2026-06-07  
**Fichier cible :** `brain_app/renderer.js`  
**Statut :** Approuvé

---

## Contexte

La vue Constellation affiche les notes comme des nodes positionnés sur un canvas avec des edges Bézier reliant les notes liées. Trois problèmes identifiés :

1. Les nodes ne sont pas déplaçables individuellement — seul le pan global fonctionne.
2. Cliquer sur un node pour ouvrir la modale est cassé : `pointerdown` sur un node déclenche aussi le pan, tout tremblement de souris déplace la vue au lieu d'ouvrir la note.
3. La disposition est recalculée à chaque ouverture — les positions ne persistent pas.

Cause racine supplémentaire : `mouseenter` sur un node appelle `renderConstellation()` qui reconstruit tout le `innerHTML`, ce qui est coûteux et crée des effets de bord sur les events pointer.

---

## Approche retenue : Option A — Extension directe

Trois changements ciblés dans `renderer.js`, sans réécriture de l'architecture.

---

## Section 1 — Séparation drag node / pan

### Nouvel état module

```js
let nodeDrag = null;
// { id, startClientX, startClientY, origX, origY, moved: false }

let constellationPositions = {};
// { [noteId]: { x, y } } — chargé depuis localStorage
```

`constellationPositions` est chargé une seule fois à l'initialisation du module :
```js
constellationPositions = JSON.parse(
  localStorage.getItem('brain_constellation_positions') || '{}'
);
```

### pointerdown sur `.cnode`

```js
el.addEventListener('pointerdown', e => {
  e.stopPropagation(); // empêche la bulle vers constel-inner → pan ne démarre pas
  // Priorité aux positions sauvegardées (post-drag) sur les positions calculées
  const currentPos = constellationPositions[el.dataset.cid] || pos[el.dataset.cid];
  nodeDrag = {
    id: el.dataset.cid,
    el,
    startClientX: e.clientX,
    startClientY: e.clientY,
    origX: currentPos.x,
    origY: currentPos.y,
    moved: false,
  };
  el.setPointerCapture(e.pointerId); // capture les events suivants sur ce node
});
```

### pointermove sur `constel-inner`

```js
inner.addEventListener('pointermove', e => {
  if (nodeDrag) {
    const dx = e.clientX - nodeDrag.startClientX;
    const dy = e.clientY - nodeDrag.startClientY;
    if (Math.abs(dx) > 6 || Math.abs(dy) > 6) nodeDrag.moved = true;
    const newX = nodeDrag.origX + dx;
    const newY = nodeDrag.origY + dy;
    nodeDrag.el.style.left = newX + 'px';
    nodeDrag.el.style.top  = newY + 'px';
    return;
  }
  if (!constellationDrag) return;
  // pan existant inchangé
  constellationPan = { x: e.clientX - constellationDrag.x, y: e.clientY - constellationDrag.y };
  document.getElementById('constel-world').style.transform =
    `translate(${constellationPan.x}px,${constellationPan.y}px)`;
});
```

### pointerup sur `constel-inner`

```js
inner.addEventListener('pointerup', e => {
  if (nodeDrag) {
    if (!nodeDrag.moved) {
      // c'était un clic → ouvrir la modale
      const note = state.filteredList.find(n => n.id === nodeDrag.id);
      if (note) openModal(note);
    } else {
      // c'était un drag → calculer et sauvegarder la position finale
      const dx = e.clientX - nodeDrag.startClientX;
      const dy = e.clientY - nodeDrag.startClientY;
      const newX = nodeDrag.origX + dx;
      const newY = nodeDrag.origY + dy;
      constellationPositions[nodeDrag.id] = { x: newX, y: newY };
      localStorage.setItem(
        'brain_constellation_positions',
        JSON.stringify(constellationPositions)
      );
      nodeDrag = null;
      renderConstellation(); // met à jour les edges SVG vers la nouvelle position
      return;
    }
    nodeDrag = null;
    return;
  }
  constellationDrag = null;
});
```

Note : `pointerleave` sur `constel-inner` remet uniquement `constellationDrag = null` (inchangé). Si `nodeDrag` est actif et que le pointeur quitte le inner, `setPointerCapture` garantit que les events continuent d'arriver sur le node.

---

## Section 2 — Hover sans re-render

### Suppression

Retirer les handlers `mouseenter/mouseleave` qui appellent `renderConstellation()`.

### Ajout de data-attrs sur les edges SVG

Dans la génération des paths SVG (`edgeSvg`) :
```js
return `<path class="edge" data-ea="${e.a}" data-eb="${e.b}" ... d="..."/>`;
```

### Nouveaux handlers hover (sans re-render)

```js
el.addEventListener('mouseenter', () => {
  const id = el.dataset.cid;
  document.querySelectorAll(`.edge[data-ea="${id}"], .edge[data-eb="${id}"]`)
    .forEach(path => path.classList.add('lit'));
});
el.addEventListener('mouseleave', () => {
  document.querySelectorAll('.edge.lit')
    .forEach(path => path.classList.remove('lit'));
});
```

Le CSS `.edge.lit` existant (stroke coloré + glow via `--accent`) fonctionne sans modification.

**Suppression** de la variable `constellationHover` et de son usage dans `renderConstellation()` — devenue inutile.

---

## Section 3 — Persistance localStorage

### Application des positions sauvegardées

Dans `renderConstellation()`, après `computeLayout(notes, w, h)` :

```js
const { pos, edges } = computeLayout(notes, w, h);

// Surcharger avec les positions sauvegardées
notes.forEach(n => {
  if (constellationPositions[n.id]) {
    pos[n.id] = constellationPositions[n.id];
  }
});
```

Les notes sans position sauvegardée gardent la position calculée par `computeLayout`.  
Les nouvelles notes apparaissent à leur position calculée jusqu'au premier drag.

### Comportement sur filtre

Les positions sont globales (par `note.id`). Quand un filtre est actif, seuls les nodes visibles sont rendus, mais leurs positions sauvegardées sont respectées. Aucune position n'est perdue lors d'un changement de filtre.

---

## Fichiers modifiés

| Fichier | Modifications |
|---|---|
| `brain_app/renderer.js` | Variables `nodeDrag`, `constellationPositions` ; logique pointerdown/move/up ; handlers hover ; application positions dans renderConstellation |

Aucun changement CSS requis. Aucun changement côté serveur ou `brain_agent.py`.

---

## Non inclus dans ce design

- Bouton "Reset layout" (positions définitives, pas de réinitialisation)
- Zoom in/out sur la constellation
- Animation de snap des nodes lors du drop
