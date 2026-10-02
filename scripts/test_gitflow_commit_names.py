#!/usr/bin/env python3
"""Tests for `gitflow.sh commit` with file names that hold a line break. Issue #229.

test_gitflow_commit.py is locked; these cases came from review. A name with a line
break must never match part of another name, and the refusal still prints one line
per path. Each case runs under bash and under /bin/bash (3.2 on macOS). Stdlib only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "skills/general/implement/scripts/gitflow.sh"
HEADER = "gitflow.sh commit: these files are staged but were not named:"
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
    run = lambda *a: subprocess.run(["git", *a], cwd=path, env=env, check=True, capture_output=True)
    run("init", "-q", "-b", "main")
    (path / "a.txt").write_text("a\n")
    run("add", "a.txt")
    run("commit", "-q", "-m", "chore: init")
    run("checkout", "-q", "-b", "feat/x")
    # Two staged files: `foo`, and a name made of `foo`, a line break, and `bar`.
    (path / "foo").write_text("foo\n")
    (path / "foo\nbar").write_text("foo bar\n")
    run("add", "--", "foo", "foo\nbar")
    return path, env


def staged(path: Path, env: dict) -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "-z"], cwd=path, env=env,
                         capture_output=True, text=True).stdout
    return sorted(p for p in out.split("\0") if p)


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        base = Path(t).resolve()
        for i, shell in enumerate(SHELLS):
            # Naming only the line-break name must not count as naming `foo`.
            path, env = repo(base, f"a{i}")
            r = subprocess.run([shell, str(GITFLOW), "commit", "fix: one", "foo\nbar"], cwd=path, env=env,
                               capture_output=True, text=True)
            lines = r.stderr.splitlines()
            listed = lines[lines.index(HEADER) + 1:-1] if HEADER in lines else []
            check(r.returncode == 1 and listed == ["  foo"] and staged(path, env) == ["foo", "foo\nbar"],
                  f"{shell}: a name with a line break does not stand in for a shorter staged name",
                  f"exit {r.returncode} stderr={r.stderr!r}")
            # Naming only `foo`: the line-break name is listed on one line, quoted.
            path, env = repo(base, f"b{i}")
            r = subprocess.run([shell, str(GITFLOW), "commit", "fix: one", "foo"], cwd=path, env=env,
                               capture_output=True, text=True)
            lines = r.stderr.splitlines()
            listed = lines[lines.index(HEADER) + 1:-1] if HEADER in lines else []
            check(r.returncode == 1 and listed == ["  $'foo\\nbar'"],
                  f"{shell}: a staged name with a line break is listed on one line",
                  f"exit {r.returncode} stderr={r.stderr!r}")
            # Naming both commits both.
            path, env = repo(base, f"c{i}")
            r = subprocess.run([shell, str(GITFLOW), "commit", "fix: both", "foo", "foo\nbar"], cwd=path,
                               env=env, capture_output=True, text=True)
            check(r.returncode == 0 and staged(path, env) == [],
                  f"{shell}: naming both commits both", f"exit {r.returncode} stderr={r.stderr!r}")
        for i, shell in enumerate(SHELLS):
            # A name that ends in a line break, named exactly, is committed: no step may strip it.
            path, env = repo(base, f"d{i}")
            (path / "end\n").write_text("end\n")
            subprocess.run(["git", "add", "--", "end\n"], cwd=path, env=env, check=True, capture_output=True)
            r = subprocess.run([shell, str(GITFLOW), "commit", "fix: all", "foo", "foo\nbar", "end\n"],
                               cwd=path, env=env, capture_output=True, text=True)
            check(r.returncode == 0 and staged(path, env) == [],
                  f"{shell}: a staged name that ends in a line break, named exactly, is committed",
                  f"exit {r.returncode} stderr={r.stderr!r}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
