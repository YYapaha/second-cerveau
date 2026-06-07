// icons.js — Monoline SVG icon set (currentColor)
// Shared between renderer.js and zen.js

export const ICONS = {
  // ---- UI icons ----
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

  zen: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <path d="M4 16c2.5-2 4-2 6 0s3.5 2 6 0 3.5-2 4-1" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
    <circle cx="12" cy="7" r="2.4" stroke="currentColor" stroke-width="1.7"/>
  </svg>`,

  refresh: `<svg viewBox="0 0 24 24" fill="none" width="14" height="14">
    <path d="M20 11a8 8 0 10-1.8 6.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
    <path d="M20 5v5h-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
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

  ext: `<svg viewBox="0 0 24 24" fill="none" width="12" height="12">
    <path d="M14 5h5v5M19 5l-8 8M18 13v5a1 1 0 01-1 1H6a1 1 0 01-1-1V7a1 1 0 011-1h5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,

  trash: `<svg viewBox="0 0 24 24" fill="none" width="14" height="14">
    <path d="M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,

  plus: `<svg viewBox="0 0 24 24" fill="none" width="12" height="12">
    <path d="M12 6v12M6 12h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
  </svg>`,

  trier: `<svg viewBox="0 0 24 24" fill="none" width="13" height="13">
    <path d="M3 6h18M7 12h10M11 18h2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
  </svg>`,

  // ---- Zen activity icons ----
  target: `<svg viewBox="0 0 24 24" fill="none" width="26" height="26">
    <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.7"/>
    <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.7"/>
    <circle cx="12" cy="12" r="1.2" fill="currentColor"/>
  </svg>`,

  orbit: `<svg viewBox="0 0 24 24" fill="none" width="26" height="26">
    <circle cx="12" cy="12" r="3" fill="currentColor"/>
    <ellipse cx="12" cy="12" rx="9" ry="4.2" stroke="currentColor" stroke-width="1.6"/>
    <circle cx="21" cy="12" r="1.6" fill="currentColor"/>
  </svg>`,

  lungs: `<svg viewBox="0 0 24 24" fill="none" width="26" height="26">
    <path d="M12 4v8" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
    <path d="M9 9c0 4-1 5-1 7 0 2-2 3-3 2s-1-5 0-8 3-3 4-1zM15 9c0 4 1 5 1 7 0 2 2 3 3 2s1-5 0-8-3-3-4-1z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,

  sparkles: `<svg viewBox="0 0 24 24" fill="none" width="26" height="26">
    <path d="M12 4l1.6 4.4L18 10l-4.4 1.6L12 16l-1.6-4.4L6 10l4.4-1.6L12 4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
    <circle cx="18.5" cy="17.5" r="1.2" fill="currentColor"/>
  </svg>`,

  bubbles: `<svg viewBox="0 0 24 24" fill="none" width="26" height="26">
    <circle cx="9" cy="13" r="5" stroke="currentColor" stroke-width="1.6"/>
    <circle cx="17" cy="8" r="3" stroke="currentColor" stroke-width="1.6"/>
  </svg>`,

  sliders: `<svg viewBox="0 0 24 24" fill="none" width="26" height="26">
    <path d="M5 7h14M5 12h14M5 17h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
    <circle cx="9" cy="7" r="2" fill="currentColor"/>
    <circle cx="15" cy="12" r="2" fill="currentColor"/>
    <circle cx="8" cy="17" r="2" fill="currentColor"/>
  </svg>`,

  wave: `<svg viewBox="0 0 24 24" fill="none" width="26" height="26">
    <path d="M3 9c2-2 4-2 6 0s4 2 6 0 4-2 6 0M3 15c2-2 4-2 6 0s4 2 6 0 4-2 6 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  </svg>`,

  ripple: `<svg viewBox="0 0 24 24" fill="none" width="26" height="26">
    <circle cx="12" cy="12" r="2" stroke="currentColor" stroke-width="1.6"/>
    <path d="M12 6.5a5.5 5.5 0 010 11M12 3a9 9 0 010 18" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" opacity="0.6"/>
  </svg>`,

  kaleido: `<svg viewBox="0 0 24 24" fill="none" width="26" height="26">
    <path d="M12 3l4 5-4 4-4-4 4-5zM12 21l-4-5 4-4 4 4-4 5zM3 12l5-4 4 4-4 4-5-4zM21 12l-5 4-4-4 4-4 5 4z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
  </svg>`,

  // backward-compat alias used in renderer.js
  externalLink: `<svg viewBox="0 0 24 24" fill="none" width="12" height="12">
    <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
};
