#!/usr/bin/env python3
"""Self-test for scripts/validate_data.py.

Each case copies data/ to a scratch tree, breaks it in exactly one way, and
asserts the validator reports the expected check code and exits non-zero.
Without this, a check that silently stops firing would look like clean data.

Run: python3 scripts/test_validate_data.py
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")


def read(root, *parts):
    with open(os.path.join(root, "data", *parts), encoding="utf-8") as fh:
        return json.load(fh)


def write(root, doc, *parts):
    with open(os.path.join(root, "data", *parts), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False)


CITY = "san-francisco"
WEEK = "2026-08-17.json"


def first_event(week):
    return week["tracks"]["music"][0]


def day_before(window):
    """The day before a `YYYY-MM-DD..YYYY-MM-DD` window opens."""
    start = datetime.date.fromisoformat(window.split("..")[0])
    return (start - datetime.timedelta(days=1)).isoformat()


# (expected check code, mutation) — the mutation gets the scratch repo root.
def _week(fn):
    def apply(root):
        week = read(root, CITY, WEEK)
        fn(week)
        write(root, week, CITY, WEEK)

    return apply


def _index(fn):
    def apply(root):
        index = read(root, CITY, "index.json")
        fn(index)
        write(root, index, CITY, "index.json")

    return apply


def _stats(fn):
    def apply(root):
        stats = read(root, "stats.json")
        fn(stats)
        write(root, stats, "stats.json")

    return apply


def _cities(fn):
    def apply(root):
        doc = read(root, "cities.json")
        fn(doc)
        write(root, doc, "cities.json")

    return apply


def _truncate(root):
    with open(os.path.join(root, "data", CITY, WEEK), "a", encoding="utf-8") as fh:
        fh.write("}}}")


def _new_partition(root):
    os.mkdir(os.path.join(root, "data", "atlantis"))


def _copy_week_as(stem):
    """Drop an extra week file under a different (bad) week_start."""

    def apply(root):
        week = read(root, CITY, WEEK)
        week["week_start"] = stem
        write(root, week, CITY, f"{stem}.json")

    return apply


CASES = [
    ("json-parse", _truncate),
    ("cities-unlisted-partition", _new_partition),
    ("cities-missing-partition", _cities(lambda d: d["cities"].append({"slug": "atlantis", "label": "Atlantis"}))),
    ("cities-shape", _cities(lambda d: d.__setitem__("cities", [{"slug": "x"}]))),
    ("week-missing-field", _week(lambda w: w.pop("title"))),
    ("week-field-type", _week(lambda w: w.__setitem__("title", 5))),
    ("week-filename-mismatch", _week(lambda w: w.__setitem__("week_start", "2026-08-10"))),
    ("week-start-not-monday", _copy_week_as("2026-08-18")),  # a Tuesday
    ("week-start-format", _copy_week_as("2026-02-30")),  # matches the regex, not a real day
    ("week-window-format", _week(lambda w: w.__setitem__("window", "next weekend"))),
    ("week-window-format", _week(lambda w: w.__setitem__("window", "2026-02-30..2026-08-23"))),
    ("week-window-outside-week", _week(lambda w: w.__setitem__("window", "2026-08-30..2026-08-31"))),
    ("week-window-reversed", _week(lambda w: w.__setitem__("window", "2026-08-22..2026-08-20"))),
    ("week-city-mismatch", _week(lambda w: w.__setitem__("city", "oakland"))),
    ("week-city-label-mismatch", _week(lambda w: w.__setitem__("city_label", "SF"))),
    ("week-unknown-track", _week(lambda w: w["tracks"].__setitem__("comedy", []))),
    ("week-track-type", _week(lambda w: w["tracks"].__setitem__("music", {}))),
    ("event-not-object", _week(lambda w: w["tracks"]["music"].append("nope"))),
    ("event-missing-field", _week(lambda w: first_event(w).pop("area"))),
    ("event-field-type", _week(lambda w: first_event(w).__setitem__("tags", "house"))),
    ("event-field-type", _week(lambda w: first_event(w).__setitem__("popularity", True))),
    ("event-unknown-field", _week(lambda w: first_event(w).__setitem__("link", "https://x"))),
    ("event-empty-field", _week(lambda w: first_event(w).__setitem__("eid", "  "))),
    ("event-bad-track", _week(lambda w: first_event(w).__setitem__("track", "comedy"))),
    ("event-track-mismatch", _week(lambda w: first_event(w).__setitem__("track", "sports"))),
    ("event-date-format", _week(lambda w: first_event(w).__setitem__("date", "08/20/2026"))),
    ("event-date-format", _week(lambda w: first_event(w).__setitem__("date", "2026-02-30"))),
    ("event-date-outside-window", _week(lambda w: first_event(w).__setitem__("date", day_before(w["window"])))),
    ("event-time-format", _week(lambda w: first_event(w).__setitem__("start", "8pm"))),
    ("event-maps-keys", _week(lambda w: first_event(w).__setitem__("maps", {"bing": "https://x"}))),
    ("event-coords-keys", _week(lambda w: first_event(w).__setitem__("coords", {"lat": 1.0}))),
    ("event-lineup-shape", _week(lambda w: first_event(w).__setitem__("lineup", ["Karizma"]))),
    ("event-popularity-range", _week(lambda w: first_event(w).__setitem__("popularity", 11))),
    ("event-enriched-range", _week(lambda w: first_event(w).__setitem__("enriched", -1))),
    ("event-duplicate-id", _week(lambda w: w["tracks"]["music"].append(dict(first_event(w), eid="dup-1")))),
    ("event-duplicate-eid", _week(lambda w: w["tracks"]["music"].append(dict(first_event(w), id="dup-1")))),
    ("index-count-mismatch", _index(lambda d: d["weeks"][0]["counts"].__setitem__("music", 999))),
    ("index-extra-week", _index(lambda d: d["weeks"].insert(0, dict(d["weeks"][0], week_start="2026-12-28")))),
    ("index-missing-week", _index(lambda d: d["weeks"].pop(0))),
    ("index-order", _index(lambda d: d["weeks"].reverse())),
    ("index-title-mismatch", _index(lambda d: d["weeks"][0].__setitem__("title", "Some other week"))),
    ("index-window-mismatch", _index(lambda d: d["weeks"][0].__setitem__("window", "2026-01-01..2026-01-02"))),
    ("index-duplicate-week", _index(lambda d: d["weeks"].insert(1, dict(d["weeks"][0])))),
    ("index-entry-shape", _index(lambda d: d["weeks"][0].__setitem__("counts", []))),
    ("index-shape", _index(lambda d: d.__setitem__("weeks", {}))),
    ("stats-total-n", _stats(lambda s: s["total"].__setitem__("n", 1))),
    ("stats-total-weeks_published", _stats(lambda s: s["total"].__setitem__("weeks_published", 99))),
    ("stats-total-cities", _stats(lambda s: s["total"].__setitem__("cities", 7))),
    ("stats-city-n", _stats(lambda s: s["cities"][0].__setitem__("n", 1))),
    ("stats-city-weeks", _stats(lambda s: s["cities"][0].__setitem__("weeks_published", 99))),
    ("stats-week-n", _stats(lambda s: s["cities"][0]["weeks"][0].__setitem__("n", 12345))),
    ("stats-missing-city", _stats(lambda s: s["cities"].pop(0))),
    ("stats-unknown-city", _stats(lambda s: s["cities"][0].__setitem__("city", "atlantis"))),
    # A check that is already in the baseline must still fail when it grows.
    ("event-field-type", _week(lambda w: first_event(w).__setitem__("price", None))),
]


def run(root):
    return subprocess.run(
        [sys.executable, os.path.join(root, "scripts", "validate_data.py")],
        capture_output=True,
        text=True,
    )


def failed_codes(out: str) -> set:
    if "FAILED —" not in out:
        return set()
    return {
        line.strip().split(":")[0]
        for line in out.split("FAILED —", 1)[1].splitlines()
        if line.startswith("  ") and ":" in line
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        pristine = os.path.join(tmp, "pristine")
        os.makedirs(os.path.join(pristine, "scripts"))
        shutil.copytree(os.path.join(ROOT, "data"), os.path.join(pristine, "data"))
        for name in ("validate_data.py", "validation_baseline.json"):
            shutil.copy(os.path.join(SCRIPTS, name), os.path.join(pristine, "scripts", name))

        failures = []
        result = run(pristine)
        if result.returncode != 0:
            failures.append("control: clean data should pass\n" + result.stdout + result.stderr)
        print("  ok   control (clean data passes)" if not failures else "  FAIL control")

        for i, (code, mutate) in enumerate(CASES):
            root = os.path.join(tmp, f"case{i}")
            shutil.copytree(pristine, root)
            mutate(root)
            result = run(root)
            got = failed_codes(result.stdout)
            if result.returncode == 0 or code not in got:
                failures.append(
                    f"{code}: exit={result.returncode} reported={sorted(got)}\n{result.stdout}{result.stderr}"
                )
                print(f"  FAIL {code}")
            else:
                print(f"  ok   {code}")
            shutil.rmtree(root)

    print()
    if failures:
        for failure in failures:
            print(failure)
        print(f"{len(failures)}/{len(CASES) + 1} cases FAILED")
        return 1
    print(f"{len(CASES) + 1}/{len(CASES) + 1} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
