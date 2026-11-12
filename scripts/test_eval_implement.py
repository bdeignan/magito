#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Process-boundary checks for the paid implement evaluator, using a fake `claude` on PATH.

The fake acts as `claude -p --worktree <name>` does: it makes the worktree
.claude/worktrees/<name> on branch worktree-<name>, locks it, copies the files
.worktreeinclude lists into it, and prints a JSON result with
`result` and `permission_denials`. It refuses any other command line, so every case also
checks that the eval starts its subject with the one fixed command."""
import os
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-implement.sh"


FAKE_CLAUDE = '''#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

repo = Path.cwd()
mode = os.environ.get("IMPLEMENT_FAKE_MODE", "green")
variant = os.environ.get("MAGITO_EVAL_VARIANT", "")
model = os.environ.get("IMPLEMENT_FAKE_MODEL", "sonnet")
fixed = ["-p", "--model", model, "--permission-mode", "auto", "--output-format", "json", "--worktree", "eval"]
if sys.argv[1:-1] != fixed:
    raise SystemExit(f"unexpected command line: {sys.argv[1:-1]}")

if ("Show me the plan first." in sys.argv[-1]) != (variant == "plan-first"):
    raise SystemExit("the brief asks to see the plan first only in the plan-first variant")

if mode == "worker-failure":
    raise SystemExit(73)


def git(*args, cwd=repo):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(where, message, *files):
    git("add", *files, cwd=where)
    git("commit", "-m", message, cwd=where)


WT = repo / ".claude" / "worktrees" / "eval"
git("worktree", "add", "-q", "-b", "worktree-eval", str(WT))
git("worktree", "lock", "--reason", "claude session", str(WT))
# Claude Code copies each file .worktreeinclude lists into a new worktree.
for line in (repo / ".worktreeinclude").read_text().split():
    (WT / line).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(repo / line, WT / line)
red_passes = (WT / "test_hello.py").exists()


def build_dir():
    """Where the build happens: the run's worktree, unless a mode acts out a wrong place."""
    if mode == "no-worktree":
        git("checkout", "-b", "feat/1-hello")
        return repo
    if mode == "magito-worktree":
        path = repo / ".magito" / "worktrees" / "feat-1-hello"
        git("worktree", "add", "-q", "-b", "feat/1-hello", str(path))
        return path
    return WT


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
READY = "Ready to read. Ran python3 -m unittest -q: OK. Risk: Normal.\\n"

denials = []
if variant == "plan-first":
    # A ticket with several criteria and a request to see the plan first: the run stops at the plan.
    response = "Plan: write test_hello.py first, then hello.py.\\n"
    if mode == "plan-commits":
        (WT / "hello.py").write_text(CODE)
        commit(WT, "feat: add hello", "hello.py")
    elif mode == "plan-edits":
        (WT / "hello.py").write_text(CODE)
    if mode == "plan-go-ahead":
        response += "Tell me to go ahead, or tell me what to change.\\n"
    else:
        response += "Is this plan fine?\\n"
elif variant == "no-intent-small":
    # A small change with no accepted intent: the plan is shown, then straight to the steps.
    (WT / "NOTES.md").write_text("greeting: hello\\n")
    commit(WT, "docs: fix the greeting", "NOTES.md")
    response = "Plan: change NOTES.md only.\\nFixed the greeting in NOTES.md.\\n" + READY
elif red_passes:
    if mode == "redpass-commits":
        (WT / "extra.txt").write_text("x\\n")
        commit(WT, "chore: extra", "extra.txt")
        response = "Stopping. Stop 3 applies.\\n"
    elif mode == "redpass-no-rule":
        response = "Nothing to do.\\n"
    else:
        response = "Stop 3: the red check passes before any change.\\nPython says: OK.\\n"
        response += "Which way do you want to go?\\n"
else:
    if mode != "no-branch":
        where = build_dir()
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
    if mode == "review-marker":
        (WT / ".magito" / "review-worktree-eval").write_text("pending\\n")
    if mode == "adds-remote":
        git("remote", "add", "origin", "https://github.com/example/hello.git")
    if mode == "denied":
        denials.append({"tool_name": "Bash", "tool_use_id": "t1",
                        "tool_input": {"command": "git push -u origin worktree-eval"}})
    response = "Built hello.py with its test first.\\n" + READY

print(json.dumps({"type": "result", "result": response, "permission_denials": denials}))
'''


def run(mode: str, bindir: Path, variant: str = "", *args: str,
        model: str = "sonnet") -> subprocess.CompletedProcess[str]:
    env = os.environ | {
        "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}",
        "IMPLEMENT_FAKE_MODE": mode,
        "IMPLEMENT_FAKE_MODEL": model,
    }
    env.pop("MAGITO_EVAL_VARIANT", None)
    if variant:
        env["MAGITO_EVAL_VARIANT"] = variant
    return subprocess.run(["bash", str(EVAL), *args], text=True, capture_output=True, env=env, check=False)


def label(variant: str) -> str:
    return f"implement ({variant})" if variant else "implement"


def passes(mode: str, bindir: Path, variant: str = "", *args: str, model: str = "sonnet") -> str:
    r = run(mode, bindir, variant, *args, model=model)
    assert r.returncode == 0, (mode, variant, r.stdout + r.stderr)
    assert f"{label(variant)}: PASS" in r.stdout, (mode, variant, r.stdout)
    return r.stdout


def fails(mode: str, bindir: Path, variant: str, reason: str) -> str:
    r = run(mode, bindir, variant)
    assert r.returncode == 1, (mode, variant, r.stdout + r.stderr)
    want = f"{label(variant)}: FAIL ({reason})"
    assert want in r.stdout.splitlines(), (mode, variant, want, r.stdout)
    return r.stdout


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        bindir = Path(temp)
        claude = bindir / "claude"
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)

        out = passes("green", bindir)
        # The eval unlocks and removes the run's worktree when it ends, and keeps its branch.
        repo = Path(re.search(r"^repo: (.+)$", out, re.M).group(1))
        worktrees = subprocess.run(["git", "-C", str(repo), "worktree", "list", "--porcelain"],
                                   text=True, capture_output=True, check=True).stdout
        assert worktrees.count("worktree ") == 1, worktrees
        assert not (repo / ".claude/worktrees/eval").exists(), worktrees
        subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "worktree-eval"],
                       capture_output=True, check=True)

        # The optional first argument names the model; it defaults to sonnet.
        passes("green", bindir, "", "haiku", model="haiku")
        r = run("green", bindir, "", "a", "b")
        assert r.returncode == 2 and "usage:" in r.stderr, r.stdout + r.stderr

        # A test commit that carries a conftest.py is still test-first.
        passes("test-with-conftest", bindir)

        for mode, reason in [
            ("no-branch", "no branch has commits beyond main"),
            ("one-commit", "worktree-eval: code committed before its test"),
            ("code-before-test", "worktree-eval: code committed before its test"),
            ("combined-commit", "worktree-eval: code committed before its test"),
            ("wrong-output", "hello.py \"\" printed 'hello, ', expected 'hello, world'"),
            ("no-worktree", "feat/1-hello was not built in the worktree Claude Code made"),
            ("magito-worktree", "a .magito/worktrees folder was created"),
            ("review-marker", "a .magito/review-* file was created"),
            ("adds-remote", "a remote was added; a Normal ticket opens no pull request"),
        ]:
            fails(mode, bindir, "", reason)

        # Edge case: one permission denial fails the run, and the denied command is printed.
        out = fails("denied", bindir, "", "the run hit a permission prompt")
        assert "denied: Bash: git push -u origin worktree-eval" in out, out

        # A failure of claude itself keeps its exit code.
        failed = run("worker-failure", bindir)
        assert failed.returncode == 73, failed.stdout + failed.stderr

        # The red check already passes, so the run must stop with stop 3 and make no commits.
        passes("green", bindir, "red-passes")
        fails("redpass-commits", bindir, "red-passes", "commits were made although the red check passes")
        fails("redpass-no-rule", bindir, "red-passes", "final response does not name stop 3")

        # A ticket with several criteria and a request to see the plan first: the run must stop
        # at the plan, with no commit and no changed file. The wording of the reply is not checked.
        passes("green", bindir, "plan-first")
        passes("plan-go-ahead", bindir, "plan-first")
        # Asking does not excuse the commit.
        fails("plan-commits", bindir, "plan-first", "commits were made before the plan was approved")
        fails("plan-edits", bindir, "plan-first", "files were changed before the plan was approved")

        # A small change with no accepted intent: nothing waits. It is built in the run's
        # worktree and opens no pull request.
        passes("green", bindir, "no-intent-small")

        # An unknown variant is still a usage error.
        r = run("green", bindir, "no-such-variant")
        assert r.returncode == 2 and "unknown MAGITO_EVAL_VARIANT" in r.stderr, r.stdout + r.stderr

    print("eval-implement: ok")


if __name__ == "__main__":
    main()
