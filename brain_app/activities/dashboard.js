// activities/dashboard.js — Tableau de bord Aurora

const PANEL_H = 160;

const SLIDER_CONFIGS = [
  { param: 'hueShift',  label: 'HUE',      color: 'oklch(0.72 0.15 25)',  min: 0,   max: 360 },
  { param: 'speed',     label: 'VITESSE',   color: 'oklch(0.72 0.13 255)', min: 0.1, max: 3.0 },
  { param: 'blur',      label: 'BLUR',      color: 'oklch(0.65 0.16 290)', min: 20,  max: 120 },
  { param: 'intensity', label: 'INTENSITÉ', color: 'oklch(0.78 0.14 150)', min: 0.1, max: 1.0 },
];

export function create(container) {
  const params = {
    hueShift: 0, speed: 1.0, blur: 70, intensity: 0.45,
    scale: 1.0, chaos: 0.3,
    b1: true, b2: true, b3: true, particles: false, lines: false,
  };

  const blobs = [
    { rx: 220, ry: 160, color: 'oklch(0.7 0.16 30)',   phaseX: 0,   phaseY: 0,   speedX: 0.4,  speedY: 0.3,  driftX: 200, driftY: 120 },
    { rx: 200, ry: 180, color: 'oklch(0.65 0.16 290)', phaseX: 2.1, phaseY: 1.4, speedX: 0.3,  speedY: 0.5,  driftX: 180, driftY: 140 },
    { rx: 240, ry: 150, color: 'oklch(0.66 0.15 245)', phaseX: 4.2, phaseY: 3.1, speedX: 0.5,  speedY: 0.25, driftX: 220, driftY: 100 },
  ];
  const BLOB_KEYS = ['b1', 'b2', 'b3'];

  let pts = [];

  function initParticles(W, H) {
    pts = Array.from({ length: 30 }, () => ({
      x: Math.random() * W,  y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.8, vy: (Math.random() - 0.5) * 0.8,
      r: 2 + Math.random() * 2,
    }));
  }

  function drawParticles() {
    const W = canvas.width, H = canvas.height;
    pts.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,255,255,0.6)';
      ctx.fill();
    });
    if (params.lines) {
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 80) {
            ctx.beginPath();
            ctx.strokeStyle = `rgba(255,255,255,${(1 - dist / 80).toFixed(3)})`;
            ctx.lineWidth = 0.5;
            ctx.moveTo(pts[i].x, pts[i].y);
            ctx.lineTo(pts[j].x, pts[j].y);
            ctx.stroke();
          }
        }
      }
    }
  }

  container.innerHTML = `
    <canvas id="db-canvas" style="position:absolute;top:0;left:0;width:100%;height:calc(100% - ${PANEL_H}px)"></canvas>
    <div id="db-panel" style="
      position:absolute;bottom:0;left:0;right:0;height:${PANEL_H}px;
      display:flex;align-items:center;justify-content:center;gap:24px;padding:0 24px;
      background:rgba(255,255,255,0.04);border-top:1px solid rgba(255,255,255,0.085);
      backdrop-filter:blur(18px);
    ">
      <div id="db-sliders" style="display:flex;gap:12px;align-items:flex-end;height:120px;"></div>
      <div style="width:1px;height:80px;background:rgba(255,255,255,0.085);"></div>
      <div id="db-knobs" style="display:flex;gap:20px;align-items:center;"></div>
      <div style="width:1px;height:80px;background:rgba(255,255,255,0.085);"></div>
      <div id="db-toggles" style="display:flex;flex-direction:column;gap:8px;"></div>
    </div>
  `;

  const canvas = container.querySelector('#db-canvas');
  const ctx = canvas.getContext('2d');

  const slidersEl = container.querySelector('#db-sliders');
  const knobsEl   = container.querySelector('#db-knobs');
  const togglesEl = container.querySelector('#db-toggles');

  // --- Sliders ---
  SLIDER_CONFIGS.forEach(({ param, label, color, min, max }) => {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:6px;width:28px;height:100%;';

    const track = document.createElement('div');
    track.style.cssText = [
      'flex:1;width:6px;position:relative;',
      'background:rgba(255,255,255,0.08);border-radius:3px;',
      'border:1px solid rgba(255,255,255,0.085);cursor:ns-resize;',
    ].join('');

    const fill = document.createElement('div');
    fill.style.cssText = [
      'position:absolute;bottom:0;left:0;right:0;',
      `background:${color};border-radius:3px;pointer-events:none;`,
    ].join('');

    const thumb = document.createElement('div');
    thumb.style.cssText = [
      'position:absolute;left:50%;transform:translateX(-50%);',
      'width:12px;height:4px;background:white;border-radius:2px;pointer-events:none;',
    ].join('');

    track.appendChild(fill);
    track.appendChild(thumb);

    const lbl = document.createElement('span');
    lbl.textContent = label;
    lbl.style.cssText = [
      'font-size:8px;letter-spacing:0.08em;color:rgba(255,255,255,0.45);',
      "font-family:var(--font-mono,'JetBrains Mono',monospace);",
      'writing-mode:vertical-rl;transform:rotate(180deg);user-select:none;',
    ].join('');

    wrap.appendChild(track);
    wrap.appendChild(lbl);
    slidersEl.appendChild(wrap);

    function updateSlider() {
      const t = (params[param] - min) / (max - min);
      fill.style.height  = `${t * 100}%`;
      thumb.style.bottom = `calc(${t * 100}% - 2px)`;
    }

    track.addEventListener('mousedown', e => {
      e.preventDefault();
      function onMove(ev) {
        const rect = track.getBoundingClientRect();
        let t = 1 - (ev.clientY - rect.top) / rect.height;
        t = Math.max(0, Math.min(1, t));
        params[param] = min + t * (max - min);
        updateSlider();
      }
      onMove(e);
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', () => document.removeEventListener('mousemove', onMove), { once: true });
    });

    updateSlider();
  });

  function resize() {
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight - PANEL_H;
    if (params.particles && pts.length) initParticles(canvas.width, canvas.height);
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);

  let rafId = null;

  function draw(now) {
    const t = now * 0.001;
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    blobs.forEach((b, i) => {
      if (!params[BLOB_KEYS[i]]) return;
      const noise = (Math.random() - 0.5) * params.chaos * 40;
      const cx = W * 0.5 + Math.sin(t * b.speedX * params.speed + b.phaseX) * b.driftX + noise;
      const cy = H * 0.5 + Math.sin(t * b.speedY * params.speed + b.phaseY) * b.driftY + noise;
      const s = params.scale;

      ctx.filter = `blur(${params.blur}px) hue-rotate(${params.hueShift}deg)`;
      ctx.globalAlpha = params.intensity;

      const R = Math.max(b.rx, b.ry) * s;
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, R);
      grad.addColorStop(0, b.color);
      grad.addColorStop(1, 'rgba(0,0,0,0)');

      ctx.beginPath();
      ctx.ellipse(cx, cy, b.rx * s, b.ry * s, 0, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();
    });

    ctx.filter = 'none';
    ctx.globalAlpha = 1;

    if (params.particles && pts.length) drawParticles();

    rafId = requestAnimationFrame(draw);
  }

  function start() {
    resize();
    rafId = requestAnimationFrame(draw);
  }

  function stop() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    ro.disconnect();
    container.innerHTML = '';
  }

  return { start, stop };
}
