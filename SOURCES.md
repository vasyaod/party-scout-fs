# Party Scout — sources master list

**Single source of truth** for the sites we pull **event listings** and **ticket
prices** from. Read this list from here — it lives in the `party-scout-fs` repo
(alongside the generated weekly data + the Pages site). The generator
(`party-scout-code`) and the scan spec (`party/README.md`) point here rather than
keeping their own copy.

**Per-city.** The table below is the **San Francisco** source set. Each city uses the
same *kinds* of sources at its own URLs — for **Los Angeles** (`los-angeles`):
19hz LA `https://19hz.info/eventlisting_LosAngeles.php` (anchor) · RA LA
`ra.co/events/us/losangeles` · EDMtrain `edmtrain.com/los-angeles-ca` · Eventbrite LA ·
Dice · Funcheap LA `losangeles.funcheap.com` (free/outdoor) · Meetup LA + LA run/cycle
clubs (sports). Same price-source order and fetch methods. Add a new city's source
URLs here when you add the city.

Legend — Use: `L` = event listing, `P` = ticket price. Fetch: `HTTP` = plain
web_fetch/HTTP, `GQL` = `ra.co/graphql`, `JSON-LD` = schema.org in the page,
`common` = remote-browser `common` session (real Chrome, passes Cloudflare/JS).

| Site | URL | Use | Track | Fetch | Notes |
|------|-----|-----|-------|-------|-------|
| **19hz** | https://19hz.info/eventlisting_BayArea.php | L + **P** | Music | HTTP | **Anchor source.** Chronological, has a price column; rows link out to the ticketer. Try price here first. |
| **Resident Advisor (RA)** | https://ra.co/events/us/sanfrancisco | L + P + flyer | Music | GQL / common | `enrich_ra.py` → `ra.co/graphql` (bare, not Cloudflare-gated): `interestedCount`/`attending` (the "rating") + the **poster** via `event.images[]` (the `FLYERFRONT` one; `filename` is a direct images.ra.co URL that downloads bare). CLI: `enrich_ra.py flyer <ra_id\|url> <out.jpg>` / `flyerurl <id>`; import `flyer_url()` / `save_flyer()`. Event HTML is Cloudflare-gated → render via `common`. |
| **EDMtrain** | https://edmtrain.com/san-francisco-ca | L | Music | HTTP / web_search | Good listing, sparse pricing. |
| **Eventbrite** | https://www.eventbrite.com/d/ca--san-francisco/ | L + P | Both | JSON-LD | `eb_demand.py`: `offers.lowPrice/highPrice` + SoldOut/salesStatus. |
| **Dice** | https://dice.fm | L + P | Music | common | Price in JS app. |
| **Tixr** | https://www.tixr.com | P + flyer | Music | ephemeral RBS | `tixr.py`: one ephemeral remote-browser fetch (real Chrome passes **DataDome**), then reads the page's schema.org **JSON-LD** in one shot → flyer (`static.tixr.com` image, downloads bare) + **all price tiers** + venue/time/age. `event_info(url)` → `{image, offers[], price_low/high, price, address, time, …}`; `save_flyer(img_or_url, out)` fits ≤512px JPEG. price_low/high exclude add-ons (parking/coat/etc). |
| **AXS / Ticketmaster / venue box office** | e.g. https://thefoxoakland.com | P | Music | common | Price sits in a Buy-Tickets **widget/iframe** — open/expand it, don't just scrape body. |
| **Halcyon (venue)** | https://halcyon-sf.com/main/tickets/ | L + P | Music | common | SoMa club (314 11th St). Full upcoming-events + ticket listing; each event links out to its ticketer (mostly Dice). |
| **The Regency Ballroom (venue)** | https://www.theregencyballroom.com/shows | L + P | Music | common | 1300 Van Ness. "Shows" page = upcoming-events calendar; events link out to AXS/Ticketmaster for price. |
| **1015 Folsom (venue)** | https://1015.com/ | L + P | Music | HTTP | SoMa mega-club (1015 Folsom St), big-room EDM/house/techno/bass. **Homepage renders the full upcoming-shows calendar in plain HTML** (date + artist); each show links out to its ticketer (**mostly RA/ra.co**, some Dice) for tickets/price. |
| **The Midway (venue)** | https://themidwaysf.com/Events/ | L + P | Music | common | Dogpatch/Central Waterfront warehouse venue (900 Marin St), EDM/house/techno/bass + big **day parties**. `/Events/` = upcoming-events calendar. **Cloudflare-gated → render via `common`** (plain HTTP 403s). Events link out to **AXS / Eventbrite / venue box office** for price. |
| **See Tickets / Posh / Etix** | various | P | Music | common | Misc ticketers the 19hz/RA rows link to. |
| **Do415** | https://do415.com | L | Both | web_search | SF happenings. |
| **Funcheap** | https://sf.funcheap.com | L (free) | Both | HTTP | Good for free/outdoor events. |
| **Meetup** | https://www.meetup.com | L + P | Sports | web_search / common | Rides/runs/club meets; default **Free** unless a fee is shown. |
| **SF Bike Coalition** | https://sfbike.org | L | Sports (cycling) | web_search | Group rides, Critical Mass. |
| **RunGuides / RunningInTheUSA** | https://runguides.com · https://runningintheusa.com | L | Sports (running) | web_search | Race calendars. |
| **Strava clubs** | https://www.strava.com/clubs | L | Sports | web_search | Local moto/cycling/run clubs. |
| **Instagram organizers** | (handle list below) | L | Music / Immersive | `ig` | `instagram/ig_events.py` → bio + external link per handle (post feed is empty now). Events live on the linked linktr.ee/site → fetch + AI-parse. See handle list below. |

**Excluded (do NOT scan / add as a source):**
- **Stern Grove Festival** (`sterngrove.org`) — an **annual, once-a-year festival series**, not the recurring nightlife/party scene Party Scout tracks. Don't list it as a source or auto-add its concerts. (Any Stern Grove events already in the DB stay; just don't scan the site for more.)

**Price-source order** (cheapest → heaviest): **19hz column → RA GraphQL → Eventbrite
JSON-LD → `common`-session render** (Tixr/AXS/RA-HTML/venue). Free/outdoor/park → `Free`;
leave blank only if genuinely unobtainable — never guess a number.

## Instagram organizer handles (parse periodically)

> ✅ **RE-ENABLED (2026-07-02, owner go-ahead).** The Instagram scout is back on for
> discovery. Run `instagram/ig_events.py` again, but follow **every** rule in
> `instagram/README.md` (human-emulation: UI/mouse only for interactive actions, no URL
> jumps, Search-bar nav, slow moves, typed pauses, feed breaks; private-API reads are
> fine). Paused 06-25 for account safety; owner accepted the risk with "follow all the rules."

Curated SF event organizers, **DJs, and run crews** we **periodically parse from
Instagram** each scan, via `instagram/ig_events.py` (uses the authenticated
`instagram` session). IG's post feed comes back empty, so the chain is: **handle →
profile (bio + external link) → fetch that linktr.ee/site → AI-parse the events**
(date, venue, price, ticket link). Two lanes the 19hz/RA listings miss: immersive /
sound-bath / experiential organizers, and **DJs/promoters** — who play and promote
parties, often putting their **next gig date right in the bio text** (e.g. "6/26
@halcyon_sf"), so read the bio gig line + external link, not just the linktree. Run
crews feed the **sports** track.

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
| `@psy_matik` | Psymatik — hard dance fusion DJ | Music (DJ) | linktr.ee/Psymatik |
| `@ryl3r` | Ryan Abuel (ryl3r) — DJ (SF/San Jose clubs) | Music (DJ) | posh.vip/f/5d9e8 |
| `@sethfinkin` | Seth Finkin — SF DJ (8.5k) | Music (DJ) | soundcloud (sethfinkin) — no event link; gigs in posts/stories |
| `@throttle_techno` | THROTTLE — recurring SF techno party series at 1015 Folsom | Music (techno) | no bio link; dates in flyers/posts → tickets via 1015/RA/Dice |
| `@alldayallnightevents` | All Day All Night — SF Bay music/concert promoter since 2009 (24k, @audiosf); open-airs + club shows | Music | **alldayallnightevents.com** — full parseable events list (venue + date) |
| `@fortheloudmouths` | THE LOUD MOUTHS — SF Bay artist collective / free pop-up **beach raves** (e.g. QUICKSAND) | Music | discord (invite) — events on **Partiful**, not the link; read posts/stories |
| `@benseagren` | Ben Seagren — SF house/techno DJ, co-founder & resident of **DISTRIKT** (@distrikt_org); plays Public Works SF etc. Personal handle ~2.5k (bigger reach lives under DISTRIKT) | Music (DJ) | benseagren.com/music/upcoming-events — upcoming-events page (parse); gig dates also in post captions |
| `@miguelmigsmusic` | Miguel Migs — SF/Bay deep-house legend (Salted/Naked Music), 28.8k; tours nationally so not every gig is SF | Music (DJ) | gig dates in post captions (e.g. Quartyard SD, It'll Do Dallas); check bio link |
| `@djtajsf` | DJ Taj — SF-native DJ since '91 (1015 Folsom, Spundae) | Music (DJ) | gigs in post captions/stories (e.g. Hawthorn SF, Mars Bar SF) |
| `@djlisarose` | Lisa Rose — SF underground house DJ | Music (DJ) | gigs in post captions (e.g. The Bank SF) |
| `@sanfranciscofnr` | SFFNR — SF Friday Night Run, last Friday monthly since 2006 | Sports (run) | (bio — no link) |
| `@midnightrunnerssf` | Midnight Runners SF — bootcamp runs w/ music, Weds 6:30pm | Sports (run) | link.heylo.co/zdKT |
| `@raferrawb` | Rafer Rawb — Oakland hardcore DJ; promotes own Bay/North-Bay underground raves | Music (hardcore) | event details in post captions (e.g. "Legendary 90's Rave") |
| `@_dr1ft_` | Dr1ft — Bay Area hardcore/uptempo DJ; promotes NorCal raves (Stockton/SF) | Music (hardcore) | party flyers + captions |
| `@froggin_it_up` | Froggin — Oakland DJ; self-promotes own parties/events (geo-tags Oakland) | Music (hardcore/gabber) | event flyers + captions ("TIX HERE" bio link) |

> **Sourcing focus — small local events:** the goal is small local parties / bar
> nights, so prioritize **LOCAL DJs who self-promote their OWN parties** on IG
> (Bay Area residents posting their gig flyers) over big touring headliners (who
> pass through but don't run local nights). E.g. keep Rafer Rawb / Dr1ft / Froggin
> (local, self-promoting); a national act like DJ Flapjack is not a useful source.

```bash
python3 instagram/ig_events.py                       # all SEED_HANDLES
python3 instagram/ig_events.py soundmeditationpresents audiumsf   # specific handles
```

> Extend this list as new organizers surface (and mirror them into `ig_events.py`
> `SEED_HANDLES`). Drop a handle if it goes quiet / stops posting datable events.

> Keep this table current: when a site changes, dies, or a new ticketer shows up in
> the listings, update this file. It is the authoritative list everything else cites.
