#!/usr/bin/env python3
"""Strict comparisons of worker.py start against worker.py reviewer. Stdlib only.

For every roster: start prints exactly one line; it names the same reviewer as
`worker.py reviewer`, with that worker's family; and when the pick fails, start's
stderr holds every line that `worker.py reviewer` prints for the same failure.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"
PASS = "echo {brief}"
FAIL = "false {brief}"
PLAN = "plan: I will show it and wait for you"
NONE = "reviewer: none from another family, using a subagent"
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def run(home: Path, args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    e.pop("MAGITO_THRIFTY", None)
    e["HOME"] = str(home)
    e["MAGITO_WORKERS_FILE"] = str(home / "roster.toml")
    e.update(env or {})
    return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, text=True, env=e, cwd=str(home))


def main() -> int:
    a = ["[workers.a]", f'cmd = "{PASS}"', 'family = "openai"']
    b = ["[workers.b]", f'cmd = "{PASS}"', 'family = "google"']
    # name -> (roster lines or None for no file, extra environment, families by worker)
    cases: dict[str, tuple[list[str] | None, dict, dict]] = {
        "one working worker": (a, {}, {"a": "openai"}),
        "two workers": (a + b, {}, {"a": "openai", "b": "google"}),
        "reviewers order": (['reviewers = ["b", "a"]'] + a + b, {}, {"a": "openai", "b": "google"}),
        "reviewers set, spec_reviewer invalid": (['reviewers = ["b"]', 'spec_reviewer = "zzz"'] + a + b, {},
                                                 {"a": "openai", "b": "google"}),
        "bad thrifty with MAGITO_THRIFTY=0": (["thrifty = 3"] + a, {"MAGITO_THRIFTY": "0"}, {"a": "openai"}),
        "first fails its probe": (["[workers.x]", f'cmd = "{FAIL}"', 'family = "moonshot"'] + b, {},
                                  {"b": "google"}),
        "no roster file": (None, {}, {}),
        "not valid TOML": (["this is not toml ["], {}, {}),
        "only worker fails its probe": (["[workers.a]", f'cmd = "{FAIL}"', 'family = "openai"'], {}, {}),
        "reviewers names a missing worker": (['reviewers = ["zzz"]'] + a, {}, {}),
        "reviewers is a string": (['reviewers = "a"'] + a, {}, {}),
        "spec_reviewer names a missing worker": (['spec_reviewer = "zzz"'] + a, {}, {}),
        "spec_reviewer is a list": (['spec_reviewer = ["a"]'] + a, {}, {}),
        "thrifty is not a boolean": (["thrifty = 3"] + a, {}, {}),
        "workers is not a table": (['workers = "nope"'], {}, {}),
        "only a same-family worker": (["[workers.a]", f'cmd = "{PASS}"', 'family = "anthropic"'], {}, {}),
        "thrifty with no cheap worker": (["thrifty = true"] + a, {}, {}),
    }
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        for i, (name, (roster, env, families)) in enumerate(cases.items()):
            home = base / f"home{i}"
            home.mkdir()
            if roster is not None:
                (home / "roster.toml").write_text("\n".join(roster) + "\n")
            v = run(home, ["reviewer", "anthropic"], env)
            for label, args, who in (
                ("start --family", ["start", "--family", "anthropic"], "builder: this session (anthropic)"),
                ("start --label", ["start", "--family", "anthropic", "--label", "haiku-executor"],
                 "builder: haiku-executor (anthropic)"),
            ):
                s = run(home, args, env)
                if v.returncode == 0:
                    picked = v.stdout.strip()
                    want = f"{who} · reviewer: {picked} ({families[picked]}) · {PLAN}\n"
                else:
                    want = f"{who} · {NONE} · {PLAN}\n"
                check(s.returncode == 0 and s.stdout == want,
                      f"{label} prints exactly the expected line: {name}", f"want={want!r} got={s.stdout!r}")
                if v.returncode != 0 and roster is not None:
                    lines = [ln for ln in v.stderr.splitlines() if ln.strip()]
                    missing = [ln for ln in lines if ln not in s.stderr.splitlines()]
                    check(bool(lines) and not missing,
                          f"{label} repeats every stderr line reviewer prints: {name}",
                          f"missing={missing} start stderr={s.stderr!r}")
            if roster is None:
                s = run(home, ["start", "--family", "anthropic"], env)
                check(s.stderr.strip() == f"worker.py: no roster at {home / 'roster.toml'}: run the workers skill to create one",
                      "with no roster file, stderr is exactly the no-roster line", s.stderr)

        # --builder: the full line, with the builder's own family and a reviewer of another.
        home = base / "builder"
        home.mkdir()
        (home / "roster.toml").write_text("\n".join(a + b) + "\n")
        s = run(home, ["start", "--builder", "a", "--small"])
        check(s.returncode == 0 and s.stdout == "builder: a (openai) · reviewer: b (google) · plan: skipped, small change\n",
              "--builder prints exactly the expected line", s.stdout + s.stderr)
        v = run(home, ["reviewer", "openai"])
        check(v.returncode == 0 and v.stdout.strip() == "b", "reviewer agrees for the builder's family", v.stdout)
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
