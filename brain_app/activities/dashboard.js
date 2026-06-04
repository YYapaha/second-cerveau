// activities/dashboard.js — Tableau de bord Aurora

const PANEL_H = 160;

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

  function resize() {
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight - PANEL_H;
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
