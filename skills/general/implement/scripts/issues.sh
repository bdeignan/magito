#!/usr/bin/env bash
# Deterministic gh-tracker spine, sibling to gitflow.sh. Wraps the issue verbs
# weaker agents retry freehand: create/list/view/comment/close. PR creation
# stays in gitflow.sh's `pr <issue> <title>` — that's the only PR-creation
# path review-gate.py's hook recognizes (it pattern-matches the literal Bash
# command string), so a second wrapper here would silently bypass the gate.
# Mandatory args only — missing arg or missing auth fails loudly, never opens
# an interactive editor or retry-loops.
set -euo pipefail

cmd="${1:-}"; shift || true

check_auth() {
  if ! gh auth status >/dev/null 2>&1; then
    echo "gh is not authenticated — run 'gh auth login' first" >&2
    exit 1
  fi
}

case "$cmd" in
  create)
    # create <title> <body>
    check_auth
    title="${1:?title required}"; body="${2:?body required}"
    gh issue create --title "$title" --body "$body"
    ;;
  list)
    check_auth
    gh issue list "$@"
    ;;
  view)
    # view <number>
    check_auth
    number="${1:?issue number required}"
    gh issue view "$number"
    ;;
  comment)
    # comment <number> <body>
    check_auth
    number="${1:?issue number required}"; body="${2:?body required}"
    gh issue comment "$number" --body "$body"
    ;;
  close)
    # close <number>
    check_auth
    number="${1:?issue number required}"
    gh issue close "$number"
    ;;
  sub-add)
    # sub-add <parent-number> <child-number> — link child as a native GitHub sub-issue
    check_auth
    parent="${1:?parent issue number required}"; child="${2:?child issue number required}"
    repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
    child_id="$(gh api "repos/${repo}/issues/${child}" -q .id)"
    gh api -X POST "repos/${repo}/issues/${parent}/sub_issues" -F sub_issue_id="${child_id}"
    ;;
  *)
    echo "usage: issues.sh {create <title> <body>|list [gh-list-args...]|view <number>|comment <number> <body>|close <number>|sub-add <parent> <child>}" >&2
    exit 1
    ;;
esac
