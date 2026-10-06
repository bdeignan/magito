#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Tests for worker.py standards: the docs and stale doc lines a review checks. Stdlib only."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

WORKER = Path(__file__).resolve().parent.parent / "skills" / "general" / "implement" / "scripts" / "worker.py"
H1 = "## Standards docs"
H2 = "## ADRs, newest first within each chain"
H3 = "## Doc lines that name something this diff removed or renamed"
RESULTS: list[bool] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"{'ok' if ok else 'not ok'} - {label}")
    if not ok and detail:
        print("    " + detail.replace("\n", "\n    "))
    RESULTS.append(ok)


class Repo:
    """A throwaway git repo on main, committed to by write()/delete()/move()."""

    def __init__(self, tmp: Path):
        self.root = (tmp / "repo").resolve()
        self.root.mkdir()
        self.env = dict(os.environ)
        self.env.update(
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
            GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"), GIT_CONFIG_NOSYSTEM="1",
        )
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.root, env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def write(self, files: dict[str, str], msg: str = "c") -> str:
        for rel, text in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            self.git("add", rel)
        self.git("commit", "-q", "--allow-empty", "-m", msg)
        return self.head()

    def delete(self, rel: str) -> str:
        self.git("rm", "-q", rel)
        self.git("commit", "-q", "-m", "rm")
        return self.head()

    def move(self, old: str, new: str) -> str:
        (self.root / new).parent.mkdir(parents=True, exist_ok=True)
        self.git("mv", old, new)
        self.git("commit", "-q", "-m", "mv")
        return self.head()

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").strip()

    def standards(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(WORKER), "standards", *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True)


def section(out: str, heading: str) -> list[str]:
    """The lines under one heading, up to the next heading, with blank lines kept."""
    lines = out.splitlines()
    if heading not in lines:
        return ["<missing heading>"]
    body = []
    for line in lines[lines.index(heading) + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    while body and body[-1] == "":
        body.pop()
    while body and body[0] == "":
        body.pop(0)
    return body


def fresh() -> tuple[tempfile.TemporaryDirectory, Repo]:
    t = tempfile.TemporaryDirectory()
    return t, Repo(Path(t.name))


def main() -> int:
    # Usage errors exit 2.
    t, repo = fresh()
    with t:
        repo.write({"a.txt": "a\n"})
        r = repo.standards()
        check(r.returncode == 2 and r.stdout == "", "no base: exits 2 and prints nothing on stdout", r.stderr)
        r = repo.standards("no-such-ref")
        check(r.returncode == 2 and r.stdout == "", "a base git cannot resolve: exits 2", r.stderr)

    # Case 1: a diff that touches nothing relevant.
    t, repo = fresh()
    with t:
        base = repo.write({"CLAUDE.md": "rules\n", "docs/agents/GLOSSARY.md": "g\n",
                           "docs/agents/CONVENTIONS.md": "c\n", "code.txt": "x\n"})
        repo.write({"code.txt": "y\n"})
        r = repo.standards(base)
        check(r.returncode == 0, "nothing relevant: exits 0", r.stderr)
        check(section(r.stdout, H1) == ["CLAUDE.md", "docs/agents/GLOSSARY.md", "docs/agents/CONVENTIONS.md"],
              "nothing relevant: section 1 lists the three docs in order", r.stdout)
        check(section(r.stdout, H2) == ["None."] and section(r.stdout, H3) == ["None."],
              "nothing relevant: sections 2 and 3 print None.", r.stdout)
        lines = r.stdout.splitlines()
        check([l for l in lines if l.startswith("## ")] == [H1, H2, H3],
              "the three headings appear once each, in order", r.stdout)

    # Case 2: which instruction file is listed.
    for files, want, label in (
        ({"AGENTS.md": "a\n"}, ["AGENTS.md"], "AGENTS.md alone is listed"),
        ({"AGENTS.md": "a\n", "CLAUDE.md": "c\n"}, ["CLAUDE.md"], "with both, only CLAUDE.md is listed"),
        ({"other.txt": "o\n"}, ["None."], "with neither and no agent docs, section 1 prints None."),
    ):
        t, repo = fresh()
        with t:
            base = repo.write(files)
            repo.write({"other.txt": "changed\n"})
            r = repo.standards(base)
            check(r.returncode == 0 and section(r.stdout, H1) == want, label, r.stdout + r.stderr)

    # Case 3: a renamed file is searched by its old path and its old file name stem.
    t, repo = fresh()
    with t:
        base = repo.write({"agents/old-agent.md": "x\n",
                           "docs/guide.md": "see agents/old-agent.md\nthe old-agent subagent\nunrelated\n"})
        repo.move("agents/old-agent.md", "agents/new-agent.md")
        r = repo.standards(base)
        s3 = section(r.stdout, H3)
        check("`agents/old-agent.md`" in s3 and "docs/guide.md:1: see agents/old-agent.md" in s3,
              "rename: the old path is searched", r.stdout)
        check("`old-agent`" in s3 and "docs/guide.md:2: the old-agent subagent" in s3,
              "rename: the old file name without its extension is searched", r.stdout)
        check(not any("unrelated" in l for l in s3), "rename: a line with no name is not printed", r.stdout)

    # Case 4: the single-word filter.
    t, repo = fresh()
    with t:
        base = repo.write({"notes.md": "use `git` and `some-name` and `a_b` here\n",
                           "docs/ref.md": "git is a tool\nsome-name lives here\na_b too\n"})
        repo.write({"notes.md": "nothing here now\n"})
        r = repo.standards(base)
        s3 = section(r.stdout, H3)
        check("`some-name`" in s3 and "docs/ref.md:2: some-name lives here" in s3,
              "filter: a vanished term with a dash is searched", r.stdout)
        check("`a_b`" in s3, "filter: a vanished term with an underscore is searched", r.stdout)
        check("`git`" not in s3 and not any(l.endswith("git is a tool") for l in s3),
              "filter: a vanished single plain word is not searched", r.stdout)

    # Case 5: hits under docs/adr/ and docs/intent/ are never printed.
    t, repo = fresh()
    with t:
        base = repo.write({"notes.md": "the `gone-term` rule\n",
                           "docs/adr/0001-x.md": "Status: accepted\ngone-term in an ADR\n",
                           "docs/intent/0001-y.md": "gone-term in an intent\n",
                           "docs/live.md": "gone-term in a live doc\n"})
        repo.write({"notes.md": "rewritten\n"})
        r = repo.standards(base)
        s3 = section(r.stdout, H3)
        check("docs/live.md:1: gone-term in a live doc" in s3, "exclusions: a live doc hit is printed", r.stdout)
        check(not any(l.startswith(("docs/adr/", "docs/intent/")) for l in s3),
              "exclusions: no hit under docs/adr/ or docs/intent/", r.stdout)

    # Case 6: ADR links in both directions, chains, and a missing Status line.
    t, repo = fresh()
    with t:
        base = repo.write({
            "tool.sh": "echo 1\n",
            "docs/adr/0001-old.md": "# Old\n\n**Status:** superseded by ADR-0003\n\nUses tool.sh.\n",
            "docs/adr/0002-other.md": "# Other\n\nUses tool.sh too.\n",
            "docs/adr/0003-new.md": "# New\n\nStatus: accepted. Says nothing of the old one.\n",
            "docs/adr/0004-later.md": "# Later\n\nStatus: accepted. Replaces ADR 2.\n",
            "docs/adr/0005-unrelated.md": "# Unrelated\n\nStatus: accepted\n",
        })
        repo.write({"tool.sh": "echo 2\n"})
        r = repo.standards(base)
        s2 = section(r.stdout, H2)
        want = [
            "docs/adr/0004-later.md — Status: accepted. Replaces ADR 2.",
            "docs/adr/0002-other.md — Status: none",
            "",
            "docs/adr/0003-new.md — Status: accepted. Says nothing of the old one.",
            "docs/adr/0001-old.md — Status: superseded by ADR-0003",
        ]
        check(s2 == want, "ADRs: both link directions, chains newest first, Status: none", "\n".join(s2))
        check(not any("0005" in l for l in s2), "ADRs: an unlinked ADR is not listed", r.stdout)

    # Case 7: a generic file name seeds only ADRs that name it with its folder.
    t, repo = fresh()
    with t:
        base = repo.write({
            "x/SKILL.md": "a\n",
            "docs/adr/0001-folder.md": "Status: accepted\nSee x/SKILL.md.\n",
            "docs/adr/0002-bare.md": "Status: accepted\nEvery SKILL.md has frontmatter.\n",
        })
        repo.write({"x/SKILL.md": "b\n"})
        s2 = section(repo.standards(base).stdout, H2)
        check(s2 == ["docs/adr/0001-folder.md — Status: accepted"],
              "generic name: only the ADR naming x/SKILL.md is seeded", "\n".join(s2))

    # Case 8: the PR #224 case, rebuilt.
    t, repo = fresh()
    with t:
        base = repo.write({
            "skills/implement/SKILL.md": "Then run `reviewing-changes` on the diff.\n",
            "docs/agents/CONVENTIONS.md": "intro\n`reviewing-changes` and `verifying` fire inside build\n",
        })
        repo.write({"skills/implement/SKILL.md": "Then review with another family.\n"})
        r = repo.standards(base)
        s3 = section(r.stdout, H3)
        check(s3[:2] == ["`reviewing-changes`",
                         "docs/agents/CONVENTIONS.md:2: `reviewing-changes` and `verifying` fire inside build"],
              "PR #224 case: the stale CONVENTIONS.md line is printed under its name", r.stdout)

    # Case 9: a diverged base is judged at the merge base, not at the base's tip.
    t, repo = fresh()
    with t:
        repo.write({"notes.md": "keep `old-term` here\n", "docs/live.md": "old-term is described\n"})
        repo.git("checkout", "-q", "-b", "feature")
        repo.write({"code.txt": "feature work\n"})
        repo.git("checkout", "-q", "main")
        repo.write({"notes.md": "main dropped it\n"})
        repo.git("checkout", "-q", "feature")
        r = repo.standards("main")
        check(r.returncode == 0 and section(r.stdout, H3) == ["None."],
              "diverged base: a term removed only on the base branch is not reported", r.stdout + r.stderr)

    # A deleted Markdown file counts as mentioning nothing at HEAD.
    t, repo = fresh()
    with t:
        base = repo.write({"old-guide.md": "run `make-thing`\n",
                           "docs/live.md": "make-thing builds it\nsee old-guide.md\n"})
        repo.delete("old-guide.md")
        s3 = section(repo.standards(base).stdout, H3)
        check("docs/live.md:1: make-thing builds it" in s3 and "`old-guide.md`" in s3,
              "deleted file: its terms and its path are searched", "\n".join(s3))

    failed = RESULTS.count(False)
    print(f"test_worker_standards: {len(RESULTS) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
