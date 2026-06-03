// activities/solar.js — Système solaire interactif

export function create(container) {
  container.innerHTML = `
    <canvas id="solar-canvas" style="position:absolute;inset:0;width:100%;height:100%;cursor:default"></canvas>
    <div id="solar-gravity" style="position:absolute;bottom:20px;left:16px;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:10px 14px;font-family:monospace">
      <div style="font-size:8px;letter-spacing:.1em;color:#3a3a4a;margin-bottom:8px">GRAVITÉ</div>
      <label style="display:flex;align-items:center;gap:7px;font-size:10px;color:#4a4a5a;cursor:pointer;margin-bottom:4px">
        <input type="radio" name="grav" value="0"> Faible
      </label>
      <label style="display:flex;align-items:center;gap:7px;font-size:10px;color:#a6a6b6;cursor:pointer;margin-bottom:4px">
        <input type="radio" name="grav" value="1" checked> Normale
      </label>
      <label style="display:flex;align-items:center;gap:7px;font-size:10px;color:#4a4a5a;cursor:pointer">
        <input type="radio" name="grav" value="2"> Forte
      </label>
    </div>
    <div style="position:absolute;top:12px;left:50%;transform:translateX(-50%);font-family:monospace;font-size:9px;color:#2a2a3a;letter-spacing:.1em;white-space:nowrap">
      ATTRAPE LES PLANÈTES ET LANCE-LES
    </div>
  `;

  const canvas = container.querySelector('#solar-canvas');
  const ctx    = canvas.getContext('2d');

  const G_VALUES = [60, 200, 500];
  let G = G_VALUES[1];
  const SUN_MASS = 1e6;

  let rafId    = null;
  let lastTime = 0;

  const sun = { x: 0, y: 0, r: 18 };

  function resize() {
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight;
    sun.x = canvas.width  / 2;
    sun.y = canvas.height / 2;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);

  const PLANET_COLORS = [
    'oklch(0.72 0.15 25)',
    'oklch(0.72 0.13 255)',
    'oklch(0.78 0.14 150)',
  ];

  function makeOrbit(orbitR, color) {
    const angle = Math.random() * Math.PI * 2;
    const speed = Math.sqrt(G * SUN_MASS / Math.max(orbitR, 40));
    return {
      x:  sun.x + Math.cos(angle) * orbitR,
      y:  sun.y + Math.sin(angle) * orbitR,
      vx: -Math.sin(angle) * speed,
      vy:  Math.cos(angle) * speed,
      r: 9,
      color,
      trail: [],
    };
  }

  let planets = [];

  function initPlanets() {
    planets = [100, 165, 235].map((r, i) => makeOrbit(r, PLANET_COLORS[i]));
  }

  let dragging    = null;
  let dragHistory = [];

  canvas.addEventListener('mousedown', e => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    for (const p of planets) {
      if (Math.hypot(mx - p.x, my - p.y) < p.r + 10) {
        dragging    = p;
        dragHistory = [[mx, my, performance.now()]];
        canvas.style.cursor = 'grabbing';
        break;
      }
    }
  });

  canvas.addEventListener('mousemove', e => {
    if (!dragging) return;
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    dragging.x = mx; dragging.y = my;
    dragHistory.push([mx, my, performance.now()]);
    if (dragHistory.length > 6) dragHistory.shift();
  });

  canvas.addEventListener('mouseup', () => {
    if (!dragging) return;
    if (dragHistory.length >= 2) {
      const [x1, y1, t1] = dragHistory[0];
      const [x2, y2, t2] = dragHistory[dragHistory.length - 1];
      const dt = Math.max((t2 - t1) / 1000, 0.01);
      dragging.vx = (x2 - x1) / dt * 0.55;
      dragging.vy = (y2 - y1) / dt * 0.55;
    }
    dragging          = null;
    dragHistory       = [];
    canvas.style.cursor = 'default';
  });

  container.querySelectorAll('input[name="grav"]').forEach(r => {
    r.addEventListener('change', () => { G = G_VALUES[parseInt(r.value)]; });
  });

  function update(dt) {
    const maxEscape = Math.max(canvas.width, canvas.height) * 1.6;
    for (const p of planets) {
      if (p === dragging) continue;
      const dx   = sun.x - p.x;
      const dy   = sun.y - p.y;
      const dist = Math.max(sun.r + p.r, Math.hypot(dx, dy));
      const force = G * SUN_MASS / (dist * dist);
      p.vx += force * (dx / dist) * dt;
      p.vy += force * (dy / dist) * dt;
      p.x  += p.vx * dt;
      p.y  += p.vy * dt;
      p.trail.push({ x: p.x, y: p.y });
      if (p.trail.length > 90) p.trail.shift();

      // Reset escaped planet
      if (Math.hypot(p.x - sun.x, p.y - sun.y) > maxEscape) {
        const fresh = makeOrbit(80 + Math.random() * 180, p.color);
        Object.assign(p, { x: fresh.x, y: fresh.y, vx: fresh.vx, vy: fresh.vy, trail: [] });
      }
    }
  }

  function drawSun() {
    const grad = ctx.createRadialGradient(sun.x, sun.y, 0, sun.x, sun.y, sun.r * 3);
    grad.addColorStop(0,    'oklch(0.95 0.1 90 / 0.9)');
    grad.addColorStop(0.35, 'oklch(0.85 0.14 70 / 0.5)');
    grad.addColorStop(1,    'transparent');
    ctx.beginPath();
    ctx.arc(sun.x, sun.y, sun.r * 3, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.beginPath();
    ctx.arc(sun.x, sun.y, sun.r, 0, Math.PI * 2);
    ctx.fillStyle = 'oklch(0.94 0.1 90)';
    ctx.fill();
  }

  function drawPlanet(p) {
    // Trail
    if (p.trail.length > 1) {
      for (let i = 1; i < p.trail.length; i++) {
        const alpha = (i / p.trail.length) * 0.35;
        ctx.beginPath();
        ctx.moveTo(p.trail[i-1].x, p.trail[i-1].y);
        ctx.lineTo(p.trail[i].x,   p.trail[i].y);
        ctx.strokeStyle = p.color.replace(')', ` / ${alpha.toFixed(2)})`);
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
    // Glow
    const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 2.2);
    glow.addColorStop(0, p.color.replace(')', ' / 0.4)'));
    glow.addColorStop(1, 'transparent');
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r * 2.2, 0, Math.PI * 2);
    ctx.fillStyle = glow;
    ctx.fill();
    // Body
    const body = ctx.createRadialGradient(p.x - p.r*0.3, p.y - p.r*0.3, 0, p.x, p.y, p.r);
    body.addColorStop(0, p.color.replace(')', ' / 0.95)'));
    body.addColorStop(1, p.color.replace(')', ' / 0.65)'));
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fillStyle = body;
    ctx.fill();
  }

  function draw(now) {
    const dt = Math.min((now - lastTime) / 1000, 0.05);
    lastTime = now;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    update(dt);
    drawSun();
    planets.forEach(drawPlanet);
    rafId = requestAnimationFrame(draw);
  }

  function start() {
    resize();
    initPlanets();
    lastTime = performance.now();
    rafId = requestAnimationFrame(draw);
  }

  function stop() {
    if (rafId) cancelAnimationFrame(rafId);
    ro.disconnect();
    container.innerHTML = '';
  }

  return { start, stop };
}
