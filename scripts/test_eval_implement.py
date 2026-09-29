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
red_passes = (repo / "test_hello.py").exists()


def git(*args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def commit(message, *files):
    git("add", *files)
    git("commit", "-m", message)


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
if red_passes:
    if mode == "redpass-commits":
        git("checkout", "-b", "feat/1-hello")
        (repo / "extra.txt").write_text("x\\n")
        commit("chore: extra", "extra.txt")
        response = "Stopping. Rule 4 applies.\\nShould I continue?\\n"
    elif mode == "redpass-no-rule":
        response = "Nothing to do.\\n"
    else:
        response = "Escalation, rule 4: the red check passes before any change.\\nPython says: OK.\\n"
        response += "Which way do you want to go?\\n"
else:
    if mode != "no-branch":
        git("checkout", "-b", "feat/1-hello")
        if mode == "code-before-test":
            (repo / "hello.py").write_text(CODE)
            commit("feat: add hello", "hello.py")
            (repo / "test_hello.py").write_text(TEST)
            commit("test: add hello test", "test_hello.py")
        elif mode == "combined-commit":
            (repo / "test_hello.py").write_text(TEST)
            (repo / "hello.py").write_text(CODE)
            commit("feat: add hello with its test", "test_hello.py", "hello.py")
        else:
            files = ["test_hello.py"]
            (repo / "test_hello.py").write_text(TEST)
            if mode == "test-with-conftest":
                (repo / "conftest.py").write_text("# shared fixtures\\n")
                files.append("conftest.py")
            commit("test: add hello test", *files)
            if mode != "one-commit":
                (repo / "hello.py").write_text(BAD_CODE if mode == "wrong-output" else CODE)
                commit("feat: add hello", "hello.py")
    response = "Round 1: VERDICT PASS\\nBuilt hello.py.\\n"
    if mode == "no-verdict":
        response = "Built hello.py.\\n"
    if mode == "early-question":
        response = "Is the plan fine?\\n" + response
    if mode == "no-final-question":
        response += "Done.\\n"
    elif mode == "imperative-approval":
        response += "Approve the merge and I will run gitflow.sh merge.\\n"
    else:
        response += "Ready to merge feat/1-hello into main?\\n"
    if mode == "no-branch":
        response = "Here is my plan. VERDICT PASS\\nApprove the plan?\\n"

print("MAGITO_FINAL_RESPONSE_BEGIN")
print(response, end="")
print("MAGITO_FINAL_RESPONSE_END")
'''


def run(mode: str, roster: Path, variant: str = "") -> subprocess.CompletedProcess[str]:
    env = os.environ | {"MAGITO_WORKERS_FILE": str(roster), "IMPLEMENT_FAKE_MODE": mode}
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

        # A merge checkpoint phrased as a request, not a question, also passes.
        imperative = run("imperative-approval", roster)
        assert "implement: PASS" in imperative.stdout, imperative.stdout

        # A test commit that carries a conftest.py is still test-first.
        conftest = run("test-with-conftest", roster)
        assert "implement: PASS" in conftest.stdout, conftest.stdout

        for mode, needle in [
            ("no-branch", "no branch"),
            ("one-commit", "code committed before its test"),
            ("code-before-test", "code committed before its test"),
            ("combined-commit", "code committed before its test"),
            ("wrong-output", "hello.py"),
            ("no-verdict", "VERDICT PASS"),
            ("early-question", "question before the merge checkpoint"),
            ("no-final-question", "merge checkpoint"),
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

    print("eval-implement: ok")


if __name__ == "__main__":
    main()
