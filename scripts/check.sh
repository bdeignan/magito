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
check_install() {
  local out
  if out=$(python3 "$REPO_ROOT/install.py" --dry-run 2>&1); then
    echo "install.py --dry-run: ok"
  else
    echo "install.py --dry-run: FAILED"
    echo "$out" | sed 's/^/    /'
    FAILURES+=("install.py --dry-run exited non-zero")
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

# --- run everything, then summarize ------------------------------------------
check_install
check_anti_slop
check_hooks
check_model_invocation

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
