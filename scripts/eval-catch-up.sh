#!/usr/bin/env bash
# eval-catch-up.sh — headless check that `catch-up` reports every source on one
# `sources:` line, in order, with the right status, and changes nothing in the repo.
# The fixture is a throwaway git repo: CLAUDE.md, a glossary, two journal entries
# under the excluded .magito/journal/, and a local tracker with one open ticket.
# Run as:
#   bash scripts/eval-catch-up.sh <worker>
# where <worker> names a roster worker. Not part of scripts/check.sh: it calls a
# paid model. Set MAGITO_EVAL_VARIANT to run another case:
#   no-journal  the fixture has no .magito/journal/; the sources line must say
#               journal=missing
#   no-tracker  the fixture has no docs/agents/issue-tracker.md; the sources line
#               must say tracker=skipped (any reason after the colon)
# With no variant, the sources line must say journal=read and tracker=read.
# In every case no file may change, appear, or disappear outside .git/, and the
# response must hold exactly one line starting with `sources:` that names journal,
# CLAUDE.md, docs/agents/GLOSSARY.md, ADRs, tracker, git, PRs, in that order.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: bash scripts/eval-catch-up.sh <worker>" >&2
  exit 2
fi

WORKER="$1"
VARIANT="${MAGITO_EVAL_VARIANT:-}"
case "$VARIANT" in
  ""|no-journal|no-tracker) ;;
  *) echo "unknown MAGITO_EVAL_VARIANT: $VARIANT" >&2; exit 2 ;;
esac
LABEL="catch-up"
[[ -n "$VARIANT" ]] && LABEL="catch-up ($VARIANT)"

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
BEFORE="$TMP_BASE/files.before"
AFTER="$TMP_BASE/files.after"

# The temp repo is kept on purpose: the files and logs are the evidence.
git init -b main "$REPO" >/dev/null 2>&1
git -C "$REPO" config user.name "eval"
git -C "$REPO" config user.email "eval@example.invalid"
mkdir -p "$REPO/docs/agents"

cat > "$REPO/CLAUDE.md" <<'MD'
# Fixture project

A small project used to test catch-up. It has one script and no dependencies.
MD

cat > "$REPO/docs/agents/GLOSSARY.md" <<'MD'
# Glossary

**widget** — the one thing this project makes.
MD

git -C "$REPO" add CLAUDE.md docs/agents/GLOSSARY.md

if [[ "$VARIANT" != "no-tracker" ]]; then
  cp "$TRACKER_TEMPLATE" "$REPO/docs/agents/issue-tracker.md"
  MADE="$(python3 -c 'import datetime; print(datetime.date.today())')"
  USE_BY="$(python3 -c 'import datetime; print(datetime.date.today() + datetime.timedelta(days=14))')"
  mkdir -p "$REPO/.scratch/0001-widget"
  cat > "$REPO/.scratch/0001-widget/01-widget.md" <<MD
# Add the widget script

Status: open
Made: $MADE
Use by: $USE_BY

## Summary

Add a script that prints a widget.

## Behavior

Create \`widget.py\`. It prints \`widget\`.

## Done when

**Reviewable check:**
1. \`python3 widget.py\` prints \`widget\`.

## Depends on

None.

## Out of scope

Anything else.

Publication-ID: 0001-widget/01-widget.md
MD
  git -C "$REPO" add docs/agents/issue-tracker.md
  git -C "$REPO" add -f .scratch
fi

# .magito is personal state, so it stays out of git through .git/info/exclude.
echo ".magito/" >> "$REPO/.git/info/exclude"
if [[ "$VARIANT" != "no-journal" ]]; then
  mkdir -p "$REPO/.magito/journal"
  cat > "$REPO/.magito/journal/2026-10-01-101500-first-session-a1b2c3.md" <<'MD'
# First session

Landed the project skeleton. Next: write the widget script.
MD
  cat > "$REPO/.magito/journal/2026-10-02-141000-second-session-d4e5f6.md" <<'MD'
# Second session

Wrote the glossary. Gotcha: the widget name is fixed. Next: ticket 0001.
MD
fi

git -C "$REPO" commit -q -m "fixture"

# snapshot <file>: every file outside .git/, as `<sha256>  <path>`, sorted by path.
snapshot() {
  python3 - "$REPO" <<'PY' > "$1"
import hashlib
import os
import sys

root = sys.argv[1]
rows = []
for dirpath, dirnames, filenames in os.walk(root):
    if dirpath == root and ".git" in dirnames:
        dirnames.remove(".git")
    for name in filenames:
        full = os.path.join(dirpath, name)
        rel = os.path.relpath(full, root)
        if os.path.islink(full):
            digest = "link:" + os.readlink(full)
        else:
            with open(full, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
        rows.append((rel, digest))
for rel, digest in sorted(rows):
    print(f"{digest}  {rel}")
PY
}
snapshot "$BEFORE"

cat > "$BRIEF" <<BRIEF_END
Read $MAGITO/skills/general/catch-up/SKILL.md and follow it in this repo. Where it
mentions the journal command or other paths under ~/.magito, use the repo files it names
instead. Only read: change no file, and start no other work.

When finished, print your complete final response for this task only between these markers:

MAGITO_FINAL_RESPONSE_BEGIN
<your complete final response>
MAGITO_FINAL_RESPONSE_END

Redirect tool output away from standard output. The evaluator extracts this complete final
response from the worker output.
BRIEF_END

python3 "$WORKER_PY" run "$WORKER" "$REPO" "$BRIEF" 900 >"$RAW" 2>"$LOG"

python3 - "$RAW" "$RESPONSE" <<'PYEOF'
import sys

raw = open(sys.argv[1]).read()
start = "MAGITO_FINAL_RESPONSE_BEGIN\n"
end = "MAGITO_FINAL_RESPONSE_END\n"
if raw.count(start) != 1 or raw.count(end) != 1:
    raise SystemExit("worker output must contain one final-response marker pair")
before, rest = raw.split(start, 1)
response, after = rest.split(end, 1)
if not response.endswith("\n"):
    raise SystemExit("final response must end with a newline before its end marker")
open(sys.argv[2], "w").write(response)
PYEOF

fail() { echo "$LABEL: FAIL ($1)"; exit 1; }

# The repo is untouched: the same files with the same checksums, .magito/ included.
snapshot "$AFTER"
if ! diff -q "$BEFORE" "$AFTER" >/dev/null; then
  CHANGED="$({ diff "$BEFORE" "$AFTER" || true; } | sed -n 's/^[<>] [0-9a-f:]*  //p' | sort -u | tr '\n' ' ')"
  fail "fixture changed during the run: ${CHANGED% }"
fi

# Exactly one `sources:` line.
COUNT="$(grep -c '^sources:' "$RESPONSE" || true)"
[[ "$COUNT" -eq 1 ]] || fail "response holds $COUNT lines starting with sources:, expected 1"

# The line names every source, in order, and the statuses the variant calls for.
EXPECT_JOURNAL="read"; EXPECT_TRACKER="read"
[[ "$VARIANT" == "no-journal" ]] && EXPECT_JOURNAL="missing"
[[ "$VARIANT" == "no-tracker" ]] && EXPECT_TRACKER="skipped"
VERDICT="$(python3 - "$RESPONSE" "$EXPECT_JOURNAL" "$EXPECT_TRACKER" <<'PY'
import re
import sys

line = next(l for l in open(sys.argv[1]).read().splitlines() if l.startswith("sources:"))
names = ["journal", "CLAUDE.md", "docs/agents/GLOSSARY.md", "ADRs", "tracker", "git", "PRs"]
body = line[len("sources:"):]
starts = []
pos = 0
for name in names:
    m = re.compile(r"(?:^|[\s,])" + re.escape(name) + "=").search(body, pos)
    if not m:
        print("sources line does not name every source in order")
        raise SystemExit
    starts.append((m.end(), m.start()))
    pos = m.end()
status = {}
for i, name in enumerate(names):
    end = starts[i + 1][1] if i + 1 < len(names) else len(body)
    status[name] = body[starts[i][0]:end].strip().rstrip(",").strip()
for name, want in (("journal", sys.argv[2]), ("tracker", sys.argv[3])):
    got = status[name]
    ok = (got == "skipped" or got.startswith("skipped:")) if want == "skipped" else got == want
    if not ok:
        print(f"{name} is '{got}' on the sources line, expected {want}")
        raise SystemExit
print("ok")
PY
)"
[[ "$VERDICT" == "ok" ]] || fail "$VERDICT"
echo "$LABEL: PASS"

echo "response: $RESPONSE"
echo "raw output: $RAW"
echo "log: $LOG"
echo "repo: $REPO"
