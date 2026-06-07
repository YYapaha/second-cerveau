# Second Cerveau — Redesign Adaptation Design

**Date :** 2026-06-07  
**Statut :** Approuvé — implémenter  
**Source :** `redesign/` (prototype Claude Design haute-fidélité)

---

## Décisions

| Élément | Décision |
|---|---|
| À la une | ❌ Supprimée — pas de `renderUne()`, pas de `.une` |
| Cartes notes | ✅ Riches 2 colonnes (B) — `buildNoteCardHtml` + `.cards` grid |
| Dock (3 colonnes fixes) | ✅ Conservé fonctionnellement, restyled |
| Approche | ✅ A — adoption complète du redesign en un seul plan |

---

## 1. Fichiers touchés

| Fichier | Nature du changement |
|---|---|
| `brain_app/icons.js` | **Nouveau** — exporte `ICONS` (ui + zen activities) |
| `brain_app/style.css` | Tokens, ncard 2-col, statusbar, suppression corner |
| `brain_app/zen.css` | Reskin zen bar — `.locked` remplace `.available`, icônes SVG |
| `brain_app/index.html` | Supprime `.corner`, ajoute `#statusbar` |
| `brain_app/renderer.js` | Import icons, statusbar, force-directed constel, cards 2-col |
| `brain_app/zen.js` | Import icons, émojis → clés SVG |

---

## 2. Tokens (style.css `:root`)

Remplacer le bloc `:root` existant par `redesign/tokens.css`. Ajouts clés :
- `--void-3: #0e0e16` (surfaces raised — dock, blocs)
- `--glass / --glass-2 / --glass-hi` plus denses
- `--stroke / --stroke-2 / --stroke-hi` re-calibrés
- `--r-card: 18px` (était 16px), `--r-hero: 22px`, `--r-sm: 10px`
- `--shadow-card / --shadow-hero / --shadow-modal` étendus
- Palette domaine inchangée (mêmes oklch, légère variation Travail)
- `--t-*` : échelle typo agrandie pour lecture à 1 m

---

## 3. HTML (`index.html`)

```diff
- <div class="corner bl" id="corner-bl"></div>
- <div class="corner br" id="corner-br"></div>
+ <div class="statusbar" id="statusbar"></div>
```
Le `#statusbar` est placé **entre** `#grille-view` et `#blocs-section`.

Suppression de la section "À la une" : aucune balise `#une-cards` n'est ajoutée.

---

## 4. icons.js (nouveau module ES)

Exporte `{ ICONS }` = ensemble complet des icônes monoline SVG :
- UI : logo, star, spark, chev, link, clock, grid, nodes, zen, refresh, close, arrow, arrowLeft, ext, trash, plus
- Zen activities : target, orbit, lungs, sparkles, bubbles, sliders, wave, ripple, kaleido

`renderer.js` et `zen.js` importent depuis ce fichier. L'objet `const ICONS = {...}` est supprimé de `renderer.js`.

---

## 5. Cartes notes (grille)

`.cards` : `display: grid; grid-template-columns: 1fr 1fr; gap: 14px` (était `flex column`).

`buildSectionHtml` appelle `buildNoteCardHtml` (structure redesign : row1 + ninsight + nfoot).

`buildNoteCardHtml` mis à jour : 2 tags max, `.tags-inline` + `.nmeta` (links + metatime).

CSS `.ncard` :
- Pas de `backdrop-filter` (GPU + capture)
- `background: linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.028))`
- Hover : `translateY(-3px)` + glow `color-mix(accent 16%, transparent)`
- `::after` barre gauche accent : `left:0; top:14px; bottom:14px; width:3px`

---

## 6. Statusbar (remplace `.corner`)

`renderStatusbar()` rend `#statusbar` :
```
● 14 affichées / 42 · 1 synthèse · sync il y a 3 min   [tous domaines] [↓ récents]
```
Visibilité : affiché en mode grille uniquement (togglé dans `render()`).  
`renderCornerStats()` et les `.corner` sont supprimés.

---

## 7. Constellation force-directed

`computeLayout()` + `renderConstellation()` remplacés par la version force-directed de `redesign/app.js` :
- Seed : anneau elliptique (Rx=W×0.30, Ry=H×0.33)
- 220 itérations : gravité hub (0.015) + ressorts arêtes (0.005, repos 240px) + séparation boîtes (±32/26 px)
- Labels de hub au-dessus du nœud le plus haut de chaque cluster
- Bulles : `background: rgba(18,18,27,0.94)` — **pas** de `backdrop-filter`
- Pan conservé (pointerdown/move/up, seuil 4 px)
- Drag-to-save-positions supprimé (force-directed gère le placement)

---

## 8. Zen — icônes monoline

`zen.js` ACTIVITIES : icônes emoji → clés string (`'🪐'` → `'orbit'`, etc.).  
Button HTML : `<span class="zen-tab-icon">${ICONS[a.icon]}</span>`.  
Classe : `'zen-tab' + (module ? '' : ' locked')` — supprime `.available`.

`zen.css` `.zen-bar` reskinné : fond `var(--void-3)`, `.zen-tab.locked` (opacity 0.4 + point), `.zen-tab.active .zic { color: var(--d-une) }`.

---

## 9. Modal

Pas de changement : `renderModal()` gère déjà source_link + points_cles + titreEditable + domainPicker. CSS modal aligné sur redesign (taille 720px max, bandeau 210px).

---

## 10. Dock / Blocs

Structure JS/HTML conservée (`.blocs-grid`, `.bloc-col`, `.bloc-items`…).  
CSS mis à jour : `#blocs-section { background: var(--void-3) }`. `.bloc-col-header` ajoute un dot coloré (via `renderBlocCol` qui injecte `<span class="ddot">` avec `--accent` selon la colonne).

---

## Anti-patterns (à ne pas introduire)

- `backdrop-filter` sur `.ncard` ou `.cnode .bubble` — réservé au chat et au scrim
- Emoji dans l'UI — tout est SVG
- Animation `fadeUp` depuis `opacity:0` sur les cartes — retirer ou garder état final visible
- `backdrop-filter` sur les éléments répétés
