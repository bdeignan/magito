#!/usr/bin/env python3
"""More tests for `gitflow.sh commit`. Issue #229.

test_gitflow_commit.py was committed before the code and is locked, so cases found
later live here. The rule under test: a name counts as naming a staged file however
the caller spells its path, so the refusal never fires on a file that was named.
Each case also runs under /bin/bash, which is bash 3.2 on macOS. Stdlib only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "skills/general/implement/scripts/gitflow.sh"
SHELLS = ["bash"] + (["/bin/bash"] if Path("/bin/bash").exists() else [])
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def repo(base: Path, name: str) -> tuple[Path, dict]:
    path = base / name
    path.mkdir()
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=str(base / f"{name}.gitconfig"),
               GIT_CONFIG_NOSYSTEM="1")

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=path, env=env, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    (path / "sub").mkdir()
    for f in ("a.txt", "sub/c.txt"):
        (path / f).write_text(f"{f}\n")
    git("add", "a.txt", "sub/c.txt")
    git("commit", "-q", "-m", "chore: init")
    git("checkout", "-q", "-b", "feat/x")
    for f in ("a.txt", "sub/c.txt"):
        (path / f).write_text(f"{f} changed\n")
    git("add", "a.txt", "sub/c.txt")
    return path, env


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        base = Path(t).resolve()
        n = 0
        for shell in SHELLS:
            # Both files are staged. Each spelling names both, so each commit must go through.
            spellings = (
                ("a ./ prefix", lambda p: ["./a.txt", "./sub/c.txt"], lambda p: p),
                ("absolute paths", lambda p: [str(p / "a.txt"), str(p / "sub/c.txt")], lambda p: p),
                ("a ../ name from a subdirectory", lambda p: ["../a.txt", "c.txt"], lambda p: p / "sub"),
            )
            for label, names, where in spellings:
                n += 1
                path, env = repo(base, f"r{n}")
                r = subprocess.run([shell, str(GITFLOW), "commit", "fix: both", *names(path)],
                                   cwd=where(path), env=env, capture_output=True, text=True)
                left = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=path, env=env,
                                      capture_output=True, text=True).stdout
                check(r.returncode == 0 and left == "",
                      f"{shell}: staged files named with {label} are committed",
                      f"exit {r.returncode} stderr={r.stderr!r} still staged={left!r}")
            # A directory names no file: naming `sub` or `sub/` leaves sub/c.txt unnamed.
            for dirname in ("sub", "sub/"):
                n += 1
                path, env = repo(base, f"r{n}")
                r = subprocess.run([shell, str(GITFLOW), "commit", "fix: a", "a.txt", dirname], cwd=path,
                                   env=env, capture_output=True, text=True)
                check(r.returncode == 1 and "\n  sub/c.txt\n" in r.stderr,
                      f"{shell}: naming the directory {dirname!r} does not name the staged file inside it",
                      f"exit {r.returncode} {r.stderr!r}")
            # The refusal itself, under this shell.
            n += 1
            path, env = repo(base, f"r{n}")
            r = subprocess.run([shell, str(GITFLOW), "commit", "fix: a", "a.txt"], cwd=path, env=env,
                               capture_output=True, text=True)
            check(r.returncode == 1 and "\n  sub/c.txt\n" in r.stderr,
                  f"{shell}: an unnamed staged file is refused and listed", f"exit {r.returncode} {r.stderr!r}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
