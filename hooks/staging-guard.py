#!/usr/bin/env python3
"""PreToolUse hook (Bash matcher): block bulk `git add`/`git commit -a`.

Enforces "stage only the files you changed" — deny -A/--all/. staging and
commit -a shortcuts so every commit lists its files explicitly. Fails open
(allows silently) on any parsing or internal error; this must never break
unrelated Bash usage.
"""
import json
import shlex
import sys

DENY_REASON = (
    "magito staging guard: stage files explicitly (git add <file>...) — "
    "bulk staging (-A/--all/. or commit -a) is blocked. List the files you "
    "actually changed."
)

# git global flags that consume the following token as a value.
GLOBAL_FLAGS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


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
    for tok in args:
        if tok in (".", "./"):
            return True
        if tok in ("--all", "--no-ignore-removal"):
            return True
        if tok.startswith("-") and not tok.startswith("--") and "A" in tok[1:]:
            return True
    return False


def is_bulk_commit(args):
    for tok in args:
        if tok == "--amend":
            continue
        if tok == "--all":
            return True
        if tok.startswith("-") and not tok.startswith("--") and "a" in tok[1:]:
            return True
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

    for segment in split_segments(command):
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
