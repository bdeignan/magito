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
        (repo.root / ".gitignore").write_text(".magito/worktrees\n")
        repo.git("add", ".gitignore")
        repo.git("commit", "-q", "-m", "ignore worktrees only")
        r = repo.add("feat/6-u")
        check(r.returncode == 0 and repo.git("status", "--short") == "",
              f"only worktrees ignored: the review marker stays hidden too (got {repo.git('status', '--short')!r})")

    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        (repo.root / ".gitignore").write_text("probe\nreview-probe\n")
        repo.git("add", ".gitignore")
        repo.git("commit", "-q", "-m", "ignore probe names")
        r = repo.add("feat/7-t")
        check(r.returncode == 0 and repo.git("status", "--short") == "",
              f"unrelated ignore rules: still excluded (got {repo.git('status', '--short')!r})")

    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        repo.exclude.write_text("*.log")  # no final newline
        r = repo.add("feat/5-v")
        lines = repo.exclude.read_text().splitlines()
        check(r.returncode == 0 and lines == ["*.log", ".magito/"],
              f"no final newline: the entry gets its own line (got {lines!r})")

    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        elsewhere = (Path(t) / "elsewhere").resolve()
        repo.git("config", "magito.worktreeDir", str(elsewhere))
        r = repo.add("feat/4-w")
        check(r.returncode == 0 and (elsewhere / "feat-4-w").is_dir(),
              f"worktreeDir: the override still wins (got {r.stdout!r})")

    # A new branch starts from the base branch, wherever the caller stands.
    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        base = repo.git("rev-parse", "main").strip()
        repo.git("checkout", "-q", "-b", "elsewhere")
        (repo.root / "stray.txt").write_text("unrelated\n")
        repo.git("add", "stray.txt")
        repo.git("commit", "-q", "-m", "unrelated work on another branch")
        r = repo.add("feat/8-s")
        wt = repo.root / ".magito/worktrees/feat-8-s"
        check(r.returncode == 0 and repo.git("rev-parse", "feat/8-s").strip() == base
              and not (wt / "stray.txt").exists(),
              f"start point: a new branch starts from the base, not from the caller's branch (stderr {r.stderr.strip()!r})")

        # --from names another start point, as a ticket branch off an integration branch.
        repo.git("branch", "integrate/0001-x", "elsewhere")
        r = subprocess.run(["bash", str(GITFLOW), "worktree", "add", "feat/9-r", "--from", "integrate/0001-x"],
                           cwd=repo.root, env=repo.env, capture_output=True, text=True)
        check(r.returncode == 0
              and repo.git("rev-parse", "feat/9-r").strip() == repo.git("rev-parse", "integrate/0001-x").strip()
              and (repo.root / ".magito/worktrees/feat-9-r/stray.txt").exists(),
              f"--from: the branch starts from the ref given (stderr {r.stderr.strip()!r})")
        r = subprocess.run(["bash", str(GITFLOW), "worktree", "add", "feat/10-q", "--from"],
                           cwd=repo.root, env=repo.env, capture_output=True, text=True)
        check(r.returncode != 0 and not (repo.root / ".magito/worktrees/feat-10-q").exists(),
              "--from with no ref: exits non-zero and creates nothing")

        # A branch already checked out in a worktree is reused: same path, nothing new,
        # and a recorded review is kept.
        marker = repo.root / ".magito/review-feat-8-s"
        check(marker.read_text() == "pending\n", "new worktree: the marker starts as pending")
        marker.write_text("abc123 reviewed by codex\n")
        before = repo.git("worktree", "list", "--porcelain")
        r = repo.add("feat/8-s")
        check(r.returncode == 0 and r.stdout.strip().splitlines()[-1:] == [str(wt)]
              and repo.git("worktree", "list", "--porcelain") == before,
              f"resume: an existing worktree is reused and its path printed (got {r.stdout!r} {r.stderr.strip()!r})")
        check(marker.read_text() == "abc123 reviewed by codex\n", "resume: a recorded review is kept")
        marker.unlink()
        r = repo.add("feat/8-s", cwd=wt)
        check(r.returncode == 0 and marker.read_text() == "pending\n",
              "resume: a missing marker is written as pending")

    # No base branch to be found: never fall back to the caller's branch.
    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        repo.git("branch", "-m", "main", "trunk")
        (repo.root / "wip.txt").write_text("caller's work\n")
        repo.git("add", "wip.txt")
        repo.git("commit", "-q", "-m", "work on the caller's branch")
        r = repo.add("feat/11-p")
        check(r.returncode != 0 and "base branch 'main' not found" in r.stderr
              and not (repo.root / ".magito/worktrees/feat-11-p").exists()
              and repo.git("branch", "--list", "feat/11-p").strip() == "",
              f"no base: exits non-zero, names the base, and creates nothing (got {r.returncode} {r.stderr.strip()!r})")
        repo.git("config", "magito.baseBranch", "trunk")
        r = repo.add("feat/11-p")
        check(r.returncode == 0 and (repo.root / ".magito/worktrees/feat-11-p/wip.txt").exists(),
              f"magito.baseBranch: the configured base is the start point (stderr {r.stderr.strip()!r})")

    if failures:
        raise SystemExit(1)
    print("test_gitflow_worktree: ok")


if __name__ == "__main__":
    main()
