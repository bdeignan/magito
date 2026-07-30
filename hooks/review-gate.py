#!/usr/bin/env python3
"""PreToolUse hook (Bash matcher): gate landing unreviewed work.

Blocks `gitflow.sh merge`/`gitflow.sh pr`, `gh pr create`, and
`git merge <ref>` onto the base branch unless a matching review-decision
marker exists for the sha being landed. Repos opt in via
`git config magito.reviewGate true` (gitflow.sh is always gated). A leading
`cd <dir> &&` in the command shifts where later segments are judged from
(e.g. into a linked worktree). `git merge` already did this for `git -C
<path>`; this extends the same idea to a plain `cd`. Merging the base
branch's own remote-tracking ref (`git merge origin/main` while on main) is
gated like any other merge: nothing local tells a real sync apart from work
someone pushed straight to origin. Use `git pull` to sync, which this hook
does not gate — see docs/adr/0009-no-base-branch-sync-exemption.md before
re-adding an exemption here. Heredoc bodies are blanked before judging, so
writing a file that merely contains a line like `gh pr create` is not
mistaken for running it. Fails open (allows silently) on any parsing, git,
or filesystem error.

The marker lives at `<main-worktree-root>/.magito/review-<branch-slug>` and
holds one line, `<sha> <decision>` (e.g. `1b34fba reviewed` or `1b34fba
skipped: docs-only`); a bare sha with no decision text (the pre-decision
format) reads as `reviewed`. The gate only compares the sha to HEAD — the
decision text is recorded for a human to read later, never interpreted, so a
deliberate skip lands exactly as easily as a completed review. The main
worktree is resolved explicitly (`git worktree list --porcelain` always
lists it first), not derived from cwd or `--git-common-dir`, so a review or
skip recorded inside a linked worktree still counts when landing from the
main tree, and every worktree shares one `.magito/` instead of getting its
own.
"""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

GLOBAL_FLAGS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
MERGE_IN_PROGRESS_FLAGS = ("--abort", "--continue", "--quit")
# merge flags that take a MANDATORY value as a separate token, so it must not be
# mistaken for the ref (both short and long spellings — verified against `git merge -h`
# and by observing actual merge behavior on git 2.40). -S/--gpg-sign and --log take only
# an *optional* value, attached via `-Skey`/`--log=n` with no space — never as a separate
# token — so they are deliberately excluded: listing them here would swallow the next
# token (often the ref itself), recreating the same bug this set exists to prevent. The
# `--flag=value` compound form needs no entry either way: it's one token starting with
# "-", so it never matches the bare ref check below regardless of this set's contents.
MERGE_FLAGS_WITH_ARG = {
    "-m", "--message", "-F", "--file", "-s", "--strategy", "-X", "--strategy-option",
    "--cleanup", "--into-name",
}


def read_heredoc_delimiter(line, j):
    """Read the heredoc delimiter word at index j. Returns (word, next_index).

    Handles a quoted delimiter (`<<'EOF'`, `<<"EOF"`) and a bare one, which ends
    at whitespace or a shell metacharacter. Quoting only affects expansion of the
    body, not the text bash matches the terminator against, so the quotes are
    stripped here.
    """
    n = len(line)
    if j >= n:
        return None, j
    if line[j] in ("'", '"'):
        close = line.find(line[j], j + 1)
        if close == -1:
            return None, n
        return line[j + 1:close], close + 1
    word = []
    while j < n and line[j] not in " \t;&|<>()":
        if line[j] == "\\":
            j += 1
            if j < n:
                word.append(line[j])
                j += 1
            continue
        word.append(line[j])
        j += 1
    return ("".join(word), j) if word else (None, j)


def scan_heredoc_ops(line, quote):
    """Find heredoc operators on one line. Returns (delimiters, trailing quote state).

    `quote` carries across lines so a `<<` inside a multi-line quoted string is
    not mistaken for an operator. `<<<` is a here-string — one line, never a
    heredoc — and is skipped.
    """
    found = []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if quote:
            if c == quote:
                quote = None
            i += 1
            continue
        if c in ("'", '"'):
            quote = c
            i += 1
            continue
        if c == "\\":
            i += 2
            continue
        if c == "<" and line[i + 1:i + 2] == "<":
            if line[i + 2:i + 3] == "<":
                i += 3
                continue
            j = i + 2
            dash = line[j:j + 1] == "-"  # `<<-` strips leading tabs
            if dash:
                j += 1
            while j < n and line[j] in " \t":
                j += 1
            delim, j = read_heredoc_delimiter(line, j)
            if delim is None:
                return found, quote  # unreadable — stop scanning this line
            found.append((delim, dash))
            i = j
            continue
        i += 1
    return found, quote


def strip_heredocs(cmd):
    """Blank out heredoc bodies so their contents aren't judged as commands.

    In `cat > notes.md <<'EOF' / git add -A / EOF` the middle line is text on its
    way into a file, not a command. Body and terminator lines are replaced by
    empty lines (line count preserved, so later segments still line up); the line
    that OPENS a heredoc is left alone, since it is still a command. Several
    heredocs may be opened on one line, and their bodies follow in order.

    An UNTERMINATED heredoc is deliberately left un-blanked. A `<<` that is really
    something else (`$((1<<2))` is a left shift) would otherwise swallow every
    line after it, and skipping lines is the direction that opens a bypass.
    Judging a few extra lines can only cause a false deny, which is the safe way
    for a guardrail to be wrong.

    This function and its two helpers are a deliberate byte-identical copy in
    both hooks. A shared helper module cannot live in this directory, because
    install.py registers every hooks/*.py as a PreToolUse hook — the helper
    would fire on every Bash call. Change one copy, change the other.
    """
    lines = cmd.split("\n")
    blank, tentative, pending, quote = set(), [], [], None
    for i, line in enumerate(lines):
        if pending:
            delim, dash = pending[0]
            tentative.append(i)
            if (line.lstrip("\t") if dash else line) == delim:
                blank.update(tentative)  # commit only once the terminator shows up
                tentative = []
                pending.pop(0)
            continue
        found, quote = scan_heredoc_ops(line, quote)
        pending.extend(found)
    if not blank:
        return cmd
    return "\n".join("" if i in blank else ln for i, ln in enumerate(lines))


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


def resolve_cd(tokens, cwd):
    """Resolve a bare `cd <path>` to its target directory. Return None if tokens don't match, or for `cd -` (previous-directory shorthand this hook can't resolve)."""
    if len(tokens) != 2 or tokens[0] != "cd" or tokens[1] == "-":
        return None
    path = os.path.expanduser(tokens[1])
    if not os.path.isabs(path):
        path = os.path.join(cwd, path)
    return os.path.normpath(path)


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
    # magito.baseBranch override (sticky per-repo), read fail-open like opted_in:
    # a missing key / git error raises and is swallowed, falling through to detection.
    try:
        override = git(["config", "--get", "magito.baseBranch"], cwd)
        if override:
            return override
    except Exception:
        pass
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


def main_worktree(cwd):
    """Return the absolute path of the main worktree (see the module docstring
    for why the marker lives there rather than at cwd).

    `git worktree list --porcelain` always lists it first, as a line
    `worktree <path>`. Paths may contain spaces, so the line is split on the
    first space only.
    """
    out = git(["worktree", "list", "--porcelain"], cwd)
    first_line = out.split("\n", 1)[0]
    _, path = first_line.split(" ", 1)
    return path


def marker_path(branch, cwd):
    slug = branch.replace("/", "-")
    return Path(main_worktree(cwd)) / ".magito" / f"review-{slug}"


def recorded_sha(path):
    """Return the sha recorded at path, or None if it is missing, unreadable, or empty.

    The marker holds `<sha> <decision>`, but only the sha is read: the gate must
    never judge the decision text, or a deliberate skip stops landing as easily
    as a completed review. Splitting on the first whitespace also accepts a bare
    sha with no decision word, which a hand-written marker may be.
    """
    try:
        text = path.read_text().strip()
    except OSError:
        return None
    return text.split(None, 1)[0] if text else None


def gate(branch, sha, cwd):
    """Return True if denied (deny output already printed)."""
    path = marker_path(branch, cwd)
    if recorded_sha(path) == sha:
        return False
    reason = (
        f"magito review gate: no fresh review decision for branch '{branch}' "
        f"(marker {path} is missing or stale — a new commit invalidates it). "
        "Either run the reviewing-changes skill, which records the review, or record a "
        "deliberate skip and its reason — implement-issue step 6 records either answer. "
        "Do not record 'reviewed' unless a review actually ran."
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

    cur_cwd = cwd
    for segment in split_segments(strip_heredocs(command)):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        if not tokens:
            continue

        cd_target = resolve_cd(tokens, cur_cwd)
        if cd_target is not None:
            # shifts where later segments in this command are judged from
            cur_cwd = cd_target
            continue

        if gitflow_action(tokens) is not None:
            if gate_current_branch(cur_cwd):
                return
            continue

        if is_gh_pr_create(tokens):
            if opted_in(cur_cwd) and gate_current_branch(cur_cwd):
                return
            continue

        subcmd, args, chdir = find_git_subcommand(tokens, ("merge",))
        if subcmd == "merge":
            # honor `git -C <path>`: judge the repo the merge actually targets
            repo_cwd = os.path.join(cur_cwd, os.path.expanduser(chdir)) if chdir else cur_cwd
            if any(a in MERGE_IN_PROGRESS_FLAGS for a in args):
                continue
            if not opted_in(repo_cwd):
                continue
            base = get_base_branch(repo_cwd)
            branch = current_branch(repo_cwd)
            if base is None or branch != base:
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
