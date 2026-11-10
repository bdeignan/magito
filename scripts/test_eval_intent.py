#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Process-boundary checks for the paid intent evaluator, using a fake `claude` on PATH."""
import datetime
import os
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-intent.sh"
TODAY = str(datetime.date.today())

FAKE_CLAUDE = '''#!/usr/bin/env python3
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

repo = Path.cwd()
mode = os.environ.get("INTENT_FAKE_MODE", "green")
variant = os.environ.get("MAGITO_EVAL_VARIANT", "")

if mode == "worker-failure":
    raise SystemExit(73)

config = (repo / ".magito" / "config.toml").read_text()
intent_dir = re.search(r'intent_dir = "([^"]+)"', config).group(1)
if mode == "wrong-dir":
    intent_dir = "docs/intent"
folder = repo / intent_dir
folder.mkdir(parents=True, exist_ok=True)
numbers = [int(m.group(1)) for p in folder.glob("*.md") if (m := re.match(r"(\\d{4})-", p.name))]
number = max(numbers, default=0) + 1
if mode == "gap-filled":
    number = 2
if mode == "wrong-slug":
    name = f"{number:04d}-Bad_Slug.md"
else:
    name = f"{number:04d}-find-old-notes.md"

today = datetime.date.today()
if mode == "old-date":
    today = today - datetime.timedelta(days=3)
status = "accepted" if mode == "accepted" else "draft"
headings = ["Problem", "Proposed outcome", "Decisions so far", "Affected users and systems",
            "Out of scope", "Constraints", "Open questions"]
if mode == "swapped-sections":
    headings[0], headings[1] = headings[1], headings[0]
if mode == "missing-section":
    headings.remove("Constraints")
if mode == "with-not-yet-clear":
    headings.append("Not yet clear")

body = f"# Intent: find old notes\\n\\nStatus: {status} \\u00b7 Opened: {today}\\n\\n"
for h in headings:
    body += f"## {h}\\n\\nTBD\\n\\n"

if mode != "no-file":
    (folder / name).write_text(body, encoding="utf-8")
if mode == "extra-file":
    (folder / "0099-extra.md").write_text("# extra\\n")
if mode == "edits-tracked":
    (repo / "README.md").write_text("changed\\n")
if mode == "commits":
    subprocess.run(["git", "add", str(folder / name)], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "draft"], cwd=repo, check=True)

print(json.dumps({"result": "Opened the draft. First question: search or tags? I recommend search.\\n",
                  "permission_denials": []}))
'''


def run(mode: str, bindir: Path, variant: str = "") -> subprocess.CompletedProcess[str]:
    env = os.environ | {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "INTENT_FAKE_MODE": mode}
    env.pop("MAGITO_EVAL_VARIANT", None)
    if variant:
        env["MAGITO_EVAL_VARIANT"] = variant
    return subprocess.run(["bash", str(EVAL)], text=True, capture_output=True, env=env, check=False)


HEADINGS = ("Problem, Proposed outcome, Decisions so far, Affected users and systems, "
            "Out of scope, Constraints, Open questions")


def passes(bindir: Path, mode: str, variant: str) -> None:
    label = f"intent ({variant})" if variant else "intent"
    r = run(mode, bindir, variant)
    assert r.returncode == 0, (mode, variant, r.stdout + r.stderr)
    assert f"{label}: PASS" in r.stdout, (mode, variant, r.stdout)
    # The evidence line is printed and names a directory that still exists.
    m = re.search(r"^eval evidence: (.+)$", r.stdout, re.M)
    assert m and Path(m.group(1)).is_dir(), r.stdout


def fails(bindir: Path, mode: str, variant: str, reason: str) -> None:
    label = f"intent ({variant})" if variant else "intent"
    r = run(mode, bindir, variant)
    assert r.returncode == 1, (mode, variant, r.stdout + r.stderr)
    expected = f"{label}: FAIL ({reason})"
    assert expected in r.stdout.splitlines(), (mode, variant, expected, r.stdout)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        bindir = Path(temp)
        claude = bindir / "claude"
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)

        # Passing runs, one per scenario. An optional "Not yet clear" section is allowed.
        for variant in ("", "next-number", "custom-dir"):
            passes(bindir, "green", variant)
        passes(bindir, "with-not-yet-clear", "")

        # default: docs/intent/ is empty, the file is 0001-<slug>.md.
        fails(bindir, "no-file", "", "expected exactly one new file, found 0")
        fails(bindir, "extra-file", "", "expected exactly one new file, found 2")
        fails(bindir, "edits-tracked", "", "a file other than the new one changed")
        fails(bindir, "commits", "", "a commit was made; intent must leave the draft uncommitted")
        fails(bindir, "wrong-slug", "", "new file is docs/intent/0001-Bad_Slug.md, expected docs/intent/0001-<slug>.md")
        fails(bindir, "accepted", "", f"header line does not start with 'Status: draft · Opened: {TODAY}'")
        fails(bindir, "old-date", "", f"header line does not start with 'Status: draft · Opened: {TODAY}'")
        fails(bindir, "swapped-sections", "", f"headings are not {HEADINGS} in order")
        fails(bindir, "missing-section", "", f"headings are not {HEADINGS} in order")

        # next-number: 0001 and 0003 exist, so the next free number is 0004.
        fails(bindir, "gap-filled", "next-number",
              "new file is docs/intent/0002-find-old-notes.md, expected docs/intent/0004-<slug>.md")
        fails(bindir, "no-file", "next-number", "expected exactly one new file, found 0")

        # custom-dir: the file goes to design/intents/, and docs/intent/ stays absent.
        fails(bindir, "wrong-dir", "custom-dir",
              "new file is docs/intent/0001-find-old-notes.md, expected design/intents/0001-<slug>.md")
        fails(bindir, "no-file", "custom-dir", "expected exactly one new file, found 0")

        failed = run("worker-failure", bindir)
        assert failed.returncode == 73, failed.stdout + failed.stderr

        # An unknown variant is a usage error.
        r = run("green", bindir, "no-such-variant")
        assert r.returncode == 2 and "unknown MAGITO_EVAL_VARIANT" in r.stderr, r.stdout + r.stderr

    print("eval-intent: ok")


if __name__ == "__main__":
    main()
