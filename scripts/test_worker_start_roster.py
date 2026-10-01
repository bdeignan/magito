#!/usr/bin/env python3
"""Hard inputs for worker.py start. Stdlib only.

A roster path that exists but cannot be read as a file: start must still print its line
with the subagent fallback and exit 0, and reviewer must exit 2 with a message, never a
traceback. And values that hold a line break or nothing at all: start prints exactly one
line or none.
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

        # stdout is exactly one line, whatever a value or the roster holds.
        roster = Path(tmp).resolve() / "roster.toml"
        roster.write_text('[workers.a]\ncmd = "echo {brief}"\nfamily = "open\\nai"\n')
        for label, args in (("a label with a line break", ["start", "--family", "anthropic", "--label", "two\nlines"]),
                            ("a family with a line break", ["start", "--family", "anth\nropic"]),
                            ("a builder with a line break", ["start", "--builder", "a\nb"]),
                            ("an empty label", ["start", "--family", "anthropic", "--label", ""]),
                            ("an empty family", ["start", "--family", ""])):
            r = run(roster, args)
            check(r.returncode == 2 and r.stdout == "", f"{label} exits 2 and prints no line", r)
        r = run(roster, ["start", "--family", "anthropic"])
        check(r.returncode == 0 and r.stdout.count("\n") == 1 and r.stdout.endswith("\n")
              and " · reviewer: a (open ai) · " in r.stdout,
              "a roster family that holds a line break still gives one line", r)
        odd = Path(tmp).resolve() / "odd\nname.md"
        odd.write_text("Status: accepted\n")
        r = run(roster, ["start", "--family", "anthropic", "--intent", str(odd)])
        check(r.returncode == 2 and r.stdout == "", "an intent path with a line break exits 2", r)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
