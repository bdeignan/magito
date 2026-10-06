#!/usr/bin/env bash
# eval-handoff.sh — headless check that `handoff` writes one well-formed journal entry.
# The entry is the only new file under .magito/journal/, it is named
# YYYY-MM-DD-HHMMSS-<slug>-<six hex digits>.md, and the whole file holds at most 300
# words. No other file in the repo changes. Run as:
#   bash scripts/eval-handoff.sh <worker>
# where <worker> names a roster worker. Not part of scripts/check.sh: it calls a
# paid model. Set MAGITO_EVAL_VARIANT to run another case:
#   (default)        the session landed work; the entry holds a **Landed:**, a
#                    **Next:**, and a **Gotcha:** line
#   nothing-landed   the session did nothing; the entry holds **Landed:** followed by
#                    the word nothing, and needs no Next or Gotcha line
#   long-session     the summary runs over 1,000 words; the entry still holds at most
#                    300 words and the three lines
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: bash scripts/eval-handoff.sh <worker>" >&2
  exit 2
fi

WORKER="$1"
VARIANT="${MAGITO_EVAL_VARIANT:-}"
case "$VARIANT" in
  ""|nothing-landed|long-session) ;;
  *) echo "unknown MAGITO_EVAL_VARIANT: $VARIANT" >&2; exit 2 ;;
esac
LABEL="handoff"
[[ -n "$VARIANT" ]] && LABEL="handoff ($VARIANT)"

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
BEFORE="$TMP_BASE/before.json"
AFTER="$TMP_BASE/after.json"

# The temp repo is kept on purpose: the journal and logs are the evidence.
git init -b main "$REPO" >/dev/null 2>&1
git -C "$REPO" config user.name "eval"
git -C "$REPO" config user.email "eval@example.invalid"
mkdir -p "$REPO/.magito/journal" "$REPO/docs/agents" "$REPO/.scratch/0001-hello"
printf '.magito/\n' >> "$REPO/.git/info/exclude"

cat > "$REPO/.magito/config.toml" <<'TOML'
mode = "owner"
tracker = "local"
check = "python3 -m unittest -q"
intent_dir = "docs/intent"
TOML

cp "$TRACKER_TEMPLATE" "$REPO/docs/agents/issue-tracker.md"

cat > "$REPO/.magito/journal/2026-09-20-101500-first-greeting-a1b2c3.md" <<'MD'
# 2026-09-20 · first greeting

**Landed:** hello.py prints a greeting.
**Next:** accept an empty-string argument.
**Gotcha:** the test runs hello.py as a subprocess, so run it from the repo root.
MD

MADE="$(python3 -c 'import datetime; print(datetime.date.today())')"
USE_BY="$(python3 -c 'import datetime; print(datetime.date.today() + datetime.timedelta(days=14))')"
cat > "$REPO/.scratch/0001-hello/01-empty-argument.md" <<MD
# Treat an empty argument as world

Status: open
Made: $MADE
Use by: $USE_BY

## Summary

\`python3 hello.py ""\` prints \`hello, world\`.

## Behavior

An empty-string argument falls back to \`world\`.

## Done when

**Reviewable check:**
1. \`python3 hello.py ""\` prints \`hello, world\`.

## Depends on

None.

## Out of scope

Any other output format.

Spec review: eval fixture, round 1
Publication-ID: 0001-hello/01-empty-argument.md
MD

cat > "$REPO/hello.py" <<'PY'
import sys

print(f"hello, {sys.argv[1] if len(sys.argv) > 1 else 'world'}")
PY
git -C "$REPO" add hello.py
git -C "$REPO" commit -q -m "feat: add hello.py"
printf '# Notes\n\nGreeting script lives in hello.py.\n' > "$REPO/NOTES.md"
git -C "$REPO" add NOTES.md
git -C "$REPO" commit -q -m "docs: add notes"
git -C "$REPO" add docs .scratch
git -C "$REPO" commit -q -m "chore: add tracker and ticket 1"

# snapshot <out>: every file under the repo (outside .git) mapped to its content hash.
snapshot() {
  python3 - "$REPO" "$1" <<'PY'
import hashlib, json, os, sys
root, out = sys.argv[1], sys.argv[2]
files = {}
for dirpath, dirs, names in os.walk(root):
    if dirpath == root and ".git" in dirs:
        dirs.remove(".git")
    for n in names:
        p = os.path.join(dirpath, n)
        if os.path.isfile(p):
            files[os.path.relpath(p, root)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
json.dump(files, open(out, "w"))
PY
}
snapshot "$BEFORE"

case "$VARIANT" in
  nothing-landed)
    SUMMARY="We opened the session, looked at ticket 1, and then stopped. Nothing was done:
no file changed, no commit was made, and no ticket was touched. The session is over." ;;
  long-session)
    SUMMARY="$(python3 - <<'PY'
parts = ["This session was long and went through many steps."]
for i in range(1, 41):
    parts.append(
        f"Step {i}: we read part {i} of the greeting code, compared it against the notes, "
        f"tried a small variation, ran the test again, and wrote down what we saw in detail "
        f"for item {i} so that nothing would be lost between steps."
    )
parts.append("In the end hello.py already worked and the one open ticket, number 1, "
             "asks for an empty argument to print hello, world. That ticket is next. "
             "The trap we found: the test runs hello.py as a subprocess, so it only "
             "passes from the repo root.")
print(" ".join(parts))
PY
)" ;;
  *)
    SUMMARY="This session added hello.py and NOTES.md, both committed on main. The next session
will take open ticket 1, which makes an empty-string argument print hello, world.
The trap we found: the test runs hello.py as a subprocess, so it only passes when run
from the repo root." ;;
esac

cat > "$BRIEF" <<BRIEF_END
Read $MAGITO/skills/general/handoff/SKILL.md and follow it to close this session. Where it
names ~/.magito/bin/journal, use $MAGITO/bin/journal. Here is what happened in the session:

$SUMMARY

When finished, print your complete final response for this task only between these markers:

MAGITO_FINAL_RESPONSE_BEGIN
<your complete final response>
MAGITO_FINAL_RESPONSE_END

Redirect tool output away from standard output. The evaluator extracts this complete final
response from the worker output.
BRIEF_END

python3 "$WORKER_PY" run "$WORKER" "$REPO" "$BRIEF" 900 >"$RAW" 2>"$LOG"

python3 - "$RAW" <<'PYEOF'
import sys

raw = open(sys.argv[1]).read()
if raw.count("MAGITO_FINAL_RESPONSE_BEGIN\n") != 1 or raw.count("MAGITO_FINAL_RESPONSE_END\n") != 1:
    raise SystemExit("worker output must contain one final-response marker pair")
PYEOF

fail() { echo "$LABEL: FAIL ($1)"; exit 1; }

snapshot "$AFTER"

# The checks read files only: the journal folder before and after, and the entry itself.
REASON="$(python3 - "$BEFORE" "$AFTER" "$VARIANT" "$REPO" <<'PY'
import json, os, re, sys

before, after = (json.load(open(p)) for p in sys.argv[1:3])
variant, repo = sys.argv[3], sys.argv[4]
JOURNAL = ".magito/journal/"
added = sorted(set(after) - set(before))
changed = sorted(p for p in before if after.get(p) != before[p])
journal = [p for p in added if p.startswith(JOURNAL) and "/" not in p[len(JOURNAL):]]
if len(journal) != 1:
    print(f"expected exactly one new journal file, found {len(journal)}")
    raise SystemExit(0)
if changed or added != journal:
    print("a file other than the new journal entry changed")
    raise SystemExit(0)
name = journal[0][len(JOURNAL):]
if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d{6}-[a-z0-9]+(-[a-z0-9]+)*-[0-9a-f]{6}\.md", name):
    print("journal entry name does not match YYYY-MM-DD-HHMMSS-<slug>-<six hex digits>.md")
    raise SystemExit(0)
text = open(os.path.join(repo, journal[0])).read()
if len(text.split()) > 300:
    print("journal entry is over 300 words")
    raise SystemExit(0)
lines = text.splitlines()
if variant == "nothing-landed":
    if not any(re.match(r"\*\*Landed:\*\*\s*nothing\b", ln, re.I) for ln in lines):
        print("the Landed line does not say nothing")
    raise SystemExit(0)
for part in ("Landed", "Next", "Gotcha"):
    if not any(ln.startswith(f"**{part}:**") for ln in lines):
        print(f"journal entry has no **{part}:** line")
        raise SystemExit(0)
PY
)"
[[ -z "$REASON" ]] || fail "$REASON"
echo "$LABEL: PASS"
