import React, { useEffect, useRef, useState, useCallback } from 'react'
import {
  TRACKS, SHOW_LIMIT, getJSON, sortItems, parseHash, currentWeekStart,
} from './lib.js'
import Cloud from './Cloud.jsx'
import Card from './Card.jsx'

// A single track section (header pill + grid + per-track "Show more").
function Track({ track, items, weekStart, activeTag, onToggleTag, registerCard }) {
  const [showAll, setShowAll] = useState(false);
  // Collapse back to the limit whenever the underlying list changes.
  useEffect(() => { setShowAll(false); }, [items, weekStart, activeTag]);

  if (!items.length) return null;
  const extra = items.length - SHOW_LIMIT;

  return (
    <section className={"track " + track.key}>
      <h2>
        {track.label}
        <span className="pill">{items.length} events</span>
      </h2>
      <div className="grid">
        {items.map((it, idx) => (
          <Card
            key={it.eid || (track.key + idx)}
            it={it}
            weekStart={weekStart}
            activeTag={activeTag}
            onToggleTag={onToggleTag}
            moreHidden={!showAll && idx >= SHOW_LIMIT}
            cardRef={it.eid ? (node => registerCard(it.eid, node)) : undefined}
          />
        ))}
      </div>
      {items.length > SHOW_LIMIT && !showAll && (
        <button className="showmore" onClick={() => setShowAll(true)}>
          Show {extra} more ▾
        </button>
      )}
    </section>
  );
}

export default function App() {
  const [weeks, setWeeks] = useState([]);        // index.json weeks[]
  const [week, setWeek] = useState(null);        // loaded week object
  const [tag, setTag] = useState(null);          // active filter tag
  const [error, setError] = useState(null);
  const [noWeeks, setNoWeeks] = useState(false);

  const cardEls = useRef(new Map());             // eid -> DOM node
  const registerCard = useCallback((eid, node) => {
    if (node) cardEls.current.set(eid, node);
    else cardEls.current.delete(eid);
  }, []);

  const meta = week
    ? (week.window ? `window ${week.window}` : "") + (week.title ? ` · ${week.title}` : "")
    : "";

  // Load a week's JSON, clear the active tag, and focus the hash eid afterwards.
  const loadWeek = useCallback(async (ws) => {
    try {
      const w = await getJSON(`/data/${ws}.json`);
      setWeek(w);
      setTag(null);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  // Focus / scroll / highlight a card by eid. Reveals it if hidden under "Show more".
  const focusEid = useCallback((eid) => {
    if (!eid) return;
    // Defer so the just-rendered cards are mounted.
    requestAnimationFrame(() => {
      const card = cardEls.current.get(eid);
      if (!card) return;
      if (card.classList.contains("more-hidden")) {
        const sec = card.closest("section.track");
        if (sec) {
          sec.querySelectorAll(".more-hidden").forEach(c => c.classList.remove("more-hidden"));
          const btn = sec.querySelector(".showmore");
          if (btn) btn.remove();
        }
      }
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      card.classList.add("focused");
      setTimeout(() => card.classList.remove("focused"), 2600);
    });
  }, []);

  // Initial load: fetch index, build week list, pick default (or hash) week.
  useEffect(() => {
    (async () => {
      try {
        const idx = await getJSON("/data/index.json");
        setWeeks(idx.weeks || []);
        if (idx.weeks && idx.weeks.length) {
          const wks = idx.weeks.map(w => w.week_start);
          const hw = parseHash().week;
          const start = (hw && wks.includes(hw)) ? hw
            : (currentWeekStart(wks) || idx.weeks[0].week_start);
          await loadWeek(start);
        } else {
          setNoWeeks(true);
        }
      } catch (e) {
        setError(e.message);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // After a week renders, honor #/<week>/<eid> by focusing the eid.
  useEffect(() => {
    if (week) focusEid(parseHash().eid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [week]);

  // hashchange: switch week if the hash names a different listed one, else focus.
  useEffect(() => {
    function applyHash() {
      const { week: hw, eid } = parseHash();
      const wks = weeks.map(w => w.week_start);
      if (hw && week && hw !== week.week_start && wks.includes(hw)) {
        loadWeek(hw);   // the [week] effect focuses the eid afterwards
      } else {
        focusEid(eid);
      }
    }
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, [weeks, week, loadWeek, focusEid]);

  const onToggleTag = useCallback((t) => {
    setTag(prev => (prev === t ? null : t));
  }, []);

  // Week <select> change: clear the hash and load.
  function onSelectWeek(e) {
    location.hash = "";
    loadWeek(e.target.value);
  }

  // Build the sorted/filtered item lists per track (mirrors render()).
  const tracksOut = week ? TRACKS.map(t => {
    let items = sortItems((week.tracks && week.tracks[t.key]) || []);
    if (tag) items = items.filter(it => (it.tags || []).includes(tag));
    return { track: t, items };
  }) : [];
  const anyItems = tracksOut.some(t => t.items.length);

  const selValue = week ? week.week_start : "";

  return (
    <>
      <header>
        <div className="brand">
          <img className="logo" src="/logo.png" alt="Party Scout" width="56" height="56" />
          <div>
            <h1><span className="spark">Party Scout</span></h1>
            <div className="sub">Weekly SF &amp; Bay Area events digest — music + sports, ranked.</div>
          </div>
        </div>
      </header>
      <main>
        <div className="controls">
          <label className="meta" htmlFor="week">Week:</label>
          <select id="week" value={selValue} onChange={onSelectWeek}>
            {weeks.map(w => {
              const n = (w.counts ? (w.counts.music || 0) + (w.counts.sports || 0) : 0);
              return (
                <option key={w.week_start} value={w.week_start}>
                  {`${w.week_start}${w.window ? "  (" + w.window + ")" : ""} — ${n} events`}
                </option>
              );
            })}
          </select>
          <span className="meta">{meta}</span>
          <span className="meta">·</span>
          <a
            className="meta"
            href={week ? `/data/${week.week_start}.md` : "#"}
            target="_blank"
            rel="noopener"
          >view markdown</a>
        </div>

        {week && <Cloud week={week} activeTag={tag} onToggleTag={onToggleTag} />}

        <div id="report">
          {error && (
            <div className="empty">Could not load data/index.json — {error}</div>
          )}
          {noWeeks && <div className="empty">No weeks yet.</div>}
          {week && (
            anyItems ? (
              tracksOut.map(({ track, items }) => (
                <Track
                  key={track.key}
                  track={track}
                  items={items}
                  weekStart={week.week_start}
                  activeTag={tag}
                  onToggleTag={onToggleTag}
                  registerCard={registerCard}
                />
              ))
            ) : (
              <div className="empty">
                {tag ? `No “${tag}” events this week.` : "No events for this week."}
              </div>
            )
          )}
        </div>
      </main>
      <footer>
        Data: <a href="/data/index.json">data/index.json</a> ·
        Generated by <code>party-scout-code</code>. One JSON + MD per week.
      </footer>
    </>
  );
}
