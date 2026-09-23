#!/usr/bin/env python3
"""Self-test for scripts/validate_data.py.

Each case copies data/ to a scratch tree, breaks it in exactly one way, and
asserts the validator reports the expected check code and exits non-zero.
Without this, a check that silently stops firing would look like clean data.

The scratch tree's baseline is pinned to the scratch data's own counts first,
so a single injected violation always takes its check above what is allowed.
Against the committed baseline it would not whenever the real data has
improved below it: the injection just refills the headroom and nothing is
reported (issue #20 — `event-empty-field` went 2 -> 1 and CI went red).

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
OTHER_WEEK = "2026-08-10.json"


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
    # Issue #22: `area` is enrichment-owned — empty on an ENRICHED event is a violation.
    ("event-empty-field", _week(lambda w: first_event(w).update(enriched=1, area=""))),
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


def run(root, *args):
    return subprocess.run(
        [sys.executable, os.path.join(root, "scripts", "validate_data.py"), *args],
        capture_output=True,
        text=True,
    )


def pin(root):
    """Set `root`'s baseline to exactly its own counts: zero headroom anywhere."""
    result = run(root, "--update-baseline")
    if result.returncode != 0:
        raise RuntimeError("--update-baseline failed\n" + result.stdout + result.stderr)


def set_allowed(root, code, delta):
    """Move one check's allowance in `root`'s baseline by `delta`."""
    path = os.path.join(root, "scripts", "validation_baseline.json")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["allowed"][code] = doc["allowed"].get(code, 0) + delta
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)


def empty_area(root, fill):
    """Blank (fill=None) or fill the `area` of the last music event in another week.

    A violation of a check that is in the baseline, somewhere other than the
    event the cases mutate — the fixture for "the real count dropped by one".
    """
    week = read(root, CITY, OTHER_WEEK)
    event = week["tracks"]["music"][-1]
    event["area"] = "" if fill is None else fill
    # An empty `area` only counts on an enriched event (issue #22).
    event["enriched"] = max(1, event.get("enriched") or 0)
    write(root, week, CITY, OTHER_WEEK)


def git(root, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root, check=True, capture_output=True,
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

        def expect(label, ok, detail):
            if not ok:
                failures.append(f"{label}\n{detail}")
            print(f"  {'ok  ' if ok else 'FAIL'} {label}")

        def check_case(base, name, code, mutate):
            root = os.path.join(tmp, name)
            shutil.copytree(base, root)
            mutate(root)
            result = run(root)
            got = failed_codes(result.stdout)
            expect(
                f"{code}" + ("" if base == pristine else f" ({name})"),
                result.returncode != 0 and code in got,
                f"exit={result.returncode} reported={sorted(got)}\n{result.stdout}{result.stderr}",
            )
            shutil.rmtree(root)

        # The real data against the committed baseline — what CI checks last.
        result = run(pristine)
        expect("control (clean data passes)", result.returncode == 0, result.stdout + result.stderr)

        pin(pristine)
        for i, (code, mutate) in enumerate(CASES):
            check_case(pristine, f"case{i}", code, mutate)

        # Issue #22: an empty `area` on a draft (`enriched: 0`) is NOT a violation;
        # an empty `eid` on the same draft still is.
        root = os.path.join(tmp, "draft-area")
        shutil.copytree(pristine, root)
        _week(lambda w: first_event(w).update(enriched=0, area=""))(root)
        result = run(root)
        expect(
            "draft: empty area on an enriched=0 event is not reported",
            result.returncode == 0 and "event-empty-field" not in failed_codes(result.stdout),
            result.stdout + result.stderr,
        )
        shutil.rmtree(root)
        root = os.path.join(tmp, "draft-eid")
        shutil.copytree(pristine, root)
        _week(lambda w: first_event(w).update(enriched=0, eid=" "))(root)
        result = run(root)
        expect(
            "draft: empty eid on an enriched=0 event is still reported",
            result.returncode != 0 and "event-empty-field" in failed_codes(result.stdout),
            result.stdout + result.stderr,
        )
        shutil.rmtree(root)

        # Regression for issue #20: the real count of a baselined check drops by
        # one below its baseline, and that check's case must still fire.
        improved = os.path.join(tmp, "improved")
        shutil.copytree(pristine, improved)
        empty_area(improved, None)
        pin(improved)  # the extra empty `area` is now a known, baselined violation...
        empty_area(improved, "Mission")  # ...and got fixed: one below the baseline
        slack = run(improved)
        expect(
            "fixture: event-empty-field is below its baseline",
            slack.returncode == 0 and "\n  event-empty-field: " in slack.stdout.partition("below baseline")[2],
            slack.stdout + slack.stderr,
        )
        # Not pinned: the harness before #20. The injection only refills the slack.
        case = next(m for c, m in CASES if c == "event-empty-field")
        root = os.path.join(tmp, "unpinned")
        shutil.copytree(improved, root)
        case(root)
        result = run(root)
        expect(
            "fixture: without pinning the injection is not reported (as in #20)",
            result.returncode == 0,
            result.stdout + result.stderr,
        )
        shutil.rmtree(root)
        pin(improved)
        check_case(improved, "one below baseline", "event-empty-field", case)

        # --ref: that slack does not hide a regression in CI either. `improved`
        # (baseline one above the data) is the parent commit; the child undoes
        # the fix. Within the committed baseline, yet above what the parent had.
        set_allowed(improved, "event-empty-field", +1)
        git(improved, "init", "-q")
        git(improved, "add", "-A")
        git(improved, "commit", "-q", "-m", "parent")
        empty_area(improved, None)
        plain = run(improved)
        expect(
            "fixture: the regression is within the committed baseline",
            plain.returncode == 0,
            plain.stdout + plain.stderr,
        )
        ratchet = run(improved, "--ref", "HEAD")
        got = failed_codes(ratchet.stdout)
        expect(
            "--ref: a regression into the baseline's slack fails",
            ratchet.returncode != 0 and got == {"event-empty-field"},
            f"exit={ratchet.returncode} reported={sorted(got)}\n{ratchet.stdout}{ratchet.stderr}",
        )
        # ...and an improvement against the parent never does.
        git(improved, "commit", "-q", "-am", "regressed parent")
        empty_area(improved, "Mission")
        better = run(improved, "--ref", "HEAD")
        expect(
            "--ref: an improvement passes",
            better.returncode == 0,
            better.stdout + better.stderr,
        )
        bad = run(improved, "--ref", "no-such-ref")
        expect(
            "--ref: an unreadable ref fails loudly",
            bad.returncode != 0 and "no-such-ref" in bad.stdout + bad.stderr,
            bad.stdout + bad.stderr,
        )

        # Only 8 samples are printed, in file order — nine `link`s crowd the
        # lone `shoe_size` out of them entirely. The tally is the only thing
        # in the output that says which field actually dominates.
        root = os.path.join(tmp, "breakdown")
        shutil.copytree(pristine, root)
        week = read(root, CITY, WEEK)
        for event in week["tracks"]["music"][:9]:
            event["link"] = "https://x"
        first_event(week)["shoe_size"] = 44
        write(root, week, CITY, WEEK)
        out = run(root).stdout
        expect("event-unknown-field breakdown", "by field: link 9, shoe_size 1" in out,
               "no per-field tally\n" + out)
        shutil.rmtree(root)

    total = len(CASES) + 9  # the cases, the control, #20's 7 and the breakdown
    print()
    if failures:
        for failure in failures:
            print(failure)
        print(f"{len(failures)}/{total} cases FAILED")
        return 1
    print(f"{total}/{total} cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
