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
1a. **`sources` is an ordered list; index 0 is the highest priority — and it must
   collect EVERY site the event appears on, not just one.** Every event's info/source
   links live in a `sources` **array** (replaces the old single `link`; see MODEL.md)
   — the **Open** button uses `sources[0]`. **Gather all distinct sites where the
   event is listed or mentioned** and store them as separate entries: the event's
   official/organizer page, the **venue's own event page** (e.g. `themidwaysf.com`,
   `1015.com`), the **ticketer** (RA / Tixr / Eventbrite / AXS / Dice), the IG
   organizer post/permalink it was scouted from, and any editorial listing
   (Funcheap, DoTheBay, etc.). Do **not** keep only the ticket link and drop the site
   the event was discovered on. The list is **priority-ordered: the FIRST link is the
   most authoritative** (the anchor we trust most; e.g. the RA/venue listing) — put
   the primary link first, the rest after. The ONLY things excluded are our own
   **scrape aggregators / listing indexes** (19hz and similar — see rule 11): those
   just point back at our own pipeline, so resolve them to the real page instead of
   storing them. Deduplicate by URL. On merge the order is preserved (first wins) and
   new links are appended; `[]` when none is known.
1b. **Same event from another source → ADD the source, never duplicate.** When a scan
   finds an event that is **already in the DB** — the same real-world event (match on
   artist/name + date + venue, even if a *different* source surfaced it or the title
   string differs) — do **not** create a second card. Fold the new URL into the existing
   event's `sources` (and `tickets` if it's a ticketer) per rule 1a, and merge any newly
   learned fields (price, address, flyer…). Add a NEW event only when it is genuinely not
   present yet. Note `generate.py` merges by a stable `id` derived from
   week+track+name/day/area/venue, so when the new source spells the name/venue
   differently, reuse the existing event's `id` (edit the existing entry) instead of
   letting a near-duplicate spawn a second card.
1c. **Auto-add new events — don't ask.** When a scan (or a source the user forwards)
   turns up an event that is **verified** (rule 1), **in the scan window**, and **not
   already in the DB** (rule 1b dedup), ADD it immediately with full enrichment — do
   **not** pause to ask "want me to add it?". Report what was added afterward. Only stop
   to ask when there's a genuine judgment call (off-genre / quality doubt, a data
   conflict, or an event that would need guessing a core field). Default is act, then
   summarize.
2. **Never guess.** Leave a field `""` rather than inventing a value (price,
   venue, address, URL).
2a. **Structured start/end times.** Besides the human `time` string, each event
   carries **`start`** and **`end`** as 24-hour **`"HH:MM"`** strings (or `null` when
   unknown). These are what the site uses for the fade / past-event logic, so it
   never has to parse the fuzzy `time` (which broke on "4–10pm" etc.). Rules:
   `end` earlier than `start` ⇒ the event **crosses midnight** (e.g. `"22:00"` →
   `"03:00"`); a lone start with no end (`"9pm"` → `start:"21:00", end:null`) gets a
   ~4h grace client-side. When you ADD an event, set `start`/`end` explicitly from
   the flyer when you can (most reliable); otherwise `generate.py` derives them from
   `time` (`derive_times`). `null`/omitted is fine when there's genuinely no time.
2b. **Optional DJ lineup.** Events may carry a **`lineup`** — an array of
   `{name, instagram}` objects, one per DJ/artist on the flyer. `name` is the
   artist as printed; `instagram` is the **handle only** (username, no `@`, no URL —
   the site builds `instagram.com/<handle>`), or **`null`** when a handle can't be
   confirmed. **Optional** — omit or use `[]` when there's no lineup (venue nights,
   runs, etc.). When adding an event, parse the DJ list from the flyer/caption and
   look up each handle (IG search); **never guess a wrong handle** — `null` if unsure.
   Backfill existing events gradually; nothing breaks when it's absent.
3. **Weeks are Monday-dated, and every event is filed by its own date.** A week
   file/`week_start` is the Monday of the week it covers. When a new event is found
   (from any source — the scan, the Instagram organizers in SOURCES.md, or one the
   user forwards), route it into the week whose Monday contains **that event's date**
   and merge it there — **create the week file if it doesn't exist yet.** Never dump
   an event into the current week regardless of date; one organizer's events can land
   in different weeks, so split them by date.
3b. **Scan window = current week + the next 3 weeks (4 Monday-dated buckets).** "In the
   scan window" (rules 1c, 4) means an event whose date falls in the current week's
   Monday through the end of the 3rd week after it — 4 weekly buckets total. E.g. with
   the current Monday `2026-06-29`, in-window = weeks `2026-06-29, 07-06, 07-13, 07-20`
   (dates through Sun 2026-08-02). Events dated beyond that are out-of-window: note
   them, don't add them, until the window rolls forward to include them. (Widened from
   3→4 buckets on 2026-07-04.)
3d. **Big events found individually → add even when out-of-window.** The scan-window
   gate (3b) is for routine scans. When a **large event** — a festival, multi-day
   campout, big-venue headliner, or major recurring institution — is found
   individually (user-forwarded or specifically surfaced), ADD it immediately even if
   its date is **beyond** the scan window. Rationale: big events are announced far
   ahead and almost never cancel, so parking them until the window rolls just loses
   coverage. File it into its own week bucket (create it if needed, rule 3), full
   enrichment. Still gated by genre/quality (rule 1) and dedup (rule 1b). Small one-off
   club nights stay window-bound (those can move or cancel).
3c. **Research the WHOLE week, not just the weekend.** When scanning/searching for
   events, cover all seven days **Mon–Sun**, not only Fri–Sun. Weeknight nightlife is
   real and in-scope — Monday goth/industrial nights, Tuesday/Wednesday residencies,
   Thursday openers, midweek gigs and day events all count. Don't skip a day because
   it isn't the weekend; file each event into its own date (rule 3) whatever weekday
   it lands on. The ~40-per-track target (rule 4) spans the full week, not the weekend
   alone.
3e. **The weekly scan uses WEBSITES / APIs only — Instagram is a SEPARATE process.**
   The scheduled scan pulls from the web/API sources in SOURCES.md (19hz, RA,
   EDMtrain, Eventbrite, Dice, Tixr, TicketWeb, venue sites, Funcheap, Meetup, etc.).
   **Do NOT run the Instagram scout as part of the weekly scan.** Instagram
   organizer/DJ handles are covered by a **separate hourly IG scout** cron ("IG hourly
   random-handle event scout"), which shares the single `instagram` session — running
   IG from the weekly scan too would contend for that session and duplicate work.
   Events surfaced by the IG scout (or user-forwarded) still merge into the same DB
   normally; the weekly scan just doesn't crawl IG itself.
3a. **Every week has a short `title` (3–4 words).** Each week's `title` is a tight
   3–4-word label capturing the week's character (e.g. `"SF Pride weekend"`,
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
11. **No circular / source links — but that means ONLY third-party scrape indexes.**
    Never store a **third-party aggregator / listing index** we scrape (e.g.
    `19hz.info`, or any multi-venue index) in an event's `sources` list — it just
    points back at our own pipeline. Resolve the event's real page instead, or leave
    `sources` empty (no Open button). **This exclusion does NOT apply to a venue's own
    site** (`themidwaysf.com`, `1015.com`, `halcyon-sf.com`, …) or an organizer's own
    page — those are legitimate first-party sources and SHOULD be collected under rule
    1a alongside the ticketer. The line: a site that lists many unrelated venues =
    excluded aggregator; the venue/organizer describing its own event = keep it.
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

20a. **Every event has an image — REAL FLYER FIRST, always.** Each event carries an
    `image` — a small JPG of the event's flyer/hero. **A generated placeholder is a last
    resort: only generate (rule 20b) when NO real flyer can be found on ANY of the event's
    sources.** Enrich with `enrich_images.py`: pull the page `og:image`, and **try EVERY
    URL the event has — every entry in `tickets[]` then every entry in `sources[]`** (the
    ticketer, the venue's own page, the organizer page, editorial listings — the full
    multi-site list rule 1a now collects), not just the first one. Take the first real
    flyer found. Fit to **≤512px** (longest side), **JPEG**. Images are **hosted on the image service**, NOT committed
    to this Pages repo (Pages can't serve Git-LFS binaries, and plain files bloat the
    repo): each is `PUT` to `https://api.party-scout.app/img/<city>/<week>/<eid>.jpg`
    (auth via `IMG_TOKEN`), and `image` is set to that public URL. No flyer found →
    **generate one** (rule 20b); only if that also fails is `image` left `""` and the
    UI shows the shared stub `https://party-scout.app/stub.jpg`. The `og:image` lookup
    is deterministic (no model needed); the intelligent fallback (read the page, pick
    the real poster, skip logos/avatars) may run on a cheaper model (e.g. Sonnet).
20b. **Generate a placeholder ONLY when no real flyer exists — text-free club-scene recipe.**
    **Generation is the fallback of last resort — never generate an image while a real
    flyer is still reachable on any of the event's sources (rule 20a).** Only once
    `enrich_images.py` has checked **every** `tickets[]`/`sources[]` URL and found no real
    flyer do you **generate** one with the recipe below (implemented in
    `party-scout-code/gen_images.py`). See
    `party-scout-code/IMAGE_GEN_PROMPT_HISTORY.md` for the prompt version history and why
    the earlier neon-city-reference recipe was dropped.
    - **Model + endpoint:** `gpt-image-1-mini`, `quality=low`, via the **image *generations***
      endpoint (`POST https://api.openai.com/v1/images/generations`). **No style-reference
      image** — the neon look is carried by the prompt.
    - **Prompt = a TEXT-FREE atmospheric scene** evoked from `category`/genre + vibe `tags`.
      **Palette + scene are varied per-event, seeded deterministically from `eid`** (a hash
      picks one of ~10 palettes and one of several scene archetypes) so flyers do NOT all
      read as the same neon club shot — neighbours in a week look visibly different, but a
      re-run reproduces the same image family. Music track → a cinematic club/festival/rave
      scene; sports track → a dynamic outdoor action scene. **Do NOT** pass the event
      `name`/`summary`/`why` as rendered text — that produced ugly, misspelled headline
      letters. Hard negative: "ABSOLUTELY NO text, no letters, no words, no typography, no
      logos, no signage, no faces." (The card UI already shows the title.)
    - **Output:** downscale to **≤512px JPEG**, save to **`img/gen/<eid>.jpg`** in this
      repo (Pages serves it; no upload token needed), set
      `image = https://party-scout.app/img/gen/<eid>.jpg`, and mark **`image_generated: true`**.
    - **Cost:** ~1–2¢ each (≈ \$1 for a full ~80-event pass). The script is
      idempotent/incremental — it only touches events with an empty `image` and writes
      each result immediately, so it's safe to re-run/resume.
    - **Route: use `gen_images.py` directly (the paid OpenAI API).** This is the
      standard path for all fills, bulk included. **Do NOT route generation through the
      `codex` agent** — despite appearances its `image_generate` is **not free**, it
      charges our own API tokens, so it buys nothing over calling the API directly and
      adds an unreliable indirection (empty self-reports). The Codex route is retired;
      `CODEX_IMAGE_GEN.md` is kept only as a historical note.
20c. **A generated image is a placeholder, not final — replace it.** `image_generated:
    true` means "no real flyer yet." A later enrichment run **re-attempts** these and,
    if it now finds a real flyer, **overwrites** the generated image and flips
    `image_generated` to `false`. Never overwrite a *real* flyer with a generated one,
    and never overwrite a generated one with the stub.

20d. **Image enrichment runs event-by-event, not as a batch — one sub-sub-agent per
    event, commit every 5–10.** When a Sonnet enrichment sub-agent fills images, it must
    process events **one at a time**, spawning a small **event sub-sub-agent per event**
    that does the full "discover the real flyer (rule 20a) → generate a placeholder only
    if none is found (rule 20b)" for that single event. **Do NOT** run image discovery/gen
    as one big batch pass over the whole week — per-event keeps each unit small, isolates
    failures (a gated page or a bad gen doesn't stall the rest), and lets a real flyer be
    resolved before falling back to generation. **Commit after every 5–10 events** (not
    once at the very end) so progress is durable and a crash never loses a long unsaved run.

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
16a. **Batch scanning + deduping along week / day / city / source dimensions — and
    collect stats.** When fanning out scan + dedup work across sub-agents, partition it
    into batches keyed by any of these dimensions — **week**, **day**, **city**,
    **source** (19hz / RA / EDMtrain / Eventbrite / venue site …) — or a **combination**
    (e.g. one batch per `(city, week)`, per `(city, day)` when a week is dense or a single
    weekday is under-covered, or per `(city, source)` to run one source end-to-end). Pick
    the granularity to fit volume: coarse (a whole `city×week`) when the week is thin,
    **fine (per-day or per-source)** when it's dense or when a specific day/source is a
    known gap (the Monday-0 miss is exactly why per-day batches matter — rule 3c; a source
    that returned nothing is why per-source batches surface coverage holes). Each batch
    runs the same verify → dedup (rule 1b) → enrich flow.
    **Collect and report stats per batch** — events found, added, merged/deduped, dropped
    (unverified), and images real vs generated — broken down by the batch dimension, so
    coverage holes (e.g. a weekday with 0 events, a thin city-week) are visible and can be
    re-scanned. Surface the stats in the run's summary/report.
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

## Date filters (site + app)

22. **Quick date filter chips, above the grid.** In place of the always-on week
    dropdown, show a chip row: **This week** (default) · **Today** · **Tomorrow** ·
    **Next week** · **📅 (pick week)**. Identical behaviour on web and phone (mirror
    both `App.jsx`s + `lib.js`). No separate clear button — the **This week** chip is
    the reset.
    - **This week** — the current weekly bucket (`currentWeekStart`); the default.
    - **Today / Tomorrow** — load whichever weekly bucket *contains that date*
      (`weekStartOn`; tomorrow can spill into next week, e.g. a Sun→Mon roll) and
      narrow the grid to that single calendar date (`isOnDate`). Past-but-today
      events still show (faded), sunk to the bottom like everywhere else.
    - **Next week** — the bucket immediately after the current one (null → empty).
    - **📅 pick** — keeps the current week and reveals the `◀ WeekPicker ▶` control
      so any bucket is browsable; the dropdown is hidden in every other mode.
    - A deep link to a non-current week opens in pick mode.
    - Empty states are filter-aware ("No events today." / "…tomorrow." / "…this
      week.").
