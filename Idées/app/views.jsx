/* ============================================================
   SECOND CERVEAU — views: NoteModal + Constellation
   ============================================================ */
const { useState, useMemo, useEffect, useRef } = React;

/* ---------- expanded note modal ---------- */
function NoteModal({ note, onClose, onOpen, index, total, onNav }) {
  const dom = domainOf(note);
  const all = D().all;
  const linked = (note.liens || []).map((id) => all.find((n) => n.id === id)).filter(Boolean);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") onNav(1);
      if (e.key === "ArrowLeft") onNav(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [note]);

  return (
    <div className="scrim" onClick={onClose}>
      <div className="modal" style={accentStyle(note)} onClick={(e) => e.stopPropagation()}>
        <div className="mhead">
          <div className="au"><div className="a1" /><div className="a2" /><div className="a3" /></div>
          <div className="grain" />
          <button className="navbtn prev" onClick={() => onNav(-1)} title="Précédente"><Icon.arrow style={{ transform: "rotate(180deg)" }} /></button>
          <button className="navbtn next" onClick={() => onNav(1)} title="Suivante"><Icon.arrow /></button>
          <button className="closebtn" onClick={onClose}><Icon.close /></button>
          <div className="htext">
            <div className="domrow">
              <span className="ddot" />
              <span className="domlabel">{note.est_meta ? "Synthèse · " : ""}{dom ? dom.label : ""}</span>
            </div>
            <h2>{note.titre}</h2>
          </div>
        </div>

        <div className="mbody">
          <div className="insight-box">
            <div className="bar" />
            <div className="it">{note.insight}</div>
          </div>

          <div className="blocklabel">Résumé</div>
          <div className="resume">{note.resume}</div>

          {note.tags && note.tags.length ? (
            <>
              <div className="blocklabel">Tags</div>
              <div className="tags">{note.tags.map((t) => <span key={t} className="tagpill">#{t}</span>)}</div>
            </>
          ) : null}

          {linked.length ? (
            <>
              <div className="blocklabel">{note.est_meta ? "Notes sources" : "Notes liées"} · {linked.length}</div>
              <div className="linked">
                {linked.map((l) => (
                  <button key={l.id} className="lrow" style={accentStyle(l)} onClick={() => onOpen(l)}>
                    <span className="ddot" />
                    <span className="lt">{l.titre}</span>
                    <Icon.arrow />
                  </button>
                ))}
              </div>
            </>
          ) : null}

          <div className="mfoot">
            <span className="metatime">{relTime(note._days)}</span>
            <span className="metatime">· {String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}</span>
            <div className="scoremeter">
              <span className="metatime">pertinence</span>
              <div className="track"><div className="fill" style={{ width: `${Math.round(note.score * 100)}%` }} /></div>
              <span className="metatime">{note.score.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---------- constellation ---------- */
function Constellation({ notes, onOpen }) {
  const wrapRef = useRef(null);
  const [size, setSize] = useState({ w: 580, h: 820 });
  const [hover, setHover] = useState(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef(null);

  useEffect(() => {
    const el = wrapRef.current; if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el); return () => ro.disconnect();
  }, []);

  // layout: domain hubs on a ring, notes clustered around their hub
  const layout = useMemo(() => {
    const cx = size.w / 2, cy = size.h / 2;
    const R = Math.min(size.w, size.h) * 0.26;
    const domKeys = Object.keys(D().domains);
    const pos = {};
    const byDom = {};
    notes.forEach((n) => { (byDom[n.domaine] = byDom[n.domaine] || []).push(n); });
    const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
    domKeys.forEach((dk, di) => {
      const ang = (di / domKeys.length) * Math.PI * 2 - Math.PI / 2;
      const hx = cx + Math.cos(ang) * R, hy = cy + Math.sin(ang) * R;
      const list = byDom[dk] || [];
      list.forEach((n, i) => {
        if (n.est_meta) { pos[n.id] = { x: cx + (i - 0.5) * 26, y: cy }; return; }
        const k = list.filter((x) => !x.est_meta).length;
        const a2 = ang + (i - (k - 1) / 2) * 0.5;
        const rr = 64 + (i % 2) * 22;
        pos[n.id] = {
          x: clamp(hx + Math.cos(a2) * rr * 0.55, 96, size.w - 96),
          y: clamp(hy + Math.sin(a2) * rr, 84, size.h - 70),
        };
      });
    });
    // edges (dedup)
    const seen = new Set(); const edges = [];
    notes.forEach((n) => (n.liens || []).forEach((tid) => {
      if (!pos[n.id] || !pos[tid]) return;
      const key = [n.id, tid].sort().join("-");
      if (seen.has(key)) return; seen.add(key);
      edges.push({ a: n.id, b: tid, key, accent: (D().domains[n.domaine] || {}).color || "var(--ink-3)" });
    }));
    return { pos, edges };
  }, [notes, size.w, size.h]);

  const onDown = (e) => { drag.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }; };
  const onMove = (e) => { if (drag.current) setPan({ x: e.clientX - drag.current.x, y: e.clientY - drag.current.y }); };
  const onUp = () => { drag.current = null; };

  const litFor = (edge) => hover && (edge.a === hover || edge.b === hover);

  return (
    <div className="constel" ref={wrapRef} onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerLeave={onUp}>
      <span className="hint">glisser pour naviguer</span>
      <div className="world" style={{ transform: `translate(${pan.x}px, ${pan.y}px)` }}>
        <svg className="links">
          {layout.edges.map((e) => {
            const a = layout.pos[e.a], b = layout.pos[e.b];
            const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2 - 28;
            return (
              <path key={e.key} className={"edge" + (litFor(e) ? " lit" : "")}
                style={litFor(e) ? { "--accent": e.accent } : null}
                d={`M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}`} />
            );
          })}
        </svg>
        {notes.map((n) => {
          const p = layout.pos[n.id]; if (!p) return null;
          return (
            <div key={n.id} className={"cnode" + (n.est_meta ? " meta" : "") + (hover === n.id ? " active" : "")}
              style={{ left: p.x, top: p.y, "--accent": (D().domains[n.domaine] || {}).color }}
              onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}
              onClick={() => onOpen(n)}>
              <div className="bubble"><span className="ddot" /><span className="ct">{n.titre}</span></div>
            </div>
          );
        })}
      </div>
      <div className="legend">
        {Object.values(D().domains).map((d) => (
          <div className="li" key={d.key} style={{ "--accent": d.color }}><span className="ddot" /><span>{d.label}</span></div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { NoteModal, Constellation });
