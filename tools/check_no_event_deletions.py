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

The one legitimate removal is a *fold*: rule 1b says the same real-world event
gets one card, so when a dedupe verdict merges two already-published duplicates
the loser's card is orphaned and belongs out of the file. That is declared in the
commit message with a `Fold: <removed-id> -> <keeper-id>` trailer, and it is only
honoured when `<keeper-id>` is actually present in the same week file at head —
so a fold cannot quietly become a deletion by naming a keeper that isn't there.
Every commit in `<base>..<head>` is read, because one push can carry several.

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

# A whole line of its own, so the prose above it ("… -> …" shorthand in the body
# of 1bf1f30, say) cannot be mistaken for a declaration.
FOLD_TRAILER = re.compile(r"^Fold:[ \t]*(\S+)[ \t]*->[ \t]*(\S+)[ \t]*$", re.MULTILINE)


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


def fold_declarations(base, head):
    """`{removed-id: {keeper-id, …}}` declared by the commits in `base..head`.

    Read across the whole range, not just the tip: a single push can carry
    several folds, and the range is exactly the set of commits this run is
    judging. A removed id declared more than once is accounted for if *any* of
    its declared keepers survives — the check below is "the event went
    somewhere", and one surviving keeper is that somewhere.
    """
    out = git("log", "--format=%B", f"{base}..{head}")
    if out is None:
        sys.exit(f"error: cannot read commit messages for {base}..{head}")
    folds = {}
    for removed, keeper in FOLD_TRAILER.findall(out.decode("utf-8", "replace")):
        folds.setdefault(removed, set()).add(keeper)
    return folds


def split_folds(gone, head_events, folds):
    """Partition `gone` into (honoured folds, still-unaccounted removals).

    Returns `([(event, keeper), …], [(event, note), …])`. An event is a fold
    only when its `id` was declared *and* the declared keeper is present in this
    same week file at head; a declaration whose keeper is missing stays a
    failure, and says so.
    """
    head_ids = {e["id"] for e in head_events if e.get("id")}
    folded, unaccounted = [], []
    for event in gone:
        eid = event.get("id")
        declared = folds.get(eid) if eid else None
        if not declared:
            unaccounted.append((event, None))
            continue
        present = sorted(k for k in declared if k in head_ids)
        if present:
            folded.append((event, present[0]))
        else:
            missing = ", ".join(sorted(declared))
            unaccounted.append(
                (event, f"declared `Fold: … -> {missing}`, but no such event is here")
            )
    return folded, unaccounted


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

    folds = fold_declarations(base, head)

    failures = []
    honoured = []
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
            # No head copy at all, so no keeper can be present in it: a declared
            # fold cannot excuse the whole week file going away.
            gone = [(e, None) for e in base_events]
            failures.append((path, gone, "the file itself was deleted"))
            continue
        try:
            head_events = events(after, path, head)
        except ValueError as exc:
            failures.append((path, [(e, None) for e in base_events], str(exc)))
            continue
        gone = removed_events(base_events, head_events)
        if gone:
            folded, unaccounted = split_folds(gone, head_events, folds)
            if folded:
                honoured.append((path, folded))
            if unaccounted:
                failures.append((path, unaccounted, None))

    if honoured:
        total_folds = sum(len(f) for _, f in honoured)
        print(f"{total_folds} declared fold(s) honoured:")
        for path, folded in honoured:
            print(f"\n  {path}")
            for event, keeper in folded:
                print(f"    - {describe(event)}\n      folded into {keeper}")
        print()

    total = sum(len(gone) for _, gone, _ in failures)
    if not failures:
        print(f"ok: {len(paths)} week file(s) checked, no event removed")
        return 0

    print(f"{total} event(s) removed across {len(failures)} week file(s):")
    for path, gone, why in failures:
        print(f"\n  {path}" + (f" — {why}" if why else ""))
        for event, note in gone:
            print(f"    - {describe(event)}" + (f" — {note}" if note else ""))
    print(
        "\nREQUIREMENTS.md rule 7: never delete events. An event that dropped out"
        "\nof view is kept and flagged `active: false` ('carried over'), so that it"
        "\nflips back to `active: true` if it reappears. Restore the entries above"
        "\nfrom the base commit rather than removing them."
        "\n\nIf a removal is a rule 1b fold — a duplicate retracted into a keeper card"
        "\nthat stays in the same week file — declare it in the commit message with a"
        "\n`Fold: <removed-id> -> <keeper-id>` trailer on a line of its own, one per"
        "\nretracted card. The keeper must be present at head for it to count."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
