# Zen — Tableau de bord Aurora
**Date :** 2026-06-04
**Statut :** Approuvé

---

## Objectif

Activité Zen : un tableau de bord interactif (sliders + knobs + toggles) qui contrôle en temps réel une aurora animée. Satisfaisant à manipuler, hypnotique à regarder.

---

## Architecture

```
brain_app/activities/dashboard.js   ← nouveau module ES
```

Pattern identique aux 3 autres activités : `export function create(container)` → `{ start, stop }`.

---

## Canvas Aurora

Canvas plein écran (hors panel) avec 3 blobs aurora animés via `requestAnimationFrame`.

Chaque blob :
```javascript
{ cx, cy, rx, ry, color, phaseX, phaseY, speedX, speedY }
```

Position : `cx = centerX + Math.sin(t * speedX + phaseX) * driftX`

Les 3 couleurs de base (identiques au fond de l'app) :
- Blob 1 : `oklch(0.7 0.16 30)` — orange/rouge
- Blob 2 : `oklch(0.65 0.16 290)` — violet
- Blob 3 : `oklch(0.66 0.15 245)` — bleu

Rendu : `ctx.filter = \`blur(${params.blur}px) hue-rotate(${params.hueShift}deg)\`` avant chaque blob, `globalAlpha = params.intensity`, fill radial gradient. Le filtre est réinitialisé à `'none'` après les blobs pour ne pas affecter les particules.

**Paramètres live (objet `params`) :**

| param | range | défaut | effet |
|---|---|---|---|
| `hueShift` | 0–360 | 0 | `ctx.filter += hue-rotate(Xdeg)` |
| `speed` | 0.1–3.0 | 1.0 | multiplie `speedX/Y` de chaque blob |
| `blur` | 20–120 | 70 | rayon de blur canvas |
| `intensity` | 0.1–1.0 | 0.45 | opacité globale |
| `scale` | 0.5–2.0 | 1.0 | taille des blobs (`rx`, `ry`) |
| `chaos` | 0–1 | 0.3 | amplitude des dérivations aléatoires |
| `b1`, `b2`, `b3` | bool | true | active/désactive chaque blob |
| `particles` | bool | false | overlay de dots flottants |
| `lines` | bool | false | lignes entre particules proches |

**Particules (si `params.particles = true`) :**
30 dots initialisés avec position/vélocité aléatoires, rebondissent sur les bords. Taille 2-4px, couleur blanche semi-transparente.

**Lignes (si `params.lines = true`) :**
Pour chaque paire de particules à moins de 80px de distance, dessiner une ligne dont l'opacité = `1 - dist/80`.

---

## Panel de contrôles

HTML injecté par `create()`, div fixe en bas du container (~160px).

### Sliders verticaux (4)

Chaque slider :
```html
<div class="db-slider" data-param="hue">
  <div class="db-slider-track">
    <div class="db-slider-fill"></div>
    <div class="db-slider-thumb"></div>
  </div>
  <span class="db-slider-label">HUE</span>
</div>
```

Interaction : `mousedown` sur le track → écoute `mousemove` sur `document` → calcule `value = 1 - (mouseY - trackTop) / trackHeight` → clamp [0,1] → mappe sur la plage du param → met à jour `params` + repaint thumb.

Couleurs des tracks :
- HUE : `oklch(0.72 0.15 25)` (orange)
- VITESSE : `oklch(0.72 0.13 255)` (bleu)
- BLUR : `oklch(0.65 0.16 290)` (violet)
- INTENSITÉ : `oklch(0.78 0.14 150)` (vert)

### Knobs rotatifs (2)

Chaque knob : cercle SVG avec arc de progression + indicateur.

Interaction `mousedown` → sur `mousemove` calcule `angle = atan2(dy, dx)` → mappe angle (-135°..+135°) sur la plage du param.

- TAILLE : mappe [0.5, 2.0]
- CHAOS : mappe [0, 1]

### Toggles pill (5)

Simple `<button class="db-toggle [active]" data-param="b1">B1</button>`.

Clic → toggle `params[key]`, toggle classe `.active`, transition couleur CSS.

Labels : **B1** · **B2** · **B3** · **∴** (particules) · **—** (lignes)

---

## CSS (inline dans le module, pas de fichier séparé)

Styles injectés via `<style>` tag dans le container ou directement via `style=""` sur les éléments. Pas de fichier CSS externe pour ne pas polluer le scope global.

Couleurs/variables réutilisées depuis les custom properties CSS déjà définies dans style.css (`var(--glass)`, `var(--stroke)`, `var(--font-mono)`, etc.).

---

## Fichiers modifiés/créés

| Fichier | Changement |
|---|---|
| `brain_app/activities/dashboard.js` | Nouveau module complet |
| `brain_app/zen.js` | Décommenter l'entrée `sliders` dans `ACTIVITIES` (remplacer `module: null` par la fonction d'import) + corriger le label en "Tableau" |

---

## Hors scope

- Sauvegarde des paramètres entre sessions (pas de localStorage)
- Preset buttons (sauvegarder une configuration)
- Contrôle audio (pas de son sur ce module)
