# Brain UI Redesign — Plan 3

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Réécrire les 3 fichiers UI Electron (`style.css`, `index.html`, `renderer.js`) pour implanter le nouveau design dark-cosmos/glass fourni par Claude Design, en s'appuyant sur le prototype React (`idées/`) comme référence visuelle et comportementale exacte.

**Architecture:** Traduction directe du prototype React vers vanilla JS impératif. Un objet `state` global + `setState(patch)` → `render()`. Les CSS tokens et styles du prototype sont copiés tels quels dans `style.css` avec une adaptation Electron (panel plein écran). Le JS traduit `useState` → état global, composants React → fonctions `render*()`, `useMemo` → recalcul dans `setState`.

**Tech Stack:** Electron 35, HTML5/CSS3 (oklch, backdrop-filter), Anime.js v4 (`brain_app/node_modules/animejs/dist/modules/index.js`), Satoshi (Fontshare) + JetBrains Mono (Google Fonts), SVG inline

**Référence design:** `idées/Design Spec - Second Cerveau.md` + `idées/Second Cerveau.html` + `idées/app/` (tokens.css, app.css, components.jsx, views.jsx, app.jsx)

**API (Plan 1 — inchangée):**
- `GET /status` → `{ total_notes, meta_fiches_count, last_sync }`
- `GET /a-la-une?limit=6` → `[{ id, titre_court, insight_cle, resume, domaine, tags, date_capture, score_pertinence, est_meta_fiche, sources_ids }]`
- `GET /notes?limit=200` → même format
- `POST /chat` `{ query }` → `{ reponse, sources: [{ id, ... }] }`

---

## File Map

**Modifiés :**
- `brain_app/style.css` — réécriture complète (tokens + styles composants)
- `brain_app/index.html` — réécriture complète (nouvelle structure HTML)
- `brain_app/renderer.js` — réécriture complète (state, grille, modal, constellation)

**Créés :**
- `brain_app/logo.svg` — copié depuis `idées/assets/logo.svg`

---

### Task 1 : style.css + logo.svg

**Files:**
- Modify: `brain_app/style.css`
- Create: `brain_app/logo.svg`

Pas de tests automatisés pour le CSS — vérification visuelle après Task 2.

- [ ] **Step 1 : Copier logo.svg**

Créer `brain_app/logo.svg` avec ce contenu (copié depuis `idées/assets/logo.svg`) :

```svg
<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="32" cy="32" r="9.5" fill="none" stroke="currentColor" stroke-width="2.4"></circle>
  <circle cx="32" cy="32" r="2.6" fill="currentColor"></circle>
  <ellipse cx="32" cy="32" rx="22" ry="22" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.28"></ellipse>
  <circle cx="51" cy="21" r="3.4" fill="currentColor"></circle>
  <circle cx="14" cy="44" r="2.6" fill="currentColor"></circle>
  <path d="M40.5 27 C45 23.5, 47.5 22.5, 51 21" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"></path>
  <path d="M24 38 C19.5 41, 16.5 42.5, 14 44" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
</svg>
```

- [ ] **Step 2 : Réécrire brain_app/style.css**

Remplacer l'intégralité du fichier par le contenu ci-dessous (fusion de `idées/app/tokens.css` + `idées/app/app.css` + overrides Electron + règles supplémentaires) :

```css
/* ============================================================
   SECOND CERVEAU — Design tokens
   ============================================================ */
:root {
  --void:        #08080c;
  --void-2:      #0b0b11;
  --grid-dot:    rgba(255, 255, 255, 0.035);
  --glass:       rgba(255, 255, 255, 0.040);
  --glass-2:     rgba(255, 255, 255, 0.060);
  --glass-hi:    rgba(255, 255, 255, 0.090);
  --stroke:      rgba(255, 255, 255, 0.085);
  --stroke-hi:   rgba(255, 255, 255, 0.150);
  --blur:        18px;
  --ink:         #f4f4f7;
  --ink-2:       #a6a6b6;
  --ink-3:       #6a6a7c;
  --ink-4:       #4a4a5a;
  --d-travail:        oklch(0.81 0.13 82);
  --d-apprentissage:  oklch(0.72 0.13 255);
  --d-projets:        oklch(0.72 0.15 25);
  --d-jeux:           oklch(0.72 0.15 322);
  --d-plantes:        oklch(0.78 0.14 150);
  --d-tdah:           oklch(0.77 0.12 200);
  --d-meta:           oklch(0.80 0.04 280);
  --d-une:            oklch(0.85 0.11 90);
  --r-card:   16px;
  --r-inner:  12px;
  --r-pill:   999px;
  --r-sm:     9px;
  --s1: 4px;  --s2: 8px;  --s3: 12px; --s4: 16px;
  --s5: 20px; --s6: 24px; --s7: 32px; --s8: 44px;
  --shadow-card:  0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 30px rgba(0,0,0,0.45);
  --shadow-float: 0 18px 60px rgba(0,0,0,0.6);
  --shadow-modal: 0 40px 120px rgba(0,0,0,0.7);
  --font-ui:   "Satoshi", "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
  --ease:     cubic-bezier(0.22, 0.61, 0.36, 1);
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
}

*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--void); color: var(--ink);
  font-family: var(--font-ui); -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
.mono { font-family: var(--font-mono); }
.uppercase-label { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: 0.18em;
  text-transform: uppercase; color: var(--ink-3); font-weight: 500; }
::selection { background: rgba(255,255,255,0.18); }
*::-webkit-scrollbar { width: 8px; height: 8px; }
*::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 99px; }
*::-webkit-scrollbar-track { background: transparent; }

/* ============================================================
   Stage & aurora
   ============================================================ */
.stage { position: fixed; inset: 0; display: grid; place-items: center;
  background: radial-gradient(120% 90% at 50% -10%, #101019 0%, var(--void) 55%); overflow: hidden; }
.aurora { position: fixed; inset: -20% -10%; z-index: 0; pointer-events: none;
  filter: blur(70px); opacity: var(--aurora-opacity, 0.30); }
.aurora b { position: absolute; border-radius: 50%; mix-blend-mode: screen; }
.aurora .b1 { width: 46vmax; height: 46vmax; left: -6vw; top: -8vh;
  background: radial-gradient(circle, oklch(0.7 0.16 30) 0%, transparent 60%);
  animation: drift1 26s var(--ease) infinite alternate; }
.aurora .b2 { width: 40vmax; height: 40vmax; right: -4vw; top: 12vh;
  background: radial-gradient(circle, oklch(0.65 0.16 290) 0%, transparent 60%);
  animation: drift2 32s var(--ease) infinite alternate; }
.aurora .b3 { width: 34vmax; height: 34vmax; left: 30vw; bottom: -16vh;
  background: radial-gradient(circle, oklch(0.66 0.15 245) 0%, transparent 62%);
  animation: drift3 38s var(--ease) infinite alternate; }
@keyframes drift1 { to { transform: translate(8vw, 6vh) scale(1.12); } }
@keyframes drift2 { to { transform: translate(-6vw, 8vh) scale(1.08); } }
@keyframes drift3 { to { transform: translate(4vw, -8vh) scale(1.15); } }
@media (prefers-reduced-motion: reduce) { .aurora b { animation: none; } }

/* ============================================================
   Panel — plein écran Electron (override du prototype)
   ============================================================ */
.panel { position: relative; z-index: 1; width: 100%; height: 100%;
  border-radius: 0; border: none;
  background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0.0)), var(--void-2);
  overflow: hidden; display: flex; flex-direction: column; }
.panel::before { content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: radial-gradient(var(--grid-dot) 1px, transparent 1px);
  background-size: 22px 22px;
  mask-image: linear-gradient(180deg, transparent 0, #000 8%, #000 100%); }

/* ============================================================
   Top bar
   ============================================================ */
.topbar { position: relative; z-index: 3; display: flex; align-items: center; gap: 10px;
  padding: 16px 18px 12px; overflow: hidden; }
.brand { display: flex; align-items: center; gap: 10px; color: var(--ink); flex: 0 0 auto; }
.brand .logo { width: 26px; height: 26px; color: var(--ink); opacity: 0.95; display: flex; align-items: center; }
.brand .wordmark { font-weight: 700; font-size: 16px; letter-spacing: -0.01em; white-space: nowrap; }
.topbar .spacer { flex: 1; }
.pill-stat { font-family: var(--font-mono); font-size: 10.5px; color: var(--ink-3);
  border: 1px solid var(--stroke); border-radius: var(--r-pill); white-space: nowrap; flex: 0 0 auto;
  padding: 5px 10px; background: var(--glass); display: inline-flex; gap: 7px; align-items: center; }
.pill-stat .dot { width: 5px; height: 5px; border-radius: 50%; background: var(--d-plantes); box-shadow: 0 0 8px var(--d-plantes); }
.modeswitch { display: inline-flex; padding: 3px; gap: 2px; border-radius: var(--r-pill);
  background: var(--glass); border: 1px solid var(--stroke); flex: 0 0 auto; }
.modeswitch button { all: unset; cursor: pointer; font-family: var(--font-mono); font-size: 10px;
  letter-spacing: 0.02em; text-transform: uppercase; color: var(--ink-3); white-space: nowrap;
  padding: 6px 10px; border-radius: var(--r-pill); transition: all .25s var(--ease);
  display: flex; align-items: center; gap: 6px; }
.modeswitch button.active { background: var(--glass-hi); color: var(--ink); }
.modeswitch button:hover:not(.active) { color: var(--ink-2); }
.modeswitch svg { width: 13px; height: 13px; }

/* ============================================================
   Scroll body
   ============================================================ */
.scroll { position: relative; z-index: 2; flex: 1; overflow-y: auto; overflow-x: hidden; padding: 6px 20px 90px; }

/* ============================================================
   À la une
   ============================================================ */
.une-head { display: flex; align-items: center; gap: 10px; margin: 8px 2px 12px; }
.une-head .star { width: 13px; height: 13px; color: var(--d-une); }
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

/* ============================================================
   Domain dot + meta time (shared)
   ============================================================ */
.ddot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent);
  box-shadow: 0 0 10px 0 color-mix(in oklch, var(--accent) 70%, transparent); flex: 0 0 auto; }
.metatime { font-family: var(--font-mono); font-size: 10.5px; color: var(--ink-3); letter-spacing: 0.02em; }

/* ============================================================
   Chat bar
   ============================================================ */
.chat { position: relative; margin: 10px 2px 4px; }
.chat .field { display: flex; align-items: center; gap: 12px; padding: 14px 16px;
  border-radius: 14px; border: 1px solid var(--stroke); background: var(--glass);
  backdrop-filter: blur(var(--blur)); -webkit-backdrop-filter: blur(var(--blur));
  transition: border-color .25s var(--ease), background .25s var(--ease); }
.chat .field:focus-within { border-color: var(--stroke-hi); background: var(--glass-2); }
.chat svg { width: 17px; height: 17px; color: var(--ink-3); flex: 0 0 auto; }
.chat input { all: unset; flex: 1; font-family: var(--font-ui); font-size: 14px; color: var(--ink); }
.chat input::placeholder { color: var(--ink-3); }
.chat .kbd { font-family: var(--font-mono); font-size: 10px; color: var(--ink-4);
  border: 1px solid var(--stroke); border-radius: 6px; padding: 3px 6px; }
.chat-response { background: var(--glass-2); border: 1px solid var(--stroke); border-radius: var(--r-inner);
  padding: 12px 15px; margin-top: 8px; font-size: 13px; color: var(--ink-2); line-height: 1.7; white-space: pre-wrap; }

/* ============================================================
   Filter bar
   ============================================================ */
.filters { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 18px 2px 14px; }
.fpill { all: unset; cursor: pointer; display: inline-flex; align-items: center; gap: 7px;
  font-size: 12px; color: var(--ink-2); padding: 7px 12px; border-radius: var(--r-pill);
  border: 1px solid var(--stroke); background: var(--glass); transition: all .22s var(--ease); }
.fpill:hover { color: var(--ink); border-color: var(--stroke-hi); }
.fpill.active { color: var(--ink); background: var(--glass-hi); border-color: var(--stroke-hi); }
.fpill .ddot { width: 6px; height: 6px; box-shadow: none; }
.filters .sep { width: 1px; height: 18px; background: var(--stroke); margin: 0 2px; }
.fpill.toggle.active { background: color-mix(in oklch, var(--d-apprentissage) 16%, var(--glass)); }
.fpill svg { width: 13px; height: 13px; }

/* ============================================================
   Sections
   ============================================================ */
.section { margin-bottom: 8px; }
.shead { display: flex; align-items: center; gap: 10px; padding: 12px 2px; cursor: pointer; user-select: none; }
.shead .ddot { width: 7px; height: 7px; }
.shead .slabel { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.16em;
  text-transform: uppercase; color: var(--ink-2); font-weight: 500; }
.shead .scount { font-family: var(--font-mono); font-size: 11px; color: var(--ink-4); }
.shead .line { flex: 1; height: 1px; background: linear-gradient(90deg, var(--stroke), transparent); }
.shead .chev { width: 14px; height: 14px; color: var(--ink-3); transition: transform .3s var(--ease); display: flex; }
.shead.collapsed .chev { transform: rotate(-90deg); }
.cards { display: flex; flex-direction: column; gap: 10px; overflow: hidden; }

/* ============================================================
   Note card
   ============================================================ */
.ncard { position: relative; cursor: pointer; text-align: left; width: 100%;
  border-radius: var(--r-card); border: 1px solid var(--stroke); background: var(--glass);
  backdrop-filter: blur(var(--blur)); -webkit-backdrop-filter: blur(var(--blur));
  padding: 14px 16px 13px;
  transition: transform .25s var(--ease-out), border-color .25s var(--ease), background .25s var(--ease);
  overflow: hidden; }
.ncard:hover { transform: translateX(2px); border-color: var(--stroke-hi); background: var(--glass-2); }
.ncard::after { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 2px;
  background: var(--accent); opacity: 0; transition: opacity .25s var(--ease); }
.ncard:hover::after { opacity: 0.8; }
.ncard.highlighted { border-color: color-mix(in oklch, var(--accent) 60%, var(--stroke-hi)); }
.ncard .row1 { display: flex; align-items: center; gap: 9px; }
.ncard .ntitle { font-weight: 600; font-size: 14px; letter-spacing: -0.005em; color: var(--ink); }
.ncard .ninsight { font-size: 12.5px; line-height: 1.45; color: var(--ink-2); margin-top: 6px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ncard .nfoot { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
.ncard .tag { font-family: var(--font-mono); font-size: 10px; color: var(--ink-3); }
.ncard .meta-badge { display: inline-flex; align-items: center; gap: 5px; margin-left: auto; }
.ncard .link-ic { width: 13px; height: 13px; color: var(--ink-3); }
.metachip { font-family: var(--font-mono); font-size: 9.5px; letter-spacing: 0.08em; text-transform: uppercase;
  color: color-mix(in oklch, var(--d-meta) 80%, white);
  border: 1px solid color-mix(in oklch, var(--d-meta) 35%, transparent);
  background: color-mix(in oklch, var(--d-meta) 12%, transparent);
  border-radius: var(--r-pill); padding: 3px 8px; }

/* ============================================================
   Corner stats
   ============================================================ */
.corner { position: absolute; z-index: 3; font-family: var(--font-mono); font-size: 10px;
  color: var(--ink-4); line-height: 1.7; letter-spacing: 0.04em; pointer-events: none; }
.corner.bl { left: 20px; bottom: 16px; }
.corner.br { right: 20px; bottom: 16px; text-align: right; }

/* ============================================================
   Entrance animation
   ============================================================ */
@keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
.enter { animation: fadeUp .5s var(--ease-out) both; }

/* ============================================================
   Modal
   ============================================================ */
.scrim { position: absolute; inset: 0; z-index: 20; display: grid; place-items: center; padding: 28px;
  background: rgba(6,6,10,0.55); backdrop-filter: blur(10px) saturate(0.9);
  -webkit-backdrop-filter: blur(10px) saturate(0.9);
  animation: scrimIn .28s var(--ease) both; }
@keyframes scrimIn { from { opacity: 0; } to { opacity: 1; } }
.modal { position: relative; width: min(540px, 100%); max-height: 92%; display: flex; flex-direction: column;
  border-radius: 20px; border: 1px solid var(--stroke-hi); overflow: hidden;
  background: var(--void-2); box-shadow: var(--shadow-modal);
  animation: modalIn .42s var(--ease-out) both; }
@keyframes modalIn { from { opacity: 0; transform: translateY(16px) scale(0.98); } to { opacity: 1; transform: none; } }
.modal .mhead { position: relative; height: 168px; flex: 0 0 auto; overflow: hidden;
  border-bottom: 1px solid var(--stroke); }
.modal .mhead .au { position: absolute; inset: -40% -20%; filter: blur(34px); opacity: 0.9; }
.modal .mhead .au .a1 { position: absolute; width: 60%; height: 90%; left: -6%; top: -10%; border-radius: 50%;
  background: radial-gradient(circle, color-mix(in oklch, var(--accent) 80%, transparent), transparent 60%); }
.modal .mhead .au .a2 { position: absolute; width: 55%; height: 80%; right: -8%; bottom: -16%; border-radius: 50%;
  background: radial-gradient(circle, oklch(0.62 0.16 290) 0%, transparent 62%); mix-blend-mode: screen; }
.modal .mhead .au .a3 { position: absolute; width: 50%; height: 70%; right: 18%; top: -6%; border-radius: 50%;
  background: radial-gradient(circle, oklch(0.7 0.14 30) 0%, transparent 62%); mix-blend-mode: screen; }
.modal .mhead .grain { position: absolute; inset: 0;
  background-image: radial-gradient(rgba(255,255,255,0.05) 1px, transparent 1px); background-size: 20px 20px; }
.modal .mhead .htext { position: absolute; left: 22px; right: 22px; bottom: 18px; z-index: 2; }
.modal .mhead .domrow { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; }
.modal .mhead .domrow .ddot { width: 8px; height: 8px; }
.modal .mhead .domlabel { font-family: var(--font-mono); font-size: 10.5px; letter-spacing: 0.16em;
  text-transform: uppercase; color: rgba(255,255,255,0.85); }
.modal .mhead h2 { margin: 0; font-size: 23px; line-height: 1.12; letter-spacing: -0.02em; color: #fff;
  font-weight: 700; text-wrap: balance; }
.modal .closebtn { position: absolute; top: 14px; right: 14px; z-index: 4; width: 32px; height: 32px;
  display: grid; place-items: center; border-radius: 50%; border: 1px solid var(--stroke-hi);
  background: rgba(10,10,14,0.5); color: var(--ink-2); cursor: pointer; transition: all .2s var(--ease); }
.modal .closebtn:hover { color: #fff; background: rgba(10,10,14,0.8); }
.modal .navbtn { position: absolute; top: 14px; z-index: 4; width: 32px; height: 32px;
  display: grid; place-items: center; border-radius: 50%; border: 1px solid var(--stroke);
  background: rgba(10,10,14,0.5); color: var(--ink-3); cursor: pointer; transition: all .2s var(--ease); }
.modal .navbtn:hover { color: #fff; border-color: var(--stroke-hi); }
.modal .navbtn.prev { right: 90px; } .modal .navbtn.next { right: 52px; }
.modal .mbody { padding: 20px 22px 22px; overflow-y: auto; }
.modal .insight-box { display: flex; gap: 11px; padding: 14px 15px; border-radius: var(--r-inner);
  border: 1px solid color-mix(in oklch, var(--accent) 28%, transparent);
  background: color-mix(in oklch, var(--accent) 9%, transparent); }
.modal .insight-box .bar { width: 3px; border-radius: 99px; background: var(--accent); flex: 0 0 auto;
  box-shadow: 0 0 12px var(--accent); }
.modal .insight-box .it { font-size: 15px; line-height: 1.4; color: var(--ink); font-weight: 500; letter-spacing: -0.01em; }
.modal .blocklabel { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.16em;
  text-transform: uppercase; color: var(--ink-3); margin: 20px 0 8px; }
.modal .resume { font-size: 14px; line-height: 1.6; color: var(--ink-2); }
.modal .tags { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 8px; }
.modal .tagpill { font-family: var(--font-mono); font-size: 10.5px; color: var(--ink-2);
  border: 1px solid var(--stroke); background: var(--glass); border-radius: var(--r-pill); padding: 4px 10px; }
.modal .linked { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.modal .lrow { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px;
  cursor: pointer; border: 1px solid var(--stroke); background: var(--glass);
  transition: all .2s var(--ease); text-align: left; width: 100%; }
.modal .lrow:hover { border-color: var(--stroke-hi); background: var(--glass-2); transform: translateX(2px); }
.modal .lrow .ddot { width: 6px; height: 6px; }
.modal .lrow .lt { font-size: 13px; color: var(--ink); flex: 1; }
.modal .lrow svg { width: 13px; height: 13px; color: var(--ink-3); }
.modal .mfoot { display: flex; align-items: center; gap: 8px; margin-top: 20px;
  padding-top: 14px; border-top: 1px solid var(--stroke); }
.modal .scoremeter { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.modal .scoremeter .track { width: 70px; height: 4px; border-radius: 99px; background: var(--glass-hi); overflow: hidden; }
.modal .scoremeter .fill { height: 100%; background: var(--accent); border-radius: 99px; }

/* ============================================================
   Constellation
   ============================================================ */
.constel { position: absolute; inset: 0; z-index: 2; overflow: hidden; cursor: grab; }
.constel:active { cursor: grabbing; }
.constel .world { position: absolute; inset: 0; transform-origin: 0 0; }
.constel svg.links { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; }
.constel .edge { fill: none; stroke: var(--stroke); stroke-width: 1.3;
  transition: stroke .3s var(--ease), stroke-width .3s var(--ease); }
.constel .edge.lit { stroke: color-mix(in oklch, var(--accent) 70%, transparent); stroke-width: 1.8; }
.cnode { position: absolute; transform: translate(-50%, -50%); cursor: pointer; }
.cnode .bubble { display: flex; align-items: center; gap: 8px; padding: 9px 13px 9px 11px;
  border-radius: var(--r-pill); border: 1px solid var(--stroke); background: var(--glass);
  backdrop-filter: blur(var(--blur)); -webkit-backdrop-filter: blur(var(--blur));
  white-space: nowrap; transition: all .25s var(--ease-out); box-shadow: var(--shadow-card); }
.cnode:hover .bubble, .cnode.active .bubble {
  border-color: color-mix(in oklch, var(--accent) 60%, var(--stroke-hi));
  background: var(--glass-2); transform: scale(1.05);
  box-shadow: 0 0 24px color-mix(in oklch, var(--accent) 30%, transparent); }
.cnode .ddot { width: 8px; height: 8px; }
.cnode .ct { font-size: 12.5px; color: var(--ink); font-weight: 500; max-width: 150px;
  overflow: hidden; text-overflow: ellipsis; }
.cnode.meta .bubble { border-style: dashed; }
.constel .legend { position: absolute; left: 18px; bottom: 46px; z-index: 5;
  display: flex; flex-wrap: wrap; gap: 9px 14px; max-width: 320px; pointer-events: none; }
.constel .legend .li { display: flex; align-items: center; gap: 6px; }
.constel .legend .li .ddot { width: 6px; height: 6px; box-shadow: none; }
.constel .legend .li span { font-family: var(--font-mono); font-size: 9.5px;
  letter-spacing: 0.04em; color: var(--ink-3); text-transform: uppercase; }
.constel .hint { position: absolute; right: 18px; top: 70px; z-index: 5;
  font-family: var(--font-mono); font-size: 10px; color: var(--ink-4); pointer-events: none; }

/* ============================================================
   Utility
   ============================================================ */
.hidden { display: none !important; }
```

- [ ] **Step 3 : Commit**

```bash
cd C:\Users\yapa\second_cerveau
git add brain_app/style.css brain_app/logo.svg
git commit -m "feat: dark-cosmos design system — tokens, composants, constellation"
```

---

### Task 2 : index.html — réécriture complète

**Files:**
- Modify: `brain_app/index.html`

- [ ] **Step 1 : Réécrire brain_app/index.html**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'self' 'unsafe-inline' https://api.fontshare.com https://cdn.fontshare.com https://fonts.googleapis.com https://fonts.gstatic.com; connect-src http://127.0.0.1:7842; font-src 'self' data: https://cdn.fontshare.com https://fonts.gstatic.com">
  <title>Second Cerveau</title>
  <link rel="preconnect" href="https://api.fontshare.com" crossorigin>
  <link href="https://api.fontshare.com/v2/css?f[]=satoshi@400,500,700,900&display=swap" rel="stylesheet">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="style.css">
</head>
<body>

  <div class="stage">
    <!-- Aurora blobs (animés par CSS) -->
    <div class="aurora"><b class="b1"></b><b class="b2"></b><b class="b3"></b></div>

    <!-- Panneau principal -->
    <div class="panel" id="panel">

      <!-- Top bar -->
      <div class="topbar" id="topbar">
        <div class="brand">
          <span class="logo" id="logo-slot"></span>
          <span class="wordmark">Second Cerveau</span>
        </div>
        <span class="spacer"></span>
        <div class="modeswitch">
          <button id="btn-grille"></button>
          <button id="btn-constellation"></button>
        </div>
        <span class="pill-stat" id="pill-stat"><span class="dot"></span></span>
      </div>

      <!-- Vue Grille -->
      <div id="grille-view" class="scroll">

        <div class="une-head" id="une-head">
          <span class="star" id="star-icon"></span>
          <span class="uppercase-label" style="color:var(--d-une)">À la une</span>
        </div>
        <div class="rail" id="featured-cards"></div>

        <div class="chat" id="chat-bar">
          <div class="field">
            <span id="spark-icon"></span>
            <input type="text" id="chat-input" placeholder="Pose une question à tes notes…" autocomplete="off">
            <span class="kbd">↵</span>
          </div>
          <div id="chat-response" class="chat-response hidden"></div>
        </div>

        <div class="filters" id="filter-bar"></div>

        <div id="sections-container"></div>

      </div><!-- /grille-view -->

      <!-- Vue Constellation (cachée par défaut) -->
      <div id="constel-view" class="hidden"></div>

      <!-- Stats de coin (grille uniquement) -->
      <div class="corner bl" id="corner-bl"></div>
      <div class="corner br" id="corner-br"></div>

    </div><!-- /panel -->
  </div><!-- /stage -->

  <script type="module" src="renderer.js"></script>
</body>
</html>
```

- [ ] **Step 2 : Vérifier que l'app charge sans erreur console**

Lancer l'app :
```bash
cd C:\Users\yapa\second_cerveau\brain_app
npx electron .
```

Ouvrir DevTools (Ctrl+Shift+I) → Console. Expected : fond dark cosmos visible, aucune erreur rouge. Fermer avec Alt+F4.

- [ ] **Step 3 : Commit**

```bash
cd C:\Users\yapa\second_cerveau
git add brain_app/index.html
git commit -m "feat: index.html — structure complète dark-cosmos"
```

---

### Task 3 : renderer.js — grille, modal, chat RAG

**Files:**
- Modify: `brain_app/renderer.js`

- [ ] **Step 1 : Réécrire brain_app/renderer.js**

```javascript
import { animate, stagger } from './node_modules/animejs/dist/modules/index.js';

const API = window.BRAIN_API_URL || 'http://127.0.0.1:7842';

// ── Domain config ─────────────────────────────────────────────────────────────

const DOMAINS = {
  'Travail':           { key: 'travail',       label: 'Travail',       color: 'var(--d-travail)' },
  'Apprentissage':     { key: 'apprentissage', label: 'Apprentissage', color: 'var(--d-apprentissage)' },
  'Projets perso':     { key: 'projets',       label: 'Projets perso', color: 'var(--d-projets)' },
  'Jeux vidéos':       { key: 'jeux',          label: 'Jeux vidéos',   color: 'var(--d-jeux)' },
  'Plantes':           { key: 'plantes',       label: 'Plantes',       color: 'var(--d-plantes)' },
  'Organisation TDAH': { key: 'tdah',          label: 'Organisation',  color: 'var(--d-tdah)' },
};
const DOMAIN_ORDER = ['Travail', 'Apprentissage', 'Projets perso', 'Jeux vidéos', 'Plantes', 'Organisation TDAH'];
const META_DOM = { key: 'meta', label: 'Méta-fiches', color: 'var(--d-meta)' };

// ── SVG Icons ─────────────────────────────────────────────────────────────────

const ICONS = {
  logo: `<svg viewBox="0 0 64 64" fill="none" width="26" height="26">
    <circle cx="32" cy="32" r="9.5" stroke="currentColor" stroke-width="2.4"/>
    <circle cx="32" cy="32" r="2.6" fill="currentColor"/>
    <ellipse cx="32" cy="32" rx="22" ry="22" stroke="currentColor" stroke-width="1.4" opacity="0.28"/>
    <circle cx="51" cy="21" r="3.4" fill="currentColor"/>
    <circle cx="14" cy="44" r="2.6" fill="currentColor"/>
    <path d="M40.5 27 C45 23.5, 47.5 22.5, 51 21" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
    <path d="M24 38 C19.5 41, 16.5 42.5, 14 44" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
  </svg>`,
  star: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <path d="M12 3l2.4 5.6 6 .5-4.6 4 1.4 5.9L12 16.9 6.8 19l1.4-5.9L3.6 9.1l6-.5L12 3z" fill="currentColor"/>
  </svg>`,
  spark: `<svg viewBox="0 0 24 24" fill="none" width="17" height="17">
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  </svg>`,
  chev: `<svg viewBox="0 0 24 24" fill="none" width="14" height="14">
    <path d="M6 9l6 6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  link: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <path d="M9 12h6M10 8H8a4 4 0 100 8h2M14 8h2a4 4 0 110 8h-2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
  </svg>`,
  clock: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <circle cx="12" cy="12" r="8.5" stroke="currentColor" stroke-width="1.7"/>
    <path d="M12 7.5V12l3 2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
  </svg>`,
  grid: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <rect x="3.5" y="3.5" width="7" height="7" rx="1.6" stroke="currentColor" stroke-width="1.8"/>
    <rect x="13.5" y="3.5" width="7" height="7" rx="1.6" stroke="currentColor" stroke-width="1.8"/>
    <rect x="3.5" y="13.5" width="7" height="7" rx="1.6" stroke="currentColor" stroke-width="1.8"/>
    <rect x="13.5" y="13.5" width="7" height="7" rx="1.6" stroke="currentColor" stroke-width="1.8"/>
  </svg>`,
  nodes: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <circle cx="6" cy="6" r="2.6" stroke="currentColor" stroke-width="1.8"/>
    <circle cx="18" cy="9" r="2.6" stroke="currentColor" stroke-width="1.8"/>
    <circle cx="9" cy="18" r="2.6" stroke="currentColor" stroke-width="1.8"/>
    <path d="M8.1 7.2C12 8 14 8.2 15.6 8.4M7.4 8.3c.6 3 .9 5 1.1 7.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`,
  close: `<svg viewBox="0 0 24 24" fill="none" width="15" height="15">
    <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  </svg>`,
  arrow: `<svg viewBox="0 0 24 24" fill="none" width="15" height="15">
    <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  arrowLeft: `<svg viewBox="0 0 24 24" fill="none" width="15" height="15">
    <path d="M19 12H5M11 6l-6 6 6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
};

// ── State ─────────────────────────────────────────────────────────────────────

let state = {
  mode: 'grille',
  notes: [],
  featured: [],
  status: { total_notes: 0, meta_fiches_count: 0, last_sync: null },
  activeFilter: 'tous',
  sort: 'recent',
  linkedOnly: false,
  openNote: null,
  filteredList: [],
};

function getFiltered() {
  let list = state.notes.slice();
  if (state.activeFilter !== 'tous') list = list.filter(n => n.domaine === state.activeFilter);
  if (state.linkedOnly) list = list.filter(n => n.liens.length > 0);
  // recent = ascending _days (0 = today first)
  list.sort((a, b) => state.sort === 'recent' ? a._days - b._days : b._days - a._days);
  return list;
}

function setState(patch) {
  Object.assign(state, patch);
  const needsFilter = ['activeFilter', 'sort', 'linkedOnly', 'notes'].some(k => k in patch);
  if (needsFilter) state.filteredList = getFiltered();
  render();
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function daysAgo(dateStr) {
  if (!dateStr) return 999;
  return Math.max(0, Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000));
}

function relTime(days) {
  if (days <= 0) return "aujourd'hui";
  if (days === 1) return 'hier';
  if (days < 7) return `il y a ${days} j`;
  if (days < 30) return `il y a ${Math.round(days / 7)} sem`;
  return `il y a ${Math.round(days / 30)} mois`;
}

function relTimeFromDate(dateStr) {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "à l'instant";
  if (mins < 60) return `il y a ${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `il y a ${hours}h`;
  return relTime(Math.floor(hours / 24));
}

function parseTags(raw) {
  if (!raw) return [];
  try { const p = JSON.parse(raw); return Array.isArray(p) ? p : []; }
  catch { return String(raw).split(',').map(t => t.trim()).filter(Boolean); }
}

function parseLiens(sourcesIds) {
  if (!sourcesIds) return [];
  try { const p = JSON.parse(sourcesIds); return Array.isArray(p) ? p.map(String) : []; }
  catch { return []; }
}

function domainConfig(domaine) {
  return DOMAINS[domaine] || { key: 'unknown', label: domaine || '?', color: 'var(--ink-3)' };
}

function mapNote(raw) {
  return {
    ...raw,
    id: String(raw.id),
    titre: raw.titre_court || '—',
    insight: raw.insight_cle || '',
    est_meta: Boolean(raw.est_meta_fiche),
    liens: parseLiens(raw.sources_ids),
    parsedTags: parseTags(raw.tags),
    _days: daysAgo(raw.date_capture),
  };
}

// ── Render: topbar ────────────────────────────────────────────────────────────

function renderTopbar() {
  document.getElementById('logo-slot').innerHTML = ICONS.logo;
  document.getElementById('star-icon').innerHTML = ICONS.star;
  document.getElementById('spark-icon').innerHTML = ICONS.spark;

  const btnG = document.getElementById('btn-grille');
  const btnC = document.getElementById('btn-constellation');
  btnG.innerHTML = `${ICONS.grid} Grille`;
  btnC.innerHTML = `${ICONS.nodes} Constellation`;
  btnG.classList.toggle('active', state.mode === 'grille');
  btnC.classList.toggle('active', state.mode === 'constellation');

  if (!btnG._bound) {
    btnG.addEventListener('click', () => setState({ mode: 'grille' }));
    btnC.addEventListener('click', () => setState({ mode: 'constellation' }));
    btnG._bound = true;
  }

  const pill = document.getElementById('pill-stat');
  const { total_notes, meta_fiches_count } = state.status;
  pill.innerHTML = `<span class="dot"></span>${total_notes} notes · ${meta_fiches_count} synthèse${meta_fiches_count !== 1 ? 's' : ''}`;
}

// ── Render: featured cards ────────────────────────────────────────────────────

function renderFeatured() {
  const container = document.getElementById('featured-cards');
  if (!state.featured.length) { container.innerHTML = ''; return; }

  container.innerHTML = state.featured.map(n => {
    const dom = domainConfig(n.domaine);
    return `<div class="fcard" data-id="${n.id}" style="--accent:${dom.color}" tabindex="0" role="button">
      <div class="glow"></div>
      <div class="ftitle">${n.titre}</div>
      <div class="finsight">${n.insight}</div>
      <div class="fmeta">
        <span class="ddot"></span>
        <span class="metatime">${dom.label.toLowerCase()}</span>
        <span class="metatime" style="margin-left:auto">${relTime(n._days)}</span>
      </div>
    </div>`;
  }).join('');

  container.querySelectorAll('.fcard').forEach(el => {
    el.addEventListener('click', () => {
      const note = state.featured.find(n => n.id === el.dataset.id);
      if (note) openModal(note);
    });
  });

  animate(container.querySelectorAll('.fcard'), {
    opacity: [0, 1], translateY: ['10px', '0px'],
    delay: stagger(40), duration: 500, ease: 'outQuart',
  });
}

// ── Render: filters ───────────────────────────────────────────────────────────

function renderFilters() {
  const container = document.getElementById('filter-bar');
  const { activeFilter, sort, linkedOnly } = state;

  container.innerHTML = [
    `<button class="fpill${activeFilter === 'tous' ? ' active' : ''}" data-filter="tous">Tous</button>`,
    ...DOMAIN_ORDER.map(d => {
      const dom = domainConfig(d);
      return `<button class="fpill${activeFilter === d ? ' active' : ''}" data-filter="${d}" style="--accent:${dom.color}"><span class="ddot"></span>${dom.label}</button>`;
    }),
    `<span class="sep"></span>`,
    `<button class="fpill" id="btn-sort">${ICONS.clock}${sort === 'recent' ? 'Récents' : 'Anciens'}</button>`,
    `<button class="fpill toggle${linkedOnly ? ' active' : ''}" id="btn-linked">${ICONS.link}Liées</button>`,
  ].join('');

  container.querySelectorAll('[data-filter]').forEach(btn => {
    btn.addEventListener('click', () => setState({ activeFilter: btn.dataset.filter }));
  });
  document.getElementById('btn-sort').addEventListener('click', () =>
    setState({ sort: state.sort === 'recent' ? 'ancien' : 'recent' }));
  document.getElementById('btn-linked').addEventListener('click', () =>
    setState({ linkedOnly: !state.linkedOnly }));
}

// ── Render: sections ──────────────────────────────────────────────────────────

function renderSections() {
  const container = document.getElementById('sections-container');
  const { filteredList } = state;

  if (!filteredList.length) {
    container.innerHTML = `<div style="text-align:center;color:var(--ink-3);font-family:var(--font-mono);font-size:12px;padding:40px 0">aucune note ne correspond</div>`;
    return;
  }

  const regular = filteredList.filter(n => !n.est_meta);
  const meta = filteredList.filter(n => n.est_meta);
  const groups = {};
  DOMAIN_ORDER.forEach(d => { groups[d] = []; });
  regular.forEach(n => { if (groups[n.domaine]) groups[n.domaine].push(n); });

  let html = '';
  DOMAIN_ORDER.forEach(d => {
    if (!groups[d].length) return;
    html += buildSectionHtml(domainConfig(d), groups[d]);
  });
  if (meta.length) html += buildSectionHtml(META_DOM, meta);

  container.innerHTML = html;

  container.querySelectorAll('.shead').forEach(shead => {
    shead.addEventListener('click', () => {
      shead.classList.toggle('collapsed');
      shead.nextElementSibling?.classList.toggle('hidden');
    });
  });

  container.querySelectorAll('.ncard').forEach(el => {
    el.addEventListener('click', () => {
      const note = state.filteredList.find(n => n.id === el.dataset.id);
      if (note) openModal(note);
    });
  });

  const cards = container.querySelectorAll('.ncard');
  if (cards.length) {
    animate(cards, { opacity: [0, 1], translateY: ['8px', '0px'], delay: stagger(30), duration: 380, ease: 'outCubic' });
  }
}

function buildSectionHtml(dom, notes) {
  const count = String(notes.length).padStart(2, '0');
  return `<div class="section" style="--accent:${dom.color}">
    <div class="shead">
      <span class="ddot"></span>
      <span class="slabel">${dom.label}</span>
      <span class="scount">${count}</span>
      <span class="line"></span>
      <span class="chev">${ICONS.chev}</span>
    </div>
    <div class="cards">${notes.map(buildNoteCardHtml).join('')}</div>
  </div>`;
}

function buildNoteCardHtml(n) {
  const dom = domainConfig(n.domaine);
  const firstTag = n.parsedTags[0];
  const linked = n.liens.length;
  return `<button class="ncard" data-id="${n.id}" style="--accent:${dom.color}">
    <div class="row1">
      <span class="ddot"></span>
      <span class="ntitle">${n.titre}</span>
      ${n.est_meta ? `<span class="metachip" style="margin-left:auto">synthèse</span>` : ''}
    </div>
    <div class="ninsight">${n.insight}</div>
    <div class="nfoot">
      <span class="metatime">${relTime(n._days)}</span>
      ${firstTag ? `<span class="tag">#${firstTag}</span>` : ''}
      ${linked > 0 ? `<span class="meta-badge">${ICONS.link}<span class="metatime">${linked}</span></span>` : ''}
    </div>
  </button>`;
}

// ── Render: corner stats ──────────────────────────────────────────────────────

function renderCornerStats() {
  const { filteredList, status, activeFilter, sort, linkedOnly, mode } = state;
  const bl = document.getElementById('corner-bl');
  const br = document.getElementById('corner-br');
  const show = mode === 'grille';
  bl.classList.toggle('hidden', !show);
  br.classList.toggle('hidden', !show);
  if (!show) return;
  bl.innerHTML = `N: ${String(filteredList.length).padStart(2, '0')} (${status.total_notes})<br>S: ${status.meta_fiches_count} · sync ${relTimeFromDate(status.last_sync)}`;
  br.innerHTML = `${activeFilter === 'tous' ? 'all' : activeFilter}<br>${sort === 'recent' ? '↓ récents' : '↑ anciens'}${linkedOnly ? ' · liées' : ''}`;
}

// ── Modal ─────────────────────────────────────────────────────────────────────

function openModal(note) { setState({ openNote: note }); }
function closeModal()    { setState({ openNote: null }); }

function navModal(dir) {
  if (!state.openNote) return;
  const list = state.filteredList;
  const i = list.findIndex(n => n.id === state.openNote.id);
  const ni = (i + dir + list.length) % list.length;
  setState({ openNote: list[ni] });
}

document.addEventListener('keydown', e => {
  if (!state.openNote) return;
  if (e.key === 'Escape')     closeModal();
  if (e.key === 'ArrowRight') navModal(1);
  if (e.key === 'ArrowLeft')  navModal(-1);
});

function renderModal() {
  const panel = document.getElementById('panel');
  const existing = document.getElementById('modal-scrim');
  if (existing) existing.remove();
  if (!state.openNote) return;

  const note = state.openNote;
  const dom = domainConfig(note.domaine);
  const list = state.filteredList;
  const idx = Math.max(0, list.findIndex(n => n.id === note.id));
  const total = list.length;
  const scoreW = Math.round((note.score_pertinence || 0) * 100);

  const linkedNotes = note.liens
    .map(id => state.notes.find(n => n.id === id))
    .filter(Boolean);

  const tagsHtml = note.parsedTags.length
    ? `<div class="blocklabel">Tags</div><div class="tags">${note.parsedTags.map(t => `<span class="tagpill">#${t}</span>`).join('')}</div>`
    : '';

  const linkedLabel = note.est_meta ? 'Notes sources' : 'Notes liées';
  const linkedHtml = linkedNotes.length
    ? `<div class="blocklabel">${linkedLabel} · ${linkedNotes.length}</div>
       <div class="linked">${linkedNotes.map(l => {
         const ldom = domainConfig(l.domaine);
         return `<button class="lrow" data-linked="${l.id}" style="--accent:${ldom.color}"><span class="ddot"></span><span class="lt">${l.titre}</span>${ICONS.arrow}</button>`;
       }).join('')}</div>`
    : '';

  panel.insertAdjacentHTML('beforeend', `
    <div class="scrim" id="modal-scrim">
      <div class="modal" style="--accent:${dom.color}">
        <div class="mhead">
          <div class="au"><div class="a1"></div><div class="a2"></div><div class="a3"></div></div>
          <div class="grain"></div>
          <button class="navbtn prev" id="modal-prev">${ICONS.arrowLeft}</button>
          <button class="navbtn next" id="modal-next">${ICONS.arrow}</button>
          <button class="closebtn" id="modal-close">${ICONS.close}</button>
          <div class="htext">
            <div class="domrow"><span class="ddot"></span><span class="domlabel">${note.est_meta ? 'Synthèse · ' : ''}${dom.label}</span></div>
            <h2>${note.titre}</h2>
          </div>
        </div>
        <div class="mbody">
          <div class="insight-box"><div class="bar"></div><div class="it">${note.insight}</div></div>
          <div class="blocklabel">Résumé</div>
          <div class="resume">${note.resume || ''}</div>
          ${tagsHtml}
          ${linkedHtml}
          <div class="mfoot">
            <span class="metatime">${relTime(note._days)}</span>
            <span class="metatime">· ${String(idx + 1).padStart(2, '0')} / ${String(total).padStart(2, '0')}</span>
            <div class="scoremeter">
              <span class="metatime">pertinence</span>
              <div class="track"><div class="fill" style="width:${scoreW}%"></div></div>
              <span class="metatime">${(note.score_pertinence || 0).toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `);

  const scrim = document.getElementById('modal-scrim');
  scrim.addEventListener('click', e => { if (e.target === scrim) closeModal(); });
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-prev').addEventListener('click', () => navModal(-1));
  document.getElementById('modal-next').addEventListener('click', () => navModal(1));
  scrim.querySelectorAll('[data-linked]').forEach(btn => {
    btn.addEventListener('click', () => {
      const linked = state.notes.find(n => n.id === btn.dataset.linked);
      if (linked) setState({ openNote: linked });
    });
  });
}

// ── Chat RAG ──────────────────────────────────────────────────────────────────

function initChat() {
  const input = document.getElementById('chat-input');
  const responseEl = document.getElementById('chat-response');

  input.addEventListener('keydown', async e => {
    if (e.key !== 'Enter') return;
    const query = input.value.trim();
    if (!query) return;

    responseEl.classList.remove('hidden');
    responseEl.textContent = 'Recherche en cours…';

    try {
      const data = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      }).then(r => r.json());

      responseEl.textContent = data.reponse || '—';

      document.querySelectorAll('.ncard, .fcard').forEach(el => el.classList.remove('highlighted'));
      if (data.sources?.length) {
        const ids = new Set(data.sources.map(s => String(s.id)));
        document.querySelectorAll('[data-id]').forEach(el => {
          if (ids.has(el.dataset.id)) el.classList.add('highlighted');
        });
      }
    } catch {
      responseEl.textContent = 'Serveur non disponible.';
    }
  });
}

// ── Constellation (placeholder — implémenté en Task 4) ────────────────────────

function renderConstellation() {
  const view = document.getElementById('constel-view');
  view.classList.remove('hidden');
  view.innerHTML = `<div style="display:grid;place-items:center;height:100%;color:var(--ink-3);font-family:var(--font-mono);font-size:12px">Constellation — Task 4</div>`;
}

// ── Render principal ──────────────────────────────────────────────────────────

function renderGrille() {
  document.getElementById('grille-view').classList.remove('hidden');
  document.getElementById('constel-view').classList.add('hidden');
  renderFeatured();
  renderFilters();
  renderSections();
  renderCornerStats();
}

function render() {
  renderTopbar();
  if (state.mode === 'grille') renderGrille();
  else {
    document.getElementById('grille-view').classList.add('hidden');
    renderConstellation();
    renderCornerStats();
  }
  renderModal();
}

// ── Data fetch ────────────────────────────────────────────────────────────────

async function loadData() {
  try {
    const [statusData, featuredRaw, notesRaw] = await Promise.all([
      fetch(`${API}/status`).then(r => r.json()),
      fetch(`${API}/a-la-une?limit=6`).then(r => r.json()),
      fetch(`${API}/notes?limit=200`).then(r => r.json()),
    ]);
    setState({
      status: statusData,
      notes: notesRaw.map(mapNote),
      featured: featuredRaw.map(mapNote),
    });
  } catch {
    document.getElementById('pill-stat').innerHTML = '<span class="dot" style="background:var(--d-projets)"></span>hors ligne';
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

(async () => {
  render();
  initChat();
  await loadData();
  animate('#topbar, #une-head, #featured-cards, #chat-bar, #filter-bar', {
    opacity: [0, 1], translateY: ['8px', '0px'],
    delay: stagger(30), duration: 500, ease: 'outQuart',
  });
})();
```

- [ ] **Step 2 : Démarrer le serveur dans un terminal séparé**

```bash
cd C:\Users\yapa\second_cerveau
python -m uvicorn brain_server:app --host 127.0.0.1 --port 7842
```

- [ ] **Step 3 : Lancer l'app Electron et vérifier la grille**

```bash
cd C:\Users\yapa\second_cerveau\brain_app
npx electron .
```

Expected (DB vide) :
- Fond dark cosmos + aurora + JetBrains Mono / Satoshi chargés
- Topbar avec logo synapse-node + toggle Grille/Constellation
- Rail vide, chat fonctionnel, sections vides
- Pill "0 notes · 0 synthèses"
- Clic sur Constellation → placeholder "Task 4"

Expected (DB avec notes) :
- Featured cards animées au scroll horizontal
- Sections repliables par domaine avec dots colorés oklch
- Clic sur une carte → modale aurora avec insight / résumé / nav clavier

Ouvrir DevTools (Ctrl+Shift+I) → Console : aucune erreur rouge.

- [ ] **Step 4 : Commit**

```bash
cd C:\Users\yapa\second_cerveau
git add brain_app/renderer.js
git commit -m "feat: renderer.js — grille, modal, chat RAG, dark-cosmos"
```

---

### Task 4 : renderer.js — vue Constellation

**Files:**
- Modify: `brain_app/renderer.js`

- [ ] **Step 1 : Remplacer la fonction `renderConstellation` dans renderer.js**

Trouver et remplacer le bloc entier qui va de `// ── Constellation (placeholder — implémenté en Task 4)` jusqu'à la fin de la fonction `renderConstellation()` (la ligne `}`).

Le remplacer par :

```javascript
// ── Constellation ─────────────────────────────────────────────────────────────

let constellationPan = { x: 0, y: 0 };
let constellationDrag = null;
let constellationHover = null;

function computeLayout(notes, w, h) {
  const cx = w / 2, cy = h / 2;
  const R = Math.min(w, h) * 0.26;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const byDom = {};
  notes.forEach(n => { (byDom[n.domaine] = byDom[n.domaine] || []).push(n); });
  const pos = {};

  DOMAIN_ORDER.forEach((dk, di) => {
    const ang = (di / DOMAIN_ORDER.length) * Math.PI * 2 - Math.PI / 2;
    const hx = cx + Math.cos(ang) * R;
    const hy = cy + Math.sin(ang) * R;
    const list = byDom[dk] || [];
    const nonMeta = list.filter(n => !n.est_meta);
    list.forEach((n, i) => {
      if (n.est_meta) {
        pos[n.id] = { x: cx + (i - 0.5) * 26, y: cy };
        return;
      }
      const k = nonMeta.length;
      const a2 = ang + (i - (k - 1) / 2) * 0.5;
      const rr = 64 + (i % 2) * 22;
      pos[n.id] = {
        x: clamp(hx + Math.cos(a2) * rr * 0.55, 96, w - 96),
        y: clamp(hy + Math.sin(a2) * rr,         84, h - 70),
      };
    });
  });

  // Edges (dedup)
  const seen = new Set();
  const edges = [];
  notes.forEach(n => {
    (n.liens || []).forEach(tid => {
      if (!pos[n.id] || !pos[tid]) return;
      const key = [n.id, tid].sort().join('-');
      if (seen.has(key)) return;
      seen.add(key);
      edges.push({ a: n.id, b: tid, key, color: domainConfig(n.domaine).color });
    });
  });

  return { pos, edges };
}

function renderConstellation() {
  const view = document.getElementById('constel-view');
  view.classList.remove('hidden');

  const notes = state.filteredList;
  const w = view.clientWidth  || 800;
  const h = view.clientHeight || 900;
  const { pos, edges } = computeLayout(notes, w, h);
  const pan = constellationPan;
  const hov = constellationHover;

  // Build SVG edges
  const edgeSvg = edges.map(e => {
    const a = pos[e.a], b = pos[e.b];
    if (!a || !b) return '';
    const mx = (a.x + b.x) / 2;
    const my = (a.y + b.y) / 2 - 28;
    const lit = hov && (e.a === hov || e.b === hov);
    const accent = lit ? `style="--accent:${e.color}"` : '';
    return `<path class="edge${lit ? ' lit' : ''}" ${accent} d="M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}"/>`;
  }).join('');

  // Build nodes
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

  // Legend
  const legendHtml = DOMAIN_ORDER.map(d => {
    const dom = domainConfig(d);
    return `<div class="li" style="--accent:${dom.color}"><span class="ddot"></span><span>${dom.label}</span></div>`;
  }).join('');

  view.innerHTML = `
    <div class="constel" id="constel-inner">
      <span class="hint">glisser pour naviguer</span>
      <div class="world" id="constel-world" style="transform:translate(${pan.x}px,${pan.y}px)">
        <svg class="links">${edgeSvg}</svg>
        ${nodesHtml}
      </div>
      <div class="legend">${legendHtml}</div>
    </div>
  `;

  const inner = document.getElementById('constel-inner');

  // Pan
  inner.addEventListener('pointerdown', e => {
    constellationDrag = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  });
  inner.addEventListener('pointermove', e => {
    if (!constellationDrag) return;
    constellationPan = { x: e.clientX - constellationDrag.x, y: e.clientY - constellationDrag.y };
    document.getElementById('constel-world').style.transform = `translate(${constellationPan.x}px,${constellationPan.y}px)`;
  });
  inner.addEventListener('pointerup',    () => { constellationDrag = null; });
  inner.addEventListener('pointerleave', () => { constellationDrag = null; });

  // Hover + click on nodes
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
}
```

- [ ] **Step 2 : Lancer l'app et tester la Constellation**

```bash
cd C:\Users\yapa\second_cerveau\brain_app
npx electron .
```

Expected :
- Clic sur "Constellation" dans la topbar → vue constellation
- Nodes (bulles glass) disposés par domaine autour d'un anneau
- Edges (courbes Bézier SVG) entre notes liées
- Hover sur un node → edges liés s'illuminent (couleur domaine)
- Glisser → déplace le monde (pan)
- Clic sur un node → ouvre la modale identique à la grille
- Légende des domaines en bas-gauche
- Clic sur "Grille" → retour à la grille, pan conservé

- [ ] **Step 3 : Commit**

```bash
cd C:\Users\yapa\second_cerveau
git add brain_app/renderer.js
git commit -m "feat: constellation — nodes SVG, edges Bézier, pan, hover"
```

---

**Plan 3 terminé.** L'app affiche le nouveau design dark-cosmos avec grille filtrée, modale aurora, chat RAG et vue constellation.

## Self-Review

**Spec coverage :**
- ✅ Satoshi + JetBrains Mono — tokens.css → style.css
- ✅ oklch couleurs domaines — 7 variables dans tokens
- ✅ Glass + backdrop-filter sur cards (fcard, ncard, modal, cnode)
- ✅ Logo synapse-node (ICONS.logo)
- ✅ Toggle Grille / Constellation (topbar modeswitch)
- ✅ Rail scroll-x featured cards avec glow hover
- ✅ Chat RAG + highlight sources
- ✅ Filter bar (domaines + tri + liées)
- ✅ Sections repliables + shead avec dot + ligne dégradée + compteur mono
- ✅ ncard : liseré accent au hover, clamp 2 lignes insight, badge synthèse, liens
- ✅ Modale : aurora header teinté --accent, insight-box barre lumineuse, résumé, tags, notes liées, jauge pertinence, nav clavier Esc/←/→
- ✅ Constellation : anneau hubs, noeuds clustered, edges Bézier, hover lit, pan, légende
- ✅ Corner stats (grille uniquement)
- ✅ Aurora 3 blobs CSS (drift1/2/3) + dot-grid masqué topbar
- ✅ Anime.js v4 : fadeUp stagger sur featured + ncard + entrée globale
- ✅ prefers-reduced-motion : aurora b { animation: none }
- ✅ Panel full-screen Electron (override border-radius + border)
- ✅ CSP mise à jour pour Fontshare
- ✅ `.hidden { display: none !important }` présent

**Placeholders scan :** Aucun "TBD" ni "implement later" dans le plan.

**Type consistency :**
- `note.id` → toujours `String` via `mapNote` et `parseLiens`
- `domainConfig(domaine)` → retourne `{ key, label, color }` — utilisé partout de la même façon
- `state.filteredList` → mis à jour dans `setState` avant `render()`
- `constellationPan`, `constellationDrag`, `constellationHover` → variables module-level partagées entre renders
