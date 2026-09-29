#!/usr/bin/env python3
"""Tests for worker.py reviewer subcommand. Stdlib only."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def repo_root() -> Path:
    this = Path(__file__).resolve().parent
    return this.parent


def run_reviewer(home: Path, writer_family: str) -> subprocess.CompletedProcess:
    worker = repo_root() / "skills" / "general" / "implement" / "scripts" / "worker.py"
    env = dict(os.environ)
    env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(worker), "reviewer", writer_family],
        capture_output=True,
        text=True,
        env=env,
    )


def write_roster(home: Path, lines: list[str]) -> Path:
    magito = home / ".magito"
    magito.mkdir(parents=True, exist_ok=True)
    roster = magito / "workers.toml"
    roster.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return roster


def case(name: str, roster: list[str], writer_family: str, expected_stdout: str | None, expected_code: int) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        write_roster(home, roster)
        r = run_reviewer(home, writer_family)
        ok = r.returncode == expected_code and (expected_stdout is None or r.stdout.strip() == expected_stdout)
        if ok:
            print(f"ok - {name}")
        else:
            print(f"not ok - {name}")
            print(f"    expected code={expected_code} stdout={expected_stdout!r}")
            print(f"    got code={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r}")
        return ok


def main() -> int:
    passing_cmd = "echo {brief}"
    failing_cmd = "false {brief}"

    results = [
        case(
            "spec_reviewer picked when family differs",
            [
                'spec_reviewer = "a"',
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                'family = "openai"',
            ],
            "anthropic",
            "a",
            0,
        ),
        case(
            "spec_reviewer skipped on same family, next passes",
            [
                'spec_reviewer = "a"',
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                'family = "anthropic"',
                "[workers.b]",
                f'cmd = "{passing_cmd}"',
                'family = "google"',
            ],
            "anthropic",
            "b",
            0,
        ),
        case(
            "spec_reviewer fails probe, next passes",
            [
                'spec_reviewer = "a"',
                "[workers.a]",
                f'cmd = "{failing_cmd}"',
                'family = "openai"',
                "[workers.b]",
                f'cmd = "{passing_cmd}"',
                'family = "google"',
            ],
            "anthropic",
            "b",
            0,
        ),
        case(
            "family comparison is case-insensitive, no candidate outside family",
            [
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                "[workers.b]",
                f'cmd = "{passing_cmd}"',
                'family = "Anthropic"',
            ],
            "anthropic",
            None,
            3,
        ),
        case(
            "no spec_reviewer, first passing worker wins",
            [
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                'family = "openai"',
            ],
            "anthropic",
            "a",
            0,
        ),
        case(
            "spec_reviewer not in roster errors",
            [
                'spec_reviewer = "zzz"',
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                'family = "openai"',
            ],
            "anthropic",
            None,
            2,
        ),
    ]

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
