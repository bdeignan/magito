#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""More fake-`claude` cases for the paid implement evaluator, beside test_eval_implement.py.

Each case breaks exactly one thing the evaluator must check: a commit on main before the
plan is approved, a third worktree, an edit in the main checkout, a small change built
outside the run's worktree, a wrong NOTES.md, a review marker in the main checkout, and two
permission denials, which must both be printed. Stdlib only."""
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-implement.sh"

FAKE_CLAUDE = """#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
from pathlib import Path

repo = Path.cwd()
mode = os.environ["IMPLEMENT_FAKE_MODE"]
WT = repo / ".claude" / "worktrees" / "eval"


def git(*args, cwd=repo):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(where, message, file, text):
    (where / file).write_text(text)
    git("add", file, cwd=where)
    git("commit", "-m", message, cwd=where)


git("worktree", "add", "-q", "-b", "worktree-eval", str(WT))
git("worktree", "lock", str(WT))
# Claude Code copies each file .worktreeinclude lists into a new worktree.
for line in (repo / ".worktreeinclude").read_text().split():
    (WT / line).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(repo / line, WT / line)

PLAN = "Plan: write the test, then the code.\\nIs this plan fine?\\n"
READY = "Ready to read. Risk: Normal.\\n"
CODE = "import sys\\nname = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else 'world'\\nprint(f'hello, {name}')\\n"
TEST = "import unittest\\nclass T(unittest.TestCase):\\n    def test_x(self):\\n        self.assertTrue(True)\\n"
denials = []

if mode == "main-commit":
    commit(repo, "feat: straight onto main", "hello.py", CODE)
    response = PLAN
elif mode == "extra-worktree":
    git("worktree", "add", "-q", "--detach", str(repo.parent / "extra-worktree"))
    response = PLAN
elif mode == "main-edit":
    (repo / "hello.py").write_text(CODE)
    response = PLAN
elif mode == "small-green":
    commit(WT, "docs: fix the greeting", "NOTES.md", "greeting: hello\\n")
    response = READY
elif mode == "small-no-worktree":
    git("checkout", "-b", "feat/1-hello")
    commit(repo, "docs: fix the greeting", "NOTES.md", "greeting: hello\\n")
    response = READY
elif mode == "small-wrong-notes":
    commit(WT, "docs: change the greeting", "NOTES.md", "greeting: hallo\\n")
    response = READY
elif mode in ("main-review-marker", "two-denials"):
    commit(WT, "test: add hello test", "test_hello.py", TEST)
    commit(WT, "feat: add hello", "hello.py", CODE)
    if mode == "main-review-marker":
        (repo / ".magito" / "review-worktree-eval").write_text("pending\\n")
    else:
        for command in ("git push -u origin worktree-eval", "gh pr create --base main"):
            denials.append({"tool_name": "Bash", "tool_input": {"command": command}})
    response = READY
else:
    raise SystemExit(f"unknown mode {mode}")

print(json.dumps({"result": response, "permission_denials": denials}))
"""


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        bindir = Path(temp)
        claude = bindir / "claude"
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)

        def run(mode: str, variant: str) -> subprocess.CompletedProcess[str]:
            env = os.environ | {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "IMPLEMENT_FAKE_MODE": mode}
            env.pop("MAGITO_EVAL_VARIANT", None)
            if variant:
                env["MAGITO_EVAL_VARIANT"] = variant
            return subprocess.run(["bash", str(EVAL)], text=True, capture_output=True, env=env, check=False)

        def fails(mode: str, variant: str, reason: str) -> str:
            r = run(mode, variant)
            label = f"implement ({variant})" if variant else "implement"
            assert r.returncode == 1, (mode, r.stdout + r.stderr)
            assert f"{label}: FAIL ({reason})" in r.stdout, (mode, r.stdout)
            return r.stdout

        # no-intent: a commit straight onto main, a third worktree, and an edit in the
        # main checkout. The run's own worktree under .claude/ is not a change.
        fails("main-commit", "no-intent", "commits were made before the plan was approved")
        fails("extra-worktree", "no-intent", "files were changed before the plan was approved")
        fails("main-edit", "no-intent", "files were changed before the plan was approved")

        # no-intent-small: the control case passes, and each single fault fails.
        ok = run("small-green", "no-intent-small")
        assert ok.returncode == 0 and "implement (no-intent-small): PASS" in ok.stdout, ok.stdout + ok.stderr
        fails("small-no-worktree", "no-intent-small", "feat/1-hello was not built in the worktree Claude Code made")
        fails("small-wrong-notes", "no-intent-small", "NOTES.md on worktree-eval does not hold 'greeting: hello'")

        # A review marker counts in the main checkout as well as in the run's worktree.
        fails("main-review-marker", "", "a .magito/review-* file was created")

        # Every denial is printed, not only the first.
        out = fails("two-denials", "", "the run hit a permission prompt")
        assert "denied: Bash: git push -u origin worktree-eval" in out, out
        assert "denied: Bash: gh pr create --base main" in out, out

    print("eval-implement-more: ok")


if __name__ == "__main__":
    main()
