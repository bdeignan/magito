#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Tests for worker.py next-reviewer subcommand (issue #262). Stdlib only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"
PASSING = 'cmd = "echo {brief}"'
FAILING = 'cmd = "false {brief}"'


def run(home: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("MAGITO_THRIFTY", None)
    env.pop("MAGITO_WORKERS_FILE", None)
    env["HOME"] = str(home)
    return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, text=True, env=env)


def case(name: str, roster: list[str] | None, args: list[str], expected_stdout: str | None,
         expected_code: int) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        if roster is not None:
            (home / ".magito").mkdir()
            (home / ".magito" / "workers.toml").write_text("\n".join(roster) + "\n", encoding="utf-8")
        r = run(home, args)
        reviewer = run(home, ["reviewer", args[1]]) if expected_stdout == "SAME_AS_REVIEWER" else None
    want = reviewer.stdout.strip() if reviewer else expected_stdout
    ok = r.returncode == expected_code and (want is None or r.stdout.strip() == want)
    if reviewer is not None:
        ok = ok and reviewer.returncode == 0 and want != ""
    print(f"{'ok' if ok else 'not ok'} - {name}")
    if not ok:
        print(f"    expected code={expected_code} stdout={want!r}")
        print(f"    got code={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r}")
    return ok


def main() -> int:
    two_openai = [
        "[workers.a]", PASSING, 'family = "openai"',
        "[workers.b]", PASSING, 'family = "openai"',
    ]
    results = [
        # 1. No failed worker: the same name `reviewer` prints.
        case("no failed worker matches reviewer", two_openai,
             ["next-reviewer", "anthropic"], "SAME_AS_REVIEWER", 0),
        case("no failed worker prints the first pick", two_openai,
             ["next-reviewer", "anthropic"], "a", 0),
        # 2. The first pick failed: the next working worker of another family.
        case("first pick failed, next one printed", two_openai,
             ["next-reviewer", "anthropic", "--failed", "a"], "b", 0),
        case("same-family worker is never the next pick", [
            "[workers.a]", PASSING, 'family = "openai"',
            "[workers.c]", PASSING, 'family = "anthropic"',
            "[workers.b]", PASSING, 'family = "google"',
        ], ["next-reviewer", "anthropic", "--failed", "a"], "b", 0),
        # 3. Every other-family worker failed, but one answers its probe again.
        case("all failed, one answers again", two_openai,
             ["next-reviewer", "anthropic", "--failed", "a", "--failed", "b"], "a", 0),
        case("all failed, only the one that answers is printed", [
            "[workers.a]", FAILING, 'family = "openai"',
            "[workers.b]", PASSING, 'family = "openai"',
        ], ["next-reviewer", "anthropic", "--failed", "a", "--failed", "b"], "b", 0),
        # 4. No worker of another family answers at all.
        case("no other-family worker answers", [
            "[workers.a]", FAILING, 'family = "openai"',
            "[workers.c]", PASSING, 'family = "anthropic"',
        ], ["next-reviewer", "anthropic", "--failed", "a"], "subagent", 0),
        # 5. Edge cases: no roster, and usage errors.
        case("no roster file prints subagent", None,
             ["next-reviewer", "anthropic"], "subagent", 0),
        case("--failed with no name exits 2", two_openai,
             ["next-reviewer", "anthropic", "--failed"], None, 2),
        case("--failed followed by another option exits 2", two_openai,
             ["next-reviewer", "anthropic", "--failed", "--failed", "a"], None, 2),
        case("roster error exits 2", ["[workers.a", PASSING],
             ["next-reviewer", "anthropic"], None, 2),
    ]
    failed = results.count(False)
    print(f"{len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
