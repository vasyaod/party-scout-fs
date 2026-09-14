#!/usr/bin/env python3
"""Retire the `source_url` / `link` / `error` fields from data/ (issue #10).

`sources` replaced the single `link` field (MODEL.md:142); `source_url` and
`error` were never in MODEL.md at all, so `scripts/validate_data.py` counts
all three as `event-unknown-field`. This folds the URL those fields carry
into the event's own `sources` list and drops the keys, putting the files
back on the documented schema without losing a link.

What is *not* folded, and why: REQUIREMENTS.md rule 11 forbids storing a
third-party scrape index in `sources` — "it just points back at our own
pipeline. Resolve the event's real page instead, or leave `sources` empty".
So a value that is exactly the URL of a source registered in
`data/sources.json` under kind `anchor` or `directory` is dropped rather
than folded. The match is on the whole URL, not the host: `ra.co` hosts a
registered anchor listing (`ra-san-francisco`) *and* the per-event pages
that are a legitimate `sources[0]`, and only the former is an index.

Each file is rewritten with the JSON formatting it already uses — indent,
`\\uXXXX` escaping and the trailing newline all vary file to file — and a
file whose current bytes cannot be reproduced is left alone, so the diff
stays confined to the events that actually change.

Run:
    python3 tools/fold_legacy_link_fields.py --dry-run
    python3 tools/fold_legacy_link_fields.py
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# Retired field -> its value is a URL that belongs in `sources`.
URL_FIELDS = ("source_url", "link")
# Never part of the model, and carries nothing a reader can use: the two
# occurrences are enrichment diagnostics ("tixr.com 403 (Cloudflare-gated…)").
DROP_FIELDS = ("error",)
# data/sources.json kinds that are a multi-venue index in rule 11's sense.
INDEX_KINDS = ("anchor", "directory")


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT)


def norm(url: str) -> str:
    """A URL reduced for comparison — no scheme, no `www.`, no trailing slash."""
    parts = urlparse(url.strip().lower())
    host = parts.netloc[4:] if parts.netloc.startswith("www.") else parts.netloc
    tail = f"?{parts.query}" if parts.query else ""
    return f"{host}{parts.path.rstrip('/')}{tail}"


def scrape_indexes() -> set:
    """The registered listing indexes, per rule 11 — keyed by `norm`."""
    with open(os.path.join(DATA, "sources.json"), encoding="utf-8") as fh:
        registry = json.load(fh)
    return {
        norm(source["url"])
        for source in registry["sources"]
        if source.get("kind") in INDEX_KINDS and source.get("url")
    }


def dumps_like(doc, original: str):
    """Serialize `doc` the way `original` was written, or None if that is unclear."""
    for ensure_ascii in (False, True):
        for newline in ("", "\n"):
            as_written = json.dumps(json.loads(original), indent=2, ensure_ascii=ensure_ascii)
            if as_written + newline == original:
                return json.dumps(doc, indent=2, ensure_ascii=ensure_ascii) + newline
    return None


def fold_event(event: dict, indexes: set, where: str, log: list) -> bool:
    """Strip the retired fields off one event. Returns True when it changed."""
    changed = False

    for field in URL_FIELDS:
        if field not in event:
            continue
        value = event.pop(field)
        changed = True
        sources = event.get("sources")
        if not isinstance(value, str) or not value.strip():
            log.append(("dropped-empty", field, where, repr(value)))
        elif not isinstance(sources, list):
            # Nowhere to file the URL: refuse rather than lose it.
            log.append(("NO-SOURCES-LIST", field, where, value))
        elif norm(value) in indexes:
            log.append(("dropped-index", field, where, value))
        elif any(isinstance(s, str) and norm(s) == norm(value) for s in sources):
            log.append(("dropped-duplicate", field, where, value))
        else:
            # Appended, not prepended: `sources[0]` is the Open button
            # (rule 10) and the existing first entry keeps that slot.
            sources.append(value)
            log.append(("folded", field, where, value))

    for field in DROP_FIELDS:
        if field in event:
            log.append(("dropped-field", field, where, repr(event.pop(field))))
            changed = True

    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    parser.add_argument("--verbose", action="store_true", help="print every event touched")
    args = parser.parse_args(argv)

    indexes = scrape_indexes()
    log: list = []
    written = []

    for path in sorted(glob.glob(os.path.join(DATA, "*", "*.json"))):
        with open(path, encoding="utf-8") as fh:
            original = fh.read()
        week = json.loads(original)
        if not isinstance(week, dict) or not isinstance(week.get("tracks"), dict):
            continue  # index.json and friends

        changed = False
        for track, events in sorted(week["tracks"].items()):
            if not isinstance(events, list):
                continue
            for i, event in enumerate(events):
                if isinstance(event, dict):
                    changed |= fold_event(event, indexes, f"{rel(path)} tracks.{track}[{i}]", log)
        if not changed:
            continue

        body = dumps_like(week, original)
        if body is None:
            print(f"SKIPPED {rel(path)}: cannot reproduce its current formatting", file=sys.stderr)
            return 1
        if not args.dry_run:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
        written.append(rel(path))

    stuck = [entry for entry in log if entry[0] == "NO-SOURCES-LIST"]
    if stuck:
        for _, field, where, value in stuck:
            print(f"REFUSED {where}: {field}={value} has no `sources` list to fold into", file=sys.stderr)
        return 1

    if args.verbose:
        for action, field, where, value in log:
            print(f"  {action:18} {field:10} {where}  {value}")

    print(f"{'would touch' if args.dry_run else 'touched'} {len(written)} file(s), {len(log)} field(s):")
    for action in ("folded", "dropped-duplicate", "dropped-index", "dropped-empty", "dropped-field"):
        by_field: dict = {}
        for entry in log:
            if entry[0] == action:
                by_field[entry[1]] = by_field.get(entry[1], 0) + 1
        if by_field:
            tally = ", ".join(f"{name} {n}" for name, n in sorted(by_field.items()))
            print(f"  {action:18} {sum(by_field.values()):4d}  ({tally})")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
