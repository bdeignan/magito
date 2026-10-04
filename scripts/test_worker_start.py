#!/usr/bin/env python3
"""Tests for worker.py start: the one line that opens a run. Stdlib only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"
PASS = "echo {brief}"
FAIL = "false {brief}"
NONE = "reviewer: none from another family, using a subagent"
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def run(home: Path, args: list[str], roster: list[str] | None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run worker.py with the roster named through MAGITO_WORKERS_FILE. roster=None leaves
    that file missing. A decoy at the default path proves the variable selects the roster."""
    path = home / "elsewhere" / "roster.toml"
    if roster is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(roster) + "\n", encoding="utf-8")
    (home / ".magito").mkdir(parents=True, exist_ok=True)
    (home / ".magito" / "workers.toml").write_text(f'[workers.decoy]\ncmd = "{PASS}"\nfamily = "decoyfamily"\n')
    e = dict(os.environ)
    e.pop("MAGITO_THRIFTY", None)
    e["HOME"] = str(home)
    e["MAGITO_WORKERS_FILE"] = str(path)
    e.update(env or {})
    return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, text=True, env=e, cwd=str(home))


def one_line(r: subprocess.CompletedProcess) -> bool:
    return r.stdout.endswith("\n") and r.stdout.count("\n") == 1


def main() -> int:
    a_openai = ["[workers.a]", f'cmd = "{PASS}"', 'family = "openai"']
    b_google = ["[workers.b]", f'cmd = "{PASS}"', 'family = "google"']
    rosters: dict[str, list[str] | None] = {
        "one working worker of another family": a_openai,
        "two workers": a_openai + b_google,
        "no roster file": None,
        "not valid TOML": ["this is not toml ["],
        "only other-family worker fails its probe": ["[workers.a]", f'cmd = "{FAIL}"', 'family = "openai"'],
        "reviewers names a missing worker": ['reviewers = ["zzz"]'] + a_openai,
        "reviewers set, spec_reviewer invalid": ['reviewers = ["b"]', 'spec_reviewer = "zzz"'] + a_openai + b_google,
        "spec_reviewer names a missing worker": ['spec_reviewer = "zzz"'] + a_openai,
        "thrifty is not a boolean": ["thrifty = 3"] + a_openai,
        "workers is not a table": ['workers = "nope"'],
        "only a same-family worker": ["[workers.a]", f'cmd = "{PASS}"', 'family = "anthropic"'],
        "thrifty with no cheap worker": ["thrifty = true"] + a_openai,
        "an entry named subagent only": ["[workers.subagent]", f'cmd = "{PASS}"', 'family = "openai"'],
    }
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        n = 0

        def home() -> Path:
            nonlocal n
            n += 1
            h = base / f"home{n}"
            h.mkdir()
            return h

        # --- the line, and the fallback for every failed pick -------------------------------
        r = run(home(), ["start", "--family", "anthropic"], a_openai)
        check(r.returncode == 0
              and r.stdout == "builder: this session (anthropic) · reviewer: a (openai) · plan: I will show it and wait for you\n",
              "a working worker of another family is named in one line", r.stdout + r.stderr)

        h = home()
        r = run(h, ["start", "--family", "anthropic"], None)
        check(r.returncode == 0 and one_line(r) and f" · {NONE} · " in r.stdout
              and f"worker.py: no roster at {h / 'elsewhere' / 'roster.toml'}: run the workers skill to create one" in r.stderr,
              "no roster file: exit 0, the fallback text, and stderr names the missing path", r.stdout + r.stderr)

        for name, needle in (("not valid TOML", "is not valid TOML"),
                             ("only other-family worker fails its probe", "passed its probe"),
                             ("reviewers names a missing worker", "reviewers names 'zzz'"),
                             ("spec_reviewer names a missing worker", "spec_reviewer 'zzz'"),
                             ("thrifty is not a boolean", "thrifty in"),
                             ("workers is not a table", "'workers' in"),
                             ("thrifty with no cheap worker", "thrifty mode: no cheap reviewer")):
            r = run(home(), ["start", "--family", "anthropic"], rosters[name])
            check(r.returncode == 0 and one_line(r) and f" · {NONE} · " in r.stdout and needle in r.stderr,
                  f"{name}: exit 0, the fallback text, and the fault on stderr", r.stdout + r.stderr)

        r = run(home(), ["start", "--family", "anthropic"], rosters["reviewers set, spec_reviewer invalid"])
        check(r.returncode == 0 and " · reviewer: b (google) · " in r.stdout,
              "an invalid spec_reviewer is ignored when reviewers is set", r.stdout + r.stderr)
        r = run(home(), ["start", "--family", "anthropic"], rosters["thrifty is not a boolean"],
                env={"MAGITO_THRIFTY": "0"})
        check(r.returncode == 0 and " · reviewer: a (openai) · " in r.stdout,
              "MAGITO_THRIFTY in the environment decides before a bad roster thrifty value", r.stdout + r.stderr)

        # --- start and reviewer agree on every roster ------------------------------------------
        for name, roster in rosters.items():
            h = home()
            s = run(h, ["start", "--family", "anthropic"], roster)
            v = run(h, ["reviewer", "anthropic"], roster)
            picked = v.stdout.strip() if v.returncode == 0 else None
            want = f" · reviewer: {picked} (" if picked else f" · {NONE} · "
            check(s.returncode == 0 and one_line(s) and want in s.stdout,
                  f"start agrees with reviewer: {name}", f"start={s.stdout!r} reviewer={v.returncode} {v.stdout!r}")

        # --- the builder part -------------------------------------------------------------------
        r = run(home(), ["start", "--family", "anthropic", "--label", "executor"], a_openai)
        check(r.returncode == 0 and r.stdout.startswith("builder: executor (anthropic) · reviewer: a (openai) · "),
              "--label names a builder that is not this session", r.stdout + r.stderr)
        r = run(home(), ["start", "--builder", "a"], a_openai + b_google)
        check(r.returncode == 0 and one_line(r)
              and r.stdout.startswith("builder: a (openai) · reviewer: b (google) · "),
              "--builder names the worker, and the reviewer has another family", r.stdout + r.stderr)
        r = run(home(), ["start", "--builder", "a"], ['reviewers = ["zzz"]'] + a_openai)
        check(r.returncode == 0 and r.stdout.startswith(f"builder: a (openai) · {NONE} · ") and "zzz" in r.stderr,
              "--builder resolves first; a fault in the pick then gives the fallback", r.stdout + r.stderr)
        for label, args, roster in (
            ("--builder with a name the roster lacks", ["start", "--builder", "zzz"], a_openai),
            ("--builder with no roster file", ["start", "--builder", "a"], None),
            ("--builder with a roster that is not valid TOML", ["start", "--builder", "a"], ["nope ["]),
            ("--builder whose family is the number 3", ["start", "--builder", "a"],
             ["[workers.a]", f'cmd = "{PASS}"', "family = 3"]),
            ("--builder whose family is the empty string", ["start", "--builder", "a"],
             ["[workers.a]", f'cmd = "{PASS}"', 'family = ""']),
            ("--builder whose family is absent", ["start", "--builder", "a"], ["[workers.a]", f'cmd = "{PASS}"']),
            ("--label together with --builder", ["start", "--builder", "a", "--label", "x"], a_openai),
            ("--family together with --builder", ["start", "--family", "anthropic", "--builder", "a"], a_openai),
            ("neither --family nor --builder", ["start"], a_openai),
            ("--label with no --family", ["start", "--label", "x"], a_openai),
            ("--family with no value", ["start", "--family"], a_openai),
            ("--intent with no value", ["start", "--family", "anthropic", "--intent"], a_openai),
            ("an unknown option", ["start", "--family", "anthropic", "--nope"], a_openai),
            ("a stray argument", ["start", "--family", "anthropic", "stray"], a_openai),
        ):
            r = run(home(), args, roster)
            check(r.returncode == 2 and r.stdout == "" and r.stderr.strip() != "",
                  f"{label} exits 2 with a message and prints no line", f"code={r.returncode} {r.stdout!r} {r.stderr!r}")

        # --- the plan part ---------------------------------------------------------------------
        h = home()
        accepted = h / "0005-wire-workers-and-reviewers.md"
        accepted.write_text("# Title\n\nStatus: accepted · Opened: 2026-10-01 · Accepted: 2026-10-01\n\n## Problem\n")
        draft = h / "0006-something.md"
        draft.write_text("# Title\n\nStatus: draft · Opened: 2026-10-01\n")
        late = h / "0007-late.md"
        late.write_text("# Title\n\n\n\n\nStatus: accepted · on line six\n")
        named = h / "notes.md"
        named.write_text("# Title\n\nStatus: accepted\n")
        fam = ["start", "--family", "anthropic"]
        for label, args, want in (
            ("an accepted intent", fam + ["--intent", str(accepted)], "plan: already approved (intent 0005)"),
            ("--small with no intent", fam + ["--small"], "plan: skipped, small change"),
            ("neither", fam, "plan: I will show it and wait for you"),
            ("a draft intent", fam + ["--intent", str(draft)], "plan: I will show it and wait for you"),
            ("a draft intent with --small", fam + ["--intent", str(draft), "--small"], "plan: skipped, small change"),
            ("an accepted intent with --small", fam + ["--small", "--intent", str(accepted)],
             "plan: already approved (intent 0005)"),
            ("a status line below the first five lines", fam + ["--intent", str(late)],
             "plan: I will show it and wait for you"),
            ("a file name with no leading digit", fam + ["--intent", str(named)], "plan: already approved (intent notes)"),
        ):
            r = run(h, args, a_openai)
            check(r.returncode == 0 and one_line(r) and r.stdout.rstrip("\n").endswith(f" · {want}"),
                  f"plan part: {label}", r.stdout + r.stderr)
        r = run(h, fam + ["--intent", str(h / "missing.md")], a_openai)
        check(r.returncode == 0 and one_line(r) and r.stdout.rstrip("\n").endswith("plan: I will show it and wait for you")
              and "missing.md" in r.stderr,
              "an intent file that cannot be read counts as no intent, and stderr says so", r.stdout + r.stderr)
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
