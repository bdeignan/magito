#!/usr/bin/env python3
"""Tests for `gitflow.sh pr`: it refuses an empty body and a title that does not
match magito.prTitlePattern (Conventional Commits when unset). Issue #207.

Each case runs the real script in a throwaway repo on a feature branch, with a
fake `gh` first on PATH that records its arguments instead of opening a pull
request. Stdlib only."""
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITFLOW = ROOT / "skills/general/implement/scripts/gitflow.sh"

FAKE_GH = """#!/usr/bin/env bash
printf '%s\\0' "$@" > "$GH_LOG"
echo https://example.invalid/pull/1
"""

GOOD_TITLE = "fix(gitflow): refuse an empty pull request body"
GOOD_BODY = "**Why:** the body was lost.\n\n**What:** refuse it."

failures: list[str] = []


def check(ok: bool, label: str) -> None:
    if not ok:
        failures.append(label)
        print(f"FAIL: {label}")


def make_repo(tmp: Path) -> tuple[Path, dict]:
    repo = tmp / "repo"
    repo.mkdir()
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
        GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"), GIT_CONFIG_NOSYSTEM="1",
    )
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["GH_LOG"] = str(tmp / "gh.log")

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    (repo / "a.txt").write_text("a\n")
    git("add", "a.txt")
    git("commit", "-q", "-m", "chore: init")
    git("checkout", "-q", "-b", "feat/1-x")
    return repo, env


def run_pr(title: str, body: str | None, pattern: str | None = None) -> tuple[subprocess.CompletedProcess, list[str] | None]:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo, env = make_repo(tmp)
        if pattern is not None:
            subprocess.run(["git", "config", "magito.prTitlePattern", pattern], cwd=repo, env=env, check=True)
        args = ["bash", str(GITFLOW), "pr", "1", title] + ([] if body is None else [body])
        result = subprocess.run(args, cwd=repo, env=env, capture_output=True, text=True)
        log = tmp / "gh.log"
        gh_args = log.read_text().split("\0")[:-1] if log.exists() else None
        return result, gh_args


def refused(label: str, title: str, body: str | None, pattern: str | None = None, says: str = "") -> None:
    result, gh_args = run_pr(title, body, pattern)
    check(result.returncode != 0, f"{label}: exits non-zero")
    check(gh_args is None, f"{label}: gh is never called")
    if says:
        check(says in result.stderr, f"{label}: stderr mentions {says!r} (got {result.stderr.strip()!r})")


def accepted(label: str, title: str, body: str, pattern: str | None = None) -> None:
    result, gh_args = run_pr(title, body, pattern)
    check(result.returncode == 0, f"{label}: exits 0 (stderr {result.stderr.strip()!r})")
    check(gh_args is not None and title in gh_args, f"{label}: gh gets the title")
    if gh_args is not None and "--body" in gh_args:
        sent = gh_args[gh_args.index("--body") + 1]
        check(sent.startswith(body) and sent.endswith("Closes #1"), f"{label}: body precedes the Closes line")
    else:
        check(False, f"{label}: gh gets a --body")


def main() -> None:
    # The body: #206 opened with nothing but its Closes line.
    refused("no body", GOOD_TITLE, None, says="body")
    refused("empty body", GOOD_TITLE, "", says="body")
    refused("whitespace body", GOOD_TITLE, "  \n\t\n", says="body")
    refused("Closes-only body", GOOD_TITLE, "Closes #205\nCloses #199\n", says="body")
    refused("empty body with the title check off", "anything", "", pattern="off", says="body")

    # The title: Conventional Commits when magito.prTitlePattern is unset.
    refused("plain-English title", "Close two guardrail gaps", GOOD_BODY, says="title")
    refused("unknown type", "feature: add a thing", GOOD_BODY, says="title")
    refused("no summary", "fix: ", GOOD_BODY, says="title")
    accepted("conventional title", GOOD_TITLE, GOOD_BODY)
    accepted("no scope, breaking", "feat!: drop the old flag", GOOD_BODY)
    accepted("Closes lines beside real text", "docs: note it", "Say why.\n\nCloses #205")

    # Guest repos: off, or the house pattern.
    accepted("title check off", "Close two guardrail gaps", GOOD_BODY, pattern="off")
    accepted("custom pattern match", "[ABC-12] Add a thing", GOOD_BODY, pattern=r"^\[[A-Z]+-[0-9]+\] .+")
    refused("custom pattern miss", GOOD_TITLE, GOOD_BODY, pattern=r"^\[[A-Z]+-[0-9]+\] .+", says="title")

    if failures:
        raise SystemExit(1)
    print("test_gitflow_pr: ok")


if __name__ == "__main__":
    main()
