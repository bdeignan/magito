#!/usr/bin/env python3
"""Probe-count tests for worker.py: which workers a command starts, and how often.

Each fake worker appends one line to a log every time it is started, so a test can
tell a worker that was passed over from one that was probed. Stdlib only.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def setup(home: Path, top: list[str], workers: list[tuple[str, str, list[str]]]) -> Path:
    """Write a roster of logging fake workers. Returns the log path."""
    log = home / "starts.log"
    fake = home / "fake.py"
    fake.write_text("import sys\n"
                    f"open({str(log)!r}, 'a').write(sys.argv[1] + '\\n')\n"
                    "print(sys.argv[-1])\n")
    lines = list(top)
    for name, family, extra in workers:
        lines += [f"[workers.{name}]", f'cmd = "{sys.executable} {fake} {name} {{brief}}"',
                  f'family = "{family}"', *extra]
    (home / ".magito").mkdir(parents=True, exist_ok=True)
    (home / ".magito" / "workers.toml").write_text("\n".join(lines) + "\n")
    return log


def run(home: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    for k in ("MAGITO_THRIFTY", "MAGITO_WORKERS_FILE"):
        env.pop(k, None)
    env["HOME"] = str(home)
    return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, text=True,
                          env=env, cwd=str(home))


def starts(log: Path) -> list[str]:
    return log.read_text().split() if log.exists() else []


def main() -> int:
    abc = [("a", "openai", []), ("b", "google", []), ("c", "moonshot", [])]
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()

        home = base / "skip"
        home.mkdir()
        log = setup(home, [], abc)
        r = run(home, ["reviewer", "anthropic", "--skip", "a"])
        check(r.stdout.strip() == "b" and starts(log) == ["b"],
              "reviewer --skip never starts the skipped worker", f"stdout={r.stdout!r} starts={starts(log)}")

        home = base / "invalid"
        home.mkdir()
        log = setup(home, [], [("a", "openai", ['requires_env = ["MAGITO_TEST_UNSET_VAR"]']), ("b", "google", [])])
        r = run(home, ["reviewer", "anthropic"])
        check(r.stdout.strip() == "b" and starts(log) == ["b"],
              "reviewer never starts a worker whose required variable is missing",
              f"stdout={r.stdout!r} starts={starts(log)}")

        home = base / "family"
        home.mkdir()
        log = setup(home, [], abc)
        r = run(home, ["ready", "--family", "anthropic"])
        check(r.stdout.splitlines()[-1] == "reviewer for anthropic: a" and starts(log) == ["a", "b", "c"],
              "ready --family probes each worker once and does not probe the pick again",
              f"stdout={r.stdout!r} starts={starts(log)}")

        home = base / "ranked"
        home.mkdir()
        log = setup(home, ['reviewers = ["c", "a"]'], abc)
        r = run(home, ["ready", "--family", "anthropic"])
        check(r.stdout.splitlines()[-1] == "reviewer for anthropic: c" and starts(log) == ["a", "b", "c"],
              "ready --family with a reviewers list still probes each worker once",
              f"stdout={r.stdout!r} starts={starts(log)}")

        # A {model} placeholder with a model that is not a string is one entry's fault.
        home = base / "model"
        home.mkdir()
        log = setup(home, [], [("b", "google", [])])
        roster = home / ".magito" / "workers.toml"
        roster.write_text('[workers.a]\ncmd = "echo {model} {brief}"\nmodel = 3\nfamily = "openai"\n'
                          + roster.read_text())
        r = run(home, ["reviewer", "anthropic"])
        check(r.returncode == 0 and r.stdout.strip() == "b"
              and "worker.py: skip a: invalid entry (model is not a string)" in r.stderr,
              "reviewer skips an entry whose model is not a string and goes on", r.stdout + r.stderr)
        r = run(home, ["ready"])
        check(r.returncode == 0 and r.stdout.splitlines()[0] == "a: invalid entry (model is not a string)",
              "ready reports an entry whose model is not a string", r.stdout + r.stderr)

        # A fault in a top-level setting is reported with and without --family.
        for setting, word in (('reviewers = "a"', "reviewers"), ("thrifty = 3", "thrifty"),
                              ('spec_reviewer = "zzz"', "spec_reviewer")):
            home = base / f"top-{word}"
            home.mkdir()
            setup(home, [setting], abc)
            r = run(home, ["ready"])
            check(r.returncode == 0 and len(r.stdout.splitlines()) == 4 and word in r.stderr,
                  f"ready without --family names a bad {word} on stderr and still reports every worker",
                  r.stdout + r.stderr)
            r = run(home, ["ready", "--family", "anthropic"])
            check(r.returncode == 0 and r.stdout.splitlines()[-1] == "reviewer for anthropic: none"
                  and r.stderr.count(f"{word} ") == 1,
                  f"ready --family names a bad {word} once and prints reviewer none", r.stdout + r.stderr)
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
