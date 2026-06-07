# Constellation Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre les nodes de la constellation déplaçables individuellement, corriger l'ouverture de la modale au clic, et persister les positions entre sessions dans localStorage.

**Architecture:** Trois changements ciblés dans `brain_app/renderer.js` uniquement : (1) remplacement du hover full-re-render par manipulation de classes CSS sur les edges SVG ; (2) ajout de `constellationPositions` chargé depuis localStorage et appliqué après `computeLayout` ; (3) ajout de `nodeDrag` avec logique pointerdown/pointermove/pointerup qui distingue clic (< 6 px) de drag (≥ 6 px), avec sauvegarde localStorage à chaque drop.

**Tech Stack:** JavaScript ES modules, Electron 35, DOM Pointer Events API, localStorage.

---

## Fichiers modifiés

- Modify: `brain_app/renderer.js` — section Constellation uniquement (lignes ~862-988)

Aucun changement CSS, aucun changement serveur, aucun changement Python.

---

### Task 1: Fix hover — CSS class toggle sur les edges SVG

Supprime le `renderConstellation()` déclenché au survol (cause de rebuilds coûteux et d'effets de bord sur les events pointer). Remplace par manipulation directe de classes CSS sur les paths SVG.

**Files:**
- Modify: `brain_app/renderer.js`

- [ ] **Step 1: Supprimer la variable `constellationHover`**

Dans `brain_app/renderer.js`, repérer le bloc de variables module (~ligne 862) et remplacer :

```js
let constellationPan = { x: 0, y: 0 };
let constellationDrag = null;
let constellationHover = null;
```

Par :

```js
let constellationPan = { x: 0, y: 0 };
let constellationDrag = null;
```

- [ ] **Step 2: Mettre à jour la génération edgeSvg et nodesHtml dans `renderConstellation`**

Remplacer le bloc (lignes ~918–942) :

```js
  const { pos, edges } = computeLayout(notes, w, h);
  const pan = constellationPan;
  const hov = constellationHover;

  const edgeSvg = edges.map(e => {
    const a = pos[e.a], b = pos[e.b];
    if (!a || !b) return '';
    const mx = (a.x + b.x) / 2;
    const my = (a.y + b.y) / 2 - 28;
    const lit = hov && (e.a === hov || e.b === hov);
    const accent = lit ? `style="--accent:${e.color}"` : '';
    return `<path class="edge${lit ? ' lit' : ''}" ${accent} d="M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}"/>`;
  }).join('');

  const nodesHtml = notes.map(n => {
    const p = pos[n.id];
    if (!p) return '';
    const dom = domainConfig(n.domaine);
    const isHov = hov === n.id;
    return `<div class="cnode${n.est_meta ? ' meta' : ''}${isHov ? ' active' : ''}"
      data-cid="${n.id}"
      style="left:${p.x}px;top:${p.y}px;--accent:${dom.color}">
      <div class="bubble"><span class="ddot"></span><span class="ct">${n.titre}</span></div>
    </div>`;
  }).join('');
```

Par :

```js
  const { pos, edges } = computeLayout(notes, w, h);
  const pan = constellationPan;

  const edgeSvg = edges.map(e => {
    const a = pos[e.a], b = pos[e.b];
    if (!a || !b) return '';
    const mx = (a.x + b.x) / 2;
    const my = (a.y + b.y) / 2 - 28;
    return `<path class="edge" data-ea="${e.a}" data-eb="${e.b}" style="--accent:${e.color}" d="M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}"/>`;
  }).join('');

  const nodesHtml = notes.map(n => {
    const p = pos[n.id];
    if (!p) return '';
    const dom = domainConfig(n.domaine);
    return `<div class="cnode${n.est_meta ? ' meta' : ''}"
      data-cid="${n.id}"
      style="left:${p.x}px;top:${p.y}px;--accent:${dom.color}">
      <div class="bubble"><span class="ddot"></span><span class="ct">${n.titre}</span></div>
    </div>`;
  }).join('');
```

- [ ] **Step 3: Remplacer les handlers du forEach `.cnode` par des handlers hover légers**

Remplacer (lignes ~974-988) :

```js
  view.querySelectorAll('.cnode').forEach(el => {
    el.addEventListener('mouseenter', () => {
      constellationHover = el.dataset.cid;
      renderConstellation();
    });
    el.addEventListener('mouseleave', () => {
      constellationHover = null;
      renderConstellation();
    });
    el.addEventListener('click', e => {
      e.stopPropagation();
      const note = state.filteredList.find(n => n.id === el.dataset.cid);
      if (note) openModal(note);
    });
  });
```

Par :

```js
  view.querySelectorAll('.cnode').forEach(el => {
    el.addEventListener('mouseenter', () => {
      const id = el.dataset.cid;
      document.querySelectorAll(`.edge[data-ea="${id}"], .edge[data-eb="${id}"]`)
        .forEach(path => path.classList.add('lit'));
    });
    el.addEventListener('mouseleave', () => {
      document.querySelectorAll('.edge.lit').forEach(path => path.classList.remove('lit'));
    });
    el.addEventListener('click', e => {
      e.stopPropagation();
      const note = state.filteredList.find(n => n.id === el.dataset.cid);
      if (note) openModal(note);
    });
  });
```

- [ ] **Step 4: Lancer l'app et vérifier le hover**

```bash
cd brain_app && npm start
```

Vérifications :
- Vue Constellation → survoler un node → les edges connectés à ce node s'illuminent (bordure colorée), les autres restent gris
- Quitter le survol → les edges reprennent leur état normal
- Cliquer sur un node → la modale s'ouvre (comportement identique à avant)
- Aucun flash DOM au survol (pas de rebuild visible)

- [ ] **Step 5: Commit**

```bash
git add brain_app/renderer.js
git commit -m "fix: constellation hover via CSS class toggle sur edges SVG, sans DOM rebuild"
```

---

### Task 2: Infrastructure de persistance localStorage

Charge les positions sauvegardées au démarrage du module et les applique dans `renderConstellation` en surcharge des positions calculées par `computeLayout`.

**Files:**
- Modify: `brain_app/renderer.js`

- [ ] **Step 1: Ajouter `constellationPositions` aux variables module**

Remplacer :

```js
let constellationPan = { x: 0, y: 0 };
let constellationDrag = null;
```

Par :

```js
let constellationPan = { x: 0, y: 0 };
let constellationDrag = null;
let constellationPositions = JSON.parse(localStorage.getItem('brain_constellation_positions') || '{}');
```

- [ ] **Step 2: Appliquer les positions sauvegardées après `computeLayout` dans `renderConstellation`**

Remplacer :

```js
  const { pos, edges } = computeLayout(notes, w, h);
  const pan = constellationPan;
```

Par :

```js
  const { pos, edges } = computeLayout(notes, w, h);
  notes.forEach(n => {
    if (constellationPositions[n.id]) pos[n.id] = constellationPositions[n.id];
  });
  const pan = constellationPan;
```

- [ ] **Step 3: Lancer l'app et vérifier**

```bash
cd brain_app && npm start
```

Vérifications :
- Vue Constellation → layout normal (aucune position sauvegardée, `computeLayout` s'applique à tout)
- Ouvrir DevTools Electron (Ctrl+Shift+I) → onglet Application → Local Storage → `http://localhost` ou `file://`
- `brain_constellation_positions` absent ou vide `{}` — aucune erreur JS dans la console

- [ ] **Step 4: Commit**

```bash
git add brain_app/renderer.js
git commit -m "feat: charger et appliquer les positions constellation depuis localStorage"
```

---

### Task 3: Drag individuel des nodes + clic pour ouvrir la modale

Ajoute `nodeDrag` : `pointerdown` sur un node stoppe la propagation (empêche le pan), capture le pointeur, démarre le tracking. `pointermove` déplace le node directement via style. `pointerup` : si déplacement < 6 px → ouvre modale ; sinon → sauvegarde position et reconstruit les edges.

**Files:**
- Modify: `brain_app/renderer.js`

- [ ] **Step 1: Ajouter `nodeDrag` aux variables module**

Remplacer :

```js
let constellationPan = { x: 0, y: 0 };
let constellationDrag = null;
let constellationPositions = JSON.parse(localStorage.getItem('brain_constellation_positions') || '{}');
```

Par :

```js
let constellationPan = { x: 0, y: 0 };
let constellationDrag = null;
let constellationPositions = JSON.parse(localStorage.getItem('brain_constellation_positions') || '{}');
let nodeDrag = null;
```

- [ ] **Step 2: Mettre à jour `pointermove` sur `constel-inner` pour gérer `nodeDrag` en priorité**

Remplacer :

```js
  inner.addEventListener('pointermove', e => {
    if (!constellationDrag) return;
    constellationPan = { x: e.clientX - constellationDrag.x, y: e.clientY - constellationDrag.y };
    document.getElementById('constel-world').style.transform =
      `translate(${constellationPan.x}px,${constellationPan.y}px)`;
  });
```

Par :

```js
  inner.addEventListener('pointermove', e => {
    if (nodeDrag) {
      const dx = e.clientX - nodeDrag.startClientX;
      const dy = e.clientY - nodeDrag.startClientY;
      if (Math.abs(dx) > 6 || Math.abs(dy) > 6) nodeDrag.moved = true;
      nodeDrag.el.style.left = (nodeDrag.origX + dx) + 'px';
      nodeDrag.el.style.top  = (nodeDrag.origY + dy) + 'px';
      return;
    }
    if (!constellationDrag) return;
    constellationPan = { x: e.clientX - constellationDrag.x, y: e.clientY - constellationDrag.y };
    document.getElementById('constel-world').style.transform =
      `translate(${constellationPan.x}px,${constellationPan.y}px)`;
  });
```

- [ ] **Step 3: Remplacer `pointerup` sur `constel-inner` pour gérer `nodeDrag`**

Remplacer :

```js
  inner.addEventListener('pointerup',    () => { constellationDrag = null; });
```

Par :

```js
  inner.addEventListener('pointerup', e => {
    if (nodeDrag) {
      if (!nodeDrag.moved) {
        const note = state.filteredList.find(n => n.id === nodeDrag.id);
        if (note) openModal(note);
      } else {
        const dx = e.clientX - nodeDrag.startClientX;
        const dy = e.clientY - nodeDrag.startClientY;
        constellationPositions[nodeDrag.id] = { x: nodeDrag.origX + dx, y: nodeDrag.origY + dy };
        localStorage.setItem('brain_constellation_positions', JSON.stringify(constellationPositions));
        nodeDrag = null;
        renderConstellation();
        return;
      }
      nodeDrag = null;
      return;
    }
    constellationDrag = null;
  });
```

- [ ] **Step 4: Remplacer les handlers `.cnode` — ajouter `pointerdown`, supprimer `click`**

Remplacer :

```js
  view.querySelectorAll('.cnode').forEach(el => {
    el.addEventListener('mouseenter', () => {
      const id = el.dataset.cid;
      document.querySelectorAll(`.edge[data-ea="${id}"], .edge[data-eb="${id}"]`)
        .forEach(path => path.classList.add('lit'));
    });
    el.addEventListener('mouseleave', () => {
      document.querySelectorAll('.edge.lit').forEach(path => path.classList.remove('lit'));
    });
    el.addEventListener('click', e => {
      e.stopPropagation();
      const note = state.filteredList.find(n => n.id === el.dataset.cid);
      if (note) openModal(note);
    });
  });
```

Par :

```js
  view.querySelectorAll('.cnode').forEach(el => {
    el.addEventListener('mouseenter', () => {
      const id = el.dataset.cid;
      document.querySelectorAll(`.edge[data-ea="${id}"], .edge[data-eb="${id}"]`)
        .forEach(path => path.classList.add('lit'));
    });
    el.addEventListener('mouseleave', () => {
      document.querySelectorAll('.edge.lit').forEach(path => path.classList.remove('lit'));
    });
    el.addEventListener('pointerdown', e => {
      e.stopPropagation();
      const currentPos = constellationPositions[el.dataset.cid] || pos[el.dataset.cid];
      nodeDrag = {
        id:           el.dataset.cid,
        el,
        startClientX: e.clientX,
        startClientY: e.clientY,
        origX:        currentPos.x,
        origY:        currentPos.y,
        moved:        false,
      };
      el.setPointerCapture(e.pointerId);
    });
  });
```

- [ ] **Step 5: Lancer l'app et vérifier le clic**

```bash
cd brain_app && npm start
```

- Vue Constellation → cliquer sur un node sans bouger la souris → la modale s'ouvre
- La vue ne bouge pas lors du clic (pan désactivé sur les nodes)

- [ ] **Step 6: Vérifier le drag**

- Cliquer sur un node et le faire glisser de > 6 px → le node suit la souris
- Relâcher → le node reste à la nouvelle position, les edges sont recalculés vers la bonne position
- Faire glisser un second node → les deux restent à leurs nouvelles positions

- [ ] **Step 7: Vérifier la persistance**

- Déplacer 2–3 nodes à de nouvelles positions
- Fermer l'app (Ctrl+C ou fermer la fenêtre)
- Relancer `npm start` depuis `brain_app/`
- Vue Constellation → les nodes déplacés sont aux positions enregistrées
- Les nodes non déplacés sont à leurs positions calculées habituelles

- [ ] **Step 8: Vérifier le pan fonctionne toujours**

- Cliquer-glisser sur le fond vide (pas sur un node) → le canvas se déplace
- Relâcher → le pan est maintenu, les positions des nodes sont préservées

- [ ] **Step 9: Vérifier DevTools localStorage**

Ouvrir DevTools (Ctrl+Shift+I) → Application → Local Storage :
- `brain_constellation_positions` contient un objet JSON avec les IDs des notes déplacées comme clés et `{x, y}` comme valeurs

- [ ] **Step 10: Commit**

```bash
git add brain_app/renderer.js
git commit -m "feat: constellation — drag nodes, clic ouvre modal, persist positions localStorage"
```
