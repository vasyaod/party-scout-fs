# Party Scout — sources master list

**Single source of truth** for the sites we pull **event listings** and **ticket
prices** from. Read this list from here — it lives in the `party-scout-fs` repo
(alongside the generated weekly data + the Pages site). The generator
(`party-scout-code`) and the scan spec (`party/README.md`) point here rather than
keeping their own copy.

**Structure:** a **Common** section (city-agnostic ticketers + price/flyer tools +
national sports sites + methods), then **one section per city** (San Francisco,
Los Angeles) holding that city's own anchor listings, venues, and Instagram
handles. Add a new city by adding a section with its own URLs/handles.

Legend — Use: `L` = event listing, `P` = ticket price. Fetch: `HTTP` = plain
web_fetch/HTTP, `GQL` = `ra.co/graphql`, `JSON-LD` = schema.org in the page,
`common` = remote-browser `common` session (real Chrome, passes Cloudflare/JS),
`ephemeral RBS` = throwaway remote-browser session.

---

## Common (all cities)

Ticketers + price/flyer tools you reach **via links** from the per-city listings —
same everywhere, only the event URL changes. Two of them (RA, Eventbrite) are also
browsable per-city listing sources, so their **listing URLs live in each city
section** while the extraction tool is described here.

| Site | URL | Use | Track | Fetch | Notes |
|------|-----|-----|-------|-------|-------|
| **Resident Advisor (RA)** | ra.co (per-city listing URL in city section) | P + flyer + rating | Music | GQL / common | `enrich_ra.py` → `ra.co/graphql` (bare, not Cloudflare-gated): `interestedCount`/`attending` (the "rating") + the **poster** via `event.images[]` (the `FLYERFRONT` one; `filename` = direct images.ra.co URL, downloads bare). CLI: `enrich_ra.py flyer <ra_id\|url> <out.jpg>` / `flyerurl <id>`; import `flyer_url()` / `save_flyer()`. Event HTML is Cloudflare-gated → render via `common`. |
| **Tixr** | https://www.tixr.com | P + flyer | Music | ephemeral RBS | `tixr.py`: one ephemeral remote-browser fetch (real Chrome passes **DataDome**), then reads the page's schema.org **JSON-LD** in one shot → flyer (`static.tixr.com` image, downloads bare) + **all price tiers** + venue/time/age. `event_info(url)` → `{image, offers[], price_low/high, price, address, time, …}`; `save_flyer(img_or_url, out)` fits ≤512px JPEG. price_low/high exclude add-ons (parking/coat/etc). |
| **Eventbrite** | eventbrite.com (per-city discovery URL in city section) | L + P | Both | JSON-LD | `eb_demand.py`: `offers.lowPrice/highPrice` + SoldOut/salesStatus from the page JSON-LD. |
| **Dice** | https://dice.fm | L + P | Music | common | Price in JS app. |
| **AXS / Ticketmaster / venue box office** | e.g. https://thefoxoakland.com | P | Music | common | Price sits in a Buy-Tickets **widget/iframe** — open/expand it, don't just scrape body. |
| **TicketWeb** | https://www.ticketweb.com | P + flyer | Music | ephemeral RBS | `ticketweb.py`: JS-rendered (bare = ~10KB shell), so one ephemeral remote-browser fetch → read the page's schema.org **JSON-LD** (`Event`) in one shot → flyer (`i.ticketweb.com`, downloads bare) + venue/full-address + start + price. `event_info(url)` → `{image, name, address, start, time, price, …}`; `save_flyer(img_or_url, out)` ≤512px JPEG. Note: its `price` is the **online total incl. fee** — the flyer's door price may differ. |
| **See Tickets / Posh / Etix** | various | P | Music | common | Misc ticketers the 19hz/RA rows link to. |
| **Meetup** | https://www.meetup.com | L + P | Sports | web_search / common | Rides/runs/club meets; default **Free** unless a fee is shown. |
| **RunGuides / RunningInTheUSA** | https://runguides.com · https://runningintheusa.com | L | Sports (running) | web_search | Race calendars (national — filter by city). |
| **Strava clubs** | https://www.strava.com/clubs | L | Sports | web_search | Local moto/cycling/run clubs (filter by city). |

**Price-source order** (cheapest → heaviest): **19hz column → RA GraphQL → Eventbrite
JSON-LD → `common`-session render** (Tixr/AXS/RA-HTML/venue). Free/outdoor/park → `Free`;
leave blank only if genuinely unobtainable — never guess a number.

**Excluded (do NOT scan / add as a source):**
- **Stern Grove Festival** (`sterngrove.org`, SF) — an **annual, once-a-year festival series**, not the recurring nightlife/party scene Party Scout tracks. Don't list it as a source or auto-add its concerts. (Any Stern Grove events already in the DB stay; just don't scan the site for more.)

### Instagram scouting (method + focus)

> ✅ **RE-ENABLED (2026-07-02, owner go-ahead).** The Instagram scout is back on for
> discovery. Run `instagram/ig_events.py`, but follow **every** rule in
> `instagram/README.md` (human-emulation: UI/mouse only for interactive actions, no URL
> jumps, Search-bar nav, slow moves, typed pauses, feed breaks; private-API reads are
> fine). Paused 06-25 for account safety; owner accepted the risk with "follow all the rules."

We **periodically parse curated IG handles** each scan via `instagram/ig_events.py`
(authenticated `instagram` session). Chain: **handle → profile (bio + external link)
→ fetch that linktr.ee/site → AI-parse the events** (date, venue, price, ticket link).
DJs/promoters often put their **next gig date right in the bio text** (e.g. "6/26
@halcyon_sf") or in **post captions/flyers** — read those too, not just the linktree.
Handles are grouped **per city** (below). Run crews feed the **sports** track. Keep the
handle tables here in sync with `ig_events.py` `SEED_HANDLES`; drop a handle if it goes
quiet.

> **Sourcing focus — small local events:** the goal is small local parties / bar
> nights, so per city prioritize **LOCAL DJs who self-promote their OWN parties** on
> IG (residents posting their gig flyers) over big touring headliners just passing
> through. Locality is **per city**: e.g. **DJ Flapjack is LA-based** → an LA source,
> not an SF one; Rafer Rawb / Dr1ft / Froggin are Bay-local → SF sources.

```bash
python3 instagram/ig_events.py                       # all SEED_HANDLES
python3 instagram/ig_events.py soundmeditationpresents audiumsf   # specific handles
```

---

## San Francisco (`san-francisco`)

> **"San Francisco" = the whole Bay Area / NorCal**, not just the city. Oakland,
> Berkeley, San Jose, Fremont, Stockton, the North Bay, etc. all belong here — a DJ
> or event anywhere in the region is an SF source (that's why 19hz uses the **Bay
> Area** listing, and Oakland/Stockton DJs like Rafer Rawb, Dr1ft, Froggin live in
> this section). Only a genuinely different metro (e.g. Los Angeles) gets its own city.

**Anchor listings (browse per scan):**

| Site | URL | Use | Track | Fetch | Notes |
|------|-----|-----|-------|-------|-------|
| **19hz** | https://19hz.info/eventlisting_BayArea.php | L + **P** | Music | HTTP | **Anchor source.** Chronological, has a price column; rows link out to the ticketer. Try price here first. |
| **Resident Advisor (RA)** | https://ra.co/events/us/sanfrancisco | L + P | Music | GQL / common | Listing URL; extraction via the common RA tool (`enrich_ra.py`). |
| **EDMtrain** | https://edmtrain.com/san-francisco-ca | L | Music | HTTP / web_search | Good listing, sparse pricing. |
| **Eventbrite (SF)** | https://www.eventbrite.com/d/ca--san-francisco/ | L + P | Both | JSON-LD | SF discovery feed; price via the common `eb_demand.py` tool. |
| **Do415** | https://do415.com | L | Both | web_search | SF happenings. |
| **Funcheap SF** | https://sf.funcheap.com | L (free) | Both | HTTP | Good for free/outdoor events. |
| **SF Bike Coalition** | https://sfbike.org | L | Sports (cycling) | web_search | Group rides, Critical Mass. |

**Venues (SF):**

| Venue | URL | Use | Fetch | Notes |
|-------|-----|-----|-------|-------|
| **Halcyon** | https://halcyon-sf.com/main/tickets/ | L + P | common | SoMa club (314 11th St). Full upcoming-events + ticket listing; each event links out to its ticketer (mostly Dice). |
| **The Regency Ballroom** | https://www.theregencyballroom.com/shows | L + P | common | 1300 Van Ness. "Shows" page = upcoming calendar; links out to AXS/Ticketmaster for price. |
| **1015 Folsom** | https://1015.com/ | L + P | HTTP | SoMa mega-club (1015 Folsom St), big-room EDM/house/techno/bass. Homepage renders the full upcoming-shows calendar in plain HTML; each show links out to its ticketer (mostly RA, some Dice). |
| **The Midway** | https://themidwaysf.com/Events/ | L + P | common | Dogpatch warehouse (900 Marin St), EDM/house/techno/bass + big **day parties**. `/Events/` = upcoming calendar. **Cloudflare-gated → render via `common`**. Links out to AXS/Eventbrite/box office. |
| **Cat Club** | https://www.sfcatclub.com/ | L + P | web_search / common | SoMa club (1190 Folsom St), two floors — the SF **goth / darkwave / synth / industrial / 80s** hub (recurring nights: NIGHTSHIFT, 1984, etc.). Calendar on the site; mostly door cover (some ticketed). |

**Instagram handles (SF):**

| Handle | Who | Track | External link |
|--------|-----|-------|---------------|
| `@soundmeditationpresents` | Sound baths / sound-healing symphonies (Grace Cathedral, etc.) | Music/Immersive | linktr.ee/thesoundbath |
| `@audiumsf` | Audium Theater — 176-speaker spatial-sound immersive shows | Music/Immersive | linktr.ee/audiumsf |
| `@gracecathedral` | Grace Cathedral event series (TILT, labyrinth, concerts) | Music/Immersive | linktr.ee/gracecathedral |
| `@honey_gold_experience` | Honey Gold — immersive music/voice/video-mapping theater | Music/Immersive | honeygoldexperience.com |
| `@curious.connie` | SF gathering intel — sunset DJ sets, tea-house & waterfront pop-ups | Music | substack (curious0connie) |
| `@fromdust.sounds` | From Dust / Feels in the Club — emotional dance music DJ | Music | linktr.ee/fromdust |
| `@jlittlemusic` | Jacqueline Little Lopez — house/tech/techno DJ | Music (DJ) | linktr.ee/JLittle |
| `@modeleeloo_official` | MODE LEELOO — SF DJ / producer | Music (DJ) | soundcloud (mode leeloo) |
| `@jeffstraw_official` | Jeff Straw — SF Bay disco-house DJ (@b4aftrmusic) | Music (DJ) | jeffstraw.com |
| `@psy_matik` | Psymatik — hard dance fusion DJ (note: geo-tags Denver too — semi-touring) | Music (DJ) | linktr.ee/Psymatik |
| `@ryl3r` | Ryan Abuel (ryl3r) — DJ (SF/San Jose clubs) | Music (DJ) | posh.vip/f/5d9e8 |
| `@sethfinkin` | Seth Finkin — SF DJ (8.5k) | Music (DJ) | soundcloud (sethfinkin) — no event link; gigs in posts/stories |
| `@throttle_techno` | THROTTLE — recurring SF techno party series at 1015 Folsom | Music (techno) | no bio link; dates in flyers/posts → tickets via 1015/RA/Dice |
| `@alldayallnightevents` | All Day All Night — SF Bay music/concert promoter since 2009 (24k, @audiosf) | Music | **alldayallnightevents.com** — full parseable events list (venue + date) |
| `@fortheloudmouths` | THE LOUD MOUTHS — SF Bay collective / free pop-up **beach raves** (e.g. QUICKSAND) | Music | discord (invite) — events on **Partiful**; read posts/stories |
| `@benseagren` | Ben Seagren — SF house/techno DJ, DISTRIKT resident (@distrikt_org); Public Works SF etc. | Music (DJ) | benseagren.com/music/upcoming-events |
| `@miguelmigsmusic` | Miguel Migs — SF/Bay deep-house legend (Salted/Naked Music), 28.8k; tours nationally | Music (DJ) | gig dates in post captions; check bio link |
| `@djtajsf` | DJ Taj — SF-native DJ since '91 (1015 Folsom, Spundae) | Music (DJ) | gigs in post captions/stories (Hawthorn SF, Mars Bar SF) |
| `@djlisarose` | Lisa Rose — SF underground house DJ | Music (DJ) | gigs in post captions (e.g. The Bank SF) |
| `@raferrawb` | Rafer Rawb — Oakland hardcore DJ; promotes own Bay/North-Bay underground raves | Music (hardcore) | event details in post captions ("Legendary 90's Rave") |
| `@_dr1ft_` | Dr1ft — Bay Area hardcore/uptempo DJ; promotes NorCal raves (Stockton/SF) | Music (hardcore) | party flyers + captions |
| `@froggin_it_up` | Froggin — Oakland DJ; self-promotes own parties/events (geo-tags Oakland) | Music (hardcore/gabber) | event flyers + captions ("TIX HERE" bio link) |
| `@lyssnupmusic` | LYSSN UP — SF/Bay techno DJ/producer (Replicate Blackout); geotags Halcyon SF / San Jose (3k) | Music (techno) | gig posts |
| `@maxgardnermusic` | Max Gardner — SF techno DJ/producer (Throttle SF, Peer/Direct to Earth); Halcyon SF etc., tours intl (4.3k) | Music (techno) | gig posts/flyers |
| `@sanfranciscofnr` | NorCal motorcycle riding club (linked @familyandmotorcycles); group canyon/highway rides — moto rides go into the sports/Activity track (category `Moto`), on-topic | Sports (moto) | (bio — no link) |
| `@midnightrunnerssf` | Midnight Runners SF — bootcamp runs w/ music, Weds 6:30pm | Sports (run) | link.heylo.co/zdKT |

---

## Los Angeles (`los-angeles`)

**Anchor listings (browse per scan):**

| Site | URL | Use | Track | Fetch | Notes |
|------|-----|-----|-------|-------|-------|
| **19hz** | https://19hz.info/eventlisting_LosAngeles.php | L + **P** | Music | HTTP | **Anchor source.** Chronological, price column; rows link out to the ticketer. |
| **Resident Advisor (RA)** | https://ra.co/events/us/losangeles | L + P | Music | GQL / common | Listing URL; extraction via the common RA tool. |
| **EDMtrain** | https://edmtrain.com/los-angeles-ca | L | Music | HTTP / web_search | Listing, sparse pricing. |
| **Eventbrite (LA)** | https://www.eventbrite.com/d/ca--los-angeles/ | L + P | Both | JSON-LD | LA discovery feed; price via `eb_demand.py`. |
| **Funcheap LA** | https://losangeles.funcheap.com | L (free) | Both | HTTP | Free/outdoor events. |

**Big promoters (LA)** — the recurring organizers on the 19hz LA listing, ranked by
how often they appear + IG-verified as big (follower count). Each **site-verified**
as actually running LA events (19hz "LA" spans SoCal, so San Diego promoters were
split out into their own section below). Browse their site/link for the calendar;
each event links out to its ticketer for price.

| Promoter | Instagram | Website / link | Notes (site-verified LA) |
|----------|-----------|----------------|-------|
| **Insomniac Events** | @insomniacevents (942k) | https://insomniac.com | ✅ LA — HARD Summer, Lost In Dreams, Factory 93/Day Trip (also national). |
| **Brownies & Lemonade** | @browniesandlemonade (201k) | https://linktr.ee/browniesandlemonade | ✅ LA-based — Shrine/The Roxy/warehouse parties (+ national takeovers). |
| **Goldenvoice** | @goldenvoice (149k) | https://goldenvoice.com | ✅ LA — Greek Theatre, The Novo, El Rey, Shrine, Roxy (AEG's LA arm). |
| **Restless Nites** | @restlessnites (29k) | https://restlessnites.com | ✅ LA — LA nightlife guide/ticketing (LA city selector). |
| **Minimal Effort** | @minimaleffortla (21k) | https://linktr.ee/underratedpresents | ✅ LA — Underrated Presents, 📍Los Angeles (Arts District, warehouse techno). |
| **Subtract Music** | @subtractmusic (13k) | https://linktr.ee/subtractmusic | ✅ LA metro — "Subtract On The Pier" + Love Long Beach Festival (**Long Beach**). |
| **This Ain't Bristol** | @thisaintbristol (13k) | https://linktr.ee/thisaintbristol | LA-associated bass/house label+party (link is music-heavy; confirm venues at scan). |
| **Azure Day Party SoCal** | @azuredaypartysocal (7k) | https://azuredaypartysocal.com | ⚠️ **Orange County** — all events @ The Bungalow, **Huntington Beach** (greater-LA-ish, not LA proper). |

**Venues (LA):** _(TBD — add as they surface, e.g. via 19hz/RA listings.)_

**Instagram handles (LA):**

| Handle | Who | Track | External link |
|--------|-----|-------|---------------|
| `@flapjackthekandikid` | DJ Flapjack — LA-based hardcore/kandi DJ (27k); heavy US/EU festival + rave touring (EDC, Burning Man) and LA renegade scene | Music (hardcore) | gig announcements in post captions (multi-date tour graphics); no single event link |
| `@climaxevents.la` | Climax Events LA — LA warehouse/renegade rave promoter, "2 events every weekend" (21.5k) | Music (rave) | tickets via bio link (+ SMS "text CLIMAX to (833)595-0508"); event flyers in posts/stories |
| `@cyboy_` | CYBOY — TECHNOPUNK LA DJ; co-founds Malfunction.la / Blind Tiger.la parties (7.5k) | Music (techno) | posts own flyers + stories |
| `@ruukachan` | DJ RURU (Ruuka) — LA hard-techno DJ (6k) | Music (hard techno) | gig flyers + stories |
| `@andrewleedj` | Andrew Lee / HARDWERQ — LA house DJ; owns LA Raves / Rave Hard / MadHouse (4.2k) | Music (house/rave) | event flyers in posts |
| `@ginakuhn` | Gina Kuhn — LA DJ, Machine Club (Club Teegee) resident (3.5k) | Music (DJ) | posts her nights + stories |
| `@staticproductions.llc` | Static — LA-based rave DJ/production (3.1k) | Music (rave) | gig/flyer posts |
| `@bigmixmike` | Big Mix Mike — LA DJ; weekly **Reggae Love Sundays** residency @ Club Tee Gee (2.9k) | Music (reggae/dj) | posts residency + gigs |
| `@iambombsqvad` | BOMB-E — LA acid-techno DJ (8.4k); all-LA gigs (Skid Row/DTLA) | Music (acid techno) | LA gig posts + stories |
| `@itspinkstiletto` | Pink Stiletto — LA DJ (Catch One etc.), also tours (5.6k) | Music (dj) | gig flyers |
| `@vonwolfenheiser.ox` | Annika Wolfe — LA techno artist, Akela Recordings (6k) | Music (techno) | releases + gigs/stories |
| `@rawvictoria` | Victoria Rawlins — LA DJ/artist + radio host (Psychic Bassline, SiriusXM) (10k) | Music (dj) | gigs |

**Run/cycle crews (LA):** _(TBD — LA run/cycle clubs for the sports track.)_

---

## San Diego (documented, NOT an active city yet)

> **Reference section only — there is no `san-diego` city in the generator yet.**
> These surfaced on the 19hz "Los Angeles" listing (which spans all SoCal) but are
> genuinely **San Diego**, so they're split out here rather than mislabeled as LA.
> RA agrees SD is its own region (`ra.co/events/us/sandiego`, area 309 — separate
> from LA area 23). **Parked** until/if a San Diego city is added — do NOT scout
> these into LA/SF (their events have no city home yet), so they're kept OUT of
> `ig_events.py` `SEED_HANDLES` for now.

| Promoter | Instagram | Website / link | Notes |
|----------|-----------|----------------|-------|
| **FNGRS CRSSD** | @fngrscrssd (79k) | https://fngrscrssd.com | CRSSD Festival @ Waterfront Park + Proper; house/techno — all San Diego. |
| **LED Presents** | @ledpresents (74k) | https://ledpresents.com | Big-room EDM/bass; calendar is SD venues (Spin/EQ/Quartyard/Gallagher Sq). |

---

> Keep this file current: when a site changes, dies, or a new ticketer/handle shows
> up, update the right section. It is the authoritative list everything else cites,
> and its handle tables mirror `ig_events.py` `SEED_HANDLES`.
