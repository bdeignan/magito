#!/usr/bin/env python3
"""Which permissions.allow entries count as an allow rule for the worker launcher.

`worker.py ready` reports `launcher allow rule: present` only for a Bash rule whose
command is python running worker.py. An entry that merely mentions the file allows a
different command and must not count. Stdlib only."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"

PRESENT = [
    "Bash(python3 */implement/scripts/worker.py:*)",
    "Bash(python3 ~/.claude/skills/implement/scripts/worker.py *)",
    "Bash(python3 /Users/x/.claude/skills/implement/scripts/worker.py review:*)",
    "Bash(python worker.py:*)",
    "Bash(python3 worker.py)",
]
ABSENT = [
    "Read(//Users/x/code/magito/skills/general/implement/scripts/worker.py)",
    "Edit(**/worker.py)",
    "Bash(cat ~/.claude/skills/implement/scripts/worker.py)",
    "Bash(rm -f worker.py)",
    "Bash(python3 other_worker.py:*)",
    "Bash(python3 ~/scripts/worker.pyc:*)",
    "Bash(python3 ~/scripts/not-the-launcher.py worker.py)",
    "Bash(git status:*)",
    "worker.py",
]


def main() -> int:
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp).resolve()
        (home / ".claude").mkdir()
        roster = home / "roster.toml"
        roster.write_text('[workers.a]\ncmd = "echo {brief}"\nfamily = "openai"\n')
        env = dict(os.environ)
        env.pop("MAGITO_THRIFTY", None)
        env["HOME"] = str(home)
        env["MAGITO_WORKERS_FILE"] = str(roster)

        def reported(allow) -> str:
            (home / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"allow": allow}}))
            r = subprocess.run([sys.executable, str(WORKER), "ready"], capture_output=True, text=True,
                               env=env, cwd=str(home))
            return r.stdout.splitlines()[-1] if r.returncode == 0 and r.stdout else f"exit {r.returncode}"

        for want, entries in (("present", PRESENT), ("absent", ABSENT)):
            for entry in entries:
                got = reported(["Bash(git log:*)", entry])
                ok = got == f"launcher allow rule: {want}"
                print(f"{'ok' if ok else 'not ok'} - {want}: {entry}")
                if not ok:
                    print(f"    got {got!r}")
                results.append(ok)
        for label, allow in (("an empty list", []), ("a list of non-strings", [1, None, {"a": 1}])):
            got = reported(allow)
            ok = got == "launcher allow rule: absent"
            print(f"{'ok' if ok else 'not ok'} - absent: {label}")
            results.append(ok)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
