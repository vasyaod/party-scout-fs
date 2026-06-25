// Ported 1:1 from the original index.html vanilla-JS app.

export const TRACKS = [
  { key: "music", label: "🎶 Music & entertainment" },
  { key: "sports", label: "🏍️ Sports & active" },
];

// Chronological day order for sorting cards (the weekend window is Thu–Sun).
export const DAY_ORDER = { Thu: 0, Fri: 1, Sat: 2, Sun: 3, Mon: 4, Tue: 5, Wed: 6 };

export const SHOW_LIMIT = 21;   // cards shown per track before "Show more"
export const CLOUD_LIMIT = 24;  // tags shown before the cloud's "+N more"

// iOS / iPadOS / macOS -> Apple Maps; everything else -> Google Maps.
export const APPLE = /iPhone|iPad|iPod|Macintosh|Mac OS X/i.test(
  (navigator.platform || "") + " " + (navigator.userAgent || ""));

export function mapsUrl(m) {
  if (!m) return "";
  return APPLE ? (m.apple || m.google) : (m.google || m.apple);
}

// Buy-tickets target: direct ticketer URL > event listing link. NEVER a search
// engine — only send to the actual ticket seller/listing. Empty -> no button.
export function ticketsUrl(it) { return it.tickets || ""; }

export async function getJSON(u) {
  const r = await fetch(u, { cache: "no-store" });
  if (!r.ok) throw new Error(u + " " + r.status);
  return r.json();
}

export function tagCounts(week) {
  const m = new Map();
  TRACKS.forEach(t => ((week.tracks && week.tracks[t.key]) || []).forEach(it =>
    (it.tags || []).forEach(tag => m.set(tag, (m.get(tag) || 0) + 1))));
  return [...m.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

// Sort within a track: carried-over sink, popularity desc, ra.interested desc,
// then chronological by day.
export function sortItems(items) {
  return items.slice().sort((a, b) =>
    ((a.active === false) - (b.active === false)) ||           // carried-over events sink
    ((b.popularity || 0) - (a.popularity || 0)) ||             // highest popularity on top
    (((b.ra && b.ra.interested) || 0) - ((a.ra && a.ra.interested) || 0)) ||
    ((DAY_ORDER[a.day] ?? 9) - (DAY_ORDER[b.day] ?? 9)));       // then chronological by day
}

// Hash format: #/<week_start>/<eid>
export function parseHash() {
  const h = decodeURIComponent((location.hash || "").replace(/^#\/?/, "")).trim();
  if (!h) return {};
  const p = h.split("/").filter(Boolean);
  return p.length >= 2 ? { week: p[0], eid: p.slice(1).join("/") } : {};
}

// Default week when no #/<week> anchor is given: ALWAYS the current week — the one
// whose Mon–Sun span contains today. Past and future weeks may both exist, but the
// default is current. If today is inside no listed week (gap), pick the NEAREST week
// by date, preferring an upcoming one over a past one. week_start values are Mondays.
export function currentWeekStart(wks) {
  const now = new Date();
  const t = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const DAY = 86400000;
  let best = null;
  for (const ws of wks) {
    const [y, m, d] = ws.split("-").map(Number);
    const s = new Date(y, m - 1, d), e = new Date(y, m - 1, d + 7);
    if (t >= s && t < e) return ws;                        // today is inside this week → current
    // distance in days from today to this week's span (0 if inside, handled above)
    const dist = t < s ? (s - t) / DAY : (t - e) / DAY + 1;
    const future = t < s;
    // nearest wins; tie → prefer upcoming
    if (!best || dist < best.dist || (dist === best.dist && future && !best.future))
      best = { ws, dist, future };
  }
  return best ? best.ws : (wks[0] || null);
}
