#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Process-boundary checks for the paid to-issues evaluator, using a fake `claude` on PATH."""
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "scripts/eval-to-issues.sh"


FAKE_CLAUDE = '''#!/usr/bin/env python3
import json
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

print(json.dumps({"result": response, "permission_denials": []}))
'''


def run(mode: str, bindir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "TO_ISSUES_FAKE_MODE": mode}
    return subprocess.run(["bash", str(EVAL)], text=True, capture_output=True, env=env, check=False)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        bindir = Path(temp)
        claude = bindir / "claude"
        claude.write_text(FAKE_CLAUDE)
        claude.chmod(0o755)

        green = run("green", bindir)
        assert green.returncode == 0, green.stdout + green.stderr
        assert "accepted: PASS" in green.stdout, green.stdout
        assert "draft: PASS" in green.stdout, green.stdout

        asks = run("accepted-asks", bindir)
        assert asks.returncode == 1, asks.stdout + asks.stderr
        assert "accepted: FAIL (final response asks or waits for approval)" in asks.stdout, asks.stdout

        waits = run("accepted-waits", bindir)
        assert waits.returncode == 1, waits.stdout + waits.stderr

        missing = run("missing-ticket", bindir)
        assert missing.returncode == 1, missing.stdout + missing.stderr

        failed = run("worker-failure", bindir)
        assert failed.returncode == 73, failed.stdout + failed.stderr

    print("eval-to-issues: ok")


if __name__ == "__main__":
    main()
