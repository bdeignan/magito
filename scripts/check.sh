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
#   3. No `SKILL.md` under skills/ carries `disable-model-invocation`. Every
#      skill is model-invocable (#174), so the flag never comes back.
#   4. The paid to-issues evaluator checks its complete final response and
#      preserves a worker failure.
#   5. The paid implement evaluator passes and fails as its fake `claude` dictates,
#      in its default case and in the red-passes, plan-first, and no-intent-small
#      variants. One permission denial fails the run.
#   6. `standards.py` (in the reviewing-changes skill) prints the docs and ADRs a review checks a diff
#      against, and the doc lines that name something the diff removed or
#      renamed, including a rebuilt PR #224 case. See issue #241.
#   7. Every git-tracked *.py file opens with the PEP 723 block, right after its
#      shebang line when it has one. A block lower in the file counts as
#      missing. See issue #263.
#   8. The paid catch-up evaluator passes and fails as its fake workers dictate,
#      in its default case and in the no-journal and no-tracker variants. It
#      fails a run that changes any file outside .git/ or whose `sources:` line
#      is missing, doubled, out of order, or wrong. See issue #259.
#   9. The paid handoff evaluator passes and fails as its fake workers dictate, in its
#      default case and in the nothing-landed and long-session variants. It checks
#      the journal files on disk: one new entry, its name, its word count, and its
#      Landed, Next, and Gotcha lines. See issue #260.
#  10. `eval-intent.sh` pass/fail logic, run against fake workers that act out
#      passing and failing runs of each scenario. See issue #261.
#
# Not run here, because they start a real `claude -p` and cost money: the paid
# evals (eval-to-issues.sh, eval-implement.sh, eval-catch-up.sh, eval-handoff.sh,
# eval-intent.sh).
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

# --- 3. no SKILL.md carries disable-model-invocation -------------------------
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

check_standards() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_standards.py" 2>&1); then
    echo "standards: ok"
  else
    echo "standards: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("standards.py inputs")
  fi
}

# --- 7. every tracked *.py file opens with the PEP 723 block ----------------
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

# --- 8. the paid catch-up evaluator's pass/fail logic -----------------------
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

# --- 9. the paid handoff evaluator's pass/fail logic -------------------------
check_eval_handoff() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_eval_handoff.py" 2>&1); then
    echo "eval-handoff: ok"
  else
    echo "eval-handoff: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("eval-handoff pass/fail logic")
  fi
}

# --- 10. eval-intent pass/fail logic -----------------------------------------
check_eval_intent() {
  local out
  if out=$(python3 "$REPO_ROOT/scripts/test_eval_intent.py" 2>&1); then
    echo "eval-intent: ok"
  else
    echo "eval-intent: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("eval-intent pass/fail logic")
  fi
}

# --- run everything, then summarize ------------------------------------------
check_install
check_anti_slop
check_model_invocation
check_eval_to_issues
check_eval_implement
check_standards
check_pep723
check_eval_catch_up
check_eval_handoff
check_eval_intent

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
