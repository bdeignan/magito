#!/usr/bin/env python3
"""Tests for worker.py ready, requires_env, and reviewer --skip. Stdlib only."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"
PASS = "echo {brief}"
FAIL = "false {brief}"
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def run(home: Path, args: list[str], roster: list[str] | None, env: dict | None = None,
        cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run worker.py with a temporary home. roster=None leaves the roster file missing."""
    if roster is not None:
        (home / ".magito").mkdir(parents=True, exist_ok=True)
        (home / ".magito" / "workers.toml").write_text("\n".join(roster) + "\n", encoding="utf-8")
    e = dict(os.environ)
    for k in ("MAGITO_THRIFTY", "MAGITO_WORKERS_FILE", "MAGITO_TEST_VAR", "MAGITO_TEST_VAR2"):
        e.pop(k, None)
    e["HOME"] = str(home)
    e.update(env or {})
    # Outside any git repo by default, so only ~/.claude/settings.json can hold an allow rule.
    return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, text=True,
                          env=e, cwd=str(cwd or home))


def lines(r: subprocess.CompletedProcess) -> list[str]:
    return r.stdout.splitlines()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        n = 0

        def home() -> Path:
            nonlocal n
            n += 1
            h = base / f"home{n}"
            h.mkdir()
            return h

        # --- a worker that answers its probe -------------------------------------------
        r = run(home(), ["ready"], ["[workers.a]", f'cmd = "{PASS}"', 'family = "openai"'])
        check(r.returncode == 0 and lines(r)[0] == "a: family=openai installed=yes env=ok probe=ok",
              "a worker that answers shows probe=ok", r.stdout + r.stderr)
        check(lines(r)[-1] == "launcher allow rule: absent", "allow rule is absent by default", r.stdout)

        # --- a failing probe never ends the report --------------------------------------
        r = run(home(), ["ready"], ["[workers.a]", f'cmd = "{FAIL}"', 'family = "openai"',
                                    "[workers.b]", f'cmd = "{PASS}"', 'family = "google"'])
        check(r.returncode == 0 and lines(r)[:2] == [
            "a: family=openai installed=yes env=ok probe=failed",
            "b: family=google installed=yes env=ok probe=ok"],
            "a failed probe does not end the report", r.stdout + r.stderr)

        # --- requires_env: unset, empty, set, invalid -----------------------------------
        h = home()
        started = h / "started"
        fake = h / "fake.py"
        fake.write_text("import sys, pathlib\n"
                        f"pathlib.Path({str(started)!r}).write_text('x')\n"
                        "print(sys.argv[-1])\n")
        needs = ["[workers.a]", f'cmd = "{sys.executable} {fake} {{brief}}"', 'family = "openai"',
                 'requires_env = ["MAGITO_TEST_VAR", "MAGITO_TEST_VAR2"]',
                 "[workers.b]", f'cmd = "{PASS}"', 'family = "google"']
        r = run(h, ["ready"], needs)
        check(r.returncode == 0
              and lines(r)[0] == "a: family=openai installed=yes env=missing MAGITO_TEST_VAR,MAGITO_TEST_VAR2 probe=skipped"
              and lines(r)[1].endswith("probe=ok"),
              "an unset required variable shows env=missing and probe=skipped", r.stdout + r.stderr)
        check("worker.py: a needs MAGITO_TEST_VAR: set it in the environment the worker starts from" in r.stderr
              and "worker.py: a needs MAGITO_TEST_VAR2: set it in the environment the worker starts from" in r.stderr,
              "stderr names each missing variable and where to set it", r.stderr)
        check(not started.exists(), "a worker with a missing variable is never started")
        r = run(h, ["ready"], needs, env={"MAGITO_TEST_VAR": "", "MAGITO_TEST_VAR2": "x"})
        check(lines(r)[0] == "a: family=openai installed=yes env=missing MAGITO_TEST_VAR probe=skipped",
              "a variable set to the empty string counts as missing", r.stdout + r.stderr)
        r = run(h, ["ready"], needs, env={"MAGITO_TEST_VAR": "1", "MAGITO_TEST_VAR2": "x"})
        check(lines(r)[0] == "a: family=openai installed=yes env=ok probe=ok" and started.exists(),
              "with every variable set the probe runs", r.stdout + r.stderr)
        r = run(home(), ["ready"], ["[workers.a]", f'cmd = "{PASS}"', 'family = "openai"',
                                    'requires_env = "MAGITO_TEST_VAR"',
                                    "[workers.b]", f'cmd = "{PASS}"', 'family = "google"'])
        check(r.returncode == 0 and lines(r)[:2] == [
            "a: family=openai installed=yes env=invalid probe=skipped",
            "b: family=google installed=yes env=ok probe=ok"],
            "requires_env as a plain string shows env=invalid and the report goes on", r.stdout + r.stderr)

        # --- installed ---------------------------------------------------------------------
        r = run(home(), ["ready"], ["[workers.a]", 'cmd = "env -u CLAUDECODE X=1 echo {brief}"', 'family = "openai"',
                                    "[workers.b]", 'cmd = "no-such-binary-magito-test {brief}"', 'family = "google"'])
        check(lines(r)[:2] == [
            "a: family=openai installed=yes env=ok probe=ok",
            "b: family=google installed=no env=ok probe=skipped"],
            "an env prefix is skipped, and a missing program shows installed=no", r.stdout + r.stderr)

        # --- invalid entries ---------------------------------------------------------------
        r = run(home(), ["ready"], [
            "[workers]", 'plain = "text"',
            "[workers.nocmd]", 'family = "openai"',
            "[workers.numcmd]", "cmd = 3",
            "[workers.quote]", "cmd = 'echo \"unbalanced {brief}'",
            "[workers.op]", 'cmd = "echo a && echo {brief}"',
            "[workers.model]", 'cmd = "echo {model} {brief}"',
            "[workers.empty]", 'cmd = ""',
            "[workers.envonly]", 'cmd = "env -u CLAUDECODE"',
            "[workers.subagent]", f'cmd = "{PASS}"', 'family = "google"',
            "[workers.good]", f'cmd = "{PASS}"', 'family = "google"',
        ])
        want = [
            "plain: invalid entry (not a table)",
            "nocmd: invalid entry (no cmd)",
            "numcmd: invalid entry (cmd is not a string)",
            "quote: invalid entry (cmd cannot be parsed)",
            "op: invalid entry (cmd contains shell operator '&&')",
            "model: invalid entry (cmd uses {model} but declares no model)",
            "empty: invalid entry (cmd names no program)",
            "envonly: invalid entry (cmd names no program)",
            "subagent: invalid entry (the name subagent is reserved)",
            "good: family=google installed=yes env=ok probe=ok",
        ]
        check(r.returncode == 0 and lines(r)[:len(want)] == want,
              "every kind of invalid entry gets its line and the report goes on",
              f"got {lines(r)} stderr={r.stderr!r}")

        # --- family -----------------------------------------------------------------------
        r = run(home(), ["ready", "--family", "anthropic"], [
            "[workers.num]", f'cmd = "{PASS}"', "family = 3",
            "[workers.blank]", f'cmd = "{PASS}"', 'family = ""',
            "[workers.none]", f'cmd = "{PASS}"',
        ])
        check(r.returncode == 0 and lines(r)[:3] == [
            "num: family=invalid installed=yes env=ok probe=ok",
            "blank: family=none installed=yes env=ok probe=ok",
            "none: family=none installed=yes env=ok probe=ok"]
            and lines(r)[-1] == "reviewer for anthropic: none",
            "a non-string family is invalid, an empty or absent one is none, and neither reviews",
            r.stdout + r.stderr)

        # --- the roster file itself --------------------------------------------------------
        r = run(home(), ["ready"], None)
        check(r.returncode == 2 and r.stdout == "", "no roster file exits 2", r.stdout + r.stderr)
        r = run(home(), ["ready"], ["this is not toml ["])
        check(r.returncode == 2, "a roster that is not valid TOML exits 2", r.stdout + r.stderr)
        r = run(home(), ["ready", "--family", "anthropic"], ["thrifty = false"])
        check(r.returncode == 0 and lines(r) == ["launcher allow rule: absent", "reviewer for anthropic: none"],
              "a roster with no workers prints only the closing lines", r.stdout + r.stderr)
        r = run(home(), ["ready"], ['workers = "nope"'])
        check(r.returncode == 0 and lines(r) == ["launcher allow rule: absent"] and "workers" in r.stderr,
              "workers that is not a table prints no worker lines and exits 0", r.stdout + r.stderr)

        # --- --family ------------------------------------------------------------------------
        two = ["[workers.a]", f'cmd = "{PASS}"', 'family = "anthropic"',
               "[workers.b]", f'cmd = "{FAIL}"', 'family = "openai"',
               "[workers.c]", f'cmd = "{PASS}"', 'family = "google"']
        r = run(home(), ["ready", "--family", "anthropic"], two)
        check(lines(r)[-1] == "reviewer for anthropic: c" and lines(r)[-2] == "launcher allow rule: absent",
              "--family names the first ready worker of another family", r.stdout + r.stderr)
        r = run(home(), ["ready", "--family", "anthropic"], two[:6])
        check(r.returncode == 0 and lines(r)[-1] == "reviewer for anthropic: none",
              "--family prints none when no other-family worker is ready", r.stdout + r.stderr)
        r = run(home(), ["ready", "--family", "anthropic"], ['reviewers = ["c", "b"]'] + two)
        check(lines(r)[-1] == "reviewer for anthropic: c", "--family follows the reviewers order", r.stdout)
        r = run(home(), ["ready", "--family", "anthropic"], ['reviewers = "c"'] + two)
        check(r.returncode == 0 and len(lines(r)) == 5 and lines(r)[-1] == "reviewer for anthropic: none"
              and "reviewers" in r.stderr,
              "reviewers as a plain string: every worker line, reviewer none, fault on stderr, exit 0",
              r.stdout + r.stderr)
        r = run(home(), ["ready", "--family"], two)
        check(r.returncode == 2, "--family with no value exits 2", r.stdout + r.stderr)

        # --- the allow rule --------------------------------------------------------------
        h = home()
        (h / ".claude").mkdir()
        (h / ".claude" / "settings.json").write_text(json.dumps(
            {"permissions": {"allow": ["Bash(git status:*)", "Bash(python3 */implement/scripts/worker.py:*)"]}}))
        r = run(h, ["ready"], two)
        check(lines(r)[-1] == "launcher allow rule: present", "an allow rule in ~/.claude/settings.json is present",
              r.stdout)
        (h / ".claude" / "settings.json").write_text("{ not json")
        r = run(h, ["ready"], two)
        check(r.returncode == 0 and lines(r)[-1] == "launcher allow rule: absent",
              "a settings file that is not valid JSON counts as absent", r.stdout + r.stderr)
        h = home()
        repo = h / "repo"
        (repo / ".claude").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / ".claude" / "settings.local.json").write_text(json.dumps(
            {"permissions": {"allow": ["Bash(python3 ~/.claude/skills/implement/scripts/worker.py *)"]}}))
        sub = repo / "deep" / "er"
        sub.mkdir(parents=True)
        r = run(h, ["ready"], two, cwd=sub)
        check(lines(r)[-1] == "launcher allow rule: present",
              "an allow rule in the repo root's settings.local.json is present", r.stdout + r.stderr)

        # --- reviewer honors requires_env, families, invalid entries -------------------------
        r = run(home(), ["reviewer", "anthropic"], needs)
        check(r.returncode == 0 and r.stdout.strip() == "b"
              and "worker.py: skip a: missing MAGITO_TEST_VAR,MAGITO_TEST_VAR2" in r.stderr,
              "reviewer skips a candidate with a missing variable and picks the next", r.stdout + r.stderr)
        r = run(home(), ["reviewer", "anthropic"], ["[workers.a]", f'cmd = "{PASS}"', 'family = "openai"',
                                                    "requires_env = 3",
                                                    "[workers.b]", f'cmd = "{PASS}"', 'family = "google"'])
        check(r.stdout.strip() == "b" and "worker.py: skip a: requires_env is not a list of strings" in r.stderr,
              "reviewer skips a candidate whose requires_env is not a list", r.stdout + r.stderr)
        r = run(home(), ["reviewer", "anthropic"], ["[workers.a]", f'cmd = "{PASS}"', 'family = ""'])
        check(r.returncode == 3 and r.stdout == "" and "worker.py: skip a: no family" in r.stderr,
              "reviewer never picks a worker with an empty family", r.stdout + r.stderr)
        r = run(home(), ["reviewer", "anthropic"], ["[workers.subagent]", f'cmd = "{PASS}"', 'family = "openai"',
                                                    "[workers.nocmd]", 'family = "openai"',
                                                    "[workers.b]", f'cmd = "{PASS}"', 'family = "google"'])
        check(r.returncode == 0 and r.stdout.strip() == "b"
              and "worker.py: skip subagent: invalid entry (the name subagent is reserved)" in r.stderr
              and "worker.py: skip nocmd: invalid entry (no cmd)" in r.stderr,
              "reviewer skips the reserved name and an invalid entry", r.stdout + r.stderr)

        # --- reviewer --skip -----------------------------------------------------------------
        abc = ["[workers.a]", f'cmd = "{PASS}"', 'family = "openai"',
               "[workers.b]", f'cmd = "{PASS}"', 'family = "google"',
               "[workers.c]", f'cmd = "{PASS}"', 'family = "moonshot"']
        r = run(home(), ["reviewer", "anthropic", "--skip", "a"], abc)
        check(r.returncode == 0 and r.stdout.strip() == "b"
              and "worker.py: skip a: excluded by the caller" in r.stderr,
              "--skip passes over the named worker", r.stdout + r.stderr)
        r = run(home(), ["reviewer", "anthropic", "--skip", "a", "--skip", "b"], abc)
        check(r.stdout.strip() == "c", "--skip can be given more than once", r.stdout + r.stderr)
        r = run(home(), ["reviewer", "anthropic", "--skip", "a"], abc[:3])
        check(r.returncode == 3 and r.stdout == "",
              "skipping the only other-family candidate prints no name and exits 3", r.stdout + r.stderr)
        r = run(home(), ["reviewer", "anthropic", "--skip", "zzz"], abc)
        check(r.returncode == 0 and r.stdout.strip() == "a", "--skip with an unknown name changes nothing",
              r.stdout + r.stderr)
        r = run(home(), ["reviewer", "anthropic", "--skip"], abc)
        check(r.returncode == 2 and r.stdout == "", "--skip with no name exits 2", r.stdout + r.stderr)

    # --- no tool or variable name is a special case in the script -------------------------
    text = WORKER.read_text()
    check("GOOGLE_CLOUD_PROJECT" not in text and "gemini" not in text.lower(),
          "worker.py holds no tool name and no variable name of its own")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
