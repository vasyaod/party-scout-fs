#!/usr/bin/env python3
"""Install this repo's git hooks. Git never does this for you on clone.

Points `core.hooksPath` at the tracked `hooks/` directory, so the gate travels
with the repo instead of living in an untracked `.git/hooks/` copy that drifts.
`core.hooksPath` is per-clone local config: every fresh clone — every agent
working in a scratch checkout — has to run this once.

    python3 tools/install_hooks.py             # install
    python3 tools/install_hooks.py --check     # is it actually active? exit 1 if not
    python3 tools/install_hooks.py --uninstall

`--check` answers "is it wired up", not "does it work" — that is what
`python3 tools/test_pre_commit_validate.py` proves, by making real commits.

Caveat worth knowing before you run it: `core.hooksPath` replaces `.git/hooks`
wholesale, so any other hook you keep there stops firing in this clone.
"""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = "hooks"  # relative: git resolves it from the working tree root
HOOK_NAMES = ("pre-commit",)
INSTALL = "python3 tools/install_hooks.py"


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def configured() -> str | None:
    result = git("config", "--get", "core.hooksPath")
    return result.stdout.strip() if result.returncode == 0 else None


def active() -> tuple[bool, str]:
    """(is the gate live in this clone, why not)."""
    path = configured()
    if not path:
        return False, "core.hooksPath is not set"
    resolved = path if os.path.isabs(path) else os.path.join(ROOT, path)
    if os.path.realpath(resolved) != os.path.realpath(os.path.join(ROOT, HOOKS)):
        return False, f"core.hooksPath={path!r}, not {HOOKS}/"
    for name in HOOK_NAMES:
        hook = os.path.join(resolved, name)
        if not os.path.exists(hook):
            return False, f"{HOOKS}/{name} is missing"
        if not os.access(hook, os.X_OK):
            return False, f"{HOOKS}/{name} is not executable"
    return True, ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report whether the hooks are active")
    parser.add_argument("--uninstall", action="store_true", help="unset core.hooksPath")
    args = parser.parse_args(argv)

    if args.check:
        ok, why = active()
        print(f"hooks active: {', '.join(HOOK_NAMES)}" if ok else f"hooks NOT active — {why}\nrun: {INSTALL}")
        return 0 if ok else 1

    if args.uninstall:
        git("config", "--unset", "core.hooksPath")
        print("core.hooksPath unset — this clone no longer runs the pre-commit gate")
        return 0

    for name in HOOK_NAMES:
        hook = os.path.join(ROOT, HOOKS, name)
        mode = os.stat(hook).st_mode
        os.chmod(hook, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    result = git("config", "core.hooksPath", HOOKS)
    if result.returncode != 0:
        print(f"could not set core.hooksPath: {result.stderr.strip()}", file=sys.stderr)
        return 1

    ok, why = active()
    if not ok:
        print(f"install ran but the hooks are still not active — {why}", file=sys.stderr)
        return 1
    print(
        f"core.hooksPath -> {HOOKS}/\n"
        f"installed: {', '.join(HOOK_NAMES)}\n"
        "every commit touching data/ or scripts/ is now validated first "
        "(tools/pre_commit_validate.py)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
