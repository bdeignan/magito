#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Process-boundary checks for the paid catch-up evaluator, using fake workers."""
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-catch-up.sh"


FAKE_WORKER = '''#!/usr/bin/env python3
import os
import sys
from pathlib import Path

repo = Path.cwd()
mode = os.environ.get("CATCHUP_FAKE_MODE", "green")
variant = os.environ.get("MAGITO_EVAL_VARIANT", "")

if mode == "worker-failure":
    raise SystemExit(73)

journal = {"no-journal": "missing"}.get(variant, "read")
tracker = "skipped: no tracker configured, run /setup-magito" if variant == "no-tracker" else "read"
statuses = [
    ("journal", journal),
    ("CLAUDE.md", "read"),
    ("docs/agents/GLOSSARY.md", "read"),
    ("ADRs", "missing"),
    ("tracker", tracker),
    ("git", "read"),
    ("PRs", "skipped: no GitHub remote"),
]

if mode == "wrong-journal":
    statuses[0] = ("journal", "read" if journal == "missing" else "missing")
elif mode == "wrong-tracker":
    statuses[4] = ("tracker", "read" if tracker != "read" else "skipped: no tracker configured")
elif mode == "malformed-skipped":
    statuses[4] = ("tracker", "skippedOops")
elif mode == "wrong-order":
    statuses[1], statuses[2] = statuses[2], statuses[1]
elif mode == "omits-prs":
    statuses.pop()
elif mode == "omits-adrs":
    statuses.pop(3)

line = "sources: " + ", ".join(f"{k}={v}" for k, v in statuses)

if mode == "edits-file":
    (repo / "CLAUDE.md").write_text("changed\\n")
elif mode == "adds-file":
    (repo / "notes.txt").write_text("started work\\n")
elif mode == "deletes-file":
    (repo / "docs/agents/GLOSSARY.md").unlink()
elif mode == "edits-journal":
    journal_dir = repo / ".magito" / "journal"
    if journal_dir.exists():
        (journal_dir / "2026-10-03-090000-new-entry-aaaaaa.md").write_text("recorded\\n")
    else:
        (repo / ".magito").mkdir(exist_ok=True)
        (repo / ".magito" / "stray.txt").write_text("recorded\\n")

response = "Where we are: clean branch main.\\nNext: ticket 0001.\\n"
if mode == "no-sources":
    pass
elif mode == "two-sources":
    response += line + "\\n" + line + "\\n"
else:
    response += line + "\\n"
response += "What do you want to pick up?\\n"

print("MAGITO_FINAL_RESPONSE_BEGIN")
print(response, end="")
print("MAGITO_FINAL_RESPONSE_END")
'''


def run(mode: str, roster: Path, variant: str = "") -> subprocess.CompletedProcess[str]:
    env = os.environ | {"MAGITO_WORKERS_FILE": str(roster), "CATCHUP_FAKE_MODE": mode}
    env.pop("MAGITO_EVAL_VARIANT", None)
    if variant:
        env["MAGITO_EVAL_VARIANT"] = variant
    return subprocess.run(["bash", str(EVAL), "fake"], text=True, capture_output=True, env=env, check=False)


def label(variant: str) -> str:
    return f"catch-up ({variant})" if variant else "catch-up"


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        roster = Path(temp) / "workers.toml"
        worker = Path(temp) / "fake_worker.py"
        worker.write_text(FAKE_WORKER)
        roster.write_text(
            "[workers.fake]\n"
            f"cmd = {json.dumps('python3 ' + str(worker))}\n"
            'family = "test"\n'
        )

        # Every scenario has a passing run.
        for variant in ("", "no-journal", "no-tracker"):
            r = run("green", roster, variant)
            assert r.returncode == 0, (variant, r.stdout + r.stderr)
            assert f"{label(variant)}: PASS" in r.stdout, (variant, r.stdout)

        # Failing runs, in every scenario, with the exact reason.
        in_order = "sources line does not name every source in order"
        for variant in ("", "no-journal", "no-tracker"):
            cases = [
                ("edits-file", "fixture changed during the run: CLAUDE.md"),
                ("adds-file", "fixture changed during the run: notes.txt"),
                ("deletes-file", "fixture changed during the run: docs/agents/GLOSSARY.md"),
                ("no-sources", "response holds 0 lines starting with sources:, expected 1"),
                ("two-sources", "response holds 2 lines starting with sources:, expected 1"),
                ("wrong-order", in_order),
                ("omits-prs", in_order),
                ("omits-adrs", in_order),
            ]
            for mode, reason in cases:
                r = run(mode, roster, variant)
                assert r.returncode == 1, (variant, mode, r.stdout + r.stderr)
                want = f"{label(variant)}: FAIL ({reason})"
                assert want in r.stdout, (variant, mode, r.stdout)

        # The wrong status for the one source each scenario pins down.
        expected = {
            "": ("wrong-journal", "journal is 'missing' on the sources line, expected read"),
            "no-journal": ("wrong-journal", "journal is 'read' on the sources line, expected missing"),
            "no-tracker": ("wrong-tracker", "tracker is 'read' on the sources line, expected skipped"),
        }
        for variant, (mode, reason) in expected.items():
            r = run(mode, roster, variant)
            assert r.returncode == 1, (variant, mode, r.stdout + r.stderr)
            assert f"{label(variant)}: FAIL ({reason})" in r.stdout, (variant, mode, r.stdout)
        r = run("malformed-skipped", roster, "no-tracker")
        assert r.returncode == 1, r.stdout + r.stderr
        assert f"{label('no-tracker')}: FAIL (tracker is 'skippedOops' on the sources line, expected skipped)" in r.stdout, r.stdout
        r = run("wrong-tracker", roster, "")
        assert f"{label('')}: FAIL (tracker is 'skipped: no tracker configured' on the sources line, expected read)" in r.stdout, r.stdout

        # The excluded .magito/ folder counts too.
        r = run("edits-journal", roster, "")
        assert r.returncode == 1, r.stdout + r.stderr
        assert "catch-up: FAIL (fixture changed during the run: .magito/journal/2026-10-03-090000-new-entry-aaaaaa.md)" in r.stdout, r.stdout
        r = run("edits-journal", roster, "no-journal")
        assert "catch-up (no-journal): FAIL (fixture changed during the run: .magito/stray.txt)" in r.stdout, r.stdout

        # A worker failure is preserved.
        failed = run("worker-failure", roster)
        assert failed.returncode == 73, failed.stdout + failed.stderr

        # An unknown variant is a usage error.
        r = run("green", roster, "no-such-variant")
        assert r.returncode == 2 and "unknown MAGITO_EVAL_VARIANT" in r.stderr, r.stdout + r.stderr

    print("eval-catch-up: ok")


if __name__ == "__main__":
    main()
