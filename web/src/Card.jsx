import React from 'react'
import { mapsUrl, ticketsUrl } from './lib.js'

// One event card. DOM/classes mirror the original index.html `card()` so the
// ported CSS applies unchanged.
export default function Card({ it, weekStart, activeTag, onToggleTag, moreHidden, cardRef }) {
  const when = [it.day, it.time].filter(Boolean).join(" · ");
  let where = it.area || "";
  if (it.venue) where += (where ? " · " : "") + it.venue;
  const mUrl = mapsUrl(it.maps);

  const tUrl = ticketsUrl(it);
  const isFree = it.price && /free|^\$?0\b/i.test(it.price);

  // Build the action buttons (Open / Buy ticket / price), reserving the row when empty.
  const acts = [];
  if (it.link) {
    acts.push(
      <a key="open" className="btn" href={it.link} target="_blank" rel="noopener">Open</a>
    );
  }
  if (tUrl) {
    acts.push(
      <a key="tix" className={"btn tix" + (isFree ? " free" : "")} href={tUrl} target="_blank" rel="noopener">
        {it.price ? (<><b>{it.price}</b> · Buy ticket</>) : "Buy ticket"}
      </a>
    );
  } else if (it.price) {
    // No ticket link: show price/Free as a same-size (non-clickable) button.
    acts.push(
      <span key="price" className={"btn tix nolink" + (isFree ? " free" : "")}><b>{it.price}</b></span>
    );
  }
  if (!acts.length) {
    acts.push(<span key="ph" className="btn ph">&nbsp;</span>);
  }

  const anchorHref = weekStart ? `#/${weekStart}/${it.eid}` : "#" + it.eid;

  return (
    <div
      ref={cardRef}
      id={it.eid || undefined}
      className={"card" + (it.active === false ? " inactive" : "") + (moreHidden ? " more-hidden" : "")}
    >
      {it.eid && (
        <a className="anchor" href={anchorHref} title="Link to this event">#</a>
      )}
      {it.category && <div className="cat">{it.category}</div>}
      <div className="name" dangerouslySetInnerHTML={{ __html: it.name }} />
      {when && <div className="when">{when}</div>}
      {where && (
        <div className="where">
          {"📍 " + where}
          {mUrl && (
            <>
              {" · "}
              <a className="om" href={mUrl} target="_blank" rel="noopener">open map</a>
            </>
          )}
        </div>
      )}
      {it.why && <div className="why">{it.why}</div>}
      <div className="foot">
        {it.tags && it.tags.length > 0 && (
          <div className="tags">
            {it.tags.map((t, i) => (
              <span
                key={t + i}
                className={"tag " + t + (activeTag === t ? " on" : "")}
                onClick={() => onToggleTag(t)}
              >{t}</span>
            ))}
          </div>
        )}
        {it.active === false && (
          <div className="carried">↩︎ carried over — not in latest scan</div>
        )}
        <div className="acts">{acts}</div>
      </div>
    </div>
  );
}
