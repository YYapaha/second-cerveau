// activities/solar.js — Système solaire interactif

export function create(container) {
  container.innerHTML = `
    <canvas id="solar-canvas" style="position:absolute;inset:0;width:100%;height:100%;cursor:default"></canvas>
    <div id="solar-controls" style="position:absolute;bottom:16px;left:16px;background:rgba(0,0,0,0.55);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:11px 14px;font-family:monospace">
      <div style="margin-bottom:10px">
        <div style="font-size:8px;letter-spacing:.12em;color:#3a3a4a;margin-bottom:5px">VITESSE</div>
        <div style="display:flex;gap:4px">
          ${[1,2,3,4,5].map(n => `<button class="sol-spd" data-i="${n-1}" style="font-size:9px;padding:3px 7px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:5px;cursor:pointer;font-family:monospace;color:#5a5a6a">${n}×</button>`).join('')}
        </div>
      </div>
      <div style="margin-bottom:10px">
        <div style="font-size:8px;letter-spacing:.12em;color:#3a3a4a;margin-bottom:5px">PLANÈTES</div>
        <div style="display:flex;align-items:center;gap:8px">
          <button id="sol-less" style="font-size:13px;width:22px;height:22px;line-height:1;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:5px;color:#5a5a6a;cursor:pointer;font-family:monospace">−</button>
          <span id="sol-pcount" style="font-size:11px;color:#8a8a9a;font-family:monospace;min-width:12px;text-align:center">3</span>
          <button id="sol-more" style="font-size:13px;width:22px;height:22px;line-height:1;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:5px;color:#5a5a6a;cursor:pointer;font-family:monospace">+</button>
        </div>
      </div>
      <div>
        <div style="font-size:8px;letter-spacing:.12em;color:#3a3a4a;margin-bottom:5px">GRAVITÉ</div>
        ${[['Faible','0'],['Normale','1'],['Forte','2']].map(([l,v]) =>
          `<label style="display:flex;align-items:center;gap:6px;font-size:10px;cursor:pointer;margin-bottom:3px;color:#4a4a5a"><input type="radio" name="sol-grav" value="${v}"${v==='1'?' checked':''}>${l}</label>`
        ).join('')}
      </div>
    </div>
    <div style="position:absolute;top:12px;left:50%;transform:translateX(-50%);font-family:monospace;font-size:9px;color:#2a2a3a;letter-spacing:.1em;white-space:nowrap">
      ATTRAPE LES PLANÈTES ET LANCE-LES
    </div>
  `;

  const canvas = container.querySelector('#solar-canvas');
  const ctx    = canvas.getContext('2d');

  const G_VALUES    = [60, 200, 500];
  const SPEED_MULTS = [0.12, 0.28, 0.52, 0.76, 1.0];
  const SUN_MASS    = 1e6;

  let G         = G_VALUES[1];
  let speedMult = SPEED_MULTS[2]; // default 3×
  let rafId = null, lastTime = 0;

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
    'oklch(0.75 0.15 300)',
    'oklch(0.80 0.12 50)',
    'oklch(0.70 0.15 200)',
    'oklch(0.75 0.14 350)',
    'oklch(0.78 0.13 100)',
    'oklch(0.72 0.16 0)',
    'oklch(0.78 0.12 220)',
  ];

  function orbitR(i) { return 70 + i * 38; }

  function makePlanet(targetR, color) {
    const angle = Math.random() * Math.PI * 2;
    const spd   = Math.sqrt(G * SUN_MASS / Math.max(targetR, 40));
    return {
      x: sun.x + Math.cos(angle) * targetR,
      y: sun.y + Math.sin(angle) * targetR,
      vx: -Math.sin(angle) * spd,
      vy:  Math.cos(angle) * spd,
      r: 9, color, trail: [], targetR,
    };
  }

  let planets = [];
  let dragging = null, dragHistory = [];

  function setCount(n) {
    n = Math.max(1, Math.min(10, n));
    while (planets.length < n) {
      const i = planets.length;
      planets.push(makePlanet(orbitR(i), PLANET_COLORS[i % PLANET_COLORS.length]));
    }
    while (planets.length > n) {
      const last = planets.at(-1);
      if (last !== dragging) {
        planets.pop();
      } else if (planets.length > 1) {
        planets.splice(-2, 1); // can't remove dragged — remove second-to-last
      } else {
        break;
      }
    }
    const c = planets.length;
    container.querySelector('#sol-pcount').textContent = c;
    container.querySelector('#sol-less').style.opacity = c <= 1  ? '0.3' : '1';
    container.querySelector('#sol-more').style.opacity = c >= 10 ? '0.3' : '1';
  }

  // ── Drag interaction ──────────────────────────────────────────────────────────

  canvas.addEventListener('mousedown', e => {
    const { left, top } = canvas.getBoundingClientRect();
    const mx = e.clientX - left, my = e.clientY - top;
    for (const p of planets) {
      if (Math.hypot(mx - p.x, my - p.y) < p.r + 12) {
        dragging    = p;
        dragHistory = [[mx, my, performance.now()]];
        canvas.style.cursor = 'grabbing';
        break;
      }
    }
  });

  canvas.addEventListener('mousemove', e => {
    if (!dragging) return;
    const { left, top } = canvas.getBoundingClientRect();
    const mx = e.clientX - left, my = e.clientY - top;
    dragging.x = mx; dragging.y = my;
    dragHistory.push([mx, my, performance.now()]);
    if (dragHistory.length > 6) dragHistory.shift();
  });

  canvas.addEventListener('mouseup', () => {
    if (!dragging) return;
    if (dragHistory.length >= 2) {
      const [x1, y1, t1] = dragHistory[0];
      const [x2, y2, t2] = dragHistory[dragHistory.length - 1];
      const elapsed = Math.max((t2 - t1) / 1000, 0.01);
      dragging.vx = (x2 - x1) / elapsed * 0.55;
      dragging.vy = (y2 - y1) / elapsed * 0.55;
    }
    dragging.trail = [];
    dragging = null; dragHistory = [];
    canvas.style.cursor = 'default';
  });

  // ── Controls ──────────────────────────────────────────────────────────────────

  const spdBtns = container.querySelectorAll('.sol-spd');
  function highlightSpeed() {
    spdBtns.forEach(b => {
      const on = SPEED_MULTS[+b.dataset.i] === speedMult;
      b.style.color       = on ? '#c8c8d8' : '#5a5a6a';
      b.style.borderColor = on ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.08)';
      b.style.background  = on ? 'rgba(255,255,255,0.1)'  : 'rgba(255,255,255,0.04)';
    });
  }
  spdBtns.forEach(b => b.addEventListener('click', () => {
    speedMult = SPEED_MULTS[+b.dataset.i];
    highlightSpeed();
  }));

  container.querySelector('#sol-less').addEventListener('click', () => setCount(planets.length - 1));
  container.querySelector('#sol-more').addEventListener('click', () => setCount(planets.length + 1));

  container.querySelectorAll('input[name="sol-grav"]').forEach(r => {
    r.addEventListener('change', () => {
      G = G_VALUES[+r.value];
      // Re-derive circular orbit velocities at current positions
      for (const p of planets) {
        if (p === dragging) continue;
        const rx = p.x - sun.x, ry = p.y - sun.y;
        const d  = Math.max(sun.r + p.r, Math.hypot(rx, ry));
        const v  = Math.sqrt(G * SUN_MASS / d);
        p.vx = -ry / d * v;
        p.vy =  rx / d * v;
      }
    });
  });

  // ── Physics ───────────────────────────────────────────────────────────────────

  function update(simDt) {
    const maxEscape = Math.max(canvas.width, canvas.height) * 1.6;
    for (const p of planets) {
      if (p === dragging) continue;

      const rx   = p.x - sun.x, ry = p.y - sun.y;
      const dist = Math.max(sun.r + p.r, Math.hypot(rx, ry));

      // Gravity toward sun
      const f = G * SUN_MASS / (dist * dist);
      p.vx -= f * (rx / dist) * simDt;
      p.vy -= f * (ry / dist) * simDt;

      // Orbit circularization — blends velocity toward CCW circular orbit at current dist
      // Gives planets a gentle "return to orbit" behavior after being thrown
      const orbSpd  = Math.sqrt(G * SUN_MASS / dist);
      const idealVx = -ry / dist * orbSpd;
      const idealVy =  rx / dist * orbSpd;
      const retF    = Math.min(simDt * 0.8, 0.12);
      p.vx += (idealVx - p.vx) * retF;
      p.vy += (idealVy - p.vy) * retF;

      p.x += p.vx * simDt;
      p.y += p.vy * simDt;
      p.trail.push({ x: p.x, y: p.y });
      if (p.trail.length > 90) p.trail.shift();

      // Respawn escaped planet at its original orbit
      if (Math.hypot(p.x - sun.x, p.y - sun.y) > maxEscape) {
        const fresh = makePlanet(p.targetR, p.color);
        Object.assign(p, { x: fresh.x, y: fresh.y, vx: fresh.vx, vy: fresh.vy, trail: [] });
      }
    }
  }

  // ── Drawing ───────────────────────────────────────────────────────────────────

  function drawSun() {
    const g = ctx.createRadialGradient(sun.x, sun.y, 0, sun.x, sun.y, sun.r * 3);
    g.addColorStop(0,    'oklch(0.95 0.1 90 / 0.9)');
    g.addColorStop(0.35, 'oklch(0.85 0.14 70 / 0.5)');
    g.addColorStop(1,    'transparent');
    ctx.beginPath(); ctx.arc(sun.x, sun.y, sun.r * 3, 0, Math.PI * 2);
    ctx.fillStyle = g; ctx.fill();
    ctx.beginPath(); ctx.arc(sun.x, sun.y, sun.r, 0, Math.PI * 2);
    ctx.fillStyle = 'oklch(0.94 0.1 90)'; ctx.fill();
  }

  function drawPlanet(p) {
    // Trail
    if (p.trail.length > 1) {
      for (let i = 1; i < p.trail.length; i++) {
        const a = (i / p.trail.length) * 0.35;
        ctx.beginPath();
        ctx.moveTo(p.trail[i-1].x, p.trail[i-1].y);
        ctx.lineTo(p.trail[i].x,   p.trail[i].y);
        ctx.strokeStyle = p.color.replace(')', ` / ${a.toFixed(2)})`);
        ctx.lineWidth = 1.5; ctx.stroke();
      }
    }
    // Glow
    const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 2.2);
    glow.addColorStop(0, p.color.replace(')', ' / 0.4)')); glow.addColorStop(1, 'transparent');
    ctx.beginPath(); ctx.arc(p.x, p.y, p.r * 2.2, 0, Math.PI * 2); ctx.fillStyle = glow; ctx.fill();
    // Body
    const body = ctx.createRadialGradient(p.x - p.r * .3, p.y - p.r * .3, 0, p.x, p.y, p.r);
    body.addColorStop(0, p.color.replace(')', ' / 0.95)')); body.addColorStop(1, p.color.replace(')', ' / 0.65)'));
    ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fillStyle = body; ctx.fill();
    // Grab ring when dragging
    if (p === dragging) {
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r + 5, 0, Math.PI * 2);
      ctx.strokeStyle = p.color.replace(')', ' / 0.6)'); ctx.lineWidth = 1.5; ctx.stroke();
    }
  }

  function draw(now) {
    const dt = Math.min((now - lastTime) / 1000, 0.05);
    lastTime = now;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    update(dt * speedMult);
    drawSun();
    planets.forEach(drawPlanet);
    rafId = requestAnimationFrame(draw);
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────────

  function start() {
    resize();
    planets = [];
    setCount(3);
    highlightSpeed();
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
