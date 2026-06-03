// activities/breath.js — Bulle respiratoire guidée

export function create(container) {
  container.innerHTML = `
    <canvas id="breath-canvas" style="position:absolute;inset:0;width:100%;height:100%"></canvas>
    <div id="breath-label" style="position:absolute;bottom:32%;left:50%;transform:translateX(-50%);font-family:monospace;font-size:20px;font-weight:600;letter-spacing:.15em;pointer-events:none;transition:color .5s;white-space:nowrap"></div>
    <div id="breath-rhythm" style="position:absolute;bottom:18px;left:50%;transform:translateX(-50%);display:flex;gap:8px">
      <button data-r="0" style="font-family:monospace;font-size:10px;padding:7px 14px;border-radius:8px;cursor:pointer;transition:all .15s;background:rgba(255,255,255,0.09);color:#f4f4f7;border:1px solid rgba(255,255,255,0.15)">Doux</button>
      <button data-r="1" style="font-family:monospace;font-size:10px;padding:7px 14px;border-radius:8px;cursor:pointer;transition:all .15s;background:rgba(255,255,255,0.04);color:#4a4a5a;border:1px solid rgba(255,255,255,0.07)">Box</button>
      <button data-r="2" style="font-family:monospace;font-size:10px;padding:7px 14px;border-radius:8px;cursor:pointer;transition:all .15s;background:rgba(255,255,255,0.04);color:#4a4a5a;border:1px solid rgba(255,255,255,0.07)">Rapide</button>
    </div>
  `;

  const canvas  = container.querySelector('#breath-canvas');
  const ctx     = canvas.getContext('2d');
  const labelEl = container.querySelector('#breath-label');

  const RHYTHMS = [
    [4000, 4000, 4000, 2000],
    [4000, 4000, 4000, 4000],
    [3000, 3000, 3000, 2000],
  ];
  const PHASE_LABELS = ['Inspire', 'Retiens', 'Expire', 'Retiens'];
  const PHASE_COLORS = [
    'oklch(0.72 0.13 255)',
    'oklch(0.65 0.16 290)',
    'oklch(0.72 0.14 150)',
    'oklch(0.60 0.06 250)',
  ];
  // Blob scale target at end of each phase
  const SIZE_END = [1.0, 1.0, 0.38, 0.38];

  let rhythm     = 0;
  let phase      = 0;
  let phaseStart = 0;
  let blobScale  = 0.38;
  let rafId      = null;

  function resize() {
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);
  resize();

  function easeInOut(t) { return t < 0.5 ? 2*t*t : -1 + (4 - 2*t)*t; }

  function drawBlob(cx, cy, r, t) {
    const N = 14;
    ctx.beginPath();
    for (let i = 0; i <= N; i++) {
      const a = (Math.PI * 2 / N) * i;
      const noise = 1
        + 0.07 * Math.sin(a * 3 + t * 0.7)
        + 0.04 * Math.sin(a * 5 - t * 1.1)
        + 0.025 * Math.sin(a * 7 + t * 1.6);
      const pr = r * noise;
      const x = cx + Math.cos(a) * pr;
      const y = cy + Math.sin(a) * pr;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
  }

  function draw(now) {
    const durations = RHYTHMS[rhythm];
    const elapsed   = now - phaseStart;
    const duration  = durations[phase];

    if (elapsed >= duration) {
      phase      = (phase + 1) % 4;
      phaseStart = now;
    }

    const progress = Math.min(1, elapsed / duration);
    const prevSize = SIZE_END[(phase - 1 + 4) % 4];
    const nextSize = SIZE_END[phase];
    blobScale = prevSize + (nextSize - prevSize) * easeInOut(progress);

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const cx    = canvas.width  / 2;
    const cy    = canvas.height * 0.42;
    const baseR = Math.min(canvas.width, canvas.height) * 0.20;
    const r     = baseR * blobScale;
    const color = PHASE_COLORS[phase];
    const t     = now / 1000;

    // Glow layer
    drawBlob(cx, cy, r * 1.35, t);
    const glowGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 1.35);
    glowGrad.addColorStop(0, color.replace(')', ' / 0.15)'));
    glowGrad.addColorStop(1, 'transparent');
    ctx.fillStyle = glowGrad;
    ctx.fill();

    // Body layer
    drawBlob(cx, cy, r, t);
    const bodyGrad = ctx.createRadialGradient(cx - r*0.25, cy - r*0.25, 0, cx, cy, r);
    bodyGrad.addColorStop(0,   color.replace(')', ' / 0.75)'));
    bodyGrad.addColorStop(0.7, color.replace(')', ' / 0.40)'));
    bodyGrad.addColorStop(1,   color.replace(')', ' / 0.15)'));
    ctx.fillStyle = bodyGrad;
    ctx.fill();

    // Progress arc background
    const arcR = r * 1.28;
    ctx.beginPath();
    ctx.arc(cx, cy, arcR, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Progress arc fill
    if (progress > 0.005) {
      ctx.beginPath();
      ctx.arc(cx, cy, arcR, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * progress);
      ctx.strokeStyle = color.replace(')', ' / 0.55)');
      ctx.lineWidth = 3;
      ctx.stroke();
    }

    labelEl.textContent = PHASE_LABELS[phase];
    labelEl.style.color = color;

    rafId = requestAnimationFrame(draw);
  }

  container.querySelectorAll('[data-r]').forEach(btn => {
    btn.addEventListener('click', () => {
      rhythm     = parseInt(btn.dataset.r);
      phase      = 0;
      phaseStart = performance.now();
      container.querySelectorAll('[data-r]').forEach(b => {
        const active = b === btn;
        b.style.background  = active ? 'rgba(255,255,255,0.09)' : 'rgba(255,255,255,0.04)';
        b.style.color       = active ? '#f4f4f7' : '#4a4a5a';
        b.style.borderColor = active ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.07)';
      });
    });
  });

  function start() {
    resize();
    phaseStart = performance.now();
    rafId = requestAnimationFrame(draw);
  }

  function stop() {
    if (rafId) cancelAnimationFrame(rafId);
    ro.disconnect();
    container.innerHTML = '';
  }

  return { start, stop };
}
