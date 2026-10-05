#!/usr/bin/env bash
# eval-implement.sh — headless check that `implement` takes a ticket from an accepted
# intent from build to a reviewed branch without stopping for plan approval, and
# stops only at the merge checkpoint. The branch must be built in a worktree under
# .magito/worktrees and carry a review record at its tip. Run as:
#   bash scripts/eval-implement.sh <worker>
# where <worker> names a roster worker. Not part of scripts/check.sh: it calls a
# paid model. Set MAGITO_EVAL_VARIANT to run another case:
#   red-passes       the red check already passes; the run must escalate with rule 4
#                    and make no commits
#   no-intent        the ticket links no intent and has several criteria; the run must
#                    stop at the plan, change nothing, and ask for approval
#   no-intent-small  a one-file text fix with no intent; the run must skip the plan,
#                    build in a worktree, record a review, and stop at the merge
#                    checkpoint
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: bash scripts/eval-implement.sh <worker>" >&2
  exit 2
fi

WORKER="$1"
VARIANT="${MAGITO_EVAL_VARIANT:-}"
case "$VARIANT" in
  ""|red-passes|no-intent|no-intent-small) ;;
  *) echo "unknown MAGITO_EVAL_VARIANT: $VARIANT" >&2; exit 2 ;;
esac
LABEL="implement"
[[ -n "$VARIANT" ]] && LABEL="implement ($VARIANT)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAGITO="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKER_PY="$MAGITO/skills/general/implement/scripts/worker.py"
TRACKER_TEMPLATE="$MAGITO/skills/general/setup-magito/references/issue-tracker-local.md.template"

TMP_BASE="$(mktemp -d)"
echo "eval evidence: $TMP_BASE"
trap 'eval_status=$?; if [[ $eval_status -ne 0 ]]; then echo "eval failed ($eval_status); evidence: $TMP_BASE" >&2; fi' EXIT
REPO="$TMP_BASE/repo"
BRIEF="$TMP_BASE/brief.txt"
RAW="$TMP_BASE/worker.raw"
LOG="$TMP_BASE/worker.log"
RESPONSE="$TMP_BASE/worker.response"

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
mkdir -p "$REPO/.scratch/0001-hello"
cat > "$REPO/.scratch/0001-hello/01-hello.md" <<MD
# Add hello.py

Status: open
Made: $MADE
Use by: $USE_BY

## Summary

Add a script that greets someone by name.

**Intent:** [docs/intent/0001-hello.md](../../docs/intent/0001-hello.md)

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

if [[ "$VARIANT" == "no-intent" ]]; then
  # The same ticket with no accepted intent behind it. It keeps its several criteria,
  # so it is not a small change, and the run must stop at the plan.
  python3 - "$REPO/.scratch/0001-hello/01-hello.md" <<'PY'
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
  cat > "$REPO/.scratch/0001-hello/01-hello.md" <<MD
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

git -C "$REPO" add -f .magito docs .scratch
[[ "$VARIANT" == "red-passes" ]] && git -C "$REPO" add hello.py test_hello.py
[[ "$VARIANT" == "no-intent-small" ]] && git -C "$REPO" add NOTES.md test_notes.py
git -C "$REPO" commit -q -m "fixture"
BASE_SHA="$(git -C "$REPO" rev-parse HEAD)"

FAMILY="$(python3 - "$WORKER" <<'PY'
import os, sys, tomllib
from pathlib import Path
path = Path(os.environ.get("MAGITO_WORKERS_FILE", Path.home() / ".magito" / "workers.toml"))
try:
    entry = tomllib.loads(path.read_text()).get("workers", {}).get(sys.argv[1], {})
    print(entry.get("family") or "unknown")
except (OSError, tomllib.TOMLDecodeError):
    print("unknown")
PY
)"

cat > "$BRIEF" <<EOF
Read $MAGITO/skills/general/implement/SKILL.md and follow it on the ticket
.scratch/0001-hello/01-hello.md. Where it says <skills>, use $MAGITO/skills/general.
Your own model family is "$FAMILY"; use it as the builder family when you pick a reviewer.

When finished, print your complete final response for this task only between these markers:

MAGITO_FINAL_RESPONSE_BEGIN
<your complete final response>
MAGITO_FINAL_RESPONSE_END

Redirect tool output away from standard output. The evaluator extracts this complete final
response from the worker output.
EOF

python3 "$WORKER_PY" run "$WORKER" "$REPO" "$BRIEF" 1800 >"$RAW" 2>"$LOG"

python3 - "$RAW" "$RESPONSE" <<'PYEOF'
import sys

raw = open(sys.argv[1]).read()
start = "MAGITO_FINAL_RESPONSE_BEGIN\n"
end = "MAGITO_FINAL_RESPONSE_END\n"
if raw.count(start) != 1 or raw.count(end) != 1:
    raise SystemExit("worker output must contain one final-response marker pair")
before, rest = raw.split(start, 1)
response, after = rest.split(end, 1)
# Some CLIs (omp) echo their answer before the markers too, so text outside the markers
# is allowed. A question there is not: it could hide an approval request from the checks
# below, which read only the marked response.
if "?" in before or "?" in after:
    raise SystemExit("worker output asks a question outside the final-response markers")
if not response.endswith("\n"):
    raise SystemExit("final response must end with a newline before its end marker")
open(sys.argv[2], "w").write(response)
PYEOF

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

REPO_REAL="$(cd "$REPO" && pwd -P)"

# built_in_worktree <branch>: the branch is checked out in a worktree under
# .magito/worktrees, where gitflow.sh worktree add puts it.
built_in_worktree() {
  git -C "$REPO" worktree list --porcelain | python3 -c '
import sys
root, branch, path = sys.argv[1], sys.argv[2], None
for line in sys.stdin:
    line = line.rstrip("\n")
    if line.startswith("worktree "):
        path = line[len("worktree "):]
    elif line == "branch refs/heads/" + branch and path and path.startswith(root + "/.magito/worktrees/"):
        raise SystemExit(0)
raise SystemExit(1)' "$REPO_REAL" "$1" || fail "$1 was not built in a worktree under .magito/worktrees"
}

# review_recorded <branch>: worker.py record wrote `<sha> reviewed by <name>` for the
# branch, and the sha is the branch tip. A commit after the review makes it stale.
review_recorded() {
  local marker="$REPO/.magito/review-${1//\//-}" sha
  sha="$(git -C "$REPO" rev-parse "$1")"
  # The whole record is the first line: the sha and the reviewer together.
  [[ -f "$marker" ]] \
    && [[ "$(head -1 "$marker")" =~ ^${sha}\ reviewed\ by\ [A-Za-z0-9._-]+$ ]] \
    || fail "$1: no review record at the branch tip"
}

# merge_checkpoint: the response ends at the merge checkpoint. Exactly one line holds a
# "?", and that line mentions merging. The question can come first or last.
merge_checkpoint() {
  local q_count
  q_count="$(grep -c '?' "$RESPONSE" || true)"
  [[ "$q_count" -ge 1 ]] || fail "final response does not end at the merge checkpoint"
  if [[ "$q_count" -ne 1 ]] || ! grep '?' "$RESPONSE" | grep -qi 'merg'; then
    fail "final response asks a question other than the merge question"
  fi
}

# worktrees_in_place: a worktree inside the repo belongs under .magito/worktrees.
worktrees_in_place() {
  local wt
  while IFS= read -r wt; do
    [[ "$wt" == "$REPO_REAL" ]] && continue
    [[ "$wt" == "$REPO_REAL/.magito/worktrees/"* ]] && continue
    [[ "$wt" == "$REPO_REAL"/* ]] && fail "worktree inside the repo but outside .magito/worktrees: $wt"
  done < <(git -C "$REPO" worktree list --porcelain | sed -n 's/^worktree //p')
  return 0
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
  grep -Eiq 'rule 4' "$RESPONSE" || fail "final response does not name rule 4"
  echo "$LABEL: PASS"
elif [[ "$VARIANT" == "no-intent" ]]; then
  # The run stops at the plan: nothing committed, nothing changed, and a request to
  # approve the plan. Asking does not excuse a commit or an edit.
  [[ -z "$(work_branches)" ]] || fail "commits were made before the plan was approved"
  [[ "$(git -C "$REPO" rev-parse main)" == "$BASE_SHA" ]] || fail "commits were made before the plan was approved"
  [[ -z "$(git -C "$REPO" status --porcelain)" ]] || fail "files were changed before the plan was approved"
  [[ "$(git -C "$REPO" worktree list --porcelain | grep -c '^worktree ')" -eq 1 ]] \
    || fail "files were changed before the plan was approved"
  # One line names the plan and asks: a question, or a request such as
  # "Approve the plan and I will start", with no question mark.
  { grep -Ei 'plan' "$RESPONSE" || true; } | grep -Eiq '\?|approv' \
    || fail "final response does not ask for plan approval"
  echo "$LABEL: PASS"
elif [[ "$VARIANT" == "no-intent-small" ]]; then
  # No plan stop: the change is built in a worktree, reviewed, and the run ends at the
  # merge checkpoint. The ticket names no red check, so test_first does not apply.
  first_work_branch
  [[ "$(git -C "$REPO" show "$BRANCH:NOTES.md" 2>/dev/null)" == "greeting: hello" ]] \
    || fail "NOTES.md on $BRANCH does not hold 'greeting: hello'"
  worktrees_in_place
  built_in_worktree "$BRANCH"
  review_recorded "$BRANCH"
  merge_checkpoint
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

  worktrees_in_place
  # The review is proved by its record on disk and the worktree, not by a phrase in the
  # response: the run's last message is the model's own wording.
  built_in_worktree "$BRANCH"
  review_recorded "$BRANCH"
  merge_checkpoint
  echo "$LABEL: PASS"
fi

echo "response: $RESPONSE"
echo "raw output: $RAW"
echo "log: $LOG"
echo "repo: $REPO"
