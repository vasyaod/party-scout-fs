#!/usr/bin/env python3
"""Self-test for the pre-commit gate (tools/pre_commit_validate.py).

Each case builds a throwaway git repo carrying this repo's real `scripts/`,
`tools/` and `hooks/` plus a tiny synthetic `data/` tree, installs the hook the
documented way, and then makes a real `git commit` — so what is asserted is the
commit landing or not landing, not a function's return value.

A gate nobody can see fail is indistinguishable from no gate at all, which is
the state issue #11 describes: the checker existed, it just never ran before
the data was already on main.

Run: python3 tools/test_pre_commit_validate.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALLER = os.path.join("tools", "install_hooks.py")
CITY, WEEK = "san-francisco", "2026-09-14"

# Enough of MODEL.md for scripts/validate_data.py to call the tree clean; the
# control case asserts exactly that, so a fixture that silently stopped being
# valid would show up as a failure rather than as a free pass.
EVENT = {
    "track": "music",
    "category": "club",
    "name": "Test Night",
    "day": "Fri",
    "date": "2026-09-18",
    "time": "22:00",
    "area": "SoMa",
    "venue": "Test Venue",
    "address": "1 Test St, San Francisco",
    "why": "A fixture, not a party.",
    "summary": "A fixture, not a party.",
    "price": "$20",
    "tags": ["techno"],
    "sources": ["https://ra.co/events/1"],
    "tickets": ["https://ra.co/events/1"],
    "maps": {},
    "popularity": 5,
    "active": True,
}


def event(n: int, **extra) -> dict:
    return dict(EVENT, id=f"ev-{n}", eid=f"eid-{n}", **extra)


def git(repo, *args, check=True):
    """git, with the caller's own GIT_* stripped so a nested run can't leak in."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        ["git", "-C", repo, "-c", "user.name=test", "-c", "user.email=test@example.invalid", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=check,
        env=env,
    )


def write_data(repo, events) -> None:
    """A consistent data/ tree for `events` — index and stats derived, never stale."""
    week = {
        "week_start": WEEK,
        "window": "2026-09-17..2026-09-20",
        "title": f"SF {WEEK}",
        "location": "San Francisco Bay Area",
        "city": CITY,
        "city_label": "San Francisco",
        "generated_at": f"{WEEK}T00:00:00Z",
        "tracks": {"music": list(events), "sports": []},
    }
    counts = {"music": len(events), "sports": 0}
    files = {
        "data/cities.json": {"cities": [{"slug": CITY, "label": "San Francisco"}]},
        f"data/{CITY}/{WEEK}.json": week,
        f"data/{CITY}/index.json": {
            "weeks": [
                {"week_start": WEEK, "window": week["window"], "title": week["title"], "counts": counts}
            ]
        },
        "data/stats.json": {
            "total": {"n": len(events), "weeks_published": 1, "cities": 1},
            "cities": [
                {
                    "city": CITY,
                    "n": len(events),
                    "weeks_published": 1,
                    "weeks": [{"week_start": WEEK, "n": len(events)}],
                }
            ],
        },
    }
    for name, payload in files.items():
        path = os.path.join(repo, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)


def make_repo(tmp, name, events):
    """A repo with the gate installed and `events` already published in HEAD."""
    repo = os.path.join(tmp, name)
    os.makedirs(repo)
    git(repo, "init", "-q", "-b", "main")
    for src in ("scripts", "tools", "hooks"):
        shutil.copytree(os.path.join(ROOT, src), os.path.join(repo, src))
    # An empty baseline: in the fixture every violation is a violation, so the
    # note about the committed baseline is observable too.
    with open(os.path.join(repo, "scripts", "validation_baseline.json"), "w", encoding="utf-8") as fh:
        json.dump({"allowed": {}}, fh, indent=2)
    subprocess.run([sys.executable, INSTALLER], cwd=repo, stdout=subprocess.DEVNULL, check=True)
    write_data(repo, events)
    git(repo, "add", "-A")
    # --no-verify: this is fixture setup, and some cases need HEAD to publish
    # exactly the violation the gate would refuse.
    git(repo, "commit", "-q", "--no-verify", "-m", "publish")
    return repo


def head(repo) -> str:
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def commit(repo, args=("-a",)):
    """Stage (unless `commit -a` is doing it) and commit. Returns the attempt."""
    if "-a" not in args:
        git(repo, "add", "-A")
    return git(repo, "commit", *args, "-m", "scan", check=False)


UNKNOWN = {"source_url": "https://ra.co/events/1"}  # the real issue #10 field


def case_control(repo):
    """A clean added event commits, and the tree validates outright."""
    write_data(repo, [event(0), event(1)])
    # "data/ validates" is the absolute verdict, not the ratchet's: it pins the
    # fixture as genuinely clean, so the refusals below cannot be free passes.
    return commit(repo), 0, ["pre-commit: ok — data/ validates"]


def case_unknown_field(repo):
    """The issue's own failure: an undocumented field never becomes a commit."""
    write_data(repo, [event(0), event(1, **UNKNOWN)])
    return commit(repo, ("--quiet",)), 1, ["event-unknown-field", "REFUSED", "source_url"]


def case_commit_all(repo):
    """`git commit -a` never staged a thing by hand — the gate still sees it."""
    write_data(repo, [event(0, **UNKNOWN)])
    return commit(repo, ("-a", "--quiet")), 1, ["event-unknown-field", "REFUSED"]


def case_edit_of_published(repo):
    """Breaking an event that was already fine is caught as well as adding one."""
    write_data(repo, [event(0, popularity=99)])
    return commit(repo), 1, ["event-popularity-range", "REFUSED"]


def case_no_verify(repo):
    """The documented escape hatch really does escape — hence CI stays."""
    write_data(repo, [event(0, **UNKNOWN)])
    return commit(repo, ("--no-verify", "--quiet")), 0, []


def case_untouched_data(repo):
    """A commit that touches no data/ skips the validator instead of paying for it."""
    with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("hello\n")
    return commit(repo, ("--quiet",)), 0, ["validator skipped"]


def case_pre_existing(repo):
    """The ratchet: junk already in HEAD does not hold an unrelated commit hostage."""
    write_data(repo, [event(0, **UNKNOWN), event(1)])
    return commit(repo), 0, ["no new violation", "CI (validate data) stays"]


# (name, events HEAD publishes, the attempt, whether HEAD must move)
CASES = [
    ("a clean event commits", [event(0)], case_control, True),
    ("an unknown field is refused before it is a commit", [event(0)], case_unknown_field, False),
    ("`git commit -a` is gated too, not just a staged index", [event(0)], case_commit_all, False),
    ("breaking a published event is refused", [event(0)], case_edit_of_published, False),
    ("--no-verify bypasses the gate (CI is the backstop)", [event(0)], case_no_verify, True),
    ("a commit outside data/ skips the validator", [event(0)], case_untouched_data, True),
    ("a violation already in HEAD blocks nothing new", [event(0, **UNKNOWN)], case_pre_existing, True),
]


def check_install(tmp) -> list:
    """--check must be able to say no, or its yes means nothing."""
    failures = []
    repo = os.path.join(tmp, "install")
    os.makedirs(repo)
    git(repo, "init", "-q", "-b", "main")
    for src in ("tools", "hooks"):
        shutil.copytree(os.path.join(ROOT, src), os.path.join(repo, src))

    def check():
        return subprocess.run(
            [sys.executable, INSTALLER, "--check"], cwd=repo,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )

    for name, want, wanted, action in (
        ("a fresh clone reports the hooks as NOT active", 1, ["NOT active", INSTALLER], None),
        ("after the install step they are active", 0, ["hooks active"], []),
        ("--uninstall turns them off again", 1, ["NOT active"], ["--uninstall"]),
    ):
        if action is not None:
            subprocess.run([sys.executable, INSTALLER, *action], cwd=repo,
                           stdout=subprocess.DEVNULL, check=True)
        result = check()
        missing = [w for w in wanted if w not in result.stdout]
        if result.returncode != want or missing:
            failures.append(f"{name}: exit={result.returncode} (want {want}) missing={missing}\n{result.stdout}")
            print(f"  FAIL {name}")
        else:
            print(f"  ok   {name}")
    return failures


def check_first_commit(tmp) -> list:
    """With no HEAD there is nothing to ratchet against, so the bar is absolute."""
    failures = []
    repo = os.path.join(tmp, "first")
    os.makedirs(repo)
    git(repo, "init", "-q", "-b", "main")
    for src in ("scripts", "tools", "hooks"):
        shutil.copytree(os.path.join(ROOT, src), os.path.join(repo, src))
    with open(os.path.join(repo, "scripts", "validation_baseline.json"), "w", encoding="utf-8") as fh:
        json.dump({"allowed": {}}, fh, indent=2)
    subprocess.run([sys.executable, INSTALLER], cwd=repo, stdout=subprocess.DEVNULL, check=True)

    for name, events, want in (
        ("the very first commit is measured absolutely, and can fail", [event(0, **UNKNOWN)], 1),
        ("a clean first commit lands", [event(0)], 0),
    ):
        write_data(repo, events)
        result = commit(repo, ("--quiet",))
        landed = git(repo, "rev-parse", "--verify", "-q", "HEAD", check=False).returncode == 0
        if result.returncode != want or landed != (want == 0):
            failures.append(f"{name}: exit={result.returncode} (want {want}) committed={landed}\n{result.stdout}")
            print(f"  FAIL {name}")
        else:
            print(f"  ok   {name}")
    return failures


def main() -> int:
    failures = []
    print("pre-commit gate self-test\n")
    with tempfile.TemporaryDirectory() as tmp:
        failures += check_install(tmp)
        failures += check_first_commit(tmp)
        for i, (name, published, attempt, want_moved) in enumerate(CASES):
            repo = make_repo(tmp, f"case{i}", published)
            before = head(repo)
            result, want_code, wanted = attempt(repo)
            moved = head(repo) != before
            missing = [w for w in wanted if w not in result.stdout]
            if result.returncode != want_code or missing or moved != want_moved:
                failures.append(
                    f"{name}: exit={result.returncode} (want {want_code}) "
                    f"committed={moved} (want {want_moved}) missing={missing}\n{result.stdout}"
                )
                print(f"  FAIL {name}")
            else:
                print(f"  ok   {name}")

    total = len(CASES) + 5  # + check_install, check_first_commit
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
