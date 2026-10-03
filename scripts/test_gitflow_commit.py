#!/usr/bin/env python3
"""Tests for `gitflow.sh commit`: it refuses, and changes nothing, when a file is
staged that the caller did not name. Issue #229.

Each case runs the real script in a throwaway repo on a feature branch. Stdlib only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "skills/general/implement/scripts/gitflow.sh"
HEADER = "gitflow.sh commit: these files are staged but were not named:"
ADVICE = "Name each one in the command to commit it, or run `git restore --staged <path>` to leave it out."
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


class Repo:
    """A repo with a.txt, b.txt, old.txt, and sub/c.txt committed on main, checked out on feat/x."""

    def __init__(self, tmp: Path):
        self.path = tmp / "repo"
        self.path.mkdir()
        self.env = dict(os.environ)
        self.env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"),
                        GIT_CONFIG_NOSYSTEM="1")
        self.git("init", "-q", "-b", "main")
        (self.path / "sub").mkdir()
        for name in ("a.txt", "b.txt", "old.txt", "sub/c.txt"):
            (self.path / name).write_text(f"{name}\n")
        self.git("add", "a.txt", "b.txt", "old.txt", "sub/c.txt")
        self.git("commit", "-q", "-m", "chore: init")
        self.git("checkout", "-q", "-b", "feat/x")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.path, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def edit(self, name: str) -> None:
        p = self.path / name
        p.write_text(p.read_text() + "changed\n" if p.exists() else f"{name} new\n")

    def flow(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(GITFLOW), *args], cwd=cwd or self.path, env=self.env,
                              capture_output=True, text=True)

    def head(self) -> str:
        return self.git("rev-parse", "HEAD")

    def staged(self) -> list[str]:
        out = subprocess.run(["git", "diff", "--cached", "--name-only", "--no-renames", "-z"],
                             cwd=self.path, env=self.env, check=True, capture_output=True, text=True).stdout
        return sorted(p for p in out.split("\0") if p)

    def committed(self) -> list[str]:
        """The paths the last commit changed."""
        out = subprocess.run(["git", "show", "--name-only", "--no-renames", "-z", "--format=", "HEAD"],
                             cwd=self.path, env=self.env, check=True, capture_output=True, text=True).stdout
        return sorted(p for p in out.split("\0") if p)


def listed(r: subprocess.CompletedProcess) -> list[str]:
    """The paths the refusal lists: the indented lines between the header and the advice."""
    lines = r.stderr.splitlines()
    if HEADER not in lines:
        return []
    out = []
    for line in lines[lines.index(HEADER) + 1:]:
        if not line.startswith("  "):
            break
        out.append(line[2:])
    return sorted(out)


def refused(r: subprocess.CompletedProcess, want: list[str]) -> bool:
    return r.returncode == 1 and listed(r) == sorted(want) and ADVICE in r.stderr


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        base = Path(t).resolve()
        n = 0

        def fresh() -> Repo:
            nonlocal n
            n += 1
            d = base / f"case{n}"
            d.mkdir()
            return Repo(d)

        # --- 1. a staged file the caller did not name: refuse, change nothing ---------------
        r = fresh()
        r.edit("a.txt")
        r.edit("stray.txt")
        r.git("add", "stray.txt")
        before = r.head()
        out = r.flow("commit", "fix: a", "a.txt")
        check(refused(out, ["stray.txt"]), "an unnamed staged file is refused and listed",
              f"exit {out.returncode} stderr={out.stderr!r}")
        check(r.head() == before, "a refusal makes no commit")
        check(r.staged() == ["stray.txt"], "a refusal leaves the index as it was: the named file is not staged",
              repr(r.staged()))

        # --- 2. nothing staged before the call: commits the named files, as today -----------
        r = fresh()
        r.edit("a.txt")
        r.edit("new.txt")
        out = r.flow("commit", "feat: a and new", "a.txt", "new.txt")
        check(out.returncode == 0 and r.committed() == ["a.txt", "new.txt"],
              "with nothing staged, the named modified and untracked files are committed",
              f"exit {out.returncode} committed={r.committed()} stderr={out.stderr!r}")

        # --- 3. every staged file is named: commits them all --------------------------------
        r = fresh()
        r.edit("a.txt")
        r.edit("b.txt")
        r.git("add", "a.txt", "b.txt")
        out = r.flow("commit", "fix: a and b", "a.txt", "b.txt")
        check(out.returncode == 0 and r.committed() == ["a.txt", "b.txt"],
              "staged files that are all named are committed",
              f"exit {out.returncode} committed={r.committed()} stderr={out.stderr!r}")

        # --- 4. from a subdirectory, with a name relative to it ------------------------------
        r = fresh()
        r.edit("sub/c.txt")
        r.git("add", "sub/c.txt")
        out = r.flow("commit", "fix: c", "c.txt", cwd=r.path / "sub")
        check(out.returncode == 0 and r.committed() == ["sub/c.txt"],
              "from a subdirectory, a relative name matches its staged file",
              f"exit {out.returncode} committed={r.committed()} stderr={out.stderr!r}")
        r = fresh()
        r.edit("sub/c.txt")
        r.edit("a.txt")
        r.git("add", "sub/c.txt", "a.txt")
        before = r.head()
        out = r.flow("commit", "fix: c", "c.txt", cwd=r.path / "sub")
        check(refused(out, ["a.txt"]) and r.head() == before,
              "from a subdirectory, a staged file in another directory is refused and listed from the root",
              f"exit {out.returncode} stderr={out.stderr!r}")

        # --- 5. a staged deletion -----------------------------------------------------------
        r = fresh()
        r.git("rm", "-q", "a.txt")
        r.edit("b.txt")
        before = r.head()
        out = r.flow("commit", "fix: b", "b.txt")
        check(refused(out, ["a.txt"]) and r.head() == before, "a staged deletion that is not named is refused",
              f"exit {out.returncode} stderr={out.stderr!r}")
        out = r.flow("commit", "chore: drop a", "a.txt")
        check(out.returncode == 0 and r.committed() == ["a.txt"] and r.staged() == [],
              "the same deletion, named, is committed",
              f"exit {out.returncode} committed={r.committed()} stderr={out.stderr!r}")

        # --- 6. a staged rename is two paths --------------------------------------------------
        r = fresh()
        r.git("mv", "old.txt", "new.txt")
        before = r.head()
        out = r.flow("commit", "refactor: rename", "new.txt")
        check(refused(out, ["old.txt"]) and r.head() == before,
              "after git mv, naming only the new path is refused and lists the old path",
              f"exit {out.returncode} stderr={out.stderr!r}")
        out = r.flow("commit", "refactor: rename", "old.txt", "new.txt")
        check(out.returncode == 0 and r.committed() == ["new.txt", "old.txt"],
              "after git mv, naming both paths commits the rename",
              f"exit {out.returncode} committed={r.committed()} stderr={out.stderr!r}")

        # --- 7. a name with a space -----------------------------------------------------------
        r = fresh()
        r.edit("a.txt")
        r.edit("my file.txt")
        r.git("add", "my file.txt")
        out = r.flow("commit", "fix: a", "a.txt")
        check(refused(out, ["my file.txt"]), "a staged name with a space is listed whole on one line",
              f"exit {out.returncode} stderr={out.stderr!r}")
        out = r.flow("commit", "feat: a and my file", "a.txt", "my file.txt")
        check(out.returncode == 0 and r.committed() == ["a.txt", "my file.txt"],
              "a staged name with a space, named, is committed",
              f"exit {out.returncode} committed={r.committed()} stderr={out.stderr!r}")

        # --- names stay literal: a glob does not stand in for the file it would match ---------
        r = fresh()
        r.edit("a.txt")
        r.edit("x1.txt")
        r.git("add", "x1.txt")
        out = r.flow("commit", "fix: a", "a.txt", "x*.txt")
        check(out.returncode == 1 and r.staged() == ["x1.txt"],
              "a glob name does not count as naming the staged file it would match",
              f"exit {out.returncode} stderr={out.stderr!r}")

    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
