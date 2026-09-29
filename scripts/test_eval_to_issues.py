#!/usr/bin/env python3
"""Process-boundary checks for the paid to-issues evaluator."""
import os
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-to-issues.sh"


FAKE_WORKER = '''#!/usr/bin/env python3
import os
import sys
from pathlib import Path

repo = Path.cwd()
accepted = "Status: accepted" in (repo / "docs/intent/0001-hello.md").read_text()
mode = os.environ.get("TO_ISSUES_FAKE_MODE", "green")
if mode == "worker-failure" and accepted:
    raise SystemExit(73)

if accepted:
    ticket = repo / ".scratch/0001-hello/01-hello.md"
    ticket.parent.mkdir(parents=True, exist_ok=True)
    ticket.write_text("# hello\\n\\nMade: 2026-09-28\\nUse by: 2026-10-12\\n\\n## Done when\\n")
    response = "Tickets published.\\n"
    if mode == "accepted-asks":
        response += "Should I publish remaining tickets?\\nWaiting for your approval.\\n"
    if mode == "accepted-waits":
        response += "Waiting for your approval.\\n"
    if mode == "missing-ticket":
        ticket.unlink()
else:
    response = "Do you approve this ticket breakdown?\\nNo tickets published.\\n"

if mode == "outside-response":
    print("Should I continue?")
print("MAGITO_FINAL_RESPONSE_BEGIN")
print(response, end="")
print("MAGITO_FINAL_RESPONSE_END")
'''


def write_roster(roster: Path, worker: Path) -> None:
    roster.write_text(
        "[workers.fake]\n"
        f"cmd = {json.dumps('python3 ' + str(worker))}\n"
        'family = "test"\n'
    )


def run(mode: str, roster: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"MAGITO_WORKERS_FILE": str(roster), "TO_ISSUES_FAKE_MODE": mode}
    return subprocess.run(["bash", str(EVAL), "fake"], text=True, capture_output=True, env=env, check=False)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        roster = Path(temp) / "workers.toml"
        worker = Path(temp) / "fake_worker.py"
        worker.write_text(FAKE_WORKER)
        write_roster(roster, worker)

        green = run("green", roster)
        assert green.returncode == 0, green.stdout + green.stderr
        assert "accepted: PASS" in green.stdout, green.stdout
        assert "draft: PASS" in green.stdout, green.stdout

        asks = run("accepted-asks", roster)
        assert asks.returncode == 1, asks.stdout + asks.stderr
        assert "accepted: FAIL (final response asks or waits for approval)" in asks.stdout, asks.stdout

        waits = run("accepted-waits", roster)
        assert waits.returncode == 1, waits.stdout + waits.stderr

        outside = run("outside-response", roster)
        assert outside.returncode != 0, outside.stdout + outside.stderr

        missing = run("missing-ticket", roster)
        assert missing.returncode == 1, missing.stdout + missing.stderr

        failed = run("worker-failure", roster)
        assert failed.returncode == 73, failed.stdout + failed.stderr

    print("eval-to-issues: ok")


if __name__ == "__main__":
    main()
