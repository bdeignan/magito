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

probe strips approval-bypass flags (a ping needs no permissions) and checks the
worker answers VERDICT-OK. Judgement (bootstrap, fallback choice) stays with the
driver; this script only fails loudly. Exit: 0 ok, 2 config error, 3 probe fail,
124 timeout, otherwise the worker's own exit code. Stdlib only, by design.
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


def resolve(name):
    if not ROSTER.exists():
        die(2, f"{ROSTER} not found — bootstrap it per worker-contract.md")
    try:
        with open(ROSTER, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        die(2, f"{ROSTER} is not valid TOML: {e}")
    entry = data.get("workers", {}).get(name)
    if entry is None:
        live = ", ".join(data.get("workers", {})) or "none"
        die(2, f"no worker '{name}' in {ROSTER} (live: {live})")
    if "cmd" not in entry:
        die(2, f"worker '{name}' declares no cmd")
    return entry


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


def run(argv, cwd, timeout, capture):
    pipe = subprocess.PIPE if capture else None
    try:
        # New session = own process group, so a timeout kill reaps the worker's
        # children too, not just the CLI process itself.
        p = subprocess.Popen(
            argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=pipe, stderr=pipe,
            text=True, start_new_session=True,
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
        entry = resolve(name)
        here = str(Path.cwd())
        argv = strip_bypass(build_argv(entry, name, here, PROBE_PROMPT))
        r = run(argv, here, 90, capture=True)
        if r.returncode == 0 and "VERDICT-OK" in r.stdout:
            print(f"PROBE OK: {name}")
            sys.exit(0)
        print(r.stdout, end="")
        print(r.stderr, end="", file=sys.stderr)
        die(3, f"probe failed for '{name}' (exit {r.returncode}, no VERDICT-OK)")
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
               "worker.py run <worker> <dir> <brief-file> [timeout]")


if __name__ == "__main__":
    main()
