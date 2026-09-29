#!/usr/bin/env python3
"""Process-boundary checks for the paid integrate evaluator, using fake workers."""
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-integrate.sh"


FAKE_WORKER = '''#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

repo = Path.cwd()
mode = os.environ.get("INTEGRATE_FAKE_MODE", "green")
variant = os.environ.get("MAGITO_EVAL_VARIANT", "")
INT = "integrate/0001-greet"
B1 = "feat/0001-01-greet"


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=repo, check=check, capture_output=True, text=True).stdout


def build(branch, base, steps):
    git("checkout", "-b", branch, base)
    for message, files in steps:
        for name, text in files.items():
            (repo / name).write_text(text)
        git("add", *files)
        git("commit", "-m", message)


def merge(branch, flag="--no-ff"):
    git("checkout", INT)
    git("merge", flag, "-m", "merge " + branch, branch)


def gh_pr(body):
    subprocess.run(["gh", "pr", "create", "--title", "Greet", "--body", body], cwd=repo, check=True, capture_output=True)


TEST_GREET = (
    "import unittest\\nfrom greet import greet\\n"
    "class T(unittest.TestCase):\\n"
    "    def test_greet(self):\\n"
    "        self.assertEqual(greet('Ada'), 'hello, Ada')\\n"
)
GREET = "def greet(name):\\n    return f'hello, {name}'\\n"
GREET_SEM = "from names import PREFIX\\n\\ndef greet(name):\\n    return f'{PREFIX}, {name}'\\n"
TEST_HELLO = (
    "import subprocess, sys, unittest\\n"
    "class T(unittest.TestCase):\\n"
    "    def test_hello(self):\\n"
    "        out = subprocess.run([sys.executable, 'hello.py', 'Ada'], capture_output=True, text=True).stdout\\n"
    "        self.assertEqual(out.strip(), 'hello, Ada')\\n"
)
HELLO = (
    "import sys\\nfrom greet import greet\\n"
    "print(greet(sys.argv[1] if len(sys.argv) > 1 else 'world'))\\n"
)
HELLO_BAD = "import sys\\nfrom greet import greet\\nprint(greet(sys.argv[1]).upper())\\n"

if mode == "worker-failure":
    raise SystemExit(73)

TICKET1 = [("test: greet", {"test_greet.py": TEST_GREET}), ("feat: greet", {"greet.py": GREET})]
TICKET2 = [("test: hello", {"test_hello.py": TEST_HELLO}), ("feat: hello", {"hello.py": HELLO_BAD if mode == "red-final" else HELLO})]

if variant == "semantic-conflict":
    git("checkout", "-b", INT, "main")
    build(B1, INT, [("test: greet", {"test_greet.py": TEST_GREET}), ("feat: greet", {"greet.py": GREET_SEM})])
    merge(B1)
    merge("feat/0001-02-prefix")
    tests = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=repo, capture_output=True)
    assert tests.returncode != 0
    if mode != "merged-red":
        git("reset", "--hard", "HEAD^")
    if mode == "opens-pr":
        gh_pr("Closes #101")
    response = "Escalation 6: semantic conflict. feat/0001-02-prefix merged cleanly but test_greet fails.\\nWhich side changes?\\n"
    if mode == "no-escalation":
        response = "Stopped after a red merge.\\n"
else:
    if mode == "no-integrate":
        git("checkout", "-b", "feat/0001-01-greet", "main")
        (repo / "greet.py").write_text(GREET)
        git("add", "greet.py")
        git("commit", "-m", "feat: greet")
    else:
        if not git("branch", "--list", INT).strip():
            git("checkout", "-b", INT, "main")
        merged = git("branch", "--merged", INT)
        if mode == "rebuild":
            git("checkout", "-b", "feat/0001-01-greet-again", INT)
            (repo / "greet.py").write_text(GREET + "# rebuilt\\n")
            git("add", "greet.py")
            git("commit", "-m", "feat: greet again")
            merge("feat/0001-01-greet-again")
        flag = "--ff-only" if mode == "fast-forward" else "--no-ff"
        if mode == "wrong-order":
            build("feat/0001-01-greet", INT, TICKET1)
            build("feat/0001-02-hello", INT, TICKET2)
            merge("feat/0001-02-hello")
            merge("feat/0001-01-greet")
        else:
            if B1 not in merged:
                build(B1, INT, TICKET1)
                merge(B1, flag)
            build("feat/0001-02-hello", INT, TICKET2)
            merge("feat/0001-02-hello", flag)
    response = "" if mode == "no-coverage" else "COVERAGE PASS\\n"
    response += "Merged ticket 01, then ticket 02.\\n"
    if mode == "early-question":
        response = "Is the plan fine?\\n" + response
    if variant == "pr":
        body = "Merge order: 01, 02.\\nCOVERAGE PASS\\n"
        if mode != "missing-closes":
            body += "\\nCloses #102\\n"
        if mode == "double-first":
            body += "\\nCloses #101\\n"
        body += "\\nCloses #101"
        if mode != "no-pr":
            gh_pr(body)
            if mode == "two-prs":
                gh_pr(body)
        response += "Opened https://example.invalid/pull/1\\n"
    else:
        response += "Ready to merge integrate/0001-greet into main?\\n"

print("MAGITO_FINAL_RESPONSE_BEGIN")
print(response, end="")
print("MAGITO_FINAL_RESPONSE_END")
'''


def run(mode: str, roster: Path, variant: str = "") -> subprocess.CompletedProcess[str]:
    env = os.environ | {"MAGITO_WORKERS_FILE": str(roster), "INTEGRATE_FAKE_MODE": mode}
    if variant:
        env["MAGITO_EVAL_VARIANT"] = variant
    return subprocess.run(["bash", str(EVAL), "fake"], text=True, capture_output=True, env=env, check=False)


def expect_pass(label: str, r: subprocess.CompletedProcess[str]) -> None:
    assert r.returncode == 0, (label, r.stdout + r.stderr)
    assert f"{label}: PASS" in r.stdout, (label, r.stdout)


def expect_fail(label: str, mode: str, needle: str, r: subprocess.CompletedProcess[str]) -> None:
    assert r.returncode == 1, (label, mode, r.stdout + r.stderr)
    assert f"{label}: FAIL" in r.stdout and needle in r.stdout, (label, mode, r.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        roster = Path(temp) / "workers.toml"
        worker = Path(temp) / "fake_worker.py"
        worker.write_text(FAKE_WORKER)
        roster.write_text(
            "[workers.fake]\n"
            f"cmd = {json.dumps('python3 ' + str(worker))}\n"
            'family = "test"\n'
        )

        # Two tickets merged in order onto one integration branch, COVERAGE PASS.
        expect_pass("integrate", run("green", roster))
        for mode, needle in [
            ("no-integrate", "integration branch"),
            ("wrong-order", "out of order"),
            ("fast-forward", "merge commits"),
            ("red-final", "check is red"),
            ("no-coverage", "COVERAGE PASS"),
            ("early-question", "question before the merge checkpoint"),
        ]:
            expect_fail("integrate", mode, needle, run(mode, roster))

        # Resume: the integration branch already holds ticket 01, so only 02 is built.
        expect_pass("integrate (resume)", run("green", roster, "resume"))
        expect_fail("integrate (resume)", "rebuild", "rebuilt", run("rebuild", roster, "resume"))

        # Closing rule: one pull request, first ticket closed once, every other ticket closed.
        expect_pass("integrate (pr)", run("green", roster, "pr"))
        for mode, needle in [
            ("missing-closes", "Closes #102"),
            ("double-first", "Closes #101"),
            ("no-pr", "no pull request"),
            ("two-prs", "one pull request"),
        ]:
            expect_fail("integrate (pr)", mode, needle, run(mode, roster, "pr"))

        # Semantic conflict: stop with escalation 6 and open no pull request.
        expect_pass("integrate (semantic-conflict)", run("green", roster, "semantic-conflict"))
        for mode, needle in [
            ("merged-red", "check is red"),
            ("opens-pr", "pull request"),
            ("no-escalation", "escalation 6"),
        ]:
            expect_fail("integrate (semantic-conflict)", mode, needle, run(mode, roster, "semantic-conflict"))

        failed = run("worker-failure", roster)
        assert failed.returncode == 73, failed.stdout + failed.stderr

    print("eval-integrate: ok")


if __name__ == "__main__":
    main()
