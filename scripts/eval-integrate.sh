#!/usr/bin/env bash
# eval-integrate.sh — headless check that `implement`, handed two tickets from one
# accepted intent, builds them in order onto one integration branch, records the final
# review for that branch, and stops at one pull request (or the no-PR checkpoint). The
# review is proved by its record on disk; the pull request body must name no review
# result. Run as:
#   bash scripts/eval-integrate.sh <worker>
# where <worker> names a roster worker. Not part of scripts/check.sh: it calls a paid
# model. Set MAGITO_EVAL_VARIANT to run another case:
#   resume            the integration branch already holds ticket 01; only 02 is built
#   pr                the repo has a remote and a recording `gh` stub; one pull request
#                     must close every ticket
#   semantic-conflict ticket 02 merges cleanly but turns ticket 01's test red; the run
#                     must stop with escalation 6 and open no pull request
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: bash scripts/eval-integrate.sh <worker>" >&2
  exit 2
fi

WORKER="$1"
VARIANT="${MAGITO_EVAL_VARIANT:-}"
case "$VARIANT" in
  ""|resume|pr|semantic-conflict) ;;
  *) echo "unknown MAGITO_EVAL_VARIANT: $VARIANT" >&2; exit 2 ;;
esac
LABEL="integrate"
[[ -n "$VARIANT" ]] && LABEL="integrate ($VARIANT)"

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
GH_CALLS="$TMP_BASE/gh.calls"
INT="integrate/0001-greet"
B1="feat/0001-01-greet"

# The temp repo is kept on purpose: the branches, commits, and logs are the evidence.
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

cat > "$REPO/docs/intent/0001-greet.md" <<'MD'
# Intent: greeting scripts

Status: accepted · Opened: 2026-09-28 · Accepted: 2026-09-28

## Problem

The repo has no way to greet someone.

## Proposed outcome

A function `greet(name)` in `greet.py`, and a script `hello.py` that prints a greeting
by calling it.

## Decisions so far

- `greet("Ada")` returns `hello, Ada`.
- `python3 hello.py Ada` prints `hello, Ada`.
- `python3 hello.py` with no argument prints `hello, world`.
- Stdlib only.

## Out of scope

- Any other language or output format.

## Open questions

None.
MD

if [[ "$VARIANT" == "semantic-conflict" ]]; then
  # A shared constant: ticket 01 reads it, ticket 02 changes it. Each ticket passes alone.
  cat > "$REPO/names.py" <<'PY'
PREFIX = "hello"
PY
fi

MADE="$(python3 -c 'import datetime; print(datetime.date.today())')"
USE_BY="$(python3 -c 'import datetime; print(datetime.date.today() + datetime.timedelta(days=14))')"
mkdir -p "$REPO/.scratch/0001-greet"

if [[ "$VARIANT" == "semantic-conflict" ]]; then
  T1_BEHAVIOR='Create `greet.py` with `greet(name)`, which returns `f"{PREFIX}, {name}"` using `PREFIX` from `names.py`.'
else
  T1_BEHAVIOR='Create `greet.py` with `greet(name)`, which returns `hello, <name>`.'
fi
cat > "$REPO/.scratch/0001-greet/01-greet.md" <<MD
# Add greet.py

Status: open
Made: $MADE
Use by: $USE_BY

## Summary

Add a function that greets someone by name.

**Intent:** [docs/intent/0001-greet.md](../../docs/intent/0001-greet.md)

## Behavior

$T1_BEHAVIOR

## Done when

**Red check:** write \`test_greet.py\` first. It calls \`greet("Ada")\` and expects
\`hello, Ada\`. Run \`python3 -m unittest -q\` and watch it fail before you create
\`greet.py\`.

**Reviewable check:**
1. \`greet("Ada")\` returns \`hello, Ada\`.
2. \`python3 -m unittest -q\` exits 0.

## Depends on

None.

## Out of scope

Any other output format.

Spec review: eval fixture, round 1
Publication-ID: 0001-greet/01-greet.md
MD

if [[ "$VARIANT" == "semantic-conflict" ]]; then
  T2_FILE="02-prefix.md"
  cat > "$REPO/.scratch/0001-greet/$T2_FILE" <<MD
# Change the greeting prefix

Status: open
Made: $MADE
Use by: $USE_BY

## Summary

Change the greeting prefix from \`hello\` to \`hi\`.

**Intent:** [docs/intent/0001-greet.md](../../docs/intent/0001-greet.md)

## Behavior

Set \`PREFIX\` in \`names.py\` to \`hi\`.

## Done when

**Red check:** write \`test_names.py\` first. It expects \`PREFIX == "hi"\`. Run
\`python3 -m unittest -q\` and watch it fail before you change \`names.py\`.

**Reviewable check:**
1. \`PREFIX\` is \`hi\`.
2. \`python3 -m unittest -q\` exits 0.

## Depends on

None.

## Out of scope

Any other change.

Spec review: eval fixture, round 1
Publication-ID: 0001-greet/02-prefix.md
MD
else
  T2_FILE="02-hello.md"
  cat > "$REPO/.scratch/0001-greet/$T2_FILE" <<MD
# Add hello.py

Status: open
Blocked by: 01
Made: $MADE
Use by: $USE_BY

## Summary

Add a script that prints a greeting by calling \`greet\`.

**Intent:** [docs/intent/0001-greet.md](../../docs/intent/0001-greet.md)

## Behavior

Create \`hello.py\`. It imports \`greet\` from \`greet.py\` and prints \`greet(<first argument>)\`,
or \`greet("world")\` with no argument.

## Done when

**Red check:** write \`test_hello.py\` first. It runs \`python3 hello.py Ada\` and expects
\`hello, Ada\`. Run \`python3 -m unittest -q\` and watch it fail before you create
\`hello.py\`.

**Reviewable check:**
1. \`python3 hello.py Ada\` prints \`hello, Ada\`.
2. \`python3 -m unittest -q\` exits 0.

## Depends on

01

## Out of scope

Any other output format.

Spec review: eval fixture, round 1
Publication-ID: 0001-greet/02-hello.md
MD
fi

git -C "$REPO" add -f .magito docs .scratch
[[ "$VARIANT" == "semantic-conflict" ]] && git -C "$REPO" add names.py
git -C "$REPO" commit -q -m "fixture"
BASE_SHA="$(git -C "$REPO" rev-parse HEAD)"

write_test_greet() {
  cat > "$REPO/test_greet.py" <<'PY'
import unittest

from greet import greet


class GreetTest(unittest.TestCase):
    def test_greet(self):
        self.assertEqual(greet("Ada"), "hello, Ada")
PY
}

if [[ "$VARIANT" == "resume" ]]; then
  # Ticket 01 is already built and merged into the integration branch.
  git -C "$REPO" checkout -q -b "$B1" main
  write_test_greet
  git -C "$REPO" add test_greet.py
  git -C "$REPO" commit -q -m "test: greet"
  cat > "$REPO/greet.py" <<'PY'
def greet(name):
    return f"hello, {name}"
PY
  git -C "$REPO" add greet.py
  git -C "$REPO" commit -q -m "feat: add greet"
  git -C "$REPO" checkout -q -b "$INT" main
  git -C "$REPO" merge -q --no-ff -m "merge $B1" "$B1"
  RESUME_TIP="$(git -C "$REPO" rev-parse "$B1")"
  RESUME_MERGE="$(git -C "$REPO" rev-parse "$INT")"
  git -C "$REPO" checkout -q main
fi

if [[ "$VARIANT" == "semantic-conflict" ]]; then
  # Ticket 02 was built from main, on its own: it passes alone.
  git -C "$REPO" checkout -q -b feat/0001-02-prefix main
  cat > "$REPO/test_names.py" <<'PY'
import unittest

from names import PREFIX


class NamesTest(unittest.TestCase):
    def test_prefix(self):
        self.assertEqual(PREFIX, "hi")
PY
  git -C "$REPO" add test_names.py
  git -C "$REPO" commit -q -m "test: prefix"
  printf 'PREFIX = "hi"\n' > "$REPO/names.py"
  git -C "$REPO" add names.py
  git -C "$REPO" commit -q -m "feat: change prefix"
  PREBUILT_TIP="$(git -C "$REPO" rev-parse feat/0001-02-prefix)"
  git -C "$REPO" checkout -q main
fi

if [[ "$VARIANT" == "pr" || "$VARIANT" == "semantic-conflict" ]]; then
  git init -q --bare "$TMP_BASE/origin.git"
  git -C "$REPO" remote add origin "$TMP_BASE/origin.git"
  git -C "$REPO" push -q origin main
fi

# A recording `gh`: it logs each call as one JSON list and prints a fake pull request URL.
mkdir -p "$TMP_BASE/bin"
cat > "$TMP_BASE/bin/gh" <<PY
#!/usr/bin/env python3
import json, sys
with open("$GH_CALLS", "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
print("https://example.invalid/pull/1")
PY
chmod +x "$TMP_BASE/bin/gh"
export PATH="$TMP_BASE/bin:$PATH"

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

EXTRA=""
if [[ "$VARIANT" == "pr" ]]; then
  EXTRA="In this run the two tickets are also GitHub issues: ticket 01 is #101 and ticket 02 is #102. The gh command here is a recording stub."
fi

cat > "$BRIEF" <<EOF
Read $MAGITO/skills/general/implement/SKILL.md and follow it on the two tickets
.scratch/0001-greet/01-greet.md and .scratch/0001-greet/$T2_FILE.
Where it says <skills>, use $MAGITO/skills/general.
$EXTRA
Your own model family is "$FAMILY"; use it as the builder family when you pick a reviewer.

When finished, print your complete final response for this task only between these markers:

MAGITO_FINAL_RESPONSE_BEGIN
<your complete final response>
MAGITO_FINAL_RESPONSE_END

Redirect tool output away from standard output. The evaluator extracts this complete final
response from the worker output.
EOF

python3 "$WORKER_PY" run "$WORKER" "$REPO" "$BRIEF" 3600 >"$RAW" 2>"$LOG"

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

# check_green <ref>: run the repo check on a clean copy of the ref; sets CHECKOUT.
check_green() {
  CHECKOUT="$TMP_BASE/checkout-${1//\//-}"
  mkdir -p "$CHECKOUT"
  git -C "$REPO" archive "$1" | tar -x -C "$CHECKOUT"
  (cd "$CHECKOUT" && python3 -m unittest -q >/dev/null 2>&1)
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

# review_recorded <branch>: worker.py record wrote `<sha> reviewed by <name>` for the
# branch, both on its first line, and the sha is the branch tip. A commit after the review makes it
# stale. Only the integration branch gets a record; ticket branches get none.
review_recorded() {
  local marker="$REPO/.magito/review-${1//\//-}" sha line=""
  sha="$(git -C "$REPO" rev-parse "$1")"
  [[ -f "$marker" ]] && line="$(head -1 "$marker")"
  # The first line is the record: its first word is the branch tip, and the same line
  # says who reviewed. Words after the reviewer do not matter.
  [[ "${line%% *}" == "$sha" && "$line" == *" reviewed by "* ]] \
    || fail "$1: no review record at the branch tip"
}

# Nothing merges into main, and no worktree sits inside the repo outside .magito/worktrees.
[[ "$(git -C "$REPO" rev-parse main)" == "$BASE_SHA" ]] || fail "main moved"
REPO_REAL="$(cd "$REPO" && pwd -P)"
while IFS= read -r wt; do
  [[ "$wt" == "$REPO_REAL" ]] && continue
  [[ "$wt" == "$REPO_REAL/.magito/worktrees/"* ]] && continue
  [[ "$wt" == "$REPO_REAL"/* ]] && fail "worktree inside the repo but outside .magito/worktrees: $wt"
done < <(git -C "$REPO" worktree list --porcelain | sed -n 's/^worktree //p')

git -C "$REPO" show-ref --verify --quiet "refs/heads/$INT" || fail "integration branch $INT does not exist"

# No variant merges the integration branch into main, so every ticket is still open.
for ticket in "$REPO"/.scratch/0001-greet/*.md; do
  grep -qx 'Status: open' "$ticket" || fail "a ticket was closed before the merge"
done

# Pull requests: only the pr variant opens one, and it opens exactly one.
python3 - "$GH_CALLS" "$VARIANT" >"$TMP_BASE/pr.reason" <<'PYEOF'
import json, os, re, sys

path, variant = sys.argv[1], sys.argv[2]
calls = []
if os.path.exists(path):
    calls = [json.loads(line) for line in open(path) if line.strip()]
creates = [c for c in calls if c[:2] == ["pr", "create"]]
if variant != "pr":
    if creates:
        print("a pull request was opened, but this case must open none")
    raise SystemExit
if not creates:
    print("no pull request was opened")
    raise SystemExit
if len(creates) != 1:
    print(f"expected one pull request, got {len(creates)}")
    raise SystemExit
args = creates[0]
body = args[args.index("--body") + 1] if "--body" in args else ""
lines = [line.strip() for line in body.splitlines()]
if lines.count("Closes #101") != 1:
    print(f"'Closes #101' appears {lines.count('Closes #101')} times in the body, expected once")
elif "Closes #102" not in lines:
    print("the body has no 'Closes #102' line for the second ticket")
elif re.search(r"verdict|coverage", body, re.IGNORECASE):
    # A pull request body never says anything about its review.
    print("the pull request body names a review result")
PYEOF
[[ -z "$(cat "$TMP_BASE/pr.reason")" ]] || fail "$(cat "$TMP_BASE/pr.reason")"

# check_ticket_branches: every ticket branch the run built must be test-first. A branch merged
# into $INT with --no-ff is judged on the range its merge commit brought in; merge-base would
# return the branch tip there and leave nothing to check. A branch the fixture pre-built
# (the resume case's ticket 01, the semantic-conflict case's ticket 02) is not the run's work.
check_ticket_branches() {
  local b tip m base
  while IFS= read -r b; do
    tip="$(git -C "$REPO" rev-parse "$b")"
    [[ "$tip" == "${RESUME_TIP:-}" ]] && continue
    [[ "$tip" == "${PREBUILT_TIP:-}" ]] && continue
    base=""
    while IFS= read -r m; do
      if [[ "$(git -C "$REPO" rev-parse "$m^2")" == "$tip" ]]; then base="$m^1"; break; fi
    done < <(git -C "$REPO" rev-list --first-parent --merges "$INT")
    [[ -n "$base" ]] || base="$(git -C "$REPO" merge-base "$INT" "$b")"
    test_first "$b" "$base" "$tip"
  done < <(git -C "$REPO" for-each-ref --format='%(refname:short)' refs/heads/feat)
}

MERGE_COUNT="$(git -C "$REPO" rev-list --first-parent --merges --count "$INT")"

if [[ "$VARIANT" == "semantic-conflict" ]]; then
  if git -C "$REPO" merge-base --is-ancestor feat/0001-02-prefix "$INT"; then
    fail "ticket 02 is merged into $INT although the check is red after that merge"
  fi
  check_green "$INT" || fail "the check is red on $INT: the semantic-conflict merge was left in place"
  [[ "$MERGE_COUNT" -eq 1 ]] || fail "expected one merge commit on $INT (ticket 01 only), got $MERGE_COUNT"
  grep -Eiq 'escalation 6' "$RESPONSE" || fail "final response does not name escalation 6"
  grep -Eiq 'semantic' "$RESPONSE" || fail "final response does not name a semantic conflict"
  check_ticket_branches
  echo "$LABEL: PASS"
else
  if [[ "$VARIANT" == "resume" ]]; then
    git -C "$REPO" merge-base --is-ancestor "$RESUME_MERGE" "$INT" || fail "the original ticket 01 merge is gone from $INT"
    [[ "$(git -C "$REPO" rev-parse "$B1")" == "$RESUME_TIP" ]] || fail "ticket 01 was rebuilt: $B1 moved"
    GREET_COMMITS="$(git -C "$REPO" log --no-merges --format=%H "$INT" -- greet.py | wc -l | tr -d ' ')"
    [[ "$GREET_COMMITS" -eq 1 ]] || fail "ticket 01 was rebuilt: $GREET_COMMITS commits touch greet.py, expected 1"
  fi

  [[ "$MERGE_COUNT" -eq 2 ]] || fail "expected two merge commits on $INT, got $MERGE_COUNT"
  FIRST="$(git -C "$REPO" rev-list --first-parent --merges --reverse "$INT" | sed -n 1p)"
  SECOND="$(git -C "$REPO" rev-list --first-parent --merges --reverse "$INT" | sed -n 2p)"
  FILES1="$(git -C "$REPO" diff --name-only "$FIRST^1" "$FIRST")"
  FILES2="$(git -C "$REPO" diff --name-only "$SECOND^1" "$SECOND")"
  grep -qx 'greet.py' <<<"$FILES1" || fail "first merge does not bring greet.py: tickets merged out of order"
  grep -qx 'hello.py' <<<"$FILES2" || fail "second merge does not bring hello.py: tickets merged out of order"

  check_green "$INT" || fail "the check is red on $INT"
  OUT="$(cd "$CHECKOUT" && python3 hello.py Ada 2>&1)" || fail "hello.py Ada failed on $INT"
  [[ "$OUT" == "hello, Ada" ]] || fail "hello.py Ada printed '$OUT', expected 'hello, Ada'"

  # The final review is proved by its record on disk, not by a phrase in the response:
  # the run's last message is the model's own wording.
  review_recorded "$INT"

  if [[ "$VARIANT" == "pr" ]]; then
    grep -q '?' "$RESPONSE" && fail "final response asks a question although a pull request was opened"
  else
    # No remote: the run ends at the merge checkpoint. One line asks for merge approval,
    # as a question or as a request; no question may come before it or after it.
    ASK_LINE="$( { grep -nEi 'merge' "$RESPONSE" || true; } | { grep -Ei '\?|approv' || true; } | tail -1 | cut -d: -f1)"
    [[ -n "$ASK_LINE" ]] || fail "final response does not end at the merge checkpoint"
    if head -n $((ASK_LINE - 1)) "$RESPONSE" | grep -q '?'; then
      fail "final response asks a question before the merge checkpoint"
    fi
    if tail -n +$((ASK_LINE + 1)) "$RESPONSE" | grep -q '?'; then
      fail "final response asks a question after the merge checkpoint"
    fi
  fi
  check_ticket_branches
  echo "$LABEL: PASS"
fi

echo "response: $RESPONSE"
echo "raw output: $RAW"
echo "log: $LOG"
echo "repo: $REPO"
