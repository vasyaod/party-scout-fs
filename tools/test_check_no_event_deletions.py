#!/usr/bin/env python3
"""Self-test for tools/check_no_event_deletions.py.

Each case builds a throwaway git repo with one week file, commits a change to
it, and asserts the checker's verdict on `parent..HEAD`. Without this, the gate
could stop firing — or start excusing removals it shouldn't — and both failures
look like "CI is green".

The last case replays the real retraction that motivated the `Fold:` trailer
(party-scout-fs@1bf1f30, issue #8) against this very repo, so the fixture and
the incident cannot drift apart.

Run: python3 tools/test_check_no_event_deletions.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(ROOT, "tools", "check_no_event_deletions.py")
WEEK = os.path.join("data", "los-angeles", "2026-09-14.json")

# The incident this gate had to learn about: two orphaned duplicates retracted
# into keepers that stay in the same week file.
INCIDENT_BASE = "87528b4611f73a13f8a888c9ff674f9e8769d9bd"
INCIDENT_HEAD = "1bf1f309d6171504a21659cba5a99275369b8674"
INCIDENT_TRAILERS = (
    "Fold: 2026-09-14-music-gravedgr-61961b -> "
    "2026-09-14-music-gravedgr-alyssa-jolee-034f4b\n"
    "Fold: 2026-09-14-music-nandu-212b21 -> 2026-09-14-music-nandu-hbb-4dff09"
)

DUPE = {"id": "ev-dupe", "date": "2026-09-18", "name": "Gravedgr", "venue": "Palladium"}
KEEPER = {
    "id": "ev-keeper",
    "date": "2026-09-18",
    "name": "Gravedgr, Alyssa Jolee",
    "venue": "Palladium",
}
OTHER = {"id": "ev-other", "date": "2026-09-19", "name": "Nandu", "venue": "Matriarch"}

# The four real cards of the incident: two orphaned duplicates (first) and the
# two keepers they were folded into (last), which stay in the week file.
INCIDENT_PUBLISHED = [
    {
        "id": "2026-09-14-music-gravedgr-61961b",
        "date": "2026-09-18",
        "name": "Gravedgr",
        "venue": "Hollywood Palladium",
    },
    {
        "id": "2026-09-14-music-nandu-212b21",
        "date": "2026-09-18",
        "name": "Nandu",
        "venue": "Matriarch La",
    },
    {
        "id": "2026-09-14-music-gravedgr-alyssa-jolee-034f4b",
        "date": "2026-09-18",
        "name": "Gravedgr, Alyssa Jolee",
        "venue": "Hollywood Palladium",
    },
    {
        "id": "2026-09-14-music-nandu-hbb-4dff09",
        "date": "2026-09-18",
        "name": "Nandu, HBB",
        "venue": "Matriarch La",
    },
]


def week(events):
    return {"week_start": "2026-09-14", "tracks": {"music": list(events)}}


def git(repo, *args, **kwargs):
    return subprocess.run(
        ["git", "-C", repo, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
        **kwargs,
    )


def write_week(repo, events):
    path = os.path.join(repo, WEEK)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(week(events), fh, ensure_ascii=False, indent=2)


def commit(repo, message):
    git(repo, "add", "-A")
    git(
        repo,
        "-c",
        "user.name=test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )


def make_repo(tmp, name, revisions):
    """A repo whose first commit publishes `revisions[0]`, then one per rest.

    Each revision is `(events, commit message)`.
    """
    repo = os.path.join(tmp, name)
    os.makedirs(repo)
    git(repo, "init", "-q", "-b", "main")
    for events, message in revisions:
        write_week(repo, events)
        commit(repo, message)
    return repo


def check(repo, base="HEAD~1", head="HEAD"):
    return subprocess.run(
        [sys.executable, CHECKER, "--no-merge-base", "--base", base, "--head", head],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


# Each case: (name, [(events, message), …], expected exit, substrings expected
# in the output).
PUBLISHED = [DUPE, KEEPER, OTHER]

CASES = [
    (
        "control: an edit that removes nothing passes",
        [
            (PUBLISHED, "publish"),
            ([DUPE, KEEPER, dict(OTHER, venue="Matriarch LA")], "fill a venue in"),
        ],
        0,
        ["no event removed"],
    ),
    (
        "an undeclared removal still fails",
        [(PUBLISHED, "publish"), ([KEEPER, OTHER], "drop a card")],
        1,
        ["1 event(s) removed", "ev-dupe", "rule 7"],
    ),
    (
        "a declared fold whose keeper is present passes",
        [
            (PUBLISHED, "publish"),
            ([KEEPER, OTHER], "retract a duplicate\n\nFold: ev-dupe -> ev-keeper"),
        ],
        0,
        ["1 declared fold(s) honoured", "folded into ev-keeper", "no event removed"],
    ),
    (
        "a declared fold whose keeper is absent fails",
        [
            (PUBLISHED, "publish"),
            ([OTHER], "retract both\n\nFold: ev-dupe -> ev-keeper"),
        ],
        1,
        ["2 event(s) removed", "no such event is here", "ev-keeper"],
    ),
    (
        "a fold trailer naming another id does not excuse this removal",
        [
            (PUBLISHED, "publish"),
            ([DUPE, KEEPER], "drop a card\n\nFold: ev-dupe -> ev-keeper"),
        ],
        1,
        ["1 event(s) removed", "ev-other"],
    ),
    (
        "the trailer is read across every commit in the range, not just the tip",
        [
            (PUBLISHED, "publish"),
            ([KEEPER, OTHER], "retract a duplicate\n\nFold: ev-dupe -> ev-keeper"),
            ([KEEPER, OTHER, dict(DUPE, id="ev-new", name="Ovrkast")], "add a card"),
        ],
        0,
        ["1 declared fold(s) honoured", "no event removed"],
    ),
    (
        "prose that merely mentions a fold is not a declaration",
        [
            (PUBLISHED, "publish"),
            ([KEEPER, OTHER], "drop a card\n\n  ev-dupe -> ev-keeper was proposed"),
        ],
        1,
        ["1 event(s) removed", "ev-dupe"],
    ),
    (
        "the incident's own commit message, both folds honoured",
        [
            (INCIDENT_PUBLISHED, "publish"),
            (
                INCIDENT_PUBLISHED[2:],
                "los-angeles 2026-09-14: retract 2 duplicate cards folded in the"
                " pool (issue #47)\n\n" + INCIDENT_TRAILERS,
            ),
        ],
        0,
        [
            "2 declared fold(s) honoured",
            "folded into 2026-09-14-music-gravedgr-alyssa-jolee-034f4b",
            "folded into 2026-09-14-music-nandu-hbb-4dff09",
            "no event removed",
        ],
    ),
]


def incident_replay():
    """Replay party-scout-fs@1bf1f30 itself, when its history is at hand.

    Returns `(ran, failures)`. A shallow clone won't have the commit; CI checks
    out with fetch-depth 0, so there this is the real thing, not a fixture.
    """
    have = subprocess.run(
        ["git", "-C", ROOT, "cat-file", "-e", f"{INCIDENT_HEAD}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if have.returncode != 0:
        print(f"  skip {INCIDENT_HEAD[:7]} not in this clone — fixtures only")
        return False, []
    result = check(ROOT, base=INCIDENT_BASE, head=INCIDENT_HEAD)
    name = "1bf1f30 (the incident) passes: two folds, both keepers present"
    wanted = [
        "2 declared fold(s) honoured",
        "2026-09-14-music-gravedgr-alyssa-jolee-034f4b",
        "2026-09-14-music-nandu-hbb-4dff09",
        "no event removed",
    ]
    missing = [w for w in wanted if w not in result.stdout]
    if result.returncode != 0 or missing:
        print(f"  FAIL {name}")
        why = f"{name}: exit={result.returncode} missing={missing}\n{result.stdout}"
        return True, [why]
    print(f"  ok   {name}")
    return True, []


def main():
    failures = []
    print("check_no_event_deletions self-test\n")
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, revisions, want_code, wanted) in enumerate(CASES):
            repo = make_repo(tmp, f"case{i}", revisions)
            base = f"HEAD~{len(revisions) - 1}"
            result = check(repo, base=base)
            missing = [w for w in wanted if w not in result.stdout]
            if result.returncode != want_code or missing:
                failures.append(
                    f"{name}: exit={result.returncode} (want {want_code}) "
                    f"missing={missing}\n{result.stdout}"
                )
                print(f"  FAIL {name}")
            else:
                print(f"  ok   {name}")
        ran_replay, replay_failures = incident_replay()
        failures.extend(replay_failures)

    total = len(CASES) + (1 if ran_replay else 0)
    print()
    if failures:
        for failure in failures:
            print(failure)
        print(f"{len(failures)}/{total} case(s) FAILED")
        return 1
    print(f"{total}/{total} case(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
