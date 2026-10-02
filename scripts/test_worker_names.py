#!/usr/bin/env python3
"""Roster worker names that are not one word: empty, with a space, with a line break.

Such an entry is invalid everywhere: the reviewer pick skips it, ready gives it one line,
and record refuses to write it, so the review record stays one line. Stdlib only.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts"
WORKER = SCRIPTS / "worker.py"
GITFLOW = SCRIPTS / "gitflow.sh"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
BAD = ['""', '"two words"', '"line\\nbreak"', '" padded"']
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp).resolve()
        root = home / "repo"
        root.mkdir()
        env = os.environ | GIT_ENV
        subprocess.run(["git", "-C", str(root), "init", "-q", "-b", "main"], check=True, env=env)
        subprocess.run(["git", "-C", str(root), "commit", "-q", "--allow-empty", "-m", "base"], check=True, env=env)
        out = subprocess.run(["bash", str(GITFLOW), "worktree", "add", "feat/1-names"], cwd=root, check=True,
                             capture_output=True, text=True, env=env).stdout
        worktree = out.strip().splitlines()[-1]
        marker = root / ".magito" / "review-feat-1-names"
        roster = home / "roster.toml"

        def run(*args: str) -> subprocess.CompletedProcess:
            e = dict(os.environ)
            e.pop("MAGITO_THRIFTY", None)
            e["HOME"] = str(home)
            e["MAGITO_WORKERS_FILE"] = str(roster)
            return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, text=True,
                                  env=e, cwd=str(home))

        only_bad = []
        for key in BAD:
            only_bad += [f"[workers.{key}]", 'cmd = "echo {brief}"', 'family = "openai"']
        good = ["[workers.good]", 'cmd = "echo {brief}"', 'family = "google"']

        # Only badly named workers of another family: the pick finds no one.
        roster.write_text("\n".join(only_bad) + "\n")
        v = run("reviewer", "anthropic")
        check(v.returncode == 3 and v.stdout == "", "reviewer never picks a worker whose name is not one word",
              f"{v.returncode} {v.stdout!r} {v.stderr!r}")
        s = run("start", "--family", "anthropic")
        check(s.returncode == 0 and s.stdout.count("\n") == 1
              and "reviewer: none from another family, using a subagent" in s.stdout,
              "start falls back to a subagent for such a roster", s.stdout + s.stderr)
        r = run("ready", "--family", "anthropic")
        lines = r.stdout.splitlines()
        check(r.returncode == 0 and len(lines) == len(BAD) + 2
              and all("invalid entry (the name must be one word" in ln for ln in lines[:len(BAD)])
              and lines[-1] == "reviewer for anthropic: none",
              "ready gives each badly named entry exactly one line", r.stdout + r.stderr)
        r = run("record", worktree, "anthropic", "subagent")
        check(r.returncode == 0 and marker.read_text().endswith(" reviewed by subagent\n")
              and marker.read_text().count("\n") == 1,
              "record subagent agrees with reviewer: no worker, so the record is written", r.stdout + r.stderr)

        # Recording a badly named worker is refused, and the marker stays one line.
        for name in ("", "two words", "line\nbreak", " padded"):
            marker.write_text("pending\n")
            r = run("record", worktree, "anthropic", name)
            check(r.returncode == 2 and r.stdout == "" and marker.read_text() == "pending\n"
                  and "invalid entry" in r.stderr and "Traceback" not in r.stderr,
                  f"record refuses the worker name {name!r}", f"{r.returncode} {r.stdout!r} {r.stderr!r}")

        # With a well named worker beside them, the pick goes to that worker.
        roster.write_text("\n".join(only_bad + good) + "\n")
        marker.write_text("pending\n")
        v = run("reviewer", "anthropic")
        r = run("record", worktree, "anthropic", "subagent")
        check(v.returncode == 0 and v.stdout.strip() == "good" and r.returncode == 6
              and "good (google) answers its probe" in r.stderr and marker.read_text() == "pending\n",
              "a well named worker is still picked, and a subagent record is still refused",
              f"{v.stdout!r} {r.returncode} {r.stderr!r}")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
