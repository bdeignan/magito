#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Strict checks for the commit test in gitflow.sh, beside test_gitflow_ahead.py:
the exact dirty-tree output, the local branch winning over origin, and the full
text of the gate's advice. Issue #216. Stdlib only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "skills/general/implement/scripts/gitflow.sh"
HOOK = ROOT / "hooks/review-gate.py"
ADVICE = ("python3 <skills>/implement/scripts/worker.py record <worktree> <builder-family> "
          "<reviewer|subagent>")
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t).resolve()
        repo = tmp / "repo"
        repo.mkdir()
        env = dict(os.environ)
        env.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
                   GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"), GIT_CONFIG_NOSYSTEM="1", GH_LOG=str(tmp / "gh.log"))
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "gh").write_text("#!/usr/bin/env bash\nprintf x > \"$GH_LOG\"\necho https://example.invalid/pull/1\n")
        (bin_dir / "gh").chmod(0o755)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"

        def git(*args: str) -> str:
            return subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True,
                                  text=True).stdout.rstrip("\n")

        def commit(name: str) -> None:
            (repo / name).write_text(name + "\n")
            git("add", name)
            git("commit", "-q", "-m", f"feat: {name}")

        def flow(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(["bash", str(GITFLOW), *args], cwd=repo, env=env, capture_output=True, text=True)

        git("init", "-q", "-b", "main")
        commit("a.txt")
        with open(repo / ".git" / "info" / "exclude", "a") as f:
            f.write(".magito/\n")

        # --- the local branch wins over origin/<base> when both exist -------------------------
        # origin/main sits one commit behind local main. Against local main the feature
        # branch is 1 ahead; against origin/main it would be 2.
        git("update-ref", "refs/remotes/origin/main", git("rev-parse", "HEAD"))
        commit("b.txt")
        git("checkout", "-q", "-b", "feat/1-x")
        commit("c.txt")
        out = flow("ahead")
        check(out.returncode == 0 and out.stdout == "1\n",
              "ahead counts against the local base, not origin, when both exist", out.stdout + out.stderr)
        out = flow("ahead", "main")
        check(out.stdout == "1\n", "ahead main does the same with the base named", out.stdout + out.stderr)
        git("branch", "-m", "main", "trunk-local")
        out = flow("ahead", "main")
        check(out.returncode == 0 and out.stdout == "2\n",
              "with no local branch of that name, ahead main counts against origin/main", out.stdout + out.stderr)
        git("branch", "-m", "trunk-local", "main")

        # --- the dirty-tree output, exactly --------------------------------------------------------
        (repo / "stray one.txt").write_text("x\n")
        (repo / "c.txt").write_text("changed\n")
        (repo / "d.txt").write_text("new\n")
        git("add", "d.txt")
        porcelain = git("status", "--porcelain")
        for verb, args in (("ahead", ["ahead"]), ("push", ["push"]), ("pr", ["pr", "1", "fix: x", "Why: y."])):
            out = flow(*args)
            want = f"working tree dirty — commit or discard every change before {verb}\n{porcelain}\n"
            check(out.returncode == 1 and out.stdout == "" and out.stderr == want,
                  f"{verb} on a dirty tree prints the header ending in `{verb}`, then the porcelain lines, and nothing else",
                  f"want={want!r} got={out.stderr!r}")
        check(len(porcelain.splitlines()) == 3, "the dirty tree in this test has three porcelain lines", porcelain)
        git("checkout", "-q", "--", "c.txt")
        git("rm", "-q", "-f", "--cached", "d.txt")
        (repo / "d.txt").unlink()
        (repo / "stray one.txt").unlink()

        # --- the gate's advice, in full ---------------------------------------------------------------
        (repo / ".magito").mkdir()
        (repo / ".magito" / "review-feat-1-x").write_text("pending\n")
        out = flow("pr", "1", "fix: x", "Why: y.")
        lines = out.stderr.splitlines()
        check(out.returncode == 1 and f"Review the branch, then record it: {ADVICE}" in lines
              and "Do not record 'reviewed' unless a review actually ran." in lines
              and "reviewing-changes" not in out.stderr and not (tmp / "gh.log").exists(),
              "the gate prints the whole record command with its three arguments", out.stderr)
    hook = " ".join(part.strip().strip('"') for part in HOOK.read_text().splitlines())
    check(f"Review the branch, then record it: {ADVICE.split(' <reviewer')[0]}" in hook.replace('  ', ' ')
          and "<reviewer|subagent>" in hook and "reviewing-changes skill" not in hook,
          "the hook's advice holds the whole record command with its three arguments")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
