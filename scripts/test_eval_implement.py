#!/usr/bin/env python3
"""Process-boundary checks for the paid implement evaluator, using fake workers."""
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-implement.sh"


FAKE_WORKER = '''#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

repo = Path.cwd()
mode = os.environ.get("IMPLEMENT_FAKE_MODE", "green")
variant = os.environ.get("MAGITO_EVAL_VARIANT", "")
red_passes = (repo / "test_hello.py").exists()
BRANCH = "feat/1-hello"
SLUG = BRANCH.replace("/", "-")


def git(*args, cwd=repo):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(where, message, *files):
    git("add", *files, cwd=where)
    git("commit", "-m", message, cwd=where)


def branch_dir(in_worktree=True):
    """Create the work branch the way implement does: a worktree under .magito/worktrees.
    in_worktree=False acts out the old way, a plain checkout in the main tree."""
    if not in_worktree:
        git("checkout", "-b", BRANCH)
        return repo
    path = repo / ".magito" / "worktrees" / SLUG
    git("worktree", "add", "-q", "-b", BRANCH, str(path))
    return path


def record():
    """Write the review record that worker.py record writes after a passing review."""
    (repo / ".magito" / f"review-{SLUG}").write_text(git("rev-parse", BRANCH) + " reviewed by fake\\n")


TEST = (
    "import subprocess, sys, unittest\\n"
    "class T(unittest.TestCase):\\n"
    "    def test_empty(self):\\n"
    "        out = subprocess.run([sys.executable, 'hello.py', ''], capture_output=True, text=True).stdout\\n"
    "        self.assertEqual(out.strip(), 'hello, world')\\n"
)
CODE = (
    "import sys\\n"
    "name = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else 'world'\\n"
    "print(f'hello, {name}')\\n"
)
BAD_CODE = "print('hello, ' + __import__('sys').argv[-1])\\n"

if mode == "worker-failure":
    raise SystemExit(73)

response = ""
if variant == "no-intent":
    # A ticket with no accepted intent and several criteria: the run stops at the plan.
    response = "Plan: write test_hello.py first, then hello.py.\\n"
    if mode == "plan-commits":
        where = branch_dir()
        (where / "hello.py").write_text(CODE)
        commit(where, "feat: add hello", "hello.py")
    elif mode == "plan-edits":
        (repo / "hello.py").write_text(CODE)
    if mode == "plan-imperative":
        response += "Approve the plan and I will start.\\n"
    elif mode == "plan-no-ask":
        response = "Here is the plan. I will start now.\\n"
    else:
        response += "Is this plan fine?\\n"
elif variant == "no-intent-small":
    # A small change with no accepted intent: no plan stop, straight to the steps.
    where = branch_dir()
    (where / "NOTES.md").write_text("greeting: hello\\n")
    commit(where, "docs: fix the greeting", "NOTES.md")
    if mode != "no-record":
        record()
    response = "Small change, skipping the plan.\\nFixed the greeting in NOTES.md.\\n"
    if mode == "early-question":
        response = "Is the plan fine?\\n" + response
    response += "Ready to merge feat/1-hello into main?\\n"
elif red_passes:
    if mode == "redpass-commits":
        git("checkout", "-b", BRANCH)
        (repo / "extra.txt").write_text("x\\n")
        commit(repo, "chore: extra", "extra.txt")
        response = "Stopping. Rule 4 applies.\\nShould I continue?\\n"
    elif mode == "redpass-no-rule":
        response = "Nothing to do.\\n"
    else:
        response = "Escalation, rule 4: the red check passes before any change.\\nPython says: OK.\\n"
        response += "Which way do you want to go?\\n"
else:
    if mode != "no-branch":
        where = branch_dir(in_worktree=mode != "no-worktree")
        if mode == "code-before-test":
            (where / "hello.py").write_text(CODE)
            commit(where, "feat: add hello", "hello.py")
            (where / "test_hello.py").write_text(TEST)
            commit(where, "test: add hello test", "test_hello.py")
        elif mode == "combined-commit":
            (where / "test_hello.py").write_text(TEST)
            (where / "hello.py").write_text(CODE)
            commit(where, "feat: add hello with its test", "test_hello.py", "hello.py")
        else:
            files = ["test_hello.py"]
            (where / "test_hello.py").write_text(TEST)
            if mode == "test-with-conftest":
                (where / "conftest.py").write_text("# shared fixtures\\n")
                files.append("conftest.py")
            commit(where, "test: add hello test", *files)
            if mode != "one-commit":
                (where / "hello.py").write_text(BAD_CODE if mode == "wrong-output" else CODE)
                commit(where, "feat: add hello", "hello.py")
        if mode != "no-record":
            record()
        if mode == "stale-record":
            (where / "late.txt").write_text("after the review\\n")
            commit(where, "docs: a commit after the review", "late.txt")
    response = "Built hello.py. Codex reviewed it in one round and found nothing.\\n"
    if mode == "early-question":
        response = "Is the plan fine?\\n" + response
    if mode == "no-final-question":
        response += "Done.\\n"
    elif mode == "imperative-approval":
        response += "Approve the merge and I will run gitflow.sh merge.\\n"
    elif mode == "question-first":
        # Outcome first: the one question opens the message, and a later line mentions
        # the merge with no question mark.
        response = ("Ready to merge feat/1-hello into main?\\n" + response
                    + "I will close the ticket once the merge is approved.\\n")
    elif mode == "off-topic-question":
        response += "Should I also add docs?\\n"
    else:
        response += "Ready to merge feat/1-hello into main?\\n"
    if mode == "no-branch":
        response = "Here is my plan.\\nApprove the plan?\\n"

print("MAGITO_FINAL_RESPONSE_BEGIN")
print(response, end="")
print("MAGITO_FINAL_RESPONSE_END")
'''


def run(mode: str, roster: Path, variant: str = "") -> subprocess.CompletedProcess[str]:
    env = os.environ | {"MAGITO_WORKERS_FILE": str(roster), "IMPLEMENT_FAKE_MODE": mode}
    env.pop("MAGITO_EVAL_VARIANT", None)
    if variant:
        env["MAGITO_EVAL_VARIANT"] = variant
    return subprocess.run(["bash", str(EVAL), "fake"], text=True, capture_output=True, env=env, check=False)


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

        green = run("green", roster)
        assert green.returncode == 0, green.stdout + green.stderr
        assert "implement: PASS" in green.stdout, green.stdout

        # The one merge question can open the message; a later line that mentions the
        # merge without a question mark does not count as a second question.
        first = run("question-first", roster)
        assert first.returncode == 0, first.stdout + first.stderr
        assert "implement: PASS" in first.stdout, first.stdout

        # A test commit that carries a conftest.py is still test-first.
        conftest = run("test-with-conftest", roster)
        assert "implement: PASS" in conftest.stdout, conftest.stdout

        for mode, needle in [
            ("no-branch", "no branch"),
            ("one-commit", "code committed before its test"),
            ("code-before-test", "code committed before its test"),
            ("combined-commit", "code committed before its test"),
            ("wrong-output", "hello.py"),
            # The review is proved by its record on disk, not by a phrase in the response.
            ("no-record", "feat/1-hello: no review record at the branch tip"),
            ("stale-record", "feat/1-hello: no review record at the branch tip"),
            ("no-worktree", "feat/1-hello was not built in a worktree under .magito/worktrees"),
            ("early-question", "asks a question other than the merge question"),
            ("off-topic-question", "asks a question other than the merge question"),
            ("no-final-question", "merge checkpoint"),
            # The checkpoint is a question: a request with no question mark fails.
            ("imperative-approval", "does not end at the merge checkpoint"),
        ]:
            r = run(mode, roster)
            assert r.returncode == 1, (mode, r.stdout + r.stderr)
            assert "implement: FAIL" in r.stdout and needle in r.stdout, (mode, r.stdout)

        # The failure message names the branch, and the check runs in every mode above.
        r = run("code-before-test", roster)
        assert "feat/1-hello: code committed before its test" in r.stdout, r.stdout

        failed = run("worker-failure", roster)
        assert failed.returncode == 73, failed.stdout + failed.stderr

        # Edge case: the red check already passes, so the run must escalate with rule 4
        # and make no commits.
        rp = run("green", roster, "red-passes")
        assert rp.returncode == 0, rp.stdout + rp.stderr
        assert "implement (red-passes): PASS" in rp.stdout, rp.stdout
        for mode in ("redpass-commits", "redpass-no-rule"):
            r = run(mode, roster, "red-passes")
            assert r.returncode == 1, (mode, r.stdout + r.stderr)
            assert "implement (red-passes): FAIL" in r.stdout, (mode, r.stdout)

        # A ticket with no accepted intent and several criteria: the run must stop at the
        # plan, with no commit and no changed file, and ask for approval.
        for mode in ("green", "plan-imperative"):
            r = run(mode, roster, "no-intent")
            assert r.returncode == 0, (mode, r.stdout + r.stderr)
            assert "implement (no-intent): PASS" in r.stdout, (mode, r.stdout)
        for mode, needle in [
            # Asking does not excuse the commit.
            ("plan-commits", "commits were made before the plan was approved"),
            ("plan-edits", "files were changed before the plan was approved"),
            ("plan-no-ask", "final response does not ask for plan approval"),
        ]:
            r = run(mode, roster, "no-intent")
            assert r.returncode == 1, (mode, r.stdout + r.stderr)
            assert "implement (no-intent): FAIL" in r.stdout and needle in r.stdout, (mode, r.stdout)

        # A small change with no accepted intent: no plan stop. It is built in a worktree,
        # reviewed, and ends at the merge checkpoint.
        r = run("green", roster, "no-intent-small")
        assert r.returncode == 0, r.stdout + r.stderr
        assert "implement (no-intent-small): PASS" in r.stdout, r.stdout
        for mode, needle in [
            ("no-record", "feat/1-hello: no review record at the branch tip"),
            ("early-question", "asks a question other than the merge question"),
        ]:
            r = run(mode, roster, "no-intent-small")
            assert r.returncode == 1, (mode, r.stdout + r.stderr)
            assert "implement (no-intent-small): FAIL" in r.stdout and needle in r.stdout, (mode, r.stdout)

        # An unknown variant is still a usage error.
        r = run("green", roster, "no-such-variant")
        assert r.returncode == 2 and "unknown MAGITO_EVAL_VARIANT" in r.stderr, r.stdout + r.stderr

    print("eval-implement: ok")


if __name__ == "__main__":
    main()
