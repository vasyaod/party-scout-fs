#!/usr/bin/env python3
"""Fail when a change would remove an event from a committed week file.

REQUIREMENTS.md rule 7 ("Never delete events") says an event that drops out of
view is *kept* and flagged `active: false` — it is never removed from the JSON.
Nothing enforced that: a generator regression could drop a historical event from
a committed `data/<city>/<week>.json` and the loss would be silent and, for a
public database, effectively unrecoverable.

This compares every changed `data/<city>/<YYYY-MM-DD>.json` against its version
at a base commit and fails if an event that was present there is gone. Additions
are free; so is `active: true` -> `active: false` (that IS the carried-over
form rule 7 asks for).

Usage:
    tools/check_no_event_deletions.py --base <ref> [--head <ref>]

`--head` defaults to HEAD. By default the comparison point is
`git merge-base <base> <head>`, so only the change's own edits are judged and a
deletion that already exists on the base branch is not blamed on it; pass
`--no-merge-base` to compare against `<base>` verbatim (what a push event wants,
where before/after are already consecutive).
"""

import argparse
import json
import re
import subprocess
import sys

WEEK_FILE = re.compile(r"^data/[^/]+/\d{4}-\d{2}-\d{2}\.json$")


def git(*args):
    """Run a git command and return its stdout, or None if it failed."""
    proc = subprocess.run(
        ["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def blob(ref, path):
    """The bytes of `path` at `ref`, or None when the file is absent there."""
    return git("show", f"{ref}:{path}")


def events(raw, path, ref):
    """Every event in a week file, as a list of dicts.

    Raises ValueError when the file will not parse — a week that stopped being
    readable JSON has lost every event in it just as thoroughly as one whose
    entries were deleted.
    """
    try:
        week = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} at {ref} is not valid JSON: {exc}") from exc
    if not isinstance(week, dict) or not isinstance(week.get("tracks"), dict):
        raise ValueError(f"{path} at {ref} has no `tracks` object")
    out = []
    for track, listing in week["tracks"].items():
        if not isinstance(listing, list):
            raise ValueError(f"{path} at {ref}: track `{track}` is not a list")
        out.extend(e for e in listing if isinstance(e, dict))
    return out


def fallback_key(event):
    """Identity that survives an `id` change.

    `id` is derived from week + track + name/day/area/venue (MODEL.md:124), so
    it is stable only while those are — filling a venue in (`TBA` ->
    `Globe Theatre`, d0ad204) or re-classifying a track (`music` -> `sports`,
    77224c8) re-keys an event that never went anywhere. Date + name is what
    stays put across both, and it is also the only handle on the one event
    published before `id` existed (`data/los-angeles/2026-07-20.json`,
    "Reggae Love & Brunch"), so that backfilling an `id` onto it reads as an
    edit rather than a removal.
    """
    name = event.get("name")
    return (event.get("date"), name.strip().lower() if isinstance(name, str) else name)


def describe(event):
    bits = [b for b in (event.get("day"), event.get("date"), event.get("venue")) if b]
    where = f" ({', '.join(bits)})" if bits else ""
    return f'{event.get("id") or "<no id>"}  "{event.get("name")}"{where}'


def removed_events(before, after):
    """Events present in `before` that no longer appear in `after`.

    An event counts as still there if its `id` is still there, or — for the
    re-keying above — if some event with the same date and name is.
    """
    ids = {e["id"] for e in after if e.get("id")}
    keys = {fallback_key(e) for e in after}
    return [
        e
        for e in before
        if not (e.get("id") and e["id"] in ids) and fallback_key(e) not in keys
    ]


def changed_week_files(base, head):
    # --no-renames so a week file renamed away still shows up under its old
    # path; a rename out of `data/<city>/<week>.json` drops the week from the
    # site exactly like a delete does.
    out = git("diff", "--name-only", "--no-renames", base, head, "--", "data")
    if out is None:
        sys.exit(f"error: cannot diff {base}..{head} — is the base commit fetched?")
    paths = out.decode().splitlines()
    return sorted(p for p in paths if WEEK_FILE.match(p))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="commit to compare against")
    parser.add_argument("--head", default="HEAD", help="commit to check (default HEAD)")
    parser.add_argument(
        "--no-merge-base",
        action="store_true",
        help="compare against --base itself instead of merge-base(base, head)",
    )
    args = parser.parse_args()

    base, head = args.base, args.head
    if not args.no_merge_base:
        merge_base = git("merge-base", base, head)
        if merge_base is None:
            sys.exit(f"error: no merge base between {base} and {head}")
        base = merge_base.decode().strip()

    paths = changed_week_files(base, head)
    if not paths:
        print(f"no week files changed between {base[:12]} and {head} — nothing to check")
        return 0

    failures = []
    for path in paths:
        before = blob(base, path)
        if before is None:
            continue  # new week file: nothing could have been removed from it
        try:
            base_events = events(before, path, base)
        except ValueError as exc:
            # Already broken at the base commit — not this change's doing.
            print(f"warning: skipping {path}: {exc}", file=sys.stderr)
            continue
        after = blob(head, path)
        if after is None:
            failures.append((path, base_events, "the file itself was deleted"))
            continue
        try:
            head_events = events(after, path, head)
        except ValueError as exc:
            failures.append((path, base_events, str(exc)))
            continue
        gone = removed_events(base_events, head_events)
        if gone:
            failures.append((path, gone, None))

    total = sum(len(gone) for _, gone, _ in failures)
    if not failures:
        print(f"ok: {len(paths)} week file(s) checked, no event removed")
        return 0

    print(f"{total} event(s) removed across {len(failures)} week file(s):")
    for path, gone, why in failures:
        print(f"\n  {path}" + (f" — {why}" if why else ""))
        for event in gone:
            print(f"    - {describe(event)}")
    print(
        "\nREQUIREMENTS.md rule 7: never delete events. An event that dropped out"
        "\nof view is kept and flagged `active: false` ('carried over'), so that it"
        "\nflips back to `active: true` if it reappears. Restore the entries above"
        "\nfrom the base commit rather than removing them."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
