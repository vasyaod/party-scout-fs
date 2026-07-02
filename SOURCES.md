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
| **Resident Advisor (RA)** | https://ra.co/events/us/sanfrancisco | L + P | Music | GQL / common | `ra_interest.py` → `ra.co/graphql`: `interestedCount` + `tickets[].priceRetail` (price only when RA sells the tickets). HTML is Cloudflare-gated → render via `common`. |
| **EDMtrain** | https://edmtrain.com/san-francisco-ca | L | Music | HTTP / web_search | Good listing, sparse pricing. |
| **Eventbrite** | https://www.eventbrite.com/d/ca--san-francisco/ | L + P | Both | JSON-LD | `eb_demand.py`: `offers.lowPrice/highPrice` + SoldOut/salesStatus. |
| **Dice** | https://dice.fm | L + P | Music | common | Price in JS app. |
| **Tixr** | https://www.tixr.com | P | Music | common | Tiered prices; JS-rendered. |
| **AXS / Ticketmaster / venue box office** | e.g. https://thefoxoakland.com | P | Music | common | Price sits in a Buy-Tickets **widget/iframe** — open/expand it, don't just scrape body. |
| **Halcyon (venue)** | https://halcyon-sf.com/main/tickets/ | L + P | Music | common | SoMa club (314 11th St). Full upcoming-events + ticket listing; each event links out to its ticketer (mostly Dice). |
| **The Regency Ballroom (venue)** | https://www.theregencyballroom.com/shows | L + P | Music | common | 1300 Van Ness. "Shows" page = upcoming-events calendar; events link out to AXS/Ticketmaster for price. |
| **See Tickets / Posh / Etix** | various | P | Music | common | Misc ticketers the 19hz/RA rows link to. |
| **Do415** | https://do415.com | L | Both | web_search | SF happenings. |
| **Funcheap** | https://sf.funcheap.com | L (free) | Both | HTTP | Good for free/outdoor events. |
| **Meetup** | https://www.meetup.com | L + P | Sports | web_search / common | Rides/runs/club meets; default **Free** unless a fee is shown. |
| **SF Bike Coalition** | https://sfbike.org | L | Sports (cycling) | web_search | Group rides, Critical Mass. |
| **RunGuides / RunningInTheUSA** | https://runguides.com · https://runningintheusa.com | L | Sports (running) | web_search | Race calendars. |
| **Strava clubs** | https://www.strava.com/clubs | L | Sports | web_search | Local moto/cycling/run clubs. |
| **Instagram organizers** | (handle list below) | L | Music / Immersive | `ig` | `instagram/ig_events.py` → bio + external link per handle (post feed is empty now). Events live on the linked linktr.ee/site → fetch + AI-parse. See handle list below. |

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
| `@fortheloudmouths` | THE LOUD MOUTHS — SF Bay artist collective / free pop-up **beach raves** (e.g. QUICKSAND) | Music | discord (invite) — events on **Partiful**, not the link; read posts/stories |
| `@sanfranciscofnr` | SFFNR — SF Friday Night Run, last Friday monthly since 2006 | Sports (run) | (bio — no link) |
| `@midnightrunnerssf` | Midnight Runners SF — bootcamp runs w/ music, Weds 6:30pm | Sports (run) | link.heylo.co/zdKT |

```bash
python3 instagram/ig_events.py                       # all SEED_HANDLES
python3 instagram/ig_events.py soundmeditationpresents audiumsf   # specific handles
```

> Extend this list as new organizers surface (and mirror them into `ig_events.py`
> `SEED_HANDLES`). Drop a handle if it goes quiet / stops posting datable events.

> Keep this table current: when a site changes, dies, or a new ticketer shows up in
> the listings, update this file. It is the authoritative list everything else cites.
