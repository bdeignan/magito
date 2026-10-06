#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Tests for `worker.py review`: one command runs a review round, proves the
reviewer changed no files, and prints only the verdict lines. Issue #209.

Each case runs the real worker.py against a throwaway repo, with a fake worker
whose behavior the brief selects. Stdlib only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "skills/general/implement/scripts/worker.py"

# The brief's first line picks the mode. Like Codex, the fake echoes the brief
# back before it answers, and prints its final answer twice.
FAKE = r'''
import sys
from pathlib import Path
brief = sys.argv[1]
mode = brief.splitlines()[0]
print("workdir: .")
print(brief)
answer = {
    "pass": "VERDICT PASS",
    "fix": "- VERDICT FIX: `a.py:3` \u2014 the test runs one hook\n`COVERAGE PASS`",
    "none": "Looks good to me.",
    "fail": "VERDICT PASS",
}.get(mode, "VERDICT PASS")
if mode == "tracked":
    Path("a.txt").write_text("changed\n")
if mode == "untracked":
    Path("new.txt").write_text("new\n")
if mode == "chmod":
    Path("a.txt").chmod(0o755)
if mode == "slow":
    Path("a.txt").write_text("changed\n")
    print("partial answer", flush=True)
    import time
    time.sleep(30)
if mode == "log":
    # Like Codex: exploration on stderr (here a file quoting a verdict), the answer on stdout.
    print("exec cat worker-contract.md\nVERDICT PASS\n", file=sys.stderr)
    print("VERDICT FIX: a real finding")
    sys.exit(0)
if mode == "scratch":
    Path(".scratch").mkdir(exist_ok=True)
    Path(".scratch/draft.md").write_text("edited\n")
if mode == "cache":
    # What running Python tests leaves behind: never part of the change.
    Path("pkg/__pycache__").mkdir(parents=True, exist_ok=True)
    Path("pkg/__pycache__/m.cpython-311.pyc").write_bytes(b"\x00cache")
    Path(".pytest_cache/v/cache").mkdir(parents=True, exist_ok=True)
    Path(".pytest_cache/v/cache/lastfailed").write_text("{}\n")
if mode == "notes":
    Path("pkg").mkdir(exist_ok=True)
    Path("pkg/notes.txt").write_text("a note\n")
if mode == "cachename":
    # A file named like the cache folder, not inside one, is an ordinary change.
    Path("__pycache__.txt").write_text("not a cache\n")
if mode == "env":
    import os
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        answer = "VERDICT FIX: PYTHONDONTWRITEBYTECODE is not set to 1"
print(answer)
print(answer)
sys.exit(7 if mode == "fail" else 0)
'''

# The reply format quotes verdict lines, so the echoed brief holds some too.
BRIEF_TAIL = "\nReply format:\nVERDICT PASS\nVERDICT FIX: <finding>\nCOVERAGE PASS\n"

failures: list[str] = []


def check(ok: bool, label: str) -> None:
    if not ok:
        failures.append(label)
        print(f"FAIL: {label}")


def review(mode: str, timeout: str | None = None) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = tmp / "repo"
        repo.mkdir()
        env = dict(os.environ)
        env.update(
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
            GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"), GIT_CONFIG_NOSYSTEM="1",
        )
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, env=env, check=True)
        (repo / "a.txt").write_text("a\n")
        subprocess.run(["git", "add", "a.txt"], cwd=repo, env=env, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, env=env, check=True)
        (repo / ".git/info/exclude").write_text(".scratch/\n")
        (repo / ".scratch").mkdir()
        (repo / ".scratch/draft.md").write_text("draft\n")

        fake = tmp / "fake.py"
        fake.write_text(FAKE)
        roster = tmp / "workers.toml"
        roster.write_text(f'[workers.fake]\ncmd = "{sys.executable} {fake} {{brief}}"\nfamily = "openai"\n')
        env["MAGITO_WORKERS_FILE"] = str(roster)
        env.pop("MAGITO_THRIFTY", None)
        brief = tmp / "brief.md"
        brief.write_text(mode + BRIEF_TAIL)

        result = subprocess.run(
            [sys.executable, str(WORKER), "review", "fake", str(repo), str(brief)] + ([timeout] if timeout else []),
            capture_output=True, text=True, env=env,
        )
        # The saved output must outlive the call; read it before the temp dir goes.
        saved = [line.split(": ", 1)[1] for line in result.stderr.splitlines() if line.startswith("review output: ")]
        result.saved_text = Path(saved[0]).read_text() if saved and Path(saved[0]).exists() else None
        return result


def main() -> None:
    r = review("pass")
    check(r.returncode == 0, f"pass: exits 0 (got {r.returncode}, stderr {r.stderr.strip()!r})")
    check(r.stdout == "VERDICT PASS\n", f"pass: prints the verdict once, not the brief's copy (got {r.stdout!r})")
    check(r.saved_text is not None and "workdir: ." in r.saved_text, "pass: full output is saved and its path printed")

    r = review("fix")
    check(r.returncode == 0, f"fix: exits 0 (got {r.returncode})")
    check(r.stdout == "VERDICT FIX: `a.py:3` \u2014 the test runs one hook\nCOVERAGE PASS\n",
          f"fix: bullets and backticks are stripped, each line printed once (got {r.stdout!r})")

    for mode, path in (("tracked", "a.txt"), ("chmod", "a.txt"), ("untracked", "new.txt"), ("scratch", ".scratch/draft.md")):
        r = review(mode)
        check(r.returncode == 4, f"{mode}: a changed file exits 4 (got {r.returncode})")
        check(path in r.stdout + r.stderr, f"{mode}: names the changed file {path}")
        check("VERDICT" not in r.stdout, f"{mode}: prints no verdict to act on (got {r.stdout!r})")

    r = review("cache")
    check(r.returncode == 0 and r.stdout == "VERDICT PASS\n",
          f"cache: __pycache__ and .pytest_cache files do not void the round (got {r.returncode}, "
          f"stdout {r.stdout!r}, stderr {r.stderr.strip()!r})")

    for mode, path in (("notes", "pkg/notes.txt"), ("cachename", "__pycache__.txt")):
        r = review(mode)
        check(r.returncode == 4, f"{mode}: a file outside a cache folder still exits 4 (got {r.returncode})")
        check(path in r.stdout + r.stderr, f"{mode}: names the changed file {path}")

    r = review("env")
    check(r.returncode == 0 and r.stdout == "VERDICT PASS\n",
          f"env: the reviewer runs with PYTHONDONTWRITEBYTECODE=1 (got {r.stdout!r})")

    r = review("log")
    check(r.returncode == 0 and r.stdout == "VERDICT FIX: a real finding\n",
          f"log: a verdict quoted in stderr noise is ignored (got {r.returncode}, {r.stdout!r})")

    r = review("slow", timeout="2")
    check(r.returncode == 4, f"slow: a reviewer that edits a file and times out exits 4, not 124 (got {r.returncode})")
    check(r.saved_text is not None and "partial answer" in r.saved_text, "slow: the output before the timeout is saved")

    r = review("none")
    check(r.returncode == 5, f"none: no verdict line exits 5 (got {r.returncode})")

    r = review("fail")
    check(r.returncode == 7, f"fail: the worker's own exit code passes through (got {r.returncode})")

    if failures:
        raise SystemExit(1)
    print("test_worker_review: ok")


if __name__ == "__main__":
    main()
