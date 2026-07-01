#!/usr/bin/env bash
# Deterministic git spine for /implement-issue. Judgement (slug, message, title,
# which files) comes from the agent; this script just runs the rigid steps safely.
# Staging is always explicit — this script never runs `git add -A`/`git add .`.
set -euo pipefail

cmd="${1:-}"; shift || true

current_branch() { git rev-parse --abbrev-ref HEAD; }

guard_not_base() {
  local b; b="$(current_branch)"
  case "$b" in
    main|master)
      echo "refusing to operate on '$b' — create a feature branch first" >&2
      exit 1
      ;;
  esac
}

case "$cmd" in
  branch)
    # branch <issue> <slug> [kind]   kind defaults to feat
    issue="${1:?issue required}"; slug="${2:?slug required}"; kind="${3:-feat}"
    git checkout -b "${kind}/${issue}-${slug}"
    ;;
  commit)
    # commit "<message>" <file>...   stages only the listed files
    guard_not_base
    msg="${1:?message required}"; shift
    [ "$#" -gt 0 ] || { echo "commit needs explicit files — never git add -A" >&2; exit 1; }
    git add -- "$@"
    git commit -m "$msg"
    ;;
  push)
    guard_not_base
    git push -u origin "$(current_branch)"
    ;;
  pr)
    # pr <issue> "<title>"
    guard_not_base
    issue="${1:?issue required}"; title="${2:?title required}"
    gh pr create --title "$title" --body "Closes #${issue}"
    ;;
  *)
    echo "usage: gitflow.sh {branch <issue> <slug> [kind]|commit <msg> <file>...|push|pr <issue> <title>}" >&2
    exit 1
    ;;
esac
