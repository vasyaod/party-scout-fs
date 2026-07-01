# REQUIREMENTS.md — rules the data and site must follow

The agreed rules for the Party Scout weekly database and site. Anything that
generates or edits the data must honor these. (Field shapes live in
[MODEL.md](MODEL.md); where data comes from lives in [SOURCES.md](SOURCES.md).)

## Cities

Data is partitioned **by city**. Each city is a kebab-case `slug` with a display
`label`, and its weeks live under **`data/<slug>/`** (`index.json` + the per-week
`<week>.json`/`.md`). The top-level **`data/cities.json`** lists the offered cities,
in order (first = site default). Each week input carries `city` + `city_label`;
`generate.py` writes to `data/<city>/` and keeps `cities.json` in sync.

**Current city list:**

| slug | label | location | sources |
|------|-------|----------|---------|
| `san-francisco` | San Francisco | San Francisco & Bay Area | 19hz Bay Area, RA SF, EDMtrain SF, … (see SOURCES.md) |
| `los-angeles` | Los Angeles | Los Angeles & SoCal | 19hz LA, RA LA, EDMtrain LA, Funcheap LA, … |

Add a city by: scanning its weeks into `weeks/<slug>/<week>.input.json` (with `city`
+ `city_label` set), running `generate.py`, and adding it to this list. Every city
follows ALL the rules below (per-week, per-track). Week files are still Monday-dated
within each city.

On the site, default city selection should be: hash deep-link -> saved city choice ->
browser geolocation if the user already granted it -> IP-based geolocation fallback
-> San Francisco.

## Data integrity

1. **Verify every event.** Each event must tie to a concrete source (ticket /
   listing / venue page). If it can't be verified, **drop it** — never keep vague,
   unsourced entries. (This is what caught and removed "Pride Rooftop Party
   (daytime)".)
1a. **`sources` is an ordered list; index 0 is the highest priority.** Every event's
   info/source links live in a `sources` **array** (replaces the old single `link`;
   see MODEL.md) — the **Open** button uses `sources[0]`. The list is
   **priority-ordered: the FIRST link is the most authoritative** (the anchor we
   trust most; e.g. the RA/venue listing). Put the primary link first. Scrape
   sources (19hz) are never stored. On merge the order is preserved (first wins) and
   new links are appended; `[]` when none is known.
2. **Never guess.** Leave a field `""` rather than inventing a value (price,
   venue, address, URL).
3. **Weeks are Monday-dated, and every event is filed by its own date.** A week
   file/`week_start` is the Monday of the week it covers. When a new event is found
   (from any source — the scan, the Instagram organizers in SOURCES.md, or one the
   user forwards), route it into the week whose Monday contains **that event's date**
   and merge it there — **create the week file if it doesn't exist yet.** Never dump
   an event into the current week regardless of date; one organizer's events can land
   in different weeks, so split them by date.
3a. **Every week has a short `title` (3–4 words).** Each week's `title` is a tight
   3–4-word label capturing the weekend's character (e.g. `"SF Pride weekend"`,
   `"July 4th weekend"`). No parentheticals or trailing qualifiers like
   `"(stacked)"` / `"(open-air + block parties)"` — keep it punchy. It shows in the
   site's week picker (`window · N events · title`), so it must stay scannable.

## Volume

4. **Target ~40 events per track to start — NO upper cap.** Aim for about 40 events
   per track (music/EDM and sports/active) in the initial scan; **going over is
   normal and fine — 50, 60+ is all good.** 40 is a starting target, not a ceiling.
   Gather and verify as many real in-window events as exist. Fewer is fine when the
   weekend is thin; never pad to hit a number, and never drop a real event to stay
   under one.

## Pricing

5. **Always pull a ticket price** for every event — `"$NN"`, a range `"$NN–MM"`,
   or `"Free"`. Source order: 19hz price column → RA GraphQL → Eventbrite JSON-LD →
   real-browser render of the ticketer (see SOURCES.md). Free/outdoor → `Free`.

## Merging (updates)

6. **Merge, never overwrite.** Re-running a week folds new data into the existing
   JSON, field by field, keyed by the stable `id`. New non-empty values win;
   otherwise the previously-pulled value is kept (a price/link grabbed earlier is
   never wiped by a later run that lacks it). Tags are unioned.
7. **Never delete events.** A party can drop out of view but still exist — an event
   missing from the latest scan is kept and flagged `active: false` ("carried
   over"); it flips back to `active: true` if it reappears.

## Links & buttons (site)

8. **No raw URLs as text.** `sources`, `tickets`, `maps` live in the JSON and are
   surfaced only as buttons / the `open map` link — never printed as URL text, in
   the site or the Markdown digest.
9. **Buy ticket → the real seller only.** `tickets` is a list; `tickets[0]` (the Buy-ticket target) points at the actual ticketer
   (RA / Tixr / Eventbrite / Etix / Ticketmaster / AXS / venue). **Never** a search
   engine. No real seller → no Buy-ticket button.
10. **Open → the event website** (`sources[0]`): event info/lineup page.
11. **No circular / source links.** Never store a scrape source (e.g. `19hz.info`) in
    an event's `sources` list — it just points back at our own aggregator. Resolve
    the event's real page (RA / Tixr / Eventbrite / venue / official site) or leave
    `sources` empty (no Open button). Same for any other listing index we pull from.
12. **Map per device.** The 📍 location's `open map` link opens **Apple Maps on
    iOS/iPadOS/macOS, Google Maps elsewhere**, using the per-event `address` for a
    precise pin when known.
12a. **Every event gets `coords` — exact venue, else the city.** Store `{lat, lon}`
    (WGS84 decimal degrees) in `coords` for a map pin / future map view. Filled by
    `geocode.py` (OpenStreetMap Nominatim, free, no key; honors its policy —
    descriptive User-Agent, ≤1 req/sec, on-disk cache). Resolve the **most precise
    point** first: `address` → known-venue address → `venue, area`. **If the exact
    venue can't be pinned, fall back to the event's CITY** — geocode the `area` as a
    city (e.g. a Sunnyvale venue we can't find → use **Sunnyvale's** coordinates),
    then the week's `city_label`. Set **`coords_precise`**: `true` for an exact venue
    point, `false` for a city-level fallback (so the map never drops a precise pin on
    a city centroid). **Never guess** — only if even the city won't resolve is
    `coords` left `null`. Both fields are preserved across re-runs (a point pulled
    earlier is never wiped by a later run that lacks it).
13. **Price on the button.** Price is combined into the Buy-ticket button
    (`$NN · Buy ticket`); `Free` is a gold, same-size, non-clickable button.
14. **Aligned cards.** In a row, tags and the action button line up across cards
    (footer pinned to the bottom; an empty action row is reserved when a card has
    no button).

## Images

20. **Adding an event ALWAYS includes its image — inline, never deferred.** Whenever a
    single event is added or hand-forwarded (e.g. the user shares a flyer or asks to add
    one show), set its `image` in the SAME pass — do not commit a new event with an empty
    `image`. Order of preference: (1) a flyer the **user provided** in the conversation →
    use it; (2) a **real flyer** found for the event (`og:image` from the ticket/listing
    page, rule 20a); (3) otherwise **generate a cheap placeholder immediately** (rule 20b,
    `gen_images.py` neon-city recipe, ~1–2¢). Hosted in-repo at `img/gen/<eid>.jpg` works
    without the upload token. The point: a freshly-added card must never ship with the bare
    stub when a real or generated image was one step away.

20a. **Every event has an image.** Each event carries an `image` — a small JPG of the
    event's flyer/hero. Enrich with `enrich_images.py`: pull the page `og:image`,
    **preferring the ticket site** (`tickets[0]`, then `sources[0]`), fit to **≤512px**
    (longest side), **JPEG**. Images are **hosted on the image service**, NOT committed
    to this Pages repo (Pages can't serve Git-LFS binaries, and plain files bloat the
    repo): each is `PUT` to `https://api.party-scout.app/img/<city>/<week>/<eid>.jpg`
    (auth via `IMG_TOKEN`), and `image` is set to that public URL. No flyer found →
    **generate one** (rule 20b); only if that also fails is `image` left `""` and the
    UI shows the shared stub `https://party-scout.app/stub.jpg`. The `og:image` lookup
    is deterministic (no model needed); the intelligent fallback (read the page, pick
    the real poster, skip logos/avatars) may run on a cheaper model (e.g. Sonnet).
20b. **Generate a placeholder when no real flyer exists — text-free club-scene recipe.**
    When `enrich_images.py` can't find a real flyer, **generate** one with the recipe
    below (implemented in `party-scout-code/gen_images.py`). See
    `party-scout-code/IMAGE_GEN_PROMPT_HISTORY.md` for the prompt version history and why
    the earlier neon-city-reference recipe was dropped.
    - **Model + endpoint:** `gpt-image-1-mini`, `quality=low`, via the **image *generations***
      endpoint (`POST https://api.openai.com/v1/images/generations`). **No style-reference
      image** — the neon look is carried by the prompt.
    - **Prompt = a TEXT-FREE atmospheric scene** evoked from `category`/genre + vibe `tags`:
      a cinematic nightclub scene (silhouetted crowd facing a DJ booth, volumetric haze,
      bold neon laser lighting — deep blues/purples, magenta + teal glow, moody and dark);
      sports track → a dynamic outdoor neon-tinged action scene. **Do NOT** pass the event
      `name`/`summary`/`why` as rendered text — that produced ugly, misspelled headline
      letters. Hard negative: "ABSOLUTELY NO text, no letters, no words, no typography, no
      logos, no signage, no faces." (The card UI already shows the title.)
    - **Output:** downscale to **≤512px JPEG**, save to **`img/gen/<eid>.jpg`** in this
      repo (Pages serves it; no upload token needed), set
      `image = https://party-scout.app/img/gen/<eid>.jpg`, and mark **`image_generated: true`**.
    - **Cost:** ~1–2¢ each (≈ \$1 for a full ~80-event pass). The script is
      idempotent/incremental — it only touches events with an empty `image` and writes
      each result immediately, so it's safe to re-run/resume.
    - **Free route (preferred for bulk fills):** offload generation to the **`codex`
      agent** (openai/gpt-5.5), whose `image_generate` tool is covered by the
      ChatGPT/Codex subscription — **\$0, no paid `OPENAI_API_KEY`**. Same text-free
      recipe/prompt and same `img/gen/<eid>.jpg` output. Procedure + dispatch prompt:
      **`party-scout-code/CODEX_IMAGE_GEN.md`**; build the resumable work-list with
      `party-scout-code/gen_missing_list.py` → `tmp/missing_images.json`. **Mandatory:
      VERIFY files on disk after every Codex run — Codex frequently returns empty text
      even when it succeeded**, so never trust its self-report; re-run
      `gen_missing_list.py` and re-dispatch the shrinking remainder until missing=0.
      Keep `gen_images.py` (paid) as the fallback.
20c. **A generated image is a placeholder, not final — replace it.** `image_generated:
    true` means "no real flyer yet." A later enrichment run **re-attempts** these and,
    if it now finds a real flyer, **overwrites** the generated image and flips
    `image_generated` to `false`. Never overwrite a *real* flyer with a generated one,
    and never overwrite a generated one with the stub.

## Generation

15. Data is **generated**, not hand-edited. The generator + reusable enrichment
    (RA ratings, per-event research) live in `party-scout-code`. Read SOURCES.md,
    MODEL.md, and this file before changing the data.

## Enrichment (AI / subagents)

16. **Resolve fields intelligently with AI subagents.** Don't ship whatever the raw
    scan emits — fan out per-event research agents (parallel) to verify each event is
    real and resolve its fields (venue, exact address, price, ticket URL, event
    website, tags, RA rating). New events and any sparse/unverified ones get this
    pass; unverifiable events are dropped (rule 1). This is how the data reaches the
    quality the rest of these rules assume.
17. **Score hidden popularity (0–10).** Every event gets a `popularity` integer
    (0–10) — a **hidden** ranking signal, never shown on the site. Fill it
    heuristically from real characteristics: RA interest count, headliner / marquee
    fame (≈ Google-Trends-level recognition), festival/block-party scale, price tier.
    It's a rough nudge for ordering, not a displayed rating.
18. **Write a DIFFERENTIATOR `why`.** Each event gets a punchy one-liner (~8–16
    words) that is the single thing helping someone pick THIS event over the others
    that weekend — vibe, who it's for, what's rare, the trade-off, free/outdoor
    appeal. **Never restate the lineup / artist names / titles** (already in the
    event name) and **never describe what happens** (that's `summary`). Shown on the
    card; generated by the enrichment pass (rule 16).
19. **Read the event page → write `summary` + `why`.** Visit every event's own page
    (`sources[0]`/`tickets`) via an **ephemeral remote-browser session** (real Chrome;
    **max 5 in parallel**, one throwaway session per event, deleted after), pull the
    readable text, and have AI write the `summary` (1–2 sentences) and refine `why`
    from what the page actually says. Fall back to known metadata when a page is
    gated/empty; never invent.

## Identity & deep-linking

20. **Two ids, different jobs.** `id` is the stable MERGE key (rule 5) — never use
    it for the UI. `eid` is a short, URL-safe, week-unique **selection id** for
    deep-linking only; it is **not** used for merging.
21. **Deep-link to a card via `#/<week_start>/<eid>`.** The hash carries both the
    week and the event, e.g. `…/#/2026-06-22/kaskade-90bf` — the site loads that
    week, then reveals (past Show more), scrolls to, and highlights the event. A
    per-card `#` anchor copies that link.
