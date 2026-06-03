# Brain Blocs Resize Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une poignée de redimensionnement drag à la section blocs en bas de l'app, avec persistance de la hauteur en localStorage.

**Architecture:** Poignée HTML en haut de `#blocs-section`, drag natif JS (mousedown/mousemove/mouseup sur document), hauteur sauvegardée en localStorage. `renderBlocs()` modifié pour ne mettre à jour que `.blocs-grid` sans écraser la poignée.

**Tech Stack:** HTML/CSS/JS vanilla, localStorage, Electron.

---

## File structure

| Fichier | Changement |
|---|---|
| `brain_app/index.html` | Ajouter `<div class="blocs-resize-handle" id="blocs-resize-handle">` dans `#blocs-section` |
| `brain_app/style.css` | Modifier `#blocs-section` (height+flex+padding), modifier `.blocs-grid` (flex:1, retirer max-height), ajouter `.blocs-resize-handle` |
| `brain_app/renderer.js` | Ajouter `initBlocsResize()`, modifier `renderBlocs()`, appeler `initBlocsResize()` dans l'IIFE |

---

## Task 1 : HTML + CSS

**Files:**
- Modify: `brain_app/index.html:66`
- Modify: `brain_app/style.css:383-396`

- [ ] **Step 1 : Modifier `index.html` — ajouter la poignée dans `#blocs-section`**

La ligne 66 actuelle est :
```html
      <section id="blocs-section"></section>
```

La remplacer par :
```html
      <section id="blocs-section">
        <div class="blocs-resize-handle" id="blocs-resize-handle"></div>
      </section>
```

- [ ] **Step 2 : Modifier `#blocs-section` dans `style.css`**

La règle actuelle (lignes 383-390) est :
```css
#blocs-section {
  flex-shrink: 0;
  border-top: 1px solid var(--stroke);
  background: rgba(255,255,255,0.015);
  padding: 10px 16px 14px;
  position: relative;
  z-index: 2;
}
```

La remplacer par :
```css
#blocs-section {
  flex-shrink: 0;
  border-top: 1px solid var(--stroke);
  background: rgba(255,255,255,0.015);
  padding: 0 16px 14px;
  position: relative;
  z-index: 2;
  height: 160px;
  display: flex;
  flex-direction: column;
}
```

- [ ] **Step 3 : Modifier `.blocs-grid` dans `style.css`**

La règle actuelle (lignes 392-396) est :
```css
.blocs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  max-height: 200px;
}
```

La remplacer par :
```css
.blocs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  flex: 1;
  min-height: 0;
}
```

- [ ] **Step 4 : Ajouter `.blocs-resize-handle` à la fin de `style.css`**

Ajouter après les styles blocs existants (après `.bloc-add-input.hidden { display: none; }`) :

```css
.blocs-resize-handle {
  flex-shrink: 0;
  height: 14px;
  cursor: ns-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 -16px;
  transition: background .15s var(--ease);
}
.blocs-resize-handle:hover { background: rgba(255,255,255,0.04); }

.blocs-resize-handle::after {
  content: "";
  width: 28px;
  height: 3px;
  border-radius: 99px;
  background: var(--ink-4);
  box-shadow: 0 -5px 0 var(--ink-4), 0 5px 0 var(--ink-4);
  transition: background .15s var(--ease), box-shadow .15s var(--ease);
}
.blocs-resize-handle:hover::after {
  background: var(--ink-3);
  box-shadow: 0 -5px 0 var(--ink-3), 0 5px 0 var(--ink-3);
}
```

- [ ] **Step 5 : Commit**

```powershell
cd "C:\Users\yapa\second_cerveau"
git add brain_app/index.html brain_app/style.css
git commit -m "feat: add blocs resize handle HTML and CSS"
```

---

## Task 2 : renderer.js — initBlocsResize + renderBlocs fix

**Files:**
- Modify: `brain_app/renderer.js`

- [ ] **Step 1 : Ajouter `initBlocsResize()` avant la section `// ── Blocs actions`**

Insérer juste avant le commentaire `// ── Blocs actions` (qui est avant `checkItem`) :

```javascript
// ── Blocs resize ──────────────────────────────────────────────────────────────

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

- [ ] **Step 2 : Modifier `renderBlocs()` pour ne pas écraser la poignée**

La ligne 744 actuelle est :
```javascript
  section.innerHTML = `<div class="blocs-grid">${state.blocs.map(renderBlocCol).join('')}</div>`;
```

La remplacer par :
```javascript
  let grid = section.querySelector('.blocs-grid');
  if (!grid) {
    grid = document.createElement('div');
    grid.className = 'blocs-grid';
    section.appendChild(grid);
  }
  grid.innerHTML = state.blocs.map(renderBlocCol).join('');
```

Cette approche met à jour le contenu du grid sans toucher à la poignée `#blocs-resize-handle` qui est également un enfant de `#blocs-section`.

- [ ] **Step 3 : Appeler `initBlocsResize()` dans l'IIFE d'initialisation**

La section init actuelle (lignes 835-844) est :
```javascript
(async () => {
  render();
  initChat();
  await loadData();
  setInterval(loadData, 2 * 60 * 1000);
  animate('#topbar, #une-head, #featured-cards, #chat-bar, #filter-bar', {
    opacity: [0, 1], translateY: ['8px', '0px'],
    delay: stagger(30), duration: 500, ease: 'outQuart',
  });
})();
```

La remplacer par :
```javascript
(async () => {
  render();
  initChat();
  initBlocsResize();
  await loadData();
  setInterval(loadData, 2 * 60 * 1000);
  animate('#topbar, #une-head, #featured-cards, #chat-bar, #filter-bar', {
    opacity: [0, 1], translateY: ['8px', '0px'],
    delay: stagger(30), duration: 500, ease: 'outQuart',
  });
})();
```

- [ ] **Step 4 : Vérifier manuellement**

Lancer l'app (`brain_start.bat` ou `cd brain_app && npx electron .`). Vérifier :

- [ ] La section blocs est visible avec la poignée (3 traits horizontaux) en haut
- [ ] Glisser la poignée vers le haut agrandit la section
- [ ] Glisser vers le bas réduit la section
- [ ] La section ne passe pas sous 80px ni au-dessus de 400px
- [ ] Quitter et relancer → la hauteur est restaurée
- [ ] Les items des blocs sont toujours cliquables, les boutons `+ ajouter` fonctionnent

- [ ] **Step 5 : Vérifier les tests existants**

```powershell
cd "C:\Users\yapa\second_cerveau"
python -m pytest tests/ -q
```

Expected: 33 tests PASSED (aucune régression — les tests sont côté serveur et non affectés par ce changement frontend).

- [ ] **Step 6 : Commit**

```powershell
git add brain_app/renderer.js
git commit -m "feat: blocs section drag-to-resize with localStorage persistence"
```
