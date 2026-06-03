# Second Cerveau — Spec de design (handoff Claude Code)

**Version :** 1.0 · **Date :** 2026-06-03
**Cible technique :** Electron + HTML/CSS/JS vanilla + **anime.js v4** (cf. `ambient-brain-display-design.md`)
**Esprit visuel :** *dark-cosmos / node-editor* — verre dépoli, fond nocturne tiède, dots colorés par domaine, micro-typo monospace, aurora gradient. **Zéro emoji dans l'UI.**

> Ce document décrit le **design**. L'architecture (agent Python, FastAPI, schéma `brain.db`) reste celle de `ambient-brain-display-design.md`. Un prototype React cliquable accompagne cette spec (`Second Cerveau.html` + dossier `app/`) — il sert de **référence visuelle et comportementale**. Les valeurs ci-dessous sont prêtes à être recopiées en CSS vanilla.

---

## 1. Principes

1. **Une note ne montre jamais de markdown brut.** Toujours : titre court + insight + dot de domaine.
2. **Calme par défaut, profondeur à la demande.** La grille respire ; le détail s'ouvre en overlay focalisé.
3. **Le domaine = une couleur, pas un mot ni une icône.** Un dot coloré suffit ; le label texte n'apparaît que dans les en-têtes de section et la modale.
4. **Micro-typo technique.** Tout ce qui est méta (compteurs, dates, états, stats de coin) est en monospace, discret.
5. **Le verre flotte sur le cosmos.** Cartes translucides + blur, posées sur un fond nocturne avec dot-grid et 1–2 blobs aurora très lents.
6. **Toujours visible, jamais bruyant.** L'app vit sur le 3ᵉ écran portrait en permanence : pas d'animations en boucle agressives, pas de notifications clignotantes.

---

## 2. Typographie

| Rôle | Police | Graisses | Usage |
|---|---|---|---|
| UI / titres / corps | **Satoshi** (Fontshare) | 400 / 500 / 700 / 900 | Tout le texte lisible |
| Méta / labels / stats | **JetBrains Mono** (Google Fonts) | 400 / 500 | Compteurs, dates, labels de section, stats de coin, tags |

```html
<link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,900&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

**Échelle (px) :** titre modale 23/700 · titre carte 14–14.5/600 · insight 12.5/400 · résumé 14/400 · label section (mono) 11/500 0.16em uppercase · meta (mono) 10–11/400. `letter-spacing` titres ≈ −0.01 à −0.02em. `text-wrap: balance` sur les titres de modale, `pretty` sur les paragraphes.

> Remplace l'ancien choix « Inter/Geist » : Satoshi donne un rendu plus pro et géométrique, JetBrains Mono ancre le côté node-editor.

---

## 3. Couleurs

### Surfaces (fond nocturne tiède)
```css
--void:   #08080c;   /* fond app          */
--void-2: #0b0b11;   /* panneau / modale  */
--grid-dot: rgba(255,255,255,0.035); /* dot-grid 22px */
```

### Verre
```css
--glass:    rgba(255,255,255,0.040);  /* carte au repos      */
--glass-2:  rgba(255,255,255,0.060);  /* carte hover         */
--glass-hi: rgba(255,255,255,0.090);  /* pill active         */
--stroke:   rgba(255,255,255,0.085);  /* bordure au repos    */
--stroke-hi:rgba(255,255,255,0.150);  /* bordure hover/focus */
--blur: 18px;                         /* backdrop-filter     */
```

### Texte
```css
--ink:   #f4f4f7;  /* titres        */
--ink-2: #a6a6b6;  /* insight/corps */
--ink-3: #6a6a7c;  /* meta          */
--ink-4: #4a4a5a;  /* stats de coin */
```

### Accents par domaine (oklch — **L/C partagés, hue variée** → palette harmonieuse)
| Domaine | Token | oklch | ~hex |
|---|---|---|---|
| Travail | `--d-travail` | `oklch(0.81 0.13 82)` | ambre `#e7b24d` |
| Apprentissage | `--d-apprentissage` | `oklch(0.72 0.13 255)` | bleu `#5b9df0` |
| Projets perso | `--d-projets` | `oklch(0.72 0.15 25)` | corail `#f0795f` |
| Jeux vidéos | `--d-jeux` | `oklch(0.72 0.15 322)` | magenta `#d56fd0` |
| Plantes | `--d-plantes` | `oklch(0.78 0.14 150)` | vert `#52c785` |
| Organisation (TDAH) | `--d-tdah` | `oklch(0.77 0.12 200)` | cyan `#4ec3cf` |
| Méta-fiches | `--d-meta` | `oklch(0.80 0.04 280)` | lilas neutre |
| À la une | `--d-une` | `oklch(0.85 0.11 90)` | doré |

> Garde **oklch** : pour ajouter/retirer un domaine, ne change que le `hue`, jamais L ni C → l'harmonie reste garantie.
> Le dot de domaine = `background: var(--accent)` + halo `box-shadow: 0 0 10px color-mix(in oklch, var(--accent) 70%, transparent)`.

---

## 4. Forme & espace

```css
--r-card: 16px;  --r-inner: 12px;  --r-pill: 999px;  --r-sm: 9px;
/* échelle 4px */ --s1:4 --s2:8 --s3:12 --s4:16 --s5:20 --s6:24 --s7:32 --s8:44
--shadow-card:  0 1px 0 rgba(255,255,255,.04) inset, 0 8px 30px rgba(0,0,0,.45);
--shadow-float: 0 18px 60px rgba(0,0,0,.6);
--shadow-modal: 0 40px 120px rgba(0,0,0,.7);
--ease: cubic-bezier(.22,.61,.36,1);  --ease-out: cubic-bezier(.16,1,.3,1);
```

Le **panneau portrait** (l'app plein écran sur l'écran 3) : bordure `1px var(--stroke)`, fond `var(--void-2)` + léger dégradé blanc 2.5 %→0 en haut, dot-grid en `::before` masqué en fondu vers le haut, `--shadow-float`.

---

## 5. Layout (écran portrait)

```
┌───────────────────────────────────────────────┐
│ ◐ Second Cerveau     [Grille|Constellation]  ● 16 notes · 1 synthèse │  topbar
├───────────────────────────────────────────────┤
│ ★ À LA UNE                                      │
│ [fcard] [fcard] [fcard] →   (rail scroll-x)     │
│                                                 │
│ ✦ Pose une question à tes notes…           ↵    │  chat RAG
│                                                 │
│ [Tous][● Travail][● Apprentissage]… │ �clock Récents │ ⛓ Liées │  filtres
│                                                 │
│ ● TRAVAIL            03 ────────────────── ⌄    │  section repliable
│   [ncard] [ncard] [ncard]                       │
│ ● APPRENTISSAGE      05 ────────────────── ⌄    │
│   …                                             │
│ ● MÉTA-FICHES        01 ────────────────── ⌄    │
│                                                 │
│ N: 17 (16)                          all         │  stats de coin (mono)
│ S: 1 · sync il y a 14 min        ↓ récents      │
└───────────────────────────────────────────────┘
```

- **topbar** : logo + wordmark à gauche · segmented `Grille / Constellation` au centre-droit · pill de statut à droite. `overflow:hidden`, tout en `nowrap`.
- **scroll** : `overflow-y:auto; overflow-x:hidden;` padding bas 90px (laisse respirer au-dessus des stats de coin).
- **stats de coin** : visibles en mode Grille uniquement (la Constellation a sa propre légende + hint).

---

## 6. Composants

### 6.1 Carte « À la une » (`.fcard`)
Rail horizontal scroll-snap. `flex:0 0 232px`, glass + blur, `--r-card`. Contenu : titre (600/14.5) · insight (clamp 3 lignes) · pied = dot + domaine (mono minuscule) + date relative à droite. **Hover** : `translateY(-3px)`, bordure `--stroke-hi`, et un `.glow` radial teinté `--accent` apparaît en fond (coin haut-gauche).

### 6.2 Barre de chat RAG (`.chat`)
Pleine largeur, glass, `border-radius:14px`. Icône *spark* à gauche, input transparent, badge clavier `↵` à droite. `:focus-within` → bordure `--stroke-hi`, fond `--glass-2`. Comportement : envoie à `POST /chat`, affiche la réponse sous la barre et **met en évidence les cartes sources** (halo `--accent`).

### 6.3 Barre de filtres (`.filters`)
Rangée de **pills** : `Tous` puis un pill par domaine (dot + label). Séparateur fin, puis un pill **tri** (`clock` → bascule Récents/Anciens) et un pill **toggle** `Liées` (n'affiche que les notes ayant des liens). Pill actif : `--glass-hi` + `--stroke-hi`. Le toggle `Liées` actif se teinte légèrement.

### 6.4 En-tête de section (`.shead`)
`● dot` + label mono uppercase + compteur mono (`03`) + ligne dégradée + chevron. Cliquable → replie/déplie (chevron −90°). Le `--accent` de la section colore le dot.

### 6.5 Carte de note (`.ncard`)
Bouton glass pleine largeur. Ligne 1 : dot + titre (+ badge `synthèse` à droite si méta). Insight clamp 2 lignes. Pied : date relative (mono) + 1ᵉʳ tag (`#xxx` mono) + compteur de liens (icône `link` + n) poussé à droite. **Hover** : `translateX(2px)`, bordure `--stroke-hi`, et un liseré vertical `--accent` (2px) apparaît à gauche.

### 6.6 Pill de statut & stats de coin
Mono. Pill : `● {total} notes · {meta} synthèse`. Coins : `N: {affichées} ({total})` / `S: {meta} · sync {last_sync}` à gauche, état des filtres à droite.

---

## 7. Vue agrandie — modale (clic sur une note)

Overlay centré, **fond flouté** (`.scrim` : `rgba(6,6,10,.55)` + `blur(10px) saturate(.9)`), focus total. Largeur `min(540px, 100%)`, `max-height:92%`.

- **En-tête aurora** (168px) : 3 blobs flous en `mix-blend:screen`, **le premier teinté `--accent` du domaine**, les autres violet/orange — c'est l'écho du « Final Result » de la réf. Grain de points par-dessus. En bas : dot + label domaine (mono) + **titre 23/700**.
- **Boutons** : `← →` (note précédente/suivante dans la liste filtrée) + `✕` en haut-droite, ronds, glass.
- **Corps** :
  - *Encadré insight* : barre verticale `--accent` lumineuse + texte 15/500 sur fond `color-mix(--accent 9%)`, bordure `color-mix(--accent 28%)`.
  - *Résumé* : label mono + paragraphe 14/1.6.
  - *Tags* : pills mono.
  - *Notes liées / sources* : lignes cliquables (dot + titre + flèche) qui **naviguent vers la note liée** (la modale se recharge).
  - *Pied* : date · index `01 / 17` · jauge de **pertinence** (track + fill `--accent` + valeur `0.94`).
- **Clavier** : `Esc` ferme · `←/→` navigue.
- **Entrée** : `modalIn` (translateY 16px + scale .98 → 0) sur `--ease-out`, scrim en fondu.

---

## 8. Mode Constellation (toggle topbar)

Vue alternative : chaque note est un **node bulle** (pill glass : dot + titre tronqué), regroupé par domaine autour de hubs disposés en anneau ; les **liens entre notes** sont des **courbes de Bézier** (`<path>` quadratique) couleur `--stroke`, qui **s'illuminent à la couleur du domaine au survol** d'un node. 

- **Layout** : hubs sur un cercle `R = min(w,h)·0.26` ; notes en grappe autour de leur hub ; méta-fiches au centre ; positions **clampées** dans `[96, w−96] × [84, h−70]` pour ne jamais déborder.
- **Pan** : glisser pour déplacer le monde (`pointerdown/move/up` → `translate`). Hint mono « glisser pour naviguer » en haut-droite.
- **Légende** : dots + labels de domaine en bas-gauche.
- **Node méta** : bordure `dashed`. Hover/active : `scale(1.05)` + halo `--accent`.
- Clic sur un node → ouvre la même **modale** qu'en grille.

> C'est le pont le plus direct avec la réf node-editor : conserve les courbes douces, le dot-grid en fond, et le verre.

---

## 9. Fond cosmos & aurora

- **Dot-grid** : `radial-gradient(--grid-dot 1px, transparent 1px)` taille `22px`, masqué en fondu sous la topbar.
- **Aurora** : 2–3 blobs radiaux (`oklch(0.7 0.16 30)` orange, `oklch(0.65 0.16 290)` violet, `oklch(0.66 0.15 245)` bleu), `filter: blur(70px)`, `mix-blend:screen`, `opacity` réglée par `--aurora-opacity` (**défaut 0.30**), dérive très lente (26–38 s, `alternate`). `prefers-reduced-motion` → fige.

---

## 10. Animation (anime.js v4)

| Élément | Effet | Détail |
|---|---|---|
| Entrée des sections/cartes | `fadeUp` | `opacity 0→1`, `translateY 10→0`, **stagger 40 ms**, `--ease-out` |
| topbar / à la une / chat / filtres | `fadeUp` cascadé | délais 0 / .03 / .05 / .1 s |
| Blobs aurora | dérive continue | 26–38 s, `alternate`, lent |
| Modale | `modalIn` | scale .98→1 + translateY, scrim en fondu |
| Node constellation hover | scale + halo | `1→1.05`, edges « lit » |
| Réponse chat | apparition + halo sources | met en évidence les cartes citées |

Pas de boucle décorative permanente sur le contenu (écran toujours allumé). Respecte `prefers-reduced-motion`.

---

## 11. Mapping données → UI (API existante)

| Champ `brain.db` / API | UI |
|---|---|
| `titre_court` | titre carte / modale |
| `insight_cle` | insight (cartes) + encadré insight (modale) |
| `resume` | bloc « Résumé » de la modale |
| `domaine` | couleur du dot + section + en-tête modale |
| `tags` | 1ᵉʳ tag sur la carte · tous dans la modale |
| `date_capture` | date relative (`aujourd'hui`, `hier`, `il y a 3 j`, `il y a 2 sem`) |
| `score_pertinence` | tri « pertinence » + jauge modale + sélection À la une |
| `est_meta_fiche` | badge `synthèse`, bordure dashed en constellation, section Méta-fiches |
| `sources_ids` | « Notes sources » (méta) · sinon « Notes liées » via voisins |
| `GET /a-la-une` | rail À la une |
| `GET /status` | pill statut + stats de coin |
| `POST /chat` | barre RAG + mise en évidence des sources |

**Dates relatives** : `≤0 → aujourd'hui` · `1 → hier` · `<7 → il y a N j` · `<30 → il y a N sem` · sinon `il y a N mois`.

---

## 12. Assets fournis

| Fichier | Rôle |
|---|---|
| `assets/logo.svg` | Mark **synapse-node** (neurone + node-graph) : node central + ring d'orbite + 2 satellites reliés par des courbes. Monoline `currentColor` → s'encre en blanc sur fond sombre. 26px dans la topbar. |
| `app/tokens.css` | Toutes les variables (à recopier tel quel en vanilla). |
| `app/app.css` | Styles composants + modale + constellation (référence 1:1). |
| `Second Cerveau.html` + `app/*.jsx` | Prototype React de référence (comportement + visuel). |

> En production (Electron vanilla), recopie `tokens.css` et `app.css` directement, et réécris la logique React (`useState`) en JS impératif : un `state` global, des fonctions `render*()`, des écouteurs `click`. Le HTML/CSS ne change pas.

---

## 13. Accessibilité & qualité

- Contraste titres `--ink` sur `--void-2` ≈ AAA ; insight `--ink-2` ≈ AA.
- Cibles tactiles ≥ 44px non requises (écran non tactile) mais garde les pills ≥ 28px de haut.
- Focus clavier visible sur input chat (`:focus-within`).
- `Esc`/`←`/`→` dans la modale.
- Jamais de texte < 10px ; le mono descend à 10px **uniquement** pour les stats de coin.

---

## 14. À éviter (anti-slop)

- ❌ Emoji dans l'UI (les domaines = dots colorés).
- ❌ Markdown brut affiché.
- ❌ Dégradés saturés en aplat de fond (l'aurora reste à ~30 %, floue, lente).
- ❌ Coins très arrondis + liseré gauche coloré en bloc partout (le liseré `--accent` n'apparaît qu'au hover des `ncard`).
- ❌ Inter/Roboto — on utilise Satoshi + JetBrains Mono.
- ❌ Boucles d'animation permanentes sur le contenu.
