#!/usr/bin/env bash
# eval-implement.sh — headless check that `implement` takes a ticket from an accepted
# intent to "ready to read" in the worktree Claude Code made for the run, with zero
# permission prompts. Run as:
#   bash scripts/eval-implement.sh [model]
# where [model] is the model `claude -p` runs, sonnet when left out. Not part of
# scripts/check.sh: it calls a paid model.
#
# The run is one `claude -p --worktree eval`, so the build happens in
# .claude/worktrees/eval, as a Desktop worker's does. Every case checks that the JSON
# result's permission_denials list is empty and that no .magito/worktrees folder and no
# .magito/review-* file appears. The ticket has no Risk line, so it counts as Normal: the
# run stops at "ready to read" and opens no pull request. Set MAGITO_EVAL_VARIANT to run
# another case:
#   red-passes       the red check already passes; the run must stop with stop 3 and
#                    make no commits
#   plan-first       the ticket links no intent and has several criteria, and the brief
#                    says "Show me the plan first."; the run must stop at the plan
#                    and change nothing
#   no-intent-small  a one-file text fix with no intent; the run must build in the
#                    worktree and open no pull request
set -euo pipefail

if [[ $# -gt 1 ]]; then
  echo "usage: bash scripts/eval-implement.sh [model]" >&2
  exit 2
fi

MODEL="${1:-sonnet}"
VARIANT="${MAGITO_EVAL_VARIANT:-}"
case "$VARIANT" in
  ""|red-passes|plan-first|no-intent-small) ;;
  *) echo "unknown MAGITO_EVAL_VARIANT: $VARIANT" >&2; exit 2 ;;
esac
LABEL="implement"
[[ -n "$VARIANT" ]] && LABEL="implement ($VARIANT)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAGITO="$(cd "$SCRIPT_DIR/.." && pwd)"
TRACKER_TEMPLATE="$MAGITO/skills/general/setup-magito/references/issue-tracker-local.md.template"

TMP_BASE="$(mktemp -d)"
echo "eval evidence: $TMP_BASE"
REPO="$TMP_BASE/repo"
BRIEF="$TMP_BASE/brief.txt"
TICKET="$TMP_BASE/ticket.md"
RESULT="$TMP_BASE/result.json"
LOG="$TMP_BASE/claude.log"
RESPONSE="$TMP_BASE/response.txt"
WT_NAME="eval"
WT="$REPO/.claude/worktrees/$WT_NAME"

# A `-p --worktree` run leaves its worktree locked. Remove it when the eval ends; its
# branch and commits stay behind as the evidence.
cleanup() {
  local status=$?
  git -C "$REPO" worktree unlock "$WT" >/dev/null 2>&1 || true
  git -C "$REPO" worktree remove --force "$WT" >/dev/null 2>&1 || true
  if [[ $status -ne 0 ]]; then
    echo "eval failed ($status); evidence: $TMP_BASE" >&2
  fi
  exit "$status"
}
trap cleanup EXIT

# The temp repo is kept on purpose: the branch, commits, and logs are the evidence.
git init -b main "$REPO" >/dev/null 2>&1
git -C "$REPO" config user.name "eval"
git -C "$REPO" config user.email "eval@example.invalid"
mkdir -p "$REPO/.magito" "$REPO/docs/agents" "$REPO/docs/intent"

cat > "$REPO/.magito/config.toml" <<'TOML'
mode = "owner"
tracker = "local"
check = "python3 -m unittest -q"
intent_dir = "docs/intent"
TOML

cp "$TRACKER_TEMPLATE" "$REPO/docs/agents/issue-tracker.md"

cat > "$REPO/docs/intent/0001-hello.md" <<'MD'
# Intent: hello script

Status: accepted · Opened: 2026-09-28 · Accepted: 2026-09-28

## Problem

The repo has no way to greet someone.

## Proposed outcome

A script `hello.py` that prints a greeting.

## Decisions so far

- `python3 hello.py Ada` prints `hello, Ada`.
- `python3 hello.py` with no argument prints `hello, world`.
- An empty-string argument also prints `hello, world`.
- Stdlib only.

## Out of scope

- Any other language or output format.

## Open questions

None.
MD

MADE="$(python3 -c 'import datetime; print(datetime.date.today())')"
USE_BY="$(python3 -c 'import datetime; print(datetime.date.today() + datetime.timedelta(days=14))')"
# The ticket lives outside the repo: a worker gets a local ticket's body in its brief.
cat > "$TICKET" <<MD
# Add hello.py

Status: open
Made: $MADE
Use by: $USE_BY

## Summary

Add a script that greets someone by name.

**Intent:** docs/intent/0001-hello.md

## Behavior

Create \`hello.py\` in the repo root. \`python3 hello.py Ada\` prints \`hello, Ada\`. With no
argument, and with an empty-string argument, it prints \`hello, world\`. Stdlib only.

## Done when

**Red check:** write \`test_hello.py\` first. It runs \`hello.py\` with an empty-string
argument and expects \`hello, world\`. Run \`python3 -m unittest -q\` and watch it fail
before you create \`hello.py\`.

**Reviewable check:**
1. \`python3 hello.py ""\` prints \`hello, world\`.
2. \`python3 -m unittest -q\` exits 0.

## Depends on

None.

## Out of scope

Any other output format.

Spec review: eval fixture, round 1
Publication-ID: 0001-hello/01-hello.md
MD

if [[ "$VARIANT" == "plan-first" ]]; then
  # The same ticket with no accepted intent behind it. It keeps its several criteria,
  # and the brief asks to see the plan first, so the run must stop at the plan.
  python3 - "$TICKET" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
lines = [ln for ln in p.read_text().splitlines() if not ln.startswith("**Intent:**")]
p.write_text("\n".join(lines) + "\n")
PY
fi

if [[ "$VARIANT" == "no-intent-small" ]]; then
  # A one-file text fix with no intent, one criterion, and no red check. The fixture
  # carries a passing test, so the check command exits 0 before and after the change:
  # with no test at all, `python3 -m unittest -q` exits non-zero on recent Pythons.
  cat > "$TICKET" <<MD
# Fix the greeting in NOTES.md

Status: open
Made: $MADE
Use by: $USE_BY

## Summary

The notes file spells the greeting wrong.

## Behavior

In \`NOTES.md\`, change \`helo\` to \`hello\`. Change nothing else.

## Done when

**Reviewable check:**
1. \`NOTES.md\` holds the line \`greeting: hello\`.

## Depends on

None.

## Out of scope

Any other file.

Spec review: eval fixture, round 1
Publication-ID: 0001-hello/01-hello.md
MD
  printf 'greeting: helo\n' > "$REPO/NOTES.md"
  cat > "$REPO/test_notes.py" <<'PY'
import unittest
from pathlib import Path


class NotesTest(unittest.TestCase):
    def test_notes_has_a_greeting(self):
        self.assertTrue(Path("NOTES.md").read_text().startswith("greeting:"))
PY
fi

if [[ "$VARIANT" == "red-passes" ]]; then
  # Edit the fixture so the test file already exists and passes.
  cat > "$REPO/hello.py" <<'PY'
import sys

name = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else "world"
print(f"hello, {name}")
PY
  cat > "$REPO/test_hello.py" <<'PY'
import subprocess
import sys
import unittest


class HelloTest(unittest.TestCase):
    def test_empty_argument(self):
        out = subprocess.run([sys.executable, "hello.py", ""], capture_output=True, text=True).stdout
        self.assertEqual(out.strip(), "hello, world")
PY
fi

# As in a repo setup-magito has run: .magito/ is excluded, and .worktreeinclude copies its
# config into each worktree. The run's own worktree is excluded too, so it is no change.
printf '.magito/\n.claude/worktrees/\n' >> "$REPO/.git/info/exclude"
printf '.magito/config.toml\n' > "$REPO/.worktreeinclude"
git -C "$REPO" add docs .worktreeinclude
[[ "$VARIANT" == "red-passes" ]] && git -C "$REPO" add hello.py test_hello.py
[[ "$VARIANT" == "no-intent-small" ]] && git -C "$REPO" add NOTES.md test_notes.py
git -C "$REPO" commit -q -m "fixture"
BASE_SHA="$(git -C "$REPO" rev-parse HEAD)"

cat > "$BRIEF" <<EOF
Read $MAGITO/skills/general/implement/SKILL.md and follow it on the ticket below. Where it
says <skills>, use $MAGITO/skills/general. The ticket is a local one, and this is its body:

$(<"$TICKET")
EOF
[[ "$VARIANT" == "plan-first" ]] && printf '\nShow me the plan first.\n' >> "$BRIEF"

cd "$REPO"
claude -p --model "$MODEL" --permission-mode auto --output-format json --worktree "$WT_NAME" "$(<"$BRIEF")" >"$RESULT" 2>"$LOG"
# The final reply goes to $RESPONSE, and each permission denial becomes one printed line.
DENIED="$(python3 - "$RESULT" "$RESPONSE" <<'PY'
import json
import sys

result = json.load(open(sys.argv[1]))
open(sys.argv[2], "w").write(result["result"])
if "permission_denials" not in result:
    print("denied: the result holds no permission_denials list")
for d in result.get("permission_denials", []):
    tool_input = d.get("tool_input") or {}
    print(f"denied: {d.get('tool_name', '?')}: {tool_input.get('command') or json.dumps(tool_input)}")
PY
)"

fail() { echo "$LABEL: FAIL ($1)"; exit 1; }

# Every branch that holds commits beyond the fixture commit, except main itself.
work_branches() {
  local b
  while IFS= read -r b; do
    [[ "$b" == "main" ]] && continue
    if [[ "$(git -C "$REPO" rev-list --count "$BASE_SHA..$b")" -gt 0 ]]; then
      echo "$b"
    fi
  done < <(git -C "$REPO" for-each-ref --format='%(refname:short)' refs/heads)
}

# test_first <branch> <base> <tip>: the branch's own commits, oldest first, must start with a
# commit that changes a test_*.py file and no source file, and a later commit must change one.
# A source file is a changed .py file that is not test_*.py and not conftest.py.
test_first() {
  local branch="$1" base="$2" tip="$3" sha f name first=1 has_test has_src later_src=0
  while IFS= read -r sha; do
    has_test=0; has_src=0
    while IFS= read -r f; do
      [[ "$f" == *.py ]] || continue
      name="${f##*/}"
      if [[ "$name" == test_*.py ]]; then has_test=1
      elif [[ "$name" != conftest.py ]]; then has_src=1; fi
    done < <(git -C "$REPO" show --name-only --format= "$sha")
    if [[ $first -eq 1 ]]; then
      first=0
      [[ $has_test -eq 1 && $has_src -eq 0 ]] || fail "$branch: code committed before its test"
    elif [[ $has_src -eq 1 ]]; then
      later_src=1
    fi
  done < <(git -C "$REPO" rev-list --reverse "$base..$tip")
  [[ $later_src -eq 1 ]] || fail "$branch: code committed before its test"
}

# Zero prompts: the run needed no permission it was not granted. Each denial is printed.
if [[ -n "$DENIED" ]]; then
  echo "$DENIED"
  fail "the run hit a permission prompt"
fi

# The old harness's folders never appear, in the main checkout or in the run's worktree.
for dir in "$REPO" "$WT"; do
  [[ ! -e "$dir/.magito/worktrees" ]] || fail "a .magito/worktrees folder was created"
  if compgen -G "$dir/.magito/review-*" >/dev/null; then fail "a .magito/review-* file was created"; fi
done

# built_in_session_worktree <branch>: the branch is the one checked out in the worktree
# that `claude -p --worktree` made.
built_in_session_worktree() {
  [[ "$(git -C "$WT" branch --show-current 2>/dev/null)" == "$1" ]] \
    || fail "$1 was not built in the worktree Claude Code made"
}

# no_pull_request: a Normal ticket stops at "ready to read" and opens no pull request. The
# fixture has no remote, so a pull request needs the run to add one. "Ready to read" is
# proved by the built, committed branch the other checks read, not by a phrase: the
# message is in the model's own words, and a real run that reached it never said them.
no_pull_request() {
  [[ -z "$(git -C "$REPO" remote)" ]] || fail "a remote was added; a Normal ticket opens no pull request"
}

# first_work_branch: the first branch other than main with a commit beyond main; sets BRANCH.
first_work_branch() {
  local branches b
  branches="$(git -C "$REPO" for-each-ref --format='%(refname:short)' refs/heads | grep -vx main || true)"
  [[ -n "$branches" ]] || fail "no branch other than main exists"
  BRANCH=""
  while IFS= read -r b; do
    if [[ "$(git -C "$REPO" rev-list --count "main..$b")" -ge 1 ]]; then BRANCH="$b"; break; fi
  done <<< "$branches"
  [[ -n "$BRANCH" ]] || fail "no branch has commits beyond main"
}

if [[ "$VARIANT" == "red-passes" ]]; then
  [[ -z "$(work_branches)" ]] || fail "commits were made although the red check passes"
  [[ "$(git -C "$REPO" rev-parse main)" == "$BASE_SHA" ]] || fail "main moved although the red check passes"
  grep -Eiq 'stop 3' "$RESPONSE" || fail "final response does not name stop 3"
  echo "$LABEL: PASS"
elif [[ "$VARIANT" == "plan-first" ]]; then
  # The run stops at the plan: nothing committed and nothing changed. The wording of the
  # reply is not checked: the stop itself is the evidence.
  [[ -z "$(work_branches)" ]] || fail "commits were made before the plan was approved"
  [[ "$(git -C "$REPO" rev-parse main)" == "$BASE_SHA" ]] || fail "commits were made before the plan was approved"
  [[ -z "$(git -C "$REPO" status --porcelain 2>&1)" ]] \
    && [[ -z "$(git -C "$WT" status --porcelain 2>&1)" ]] \
    || fail "files were changed before the plan was approved"
  [[ "$(git -C "$REPO" worktree list --porcelain | grep -c '^worktree ')" -eq 2 ]] \
    || fail "files were changed before the plan was approved"
  echo "$LABEL: PASS"
elif [[ "$VARIANT" == "no-intent-small" ]]; then
  # The plan is shown but nothing waits: the change is built in the run's worktree, and the
  # run ends at "ready to read". The ticket names no red check, so test_first does not apply.
  first_work_branch
  [[ "$(git -C "$REPO" show "$BRANCH:NOTES.md" 2>/dev/null)" == "greeting: hello" ]] \
    || fail "NOTES.md on $BRANCH does not hold 'greeting: hello'"
  built_in_session_worktree "$BRANCH"
  no_pull_request
  echo "$LABEL: PASS"
else
  first_work_branch
  while IFS= read -r b; do test_first "$b" "$BASE_SHA" "$b"; done < <(work_branches)

  CHECKOUT="$TMP_BASE/branch-checkout"
  mkdir -p "$CHECKOUT"
  git -C "$REPO" archive "$BRANCH" | tar -x -C "$CHECKOUT"
  [[ -f "$CHECKOUT/hello.py" ]] || fail "hello.py is missing on $BRANCH"
  OUT="$(cd "$CHECKOUT" && python3 hello.py "" 2>&1)" || fail "hello.py \"\" failed on $BRANCH"
  [[ "$OUT" == "hello, world" ]] || fail "hello.py \"\" printed '$OUT', expected 'hello, world'"

  built_in_session_worktree "$BRANCH"
  no_pull_request
  echo "$LABEL: PASS"
fi

echo "response: $RESPONSE"
echo "result: $RESULT"
echo "log: $LOG"
echo "repo: $REPO"
