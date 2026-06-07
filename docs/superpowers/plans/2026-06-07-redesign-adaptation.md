# Plan — Redesign Adaptation

**Date :** 2026-06-07  
**Spec :** `docs/superpowers/specs/2026-06-07-redesign-adaptation-design.md`  
**Statut :** À exécuter

---

## Tâches

### T1 — Créer `brain_app/icons.js`
- Nouveau fichier ES module
- Exporte `{ ICONS }` avec tous les icônes UI + zen activities (target, orbit, lungs, sparkles, bubbles, sliders, wave, ripple, kaleido)
- Source : `redesign/icons.js` (adapter en `export const ICONS = {...}`)

### T2 — Mettre à jour `brain_app/index.html`
- Supprimer `<div class="corner bl" ...>` et `<div class="corner br" ...>`
- Ajouter `<div class="statusbar" id="statusbar"></div>` entre `#grille-view` et `#blocs-section`

### T3 — Mettre à jour `brain_app/style.css`
- Remplacer le bloc `:root` par les tokens v2 (redesign/tokens.css)
- Mettre à jour `.cards` : `display:grid; grid-template-columns:1fr 1fr; gap:14px`
- Mettre à jour `.ncard` : gradient bg, no backdrop-filter, hover translateY(-3px)+glow, ::after barre gauche
- Supprimer CSS `.corner`
- Ajouter CSS `.statusbar`
- Mettre à jour `.ncard .nfoot` : `.tags-inline` + `.nmeta` layout
- Mettre à jour `.cnode .bubble` : `background:rgba(18,18,27,0.94)`, pas de backdrop-filter
- Mettre à jour `#blocs-section` : `background: var(--void-3)`
- Mettre à jour `.ncard::after` : position et dimensions correctes

### T4 — Mettre à jour `brain_app/zen.css`
- Reskin `#zen-bottom-bar` : `background: var(--void-3)`, padding élargi
- Reskin `.zen-tab` : flex column, gap 8px, width 92px, border transparent
- Remplacer `.zen-tab.available` par `.zen-tab:not(.locked):hover` et `.zen-tab:not(.locked)`
- Ajouter `.zen-tab.locked` : opacity 0.4 + `::after` petit point
- Mettre à jour `.zen-tab.active` : `--glass-hi`, border `--stroke-hi`
- Mettre à jour `.zen-tab-icon` : width/height 26px (conteneur SVG)
- Mettre à jour `.zen-tab-label` : 11px, 0.08em letter-spacing

### T5 — Mettre à jour `brain_app/renderer.js`
- Import : `import { ICONS } from './icons.js'` (supprimer `const ICONS = {...}`)
- Supprimer `renderATrier()` (stub vide)
- Supprimer `renderCornerStats()` et ses appels dans `renderGrille()` et `render()`
- Ajouter `renderStatusbar()` — affiche filteredList.length, total, meta_count, sync, sort
- Mettre à jour `renderGrille()` : appeler `renderStatusbar()` au lieu de `renderCornerStats()`
- Mettre à jour `render()` : toggle `#statusbar` visible en grille seulement
- Mettre à jour `buildNoteCardHtml` : 2 tags, `.tags-inline` + `.nmeta`, structure redesign
- Mettre à jour `buildSectionHtml` : appeler `buildNoteCardHtml` au lieu de `buildNoteRowHtml`
- Mettre à jour `renderSections` : event listeners sur `.ncard` au lieu de `.nrow`, animation cible `.ncard`
- Mettre à jour `renderTopbar` : `btnZ.innerHTML = \`${ICONS.zen} Zen\``
- Remplacer `computeLayout()` par force-directed
- Remplacer `renderConstellation()` par version force-directed (adapter depuis redesign/app.js)
- Mettre à jour `renderBlocs` / `renderBlocCol` : ajouter ddot coloré dans l'en-tête de colonne
- Supprimer `constellationPositions` localStorage et `nodeDrag` (drag-to-save supprimé)

### T6 — Mettre à jour `brain_app/zen.js`
- Import : `import { ICONS } from './icons.js'`
- Mettre à jour ACTIVITIES : emoji → clés string (aim→target, solar→orbit, breath→lungs, etc.)
- Mettre à jour button rendering : `${ICONS[a.icon] || ''}` dans `.zen-tab-icon`
- Mettre à jour classe : `'zen-tab' + (a.module ? '' : ' locked')`
- `loadActivity` : ajouter classList toggle `active` proprement

### T7 — Tests manuels & commit
- Vérifier : scroll grille, cartes 2-col visibles, statusbar, no corner stats
- Vérifier : constellation force-directed sans chevauchements
- Vérifier : zen tabs icônes SVG, locked tabs visuellement différenciés
- Vérifier : modal ouvre/ferme/navigue, source link, points clés
- Vérifier : blocs dock headers avec dots colorés
- `git add` + `git commit` + `git push master`
