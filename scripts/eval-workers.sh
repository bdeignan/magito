#!/usr/bin/env bash
# eval-workers.sh — check the worker commands against the REAL roster on this machine.
# A real tool from another model family must answer its probe, review a real diff, and
# be the reason a subagent record is refused. Every other test of these commands uses a
# fake worker; a fake worker missed real failures in an earlier pilot, so this one does
# not. Run as:
#   bash scripts/eval-workers.sh <your-family>
# where <your-family> is the model family of the session that would build (anthropic,
# openai, google, ...). Not part of scripts/check.sh: it starts real tools and can cost
# money. It reads ~/.magito/workers.toml (or MAGITO_WORKERS_FILE) and never changes it.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: bash scripts/eval-workers.sh <your-family>" >&2
  exit 2
fi
FAMILY="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAGITO="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKER_PY="$MAGITO/skills/general/implement/scripts/worker.py"
GITFLOW="$MAGITO/skills/general/implement/scripts/gitflow.sh"

TMP="$(mktemp -d)"
echo "eval evidence: $TMP"
fail() { echo "workers: FAIL ($1)"; exit 1; }

# 1. The readiness report names a ready reviewer from another family.
python3 "$WORKER_PY" ready --family "$FAMILY" | tee "$TMP/ready.txt"
REVIEWER="$(sed -n "s/^reviewer for $FAMILY: //p" "$TMP/ready.txt")"
[[ -n "$REVIEWER" && "$REVIEWER" != "none" ]] \
  || fail "no roster worker from a family other than '$FAMILY' is ready on this machine"

# 2. The start line names the same reviewer, on one line.
python3 "$WORKER_PY" start --family "$FAMILY" > "$TMP/start.txt"
cat "$TMP/start.txt"
[[ "$(wc -l < "$TMP/start.txt" | tr -d ' ')" -eq 1 ]] || fail "the start line is not one line"
grep -q " · reviewer: $REVIEWER (" "$TMP/start.txt" || fail "the start line does not name $REVIEWER as reviewer"

# 3. A real review round, in a throwaway repo with a worktree made by gitflow.sh.
REPO="$TMP/repo"
git init -q -b main "$REPO"
git -C "$REPO" config user.name "eval"
git -C "$REPO" config user.email "eval@example.invalid"
git -C "$REPO" commit -q --allow-empty -m "base"
WT="$(cd "$REPO" && bash "$GITFLOW" worktree add feat/1-greeting | tail -1)"
printf 'hello\n' > "$WT/greeting.txt"
git -C "$WT" add greeting.txt
git -C "$WT" commit -q -m "feat: add the greeting"
MARKER="$REPO/.magito/review-feat-1-greeting"
[[ "$(cat "$MARKER")" == "pending" ]] || fail "gitflow.sh worktree add did not leave the marker as pending"

{
  echo "You are reviewing a code change, not building. Do not create, edit, or delete any file."
  echo
  echo "The ticket: add a file named greeting.txt to the repository root. It must hold exactly"
  echo "one line, the word hello, and nothing else. No other file changes."
  echo
  echo "Reply with exactly one line and nothing else. Reply VERDICT PASS when the diff below"
  echo "does what the ticket says. Otherwise reply VERDICT FIX: followed by what is wrong."
  echo
  echo "The diff:"
  echo
  git -C "$WT" diff main...HEAD
} > "$TMP/brief.md"

set +e
python3 "$WORKER_PY" review "$REVIEWER" "$WT" "$TMP/brief.md" 900 > "$TMP/verdict.txt" 2> "$TMP/review.err"
CODE=$?
set -e
cat "$TMP/verdict.txt"
[[ $CODE -eq 0 ]] || fail "the review round with $REVIEWER exited $CODE; see $TMP/review.err"
grep -q '^VERDICT PASS' "$TMP/verdict.txt" || fail "$REVIEWER did not answer VERDICT PASS"
! grep -q '^VERDICT FIX' "$TMP/verdict.txt" || fail "$REVIEWER answered VERDICT FIX on a correct diff"

# 4. A subagent record is refused while that reviewer answers, and nothing is written.
set +e
python3 "$WORKER_PY" record "$WT" "$FAMILY" subagent > "$TMP/refuse.out" 2> "$TMP/refuse.err"
CODE=$?
set -e
cat "$TMP/refuse.err"
[[ $CODE -eq 6 ]] || fail "record subagent exited $CODE, expected 6, while $REVIEWER answers"
grep -q "$REVIEWER (" "$TMP/refuse.err" || fail "the refusal does not name $REVIEWER"
[[ "$(cat "$MARKER")" == "pending" ]] || fail "a refused record changed the marker"

# 5. The real review is recorded, and the commit test counts the branch's one commit.
python3 "$WORKER_PY" record "$WT" "$FAMILY" "$REVIEWER" > "$TMP/record.out"
[[ "$(cat "$MARKER")" == "$(git -C "$WT" rev-parse HEAD) reviewed by $REVIEWER" ]] \
  || fail "the record does not read '<sha> reviewed by $REVIEWER'"
[[ "$(cd "$WT" && bash "$GITFLOW" ahead)" == "1" ]] || fail "gitflow.sh ahead did not print 1"

echo "workers: PASS (reviewer: $REVIEWER)"
