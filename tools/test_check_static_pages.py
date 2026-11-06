#!/usr/bin/env python3
"""Self-test for tools/check_static_pages.py.

Each case builds a synthetic site tree — week files under data/ plus whatever
pages it should or should not have — and asserts the checker's verdict with
`today` pinned. Without this the gate could stop firing, and a gate that
stopped firing reads as green just like a complete site does.

Run: python3 tools/test_check_static_pages.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(ROOT, "tools", "check_static_pages.py")

TODAY = "2026-11-06"  # a Friday: week 2026-11-02 is current, 2026-10-26 ended
PAST, CURRENT, UPCOMING = "2026-10-26", "2026-11-02", "2026-11-09"


def card(eid, enriched=1, **extra):
    out = {"eid": eid, "name": eid, **extra}
    if enriched is not ...:
        out["enriched"] = enriched
    return out


CARDS = [card("bare-maximum-4091"), card("dreamstate-socal-2026-cbbd", enriched=3)]

# Cards that get no page: not published, or no usable slug.
UNPUBLISHED = [
    card("draft-0", enriched=0),
    card("draft-null", enriched=None),
    card("draft-missing", enriched=...),
    card("draft-text", enriched="nope"),
    card("Bad Slug!", enriched=2),
    card(None, enriched=2),
]


def week(cards):
    return {"week_start": "", "tracks": {"music": list(cards)}}


def build(tmp, name, weeks, pages):
    """`weeks`: {(city, week): cards}; `pages`: paths of index.html to create."""
    root = os.path.join(tmp, name)
    for (city, start), cards in weeks.items():
        path = os.path.join(root, "data", city, f"{start}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(week(cards), fh)
    # Files under data/ that are not week files and must be ignored.
    os.makedirs(os.path.join(root, "data", "san-francisco"), exist_ok=True)
    for extra in ("index.json", "2026-11-02.md", "tmpz3z50fx8.tmp"):
        with open(os.path.join(root, "data", "san-francisco", extra), "w") as fh:
            fh.write("{}")
    for page in pages:
        path = os.path.join(root, page)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("<!doctype html>")
    return root


def complete(weeks):
    """Every page the gate wants for `weeks`, past weeks' event pages excluded."""
    out = []
    for (city, start), cards in weeks.items():
        out.append(f"{city}/{start}/index.html")
        if start != PAST:
            out += [f"{city}/{start}/{c['eid']}/index.html" for c in cards[:2]]
    return out


WEEKS = {
    ("san-francisco", PAST): CARDS,
    ("san-francisco", CURRENT): CARDS + UNPUBLISHED,
    ("los-angeles", UPCOMING): CARDS,
}
FULL = complete(WEEKS)

MANY = {("san-francisco", CURRENT): [card(f"ev-{i:03d}") for i in range(60)]}

# Each case: (name, weeks, pages, expected exit, substrings expected in output,
# substrings that must NOT be in it).
CASES = [
    (
        "a complete tree passes",
        WEEKS,
        FULL,
        0,
        ["ok: 3 week file(s), 2 current or upcoming", "4 published card(s)"],
        [],
    ),
    (
        "a week with no index.html fails, past weeks included",
        WEEKS,
        [p for p in FULL if p != f"san-francisco/{PAST}/index.html"],
        1,
        ["1 prerendered page(s) missing", f"san-francisco/{PAST}/index.html"],
        [],
    ),
    (
        "a published card of an upcoming week with no page fails",
        WEEKS,
        [p for p in FULL if "los-angeles" not in p or p.count("/") == 2],
        1,
        [
            "2 prerendered page(s) missing",
            f"los-angeles/{UPCOMING}/bare-maximum-4091/index.html",
            f"los-angeles/{UPCOMING}/dreamstate-socal-2026-cbbd/index.html",
        ],
        [f"los-angeles/{UPCOMING}/index.html"],
    ),
    (
        "no pages at all: weeks and current cards listed, past cards not",
        WEEKS,
        [],
        1,
        ["7 prerendered page(s) missing", f"san-francisco/{CURRENT}/bare-maximum-4091/"],
        [f"san-francisco/{PAST}/bare-maximum-4091", "draft-", "Bad Slug"],
    ),
    (
        "the list stops at 50 and counts the rest",
        MANY,
        [],
        1,
        ["61 prerendered page(s) missing", "ev-048/index.html", "… and 11 more"],
        ["ev-049/index.html"],
    ),
]


def check(root, today=TODAY):
    return subprocess.run(
        [sys.executable, CHECKER, "--root", root, "--today", today],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main():
    failures = []
    print("check_static_pages self-test\n")
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, weeks, pages, want_code, wanted, unwanted) in enumerate(CASES):
            result = check(build(tmp, f"case{i}", weeks, pages))
            missing = [w for w in wanted if w not in result.stdout]
            present = [u for u in unwanted if u in result.stdout]
            if result.returncode != want_code or missing or present:
                failures.append(
                    f"{name}: exit={result.returncode} (want {want_code}) "
                    f"missing={missing} unexpected={present}\n{result.stdout}"
                )
                print(f"  FAIL {name}")
            else:
                print(f"  ok   {name}")

    print()
    if failures:
        for failure in failures:
            print(failure)
        print(f"{len(failures)}/{len(CASES)} case(s) FAILED")
        return 1
    print(f"{len(CASES)}/{len(CASES)} case(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
