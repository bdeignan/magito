#!/usr/bin/env bash
# eval-intent.sh — headless check that `intent` opens its draft doc correctly: one new
# file named NNNN-<slug>.md in the folder the repo configures, with the next free
# number, the header line `Status: draft · Opened: <today>`, and the seven required
# sections in order. No other file may change. Run as:
#   bash scripts/eval-intent.sh <worker>
# where <worker> names a roster worker. Not part of scripts/check.sh: it calls a
# paid model. Set MAGITO_EVAL_VARIANT to run another case:
#   (default)    docs/intent/ is empty; the file is docs/intent/0001-<slug>.md
#   next-number  docs/intent/ holds 0001-a.md and 0003-c.md; the file is
#                docs/intent/0004-<slug>.md
#   custom-dir   .magito/config.toml sets intent_dir = "design/intents"; the file is
#                design/intents/0001-<slug>.md and nothing is created under docs/intent/
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: bash scripts/eval-intent.sh <worker>" >&2
  exit 2
fi

WORKER="$1"
VARIANT="${MAGITO_EVAL_VARIANT:-}"
case "$VARIANT" in
  ""|next-number|custom-dir) ;;
  *) echo "unknown MAGITO_EVAL_VARIANT: $VARIANT" >&2; exit 2 ;;
esac
LABEL="intent"
[[ -n "$VARIANT" ]] && LABEL="intent ($VARIANT)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAGITO="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKER_PY="$MAGITO/skills/general/implement/scripts/worker.py"

TMP_BASE="$(mktemp -d)"
echo "eval evidence: $TMP_BASE"
trap 'eval_status=$?; if [[ $eval_status -ne 0 ]]; then echo "eval failed ($eval_status); evidence: $TMP_BASE" >&2; fi' EXIT
REPO="$TMP_BASE/repo"
BRIEF="$TMP_BASE/brief.txt"
RAW="$TMP_BASE/worker.raw"
LOG="$TMP_BASE/worker.log"
RESPONSE="$TMP_BASE/worker.response"

# The temp repo is kept on purpose: the files and logs are the evidence.
git init -b main "$REPO" >/dev/null 2>&1
git -C "$REPO" config user.name "eval"
git -C "$REPO" config user.email "eval@example.invalid"
mkdir -p "$REPO/.magito" "$REPO/docs/agents" "$REPO/docs/adr"

INTENT_DIR="docs/intent"
[[ "$VARIANT" == "custom-dir" ]] && INTENT_DIR="design/intents"
EXPECT_NUMBER="0001"
[[ "$VARIANT" == "next-number" ]] && EXPECT_NUMBER="0004"

cat > "$REPO/.magito/config.toml" <<TOML
mode = "owner"
tracker = "local"
check = "python3 -m unittest -q"
intent_dir = "$INTENT_DIR"
TOML

cat > "$REPO/README.md" <<'MD'
# notes-cli

A small command-line tool that stores short text notes in a local file.
MD

cat > "$REPO/docs/agents/INDEX.md" <<'MD'
# notes-cli: agent docs index

Read `GLOSSARY.md` for the project's words. Decisions live in `docs/adr/`.
MD

cat > "$REPO/docs/agents/GLOSSARY.md" <<'MD'
# notes-cli: glossary

**note** — one line of text the user saves with `notes add`.

**notebook** — the single file, `notes.txt`, that holds every note.
MD

cat > "$REPO/docs/adr/0001-plain-text-notebook.md" <<'MD'
# 0001. The notebook is one plain-text file

Status: accepted

Every note is one line in `notes.txt`. A database would add a dependency for no gain at
this size.
MD

cat > "$REPO/notes.py" <<'PY'
import sys
from pathlib import Path

NOTEBOOK = Path("notes.txt")


def add(text: str) -> None:
    with NOTEBOOK.open("a") as f:
        f.write(text + "\n")


def listing() -> list[str]:
    return NOTEBOOK.read_text().splitlines() if NOTEBOOK.exists() else []


if __name__ == "__main__":
    if sys.argv[1:2] == ["add"]:
        add(" ".join(sys.argv[2:]))
    else:
        print("\n".join(listing()))
PY

mkdir -p "$REPO/$INTENT_DIR"
if [[ "$VARIANT" == "next-number" ]]; then
  printf '# Intent: a\n\nStatus: accepted · Opened: 2026-01-01 · Accepted: 2026-01-01\n' > "$REPO/docs/intent/0001-a.md"
  printf '# Intent: c\n\nStatus: accepted · Opened: 2026-01-03 · Accepted: 2026-01-03\n' > "$REPO/docs/intent/0003-c.md"
else
  # An empty folder cannot be tracked; the placeholder is not a numbered intent.
  : > "$REPO/$INTENT_DIR/.gitkeep"
fi
if [[ "$VARIANT" == "custom-dir" ]]; then
  # The default folder must not exist, so anything created there is a mistake.
  :
else
  mkdir -p "$REPO/docs/intent"
fi

git -C "$REPO" add -f .
git -C "$REPO" commit -q -m "fixture"
BASE_SHA="$(git -C "$REPO" rev-parse HEAD)"

cat > "$BRIEF" <<EOF
Read $MAGITO/skills/general/intent/SKILL.md and follow it. Where it says <skills>, use
$MAGITO/skills/general.

The change, as the user put it: "People forget what they saved. The notes tool should
somehow help them find old notes again, maybe with search or maybe with tags, I have not
decided. It should stay simple."

Run intent on that change. Do recon, open the draft doc, ask your first question, and stop
there. Do not wait for an answer and do not accept the doc.

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
open(sys.argv[2], "w").write(response)
PYEOF

fail() { echo "$LABEL: FAIL ($1)"; exit 1; }

# State checks only: the response is not read. Python prints the reason on a failure.
REASON="$(python3 - "$REPO" "$INTENT_DIR" "$EXPECT_NUMBER" "$BASE_SHA" <<'PYEOF'
import datetime
import re
import subprocess
import sys
from pathlib import Path

repo, intent_dir, number, base = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]


def git(*args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def bad(reason):
    print(reason)
    raise SystemExit(1)


if git("rev-parse", "HEAD").strip() != base:
    bad("a commit was made; intent must leave the draft uncommitted")
lines = [ln for ln in git("status", "--porcelain", "--untracked-files=all").splitlines() if ln]
new = [ln[3:] for ln in lines if ln.startswith("?? ")]
if len(new) != 1:
    bad(f"expected exactly one new file, found {len(new)}")
if len(lines) != 1:
    bad("a file other than the new one changed")
path = new[0]
if not re.fullmatch(re.escape(intent_dir) + "/" + number + r"-[a-z0-9]+(-[a-z0-9]+)*\.md", path):
    bad(f"new file is {path}, expected {intent_dir}/{number}-<slug>.md")
if intent_dir != "docs/intent" and (repo / "docs/intent").exists():
    bad("something was created under docs/intent/")

text = (repo / path).read_text(encoding="utf-8")
header = next((ln for ln in text.splitlines() if ln.startswith("Status:")), "")
want = f"Status: draft · Opened: {datetime.date.today()}"
if not header.startswith(want):
    bad(f"header line does not start with '{want}'")
want_headings = ["Problem", "Proposed outcome", "Decisions so far", "Affected users and systems",
                 "Out of scope", "Constraints", "Open questions"]
got = [ln[3:].strip() for ln in text.splitlines() if ln.startswith("## ")]
got = [h for h in got if h != "Not yet clear"]
if got != want_headings:
    bad("headings are not " + ", ".join(want_headings) + " in order")
PYEOF
)" || fail "$REASON"
echo "$LABEL: PASS"

echo "response: $RESPONSE"
echo "raw output: $RAW"
echo "log: $LOG"
echo "repo: $REPO"
