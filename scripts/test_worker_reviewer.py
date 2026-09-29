#!/usr/bin/env python3
"""Tests for worker.py reviewer subcommand. Stdlib only."""
import os
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


def case(name: str, roster: list[str], writer_family: str, expected_stdout: str | None, expected_code: int,
         stderr_has: str | None = None) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        write_roster(home, roster)
        r = run_reviewer(home, writer_family)
        ok = r.returncode == expected_code and (expected_stdout is None or r.stdout.strip() == expected_stdout)
        ok = ok and (stderr_has is None or stderr_has in r.stderr)
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
        case(
            "missing binary is skipped, next passes",
            [
                'spec_reviewer = "a"',
                "[workers.a]",
                'cmd = "no-such-binary-magito-test {brief}"',
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
            "non-string family is skipped, next passes",
            [
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                "family = 1",
                "[workers.b]",
                f'cmd = "{passing_cmd}"',
                'family = "google"',
            ],
            "anthropic",
            "b",
            0,
        ),
        case(
            "non-string spec_reviewer errors",
            [
                'spec_reviewer = ["a"]',
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                'family = "openai"',
            ],
            "anthropic",
            None,
            2,
        ),
        case(
            "reviewers list order wins over file order",
            [
                'reviewers = ["b", "a"]',
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
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
            "reviewers wins over spec_reviewer, stderr says so",
            [
                'reviewers = ["a"]',
                'spec_reviewer = "b"',
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                'family = "openai"',
                "[workers.b]",
                f'cmd = "{passing_cmd}"',
                'family = "google"',
            ],
            "anthropic",
            "a",
            0,
            stderr_has="worker.py: spec_reviewer ignored; reviewers is set",
        ),
        case(
            "reviewers as a string errors",
            [
                'reviewers = "a"',
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                'family = "openai"',
            ],
            "anthropic",
            None,
            2,
        ),
        case(
            "reviewers naming a missing worker errors",
            [
                'reviewers = ["zzz"]',
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                'family = "openai"',
            ],
            "anthropic",
            None,
            2,
        ),
        case(
            "reviewers with a non-string item errors",
            [
                "reviewers = [1]",
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
                'family = "openai"',
            ],
            "anthropic",
            None,
            2,
        ),
        case(
            "empty reviewers behaves as absent (spec_reviewer still used, no ignored line)",
            [
                "reviewers = []",
                'spec_reviewer = "b"',
                "[workers.a]",
                f'cmd = "{passing_cmd}"',
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
            "first ranked reviewer fails probe, next ranked passes",
            [
                'reviewers = ["a", "c"]',
                "[workers.a]",
                f'cmd = "{failing_cmd}"',
                'family = "openai"',
                "[workers.b]",
                f'cmd = "{passing_cmd}"',
                'family = "google"',
                "[workers.c]",
                f'cmd = "{passing_cmd}"',
                'family = "moonshot"',
            ],
            "anthropic",
            "c",
            0,
        ),
    ]

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
