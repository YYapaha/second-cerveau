// activities/dashboard.js — Tableau de bord Aurora

const PANEL_H = 160;

export function create(container) {
  const params = {
    hueShift: 0, speed: 1.0, blur: 70, intensity: 0.45,
    scale: 1.0, chaos: 0.3,
    b1: true, b2: true, b3: true, particles: false, lines: false,
  };

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
    ctx.clearRect(0, 0, canvas.width, canvas.height);
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
