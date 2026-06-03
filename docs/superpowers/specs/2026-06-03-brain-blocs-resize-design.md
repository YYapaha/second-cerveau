# Brain — Redimensionnement de la section blocs
**Date :** 2026-06-03
**Statut :** Approuvé

---

## Objectif

Permettre à l'utilisateur de redimensionner la section blocs (Travail / Projets / Bloc-notes) en bas de l'écran en faisant glisser une poignée horizontale. La taille choisie est mémorisée en `localStorage`.

---

## Comportement

**Hauteur initiale :** `localStorage.getItem('blocs-height')` → si absent, défaut `160px`.

**Contraintes :** min `80px`, max `400px`.

**Logique de drag (`initBlocsResize()` dans `renderer.js`) :**
1. `mousedown` sur `.blocs-resize-handle` → mémorise `startY = e.clientY` et `startHeight = #blocs-section.offsetHeight`
2. `mousemove` sur `document` → `newHeight = clamp(startHeight - (e.clientY - startY), 80, 400)` → applique `#blocs-section.style.height`
3. `mouseup` sur `document` → retire les listeners, `localStorage.setItem('blocs-height', currentHeight)`

Tirer vers le **haut** agrandit la section (le contenu est en bas, la poignée est en haut).

**Pendant le drag :** `document.body.style.cursor = 'ns-resize'` + `document.body.style.userSelect = 'none'` → reset à `mouseup`.

---

## CSS

### `#blocs-section` — modifications

Remplacer `max-height: 200px` sur `.blocs-grid` par un contrôle de hauteur sur la section elle-même :

```css
#blocs-section {
  flex-shrink: 0;
  border-top: 1px solid var(--stroke);
  background: rgba(255,255,255,0.015);
  padding: 0 16px 14px;   /* ← padding-top: 0, la poignée occupe le haut */
  position: relative;
  z-index: 2;
  height: 160px;           /* ← hauteur par défaut, overridée par JS */
  display: flex;
  flex-direction: column;
}
```

### `.blocs-grid` — retirer `max-height`

```css
.blocs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  flex: 1;          /* ← prend l'espace restant dans la section */
  min-height: 0;    /* ← nécessaire pour que flex: 1 fonctionne dans une colonne */
}
```

### Nouvelle classe `.blocs-resize-handle`

```css
.blocs-resize-handle {
  flex-shrink: 0;
  height: 14px;
  cursor: ns-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 -16px;  /* étend jusqu'aux bords du padding parent */
  transition: background .15s var(--ease);
}
.blocs-resize-handle:hover { background: rgba(255,255,255,0.04); }

.blocs-resize-handle::after {
  content: "";
  width: 28px;
  height: 3px;
  border-radius: 99px;
  background: var(--ink-4);
  transition: background .15s var(--ease);
  box-shadow: 0 -5px 0 var(--ink-4), 0 5px 0 var(--ink-4); /* 3 traits */
}
.blocs-resize-handle:hover::after { background: var(--ink-3); box-shadow: 0 -5px 0 var(--ink-3), 0 5px 0 var(--ink-3); }
```

---

## HTML

Ajouter `.blocs-resize-handle` comme **premier enfant** de `#blocs-section`, avant `.blocs-grid` (qui est rendu par JS dans `renderBlocs()`).

`index.html` :
```html
<section id="blocs-section">
  <div class="blocs-resize-handle" id="blocs-resize-handle"></div>
</section>
```

Le `.blocs-grid` est injecté par `renderBlocs()` dans `renderer.js` après la poignée.

---

## renderer.js

### `initBlocsResize()`

```javascript
function initBlocsResize() {
  const section = document.getElementById('blocs-section');
  const handle  = document.getElementById('blocs-resize-handle');
  if (!section || !handle) return;

  // Appliquer la hauteur sauvegardée
  const saved = parseInt(localStorage.getItem('blocs-height'), 10);
  if (saved >= 80 && saved <= 400) section.style.height = saved + 'px';

  let startY = 0, startH = 0, dragging = false;

  handle.addEventListener('mousedown', e => {
    e.preventDefault();
    dragging = true;
    startY = e.clientY;
    startH = section.offsetHeight;
    document.body.style.cursor     = 'ns-resize';
    document.body.style.userSelect = 'none';
  });

  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    const newH = Math.max(80, Math.min(400, startH - (e.clientY - startY)));
    section.style.height = newH + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor     = '';
    document.body.style.userSelect = '';
    localStorage.setItem('blocs-height', section.offsetHeight);
  });
}
```

### Appel dans l'IIFE d'initialisation

Appeler `initBlocsResize()` juste après `initChat()` :

```javascript
(async () => {
  render();
  initChat();
  initBlocsResize();   // ← ajouter
  await loadData();
  ...
})();
```

### `renderBlocs()` — ne pas écraser la poignée

`renderBlocs()` fait actuellement `section.innerHTML = ...`. Cela effacerait la poignée. Modifier pour ne remplacer que `.blocs-grid` :

```javascript
function renderBlocs() {
  const section = document.getElementById('blocs-section');
  if (!section || !state.blocs || state.blocs.length === 0) return;

  // Mettre à jour ou créer le grid sans toucher à la poignée
  let grid = section.querySelector('.blocs-grid');
  if (!grid) {
    grid = document.createElement('div');
    grid.className = 'blocs-grid';
    section.appendChild(grid);
  }
  grid.innerHTML = state.blocs.map(renderBlocCol).join('');

  // ... reste inchangé (event delegation, boutons +)
}
```

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `brain_app/index.html` | Ajouter `<div class="blocs-resize-handle" id="blocs-resize-handle">` dans `#blocs-section` |
| `brain_app/style.css` | `.blocs-resize-handle`, modifier `#blocs-section` (height+flex), modifier `.blocs-grid` (flex:1, retirer max-height) |
| `brain_app/renderer.js` | `initBlocsResize()`, appel dans IIFE, modifier `renderBlocs()` pour ne pas écraser la poignée |

---

## Hors scope

- Redimensionnement par touch/mobile
- Bouton "reset taille"
- Hauteur minimum différente par bloc
