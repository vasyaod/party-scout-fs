#!/usr/bin/env python3
"""Refuse a commit that adds a new `data/` violation, before it is a commit.

`scripts/validate_data.py` only ever ran in CI — i.e. after the push had
already landed on `main` and gone live on the Pages site (issue #11). This runs
the very same checker against the tree the commit is about to record, locally.

What it fails on is a **ratchet, not the committed baseline**: the staged tree
is compared against `HEAD`, both measured with *this* commit's copy of the
validator, and the commit is refused only for a check whose count goes UP.
Violations that were already in `HEAD` are somebody else's commit to fix
(issue #10 has 132 of them, above baseline right now) — blocking every scan on
them would only teach the agents to pass `--no-verify`. They are still
reported, as a note, and the absolute bar stays in CI
(`.github/workflows/validate.yml`), which this gate does not replace: a hook
can be bypassed and is absent in a clone that never ran `install_hooks.py`.

Measuring both sides with the staged validator is what lets a commit *tighten*
the rules: a newly added check finds its violations in `HEAD` too, so the count
does not move and the commit that adds the check is not refused by it.

Usage:
    python3 tools/pre_commit_validate.py            # gate what is staged now
    python3 tools/pre_commit_validate.py --ref HEAD~1   # compare against another commit

Installed as the pre-commit hook by `python3 tools/install_hooks.py`.
"""

from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The paths `validate.yml` watches: the data, and the checker that reads it.
WATCHED = ("data", "scripts")


def git(*args: str, check: bool = True) -> str:
    """Run git in this repo. Inherits GIT_INDEX_FILE, which is the point:

    under `git commit -a` (or `git commit <path>`) git points that at a
    temporary index holding the changes, so the tree we measure is the tree
    the commit will record — not the working tree, and not the stale index.
    """
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def export(tree: str, dest: str, paths) -> None:
    """Materialise `paths` of a tree into `dest` — no touching the working tree."""
    os.makedirs(dest, exist_ok=True)
    archive = subprocess.run(
        ["git", "archive", "--format=tar", tree, *paths],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        if hasattr(tarfile, "data_filter"):  # python 3.11.4+
            tar.extractall(dest, filter="data")
        else:
            tar.extractall(dest)


def top_level(tree: str, wanted) -> list:
    """Which of `wanted` exist at the root of `tree` — `git archive` errors on the rest."""
    present = set(git("ls-tree", "--name-only", tree).splitlines())
    return [name for name in wanted if name in present]


def only_failures(text: str) -> str:
    """Drop the tolerated checks from the validator's report.

    It prints every check it counted, `ok` ones included with eight samples
    each — ~70 lines here, which buries the one line that refused the commit.
    A hook nobody reads is the failure mode this gate exists to fix. The blocks
    are `  FAIL <code>` / `  ok   <code>` followed by indented samples;
    everything else (headers, the summary) is kept as-is.
    """
    kept, keeping = [], True
    for line in text.splitlines():
        if line.startswith("  FAIL ") or line.startswith("  ok   "):
            keeping = line.startswith("  FAIL ")
        elif line.strip() and not line.startswith("    "):
            keeping = True
        if keeping:
            kept.append(line)
    return "\n".join(kept).strip()


def run_validator(repo: str, *args: str):
    return subprocess.run(
        [sys.executable, os.path.join(repo, "scripts", "validate_data.py"), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", default="HEAD", help="commit to ratchet against (default HEAD)")
    args = parser.parse_args(argv)

    touched = git("diff", "--cached", "--name-only").splitlines()
    if not any(p.split("/", 1)[0] in WATCHED for p in touched):
        print(f"pre-commit: nothing staged under {'/, '.join(WATCHED)}/ — validator skipped")
        return 0

    if git("ls-files", "--unmerged"):
        print("pre-commit: the index has unmerged paths — resolve them first")
        return 0

    have_ref = subprocess.run(
        ["git", "cat-file", "-e", f"{args.ref}^{{commit}}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0

    with tempfile.TemporaryDirectory() as tmp:
        staged, before = os.path.join(tmp, "staged"), os.path.join(tmp, "before")
        tree = git("write-tree")
        export(tree, staged, top_level(tree, WATCHED))
        if not os.path.isdir(os.path.join(staged, "scripts")):
            print("pre-commit: no scripts/validate_data.py in this tree — nothing to run")
            return 0

        reference = os.path.join(tmp, "reference.json")
        if have_ref:
            # `before` is the ref's data measured by the *staged* validator, so a
            # commit that adds a check is not refused by its own new check.
            export(args.ref, before, top_level(args.ref, ("data",)))
            shutil.copytree(
                os.path.join(staged, "scripts"), os.path.join(before, "scripts")
            )
            snapshot = run_validator(before, "--update-baseline", "--baseline", reference)
            if snapshot.returncode != 0:
                print(f"pre-commit: could not measure {args.ref}, falling back to the "
                      f"committed baseline\n{snapshot.stdout}")
                reference = None
        else:
            reference = None  # first commit: nothing to ratchet against

        gate_args = ("--baseline", reference) if reference else ()
        gate = run_validator(staged, *gate_args)
        if gate.returncode != 0:
            print(only_failures(gate.stdout))
            print(
                "\npre-commit: REFUSED — this commit adds violations that "
                + (f"{args.ref} does not have.\n" if reference
                   else "scripts/validation_baseline.json does not allow.\n")
                + "Fix them in the generator (party-scout-code) and re-stage; data/ is\n"
                "generated, not hand-edited (REQUIREMENTS.md rule 15).\n"
                "Counts above are for the whole tree, so `allowed` is what was already\n"
                "there — ignore the --update-baseline line: re-blessing a brand-new\n"
                "violation into scripts/validation_baseline.json is not a fix (issue #10).\n"
                "`git commit --no-verify` skips this gate; CI will not skip it."
            )
            return 1

        # Passing the ratchet does not mean data/ is clean: what HEAD already
        # carries is above the committed baseline in this repo today, and that
        # is what keeps CI red. Say so — quietly, without blocking the commit.
        absolute = run_validator(staged)
        if absolute.returncode != 0:
            print(
                "pre-commit: ok — no new violation. Note: data/ is still above its\n"
                "committed baseline from before this commit, so CI (validate data) stays\n"
                "red until that is fixed. `python3 scripts/validate_data.py` shows it."
            )
            return 0

    print(f"pre-commit: ok — data/ validates, and no check grew against {args.ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
