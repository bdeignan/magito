#!/usr/bin/env python3
"""PreToolUse hook (Bash matcher): block bulk `git add`/`git commit -a`.

Enforces "stage only the files you changed" — deny -A/--all/. staging and
commit -a shortcuts so every commit lists its files explicitly. Heredoc
bodies are blanked before judging, so writing a file that merely contains a
line like `git add -A` is not mistaken for running it. Fails open (allows
silently) on any parsing or internal error; this must never break unrelated
Bash usage.
"""
import json
import shlex
import sys

DENY_REASON = (
    "magito staging guard: stage files explicitly (git add <file>...) — "
    "bulk staging is blocked — that means `git add` with -A, --all, or a "
    "catch-all path like `.`, `..`, `:/`, or `*`, and `git commit -a`. "
    "List the files you actually changed."
)

# git global flags that consume the following token as a value.
GLOBAL_FLAGS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

# `git add` pathspecs that mean "everything from here down", same as ".".
# Verified against real git: ":" and ":/" both anchor at the repo root with no
# filter, ".." / "../" walk up to the parent dir, and a bare "*" (whether the
# shell expanded it or git received it literally, quoted) recurses through
# every directory entry — none of these narrow the selection at all.
ADD_ALL_PATHSPECS = {".", "./", "..", "../", ":", ":/", "*"}

# Spellings of `--all` that git accepts, including unambiguous abbreviations.
# Verified via `git add --<prefix> --dry-run`: --a/--al/--all are the only
# prefixes of --all that don't collide with another git-add long option
# (--ig*, --i, --p*, --r*, --n* etc. are all ambiguous with something else).
ADD_ALL_SPELLINGS = {"--a", "--al", "--all", "--no-ignore-removal"}

# `git commit` flags whose value is a separate following token — their value
# must never be scanned for bulk-looking substrings (e.g. a commit message
# starting with "-" that happens to contain a lowercase "a"). Confirmed by
# running each against real git with a space-separated value. -S/-u and their
# long forms take only an *attached* optional value, so they're excluded.
COMMIT_VALUE_FLAGS = {
    "-m", "--message",
    "-F", "--file",
    "-C", "--reuse-message",
    "-c", "--reedit-message",
    "-t", "--template",
    "--author", "--date", "--cleanup",
    "--fixup", "--squash", "--trailer",
    "--pathspec-from-file",
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


def find_git_subcommand(tokens):
    """Return (subcommand, rest_args) if tokens is `git [globals] add|commit ...`."""
    if not tokens or tokens[0] != "git":
        return None, []
    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("add", "commit"):
            return tok, tokens[i + 1:]
        if tok.startswith("-"):
            i += 2 if tok in GLOBAL_FLAGS_WITH_ARG else 1
            continue
        return None, []  # non-flag, non-subcommand token: not the shape we match
    return None, []


def is_bulk_add(args):
    in_options = True  # flips off at a bare `--`: nothing after it is a flag
    for tok in args:
        if in_options and tok == "--":
            in_options = False
            continue
        if tok in ADD_ALL_PATHSPECS:
            return True  # a pathspec means the same thing on either side of --
        if in_options:
            if tok in ADD_ALL_SPELLINGS:
                return True
            if tok.startswith("-") and not tok.startswith("--") and "A" in tok[1:]:
                return True
    return False


def is_bulk_commit(args):
    skip_value = False  # true while the next token is a value, not a flag
    in_options = True  # flips off at a bare `--`: nothing after it is a flag
    for tok in args:
        if skip_value:
            skip_value = False
            continue
        if in_options and tok == "--":
            in_options = False
            continue
        if not in_options:
            continue  # commit has no "everything" pathspec the way add does
        if tok == "--amend":
            continue
        if tok == "--all":
            return True
        if tok in COMMIT_VALUE_FLAGS:
            skip_value = True
            continue
        if tok.startswith("-") and not tok.startswith("--"):
            # Short flags cluster (-am is -a -m), but a value-taking flag ends
            # the cluster and swallows the rest of the token (-mMessage is -m
            # with the message attached). Stop there so the value isn't read
            # as more flags.
            for i, ch in enumerate(tok[1:], start=1):
                if ch == "a":
                    return True
                if "-" + ch in COMMIT_VALUE_FLAGS:
                    break
    return False


def deny():
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": DENY_REASON,
        }
    }))


def main():
    payload = json.load(sys.stdin)
    command = payload["tool_input"]["command"]
    if not isinstance(command, str):
        return

    for segment in split_segments(strip_heredocs(command)):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue  # unbalanced quotes in this segment — not our concern
        subcmd, args = find_git_subcommand(tokens)
        if subcmd == "add" and is_bulk_add(args):
            deny()
            return
        if subcmd == "commit" and is_bulk_commit(args):
            deny()
            return


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
