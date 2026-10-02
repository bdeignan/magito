#!/usr/bin/env python3
"""More fake-worker cases for the paid integrate evaluator, beside test_eval_integrate.py.

The pull request body that holds only the line `verdict pass`, and review records in
the shapes the evaluator must accept and reject. Stdlib only."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-integrate.sh"

FAKE_WORKER = """#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

repo = Path.cwd()
mode = os.environ["INTEGRATE_FAKE_MODE"]
variant = os.environ.get("MAGITO_EVAL_VARIANT", "")
INT = "integrate/0001-greet"


def git(*args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def ticket(branch, test_name, test_text, code_name, code_text):
    git("checkout", "-b", branch, INT)
    for message, name, text in (("test: " + test_name, test_name, test_text), ("feat: " + code_name, code_name, code_text)):
        (repo / name).write_text(text)
        git("add", name)
        git("commit", "-m", message)
    git("checkout", INT)
    git("merge", "--no-ff", "-m", "merge " + branch, branch)


git("checkout", "-b", INT, "main")
ticket("feat/0001-01-greet", "test_greet.py",
       "import unittest\\nfrom greet import greet\\nclass T(unittest.TestCase):\\n"
       "    def test_greet(self):\\n        self.assertEqual(greet('Ada'), 'hello, Ada')\\n",
       "greet.py", "def greet(name):\\n    return f'hello, {name}'\\n")
ticket("feat/0001-02-hello", "test_hello.py",
       "import subprocess, sys, unittest\\nclass T(unittest.TestCase):\\n    def test_hello(self):\\n"
       "        out = subprocess.run([sys.executable, 'hello.py', 'Ada'], capture_output=True, text=True).stdout\\n"
       "        self.assertEqual(out.strip(), 'hello, Ada')\\n",
       "hello.py", "import sys\\nfrom greet import greet\\nprint(greet(sys.argv[1] if len(sys.argv) > 1 else 'world'))\\n")

sha = git("rev-parse", INT)
records = {
    "extra-text-record": sha + " reviewed by fake after two rounds\\n",
    "wrong-sha-record": "0" * 40 + " reviewed by fake\\n",
    "sha-not-first-record": "record " + sha + " reviewed by fake\\n",
    "no-reviewer-record": sha + " reviewed\\n",
}
marker = repo / ".magito" / "review-integrate-0001-greet"
marker.parent.mkdir(exist_ok=True)
marker.write_text(records.get(mode, sha + " reviewed by fake\\n"))

response = "Merged ticket 01, then ticket 02.\\n"
if variant == "pr":
    body = "Delivers ticket 01, then ticket 02.\\n"
    if mode == "body-verdict-lower":
        body += "verdict pass\\n"
    elif mode == "body-coverage-mixed":
        body += "Coverage Pass\\n"
    body += "\\nCloses #102\\n\\nCloses #101"
    subprocess.run(["gh", "pr", "create", "--title", "Greet", "--body", body], cwd=repo, check=True, capture_output=True)
    response += "Opened https://example.invalid/pull/1\\n"
else:
    response += "Ready to merge integrate/0001-greet into main?\\n"

print("MAGITO_FINAL_RESPONSE_BEGIN")
print(response, end="")
print("MAGITO_FINAL_RESPONSE_END")
"""


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        roster = Path(temp) / "workers.toml"
        worker = Path(temp) / "fake_worker.py"
        worker.write_text(FAKE_WORKER)
        roster.write_text(f"[workers.fake]\ncmd = {json.dumps('python3 ' + str(worker))}\nfamily = \"test\"\n")

        def run(mode: str, variant: str) -> subprocess.CompletedProcess[str]:
            env = os.environ | {"MAGITO_WORKERS_FILE": str(roster), "INTEGRATE_FAKE_MODE": mode}
            env.pop("MAGITO_EVAL_VARIANT", None)
            if variant:
                env["MAGITO_EVAL_VARIANT"] = variant
            return subprocess.run(["bash", str(EVAL), "fake"], text=True, capture_output=True, env=env, check=False)

        def passes(mode: str, variant: str) -> None:
            r = run(mode, variant)
            label = f"integrate ({variant})" if variant else "integrate"
            assert r.returncode == 0 and f"{label}: PASS" in r.stdout, (mode, r.stdout + r.stderr)

        def fails(mode: str, variant: str, needle: str) -> None:
            r = run(mode, variant)
            label = f"integrate ({variant})" if variant else "integrate"
            assert r.returncode == 1, (mode, r.stdout + r.stderr)
            assert f"{label}: FAIL ({needle}" in r.stdout, (mode, r.stdout)

        # The control case, with and without a pull request.
        passes("green", "")
        passes("green", "pr")

        # A body that holds only the line `verdict pass`, in lower case, and no other review
        # word, fails. So does a mixed-case `Coverage Pass`.
        fails("body-verdict-lower", "pr", "the pull request body names a review result")
        fails("body-coverage-mixed", "pr", "the pull request body names a review result")

        # The record: its first word is the branch tip and the same line says who reviewed.
        # Words after the reviewer do not matter.
        passes("extra-text-record", "")
        for mode in ("wrong-sha-record", "sha-not-first-record", "no-reviewer-record"):
            fails(mode, "", "integrate/0001-greet: no review record at the branch tip")

    print("eval-integrate-more: ok")


if __name__ == "__main__":
    main()
