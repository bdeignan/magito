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


def run_worker(home: Path, args: list[str], extra_env: dict | None = None) -> subprocess.CompletedProcess:
    worker = repo_root() / "skills" / "general" / "implement" / "scripts" / "worker.py"
    env = dict(os.environ)
    env.pop("MAGITO_THRIFTY", None)
    env.pop("MAGITO_WORKERS_FILE", None)
    env["HOME"] = str(home)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(worker), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def run_reviewer(home: Path, writer_family: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    return run_worker(home, ["reviewer", writer_family], extra_env)


def write_roster(home: Path, lines: list[str]) -> Path:
    magito = home / ".magito"
    magito.mkdir(parents=True, exist_ok=True)
    roster = magito / "workers.toml"
    roster.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return roster


def case(name: str, roster: list[str], writer_family: str, expected_stdout: str | None, expected_code: int,
         stderr_has: str | None = None, env: dict | None = None) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        write_roster(home, roster)
        r = run_reviewer(home, writer_family, env)
        ok = r.returncode == expected_code and (expected_stdout is None or r.stdout.strip() == expected_stdout)
        ok = ok and (stderr_has is None or stderr_has in r.stderr)
        if ok:
            print(f"ok - {name}")
        else:
            print(f"not ok - {name}")
            print(f"    expected code={expected_code} stdout={expected_stdout!r}")
            print(f"    got code={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r}")
        return ok


def cmd_case(name: str, roster: list[str], args: list[str], expected_stdout: str, expected_code: int = 0,
             env: dict | None = None) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        write_roster(home, roster)
        r = run_worker(home, args, env)
        ok = r.returncode == expected_code and r.stdout == expected_stdout
        print(f"{'ok' if ok else 'not ok'} - {name}")
        if not ok:
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

    def two(top: list[str], a_tier: str = "strong", b_tier: str = "cheap") -> list[str]:
        return top + [
            "[workers.a]", f'cmd = "{passing_cmd}"', 'family = "openai"',
            *([f'tier = "{a_tier}"'] if a_tier else []),
            "[workers.b]", f'cmd = "{passing_cmd}"', 'family = "google"',
            *([f'tier = "{b_tier}"'] if b_tier else []),
        ]

    on = ["thrifty = true"]
    results += [
        case("thrifty roster key picks the cheap worker", two(on), "anthropic", "b", 0),
        case("MAGITO_THRIFTY=0 overrides thrifty = true", two(on), "anthropic", "a", 0,
             env={"MAGITO_THRIFTY": "0"}),
        case("MAGITO_THRIFTY=1 with no roster key picks the cheap worker", two([]), "anthropic", "b", 0,
             env={"MAGITO_THRIFTY": "1"}),
        case("thrifty with no tier on b counts b as strong, exit 3", two(on, "strong", ""), "anthropic",
             None, 3, stderr_has="worker.py: thrifty mode: no cheap reviewer outside family 'anthropic' passed its probe"),
        case("thrifty with only strong workers exits 3 with the thrifty message", two(on, "strong", "strong"),
             "anthropic", None, 3,
             stderr_has="worker.py: thrifty mode: no cheap reviewer outside family 'anthropic' passed its probe"),
        cmd_case("thrifty prints on for thrifty = true", two(on), ["thrifty"], "on\n"),
        cmd_case("thrifty prints off with no key", two([]), ["thrifty"], "off\n"),
        cmd_case("thrifty prints off when MAGITO_THRIFTY=0 overrides", two(on), ["thrifty"], "off\n",
                 env={"MAGITO_THRIFTY": "0"}),
        cmd_case("thrifty prints on for MAGITO_THRIFTY=1", two([]), ["thrifty"], "on\n",
                 env={"MAGITO_THRIFTY": "1"}),
        cmd_case("workers lists all in file order with thrifty off", two([]), ["workers"], "a\nb\n"),
        cmd_case("workers lists only cheap with thrifty on", two(on), ["workers"], "b\n"),
        cmd_case("workers prints nothing and exits 0 when thrifty has no cheap worker",
                 two(on, "strong", "strong"), ["workers"], ""),
    ]

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
