#!/usr/bin/env bash
# eval-implement.sh — headless check that `implement` takes a pipeline ticket from
# build to a reviewed branch without stopping for plan approval, and stops only at
# the merge checkpoint. Run as:
#   bash scripts/eval-implement.sh <worker>
# where <worker> names a roster worker. Not part of scripts/check.sh: it calls a
# paid model. Set MAGITO_EVAL_VARIANT=red-passes to run the edge case where the red
# check already passes: the run must escalate with rule 4 and make no commits.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: bash scripts/eval-implement.sh <worker>" >&2
  exit 2
fi

WORKER="$1"
VARIANT="${MAGITO_EVAL_VARIANT:-}"
case "$VARIANT" in
  ""|red-passes) ;;
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
Do not merge.

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

if [[ "$VARIANT" == "red-passes" ]]; then
  [[ -z "$(work_branches)" ]] || fail "commits were made although the red check passes"
  [[ "$(git -C "$REPO" rev-parse main)" == "$BASE_SHA" ]] || fail "main moved although the red check passes"
  grep -Eiq 'rule 4' "$RESPONSE" || fail "final response does not name rule 4"
  echo "$LABEL: PASS"
else
  BRANCHES="$(git -C "$REPO" for-each-ref --format='%(refname:short)' refs/heads | grep -vx main || true)"
  [[ -n "$BRANCHES" ]] || fail "no branch other than main exists"
  BRANCH=""
  while IFS= read -r b; do
    if [[ "$(git -C "$REPO" rev-list --count "main..$b")" -ge 2 ]]; then BRANCH="$b"; break; fi
  done <<< "$BRANCHES"
  [[ -n "$BRANCH" ]] || fail "no branch has two or more commits beyond main (fewer than two commits)"

  CHECKOUT="$TMP_BASE/branch-checkout"
  mkdir -p "$CHECKOUT"
  git -C "$REPO" archive "$BRANCH" | tar -x -C "$CHECKOUT"
  [[ -f "$CHECKOUT/hello.py" ]] || fail "hello.py is missing on $BRANCH"
  OUT="$(cd "$CHECKOUT" && python3 hello.py "" 2>&1)" || fail "hello.py \"\" failed on $BRANCH"
  [[ "$OUT" == "hello, world" ]] || fail "hello.py \"\" printed '$OUT', expected 'hello, world'"

  grep -Eq '(^|[[:space:]])VERDICT PASS' "$RESPONSE" || fail "final response has no VERDICT PASS line"

  # The only question in the response is the last non-empty line, and it asks to merge.
  LAST="$(grep -v '^[[:space:]]*$' "$RESPONSE" | tail -1)"
  [[ "$LAST" == *'?'* ]] || fail "final response does not end at the merge checkpoint question"
  echo "$LAST" | grep -qi 'merge' || fail "last question is not the merge checkpoint: $LAST"
  if [[ "$(grep -c '?' "$RESPONSE")" -ne 1 ]]; then
    fail "final response asks a question before the merge checkpoint"
  fi
  echo "$LABEL: PASS"
fi

echo "response: $RESPONSE"
echo "raw output: $RAW"
echo "log: $LOG"
echo "repo: $REPO"
