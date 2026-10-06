#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
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


def roster_path(home: Path) -> Path:
    """The roster lives away from the default path and is named through
    MAGITO_WORKERS_FILE. The default path holds a decoy, so a test passes only
    when the variable selects the roster."""
    return home / "elsewhere" / "roster.toml"


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
    roster_path(home).parent.mkdir(parents=True, exist_ok=True)
    roster_path(home).write_text("\n".join(lines) + "\n")
    (home / ".magito").mkdir(parents=True, exist_ok=True)
    (home / ".magito" / "workers.toml").write_text(
        f'[workers.decoy]\ncmd = "{sys.executable} {fake} decoy {{brief}}"\nfamily = "decoyfamily"\n')
    return log


def run(home: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("MAGITO_THRIFTY", None)
    env["HOME"] = str(home)
    env["MAGITO_WORKERS_FILE"] = str(roster_path(home))
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
        roster = roster_path(home)
        roster.write_text('[workers.a]\ncmd = "echo {model} {brief}"\nmodel = 3\nfamily = "openai"\n'
                          + roster.read_text())
        r = run(home, ["reviewer", "anthropic"])
        check(r.returncode == 0 and r.stdout.strip() == "b"
              and "worker.py: skip a: invalid entry (model is not a string)" in r.stderr,
              "reviewer skips an entry whose model is not a string and goes on", r.stdout + r.stderr)
        r = run(home, ["ready"])
        check(r.returncode == 0 and r.stdout.splitlines()[0] == "a: invalid entry (model is not a string)",
              "ready reports an entry whose model is not a string", r.stdout + r.stderr)

        # MAGITO_WORKERS_FILE selects the roster: the decoy at the default path never shows.
        home = base / "selected"
        home.mkdir()
        log = setup(home, [], abc)
        r = run(home, ["ready", "--family", "anthropic"])
        check(r.returncode == 0 and "decoy" not in r.stdout and "decoy" not in starts(log)
              and r.stdout.splitlines()[0].startswith("a: family=openai"),
              "ready reads the roster that MAGITO_WORKERS_FILE names, not the default path",
              r.stdout + r.stderr)
        r = run(home, ["workers"])
        check(r.stdout == "a\nb\nc\n", "workers reads the roster that MAGITO_WORKERS_FILE names", r.stdout)

        # --skip needs a name, and only reviewer takes it.
        home = base / "usage"
        home.mkdir()
        log = setup(home, [], abc)
        for args in (["reviewer", "anthropic", "--skip", "--skip"],
                     ["reviewer", "anthropic", "--skip", "a", "--skip"],
                     ["reviewer", "anthropic", "a"],
                     ["probe", "a", "--skip", "a"],
                     ["workers", "--skip", "a"],
                     ["thrifty", "--skip", "a"],
                     ["ready", "--skip", "a"]):
            r = run(home, args)
            check(r.returncode == 2 and r.stdout == "", f"`{' '.join(args)}` exits 2 and prints nothing",
                  f"code={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r}")
        check(starts(log) == [], "a rejected command line starts no worker", f"starts={starts(log)}")

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
