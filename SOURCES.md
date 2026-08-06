# Party Scout — sources: the method

**The source lists themselves are structured data now**, in this repo beside
`cities.json`:

| File | Owner | What it holds |
|------|-------|---------------|
| [`data/sources.json`](data/sources.json) | the **weekly scan** | every web/API source: ticketers, per-city anchor listings, venues, promoters |
| [`data/ig_handles.json`](data/ig_handles.json) | the **hourly IG scout** | every Instagram handle we watch |

Two lists, one owner each: changing a handle cannot disturb the scanner's sources
and vice versa. They are loaded and **validated** by
`party-scout-agent/source_registry.py` — a missing field, a duplicate id, a
malformed URL or a typo'd key raises an error naming the entry, so a half-edited
registry stops a run loudly instead of quietly shrinking the source list.

```bash
python3 source_registry.py            # lint both files, print a summary
python3 source_registry.py --json     # the whole registry, machine-readable
```

This file keeps only what prose is actually good for: **how** to read a source,
and why the lists look the way they do. The scan's binding doctrine is
`party-scanner/SCAN_RULES.md`; the data spec is `REQUIREMENTS.md` + `MODEL.md`.

---

## Editing the registry

Add a source or a handle by adding an entry — that is the whole procedure, and
there is **no second copy to keep in sync**. `ig_events.py` reads
`data/ig_handles.json` directly (it used to restate the list as `SEED_HANDLES`;
that duplication is gone), and `scan_stats.jsonl` records yield against the same
ids the registry defines.

Every entry carries a **stable `id`** (`handle` for an IG entry). That id is what
per-source yield is recorded under, so it must not be renamed casually — rename
one and its history stops adding up. Names used before the ids existed live on as
that source's `aliases`, which is how `scan_stats.py summary` still folds the old
records into the right row.

**Fields, and what the values mean.** `use`: `listing` (it lists events),
`price`, `flyer`, `rating`. `track`: `music`, `sports` (both if it serves both);
`focus` is the free-text sharpening — `techno`, `cycling`, `hardcore`. `fetch` is
the cheapest method known to work: `HTTP` (plain `web_fetch`), `GQL`
(`ra.co/graphql`), `JSON-LD` (schema.org in the page), `common` (the
remote-browser `common` session — real Chrome, passes Cloudflare/JS),
`ephemeral-RBS` (a throwaway remote-browser session), `web_search`. `kind`:
`ticketer`, `anchor` (a per-city listing worked every scan), `venue`, `promoter`,
`directory` (national, filter by city).

**`status` is how a source stops being scanned without being forgotten:**

- `active` — worked normally.
- `documented` — deliberately parked. Today that is the **San Diego** promoters:
  they surfaced on the 19hz "Los Angeles" listing (which spans all SoCal) but are
  genuinely San Diego, and there is no `san-diego` city here yet, so their events
  have no week file to be filed into. RA agrees SD is its own region
  (`ra.co/events/us/sandiego`, area 309, separate from LA's area 23). Do **not**
  scout them into LA or SF; flip them to `active` if a San Diego city is added.
  A `documented` handle is not in the scout's roster.
- `excluded` — deliberately NOT scanned, with the reason in `notes`. Today:
  **Stern Grove Festival** (an annual once-a-year festival series, not the
  recurring nightlife scene Party Scout tracks). Events already in the DB stay;
  the point is not to scan the site for more.

The registry validates cities against `data/cities.json`, so an `active` entry in
a city the site does not publish is an error rather than a silent dead end.

## Per-source parsers

A source may declare a `parser` — a module in `party-scanner/` that extracts it
better than the generic agent fetch. **Only two exist, and both were written
because the generic path was insufficient**, not on principle:

- `ra_interest.py` (`resident-advisor`) — `ra.co/graphql` is unauthenticated and
  not Cloudflare-gated, while the HTML is gated. One call returns the heart count,
  address, times, cost, blurb, flyer and lineup.
- `eb_demand.py` (`eventbrite`) — the JSON-LD carries the price range and the
  SoldOut flag that the rendered page hides.

Everything else is fetched generically, per its `fetch` value. **Do not write a
parser speculatively.** There is a precedent: a previous set (`tixr.py`,
`ticketweb.py`, `rb_fetch.py`, `enrich_ra.py`) lived in a `party-scout-code` repo
that no longer exists anywhere — those scripts were abandoned and left behind as
dead references. The extraction *technique* each one encoded is preserved in the
relevant source's `notes`, which is the part that was actually worth keeping.

The bar for a new one: `scan_stats.py summary` shows the source is worth it (real
kept-event volume) **and** the generic fetch is measurably failing on it (breaking,
expensive, or losing the price). Declare it as `parser` on the entry so the
registry, not a comment, says which sources have one.

## Price-source order

Cheapest → heaviest: **19hz's price column → RA GraphQL → Eventbrite JSON-LD →
`common`-session render** (Tixr / AXS / RA HTML / venue box office). Free, outdoor
or park events are `Free`; leave the price blank only when it is genuinely
unobtainable — never guess a number.

Gotcha: venue pages (Fox → AXS, Regency → AXS/Ticketmaster) hide the price in a
Buy-Tickets widget or iframe. Open/expand the widget; scraping the page body finds
nothing.

## Instagram scouting — method and focus

> ✅ **RE-ENABLED (2026-07-02, owner go-ahead).** The Instagram scout is back on
> for discovery. Run `ig-party-scout/ig_events.py`, but follow **every** rule in
> the crawler's `instagram/README.md` (human-emulation: UI/mouse only for
> interactive actions, no URL jumps, Search-bar nav, slow moves, typed pauses,
> feed breaks; private-API reads are fine). Paused 06-25 for account safety; the
> owner accepted the risk with "follow all the rules."

We periodically parse the curated handles in `data/ig_handles.json`
(authenticated `instagram` session). The chain is **handle → profile (bio +
external link) → fetch that linktr.ee/site → AI-parse the events** (date, venue,
price, ticket link). DJs and promoters often put their **next gig date right in
the bio text** (e.g. "6/26 @halcyon_sf") or in **post captions and flyers** — read
those too, not just the linktree. Each entry's `notes` says where that particular
handle actually puts its dates. Run crews feed the **sports** track.

> **Sourcing focus — small local events:** the goal is small local parties and bar
> nights, so per city prioritise **LOCAL DJs who self-promote their OWN parties**
> (residents posting their gig flyers) over big touring headliners just passing
> through. Locality is **per city**: DJ Flapjack is LA-based → an LA source, not an
> SF one; Rafer Rawb / Dr1ft / Froggin are Bay-local → SF sources.

```bash
python3 ig-party-scout/ig_events.py                              # the whole roster
python3 ig-party-scout/ig_events.py soundmeditationpresents audiumsf   # specific handles
```

## What the cities mean

**San Francisco (`san-francisco`) = the whole Bay Area / NorCal**, not just the
city. Oakland, Berkeley, San Jose, Fremont, Stockton, the North Bay all belong
here — a DJ or event anywhere in the region is an SF source. That is why 19hz uses
the **Bay Area** listing and why Oakland/Stockton DJs (Rafer Rawb, Dr1ft, Froggin)
sit in this city. Only a genuinely different metro gets its own city.

**Los Angeles (`los-angeles`)** has its anchor listings and its big promoters, but
**no venue entries and no run/cycle crews yet** — add them as they surface via the
19hz LA listing or RA. The 19hz "Los Angeles" listing spans all of SoCal, so check
each row is really LA before filing it.

---

> Keep the registry current: when a site changes, dies, or a new ticketer or handle
> shows up, edit `data/sources.json` / `data/ig_handles.json` and say what changed
> in the run report. They are the authoritative lists everything else cites.
