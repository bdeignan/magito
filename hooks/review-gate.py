#!/usr/bin/env python3
"""PreToolUse hook (Bash matcher): gate landing unreviewed work.

Blocks `gitflow.sh merge`/`gitflow.sh pr`, `gh pr create`, and
`git merge <ref>` onto the base branch unless a matching reviewing-changes
marker exists for the sha being landed. Repos opt in via
`git config magito.reviewGate true` (gitflow.sh is always gated). Fails
open (allows silently) on any parsing, git, or filesystem error.
"""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

GLOBAL_FLAGS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
MERGE_IN_PROGRESS_FLAGS = ("--abort", "--continue", "--quit")
# merge flags that consume the next token, so it must not be mistaken for the ref
MERGE_FLAGS_WITH_ARG = {"-m", "-F", "-X", "-s", "-S", "--gpg-sign", "--log", "--cleanup", "--into-name"}


def split_segments(cmd):
    """Split a shell command on ; && || | and newlines, respecting quotes."""
    segments, current, quote = [], [], None
    i, n = 0, len(cmd)
    while i < n:
        c = cmd[i]
        if quote:
            current.append(c)
            quote = None if c == quote else quote
            i += 1
            continue
        if c in ("'", '"'):
            quote = c
            current.append(c)
        elif cmd[i:i + 2] in ("&&", "||"):
            segments.append("".join(current))
            current = []
            i += 1  # extra advance below covers the 2nd operator char
        elif c in (";", "|", "\n"):
            segments.append("".join(current))
            current = []
        else:
            current.append(c)
        i += 1
    segments.append("".join(current))
    return segments


def find_git_subcommand(tokens, names):
    """Return (subcommand, rest_args, chdir) if tokens is `git [globals] <name> ...`."""
    if not tokens or tokens[0] != "git":
        return None, [], None
    i, chdir = 1, None
    while i < len(tokens):
        tok = tokens[i]
        if tok in names:
            return tok, tokens[i + 1:], chdir
        if tok.startswith("-"):
            if tok == "-C" and i + 1 < len(tokens):
                chdir = tokens[i + 1]
            i += 2 if tok in GLOBAL_FLAGS_WITH_ARG else 1
            continue
        return None, [], None
    return None, [], None


def gitflow_action(tokens):
    """Return 'merge'/'pr' if tokens invoke .../gitflow.sh merge|pr, else None."""
    for i, tok in enumerate(tokens):
        if os.path.basename(tok) == "gitflow.sh" and i + 1 < len(tokens) and tokens[i + 1] in ("merge", "pr"):
            return tokens[i + 1]
    return None


def is_gh_pr_create(tokens):
    for i, tok in enumerate(tokens):
        if os.path.basename(tok) == "gh" and tokens[i + 1:i + 3] == ["pr", "create"]:
            return True
    return False


def git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def ref_exists(ref, cwd):
    try:
        git(["show-ref", "--verify", "--quiet", ref], cwd)
        return True
    except Exception:
        return False


def opted_in(cwd):
    try:
        return git(["config", "--get", "magito.reviewGate"], cwd) == "true"
    except Exception:
        return False


def get_base_branch(cwd):
    try:
        ref = git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd)
        return ref[len("origin/"):] if ref.startswith("origin/") else ref
    except Exception:
        pass
    if ref_exists("refs/heads/main", cwd):
        return "main"
    if ref_exists("refs/heads/master", cwd):
        return "master"
    return None  # no discoverable base — fail open, don't gate


def current_branch(cwd):
    return git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)


def marker_path(branch, cwd):
    # --git-common-dir so a marker written inside a linked worktree is seen
    # when merging from the main checkout (and vice versa)
    slug = branch.replace("/", "-")
    git_dir = git(["rev-parse", "--git-common-dir"], cwd)
    return (Path(cwd) / git_dir / "magito" / f"reviewed-{slug}").resolve()


def gate(branch, sha, cwd):
    """Return True if denied (deny output already printed)."""
    path = marker_path(branch, cwd)
    try:
        reviewed_sha = path.read_text().strip()
    except OSError:
        reviewed_sha = None
    if reviewed_sha == sha:
        return False
    reason = (
        f"magito review gate: no fresh reviewing-changes review for branch '{branch}' "
        f"(marker {path} is missing or stale — a new commit invalidates it). "
        "Run the reviewing-changes skill against the branch point, then retry."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    return True


def gate_current_branch(cwd):
    branch = current_branch(cwd)
    sha = git(["rev-parse", "HEAD"], cwd)
    return gate(branch, sha, cwd)


def main():
    payload = json.load(sys.stdin)
    command = payload["tool_input"]["command"]
    cwd = payload["cwd"]
    if not isinstance(command, str) or not isinstance(cwd, str):
        return

    for segment in split_segments(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        if not tokens:
            continue

        if gitflow_action(tokens) is not None:
            if gate_current_branch(cwd):
                return
            continue

        if is_gh_pr_create(tokens):
            if opted_in(cwd) and gate_current_branch(cwd):
                return
            continue

        subcmd, args, chdir = find_git_subcommand(tokens, ("merge",))
        if subcmd == "merge":
            # honor `git -C <path>`: judge the repo the merge actually targets
            repo_cwd = os.path.join(cwd, os.path.expanduser(chdir)) if chdir else cwd
            if any(a in MERGE_IN_PROGRESS_FLAGS for a in args):
                continue
            if not opted_in(repo_cwd):
                continue
            base = get_base_branch(repo_cwd)
            if base is None or current_branch(repo_cwd) != base:
                continue
            ref, skip = None, False
            for a in args:
                if skip:
                    skip = False
                elif a in MERGE_FLAGS_WITH_ARG:
                    skip = True
                elif not a.startswith("-"):
                    ref = a
                    break
            if ref is None:
                continue
            sha = git(["rev-parse", ref], repo_cwd)
            if gate(ref, sha, repo_cwd):
                return


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
