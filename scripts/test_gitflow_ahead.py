#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Tests for the commit test in gitflow.sh: `ahead`, and the clean-tree and
commit-count checks in `push` and `pr`. Issue #216.

Each case runs the real script in a throwaway repo, with a fake `gh` first on PATH
that records its arguments instead of opening a pull request. Stdlib only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "skills/general/implement/scripts/gitflow.sh"
HOOK = ROOT / "hooks/review-gate.py"
TITLE = "fix(gitflow): count commits"
BODY = "**Why:** a test.\n\n**What:** a test."
DIRTY = "working tree dirty — commit or discard every change before"
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


class Repo:
    """A repo on `main` with one commit, a bare remote named origin, and a fake gh."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.path = tmp / "repo"
        self.path.mkdir()
        self.env = dict(os.environ)
        self.env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"),
                        GIT_CONFIG_NOSYSTEM="1", GH_LOG=str(tmp / "gh.log"))
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text("#!/usr/bin/env bash\nprintf '%s\\0' \"$@\" > \"$GH_LOG\"\n"
                                    "echo https://example.invalid/pull/1\n")
        (bin_dir / "gh").chmod(0o755)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{self.env['PATH']}"
        self.git("init", "-q", "-b", "main")
        self.commit("a.txt", "chore: init")
        subprocess.run(["git", "init", "-q", "--bare", str(tmp / "origin.git")], env=self.env, check=True)
        self.git("remote", "add", "origin", str(tmp / "origin.git"))
        # .magito/ holds the review marker; gitflow.sh worktree add excludes it the same way.
        (self.path / ".git" / "info").mkdir(exist_ok=True)
        with open(self.path / ".git" / "info" / "exclude", "a") as f:
            f.write(".magito/\n")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.path, env=self.env, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, name: str, message: str) -> None:
        (self.path / name).write_text(f"{name}\n")
        self.git("add", name)
        self.git("commit", "-q", "-m", message)

    def flow(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(GITFLOW), *args], cwd=self.path, env=self.env,
                              capture_output=True, text=True)

    def gh_called(self) -> bool:
        return (self.tmp / "gh.log").exists()

    def marker(self, branch: str, text: str) -> None:
        d = self.path / ".magito"
        d.mkdir(exist_ok=True)
        (d / f"review-{branch.replace('/', '-')}").write_text(text + "\n")


def fresh(base: Path, name: str) -> Repo:
    d = base / name
    d.mkdir()
    return Repo(d)


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        base = Path(t).resolve()

        # --- ahead counts commits the base lacks ----------------------------------------------
        r = fresh(base, "count")
        r.git("checkout", "-q", "-b", "feat/1-x")
        out = r.flow("ahead")
        check(out.returncode == 0 and out.stdout == "0\n", "ahead prints 0 on a branch with no commit ahead",
              out.stdout + out.stderr)
        r.commit("b.txt", "feat: b")
        out = r.flow("ahead")
        check(out.returncode == 0 and out.stdout == "1\n", "ahead prints 1 with one commit ahead and a clean tree",
              out.stdout + out.stderr)
        r.commit("c.txt", "feat: c")
        out = r.flow("ahead")
        check(out.stdout == "2\n", "ahead prints 2 with two commits ahead", out.stdout + out.stderr)

        # --- ahead <base> counts against the branch given ---------------------------------------
        r.git("checkout", "-q", "-b", "integrate/x")
        r.git("checkout", "-q", "-b", "feat/2-y")
        r.commit("d.txt", "feat: d")
        out = r.flow("ahead", "integrate/x")
        check(out.returncode == 0 and out.stdout == "1\n", "ahead <base> counts against the branch given",
              out.stdout + out.stderr)
        out = r.flow("ahead")
        check(out.stdout == "3\n", "ahead with no argument counts against the default base", out.stdout)
        out = r.flow("ahead", "no-such-branch")
        check(out.returncode == 1 and out.stdout == "" and "base branch 'no-such-branch' not found" in out.stderr,
              "ahead with a base that does not exist exits 1", out.stdout + out.stderr)
        r.git("update-ref", "refs/remotes/origin/trunk", r.git("rev-parse", "integrate/x"))
        out = r.flow("ahead", "trunk")
        check(out.returncode == 0 and out.stdout == "1\n",
              "ahead falls back to origin/<base> when no local branch has that name", out.stdout + out.stderr)
        r.git("config", "magito.baseBranch", "integrate/x")
        out = r.flow("ahead")
        check(out.stdout == "1\n", "ahead with no argument honors magito.baseBranch", out.stdout + out.stderr)

        # --- ahead refuses the base branch itself -------------------------------------------------
        r = fresh(base, "onbase")
        out = r.flow("ahead")
        check(out.returncode == 1 and out.stdout == "" and "refusing to operate on 'main'" in out.stderr,
              "ahead on the base branch exits 1 with the existing message", out.stdout + out.stderr)

        # --- a dirty tree stops ahead, push, and pr ----------------------------------------------
        for kind in ("an untracked file", "a modified tracked file", "a staged change"):
            r = fresh(base, f"dirty-{kind.split()[1]}")
            r.git("checkout", "-q", "-b", "feat/1-x")
            r.commit("b.txt", "feat: b")
            if kind == "an untracked file":
                (r.path / "stray.txt").write_text("x\n")
                seen = "stray.txt"
            elif kind == "a modified tracked file":
                (r.path / "b.txt").write_text("changed\n")
                seen = "b.txt"
            else:
                (r.path / "b.txt").write_text("changed\n")
                r.git("add", "b.txt")
                seen = "b.txt"
            r.marker("feat/1-x", "pending")
            for verb, args in (("ahead", ["ahead"]), ("push", ["push"]), ("pr", ["pr", "1", TITLE, BODY])):
                out = r.flow(*args)
                check(out.returncode == 1 and out.stdout == "" and DIRTY in out.stderr and seen in out.stderr
                      and "review gate" not in out.stderr,
                      f"{verb} with {kind} exits 1, says the tree is dirty, and lists the file",
                      out.stdout + out.stderr)
            check(not r.gh_called(), f"gh is never called with {kind}")
            check(r.git("ls-remote", "origin") == "", f"nothing is pushed with {kind}")

        # --- pr refuses a branch with no commit ahead ---------------------------------------------
        r = fresh(base, "nocommit")
        r.git("checkout", "-q", "-b", "feat/1-x")
        r.marker("feat/1-x", "pending")
        out = r.flow("pr", "1", TITLE, BODY)
        check(out.returncode == 1 and "gitflow.sh pr: no commit ahead of 'main'" in out.stderr
              and "nothing to open; report the findings instead" in out.stderr
              and "review gate" not in out.stderr and not r.gh_called(),
              "pr with no commit ahead exits 1 before the review gate and never calls gh", out.stdout + out.stderr)
        out = r.flow("pr", "1", TITLE, "")
        check(out.returncode == 1 and "no commit ahead" in out.stderr,
              "the commit count is checked before the body", out.stderr)

        # --- the order in pr: dirty tree, commit count, review decision, body, title ---------------
        r = fresh(base, "order")
        r.git("checkout", "-q", "-b", "feat/1-x")
        r.commit("b.txt", "feat: b")
        r.marker("feat/1-x", "pending")
        out = r.flow("pr", "1", "not a conventional title", "")
        check(out.returncode == 1 and "magito review gate" in out.stderr and "worker.py record" in out.stderr
              and "reviewing-changes" not in out.stderr and not r.gh_called(),
              "with a commit and a clean tree, pr stops at the review gate, whose advice names worker.py record",
              out.stderr)
        check("Do not record 'reviewed' unless a review actually ran." in out.stderr,
              "the gate keeps its warning against recording a review that did not run", out.stderr)
        r.marker("feat/1-x", f"{r.git('rev-parse', 'HEAD')} reviewed by a")
        out = r.flow("pr", "1", TITLE, "")
        check(out.returncode == 1 and "the body is empty" in out.stderr, "then the empty body is refused", out.stderr)
        out = r.flow("pr", "1", "not a conventional title", BODY)
        check(out.returncode == 1 and "does not match magito.prTitlePattern" in out.stderr,
              "then a bad title is refused", out.stderr)
        out = r.flow("pr", "1", TITLE, BODY)
        check(out.returncode == 0 and r.gh_called(), "and a clean, reviewed branch with a commit opens the pull request",
              out.stdout + out.stderr)

        # --- pr counts against magito.baseBranch when it is set ------------------------------------
        r = fresh(base, "basebranch")
        r.git("checkout", "-q", "-b", "develop")
        r.commit("dev.txt", "feat: dev")
        r.git("checkout", "-q", "-b", "feat/1-x")
        r.git("config", "magito.baseBranch", "develop")
        out = r.flow("pr", "1", TITLE, BODY)
        check(out.returncode == 1 and "no commit ahead of 'develop'" in out.stderr and not r.gh_called(),
              "pr counts against magito.baseBranch, the same base ahead uses", out.stderr)

        # --- push on a clean tree still pushes -------------------------------------------------------
        r = fresh(base, "push")
        r.git("checkout", "-q", "-b", "feat/1-x")
        r.commit("b.txt", "feat: b")
        out = r.flow("push")
        check(out.returncode == 0 and "refs/heads/feat/1-x" in r.git("ls-remote", "origin"),
              "push on a clean tree pushes the branch", out.stdout + out.stderr)

        # --- usage ------------------------------------------------------------------------------------
        out = r.flow("nonsense")
        check(out.returncode == 1 and "ahead [base]" in out.stderr, "the usage line lists ahead [base]", out.stderr)

    hook = HOOK.read_text()
    check("worker.py record" in hook and "Run the reviewing-changes skill" not in hook
          and "Do not record 'reviewed' unless a review actually ran." in hook,
          "the hook's advice names worker.py record and no longer names reviewing-changes")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
