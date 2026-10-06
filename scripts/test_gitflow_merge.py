#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Tests for `gitflow.sh merge` from a linked worktree.

Every `implement` branch lives in a worktree under .magito/worktrees while the main
checkout sits on the base branch. git refuses to check a branch out twice, so the merge
must run where the base branch already is. Each case runs the real script in a throwaway
repo. Stdlib only."""
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
    """A repo on main with one commit, and a reviewed branch built in a gitflow worktree."""

    def __init__(self, tmp: Path, branch: str = "feat/1-x"):
        self.root = (tmp / "repo").resolve()
        self.root.mkdir()
        self.env = dict(os.environ)
        self.env.update(
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
            GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"), GIT_CONFIG_NOSYSTEM="1",
        )
        self.git("init", "-q", "-b", "main")
        (self.root / "a.txt").write_text("a\n")
        self.git("add", "a.txt")
        self.git("commit", "-q", "-m", "chore: init")
        self.branch = branch
        out = self.flow("worktree", "add", branch, cwd=self.root).stdout
        self.worktree = Path(out.strip().splitlines()[-1])
        (self.worktree / "b.txt").write_text("b\n")
        self.git("add", "b.txt", cwd=self.worktree)
        self.git("commit", "-q", "-m", "feat: b", cwd=self.worktree)
        self.marker = self.root / ".magito" / ("review-" + branch.replace("/", "-"))
        self.marker.write_text(self.git("rev-parse", "HEAD", cwd=self.worktree).strip() + " reviewed by a\n")

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(["git", *args], cwd=cwd or self.root, env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def flow(self, *args: str, cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(GITFLOW), *args], cwd=cwd, env=self.env, capture_output=True, text=True)


def main() -> None:
    # The default strategy: a merge commit on main, made from the linked worktree.
    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        r = repo.flow("merge", cwd=repo.worktree)
        check(r.returncode == 0, f"no-ff from a worktree: exits 0 (stderr {r.stderr.strip()!r})")
        check((repo.root / "b.txt").exists(), "no-ff from a worktree: the main checkout holds the merged file")
        check(repo.git("rev-list", "--merges", "--count", "main").strip() == "1",
              "no-ff from a worktree: main has one merge commit")
        check(repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main",
              "no-ff from a worktree: the main checkout is still on main")
        check(repo.git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo.worktree).strip() == repo.branch,
              "no-ff from a worktree: the worktree is still on its branch")

    for strategy, merges in (("squash", "0"), ("ff-only", "0")):
        with tempfile.TemporaryDirectory() as t:
            repo = Repo(Path(t))
            repo.git("config", "magito.mergeStrategy", strategy)
            r = repo.flow("merge", cwd=repo.worktree)
            check(r.returncode == 0 and (repo.root / "b.txt").exists()
                  and repo.git("rev-list", "--merges", "--count", "main").strip() == merges
                  and repo.git("status", "--porcelain", "--untracked-files=no").strip() == "",
                  f"{strategy} from a worktree: lands on main with nothing left staged (stderr {r.stderr.strip()!r})")
            # Tell the two strategies apart: ff-only moves main onto the branch's own
            # commit, while squash makes a new commit with the same tree.
            tip = repo.git("rev-parse", repo.branch).strip()
            main_sha = repo.git("rev-parse", "main").strip()
            same_tree = repo.git("rev-parse", "main^{tree}") == repo.git("rev-parse", f"{repo.branch}^{{tree}}")
            if strategy == "ff-only":
                check(main_sha == tip, "ff-only from a worktree: main is the branch's own commit")
            else:
                check(main_sha != tip and same_tree,
                      "squash from a worktree: main is a new commit with the branch's tree")

    # Uncommitted changes to tracked files where the base is checked out: refuse, change nothing.
    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        before = repo.git("rev-parse", "main").strip()
        (repo.root / "a.txt").write_text("edited by hand\n")
        r = repo.flow("merge", cwd=repo.worktree)
        check(r.returncode != 0 and "uncommitted changes" in r.stderr and str(repo.root) in r.stderr
              and repo.git("rev-parse", "main").strip() == before,
              f"dirty base checkout: refuses, names that worktree, and leaves main alone (got {r.returncode} {r.stderr.strip()!r})")

    # An untracked file in the main checkout is the user's own; it does not block the merge.
    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        (repo.root / "NOTES.txt").write_text("a stray file\n")
        r = repo.flow("merge", cwd=repo.worktree)
        check(r.returncode == 0 and (repo.root / "b.txt").exists() and (repo.root / "NOTES.txt").exists(),
              f"untracked file in the base checkout: the merge still lands (stderr {r.stderr.strip()!r})")

    # The review gate still holds from a worktree.
    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        before = repo.git("rev-parse", "main").strip()
        repo.marker.write_text("pending\n")
        r = repo.flow("merge", cwd=repo.worktree)
        check(r.returncode != 0 and "magito review gate" in r.stderr and repo.git("rev-parse", "main").strip() == before,
              "pending marker: the merge is refused at the review gate")

    # A branch built by hand in the main checkout, with no worktree: the old path still works.
    with tempfile.TemporaryDirectory() as t:
        repo = Repo(Path(t))
        repo.git("checkout", "-q", "-b", "feat/2-hand")
        (repo.root / "c.txt").write_text("c\n")
        repo.git("add", "c.txt")
        repo.git("commit", "-q", "-m", "feat: c")
        r = repo.flow("merge", cwd=repo.root)
        check(r.returncode == 0 and repo.git("rev-parse", "--abbrev-ref", "HEAD").strip() == "main"
              and (repo.root / "c.txt").exists(),
              f"branch in the main checkout: merge checks out the base and lands (stderr {r.stderr.strip()!r})")

    if failures:
        raise SystemExit(1)
    print("test_gitflow_merge: ok")


if __name__ == "__main__":
    main()
