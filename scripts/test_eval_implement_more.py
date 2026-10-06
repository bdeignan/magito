#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""More fake-worker cases for the paid implement evaluator, beside test_eval_implement.py.

Each case breaks exactly one thing the evaluator must check: a commit on main before the
plan is approved, a second worktree, a small change built outside a worktree, a wrong
NOTES.md, and a review record split over two lines. Stdlib only."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-implement.sh"

FAKE_WORKER = """#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

repo = Path.cwd()
mode = os.environ["IMPLEMENT_FAKE_MODE"]
BRANCH = "feat/1-hello"
SLUG = "feat-1-hello"


def git(*args, cwd=repo):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(where, message, name, text):
    (where / name).write_text(text)
    git("add", name, cwd=where)
    git("commit", "-m", message, cwd=where)


def worktree():
    path = repo / ".magito" / "worktrees" / SLUG
    git("worktree", "add", "-q", "-b", BRANCH, str(path))
    return path


def record(text=None):
    sha = git("rev-parse", BRANCH)
    (repo / ".magito" / f"review-{SLUG}").write_text(text.format(sha=sha) if text else f"{sha} reviewed by fake\\n")


PLAN = "Plan: write the test, then the code.\\nIs this plan fine?\\n"
MERGE = "Ready to merge feat/1-hello into main?\\n"
TEST = "import unittest\\nclass T(unittest.TestCase):\\n    def test_x(self):\\n        self.assertTrue(True)\\n"
CODE = "import sys\\nname = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else 'world'\\nprint(f'hello, {name}')\\n"

if mode == "main-commit":
    commit(repo, "feat: straight onto main", "hello.py", CODE)
    response = PLAN
elif mode == "extra-worktree":
    git("worktree", "add", "-q", "--detach", str(repo.parent / "extra-worktree"))
    response = PLAN
elif mode == "small-green":
    where = worktree()
    commit(where, "docs: fix the greeting", "NOTES.md", "greeting: hello\\n")
    record()
    response = MERGE
elif mode == "small-no-worktree":
    git("checkout", "-b", BRANCH)
    commit(repo, "docs: fix the greeting", "NOTES.md", "greeting: hello\\n")
    record()
    response = MERGE
elif mode == "small-wrong-notes":
    where = worktree()
    commit(where, "docs: change the greeting", "NOTES.md", "greeting: hallo\\n")
    record()
    response = MERGE
elif mode in ("split-record", "one-line-record"):
    where = worktree()
    commit(where, "test: add hello test", "test_hello.py", TEST)
    commit(where, "feat: add hello", "hello.py", CODE)
    record("{sha} pending\\nx reviewed by fake\\n" if mode == "split-record" else None)
    response = MERGE
else:
    raise SystemExit(f"unknown mode {mode}")

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
            env = os.environ | {"MAGITO_WORKERS_FILE": str(roster), "IMPLEMENT_FAKE_MODE": mode}
            env.pop("MAGITO_EVAL_VARIANT", None)
            if variant:
                env["MAGITO_EVAL_VARIANT"] = variant
            return subprocess.run(["bash", str(EVAL), "fake"], text=True, capture_output=True, env=env, check=False)

        def fails(mode: str, variant: str, needle: str) -> None:
            r = run(mode, variant)
            label = f"implement ({variant})" if variant else "implement"
            assert r.returncode == 1, (mode, r.stdout + r.stderr)
            assert f"{label}: FAIL ({needle}" in r.stdout, (mode, r.stdout)

        # no-intent: a commit made straight onto main, and a second worktree with a clean tree.
        fails("main-commit", "no-intent", "commits were made before the plan was approved")
        fails("extra-worktree", "no-intent", "files were changed before the plan was approved")

        # no-intent-small: the control case passes, and each single fault fails.
        ok = run("small-green", "no-intent-small")
        assert ok.returncode == 0 and "implement (no-intent-small): PASS" in ok.stdout, ok.stdout + ok.stderr
        fails("small-no-worktree", "no-intent-small", "feat/1-hello was not built in a worktree under .magito/worktrees")
        fails("small-wrong-notes", "no-intent-small", "NOTES.md on feat/1-hello does not hold 'greeting: hello'")

        # The review record is one line: the sha and the reviewer together.
        ok = run("one-line-record", "")
        assert ok.returncode == 0 and "implement: PASS" in ok.stdout, ok.stdout + ok.stderr
        fails("split-record", "", "feat/1-hello: no review record at the branch tip")

    print("eval-implement-more: ok")


if __name__ == "__main__":
    main()
