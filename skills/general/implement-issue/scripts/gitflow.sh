#!/usr/bin/env bash
# Deterministic git spine for /implement-issue. Judgement (slug, message, title,
# which files) comes from the agent; this script just runs the rigid steps safely.
# Staging is always explicit — this script never runs `git add -A`/`git add .`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Best-effort ledger checkpoint (issue #65). Never aborts the git verb: any
# failure (nothing clocked in, clock/python missing) is swallowed so the git
# work still succeeds. Resolves the sibling `clock` script by this script's
# own dir, not the caller's cwd, since gitflow.sh is invoked by absolute path
# from other repos — the ledger itself is global regardless of which repo the
# git work happened in. type=$1, ref=$2 (optional), summary=$3 (optional).
checkpoint() {
  local ctype="$1" ref="${2:-}" summary="${3:-}"
  local -a args=(checkpoint --type "$ctype")
  if [ -n "$ref" ]; then args+=(--ref "$ref"); fi
  if [ -n "$summary" ]; then args+=(--summary "$summary"); fi
  python3 "$SCRIPT_DIR/clock" "${args[@]}" >/dev/null 2>&1 || true
}

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
    checkpoint checkpoint "$(git rev-parse HEAD)" "$msg"
    ;;
  push)
    guard_not_base
    git push -u origin "$(current_branch)"
    ;;
  pr)
    # pr <issue> "<title>" ["<body>"]   body is optional; when given it precedes the Closes line
    # Button-merge note: when a human merges via the GitHub button instead of
    # this script's `merge` verb, this pr checkpoint is the only ledger record
    # of the work landing — the agent can optionally add a manual merge
    # checkpoint by hand (see SKILL.md step 8), but nothing is lost if it's
    # skipped since the PR is already recorded here as a type=output event.
    guard_not_base
    issue="${1:?issue required}"; title="${2:?title required}"; body="${3:-}"
    pr_url=""
    if [ -n "$body" ]; then
      pr_url="$(gh pr create --title "$title" --body "${body}"$'\n\n'"Closes #${issue}")"
    else
      pr_url="$(gh pr create --title "$title" --body "Closes #${issue}")"
    fi
    echo "$pr_url"
    checkpoint output "$pr_url" "opened PR"
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
    checkpoint checkpoint "" "merged $branch"
    ;;
  *)
    echo "usage: gitflow.sh {branch <issue> <slug> [kind]|commit <msg> <file>...|push|pr <issue> <title> [body]|merge}" >&2
    exit 1
    ;;
esac
