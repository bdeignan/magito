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
  local repo="$1" log="$2"
  python3 "$WORKER_PY" run "$WORKER" "$repo" "$BRIEF" 900 >"$log" 2>&1
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

cat > "$BRIEF" <<EOF
Read $MAGITO/skills/general/to-issues/SKILL.md and follow it on docs/intent/0001-hello.md. Where it says <skills>, use $MAGITO/skills/general. Do not call implement at the end.
EOF

make_repo "$ACCEPTED_DIR" "Status: accepted · Opened: 2026-09-28 · Accepted: 2026-09-28"
make_repo "$DRAFT_DIR" "Status: draft · Opened: 2026-09-28"

ACCEPTED_LOG="$ACCEPTED_DIR/eval.log"
DRAFT_LOG="$DRAFT_DIR/eval.log"

run_worker "$ACCEPTED_DIR" "$ACCEPTED_LOG" || true
run_worker "$DRAFT_DIR" "$DRAFT_LOG" || true

ACCEPTED_OK=0
DRAFT_OK=0

check_accepted "$ACCEPTED_DIR" && ACCEPTED_OK=1 || true
check_draft "$DRAFT_DIR" && DRAFT_OK=1 || true

echo
printf 'accepted: %s\n' "$([[ $ACCEPTED_OK -eq 1 ]] && echo PASS || echo FAIL)"
printf 'draft: %s\n' "$([[ $DRAFT_OK -eq 1 ]] && echo PASS || echo FAIL)"
echo "accepted log: $ACCEPTED_LOG"
echo "draft log: $DRAFT_LOG"

if [[ $ACCEPTED_OK -ne 1 || $DRAFT_OK -ne 1 ]]; then
  exit 1
fi
exit 0
