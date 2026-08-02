#!/usr/bin/env bash
# Deterministic git spine for /implement-issue. Judgement (slug, message, title,
# which files) comes from the agent; this script just runs the rigid steps safely.
# Staging is always explicit — this script never runs `git add -A`/`git add .`.
set -euo pipefail

cmd="${1:-}"; shift || true

current_branch() { git rev-parse --abbrev-ref HEAD; }

# default_branch: best-effort detection of the repo's base branch.
# 0) magito.baseBranch, if set — sticky per-repo override (git config magito.baseBranch <branch>)
# 1) origin/HEAD, if a remote is configured (local-tracker repos often have none)
# 2) init.defaultBranch, if that branch exists locally
# 3) local main, then local master
default_branch() {
  local override
  override="$(git config --get magito.baseBranch 2>/dev/null || true)"
  if [ -n "$override" ]; then
    echo "$override"
    return
  fi
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

# main_worktree: absolute path of the MAIN worktree, asked of git rather than
# derived from cwd. `git worktree list --porcelain` always lists it first, and
# still does when run from inside a linked worktree. Paths may contain spaces,
# so the line splits on the first space only. In a bare repo the first entry is
# the bare git dir itself — nothing runs a worktree fan-out from a bare repo, so
# that case is noted, not handled.
# awk rather than `head -1`: head exits after one line, which can SIGPIPE git and,
# under `set -o pipefail`, abort the script. awk drains the stream.
main_worktree() { git worktree list --porcelain | awk 'NR==1{sub(/^worktree /,""); print}'; }

marker_path() { local slug="${1//\//-}"; echo "$(main_worktree)/.magito/review-${slug}"; }

# require_review_decision: the fan-out gate (ADR 0014).
#
# A marker's PRESENCE is what makes a branch gated. `worktree add` writes one
# when it creates a branch for an unsupervised executor, so only those branches
# are gated; work done by hand never gets a marker and never meets a gate. The
# recorded sha must match HEAD, so any commit after the decision re-blocks.
#
# The decision TEXT is never read — `reviewed` and `skipped: <reason>` land
# identically. A local check cannot verify that a review happened, so judging
# the word would be theatre (ADR 0011).
require_review_decision() {
  local branch="$1" marker recorded sha
  marker="$(marker_path "$branch")"
  [ -f "$marker" ] || return 0   # no marker → not fan-out work → not gated
  recorded="$(head -1 "$marker" | cut -d' ' -f1)"
  sha="$(git rev-parse HEAD)"
  [ "$recorded" = "$sha" ] && return 0
  echo "magito review gate: branch '$branch' was created for an unsupervised executor," >&2
  echo "and has no review decision at the current commit ($marker)." >&2
  echo "Run the reviewing-changes skill against this worktree, which records the decision." >&2
  echo "Do not record 'reviewed' unless a review actually ran." >&2
  exit 1
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
  worktree)
    # worktree add <branch> [path]   create a worktree for an unsupervised executor
    # worktree remove <path> [--force]
    #
    # `add` also records that this branch is fan-out work, by writing `pending`
    # as its review decision. Nothing else marks a branch that way, which is how
    # the gate tells unsupervised work from work done by hand (ADR 0014).
    #
    # Layout is an argument, not a policy: pass a path, or set
    # `git config magito.worktreeDir <dir>`. The default puts worktrees in a
    # SIBLING directory for a technical reason rather than a stylistic one — a
    # worktree nested inside the repo lands inside git's own scan and inside
    # build-tool globs.
    # No braces in this message: a `}` inside `${1:?...}` would close the
    # expansion early and leave the stray brace in the value.
    sub="${1:?worktree needs a subcommand — add or remove}"; shift
    case "$sub" in
      add)
        branch="${1:?branch required}"; path="${2:-}"
        if [ -z "$path" ]; then
          dir="$(git config --get magito.worktreeDir 2>/dev/null || true)"
          if [ -z "$dir" ]; then
            root="$(main_worktree)"
            dir="$(dirname "$root")/$(basename "$root").worktrees"
          fi
          path="${dir}/${branch//\//-}"
        fi
        # `add -b` fails outright when the branch exists, so don't assume it's new.
        if git show-ref --verify --quiet "refs/heads/${branch}"; then
          git worktree add "$path" "$branch"
        else
          git worktree add -b "$branch" "$path"
        fi
        marker="$(marker_path "$branch")"
        mkdir -p "$(dirname "$marker")"
        printf 'pending\n' > "$marker"
        echo "$path"
        ;;
      remove)
        path="${1:?path required}"; shift
        # Read the branch before removal, while the worktree still exists.
        branch="$(git -C "$path" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
        # git's own removal, never `rm -rf`: it REFUSES a dirty worktree unless
        # --force, so an executor's uncommitted work fails loudly instead of
        # being destroyed silently. --force is only ever passed through from the
        # caller, never added here.
        git worktree remove "$path" "$@"
        if [ -n "$branch" ]; then rm -f "$(marker_path "$branch")"; fi
        git worktree prune
        ;;
      *)
        echo "usage: worktree {add <branch> [path]|remove <path> [--force]}" >&2
        exit 1
        ;;
    esac
    ;;
  pr)
    # pr <issue> "<title>" ["<body>"]   body is optional; when given it precedes the Closes line
    guard_not_base
    require_review_decision "$(current_branch)"
    issue="${1:?issue required}"; title="${2:?title required}"; body="${3:-}"
    # Build the PR body once (a given body precedes the Closes line).
    if [ -n "$body" ]; then
      pr_body="${body}"$'\n\n'"Closes #${issue}"
    else
      pr_body="Closes #${issue}"
    fi
    # Only override gh's base when magito.baseBranch is set; otherwise omit
    # --base so gh targets the repo's real GitHub default branch, rather than
    # force a possibly-stale local origin/HEAD (default_branch's detection).
    base="$(git config --get magito.baseBranch 2>/dev/null || true)"
    if [ -n "$base" ]; then
      pr_url="$(gh pr create --base "$base" --title "$title" --body "$pr_body")"
    else
      pr_url="$(gh pr create --title "$title" --body "$pr_body")"
    fi
    echo "$pr_url"
    ;;
  merge)
    # merge   --no-ff merge of the current feature branch into the base branch.
    # Run from the feature branch. No conflict auto-resolution — a conflict
    # fails the script and leaves it for a human.
    guard_not_base
    require_review_decision "$(current_branch)"
    [ -z "$(git status --porcelain)" ] || { echo "working tree dirty — commit or stash before merging" >&2; exit 1; }
    base="$(default_branch)"; branch="$(current_branch)"
    git checkout "$base"
    git merge --no-ff --no-edit "$branch"
    ;;
  *)
    echo "usage: gitflow.sh {branch <issue> <slug> [kind]|commit <msg> <file>...|push|pr <issue> <title> [body]|merge|worktree add <branch> [path]|worktree remove <path> [--force]}" >&2
    exit 1
    ;;
esac
