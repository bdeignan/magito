#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""More tests for the roster's per-worker `env` table. Issue #225. Stdlib only.

test_worker_env.py was committed before the code and is locked, so cases found
later live here. The rule under test: `requires_env` is judged against the
environment the worker starts with, never against a value it will not receive."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"
PASS = "echo {brief}"
SESSION = "CLAUDE_CODE_SESSION_ID"
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print(f"    {detail}")
    RESULTS.append(ok)


def run(home: Path, args: list[str], roster: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    (home / ".magito").mkdir(parents=True, exist_ok=True)
    (home / ".magito" / "workers.toml").write_text("\n".join(roster) + "\n", encoding="utf-8")
    e = dict(os.environ)
    for k in ("MAGITO_THRIFTY", "MAGITO_WORKERS_FILE", SESSION):
        e.pop(k, None)
    e["HOME"] = str(home)
    e.update(env or {})
    return subprocess.run([sys.executable, str(WORKER), *args], capture_output=True, text=True,
                          env=e, cwd=str(home))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        # The launcher removes CLAUDE_CODE_SESSION_ID from every worker, so a worker that
        # requires it never has it: from the env table, from the launcher, or from both.
        cases = (("only the env table sets it", f'env = {{ {SESSION} = "from-table" }}', None),
                 ("only the launcher's environment sets it", "", {SESSION: "inherited"}),
                 ("both set it", f'env = {{ {SESSION} = "from-table" }}', {SESSION: "inherited"}))
        for i, (label, table, env) in enumerate(cases):
            h = base / f"home{i}"
            h.mkdir()
            started = h / "started"
            fake = h / "fake.py"
            fake.write_text("import sys, pathlib\n"
                            f"pathlib.Path({str(started)!r}).write_text('x')\n"
                            "print(sys.argv[-1])\n")
            roster = ["[workers.a]", f'cmd = "{sys.executable} {fake} {{brief}}"', 'family = "openai"',
                      f'requires_env = ["{SESSION}"]', table,
                      "[workers.b]", f'cmd = "{PASS}"', 'family = "google"']
            r = run(h, ["ready"], roster, env=env)
            check(r.returncode == 0 and r.stdout.splitlines()[0]
                  == f"a: family=openai installed=yes env=missing {SESSION} probe=skipped",
                  f"ready: a required variable the worker never receives is missing ({label})",
                  r.stdout + r.stderr)
            r = run(h, ["reviewer", "anthropic"], roster, env=env)
            check(r.returncode == 0 and r.stdout.splitlines() == ["b"]
                  and f"skip a: missing {SESSION}" in r.stderr,
                  f"reviewer: passes over that worker ({label})", r.stdout + r.stderr)
            check(not started.exists(), f"that worker is never started ({label})")
    return 0 if all(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
