#!/usr/bin/env python3
"""
test_install_codex_hooks.py — install.py links the guardrail hooks for Codex, registers
them in Codex's hook file with a fail-open command, and never breaks a machine that runs
no hooks. See docs/intent/0004-pilot-guardrail-gaps.md.

Runs the real install.py against a temporary HOME. Stdlib only. Exits 0 when every
case passes, 1 otherwise.
"""
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("install_module", REPO / "install.py")
_install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_install)
fail_open_command = _install.fail_open_command
HOOKS = ["review-gate.py", "staging-guard.py"]
FAILURES: list[str] = []


def check(cond: bool, label: str) -> None:
    if not cond:
        FAILURES.append(label)
        print(f"FAIL: {label}")


def install(home: Path, toml: str) -> subprocess.CompletedProcess:
    cfg = home / "install.toml"
    cfg.write_text(toml)
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run(
        [sys.executable, str(REPO / "install.py"), "--config", str(cfg)],
        capture_output=True, text=True, env=env,
    )


def codex_toml(home: Path, hooks: bool = True) -> str:
    text = f'[tools.codex]\nenabled = true\ninstructions = "{home}/.codex/AGENTS.md"\n'
    if hooks:
        text += f'hooks = "{home}/.codex/hooks"\nhooks_config = "{home}/.codex/hooks.json"\n'
    return text


def commands(hooks_json: Path) -> list[str]:
    data = json.loads(hooks_json.read_text())
    return [
        h["command"]
        for entry in data["hooks"]["PreToolUse"]
        for h in entry["hooks"]
    ]


def commands_for(hooks_json: Path, name: str, home: Path) -> list[str]:
    path = str(home / ".codex" / "hooks" / name)
    return [c for c in commands(hooks_json) if path in shlex.split(c)]


def run_registered(command: str, stdin: str) -> subprocess.CompletedProcess:
    return subprocess.run(["sh", "-c", command], input=stdin, capture_output=True, text=True)


def backups(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.glob("hooks.json.bak.*"))


def payload(command: str) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(REPO)})


def seed(home: Path, entries: list[dict]) -> Path:
    path = home / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hooks": {"PreToolUse": entries}}, indent=2) + "\n")
    return path


def entry(command: str) -> dict:
    return {"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}


def case_fresh_install_and_fail_open() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        result = install(home, codex_toml(home))
        check(result.returncode == 0, f"fresh install exits 0 ({result.stderr.strip()})")
        hooks_json = home / ".codex" / "hooks.json"
        for name in HOOKS:
            link = home / ".codex" / "hooks" / name
            check(link.is_symlink() and link.resolve() == (REPO / "hooks" / name).resolve(),
                  f"{name} is linked into the repo")
        check(hooks_json.exists(), "hooks.json is created")
        if not hooks_json.exists():
            return
        for name in HOOKS:
            check(len(commands_for(hooks_json, name, home)) == 1, f"{name} is registered once")

        # Present script: each registered command runs its script and exits 0 on a harmless call.
        for name in HOOKS:
            cmd = commands_for(hooks_json, name, home)[0]
            check(cmd == fail_open_command(str(home / ".codex" / "hooks" / name)),
                  f"{name} is registered as the fail-open command")
            ran = run_registered(cmd, payload("git status"))
            check(ran.returncode == 0 and not ran.stdout, f"{name} registered command runs and allows 'git status'")
        cmd = commands_for(hooks_json, "staging-guard.py", home)[0]
        ran = run_registered(cmd, payload("git add -A"))
        check("deny" in ran.stdout, "staging-guard registered command passes stdin to its script")

        # The wrapper hands stdin to the script it runs: a stub that echoes its input proves it.
        stub = home / "echo-stdin.sh"
        stub.write_text("#!/bin/sh\ncat\n")
        stub.chmod(0o755)
        echoed = run_registered(fail_open_command(str(stub)), "hello-from-stdin")
        check(echoed.stdout == "hello-from-stdin", "the fail-open wrapper passes stdin through to the script")

        # Second run adds nothing.
        install(home, codex_toml(home))
        for name in HOOKS:
            check(len(commands_for(hooks_json, name, home)) == 1, f"{name} stays registered once after a rerun")

        # Missing script: exit 0, no output.
        for name in HOOKS:
            (home / ".codex" / "hooks" / name).unlink()
            cmd = commands_for(hooks_json, name, home)[0]
            gone = run_registered(cmd, payload("git status"))
            check(gone.returncode == 0 and not gone.stdout and not gone.stderr,
                  f"{name} registered command is silent and exits 0 when the script is missing")


def case_unrelated_hook_kept() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        seed(home, [entry("/usr/local/bin/other-hook")])
        install(home, codex_toml(home))
        cmds = commands(home / ".codex" / "hooks.json")
        check("/usr/local/bin/other-hook" in cmds, "an unrelated hook survives the install")
        check(len(cmds) == 3, f"unrelated hook plus two registrations (got {len(cmds)})")


def case_invalid_json_untouched() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        path = home / ".codex" / "hooks.json"
        path.parent.mkdir(parents=True)
        path.write_text("{ not json")
        result = install(home, codex_toml(home))
        check(path.read_text() == "{ not json", "invalid hooks.json is left byte-for-byte unchanged")
        check("SKIPPED" in result.stdout, "install output says SKIPPED for invalid hooks.json")
        check(result.returncode == 0, "install still exits 0 on invalid hooks.json")
        check(not backups(path.parent), "no backup is made for a skipped file")


def case_hand_made_registrations_upgraded(quoted: bool) -> None:
    label = "single-quoted" if quoted else "bare"
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        paths = {n: str(home / ".codex" / "hooks" / n) for n in HOOKS}
        wrap = (lambda p: f"'{p}'") if quoted else (lambda p: p)
        path = seed(home, [entry(wrap(paths[n])) for n in HOOKS] + [entry("/usr/local/bin/other-hook")])
        result = install(home, codex_toml(home))
        check(result.returncode == 0, f"{label}: install exits 0")
        cmds = commands(path)
        for name in HOOKS:
            found = commands_for(path, name, home)
            check(len(found) == 1, f"{label}: {name} has exactly one entry (got {len(found)})")
            check(found and found[0].startswith("sh -c "), f"{label}: {name} is rewritten to the fail-open form")
        check("/usr/local/bin/other-hook" in cmds, f"{label}: the unrelated hook is unchanged")
        check(len(cmds) == 3, f"{label}: no entry was added (got {len(cmds)})")
        check(len(backups(path.parent)) == 1, f"{label}: one backup exists")
        again = install(home, codex_toml(home))
        check("already configured" in again.stdout, f"{label}: a rerun reports already configured")
        check(len(backups(path.parent)) == 1, f"{label}: a rerun makes no new backup")


def case_hooks_off() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        result = install(home, codex_toml(home, hooks=False))
        check(result.returncode == 0, "codex stanza without hooks keys installs clean")
        check(not (home / ".codex" / "hooks").exists(), "no hooks folder is created without a hooks key")
        check(not (home / ".codex" / "hooks.json").exists(), "no hooks.json is written without a hooks key")
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        toml = (
            f'[tools.claude]\nenabled = true\ninstructions = "{home}/.claude/CLAUDE.md"\n'
            f'skills = "{home}/.claude/skills"\nagents = "{home}/.claude/agents"\n'
        )
        result = install(home, toml)
        check(result.returncode == 0, "claude stanza without a hooks key installs clean")
        check(not (home / ".claude" / "hooks").exists(), "no claude hooks folder without a hooks key")
        check(not (home / ".claude" / "settings.json").exists(), "no claude settings.json written without a hooks key")


def main() -> int:
    case_fresh_install_and_fail_open()
    case_unrelated_hook_kept()
    case_invalid_json_untouched()
    case_hand_made_registrations_upgraded(quoted=True)
    case_hand_made_registrations_upgraded(quoted=False)
    case_hooks_off()
    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed")
        return 1
    print("test_install_codex_hooks: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
