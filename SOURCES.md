# Party Scout — sources master list

**Single source of truth** for the sites we pull **event listings** and **ticket
prices** from. Read this list from here — it lives in the `party-scout-fs` repo
(alongside the generated weekly data + the Pages site). The generator
(`party-scout-code`) and the scan spec (`party/README.md`) point here rather than
keeping their own copy.

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
| **See Tickets / Posh / Etix** | various | P | Music | common | Misc ticketers the 19hz/RA rows link to. |
| **Do415** | https://do415.com | L | Both | web_search | SF happenings. |
| **Funcheap** | https://sf.funcheap.com | L (free) | Both | HTTP | Good for free/outdoor events. |
| **Meetup** | https://www.meetup.com | L + P | Sports | web_search / common | Rides/runs/club meets; default **Free** unless a fee is shown. |
| **SF Bike Coalition** | https://sfbike.org | L | Sports (cycling) | web_search | Group rides, Critical Mass. |
| **RunGuides / RunningInTheUSA** | https://runguides.com · https://runningintheusa.com | L | Sports (running) | web_search | Race calendars. |
| **Strava clubs** | https://www.strava.com/clubs | L | Sports | web_search | Local moto/cycling/run clubs. |

**Price-source order** (cheapest → heaviest): **19hz column → RA GraphQL → Eventbrite
JSON-LD → `common`-session render** (Tixr/AXS/RA-HTML/venue). Free/outdoor/park → `Free`;
leave blank only if genuinely unobtainable — never guess a number.

> Keep this table current: when a site changes, dies, or a new ticketer shows up in
> the listings, update this file. It is the authoritative list everything else cites.
