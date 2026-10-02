#!/usr/bin/env python3
"""Tests for the roster's per-worker `env` table. Issue #225. Stdlib only.

Each case runs the real worker.py with a temporary home and a fake worker that
writes the variables it received to a file, so the test reads what the worker
saw and never what the launcher printed."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"
PASS = "echo {brief}"
VAR = "MAGITO_TEST_VAR"
INVALID = "invalid entry (env is not a table of strings)"
RESULTS: list[bool] = []

# argv: <out-file> <brief>. Writes what it saw, then echoes the brief so a probe passes.
FAKE = (
    "import os, sys\n"
    "from pathlib import Path\n"
    f"seen = [os.environ.get(n, '<unset>') for n in ({VAR!r}, 'CLAUDE_CODE_SESSION_ID')]\n"
    "Path(sys.argv[1]).write_text('|'.join(seen))\n"
    "print(sys.argv[-1])\n"
)


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def run(home: Path, args: list[str], roster: list[str], env: dict | None = None,
        cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run worker.py with a temporary home and the given roster lines."""
    (home / ".magito").mkdir(parents=True, exist_ok=True)
    (home / ".magito" / "workers.toml").write_text("\n".join(roster) + "\n", encoding="utf-8")
    e = dict(os.environ)
    for k in ("MAGITO_THRIFTY", "MAGITO_WORKERS_FILE", VAR, "CLAUDE_CODE_SESSION_ID"):
        e.pop(k, None)
    e["HOME"] = str(home)
    e.update(env or {})
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
            (h / "fake.py").write_text(FAKE)
            (h / "brief.txt").write_text("do the work\n")
            return h

        def fake(h: Path, name: str) -> str:
            """A cmd for a fake worker that writes what it saw to <home>/seen-<name>."""
            return f'cmd = "{sys.executable} {h / "fake.py"} {h / ("seen-" + name)} {{brief}}"'

        def seen(h: Path, name: str) -> str:
            f = h / f"seen-{name}"
            return f.read_text() if f.exists() else "<never started>"

        def launch(h: Path, name: str, roster: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
            return run(h, ["run", name, str(h), str(h / "brief.txt")], roster, env=env)

        # --- 1. run: the worker sees the value from its env table -------------------------
        h = home()
        table = ["[workers.a]", fake(h, "a"), 'family = "openai"',
                 "[workers.a.env]", f'{VAR} = "from-table"']
        r = launch(h, "a", table)
        check(r.returncode == 0 and seen(h, "a") == "from-table|<unset>",
              "run: the worker sees the value from its env table", seen(h, "a") + r.stderr)

        # --- the inline form is the same thing ---------------------------------------------
        h = home()
        inline = ["[workers.a]", fake(h, "a"), 'family = "openai"', f'env = {{ {VAR} = "inline" }}']
        r = launch(h, "a", inline)
        check(r.returncode == 0 and seen(h, "a") == "inline|<unset>",
              "run: the inline form env = { ... } works", seen(h, "a") + r.stderr)

        # --- 2. the env table wins over a variable the launcher inherited -------------------
        h = home()
        table = ["[workers.a]", fake(h, "a"), 'family = "openai"',
                 "[workers.a.env]", f'{VAR} = "from-table"']
        r = launch(h, "a", table, env={VAR: "inherited"})
        check(r.returncode == 0 and seen(h, "a") == "from-table|<unset>",
              "run: an env entry wins over an inherited variable of the same name", seen(h, "a") + r.stderr)

        # --- a worker with no table still inherits the launcher's variable -------------------
        h = home()
        r = launch(h, "a", ["[workers.a]", fake(h, "a"), 'family = "openai"'], env={VAR: "inherited"})
        check(r.returncode == 0 and seen(h, "a") == "inherited|<unset>",
              "run: with no env table the worker inherits the launcher's variable", seen(h, "a") + r.stderr)

        # --- 3. one worker's variable never reaches another worker --------------------------
        h = home()
        two = ["[workers.a]", fake(h, "a"), 'family = "openai"', f'env = {{ {VAR} = "only-a" }}',
               "[workers.b]", fake(h, "b"), 'family = "google"']
        r = launch(h, "b", two)
        check(r.returncode == 0 and seen(h, "b") == "<unset>|<unset>",
              "run: a second worker with no env table does not see the first worker's variable",
              seen(h, "b") + r.stderr)
        # ready probes both workers in one process, a before b.
        h = home()
        two = ["[workers.a]", fake(h, "a"), 'family = "openai"', f'env = {{ {VAR} = "only-a" }}',
               "[workers.b]", fake(h, "b"), 'family = "google"']
        r = run(h, ["ready"], two)
        check(r.returncode == 0 and seen(h, "a") == "only-a|<unset>" and seen(h, "b") == "<unset>|<unset>",
              "ready: in one process, the worker probed second does not see the first worker's variable",
              f"a={seen(h, 'a')} b={seen(h, 'b')} {r.stdout}{r.stderr}")

        # --- probe and review set the table too ---------------------------------------------
        h = home()
        table = ["[workers.a]", fake(h, "a"), 'family = "openai"', f'env = {{ {VAR} = "from-table" }}']
        r = run(h, ["probe", "a"], table)
        check(r.returncode == 0 and seen(h, "a") == "from-table|<unset>",
              "probe: the worker sees the value from its env table", seen(h, "a") + r.stdout + r.stderr)
        h = home()
        repo = h / "repo"
        repo.mkdir()
        git = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                   GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=str(h / "gitconfig"), GIT_CONFIG_NOSYSTEM="1")
        (repo / "a.txt").write_text("a\n")
        for cmd in (["init", "-q"], ["add", "a.txt"], ["commit", "-q", "-m", "init"]):
            subprocess.run(["git", "-C", str(repo), *cmd], check=True, env=git, capture_output=True)
        (h / "brief.txt").write_text("VERDICT PASS\n")
        table = ["[workers.a]", fake(h, "a"), 'family = "openai"', f'env = {{ {VAR} = "from-table" }}']
        r = run(h, ["review", "a", str(repo), str(h / "brief.txt")], table)
        check(seen(h, "a") == "from-table|<unset>",
              "review: the worker sees the value from its env table", seen(h, "a") + r.stdout + r.stderr)

        # --- CLAUDE_CODE_SESSION_ID is still removed -----------------------------------------
        h = home()
        table = ["[workers.a]", fake(h, "a"), 'family = "openai"', f'env = {{ {VAR} = "x" }}']
        r = launch(h, "a", table, env={"CLAUDE_CODE_SESSION_ID": "driver-session"})
        check(seen(h, "a") == "x|<unset>",
              "run: CLAUDE_CODE_SESSION_ID is still removed from a worker with an env table", seen(h, "a"))
        h = home()
        table = ["[workers.a]", fake(h, "a"), 'family = "openai"',
                 'env = { CLAUDE_CODE_SESSION_ID = "from-table" }']
        r = launch(h, "a", table)
        check(seen(h, "a") == "<unset>|<unset>",
              "run: an env table cannot put CLAUDE_CODE_SESSION_ID back", seen(h, "a") + r.stderr)

        # --- 4. requires_env counts a name that only the env table sets ----------------------
        h = home()
        needs = ["[workers.a]", fake(h, "a"), 'family = "openai"', f'requires_env = ["{VAR}"]',
                 f'env = {{ {VAR} = "from-table" }}']
        r = run(h, ["ready"], needs)
        check(r.returncode == 0 and lines(r)[0] == "a: family=openai installed=yes env=ok probe=ok",
              "ready: a required variable that only the env table sets shows env=ok",
              r.stdout + r.stderr)
        r = run(h, ["reviewer", "anthropic"], needs)
        check(r.returncode == 0 and lines(r) == ["a"],
              "reviewer: picks a worker whose required variable only its env table sets",
              r.stdout + r.stderr)
        # An empty string in the table is what the worker receives, so the name is missing,
        # even when the launcher's own environment holds a value.
        h = home()
        empty = ["[workers.a]", fake(h, "a"), 'family = "openai"', f'requires_env = ["{VAR}"]',
                 f'env = {{ {VAR} = "" }}']
        r = run(h, ["ready"], empty, env={VAR: "inherited"})
        check(r.returncode == 0
              and lines(r)[0] == f"a: family=openai installed=yes env=missing {VAR} probe=skipped"
              and seen(h, "a") == "<never started>",
              "ready: a required variable the env table sets to the empty string is missing",
              r.stdout + r.stderr)

        # --- 5. an env that is not a table of strings makes the entry unusable ---------------
        for label, bad in (("a plain string", 'env = "text"'),
                           ("a key that starts with a digit", 'env = { "1BAD" = "x" }'),
                           ("a value that is not a string", "env = { GOOD = 3 }"),
                           ("a key with a character outside letters, digits, and _", 'env = { "A-B" = "x" }'),
                           ("an empty key", 'env = { "" = "x" }'),
                           ("a key with an = sign", 'env = { "A=B" = "x" }'),
                           ("a list", 'env = ["A=x"]'),
                           ("a nested table", "env = { A = { B = 'x' } }")):
            h = home()
            roster = ["[workers.a]", fake(h, "a"), 'family = "openai"', bad,
                      "[workers.b]", f'cmd = "{PASS}"', 'family = "google"']
            r = run(h, ["ready"], roster)
            check(r.returncode == 0 and lines(r)[:2] == [
                f"a: {INVALID}", "b: family=google installed=yes env=ok probe=ok"],
                f"ready: {label} gives an invalid entry, and the report goes on", r.stdout + r.stderr)
            r = run(h, ["reviewer", "anthropic"], roster)
            check(r.returncode == 0 and lines(r) == ["b"] and f"skip a: {INVALID}" in r.stderr,
                  f"reviewer: {label} is skipped with the same reason", r.stdout + r.stderr)
            r = run(h, ["probe", "a"], roster)
            check(r.returncode == 2 and "'a'" in r.stderr, f"probe: {label} exits 2 and names the worker",
                  f"exit {r.returncode} {r.stderr}")
            r = launch(h, "a", roster)
            check(r.returncode == 2 and "'a'" in r.stderr, f"run: {label} exits 2 and names the worker",
                  f"exit {r.returncode} {r.stderr}")
            check(seen(h, "a") == "<never started>", f"{label}: the worker is never started")

        # --- an empty env table is the same as no table --------------------------------------
        for form in (["env = {}"], ["[workers.a.env]"]):
            h = home()
            r = run(h, ["ready"], ["[workers.a]", fake(h, "a"), 'family = "openai"', *form])
            check(r.returncode == 0 and lines(r)[0] == "a: family=openai installed=yes env=ok probe=ok"
                  and seen(h, "a") == "<unset>|<unset>",
                  f"ready: an empty env table ({form[0]}) is the same as no table", r.stdout + r.stderr)

        # --- an `env KEY=value` prefix inside cmd keeps working -------------------------------
        h = home()
        prefix = ["[workers.a]",
                  f'cmd = "env {VAR}=from-prefix {sys.executable} {h / "fake.py"} {h / "seen-a"} {{brief}}"',
                  'family = "openai"']
        r = launch(h, "a", prefix)
        check(r.returncode == 0 and seen(h, "a") == "from-prefix|<unset>",
              "run: an env KEY=value prefix inside cmd still sets the variable", seen(h, "a") + r.stderr)

    # --- 7. the launcher still starts workers without a shell --------------------------------
    check("shell=True" not in WORKER.read_text(), "worker.py still starts workers without a shell")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
