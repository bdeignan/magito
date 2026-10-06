#!/usr/bin/env bash
# check.sh — the one command that can fail for magito.
#
# Runs magito's existing checks and exits non-zero if any of them fails. This is
# the "check" step the agentic pipeline (docs/intent/0001-agentic-pipeline.md,
# migration step 0) runs after every build step and trusts instead of anything
# else. See issue #173.
#
# Checks, in order:
#   1. `python3 install.py --dry-run` exits 0.
#   2. `anti-slop.py` reports no errors on every git-tracked *.md file, except
#      the files in SKIP_LIST below.
#   3. Each hook in hooks/ gives the expected decision for a few synthetic
#      PreToolUse stdin payloads.
#   4. No `SKILL.md` under skills/ carries `disable-model-invocation`. Every
#      skill is model-invocable (#174), so the flag never comes back.
#   5. `worker.py reviewer` picks a worker from a different family than the
#      writer's, probing candidates in roster order. See issue #183.
#   6. The to-issues review snapshot catches content edits that git status
#      cannot see, including ignored drafts and already-dirty tracked files.
#   7. The paid to-issues evaluator checks its complete final response and
#      preserves a worker failure.
#   8. The paid implement evaluator passes and fails as its fake workers dictate,
#      in its default case and in the red-passes, no-intent, and no-intent-small
#      variants. It proves a review by the record on disk, not by the response.
#   9. The paid integrate evaluator (two tickets, resume, closing rule, semantic
#      conflict) passes and fails as its fake workers dictate. It proves the
#      final review by the record on disk and fails a pull request body that
#      names a review result.
#  10. `install.py` links and registers the Codex hooks with a fail-open command, and
#      installs clean when a stanza has no hooks keys.
#  11. `gitflow.sh pr` refuses an empty body and a title that does not match
#      magito.prTitlePattern (Conventional Commits when unset). See issue #207.
#  12. `worker.py review` runs one review round, fails a reviewer that changed a
#      file, and prints only the verdict lines. See issue #209.
#  13. `gitflow.sh worktree add` puts worktrees in .magito/worktrees and keeps
#      them out of git status. A new branch starts from the base branch,
#      `--from` names another start point, and a branch already checked out is
#      reused. See issue #209 and ADR 0019.
#  14. `worker.py ready` reports each roster worker without ending on a bad
#      entry, `requires_env` is honored, and `reviewer --skip` passes over a
#      named worker. A second script counts worker starts: a passed-over
#      worker is never started, and `ready` probes each worker once. See
#      issue #213.
#  15. `worker.py start` prints one line that names the builder, the reviewer,
#      and the plan stop, and agrees with `worker.py reviewer` on every roster.
#      A second script covers a roster that cannot be loaded and values with
#      line breaks. A third compares the whole line and stderr against
#      `worker.py reviewer`. See issue #214.
#  16. `worker.py record` writes the review record into an existing marker,
#      and refuses a subagent record exactly when `worker.py reviewer` names a
#      worker. A second script covers worker names that are not one word, which
#      no command may pick or record. See issue #215.
#  17. `gitflow.sh ahead` counts the commits a branch has that its base lacks,
#      and `ahead`, `push`, and `pr` refuse a tree with uncommitted changes;
#      `pr` refuses a branch with no commit ahead. See issue #216.
#  18. `gitflow.sh merge` lands a branch built in a linked worktree by merging
#      where the base branch is already checked out.
#  19. A roster worker's `env` table reaches that worker alone, wins over an
#      inherited variable, counts for `requires_env`, and makes the entry
#      unusable when it is not a table of strings. A second script covers a
#      required variable the worker never receives. See issue #225.
#  20. `gitflow.sh commit` refuses when a file is staged that the caller did not
#      name, lists the unnamed staged files, and makes no commit. A second
#      script covers names spelled with `./`, `../`, or an absolute path, and
#      runs under /bin/bash (3.2 on macOS). A third covers file names that hold
#      a line break. See issue #229.
#  21. `worker.py standards` prints the docs and ADRs a review checks a diff
#      against, and the doc lines that name something the diff removed or
#      renamed, including a rebuilt PR #224 case. See issue #241.
#  22. Every git-tracked *.py file opens with the PEP 723 block, right after its
#      shebang line when it has one. A block lower in the file counts as
#      missing. See issue #263.
#  23. The paid catch-up evaluator passes and fails as its fake workers dictate,
#      in its default case and in the no-journal and no-tracker variants. It
#      fails a run that changes any file outside .git/ or whose `sources:` line
#      is missing, doubled, out of order, or wrong. See issue #259.
#
# Not run here, because they start real tools and can cost money: the three paid
# evals (eval-to-issues.sh, eval-implement.sh, eval-integrate.sh) and
# eval-workers.sh, which runs the worker commands against the real roster and a
# real reviewer from another model family.
#
# Collects all failures instead of stopping at the first one, prints a summary,
# and exits 1 if anything failed, 0 otherwise. Bash and the stdlib Python
# scripts already in the repo only — no new dependencies (out of scope: a test
# suite, changes to anti-slop.py/readability.py, CI, or any git hook).
set -u

# --- resolve repo root: run from any cwd -----------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT" || exit 1

# --- anti-slop skip list -----------------------------------------------------
# Files that fail anti-slop.py on purpose, because they quote or list banned
# words/phrases as teaching material rather than using them as ordinary prose.
# One path per entry; every entry carries a comment saying why.
SKIP_LIST=(
  "shared/SYSTEM-INSTRUCTIONS.md"                            # names the banned AI-marker words (delve, leverage, robust, ...) as instruction text every tool reads
  "skills/general/speaking-plainly/references/ste-rules.md"  # the slop-to-simple substitution table lists banned words/phrases as worked examples
)

FAILURES=()

is_skipped() {
  local candidate="$1" s
  for s in "${SKIP_LIST[@]}"; do
    [[ "$candidate" == "$s" ]] && return 0
  done
  return 1
}

# --- 1. install.py --dry-run -------------------------------------------------
# A fresh worktree has no install.toml — it is gitignored and machine-local — so
# this falls back to install.toml.example instead of failing. See #178.
check_install() {
  local out
  if [[ -f "$REPO_ROOT/install.toml" ]]; then
    if out=$(python3 "$REPO_ROOT/install.py" --dry-run 2>&1); then
      echo "install.py --dry-run: ok (used install.toml)"
    else
      echo "install.py --dry-run: FAILED (used install.toml)"
      echo "$out" | sed 's/^/    /'
      FAILURES+=("install.py --dry-run exited non-zero")
    fi
  else
    if out=$(python3 "$REPO_ROOT/install.py" --dry-run --config "$REPO_ROOT/install.toml.example" 2>&1); then
      echo "install.py --dry-run: ok (used install.toml.example)"
    else
      echo "install.py --dry-run: FAILED (used install.toml.example)"
      echo "$out" | sed 's/^/    /'
      FAILURES+=("install.py --dry-run exited non-zero")
    fi
  fi
}

# --- 2. anti-slop.py on every tracked markdown file -------------------------
check_anti_slop() {
  local antislop="$REPO_ROOT/skills/general/speaking-plainly/scripts/anti-slop.py"
  local failed_files=()
  local f out

  while IFS= read -r f; do
    is_skipped "$f" && continue
    if ! out=$(python3 "$antislop" "$f" 2>&1); then
      failed_files+=("$f")
      echo "anti-slop: FAILED on $f"
      echo "$out" | sed 's/^/    /'
    fi
  done < <(git ls-files '*.md')

  if [[ ${#failed_files[@]} -eq 0 ]]; then
    echo "anti-slop: ok ($(git ls-files '*.md' | wc -l | tr -d ' ') files checked, ${#SKIP_LIST[@]} skipped)"
  else
    FAILURES+=("anti-slop failed on: ${failed_files[*]}")
  fi
}

# --- 3. hook payload checks ---------------------------------------------------
# Builds a synthetic PreToolUse payload ({"tool_name": "Bash", "tool_input":
# {"command": ...}, "cwd": ...}) and pipes it into the hook. "Deny" means the
# hook printed JSON containing both "permissionDecision" and "deny"; "allow"
# means it exited 0 with empty stdout.
build_payload() {
  local command="$1" cwd="$2"
  python3 - "$command" "$cwd" <<'PYEOF'
import json
import sys
print(json.dumps({
    "tool_name": "Bash",
    "tool_input": {"command": sys.argv[1]},
    "cwd": sys.argv[2],
}))
PYEOF
}

hook_says_deny() {
  # $1: stdout from the hook
  [[ "$1" == *'"permissionDecision"'* && "$1" == *'"deny"'* ]]
}

hook_says_allow() {
  # $1: stdout from the hook, $2: its exit code
  [[ $2 -eq 0 && -z "$1" ]]
}

# Runs one hook payload check. Args: hook path, command string, expected
# ("deny" or "allow"), label for failure messages.
run_hook_case() {
  local hook="$1" command="$2" expected="$3" label="$4"
  local out code

  out=$(build_payload "$command" "$REPO_ROOT" | python3 "$hook" 2>&1)
  code=$?

  case "$expected" in
    deny)
      if hook_says_deny "$out"; then
        return 0
      fi
      echo "hooks: FAILED $label — expected deny, got exit=$code stdout=$out"
      FAILURES+=("$label")
      ;;
    allow)
      if hook_says_allow "$out" "$code"; then
        return 0
      fi
      echo "hooks: FAILED $label — expected allow, got exit=$code stdout=$out"
      FAILURES+=("$label")
      ;;
  esac
}

check_hooks() {
  local staging_guard="$REPO_ROOT/hooks/staging-guard.py"
  local review_gate="$REPO_ROOT/hooks/review-gate.py"
  local before=${#FAILURES[@]}

  # A heredoc whose BODY contains `git add -A` — the body is text on its way
  # into a file, not a command, so this must be allowed, not denied.
  local heredoc_cmd
  heredoc_cmd=$'cat > /tmp/x <<\047EOF\047\ngit add -A\nEOF'

  run_hook_case "$staging_guard" "git add -A" "deny" "staging-guard.py denies 'git add -A'"
  run_hook_case "$staging_guard" "git add README.md" "allow" "staging-guard.py allows 'git add README.md'"
  run_hook_case "$staging_guard" "$heredoc_cmd" "allow" "staging-guard.py allows a heredoc body containing 'git add -A'"
  run_hook_case "$review_gate" "git status" "allow" "review-gate.py allows 'git status'"

  if [[ ${#FAILURES[@]} -eq $before ]]; then
    echo "hooks: ok"
  fi
}

# --- 4. no SKILL.md carries disable-model-invocation -------------------------
check_model_invocation() {
  local hits
  hits=$(grep -rl "disable-model-invocation" skills --include="SKILL.md" 2>/dev/null || true)
  if [[ -z "$hits" ]]; then
    echo "model-invocation: ok"
  else
    echo "model-invocation: FAILED — disable-model-invocation found in:"
    echo "$hits" | sed 's/^/    /'
    FAILURES+=("disable-model-invocation present in: $(echo "$hits" | tr '\n' ' ')")
  fi
}

# --- 5. worker.py reviewer --------------------------------------------------
check_worker_reviewer() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_worker_reviewer.py" 2>&1); then
    echo "worker-reviewer: ok"
  else
    echo "worker-reviewer: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("worker.py reviewer selection")
  fi
}

# --- 6. to-issues contract ---------------------------------------------------
check_to_issues_contract() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_to_issues_contract.py" 2>&1); then
    echo "to-issues-contract: ok"
  else
    echo "to-issues-contract: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("to-issues review snapshot")
  fi
}

check_eval_to_issues() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_eval_to_issues.py" 2>&1); then
    echo "eval-to-issues: ok"
  else
    echo "eval-to-issues: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("eval-to-issues response handling")
  fi
}

check_eval_implement() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_eval_implement.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_eval_implement_more.py" 2>&1); then
    echo "eval-implement: ok"
  else
    echo "eval-implement: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("eval-implement pass/fail logic")
  fi
}

check_eval_integrate() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_eval_integrate.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_eval_integrate_more.py" 2>&1); then
    echo "eval-integrate: ok"
  else
    echo "eval-integrate: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("eval-integrate pass/fail logic")
  fi
}

check_install_codex_hooks() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_install_codex_hooks.py" 2>&1); then
    echo "install-codex-hooks: ok"
  else
    echo "install-codex-hooks: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("install.py Codex hook registration")
  fi
}

check_gitflow_pr() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_gitflow_pr.py" 2>&1); then
    echo "gitflow-pr: ok"
  else
    echo "gitflow-pr: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("gitflow.sh pr body and title checks")
  fi
}

check_worker_review() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_worker_review.py" 2>&1); then
    echo "worker-review: ok"
  else
    echo "worker-review: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("worker.py review round")
  fi
}

check_gitflow_worktree() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_gitflow_worktree.py" 2>&1); then
    echo "gitflow-worktree: ok"
  else
    echo "gitflow-worktree: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("gitflow.sh worktree location")
  fi
}

check_worker_ready() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_worker_ready.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_worker_probe_count.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_worker_allow_rule.py" 2>&1); then
    echo "worker-ready: ok"
  else
    echo "worker-ready: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("worker.py ready report and reviewer --skip")
  fi
}

check_worker_start() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_worker_start.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_worker_start_roster.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_worker_start_strict.py" 2>&1); then
    echo "worker-start: ok"
  else
    echo "worker-start: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("worker.py start line")
  fi
}

check_worker_record() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_worker_record.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_worker_names.py" 2>&1); then
    echo "worker-record: ok"
  else
    echo "worker-record: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("worker.py record")
  fi
}

check_gitflow_ahead() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_gitflow_ahead.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_gitflow_ahead_strict.py" 2>&1); then
    echo "gitflow-ahead: ok"
  else
    echo "gitflow-ahead: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("gitflow.sh commit test and clean-tree check")
  fi
}

check_gitflow_merge() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_gitflow_merge.py" 2>&1); then
    echo "gitflow-merge: ok"
  else
    echo "gitflow-merge: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("gitflow.sh merge from a linked worktree")
  fi
}

check_worker_env() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_worker_env.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_worker_env_more.py" 2>&1); then
    echo "worker-env: ok"
  else
    echo "worker-env: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("worker.py env table")
  fi
}

check_worker_standards() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_worker_standards.py" 2>&1); then
    echo "worker-standards: ok"
  else
    echo "worker-standards: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("worker.py standards inputs")
  fi
}

check_gitflow_commit() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_gitflow_commit.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_gitflow_commit_more.py" 2>&1 \
      && python3 "$REPO_ROOT/scripts/test_gitflow_commit_names.py" 2>&1); then
    echo "gitflow-commit: ok"
  else
    echo "gitflow-commit: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("gitflow.sh commit unnamed staged files")
  fi
}

# --- 22. every tracked *.py file opens with the PEP 723 block ----------------
check_pep723() {
  local block=$'# /// script\n# requires-python = ">=3.11"\n# ///'
  local missing=() f top
  while IFS= read -r -d '' f; do
    # Skip the shebang line when there is one; the block must come right after.
    if [[ $(head -1 "$REPO_ROOT/$f") == '#!'* ]]; then
      top=$(sed -n 2,4p "$REPO_ROOT/$f")
    else
      top=$(head -3 "$REPO_ROOT/$f")
    fi
    [[ $top == "$block" ]] || missing+=("$f")
  done < <(git -C "$REPO_ROOT" ls-files -z '*.py')
  if [[ ${#missing[@]} -eq 0 ]]; then
    echo "pep723: ok"
  else
    echo "pep723: FAILED — no PEP 723 block at the top of:"
    printf '    %s\n' "${missing[@]}"
    FAILURES+=("PEP 723 block missing in: ${missing[*]}")
  fi
}

# --- 23. the paid catch-up evaluator's pass/fail logic -----------------------
check_eval_catch_up() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_eval_catch_up.py" 2>&1); then
    echo "eval-catch-up: ok"
  else
    echo "eval-catch-up: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("eval-catch-up pass/fail logic")
  fi
}

# --- run everything, then summarize ------------------------------------------
check_install
check_anti_slop
check_hooks
check_model_invocation
check_worker_reviewer
check_to_issues_contract
check_eval_to_issues
check_eval_implement
check_eval_integrate
check_install_codex_hooks
check_gitflow_pr
check_worker_review
check_gitflow_worktree
check_worker_ready
check_worker_start
check_worker_record
check_gitflow_ahead
check_gitflow_merge
check_worker_env
check_gitflow_commit
check_worker_standards
check_pep723
check_eval_catch_up

echo
if [[ ${#FAILURES[@]} -eq 0 ]]; then
  echo "check.sh: all checks passed"
  exit 0
else
  echo "check.sh: ${#FAILURES[@]} check(s) failed:"
  for f in "${FAILURES[@]}"; do
    echo "  - $f"
  done
  exit 1
fi
