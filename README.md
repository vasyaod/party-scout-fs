# Party Scout FS

Public weekly database of SF / Bay Area events (music + sports), one report per
week. Powers a small GitHub Pages site that reads the JSON straight from `data/`.

**🌐 Live site: https://vasyaod.github.io/party-scout-fs/**

## File index

Read this whole file before modifying data in the repo.

- [SOURCES.md](SOURCES.md) — master list of sites we pull listings + prices from (canonical)
- [REQUIREMENTS.md](REQUIREMENTS.md) — rules the data and site must follow
- [MODEL.md](MODEL.md) — JSON data model, field by field

## Layout

```
index.html        GitHub Pages app (vanilla JS, reads data/*.json)
SOURCES.md        master list of sites we pull listings + prices from (canonical)
REQUIREMENTS.md   rules the data and site must follow
MODEL.md          JSON data model, field by field
CNAME             custom domain (party-scout-fs.f-proj.com)
.nojekyll         serve files as-is (no Jekyll processing)
data/
  index.json      list of all weeks, newest first
  <YYYY-MM-DD>.json   one week (Monday-dated), machine-readable
  <YYYY-MM-DD>.md     same week, human-readable digest
```

Each week is named after the **Monday** of the week its window falls in, e.g.
the Thu–Sun Jun 25–28 2026 weekend lives under `2026-06-22.*`.

## Week JSON shape

See **[MODEL.md](MODEL.md)** for the full field-by-field JSON data model (week
object, per-event fields, `index.json`). The rules behind those fields — pricing,
merge/never-delete, JSON-only-but-actionable links, verification — are in
**[REQUIREMENTS.md](REQUIREMENTS.md)**.

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
