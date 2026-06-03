/* ============================================================
   SECOND CERVEAU — base components (icons, cards, filters, chat)
   ============================================================ */
const { useState, useMemo, useEffect, useRef } = React;

/* ---------- helpers ---------- */
function relTime(days) {
  if (days <= 0) return "aujourd'hui";
  if (days === 1) return "hier";
  if (days < 7) return `il y a ${days} j`;
  if (days < 30) return `il y a ${Math.round(days / 7)} sem`;
  return `il y a ${Math.round(days / 30)} mois`;
}
const D = () => window.BRAIN_DATA;
function domainOf(note) { return D().domains[note.domaine]; }
function accentStyle(note) {
  const dom = domainOf(note);
  return { "--accent": dom ? dom.color : "var(--ink-3)" };
}

/* ---------- icons (monoline, currentColor) ---------- */
const Icon = {
  logo: (p) => (
    <svg viewBox="0 0 64 64" fill="none" {...p}>
      <circle cx="32" cy="32" r="9.5" stroke="currentColor" strokeWidth="2.4"/>
      <circle cx="32" cy="32" r="2.6" fill="currentColor"/>
      <ellipse cx="32" cy="32" rx="22" ry="22" stroke="currentColor" strokeWidth="1.4" opacity="0.28"/>
      <circle cx="51" cy="21" r="3.4" fill="currentColor"/>
      <circle cx="14" cy="44" r="2.6" fill="currentColor"/>
      <path d="M40.5 27 C45 23.5, 47.5 22.5, 51 21" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/>
      <path d="M24 38 C19.5 41, 16.5 42.5, 14 44" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  ),
  star: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 3l2.4 5.6 6 .5-4.6 4 1.4 5.9L12 16.9 6.8 19l1.4-5.9L3.6 9.1l6-.5L12 3z" fill="currentColor"/></svg>),
  search: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2"/><path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>),
  spark: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>),
  chev: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>),
  link: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><path d="M9 12h6M10 8H8a4 4 0 100 8h2M14 8h2a4 4 0 110 8h-2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>),
  clock: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.7"/><path d="M12 7.5V12l3 2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"/></svg>),
  grid: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><rect x="3.5" y="3.5" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.8"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.8"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.8"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.8"/></svg>),
  nodes: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><circle cx="6" cy="6" r="2.6" stroke="currentColor" strokeWidth="1.8"/><circle cx="18" cy="9" r="2.6" stroke="currentColor" strokeWidth="1.8"/><circle cx="9" cy="18" r="2.6" stroke="currentColor" strokeWidth="1.8"/><path d="M8.1 7.2C12 8 14 8.2 15.6 8.4M7.4 8.3c.6 3 .9 5 1.1 7.1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>),
  close: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>),
  arrow: (p) => (<svg viewBox="0 0 24 24" fill="none" {...p}><path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>),
};

/* ---------- À la une — featured card ---------- */
function FeaturedCard({ note, onOpen }) {
  const dom = domainOf(note);
  return (
    <div className="fcard" style={accentStyle(note)} onClick={() => onOpen(note)}>
      <div className="glow" />
      <div className="ftitle">{note.titre}</div>
      <div className="finsight">{note.insight}</div>
      <div className="fmeta">
        <span className="ddot" />
        <span className="metatime">{dom ? dom.label.toLowerCase() : ""}</span>
        <span className="metatime" style={{ marginLeft: "auto" }}>{relTime(note._days)}</span>
      </div>
    </div>
  );
}

/* ---------- note card (list) ---------- */
function NoteCard({ note, onOpen, style }) {
  const linked = (note.liens || []).length;
  return (
    <button className="ncard enter" style={{ ...accentStyle(note), ...style }} onClick={() => onOpen(note)}>
      <div className="row1">
        <span className="ddot" />
        <span className="ntitle">{note.titre}</span>
        {note.est_meta ? <span className="metachip" style={{ marginLeft: "auto" }}>synthèse</span> : null}
      </div>
      <div className="ninsight">{note.insight}</div>
      <div className="nfoot">
        <span className="metatime">{relTime(note._days)}</span>
        {note.tags && note.tags[0] ? <span className="tag">#{note.tags[0]}</span> : null}
        {linked > 0 ? (
          <span className="meta-badge">
            <Icon.link className="link-ic" />
            <span className="metatime">{linked}</span>
          </span>
        ) : null}
      </div>
    </button>
  );
}

/* ---------- chat bar ---------- */
function ChatBar() {
  const [v, setV] = useState("");
  return (
    <div className="chat enter" style={{ animationDelay: ".05s" }}>
      <div className="field">
        <Icon.spark />
        <input value={v} onChange={(e) => setV(e.target.value)} placeholder="Pose une question à tes notes…" />
        <span className="kbd">↵</span>
      </div>
    </div>
  );
}

/* ---------- filter bar ---------- */
function FilterBar({ domains, active, onPick, sort, onSort, linkedOnly, onLinked }) {
  return (
    <div className="filters enter" style={{ animationDelay: ".1s" }}>
      <button className={"fpill" + (active === "tous" ? " active" : "")} onClick={() => onPick("tous")}>Tous</button>
      {Object.values(domains).map((d) => (
        <button key={d.key} className={"fpill" + (active === d.key ? " active" : "")}
          style={{ "--accent": d.color }} onClick={() => onPick(d.key)}>
          <span className="ddot" />{d.label}
        </button>
      ))}
      <span className="sep" />
      <button className="fpill" onClick={onSort}>
        <Icon.clock />{sort === "recent" ? "Récents" : "Anciens"}
      </button>
      <button className={"fpill toggle" + (linkedOnly ? " active" : "")} onClick={onLinked}>
        <Icon.link />Liées
      </button>
    </div>
  );
}

/* ---------- section ---------- */
function Section({ dom, notes, onOpen, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  if (!notes.length) return null;
  return (
    <div className="section" style={{ "--accent": dom.color }}>
      <div className={"shead" + (open ? "" : " collapsed")} onClick={() => setOpen(!open)}>
        <span className="ddot" />
        <span className="slabel">{dom.label}</span>
        <span className="scount">{String(notes.length).padStart(2, "0")}</span>
        <span className="line" />
        <Icon.chev className="chev" />
      </div>
      {open && (
        <div className="cards">
          {notes.map((n, i) => (
            <NoteCard key={n.id} note={n} onOpen={onOpen} style={{ animationDelay: `${i * 0.04}s` }} />
          ))}
        </div>
      )}
    </div>
  );
}

Object.assign(window, { Icon, FeaturedCard, NoteCard, ChatBar, FilterBar, Section, relTime, domainOf, accentStyle, D });
