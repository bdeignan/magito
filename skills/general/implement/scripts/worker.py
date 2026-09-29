#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Deterministic launcher for shell workers (see ../references/worker-contract.md).

Resolves a named worker from ~/.magito/workers.toml, substitutes placeholders at
the argv level (no shell re-quoting — cmd is an argv template: no &&, |, or cd),
runs the worker with its working directory set, and enforces a timeout.

    python3 worker.py probe <worker>
    python3 worker.py run   <worker> <dir> <brief-file> [timeout-seconds]
    python3 worker.py reviewer <writer-family>

probe strips approval-bypass flags (a ping needs no permissions) and checks the
worker answers VERDICT-OK. reviewer picks a working worker whose family differs
from the writer's. Judgement (bootstrap, fallback choice) stays with the driver;
this script only fails loudly. Exit: 0 ok, 2 config error, 3 probe fail or no
reviewer found, 124 timeout, otherwise the worker's own exit code. Stdlib only,
by design.
"""
import os
import shlex
import signal
import subprocess
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

ROSTER = Path.home() / ".magito" / "workers.toml"
BYPASS_PAIRS = {"--approval-mode", "--permission-mode"}  # flag + value
BYPASS_SINGLE = {
    "--auto-approve", "--yolo", "--full-auto",
    "--dangerously-skip-permissions", "--dangerously-bypass-approvals-and-sandbox",
}
PROBE_PROMPT = "Reply with exactly: VERDICT-OK"


def die(code, msg):
    print(f"worker.py: {msg}", file=sys.stderr)
    sys.exit(code)


def load_roster():
    if not ROSTER.exists():
        die(2, f"{ROSTER} not found — bootstrap it per worker-contract.md")
    try:
        with open(ROSTER, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        die(2, f"{ROSTER} is not valid TOML: {e}")


def resolve(name):
    data = load_roster()
    entry = data.get("workers", {}).get(name)
    if entry is None:
        live = ", ".join(data.get("workers", {})) or "none"
        die(2, f"no worker '{name}' in {ROSTER} (live: {live})")
    if "cmd" not in entry:
        die(2, f"worker '{name}' declares no cmd")
    return entry


def probe_ok(name, echo_failure=False) -> bool:
    """Run a probe against the named worker. Return True iff it answers VERDICT-OK.
    echo_failure replays a failed probe's output for diagnosis — off for reviewer,
    whose stdout must hold only the chosen worker's name."""
    entry = resolve(name)
    here = str(Path.cwd())
    argv = strip_bypass(build_argv(entry, name, here, PROBE_PROMPT))
    r = run(argv, here, 90, capture=True)
    ok = r.returncode == 0 and "VERDICT-OK" in r.stdout
    if not ok and echo_failure:
        print(r.stdout, end="")
        print(r.stderr, end="", file=sys.stderr)
        print(f"worker.py: probe exit {r.returncode}", file=sys.stderr)
    return ok


def build_argv(entry, name, cwd, brief):
    tokens = shlex.split(entry["cmd"])
    for bad in ("&&", "||", "|", ";", "cd"):
        if bad in tokens:
            die(2, f"worker '{name}' cmd contains shell operator '{bad}' — "
                   "cmd is an argv template; drop it (worker.py sets the cwd itself)")
    model = entry.get("model", "")
    argv = []
    for tok in tokens:
        if "{model}" in tok:
            if not model:
                die(2, f"worker '{name}' cmd uses {{model}} but declares no model")
            tok = tok.replace("{model}", model)
        tok = tok.replace("{cwd}", cwd)
        tok = tok.replace("{brief}", brief)
        argv.append(tok)
    return argv


def strip_bypass(argv):
    out, skip = [], False
    for tok in argv:
        if skip:
            skip = False
            continue
        if tok in BYPASS_PAIRS:
            skip = True
            continue
        if (tok.split("=")[0] in BYPASS_PAIRS or tok in BYPASS_SINGLE
                or tok.startswith("--dangerously-")):
            continue
        out.append(tok)
    return out


def worker_env():
    """The environment a delegated worker runs in. Drops CLAUDE_CODE_SESSION_ID so
    a worker can't inherit the driver's Claude Code session identity — retained as
    hygiene for subprocess workers, even though nothing currently reads it."""
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_SESSION_ID", None)
    return env


def run(argv, cwd, timeout, capture):
    pipe = subprocess.PIPE if capture else None
    try:
        # New session = own process group, so a timeout kill reaps the worker's
        # children too, not just the CLI process itself.
        p = subprocess.Popen(
            argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=pipe, stderr=pipe,
            text=True, start_new_session=True, env=worker_env(),
        )
    except FileNotFoundError:
        die(2, f"binary not found: {argv[0]}")
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.wait()
        die(124, f"worker timed out after {timeout}s (process group killed)")
    return SimpleNamespace(returncode=p.returncode, stdout=out or "", stderr=err or "")


def main():
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "probe":
        name = args[1]
        if probe_ok(name, echo_failure=True):
            print(f"PROBE OK: {name}")
            sys.exit(0)
        die(3, f"probe failed for '{name}' (no VERDICT-OK)")
    elif len(args) >= 2 and args[0] == "reviewer":
        writer_family = args[1].lower()
        data = load_roster()
        workers = data.get("workers", {})
        spec_name = data.get("spec_reviewer")
        if spec_name is not None and spec_name not in workers:
            die(2, f"spec_reviewer '{spec_name}' is not in {ROSTER}")
        names = []
        if spec_name is not None:
            names.append(spec_name)
        for name in workers:
            if name not in names:
                names.append(name)
        for name in names:
            entry = workers[name]
            family = entry.get("family")
            if family is None:
                print(f"worker.py: skip {name}: no family", file=sys.stderr)
                continue
            if family.lower() == writer_family:
                print(f"worker.py: skip {name}: same family ({family})", file=sys.stderr)
                continue
            if probe_ok(name):
                print(name)
                sys.exit(0)
            print(f"worker.py: skip {name}: probe failed", file=sys.stderr)
        die(3, f"no reviewer outside family '{writer_family}' passed its probe")
    elif len(args) >= 4 and args[0] == "run":
        name, cwd, brief_file = args[1], args[2], args[3]
        try:
            timeout = int(args[4]) if len(args) > 4 else 600
        except ValueError:
            die(2, f"timeout must be an integer number of seconds, got: {args[4]}")
        if not Path(cwd).is_dir():
            die(2, f"assigned directory does not exist: {cwd}")
        # Absolute before substitution: a relative {cwd} lands in flags like omp's
        # --cwd, which the worker resolves against its own already-changed directory.
        cwd = str(Path(cwd).resolve())
        try:
            brief = Path(brief_file).read_text()
        except OSError as e:
            die(2, f"cannot read brief file: {e}")
        entry = resolve(name)
        argv = build_argv(entry, name, cwd, brief)
        r = run(argv, cwd, timeout, capture=False)
        sys.exit(r.returncode)
    else:
        die(2, "usage: worker.py probe <worker> | "
               "worker.py reviewer <writer-family> | "
               "worker.py run <worker> <dir> <brief-file> [timeout]")


if __name__ == "__main__":
    main()
