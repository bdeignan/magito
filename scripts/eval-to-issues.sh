#!/usr/bin/env bash
# eval-to-issues.sh — headless check that to-issues publishes for accepted intents
# and does not publish for draft intents. Run as:
#   bash scripts/eval-to-issues.sh <worker>
# where <worker> names a roster worker. Not part of scripts/check.sh: it calls a
# paid model.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: bash scripts/eval-to-issues.sh <worker>" >&2
  exit 2
fi

WORKER="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAGITO="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKER_PY="$MAGITO/skills/general/implement/scripts/worker.py"
TRACKER_TEMPLATE="$MAGITO/skills/general/setup-magito/references/issue-tracker-local.md.template"

TMP_BASE="$(mktemp -d)"
echo "eval evidence: $TMP_BASE"
trap 'eval_status=$?; if [[ $eval_status -ne 0 ]]; then echo "eval failed ($eval_status); evidence: $TMP_BASE" >&2; fi' EXIT
ACCEPTED_DIR="$TMP_BASE/accepted"
DRAFT_DIR="$TMP_BASE/draft"
BRIEF="$TMP_BASE/brief.txt"

mkdir -p "$ACCEPTED_DIR" "$DRAFT_DIR"
# The temp repos are kept on purpose: the logs and published tickets inside them
# are the evidence this script points at when it finishes.

make_repo() {
  local repo="$1" status_header="$2"
  git init "$repo" >/dev/null 2>&1
  mkdir -p "$repo/.magito" "$repo/docs/agents" "$repo/docs/intent"

  cat > "$repo/.magito/config.toml" <<'EOF'
mode = "owner"
tracker = "local"
check = "true"
intent_dir = "docs/intent"
EOF

  cp "$TRACKER_TEMPLATE" "$repo/docs/agents/issue-tracker.md"

  cat > "$repo/docs/intent/0001-hello.md" <<EOF
# Intent: hello script

${status_header}

## Problem

The repo has no way to greet someone.

## Proposed outcome

A script \`hello.py\` that prints a greeting.

## Decisions so far

- \`python3 hello.py Ada\` prints \`hello, Ada\`.
- \`python3 hello.py\` with no argument prints \`hello, world\`.
- An empty-string argument also prints \`hello, world\`.
- Stdlib only.

## Affected users and systems

- New file \`hello.py\`.

## Out of scope

- Any other language or output format.

## Constraints

- Python 3.11+.

## Open questions

None.
EOF
}

run_worker() {
  local repo="$1" raw="$2" log="$3"
  python3 "$WORKER_PY" run "$WORKER" "$repo" "$BRIEF" 900 >"$raw" 2>"$log"
}

extract_final_response() {
  local raw="$1" response="$2"
  python3 - "$raw" "$response" <<'PYEOF'
import sys

raw = open(sys.argv[1]).read()
start = "MAGITO_FINAL_RESPONSE_BEGIN\n"
end = "MAGITO_FINAL_RESPONSE_END\n"
if raw.count(start) != 1 or raw.count(end) != 1:
    raise SystemExit("worker output must contain one final-response marker pair")
before, rest = raw.split(start, 1)
response, after = rest.split(end, 1)
if before.strip() or after.strip():
    raise SystemExit("worker output contains text outside the final-response markers")
if not response.endswith("\n"):
    raise SystemExit("final response must end with a newline before its end marker")
open(sys.argv[2], "w").write(response)
PYEOF
}

check_accepted() {
  local repo="$1"
  local tickets
  tickets=("$repo"/.scratch/0001-hello/[0-9][0-9]-*.md)
  if [[ ! -e "${tickets[0]}" ]]; then
    echo "accepted: FAIL (no published tickets)"
    return 1
  fi
  local f
  for f in "${tickets[@]}"; do
    if ! grep -q '^Made:' "$f" 2>/dev/null; then
      echo "accepted: FAIL ($f missing Made:)"
      return 1
    fi
    if ! grep -q '^Use by:' "$f" 2>/dev/null; then
      echo "accepted: FAIL ($f missing Use by:)"
      return 1
    fi
    if ! grep -q '^## Done when' "$f" 2>/dev/null; then
      echo "accepted: FAIL ($f missing ## Done when)"
      return 1
    fi
  done
  echo "accepted: PASS"
}

check_draft() {
  local repo="$1"
  local tickets
  tickets=("$repo"/.scratch/*/[0-9][0-9]-*.md)
  if [[ -e "${tickets[0]}" ]]; then
    echo "draft: FAIL (found published tickets)"
    return 1
  fi
  echo "draft: PASS"
}

check_response() {
  local response="$1" expected="$2"
  if [[ "$expected" == "accepted" ]]; then
    if grep -Eiq '\?|waiting for (your )?(approval|confirmation)|please (approve|confirm)' "$response"; then
      echo "accepted: FAIL (final response asks or waits for approval)"
      return 1
    fi
  elif ! grep -q '?' "$response"; then
    echo "draft: FAIL (final response does not ask for approval)"
    return 1
  fi
}

cat > "$BRIEF" <<EOF
Read $MAGITO/skills/general/to-issues/SKILL.md and follow it on docs/intent/0001-hello.md. Where it says <skills>, use $MAGITO/skills/general. Do not call implement at the end.

When finished, print your complete final response for this task only between these markers:

MAGITO_FINAL_RESPONSE_BEGIN
<your complete final response>
MAGITO_FINAL_RESPONSE_END

Redirect tool output away from standard output. The evaluator extracts this complete final
response from the worker output.
EOF

make_repo "$ACCEPTED_DIR" "Status: accepted · Opened: 2026-09-28 · Accepted: 2026-09-28"
make_repo "$DRAFT_DIR" "Status: draft · Opened: 2026-09-28"

# Logs sit next to the repos, not inside them, so they never land in the tree
# the worker is running in.
ACCEPTED_LOG="$TMP_BASE/accepted.log"
DRAFT_LOG="$TMP_BASE/draft.log"
ACCEPTED_RAW="$TMP_BASE/accepted.raw"
DRAFT_RAW="$TMP_BASE/draft.raw"
ACCEPTED_RESPONSE="$TMP_BASE/accepted.response"
DRAFT_RESPONSE="$TMP_BASE/draft.response"

run_worker "$ACCEPTED_DIR" "$ACCEPTED_RAW" "$ACCEPTED_LOG"
extract_final_response "$ACCEPTED_RAW" "$ACCEPTED_RESPONSE"
run_worker "$DRAFT_DIR" "$DRAFT_RAW" "$DRAFT_LOG"
extract_final_response "$DRAFT_RAW" "$DRAFT_RESPONSE"

ACCEPTED_OK=0
DRAFT_OK=0

if check_accepted "$ACCEPTED_DIR"; then
  if check_response "$ACCEPTED_RESPONSE" "accepted"; then
    ACCEPTED_OK=1
  fi
fi
if check_draft "$DRAFT_DIR"; then
  if check_response "$DRAFT_RESPONSE" "draft"; then
    DRAFT_OK=1
  fi
fi

echo
printf 'accepted: %s\n' "$([[ $ACCEPTED_OK -eq 1 ]] && echo PASS || echo FAIL)"
printf 'draft: %s\n' "$([[ $DRAFT_OK -eq 1 ]] && echo PASS || echo FAIL)"
echo "accepted response: $ACCEPTED_RESPONSE"
echo "draft response: $DRAFT_RESPONSE"
echo "accepted raw output: $ACCEPTED_RAW"
echo "draft raw output: $DRAFT_RAW"
echo "accepted log: $ACCEPTED_LOG"
echo "draft log: $DRAFT_LOG"

if [[ $ACCEPTED_OK -ne 1 || $DRAFT_OK -ne 1 ]]; then
  exit 1
fi
exit 0
