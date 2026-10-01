#!/usr/bin/env python3
"""A roster path that exists but cannot be read as a file. Stdlib only.

worker.py start must still print its line with the subagent fallback and exit 0, and
worker.py reviewer must exit 2 with a message, never a traceback.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"
NONE = "reviewer: none from another family, using a subagent"


def run(roster: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("MAGITO_THRIFTY", None)
    env["HOME"] = str(roster.parent)
    env["MAGITO_WORKERS_FILE"] = str(roster)
    return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, text=True,
                          env=env, cwd=str(roster.parent))


def main() -> int:
    results = []

    def check(ok: bool, label: str, r: subprocess.CompletedProcess) -> None:
        print(f"{'ok' if ok else 'not ok'} - {label}")
        if not ok:
            print(f"    code={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r}")
        results.append(ok)

    with tempfile.TemporaryDirectory() as tmp:
        roster = Path(tmp).resolve() / "roster-is-a-directory"
        roster.mkdir()
        r = run(roster, ["start", "--family", "anthropic"])
        check(r.returncode == 0 and r.stdout == f"builder: this session (anthropic) · {NONE} · "
              "plan: I will show it and wait for you\n"
              and "cannot be read" in r.stderr and "Traceback" not in r.stderr,
              "start with a directory at the roster path prints the fallback and exits 0", r)
        r = run(roster, ["reviewer", "anthropic"])
        check(r.returncode == 2 and r.stdout == "" and "cannot be read" in r.stderr
              and "Traceback" not in r.stderr,
              "reviewer with a directory at the roster path exits 2 with a message", r)
        r = run(roster, ["start", "--builder", "a"])
        check(r.returncode == 2 and r.stdout == "" and "cannot be read" in r.stderr
              and "Traceback" not in r.stderr,
              "start --builder with a directory at the roster path exits 2 with a message", r)
        r = run(roster, ["ready"])
        check(r.returncode == 2 and "Traceback" not in r.stderr,
              "ready with a directory at the roster path exits 2 with a message", r)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
