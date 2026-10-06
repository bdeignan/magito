#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Tests for worker.py record: the one command that writes a review record. Stdlib only.

Each case uses a real git repo, a real worktree made by gitflow.sh worktree add (which
writes the `pending` marker), and a roster named through MAGITO_WORKERS_FILE.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts"
WORKER = SCRIPTS / "worker.py"
GITFLOW = SCRIPTS / "gitflow.sh"
PASS = "echo {brief}"
FAIL = "false {brief}"
RESULTS: list[bool] = []
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True,
                          env=os.environ | GIT_ENV).stdout.strip()


class Repo:
    """A repo with one linked worktree on feat/9-thing, made by gitflow.sh worktree add."""

    def __init__(self, base: Path, name: str):
        self.home = base / name
        self.root = self.home / "repo"
        self.root.mkdir(parents=True)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "commit", "-q", "--allow-empty", "-m", "base")
        out = subprocess.run(["bash", str(GITFLOW), "worktree", "add", "feat/9-thing"], cwd=self.root,
                             capture_output=True, text=True, check=True, env=os.environ | GIT_ENV).stdout
        self.worktree = Path(out.strip().splitlines()[-1])
        (self.worktree / "f.txt").write_text("x\n")
        git(self.worktree, "add", "f.txt")
        git(self.worktree, "commit", "-q", "-m", "feat: thing")
        self.marker = self.root / ".magito" / "review-feat-9-thing"
        self.sha = git(self.worktree, "rev-parse", "HEAD")
        self.roster = self.home / "roster.toml"

    def set_roster(self, lines: list[str] | None) -> None:
        if lines is None:
            self.roster.unlink(missing_ok=True)
        else:
            self.roster.write_text("\n".join(lines) + "\n")

    def reset(self) -> None:
        self.marker.write_text("pending\n")

    def run(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        e = dict(os.environ)
        e.pop("MAGITO_THRIFTY", None)
        e["HOME"] = str(self.home)
        e["MAGITO_WORKERS_FILE"] = str(self.roster)
        e.update(env or {})
        return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, text=True, env=e,
                              cwd=str(self.home))

    def pending(self) -> bool:
        return self.marker.read_text() == "pending\n"


def main() -> int:
    a = ["[workers.a]", f'cmd = "{PASS}"', 'family = "openai"']
    b = ["[workers.b]", f'cmd = "{PASS}"', 'family = "google"']
    same = ["[workers.s]", f'cmd = "{PASS}"', 'family = "Anthropic"']
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        repo = Repo(base, "main")
        wt = str(repo.worktree)
        check(repo.pending(), "gitflow.sh worktree add leaves the marker as pending")

        # --- recording a roster worker ------------------------------------------------------
        repo.set_roster(a + b + same + ["[workers.nofam]", f'cmd = "{PASS}"',
                                        "[workers.blank]", f'cmd = "{PASS}"', 'family = ""',
                                        "[workers.num]", f'cmd = "{PASS}"', "family = 3"])
        r = repo.run("record", wt, "anthropic", "a")
        check(r.returncode == 0 and repo.marker.read_text() == f"{repo.sha} reviewed by a\n"
              and r.stdout == f"{repo.marker}\n{repo.sha} reviewed by a\n",
              "a worker of another family is recorded as `<sha> reviewed by <name>`", r.stdout + r.stderr)
        check(repo.marker.read_text().split()[0] == git(repo.worktree, "rev-parse", "HEAD"),
              "the first word of the marker equals HEAD, so the gate accepts the branch")
        check(not (repo.worktree / ".magito").exists(),
              "the marker is written in the main worktree, never inside the linked worktree")
        # A stub `gh` first on PATH, so the gate is exercised and no real pull request can open.
        stub = base / "bin"
        stub.mkdir()
        (stub / "gh").write_text("#!/bin/sh\necho https://example.invalid/pull/1\n")
        (stub / "gh").chmod(0o755)
        gate = subprocess.run(["bash", str(GITFLOW), "pr", "9", "feat: thing", "Why: a test."], cwd=wt,
                              capture_output=True, text=True,
                              env=os.environ | GIT_ENV | {"PATH": f"{stub}:{os.environ['PATH']}"})
        check(gate.returncode == 0 and "magito review gate" not in gate.stderr,
              "gitflow.sh pr passes the review gate after a record", gate.stdout + gate.stderr)
        repo.reset()
        gate = subprocess.run(["bash", str(GITFLOW), "pr", "9", "feat: thing", "Why: a test."], cwd=wt,
                              capture_output=True, text=True,
                              env=os.environ | GIT_ENV | {"PATH": f"{stub}:{os.environ['PATH']}"})
        check(gate.returncode != 0 and "magito review gate" in gate.stderr,
              "gitflow.sh pr stops at the review gate while the marker is pending", gate.stdout + gate.stderr)

        for name, why in (("s", "same family"), ("zzz", "no worker"), ("nofam", "family"),
                          ("blank", "family"), ("num", "family")):
            repo.reset()
            r = repo.run("record", wt, "anthropic", name)
            check(r.returncode == 2 and r.stdout == "" and why in r.stderr and repo.pending(),
                  f"recording `{name}` exits 2, says why ({why}), and leaves the marker pending",
                  f"code={r.returncode} {r.stdout!r} {r.stderr!r}")

        # --- recording a subagent: refused while a roster reviewer answers -------------------
        repo.reset()
        repo.set_roster(a + b)
        r = repo.run("record", wt, "anthropic", "subagent")
        check(r.returncode == 6 and r.stdout == "" and repo.pending()
              and "worker.py: a (openai) answers its probe: review with it, not a subagent" in r.stderr,
              "a subagent record is refused with exit 6 while a worker of another family answers",
              f"code={r.returncode} {r.stdout!r} {r.stderr!r}")

        # --- recording a subagent: written whenever the pick fails ---------------------------
        failing = {
            "no roster file": None,
            "a roster that is not valid TOML": ["this is not toml ["],
            "other-family workers that all fail their probes": [
                "[workers.a]", f'cmd = "{FAIL}"', 'family = "openai"',
                "[workers.b]", f'cmd = "{FAIL}"', 'family = "google"'],
            "a reviewers list that names a missing worker": ['reviewers = ["zzz"]'] + a,
            "only a same-family worker": same,
            "an other-family entry named subagent": ["[workers.subagent]", f'cmd = "{PASS}"', 'family = "openai"'],
            "thrifty with no cheap worker": ["thrifty = true"] + a,
        }
        for name, roster in failing.items():
            repo.reset()
            repo.set_roster(roster)
            v = repo.run("reviewer", "anthropic")
            r = repo.run("record", wt, "anthropic", "subagent")
            check(v.returncode != 0 and r.returncode == 0
                  and repo.marker.read_text() == f"{repo.sha} reviewed by subagent\n"
                  and r.stdout == f"{repo.marker}\n{repo.sha} reviewed by subagent\n",
                  f"a subagent record is written with {name}", f"code={r.returncode} {r.stdout!r} {r.stderr!r}")
            if v.returncode == 2:
                want = [ln for ln in v.stderr.splitlines() if ln.strip()]
                check(bool(want) and all(ln in r.stderr.splitlines() for ln in want),
                      f"record repeats the fault that reviewer prints with {name}", f"{v.stderr!r} vs {r.stderr!r}")

        # --- record subagent refuses exactly when reviewer names a worker --------------------
        agree = dict(failing)
        agree.update({
            "one working worker": a,
            "reviewers order": ['reviewers = ["b", "a"]'] + a + b,
            "first fails its probe": ["[workers.x]", f'cmd = "{FAIL}"', 'family = "moonshot"'] + b,
            "reviewers set, spec_reviewer invalid": ['reviewers = ["b"]', 'spec_reviewer = "zzz"'] + a + b,
        })
        families = {"a": "openai", "b": "google"}
        for name, roster in agree.items():
            repo.reset()
            repo.set_roster(roster)
            v = repo.run("reviewer", "anthropic")
            r = repo.run("record", wt, "anthropic", "subagent")
            if v.returncode == 0:
                picked = v.stdout.strip()
                ok = (r.returncode == 6 and repo.pending()
                      and f"worker.py: {picked} ({families[picked]}) answers its probe: review with it, not a subagent"
                      in r.stderr)
            else:
                ok = r.returncode == 0 and repo.marker.read_text() == f"{repo.sha} reviewed by subagent\n"
            check(ok, f"record subagent agrees with reviewer: {name}",
                  f"reviewer={v.returncode} {v.stdout!r} record={r.returncode} {r.stderr!r}")

        # --- a branch with no marker ------------------------------------------------------------
        repo.set_roster(a)
        plain = base / "plain-worktree"
        git(repo.root, "worktree", "add", "-q", "-b", "feat/10-by-hand", str(plain))
        r = repo.run("record", str(plain), "anthropic", "a")
        hand = repo.root / ".magito" / "review-feat-10-by-hand"
        check(r.returncode == 2 and r.stdout == "" and not hand.exists()
              and "no review marker for feat/10-by-hand: create the branch with gitflow.sh worktree add" in r.stderr,
              "a branch with no marker exits 2 and no marker is created", f"{r.returncode} {r.stderr!r}")
        r = repo.run("record", str(plain), "anthropic", "subagent")
        check(r.returncode == 2 and not hand.exists(), "the same holds for a subagent record", r.stderr)

        # --- the worktree argument, and usage ---------------------------------------------------
        repo.reset()
        outside = base / "not-a-repo"
        outside.mkdir()
        for label, args in (("a path that does not exist", ["record", str(base / "missing"), "anthropic", "a"]),
                            ("a directory outside any git repo", ["record", str(outside), "anthropic", "a"]),
                            ("too few arguments", ["record", wt, "anthropic"]),
                            ("too many arguments", ["record", wt, "anthropic", "a", "extra"])):
            r = repo.run(*args)
            check(r.returncode == 2 and r.stdout == "" and r.stderr.strip() != "" and "Traceback" not in r.stderr
                  and repo.pending(),
                  f"{label} exits 2 with a message", f"code={r.returncode} {r.stdout!r} {r.stderr!r}")

        # --- the sha follows HEAD ---------------------------------------------------------------
        (repo.worktree / "g.txt").write_text("y\n")
        git(repo.worktree, "add", "g.txt")
        git(repo.worktree, "commit", "-q", "-m", "fix: more")
        new = git(repo.worktree, "rev-parse", "HEAD")
        r = repo.run("record", wt, "anthropic", "a")
        check(new != repo.sha and repo.marker.read_text() == f"{new} reviewed by a\n",
              "a record after a new commit names the new commit", r.stdout + r.stderr)
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
