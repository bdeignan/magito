#!/usr/bin/env bash
# Deterministic git spine for /implement-issue. Judgement (slug, message, title,
# which files) comes from the agent; this script just runs the rigid steps safely.
# Staging is always explicit — this script never runs `git add -A`/`git add .`.
set -euo pipefail

cmd="${1:-}"; shift || true

current_branch() { git rev-parse --abbrev-ref HEAD; }

# default_branch: best-effort detection of the repo's base branch.
# 1) origin/HEAD, if a remote is configured (local-tracker repos often have none)
# 2) init.defaultBranch, if that branch exists locally
# 3) local main, then local master
default_branch() {
  local ref
  ref="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [ -n "$ref" ]; then
    echo "${ref#origin/}"
    return
  fi
  local cfg
  cfg="$(git config init.defaultBranch 2>/dev/null || true)"
  if [ -n "$cfg" ] && git show-ref --verify --quiet "refs/heads/$cfg"; then
    echo "$cfg"
    return
  fi
  if git show-ref --verify --quiet refs/heads/main; then
    echo "main"
    return
  fi
  if git show-ref --verify --quiet refs/heads/master; then
    echo "master"
    return
  fi
  echo "main"  # last-ditch guess; a later checkout will fail loudly if wrong
}

guard_not_base() {
  local b; b="$(current_branch)"
  local base; base="$(default_branch)"
  case "$b" in
    main|master|"$base")
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
  merge)
    # merge   --no-ff merge of the current feature branch into the base branch.
    # Run from the feature branch. No conflict auto-resolution — a conflict
    # fails the script and leaves it for a human.
    guard_not_base
    [ -z "$(git status --porcelain)" ] || { echo "working tree dirty — commit or stash before merging" >&2; exit 1; }
    base="$(default_branch)"; branch="$(current_branch)"
    git checkout "$base"
    git merge --no-ff --no-edit "$branch"
    ;;
  *)
    echo "usage: gitflow.sh {branch <issue> <slug> [kind]|commit <msg> <file>...|push|pr <issue> <title>|merge}" >&2
    exit 1
    ;;
esac
