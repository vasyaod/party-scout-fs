# REQUIREMENTS.md — rules the data and site must follow

The agreed rules for the Party Scout weekly database and site. Anything that
generates or edits the data must honor these. (Field shapes live in
[MODEL.md](MODEL.md); where data comes from lives in [SOURCES.md](SOURCES.md).)

## Data integrity

1. **Verify every event.** Each event must tie to a concrete source (ticket /
   listing / venue page). If it can't be verified, **drop it** — never keep vague,
   unsourced entries. (This is what caught and removed "Pride Rooftop Party
   (daytime)".)
2. **Never guess.** Leave a field `""` rather than inventing a value (price,
   venue, address, URL).
3. **Weeks are Monday-dated.** A week file/`week_start` is the Monday of the week
   the event window falls in.

## Volume

4. **Resolve up to 40 events per track** (music/EDM and sports/active) each week —
   gather and verify as many real in-window events as exist, capped at 40. Fewer is
   fine when the weekend is thin; never pad to hit the number.

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

8. **No raw URLs as text.** `link`, `tickets`, `maps` live in the JSON and are
   surfaced only as buttons / the `open map` link — never printed as URL text, in
   the site or the Markdown digest.
9. **Buy ticket → the real seller only.** `tickets` points at the actual ticketer
   (RA / Tixr / Eventbrite / Etix / Ticketmaster / AXS / venue). **Never** a search
   engine. No real seller → no Buy-ticket button.
10. **Open → the event website** (`link`): event info/lineup page.
11. **Map per device.** The 📍 location's `open map` link opens **Apple Maps on
    iOS/iPadOS/macOS, Google Maps elsewhere**, using the per-event `address` for a
    precise pin when known.
12. **Price on the button.** Price is combined into the Buy-ticket button
    (`$NN · Buy ticket`); `Free` is a gold, same-size, non-clickable button.
13. **Aligned cards.** In a row, tags and the action button line up across cards
    (footer pinned to the bottom; an empty action row is reserved when a card has
    no button).

## Generation

14. Data is **generated**, not hand-edited. The generator + reusable enrichment
    (RA ratings, per-event research) live in `party-scout-code`. Read SOURCES.md,
    MODEL.md, and this file before changing the data.

## Enrichment (AI / subagents)

15. **Resolve fields intelligently with AI subagents.** Don't ship whatever the raw
    scan emits — fan out per-event research agents (parallel) to verify each event is
    real and resolve its fields (venue, exact address, price, ticket URL, event
    website, tags, RA rating). New events and any sparse/unverified ones get this
    pass; unverifiable events are dropped (rule 1). This is how the data reaches the
    quality the rest of these rules assume.
