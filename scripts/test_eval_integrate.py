#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
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


def record(text=None):
    """Write the review record that worker.py record writes for the integration branch
    after the final review passes: one line, the branch tip and the reviewer."""
    sha = git("rev-parse", INT).strip()
    marker = repo / ".magito" / ("review-" + INT.replace("/", "-"))
    marker.parent.mkdir(exist_ok=True)
    marker.write_text(text.format(sha=sha) if text else sha + " reviewed by fake\\n")


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
if mode == "code-before-test":
    TICKET2.reverse()

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
        if mode == "unmerged-code-first":
            build("feat/0001-03-extra", INT, [("feat: extra", {"extra.py": "X = 1\\n"}), ("test: extra", {"test_extra.py": "import unittest\\n"})])
            git("checkout", INT)
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
        # The final review passed: record it, unless the mode acts out a missing,
        # stale, or malformed record.
        if mode == "split-record":
            record("{sha} pending\\nx reviewed by fake\\n")
        elif mode != "no-coverage":
            record()
        if mode == "stale-record":
            git("checkout", INT)
            (repo / "late.txt").write_text("after the review\\n")
            git("add", "late.txt")
            git("commit", "-m", "docs: a commit after the review")
    # Closing a ticket before the integration branch merges into main, as the failed
    # 2026-10-05 run did with ticket 01.
    closing = {"early-close": "01-*.md", "late-close": "02-*.md"}.get(mode)
    if closing:
        for f in (repo / ".scratch" / "0001-greet").glob(closing):
            f.write_text(f.read_text().replace("Status: open", "Status: done"))
    response = "Merged ticket 01, then ticket 02. The reviewer passed the whole branch.\\n"
    if mode == "early-question":
        response = "Is the plan fine?\\n" + response
    if variant == "pr":
        body = "Delivers ticket 01, then ticket 02. No merge conflicts.\\n"
        if mode == "body-verdict":
            body += "COVERAGE PASS\\n"
        elif mode == "body-verdict-lower":
            body += "The review ended with verdict pass.\\n"
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
    elif mode == "question-first":
        # The failed 2026-10-05 run's shape: the one question first, and a later line
        # that mentions the merge with no question mark.
        response = ("Do you approve merging integrate/0001-greet into main?\\n" + response
                    + "Ticket 02 stays open, and I will close it once the merge is approved.\\n")
    elif mode == "off-topic-question":
        response += "Should I also add docs?\\n"
    elif mode == "no-question":
        response += "Approve the merge and I will run gitflow.sh merge.\\n"
    else:
        response += "Ready to merge integrate/0001-greet into main?\\n"

print("MAGITO_FINAL_RESPONSE_BEGIN")
print(response, end="")
print("MAGITO_FINAL_RESPONSE_END")
'''


def run(mode: str, roster: Path, variant: str = "") -> subprocess.CompletedProcess[str]:
    env = os.environ | {"MAGITO_WORKERS_FILE": str(roster), "INTEGRATE_FAKE_MODE": mode}
    env.pop("MAGITO_EVAL_VARIANT", None)
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

        # Two tickets merged in order onto one integration branch, with a review record
        # at its tip. The review is proved by that record, not by a phrase in the response.
        expect_pass("integrate", run("green", roster))
        # The one merge question can come first; a later line that mentions the merge
        # with no question mark is not a second question.
        expect_pass("integrate", run("question-first", roster))
        for mode, needle in [
            ("no-integrate", "integration branch"),
            ("wrong-order", "out of order"),
            ("fast-forward", "merge commits"),
            ("red-final", "check is red"),
            ("no-coverage", "integrate/0001-greet: no review record at the branch tip"),
            ("stale-record", "integrate/0001-greet: no review record at the branch tip"),
            ("split-record", "integrate/0001-greet: no review record at the branch tip"),
            ("early-question", "asks a question other than the merge question"),
            ("off-topic-question", "asks a question other than the merge question"),
            # The checkpoint is a question: a request with no question mark fails.
            ("no-question", "does not end at the merge checkpoint"),
            # No variant merges into main, so every ticket is still open when the run ends.
            ("early-close", "a ticket was closed before the merge"),
            ("late-close", "a ticket was closed before the merge"),
            # A merged ticket branch is still checked: its own commits, not an empty range.
            ("code-before-test", "feat/0001-02-hello: code committed before its test"),
            ("unmerged-code-first", "feat/0001-03-extra: code committed before its test"),
        ]:
            expect_fail("integrate", mode, needle, run(mode, roster))

        # Resume: the integration branch already holds ticket 01, so only 02 is built.
        expect_pass("integrate (resume)", run("green", roster, "resume"))
        expect_fail("integrate (resume)", "rebuild", "rebuilt", run("rebuild", roster, "resume"))
        expect_fail("integrate (resume)", "code-before-test", "code committed before its test", run("code-before-test", roster, "resume"))
        # A resumed run needs the review record for the integration branch too.
        expect_fail("integrate (resume)", "no-coverage", "no review record at the branch tip", run("no-coverage", roster, "resume"))

        # Closing rule: one pull request, first ticket closed once, every other ticket closed.
        expect_pass("integrate (pr)", run("green", roster, "pr"))
        for mode, needle in [
            ("missing-closes", "Closes #102"),
            ("double-first", "Closes #101"),
            ("no-pr", "no pull request"),
            ("two-prs", "one pull request"),
            # A pull request body never names a review result, in any letter case.
            ("body-verdict", "the pull request body names a review result"),
            ("body-verdict-lower", "the pull request body names a review result"),
            ("no-coverage", "no review record at the branch tip"),
            ("early-close", "a ticket was closed before the merge"),
        ]:
            expect_fail("integrate (pr)", mode, needle, run(mode, roster, "pr"))

        # Semantic conflict: stop with escalation 6 and open no pull request. The run
        # stops before any final review, so it passes with no review record on disk.
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
