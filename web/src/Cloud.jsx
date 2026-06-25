import React, { useState, useEffect } from 'react'
import { tagCounts, CLOUD_LIMIT } from './lib.js'

// Tag cloud. Ports buildCloud(): font scaled by frequency, "+N more" reveals
// hidden chips, "✕ clear" appears when a tag is active.
export default function Cloud({ week, activeTag, onToggleTag }) {
  const [expanded, setExpanded] = useState(false);
  const tags = tagCounts(week);

  // Collapse the "+N more" expansion whenever the week changes.
  useEffect(() => { setExpanded(false); }, [week]);

  if (!tags.length) return null;

  const max = tags[0][1], min = tags[tags.length - 1][1];

  // Mirror the original's `shown` counter: only non-active chips beyond the limit
  // are hidden; active chips always count as shown.
  let shown = 0;
  const chips = tags.map(([tag, n]) => {
    const f = max === min ? 1.05 : 0.85 + (n - min) / (max - min) * 0.65;
    const active = activeTag === tag;
    let hidden = false;
    if (shown >= CLOUD_LIMIT && !active) hidden = true;
    else shown++;
    return { tag, n, f, active, hidden };
  });

  const hiddenCount = chips.filter(c => c.hidden && !expanded).length;

  return (
    <div className="cloud">
      <span className="clabel">Tags</span>
      {chips.map(({ tag, n, f, active, hidden }) => (
        <span
          key={tag}
          className={"chip" + (active ? " on" : "") + (hidden && !expanded ? " chip-hidden" : "")}
          style={{ fontSize: f.toFixed(2) + "rem" }}
          onClick={() => onToggleTag(tag)}
        >
          {tag}<span className="n">{n}</span>
        </span>
      ))}
      {hiddenCount > 0 && (
        <span className="chip morechip" onClick={() => setExpanded(true)}>
          +{hiddenCount} more
        </span>
      )}
      {activeTag && (
        <span className="chip clear" onClick={() => onToggleTag(activeTag)}>✕ clear</span>
      )}
    </div>
  );
}
