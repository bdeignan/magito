#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Behavior checks for the deterministic parts of the to-issues contract."""
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "skills/general/to-issues/scripts/worktree_snapshot.py"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def git(repo: Path, *args: str) -> None:
    result = run("git", *args, cwd=repo)
    if result.returncode:
        raise AssertionError(result.stderr)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        repo = Path(temp) / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "test@example.invalid")
        git(repo, "config", "user.name", "Test")
        tracked = repo / "tracked.txt"
        tracked.write_text("committed\n")
        git(repo, "add", "tracked.txt")
        git(repo, "commit", "-qm", "initial")
        (repo / ".gitignore").write_text(".scratch/\n")
        git(repo, "add", ".gitignore")
        git(repo, "commit", "-qm", "ignore drafts")

        review_dir = repo / ".scratch/0001-example"
        draft = review_dir / "drafts/01-example.md"
        draft.parent.mkdir(parents=True)
        draft.write_text("first draft\n")
        tracked.write_text("first dirty version\n")
        before = Path(temp) / "before.json"
        after = Path(temp) / "after.json"
        unchanged = Path(temp) / "unchanged.json"

        captured = run("python3", str(SNAPSHOT), "capture", str(repo), str(review_dir), str(before), cwd=repo)
        assert captured.returncode == 0, captured.stderr
        captured = run("python3", str(SNAPSHOT), "capture", str(repo), str(review_dir), str(unchanged), cwd=repo)
        assert captured.returncode == 0, captured.stderr
        compared = run("python3", str(SNAPSHOT), "compare", str(before), str(unchanged), cwd=repo)
        assert compared.returncode == 0, compared.stdout + compared.stderr

        tracked.write_text("second dirty version\n")
        draft.write_text("reviewer changed ignored draft\n")
        captured = run("python3", str(SNAPSHOT), "capture", str(repo), str(review_dir), str(after), cwd=repo)
        assert captured.returncode == 0, captured.stderr
        compared = run("python3", str(SNAPSHOT), "compare", str(before), str(after), cwd=repo)
        assert compared.returncode == 1, compared.stdout + compared.stderr
        assert "tracked.txt" in compared.stdout, compared.stdout
        assert ".scratch/0001-example/drafts/01-example.md" in compared.stdout, compared.stdout

    print("to-issues snapshot: ok")


if __name__ == "__main__":
    main()
