# Compact Notes Layout — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer les cards de la vue Grille par des lignes compactes (titre + tag + date, ~27px) organisées en sections collapsibles par domaine, avec "À trier" en première position.

**Architecture:** Modification purement frontale dans trois fichiers. On ajoute la classe CSS `.nrow` et ses variantes, on remplace `buildNoteCardHtml()` par `buildNoteRowHtml()`, et on adapte le rendering des sections. Le rail horizontal "À trier" est supprimé au profit d'une section collapsible standard. Aucun changement côté backend, modal, blocs ou autres vues.

**Tech Stack:** Electron, CSS vanilla, JavaScript ES modules, anime.js (déjà présent)

---

## Structure des fichiers

| Fichier | Modification |
|---|---|
| `brain_app/style.css` | Ajouter `.nrow` et variantes ; ajuster `.cards` gap ; supprimer styles obsolètes |
| `brain_app/index.html` | Supprimer `<div class="une-head">` et `<div class="rail" id="featured-cards">` |
| `brain_app/renderer.js` | Ajouter `buildNoteRowHtml()` ; mettre à jour `buildSectionHtml()`, `renderSections()`, `renderATrier()`, `renderTopbar()`, animation topbar, sélecteur chat highlight |

---

## Task 1 — CSS : styles `.nrow`

**Files:**
- Modify: `brain_app/style.css` (après la section `.ncard`, ~ligne 242)

Aucun test automatisé applicable (UI visuelle Electron). Vérification manuelle après chaque tâche JS.

- [x] **Étape 1 : Ajouter les styles `.nrow` dans style.css**

Après le bloc `/* Note card */` (après la règle `.metachip` qui clôt la section, ~ligne 242), ajouter :

```css
/* ============================================================
   Note row (vue compacte)
   ============================================================ */
.nrow {
  all: unset; cursor: pointer; text-align: left; width: 100%;
  display: flex; align-items: center; gap: 8px;
  padding: 5px 6px; border-radius: 7px;
  transition: background .15s var(--ease);
}
.nrow:hover { background: rgba(255,255,255,0.05); }
.nrow-bar {
  width: 2px; height: 15px; border-radius: 99px;
  background: var(--accent); opacity: 0.55; flex-shrink: 0;
  transition: opacity .15s var(--ease);
}
.nrow:hover .nrow-bar { opacity: 0.85; }
.nrow-title {
  font-size: 12px; font-weight: 500; flex: 1;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: var(--ink);
}
.nrow-tag {
  font-family: var(--font-mono); font-size: 8.5px;
  color: var(--ink-3); background: var(--glass);
  border-radius: 4px; padding: 1px 5px;
  flex-shrink: 0; white-space: nowrap;
}
.nrow-time {
  font-family: var(--font-mono); font-size: 8.5px;
  color: var(--ink-4); flex-shrink: 0; white-space: nowrap;
}
.nrow.highlighted { background: color-mix(in oklch, var(--accent) 10%, transparent); }
```

- [x] **Étape 2 : Réduire le gap des `.cards`**

Trouver la ligne (actuellement ~ligne 214) :
```css
.cards { display: flex; flex-direction: column; gap: 10px; overflow: hidden; }
```
La remplacer par :
```css
.cards { display: flex; flex-direction: column; gap: 2px; overflow: hidden; }
```

- [x] **Étape 3 : Commit**

```
git add brain_app/style.css
git commit -m "feat: add .nrow compact row styles for grille view"
```

---

## Task 2 — HTML : supprimer le rail À trier

**Files:**
- Modify: `brain_app/index.html` (lignes 44-48)

- [x] **Étape 1 : Supprimer `une-head` et `featured-cards`**

Dans `brain_app/index.html`, supprimer ces deux blocs (ils sont consécutifs dans la `#grille-view`) :

```html
        <div class="une-head" id="une-head">
          <span class="trier-icon" id="trier-icon"></span>
          <span class="uppercase-label" style="color:var(--d-trier)">À trier</span>
        </div>
        <div class="rail" id="featured-cards"></div>
```

Le fichier doit passer de :
```html
      <div id="grille-view" class="scroll">

        <div class="une-head" id="une-head">
          <span class="trier-icon" id="trier-icon"></span>
          <span class="uppercase-label" style="color:var(--d-trier)">À trier</span>
        </div>
        <div class="rail" id="featured-cards"></div>

        <div class="chat" id="chat-bar">
```
à :
```html
      <div id="grille-view" class="scroll">

        <div class="chat" id="chat-bar">
```

- [x] **Étape 2 : Commit**

```
git add brain_app/index.html
git commit -m "feat: remove À trier horizontal rail from HTML"
```

---

## Task 3 — JS : `buildNoteRowHtml()` + `buildSectionHtml()`

**Files:**
- Modify: `brain_app/renderer.js` (~lignes 335-366)

- [x] **Étape 1 : Ajouter `buildNoteRowHtml()` après `buildNoteCardHtml()`**

Après la fonction `buildNoteCardHtml` (après la ligne 366 `}`), ajouter :

```javascript
function buildNoteRowHtml(n) {
  const dom = domainConfig(n.domaine);
  const firstTag = n.parsedTags[0];
  return `<button class="nrow" data-id="${n.id}" style="--accent:${dom.color}">
    <div class="nrow-bar"></div>
    <span class="nrow-title">${n.titre}</span>
    ${firstTag ? `<span class="nrow-tag">#${firstTag}</span>` : ''}
    <span class="nrow-time">${relTime(n._days)}</span>
  </button>`;
}
```

- [x] **Étape 2 : Mettre à jour `buildSectionHtml()` pour utiliser `buildNoteRowHtml`**

Dans `buildSectionHtml()` (ligne 345), remplacer :
```javascript
    <div class="cards">${notes.map(buildNoteCardHtml).join('')}</div>
```
par :
```javascript
    <div class="cards">${notes.map(buildNoteRowHtml).join('')}</div>
```

- [x] **Étape 3 : Lancer l'app Electron et vérifier visuellement**

```
cd C:\Users\yapa\second_cerveau\brain_app
npx electron .
```

Attendu : les sections s'affichent avec des lignes compactes (titre + tag + date) au lieu des cards. Cliquer une ligne → modal s'ouvre. Si erreur console → corriger avant de continuer.

- [x] **Étape 4 : Commit**

```
git add brain_app/renderer.js
git commit -m "feat: replace buildNoteCardHtml with buildNoteRowHtml for compact rows"
```

---

## Task 4 — JS : `renderSections()` — À trier en premier + sélecteurs

**Files:**
- Modify: `brain_app/renderer.js` (~lignes 291-333)

- [x] **Étape 1 : Reorder la boucle pour mettre À trier en première section**

Remplacer dans `renderSections()` le bloc :
```javascript
  let html = '';
  DOMAIN_ORDER.forEach(d => {
    if (!groups[d].length) return;
    html += buildSectionHtml(domainConfig(d), groups[d]);
  });
  if (meta.length) html += buildSectionHtml(META_DOM, meta);
```
par :
```javascript
  let html = '';
  // À trier en tête si des notes non classées existent
  if (groups['À trier']?.length) {
    html += buildSectionHtml(domainConfig('À trier'), groups['À trier']);
  }
  // Autres domaines dans l'ordre habituel (sans répéter À trier)
  DOMAIN_ORDER.filter(d => d !== 'À trier').forEach(d => {
    if (!groups[d]?.length) return;
    html += buildSectionHtml(domainConfig(d), groups[d]);
  });
  if (meta.length) html += buildSectionHtml(META_DOM, meta);
```

- [x] **Étape 2 : Mettre à jour les sélecteurs `.ncard` → `.nrow` dans `renderSections()`**

Remplacer le bloc (lignes ~322-332) :
```javascript
  container.querySelectorAll('.ncard').forEach(el => {
    el.addEventListener('click', () => {
      const note = state.filteredList.find(n => n.id === el.dataset.id);
      if (note) openModal(note);
    });
  });

  const cards = container.querySelectorAll('.ncard');
  if (cards.length && !state._silent) {
    animate(cards, { opacity: [0, 1], translateY: ['8px', '0px'], delay: stagger(30), duration: 380, ease: 'outCubic' });
  }
```
par :
```javascript
  container.querySelectorAll('.nrow').forEach(el => {
    el.addEventListener('click', () => {
      const note = state.filteredList.find(n => n.id === el.dataset.id);
      if (note) openModal(note);
    });
  });

  const rows = container.querySelectorAll('.nrow');
  if (rows.length && !state._silent) {
    animate(rows, { opacity: [0, 1], translateY: ['6px', '0px'], delay: stagger(20), duration: 320, ease: 'outCubic' });
  }
```

- [x] **Étape 3 : Mettre à jour le sélecteur `highlighted` dans le handler du chat**

Chercher (ligne ~659) :
```javascript
      document.querySelectorAll('.ncard, .fcard').forEach(el => el.classList.remove('highlighted'));
```
Remplacer par :
```javascript
      document.querySelectorAll('.nrow, .ncard').forEach(el => el.classList.remove('highlighted'));
```
(`.ncard` conservé par précaution ; `.fcard` supprimé.)

- [x] **Étape 4 : Vérifier dans l'app**

- Les sections s'affichent avec À trier en premier position (si des notes À trier existent)
- Cliquer un titre de section → section se plie/déplie
- Cliquer une ligne → modal s'ouvre avec les bonnes infos
- Taper une question dans la chat bar → les lignes correspondantes se mettent en surbrillance

- [x] **Étape 5 : Commit**

```
git add brain_app/renderer.js
git commit -m "feat: À trier first in sections, update .nrow selectors and animation"
```

---

## Task 5 — JS : nettoyage `renderATrier()` et topbar

**Files:**
- Modify: `brain_app/renderer.js` (~lignes 182-186, 224-261, 1023-1025)

- [x] **Étape 1 : Vider `renderATrier()`**

Remplacer le corps entier de `renderATrier()` (lignes 224-261) par un corps vide :

```javascript
function renderATrier() {
  // Remplacé par la section collapsible standard dans renderSections()
}
```

- [x] **Étape 2 : Supprimer la ligne `trier-icon` dans `renderTopbar()`**

Trouver dans `renderTopbar()` (lignes 184-185) :
```javascript
  const trierIconEl = document.getElementById('trier-icon');
  if (trierIconEl) trierIconEl.innerHTML = ICONS.trier;
```
Supprimer ces deux lignes (l'élément n'existe plus dans le HTML).

- [x] **Étape 3 : Retirer `#une-head` et `#featured-cards` de l'animation topbar**

Trouver (ligne ~1023) :
```javascript
  animate('#topbar, #une-head, #featured-cards, #chat-bar, #filter-bar', {
```
Remplacer par :
```javascript
  animate('#topbar, #chat-bar, #filter-bar', {
```

- [x] **Étape 4 : Vérifier dans l'app**

- Recharger l'app, pas d'erreur dans la console DevTools
- L'animation d'entrée (fadeUp) s'applique bien à la topbar, chat bar et filtres

- [x] **Étape 5 : Commit**

```
git add brain_app/renderer.js
git commit -m "feat: empty renderATrier, remove dead trier-icon code, fix topbar animation"
```

---

## Task 6 — CSS : supprimer les styles obsolètes

**Files:**
- Modify: `brain_app/style.css` (section `/* À trier */`, lignes ~143-162)

- [x] **Étape 1 : Supprimer les règles CSS du rail et des fcards**

Trouver et supprimer le bloc complet (lignes 141-162 environ) :

```css
/* ============================================================
   À trier
   ============================================================ */
.une-head { display: flex; align-items: center; gap: 10px; margin: 8px 2px 12px; }
.une-head .trier-icon { width: 13px; height: 13px; color: var(--d-trier); }
.rail { display: flex; gap: 12px; overflow-x: auto; padding: 2px 2px 10px; scroll-snap-type: x mandatory; }
.rail::-webkit-scrollbar { height: 0; }
.fcard { scroll-snap-align: start; flex: 0 0 220px; cursor: pointer;
  border-radius: var(--r-card); border: 1px solid var(--stroke);
  background: var(--glass); backdrop-filter: blur(var(--blur)); -webkit-backdrop-filter: blur(var(--blur));
  padding: 15px 15px 14px; position: relative; overflow: hidden;
  transition: transform .3s var(--ease-out), border-color .3s var(--ease), background .3s var(--ease);
  min-height: 138px; display: flex; flex-direction: column; }
.fcard:hover { transform: translateY(-3px); border-color: var(--stroke-hi); background: var(--glass-2); }
.fcard .glow { position: absolute; inset: 0; opacity: 0; transition: opacity .3s var(--ease); pointer-events: none;
  background: radial-gradient(120% 80% at 0% 0%, color-mix(in oklch, var(--accent) 22%, transparent), transparent 60%); }
.fcard:hover .glow { opacity: 1; }
.fcard .ftitle { font-weight: 600; font-size: 14.5px; line-height: 1.25; letter-spacing: -0.01em; color: var(--ink); }
.fcard .finsight { font-size: 12.5px; line-height: 1.45; color: var(--ink-2); margin-top: 8px; flex: 1;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.fcard .fmeta { display: flex; align-items: center; gap: 8px; margin-top: 12px; }
.fcard.highlighted { border-color: color-mix(in oklch, var(--accent) 60%, var(--stroke-hi)); }
```

- [x] **Étape 2 : Vérifier dans l'app**

Recharger — aucune régression visuelle. Les sections, lignes compactes, blocs et modal doivent tous fonctionner normalement.

- [x] **Étape 3 : Commit final**

```
git add brain_app/style.css
git commit -m "chore: remove obsolete .fcard, .rail, .une-head CSS"
```

---

## Résumé des commits

| # | Message |
|---|---|
| 1 | `feat: add .nrow compact row styles for grille view` |
| 2 | `feat: remove À trier horizontal rail from HTML` |
| 3 | `feat: replace buildNoteCardHtml with buildNoteRowHtml for compact rows` |
| 4 | `feat: À trier first in sections, update .nrow selectors and animation` |
| 5 | `feat: empty renderATrier, remove dead trier-icon code, fix topbar animation` |
| 6 | `chore: remove obsolete .fcard, .rail, .une-head CSS` |
