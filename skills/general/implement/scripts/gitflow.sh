#!/usr/bin/env bash
# Deterministic git spine for /implement. Judgement (slug, message, title,
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
# Inside a script: awk 'NR==1{...}' with no exit. In prose the agent runs directly: head -1.
# Two independent reasons, both pointing the same way:
#   - Correctness: this script runs under `set -euo pipefail` (line 5), so `| head -1`
#     exits after one line, can SIGPIPE git, and can abort the script. Prose commands
#     don't run under pipefail, so `| head -1` there carries no such risk — that's why
#     the five prose sites (implement/SKILL.md, reviewing-changes/SKILL.md) correctly
#     use `head -1` and should stay that way.
#   - Permissions: `head` is on Claude Code's and Codex's read-only safe list; `awk` is
#     on neither. Using `awk` in prose would turn a free command into an approval prompt.
# The awk form below has no `exit`, on purpose — an early exit re-introduces the same
# early-close this comment exists to avoid.
main_worktree() { git worktree list --porcelain | awk 'NR==1{sub(/^worktree /,""); print}'; }

marker_path() { local slug="${1//\//-}"; echo "$(main_worktree)/.magito/review-${slug}"; }

# root_path <name>   sets $root_path to the name's exact path from the repository
# root, $top. No path goes through a bare $(...), which would strip a trailing
# line break from a file name. The nearest folder that exists is resolved
# physically, so a symlink such as /tmp still matches. The parts below it, which
# a staged deletion can remove, are resolved by hand: `.` is dropped and `..`
# climbs one level.
root_path() {
  local f="$1" b d rest="" norm="" c
  case "$f" in
    */*) b="${f##*/}"; d="${f%/*}"; [ -n "$d" ] || d=/ ;;
    *) b="$f"; d=. ;;
  esac
  while [ ! -d "$d" ]; do
    case "$d" in
      */*) rest="${d##*/}/$rest"; d="${d%/*}"; [ -n "$d" ] || d=/ ;;
      *) rest="$d/$rest"; d=. ;;
    esac
  done
  d="$(CDPATH= cd -- "$d" && pwd -P && echo x)" || d="x"
  d="${d%$'\n'x}"
  while [ -n "$rest" ]; do
    c="${rest%%/*}"; rest="${rest#*/}"
    case "$c" in
      ""|.) ;;
      ..)
        if [ -n "$norm" ]; then
          case "$norm" in */*/) norm="${norm%/*/}/" ;; *) norm="" ;; esac
        else
          d="${d%/*}"
        fi
        ;;
      *) norm="$norm$c/" ;;
    esac
  done
  d="${d%/}"   # the root folder "/" joins as "/name", not "//name"
  root_path="$d/$norm$b"
  root_path="${root_path#"$top"/}"
}

# require_clean_tree <verb>: refuse a working tree with uncommitted changes.
# <verb> is the subcommand that asked (ahead, push, pr) and ends the message.
# An untracked file that git does not ignore counts. The commit test below
# rests on this: a run that built a change and never committed it has no commit
# ahead of the base, and would otherwise read as "nothing to merge".
require_clean_tree() {
  local dirty
  dirty="$(git status --porcelain)"
  [ -z "$dirty" ] && return 0
  echo "working tree dirty — commit or discard every change before $1" >&2
  printf '%s\n' "$dirty" >&2
  exit 1
}

# commits_ahead [base]: how many commits HEAD has that the base lacks. The base
# is the local branch when it exists, else origin/<base>. Echoes "<count> <base>".
commits_ahead() {
  local base="${1:-}" ref
  [ -n "$base" ] || base="$(default_branch)"
  if git show-ref --verify --quiet "refs/heads/$base"; then
    ref="refs/heads/$base"
  elif git show-ref --verify --quiet "refs/remotes/origin/$base"; then
    ref="refs/remotes/origin/$base"
  else
    echo "base branch '$base' not found" >&2
    exit 1
  fi
  echo "$(git rev-list --count "$ref..HEAD") $base"
}

# require_review_decision: the review gate (ADR 0014). It applies to every
# branch that `worktree add` created.
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
  echo "Review the branch, then record it: python3 <skills>/implement/scripts/worker.py record <worktree> <builder-family> <reviewer|subagent>" >&2
  echo "Do not record 'reviewed' unless a review actually ran." >&2
  exit 1
}

case "$cmd" in
  branch)
    # branch <issue> <slug> [kind]   kind defaults to feat
    # Naming follows magito.branchPattern, a template with {kind}, {issue}, and
    # {slug} placeholders (git config magito.branchPattern <template>). Default,
    # when unset, is {kind}/{issue}-{slug} — today's exact behaviour. A pattern
    # may legitimately omit a placeholder (e.g. BD-{issue}-{slug}); substitution
    # below just no-ops for whichever ones aren't present.
    issue="${1:?issue required}"; slug="${2:?slug required}"; kind="${3:-feat}"
    pattern="$(git config --get magito.branchPattern 2>/dev/null || true)"
    [ -n "$pattern" ] || pattern='{kind}/{issue}-{slug}'
    name="${pattern//\{kind\}/$kind}"
    name="${name//\{issue\}/$issue}"
    name="${name//\{slug\}/$slug}"
    git checkout -b "$name"
    ;;
  commit)
    # commit "<message>" <file>...   stages only the listed files, whatever
    # their state: new, modified, deleted-but-unstaged, or already staged as
    # deleted. Each path is handled on its own, because `git add` refuses a
    # path already gone from both the working tree and the index (a file
    # `git rm`'d before this call) with "pathspec did not match any files".
    # GIT_LITERAL_PATHSPECS makes every path a literal filename, so a name
    # like `*.txt` never expands to files the caller did not name.
    #   on disk             -> git add
    #   gone, still indexed -> git rm --cached (stages the deletion, whatever
    #                          the index held: " D", "MD", "AD")
    #   gone, only in HEAD  -> already staged as deleted; nothing to do
    #   none of these       -> the path matches nothing; fail loudly
    #
    # A file already staged but not named would ride along, since `git commit`
    # takes the whole index. So before staging anything, refuse when one is
    # there: a refusal leaves the index as it was. Each name becomes its exact
    # path from the repository root (see root_path), so `./x`, `../x`, and an
    # absolute path all count. A directory names no file: git's own path matching
    # would expand it, so it is not used here.
    guard_not_base
    msg="${1:?message required}"; shift
    [ "$#" -gt 0 ] || { echo "commit needs explicit files — never git add -A" >&2; exit 1; }
    export GIT_LITERAL_PATHSPECS=1
    top="$(git rev-parse --show-toplevel && echo x)"; top="${top%$'\n'x}"
    named=()
    for f in "$@"; do
      root_path "$f"
      named+=("$root_path")
    done
    # Paths are compared whole, one array element each, so a name that holds a
    # line break never matches part of another. Bash 3.2 has no associative arrays.
    unnamed=()
    while IFS= read -r -d '' p; do
      found=0
      for q in "${named[@]}"; do
        [ "$p" = "$q" ] && { found=1; break; }
      done
      [ "$found" = 1 ] || unnamed+=("$p")
    done < <(git diff --cached --name-only --no-renames -z)
    if [ "${#unnamed[@]}" -gt 0 ]; then
      echo "gitflow.sh commit: these files are staged but were not named:" >&2
      for p in "${unnamed[@]}"; do
        # One line per path: a name with a line break prints quoted, as $'a\nb'.
        case "$p" in
          *$'\n'*) printf '  %q\n' "$p" >&2 ;;
          *) printf '  %s\n' "$p" >&2 ;;
        esac
      done
      echo 'Name each one in the command to commit it, or run `git restore --staged <path>` to leave it out.' >&2
      exit 1
    fi
    for f in "$@"; do
      if [ -e "$f" ] || [ -L "$f" ]; then
        git add -- "$f"
      elif git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
        git rm -q --cached -- "$f"
      elif git cat-file -e "HEAD:./$f" 2>/dev/null; then
        :  # already staged as deleted
      else
        echo "gitflow.sh commit: '$f' matches nothing — not in the working tree, the index, or HEAD" >&2
        exit 1
      fi
    done
    git commit -m "$msg"
    ;;
  ahead)
    # ahead [base]   the commit test: print how many commits this branch has that
    # the base lacks. 0 means the run made no change to merge. Exits 0 either way;
    # refuses the base branch itself and a tree with uncommitted changes.
    guard_not_base
    require_clean_tree ahead
    counted="$(commits_ahead "${1:-}")"
    echo "${counted%% *}"
    ;;
  push)
    guard_not_base
    require_clean_tree push
    git push -u origin "$(current_branch)"
    ;;
  worktree)
    # worktree add <branch> [path] [--from <ref>]   create a worktree for a run
    # worktree remove <path> [--force]
    #
    # A new branch starts from the base branch, never from wherever the caller
    # happens to stand: a run started on another branch must not inherit its
    # commits. `--from <ref>` names another start point, as an integrated run does
    # for a ticket branch that starts from the integration branch. A branch that is
    # already checked out in a worktree is reused: `add` prints that worktree's
    # path and creates nothing, so a resumed run can call it again.
    #
    # `add` also records that this branch is fan-out work, by writing `pending`
    # as its review decision. Nothing else marks a branch that way, which is how
    # the gate tells unsupervised work from work done by hand (ADR 0014).
    #
    # Layout is an argument, not a policy: pass a path, or set
    # `git config magito.worktreeDir <dir>`. The default is
    # <main-worktree-root>/.magito/worktrees/<branch-slug>, inside the repo so an
    # IDE opened at the root shows it (ADR 0019). `.magito/` must be ignored for
    # that to be safe — git's own scan skips it, and so do tools that honor git's
    # ignore files — so `add` excludes it in .git/info/exclude when nothing else
    # ignores it yet. The same line hides the review marker written below.
    # No braces in this message: a `}` inside `${1:?...}` would close the
    # expansion early and leave the stray brace in the value.
    sub="${1:?worktree needs a subcommand — add or remove}"; shift
    case "$sub" in
      add)
        branch="${1:?branch required}"; shift
        path=""; from=""
        while [ "$#" -gt 0 ]; do
          case "$1" in
            --from) from="${2:?--from needs a branch or a commit}"; shift 2 ;;
            *)
              [ -z "$path" ] || { echo "usage: worktree add <branch> [path] [--from <ref>]" >&2; exit 1; }
              path="$1"; shift ;;
          esac
        done
        root="$(main_worktree)"
        # Probe the real paths `add` creates. A directory-only pattern cannot match
        # a folder that does not exist yet, so probe a path inside the worktree.
        slug="${branch//\//-}"
        if ! git -C "$root" check-ignore -q ".magito/worktrees/${slug}/x" \
          || ! git -C "$root" check-ignore -q ".magito/review-${slug}"; then
          exclude="$(git -C "$root" rev-parse --git-path info/exclude)"
          case "$exclude" in /*) ;; *) exclude="$root/$exclude" ;; esac
          mkdir -p "$(dirname "$exclude")"
          # A last line with no newline would swallow the entry.
          if [ -s "$exclude" ] && [ -n "$(tail -c 1 "$exclude")" ]; then printf '\n' >> "$exclude"; fi
          printf '.magito/\n' >> "$exclude"
        fi
        if [ -z "$path" ]; then
          dir="$(git config --get magito.worktreeDir 2>/dev/null || true)"
          [ -n "$dir" ] || dir="$root/.magito/worktrees"
          path="${dir}/${slug}"
        fi
        marker="$(marker_path "$branch")"
        mkdir -p "$(dirname "$marker")"
        # A branch already checked out in a worktree is reused as it is. Its marker
        # keeps whatever a review recorded; only a missing one is written. No
        # `exit` in the awk: see main_worktree above.
        existing="$(git worktree list --porcelain | awk -v b="branch refs/heads/${branch}" \
          '/^worktree /{p=substr($0,10)} $0==b{print p}')"
        if [ -n "$existing" ]; then
          [ -f "$marker" ] || printf 'pending\n' > "$marker"
          echo "$existing"
          exit 0
        fi
        # `add -b` fails outright when the branch exists, so don't assume it's new.
        if git show-ref --verify --quiet "refs/heads/${branch}"; then
          git worktree add "$path" "$branch"
        else
          if [ -z "$from" ]; then
            base="$(default_branch)"
            if git show-ref --verify --quiet "refs/heads/${base}"; then from="$base"
            elif git show-ref --verify --quiet "refs/remotes/origin/${base}"; then from="origin/${base}"
            else
              # Never fall back to the caller's HEAD: that is the branch the run
              # must not inherit commits from.
              echo "gitflow.sh worktree add: base branch '${base}' not found — set git config magito.baseBranch <branch>, or pass --from <ref>" >&2
              exit 1
            fi
          fi
          git worktree add --no-track -b "$branch" "$path" "$from"
        fi
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
        echo "usage: worktree {add <branch> [path] [--from <ref>]|remove <path> [--force]}" >&2
        exit 1
        ;;
    esac
    ;;
  pr)
    # pr <issue> "<title>" "<body>"   the body precedes the Closes line
    guard_not_base
    require_clean_tree pr
    # A branch with no commit ahead of the base holds no change: the run reports
    # its findings on the ticket instead. Same base as `ahead` with no argument.
    counted="$(commits_ahead)"
    if [ "${counted%% *}" -eq 0 ]; then
      echo "gitflow.sh pr: no commit ahead of '${counted#* }' — nothing to open; report the findings instead" >&2
      exit 1
    fi
    require_review_decision "$(current_branch)"
    issue="${1:?issue required}"; title="${2:?title required}"; body="${3:-}"
    # The body must say something beyond Closes lines, in every mode. #206
    # opened with only its Closes line after a shell error dropped the text,
    # and nothing noticed until after the merge (#207). A closing line is any
    # keyword GitHub honors, in any case: close/fix/resolve and their -s/-d forms.
    said="$(printf '%s\n' "$body" | grep -Eiv '^[[:space:]]*(close[sd]?|fix(e[sd])?|resolve[sd]?):?[[:space:]]+([[:alnum:]_.-]+/[[:alnum:]_.-]+)?#[0-9]+[[:space:]]*\.?[[:space:]]*$' | tr -d '[:space:]' || true)"
    if [ -z "$said" ]; then
      echo "gitflow.sh pr: the body is empty — write the Why and What for the reviewer (references/pr-body.md)" >&2
      exit 1
    fi
    # The title must match magito.prTitlePattern, an extended regex. Unset means
    # Conventional Commits; `off` skips the check, for a guest repo whose house
    # style is something else (git config magito.prTitlePattern off).
    pattern="$(git config --get magito.prTitlePattern 2>/dev/null || true)"
    [ -n "$pattern" ] || pattern='^(feat|fix|docs|chore|refactor|test|perf|build|ci|style|revert)(\([^)]+\))?!?: [^[:space:]].*$'
    if [ "$(printf '%s' "$pattern" | tr '[:upper:]' '[:lower:]')" != "off" ]; then
      # [[ =~ ]] returns 1 for no match and 2 for a regex it cannot compile.
      matched=0; [[ "$title" =~ $pattern ]] || matched=$?
      if [ "$matched" -eq 2 ]; then
        echo "gitflow.sh pr: magito.prTitlePattern is not a valid extended regex: $pattern" >&2
        exit 1
      elif [ "$matched" -ne 0 ]; then
        echo "gitflow.sh pr: the title '$title' does not match magito.prTitlePattern: $pattern" >&2
        echo "  e.g. 'fix(gitflow): refuse an empty pull request body' (references/pr-body.md)" >&2
        exit 1
      fi
    fi
    pr_body="${body}"$'\n\n'"Closes #${issue}"
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
    # merge   merges the current feature branch into the base branch, per
    # magito.mergeStrategy (git config magito.mergeStrategy <no-ff|squash|ff-only>).
    # Default, when unset, is no-ff — today's exact behaviour. Run from the
    # feature branch. No conflict auto-resolution — a conflict fails the
    # script and leaves it for a human.
    #   no-ff   — merge commit, always (unchanged from before this was configurable)
    #   squash  — `git merge --squash` leaves the changes staged but does NOT
    #             commit, so this path makes the commit itself
    #   ff-only — fails loudly when a fast-forward isn't possible; that failure
    #             is correct behaviour, not a bug to route around
    #
    # A run builds in a linked worktree while the main checkout sits on the base
    # branch, and git refuses to check a branch out twice. So when the base is
    # already checked out in another worktree, the merge runs there. Untracked
    # files in that worktree are the user's own and do not block the merge;
    # uncommitted changes to tracked files do.
    guard_not_base
    require_review_decision "$(current_branch)"
    [ -z "$(git status --porcelain)" ] || { echo "working tree dirty — commit or stash before merging" >&2; exit 1; }
    strategy="$(git config --get magito.mergeStrategy 2>/dev/null || true)"
    [ -n "$strategy" ] || strategy="no-ff"
    case "$strategy" in
      no-ff|squash|ff-only) ;;
      *)
        echo "magito.mergeStrategy '$strategy' is invalid — use one of: no-ff, squash, ff-only" >&2
        exit 1
        ;;
    esac
    base="$(default_branch)"; branch="$(current_branch)"
    # No `exit` in the awk: see main_worktree above.
    base_dir="$(git worktree list --porcelain | awk -v b="branch refs/heads/${base}" \
      '/^worktree /{p=substr($0,10)} $0==b{print p}')"
    if [ -n "$base_dir" ]; then
      if ! git -C "$base_dir" diff --quiet || ! git -C "$base_dir" diff --cached --quiet; then
        echo "the worktree that holds '$base' has uncommitted changes to tracked files — commit or stash them before merging: $base_dir" >&2
        exit 1
      fi
      cd "$base_dir"
    else
      git checkout "$base"
    fi
    case "$strategy" in
      no-ff)
        git merge --no-ff --no-edit "$branch"
        ;;
      squash)
        # `--squash` stages every changed file itself. That is git's own merge
        # mechanism, not a relaxation of this script's explicit-staging rule —
        # the files were already reviewed as commits on the feature branch.
        git merge --squash "$branch"
        # A generated subject, so the base branch gets a non-conventional commit
        # here. Squashing collapses the branch's conventional commits into one;
        # if that matters, merge through the forge UI instead.
        git commit -m "Squash merge branch '$branch'"
        ;;
      ff-only)
        git merge --ff-only "$branch"
        ;;
    esac
    ;;
  *)
    echo "usage: gitflow.sh {branch <issue> <slug> [kind]|commit <msg> <file>...|ahead [base]|push|pr <issue> <title> <body>|merge|worktree add <branch> [path] [--from <ref>]|worktree remove <path> [--force]}" >&2
    exit 1
    ;;
esac
