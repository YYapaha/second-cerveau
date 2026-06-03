/* ============================================================
   SECOND CERVEAU — app root
   ============================================================ */
const { useState, useMemo } = React;

function App() {
  const data = D();
  const [mode, setMode] = useState("grille");          // grille | constellation
  const [active, setActive] = useState("tous");        // domain filter
  const [sort, setSort] = useState("recent");          // recent | ancien
  const [linkedOnly, setLinkedOnly] = useState(false);
  const [openNote, setOpenNote] = useState(null);

  const featured = useMemo(() => data.alaUne.map((id) => data.all.find((n) => n.id === id)).filter(Boolean), []);

  // filtered + sorted flat list (used by constellation + modal nav)
  const filtered = useMemo(() => {
    let list = data.all.slice();
    if (active !== "tous") list = list.filter((n) => n.domaine === active);
    if (linkedOnly) list = list.filter((n) => (n.liens || []).length > 0);
    list.sort((a, b) => sort === "recent" ? a._days - b._days : b._days - a._days);
    return list;
  }, [active, sort, linkedOnly]);

  // group by domain for the grid (notes only; meta shown in its own section)
  const grouped = useMemo(() => {
    const g = {};
    Object.keys(data.domains).forEach((k) => { g[k] = []; });
    filtered.filter((n) => !n.est_meta).forEach((n) => { if (g[n.domaine]) g[n.domaine].push(n); });
    return g;
  }, [filtered]);

  const metaList = useMemo(() => filtered.filter((n) => n.est_meta), [filtered]);

  const navModal = (dir) => {
    if (!openNote) return;
    const i = filtered.findIndex((n) => n.id === openNote.id);
    const ni = (i + dir + filtered.length) % filtered.length;
    setOpenNote(filtered[ni]);
  };

  const metaDom = { key: "meta", label: "Méta-fiches", color: "var(--d-meta)" };

  return (
    <div className="stage">
      <div className="aurora"><b className="b1" /><b className="b2" /><b className="b3" /></div>

      <div className="panel">
        {/* top bar */}
        <div className="topbar enter">
          <div className="brand">
            <Icon.logo className="logo" />
            <span className="wordmark">Second Cerveau</span>
          </div>
          <span className="spacer" />
          <div className="modeswitch">
            <button className={mode === "grille" ? "active" : ""} onClick={() => setMode("grille")}><Icon.grid />Grille</button>
            <button className={mode === "constellation" ? "active" : ""} onClick={() => setMode("constellation")}><Icon.nodes />Constellation</button>
          </div>
          <span className="pill-stat"><span className="dot" />{data.status.total_notes} notes · {data.status.meta_count} synthèse</span>
        </div>

        {mode === "grille" ? (
          <div className="scroll">
            {/* À la une */}
            <div className="une-head enter">
              <Icon.star className="star" />
              <span className="uppercase-label" style={{ color: "var(--d-une)" }}>À la une</span>
            </div>
            <div className="rail enter" style={{ animationDelay: ".03s" }}>
              {featured.map((n) => <FeaturedCard key={n.id} note={n} onOpen={setOpenNote} />)}
            </div>

            {/* chat */}
            <ChatBar />

            {/* filters */}
            <FilterBar domains={data.domains} active={active} onPick={setActive}
              sort={sort} onSort={() => setSort(sort === "recent" ? "ancien" : "recent")}
              linkedOnly={linkedOnly} onLinked={() => setLinkedOnly(!linkedOnly)} />

            {/* sections */}
            {Object.keys(data.domains).map((k) => (
              <Section key={k} dom={data.domains[k]} notes={grouped[k]} onOpen={setOpenNote} />
            ))}
            {metaList.length ? <Section dom={metaDom} notes={metaList} onOpen={setOpenNote} /> : null}

            {filtered.length === 0 ? (
              <div style={{ textAlign: "center", color: "var(--ink-3)", fontFamily: "var(--font-mono)", fontSize: 12, padding: "40px 0" }}>
                aucune note ne correspond
              </div>
            ) : null}
          </div>
        ) : (
          <Constellation notes={filtered} onOpen={setOpenNote} />
        )}

        {/* corner stats (grid mode only) */}
        {mode === "grille" ? (
          <>
            <div className="corner bl">
              N: {String(filtered.length).padStart(2, "0")} ({data.status.total_notes})<br />
              S: {data.status.meta_count} · sync {data.status.last_sync}
            </div>
            <div className="corner br">
              {active === "tous" ? "all" : active}<br />
              {sort === "recent" ? "↓ récents" : "↑ anciens"}{linkedOnly ? " · liées" : ""}
            </div>
          </>
        ) : null}

        {openNote ? (
          <NoteModal note={openNote} onClose={() => setOpenNote(null)} onOpen={setOpenNote}
            index={Math.max(0, filtered.findIndex((n) => n.id === openNote.id))}
            total={filtered.length} onNav={navModal} />
        ) : null}
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
