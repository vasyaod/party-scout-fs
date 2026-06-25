# Party Scout FS

Public weekly database of SF / Bay Area events (music + sports), one report per
week. Powers a small GitHub Pages site that reads the JSON straight from `data/`.

**🌐 Live site: https://vasyaod.github.io/party-scout-fs/**

## Layout

```
index.html        GitHub Pages app (vanilla JS, reads data/*.json)
SOURCES.md        master list of sites we pull listings + prices from (canonical)
.nojekyll         serve files as-is (no Jekyll processing)
data/
  index.json      list of all weeks, newest first
  <YYYY-MM-DD>.json   one week (Monday-dated), machine-readable
  <YYYY-MM-DD>.md     same week, human-readable digest
```

Each week is named after the **Monday** of the week its window falls in, e.g.
the Thu–Sun Jun 25–28 2026 weekend lives under `2026-06-22.*`.

## Week JSON shape

```json
{
  "week_start": "2026-06-22",
  "window": "2026-06-25..2026-06-28",
  "title": "SF Pride weekend (stacked)",
  "location": "San Francisco & Bay Area",
  "tracks": {
    "music":  [ { "id", "track", "category", "name", "day", "time",
                  "area", "venue", "price", "tags": [], "link",
                  "tickets", "maps": { "google", "apple" }, "active",
                  "ra": { "event_id", "url", "interested", "attending" } } ],
    "sports": [ ... ]
  }
}
```

`id` is stable across re-runs of the same week (derived from the event's fields),
so the site can track the same event over time.

`ra` carries the **Resident Advisor rating** (`interested`/`attending` heart count)
for events that link to ra.co — a popularity signal; `{}` when the event isn't on RA.

`tickets` (buy-tickets URL) and `maps` (`{google, apple}` Maps search links) are
never shown as raw URL text. The site exposes them only as **🗺 Map** / **🎟 Tickets**
buttons (the URL is just the `href`); the Map button opens **Apple Maps on
iOS/iPadOS/macOS, Google Maps elsewhere**. `active: false` marks a "carried over"
event kept from a prior scan (see Updating).

## Updating

The files here are generated — do not hand-edit. The generator lives in
`party-scout-code` (in the agent workspace):

```
python generate.py weeks/<week>.input.json --repo /path/to/party-scout-fs
```

## Site

GitHub Pages serves from the repo root. Live at
**https://vasyaod.github.io/party-scout-fs/** — pick a week from the dropdown,
browse events grouped by track. Each card links out where a link exists.
