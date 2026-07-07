#!/usr/bin/env bash
# Deterministic gh-tracker spine, sibling to gitflow.sh. Wraps the issue verbs
# weaker agents retry freehand: create/list/view/comment/close, plus a generic
# pr-create. Mandatory args only — missing arg or missing auth fails loudly,
# never opens an interactive editor or retry-loops.
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
  pr)
    # pr <title> <body>   generic PR creation, no issue-closing link.
    # For the branch-lifecycle PR that closes the issue being implemented,
    # use gitflow.sh's `pr <issue> <title>` instead.
    check_auth
    title="${1:?title required}"; body="${2:?body required}"
    gh pr create --title "$title" --body "$body"
    ;;
  *)
    echo "usage: issues.sh {create <title> <body>|list [gh-list-args...]|view <number>|comment <number> <body>|close <number>|pr <title> <body>}" >&2
    exit 1
    ;;
esac
