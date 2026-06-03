// activities/aim.js — Aim Trainer

export function create(container) {
  container.innerHTML = `
    <canvas id="aim-canvas" style="position:absolute;inset:0;width:100%;height:100%;cursor:crosshair"></canvas>
    <div id="aim-hud" style="position:absolute;top:0;left:0;right:0;display:flex;align-items:center;gap:20px;padding:10px 16px;background:rgba(0,0,0,0.45);border-bottom:1px solid rgba(255,255,255,0.06);font-family:monospace">
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-size:8px;letter-spacing:.1em;color:#4a4a5a">SCORE</span>
        <span id="aim-score" style="font-size:18px;font-weight:700;color:#f4f4f7">0</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-size:8px;letter-spacing:.1em;color:#4a4a5a">STREAK</span>
        <span id="aim-streak" style="font-size:18px;font-weight:700;color:#f4f4f7">0</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-size:8px;letter-spacing:.1em;color:#4a4a5a">PRÉCISION</span>
        <span id="aim-acc" style="font-size:18px;font-weight:700;color:#f4f4f7">—</span>
      </div>
      <div style="margin-left:auto;display:flex;flex-direction:column;align-items:center;gap:2px">
        <span style="font-size:8px;letter-spacing:.1em;color:#4a4a5a">TEMPS</span>
        <span id="aim-timer" style="font-size:18px;font-weight:700;color:oklch(0.85 0.11 90)">—</span>
      </div>
    </div>
    <div id="aim-mode-bar" style="position:absolute;bottom:20px;left:50%;transform:translateX(-50%);display:flex;gap:10px">
      <button id="btn-timed" style="font-family:monospace;font-size:11px;padding:10px 18px;border-radius:8px;background:oklch(0.72 0.15 25 / 0.2);color:oklch(0.82 0.14 25);border:1px solid oklch(0.72 0.15 25 / 0.4);cursor:pointer">⏱ 30 secondes</button>
      <button id="btn-endless" style="font-family:monospace;font-size:11px;padding:10px 18px;border-radius:8px;background:rgba(255,255,255,0.05);color:#6a6a7c;border:1px solid rgba(255,255,255,0.1);cursor:pointer">∞ Endless</button>
    </div>
    <div id="aim-results" style="display:none;position:absolute;inset:0;background:rgba(8,8,12,0.92);flex-direction:column;align-items:center;justify-content:center;gap:16px;font-family:monospace">
      <div style="font-size:28px;font-weight:700;color:#f4f4f7">Résultats</div>
      <div id="aim-res-score" style="font-size:20px;color:oklch(0.85 0.11 90)"></div>
      <div id="aim-res-streak" style="font-size:14px;color:#a6a6b6"></div>
      <div id="aim-res-acc"    style="font-size:14px;color:#a6a6b6"></div>
      <button id="btn-replay" style="margin-top:12px;font-family:monospace;font-size:11px;padding:10px 24px;border-radius:8px;background:oklch(0.72 0.15 25 / 0.2);color:oklch(0.82 0.14 25);border:1px solid oklch(0.72 0.15 25 / 0.4);cursor:pointer">↺ Rejouer</button>
    </div>
  `;

  const canvas    = container.querySelector('#aim-canvas');
  const ctx       = canvas.getContext('2d');
  const scoreEl   = container.querySelector('#aim-score');
  const streakEl  = container.querySelector('#aim-streak');
  const accEl     = container.querySelector('#aim-acc');
  const timerEl   = container.querySelector('#aim-timer');
  const modeBar   = container.querySelector('#aim-mode-bar');
  const resultsEl = container.querySelector('#aim-results');

  let audioCtx = null;
  let target = null;
  let hits = 0, misses = 0, streak = 0, bestStreak = 0, score = 0;
  let mode = null;
  let timeLeft = 30;
  let timerInterval = null;
  let running = false;
  let rafId = null;

  function getAudio() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    return audioCtx;
  }

  function resize() {
    canvas.width  = container.clientWidth;
    canvas.height = container.clientHeight;
  }
  const ro = new ResizeObserver(resize);
  ro.observe(container);
  resize();

  function playPop() {
    try {
      const ac = getAudio();
      const osc = ac.createOscillator();
      const gain = ac.createGain();
      osc.connect(gain); gain.connect(ac.destination);
      osc.frequency.setValueAtTime(900, ac.currentTime);
      osc.frequency.exponentialRampToValueAtTime(200, ac.currentTime + 0.08);
      gain.gain.setValueAtTime(0.12, ac.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.1);
      osc.start(); osc.stop(ac.currentTime + 0.1);
    } catch {}
  }

  function updateHUD() {
    scoreEl.textContent  = score;
    streakEl.textContent = streak >= 3 ? `🔥${streak}` : streak;
    const total = hits + misses;
    accEl.textContent    = total > 0 ? Math.round(hits / total * 100) + '%' : '—';
    timerEl.textContent  = mode === 'timed' ? timeLeft + 's' : '∞';
  }

  function spawnTarget() {
    const pad = 80, r = 28;
    const hudH = 52;
    target = {
      x: pad + Math.random() * (canvas.width  - pad * 2),
      y: hudH + pad + Math.random() * (canvas.height - hudH - pad * 2),
      r, scale: 0,
      bornAt: performance.now(),
      lifetime: 2500,
      dying: false,
      particles: [],
    };
  }

  function onHit() {
    if (!target || !running || target.dying) return;
    playPop();
    hits++; streak++;
    if (streak > bestStreak) bestStreak = streak;
    const mult = streak >= 5 ? 3 : streak >= 3 ? 2 : 1;
    score += 10 * mult;
    for (let i = 0; i < 8; i++) {
      const a = (Math.PI * 2 / 8) * i;
      target.particles.push({ x: target.x, y: target.y, vx: Math.cos(a) * 4, vy: Math.sin(a) * 4, life: 1 });
    }
    target.dying = true;
    setTimeout(() => { target = null; if (running) spawnTarget(); }, 200);
    updateHUD();
  }

  function onMiss() {
    if (!running) return;
    misses++; streak = 0;
    updateHUD();
  }

  function draw(now) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (target) {
      const age = now - target.bornAt;

      if (age > target.lifetime && !target.dying) {
        target = null;
        if (running) spawnTarget();
        rafId = requestAnimationFrame(draw);
        return;
      }

      if (!target.dying) {
        const t = Math.min(1, age / 200);
        target.scale = t * t;
        const remaining = target.lifetime - age;
        if (remaining < 800) target.scale *= remaining / 800;
        target.scale = Math.max(0.25, target.scale);
      } else {
        target.scale = Math.max(0, target.scale - 0.1);
      }

      ctx.save();
      ctx.translate(target.x, target.y);
      ctx.scale(target.scale, target.scale);

      ctx.beginPath();
      ctx.arc(0, 0, target.r, 0, Math.PI * 2);
      ctx.strokeStyle = 'oklch(0.72 0.15 25 / 0.9)';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, target.r * 0.55, 0, Math.PI * 2);
      ctx.strokeStyle = 'oklch(0.72 0.15 25 / 0.5)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(0, 0, 5, 0, Math.PI * 2);
      ctx.fillStyle = 'oklch(0.72 0.15 25)';
      ctx.fill();

      ctx.restore();

      for (const p of target.particles) {
        p.x += p.vx; p.y += p.vy; p.vx *= 0.9; p.vy *= 0.9; p.life -= 0.06;
        if (p.life > 0) {
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3 * p.life, 0, Math.PI * 2);
          ctx.fillStyle = `oklch(0.72 0.15 25 / ${p.life.toFixed(2)})`;
          ctx.fill();
        }
      }
      target.particles = target.particles.filter(p => p.life > 0);
    }

    rafId = requestAnimationFrame(draw);
  }

  function showResults() {
    resultsEl.style.display = 'flex';
    resultsEl.querySelector('#aim-res-score').textContent  = `Score : ${score}`;
    resultsEl.querySelector('#aim-res-streak').textContent = `Meilleur streak : 🔥${bestStreak}`;
    const total = hits + misses;
    resultsEl.querySelector('#aim-res-acc').textContent    = `Précision : ${total > 0 ? Math.round(hits / total * 100) : 0}%`;
  }

  function startMode(m) {
    mode     = m;
    hits = misses = streak = bestStreak = score = 0;
    timeLeft = 30;
    running  = true;
    modeBar.style.display   = 'none';
    resultsEl.style.display = 'none';
    updateHUD();
    spawnTarget();
    if (m === 'timed') {
      timerInterval = setInterval(() => {
        timeLeft--;
        updateHUD();
        if (timeLeft <= 0) {
          clearInterval(timerInterval);
          timerInterval = null;
          running = false;
          target  = null;
          showResults();
        }
      }, 1000);
    }
  }

  canvas.addEventListener('click', e => {
    if (!running || !target) return;
    const rect = canvas.getBoundingClientRect();
    const dx = e.clientX - rect.left - target.x;
    const dy = e.clientY - rect.top  - target.y;
    if (Math.hypot(dx, dy) <= target.r * target.scale) onHit();
    else onMiss();
  });

  container.querySelector('#btn-timed').addEventListener('click',   () => startMode('timed'));
  container.querySelector('#btn-endless').addEventListener('click', () => startMode('endless'));
  container.querySelector('#btn-replay').addEventListener('click',  () => {
    resultsEl.style.display = 'none';
    modeBar.style.display   = 'flex';
    running = false;
    target  = null;
    updateHUD();
  });

  function start() {
    resize();
    rafId = requestAnimationFrame(draw);
  }

  function stop() {
    running = false;
    if (timerInterval) clearInterval(timerInterval);
    if (rafId) cancelAnimationFrame(rafId);
    ro.disconnect();
    if (audioCtx && audioCtx.state !== 'closed') audioCtx.close().catch(() => {});
    container.innerHTML = '';
  }

  return { start, stop };
}
