#!/usr/bin/env python3
"""Fail when a week in data/ has no prerendered pages.

Shared event links (`https://party-scout.app/<city>/<week>/<eid>/`) are what
link-preview bots (Telegram, Instagram, iMessage, Slack, Facebook) and crawlers
fetch. They run no JS, so a missing static file is an HTTP 404 and a preview
that reads "Page not found | Party Scout" — `404.html` hands off to the SPA only
in a browser. From 2026-08 nothing generated these files and nobody noticed for
three months: the `san-francisco/` tree stopped at `2026-08-03`
(party-scout-service#182, party-scout-fs#34).

The service's event-store flush now writes them here. This gate checks the
tree it leaves behind, for every `data/<city>/<week>.json`:

  - `<city>/<week>/index.html` must exist, for every week, past ones included;
  - while the week is current or upcoming (its end, `week + 6 days`, is today
    or later in Pacific time), every published card — `enriched >= 1`
    (int-coerced; missing or null counts as 0) with an `eid` that is a valid
    slug — must have `<city>/<week>/<eid>/index.html`.

Past weeks are not held to the per-event pages: the flush renders current and
upcoming weeks first, and a rolled-off week's index is what its links fall
back to.

Usage:
    tools/check_static_pages.py [--root <dir>] [--today YYYY-MM-DD]

`--root` defaults to the repository root; `--today` defaults to today in
America/Los_Angeles and exists for the self-test.
"""

import argparse
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WEEK_FILE = re.compile(r"^data/([a-z0-9][a-z0-9-]*)/(\d{4}-\d{2}-\d{2})\.json$")
EID = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")

# How many missing paths to list before summing up the rest.
SHOW = 50


def pacific_today():
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Los_Angeles")
    except Exception:  # no tz database on this machine
        # PST, the earlier of the two offsets: at worst "today" lags by an hour
        # in summer, which only keeps a just-ended week on the strict side.
        tz = datetime.timezone(datetime.timedelta(hours=-8))
    return datetime.datetime.now(tz).date()


def enriched(card):
    try:
        return int(card.get("enriched") or 0)
    except (TypeError, ValueError):
        return 0


def published_eids(path):
    """The slugs of every published card in a week file, in file order.

    Raises ValueError when the file will not parse; checking that is
    scripts/validate_data.py's job, so the caller warns rather than fails.
    """
    with open(path, encoding="utf-8") as fh:
        try:
            week = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"not valid JSON: {exc}") from exc
    if not isinstance(week, dict) or not isinstance(week.get("tracks"), dict):
        raise ValueError("has no `tracks` object")
    out = []
    for listing in week["tracks"].values():
        if not isinstance(listing, list):
            continue
        for card in listing:
            if not isinstance(card, dict) or enriched(card) < 1:
                continue
            eid = card.get("eid")
            if isinstance(eid, str) and EID.match(eid) and eid not in out:
                out.append(eid)
    return out


def week_files(root):
    data = os.path.join(root, "data")
    if not os.path.isdir(data):
        return []
    out = []
    for city in sorted(os.listdir(data)):
        if not os.path.isdir(os.path.join(data, city)):
            continue
        for name in sorted(os.listdir(os.path.join(data, city))):
            m = WEEK_FILE.match(f"data/{city}/{name}")
            if m:
                out.append((m.group(1), m.group(2)))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=ROOT, help="tree to check (default: repo root)")
    parser.add_argument(
        "--today",
        type=datetime.date.fromisoformat,
        help="the date to judge current weeks by (default: today, Pacific)",
    )
    args = parser.parse_args()
    root = args.root
    today = args.today or pacific_today()

    weeks = week_files(root)
    if not weeks:
        print(f"no data/<city>/<week>.json under {root} — nothing to check")
        return 0

    missing = []
    current = pages = 0
    for city, week in weeks:
        index = f"{city}/{week}/index.html"
        if not os.path.isfile(os.path.join(root, index)):
            missing.append(index)
        start = datetime.date.fromisoformat(week)
        if start + datetime.timedelta(days=6) < today:
            continue
        current += 1
        source = f"data/{city}/{week}.json"
        try:
            eids = published_eids(os.path.join(root, source))
        except ValueError as exc:
            print(f"warning: cannot read cards of {source}: {exc}", file=sys.stderr)
            continue
        for eid in eids:
            pages += 1
            page = f"{city}/{week}/{eid}/index.html"
            if not os.path.isfile(os.path.join(root, page)):
                missing.append(page)

    summary = (
        f"{len(weeks)} week file(s), {current} current or upcoming as of {today}"
        f" with {pages} published card(s)"
    )
    if not missing:
        print(f"ok: {summary}; every prerendered page is present")
        return 0

    print(f"{len(missing)} prerendered page(s) missing ({summary}):")
    for path in missing[:SHOW]:
        print(f"  {path}")
    if len(missing) > SHOW:
        print(f"  … and {len(missing) - SHOW} more")
    print(
        "\nLink-preview bots and crawlers run no JS: each path above answers 404"
        "\nand previews as \"Page not found\". party-scout-service's event-store"
        "\nflush renders them (party-scout-service#182) — a week touched by a flush"
        "\ngets its pages in the same commit or a `pages: …` one, at most"
        "\nFS_PAGES_PER_FLUSH pages per flush, current and upcoming weeks first."
        "\nIf this stays red across flushes, that generator has stopped."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
