#!/usr/bin/env python3
"""Tests for `gitflow.sh worktree add`: by default a worktree lives inside the
repo at .magito/worktrees/<branch-slug>, and git never sees it. Issue #209.

Each case runs the real script in a throwaway repo. Stdlib only."""
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "skills/general/implement/scripts/gitflow.sh"

failures: list[str] = []


def check(ok: bool, label: str) -> None:
    if not ok:
        failures.append(label)
        print(f"FAIL: {label}")


class Repo:
    def __init__(self, tmp: Path):
        self.root = (tmp / "repo").resolve()
        self.root.mkdir()
        self.root = self.root.resolve()
        self.env = dict(os.environ)
        self.env.update(
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
            GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"), GIT_CONFIG_NOSYSTEM="1",
        )
        self.git("init", "-q", "-b", "main")
        (self.root / "a.txt").write_text("a\n")
        self.git("add", "a.txt")
        self.git("commit", "-q", "-m", "init")
        self.exclude = self.root / ".git/info/exclude"
        self.exclude.write_text("# git ls-files --others --exclude-from=.git/info/exclude\n")

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(["git", *args], cwd=cwd or self.root, env=self.env,
                              check=True, capture_output=True, text=True).stdout

    def add(self, branch: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(GITFLOW), "worktree", "add", branch], cwd=cwd or self.root,
                              env=self.env, capture_output=True, text=True)


def exclude_count(repo: Repo) -> int:
    return [line.strip() for line in repo.exclude.read_text().splitlines()].count(".magito/")


def main() -> None:
    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        r = repo.add("feat/1-x")
        want = repo.root / ".magito/worktrees/feat-1-x"
        check(r.returncode == 0, f"default: exits 0 (stderr {r.stderr.strip()!r})")
        check(r.stdout.strip().splitlines()[-1:] == [str(want)], f"default: prints {want} (got {r.stdout!r})")
        check((want / "a.txt").exists(), "default: the worktree is checked out there")
        check(exclude_count(repo) == 1, "default: .magito/ is added to .git/info/exclude")
        check(repo.git("status", "--short") == "", f"default: main checkout stays clean (got {repo.git('status', '--short')!r})")

        # A second worktree, created from inside the first, still lands under the main root.
        r = repo.add("feat/2-y", cwd=want if want.is_dir() else repo.root)
        want2 = repo.root / ".magito/worktrees/feat-2-y"
        check(r.returncode == 0 and want2.is_dir(), f"nested call: lands under the main root (got {r.stdout!r})")
        check(exclude_count(repo) == 1, "second add: the exclude line is not duplicated")
        check(repo.git("status", "--short") == "", "second add: main checkout stays clean")

        r = subprocess.run(["bash", str(GITFLOW), "worktree", "remove", str(want)], cwd=repo.root,
                           env=repo.env, capture_output=True, text=True)
        check(r.returncode == 0 and not want.exists(), f"remove: the worktree is gone (stderr {r.stderr.strip()!r})")

    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        (repo.root / ".gitignore").write_text(".magito/\n")
        repo.git("add", ".gitignore")
        repo.git("commit", "-q", "-m", "ignore")
        before = repo.exclude.read_text()
        r = repo.add("feat/3-z")
        check(r.returncode == 0, "gitignored: exits 0")
        check(repo.exclude.read_text() == before, "gitignored: .git/info/exclude is left alone")

    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        elsewhere = (Path(t) / "elsewhere").resolve()
        repo.git("config", "magito.worktreeDir", str(elsewhere))
        r = repo.add("feat/4-w")
        check(r.returncode == 0 and (elsewhere / "feat-4-w").is_dir(),
              f"worktreeDir: the override still wins (got {r.stdout!r})")

    if failures:
        raise SystemExit(1)
    print("test_gitflow_worktree: ok")


if __name__ == "__main__":
    main()
