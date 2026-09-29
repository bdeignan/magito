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
    python3 worker.py thrifty
    python3 worker.py workers

probe strips approval-bypass flags (a ping needs no permissions) and checks the
worker answers VERDICT-OK. reviewer picks a working worker whose family differs
from the writer's, trying the top-level `reviewers` list first (or the older
`spec_reviewer` name). Judgement (bootstrap, fallback choice) stays with the driver;
this script only fails loudly. Thrifty mode (env MAGITO_THRIFTY=1, or `thrifty = true`
in the roster; MAGITO_THRIFTY=0 forces it off) limits reviewer to workers whose `tier`
is `cheap`, with no tier counting as `strong`. thrifty prints on or off. workers prints
the roster's worker names in file order, only cheap ones when thrifty is on, no probe. Exit: 0 ok, 2 config error, 3 probe fail or no
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

ROSTER = Path(os.environ.get("MAGITO_WORKERS_FILE", Path.home() / ".magito" / "workers.toml"))
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


def thrifty_on(data) -> bool:
    env = os.environ.get("MAGITO_THRIFTY")
    if env == "0":
        return False
    if env == "1":
        return True
    flag = data.get("thrifty", False)
    if not isinstance(flag, bool):
        die(2, f"thrifty in {ROSTER} must be true or false, got: {flag!r}")
    return flag


def is_cheap(entry) -> bool:
    return isinstance(entry, dict) and entry.get("tier") == "cheap"


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
        writer_family = args[1]
        data = load_roster()
        workers = data.get("workers", {})
        if not isinstance(workers, dict):
            die(2, f"'workers' in {ROSTER} must be a table of [workers.<name>] entries")
        ranked = data.get("reviewers")
        spec_name = data.get("spec_reviewer")
        if ranked is not None:
            if (not isinstance(ranked, list)
                    or not all(isinstance(n, str) for n in ranked)):
                die(2, f"reviewers in {ROSTER} must be a list of worker name strings, "
                       f"got: {ranked!r}")
            for n in ranked:
                if n not in workers:
                    die(2, f"reviewers names '{n}', which is not in {ROSTER}")
        if ranked:
            if spec_name is not None:
                print("worker.py: spec_reviewer ignored; reviewers is set", file=sys.stderr)
            names = list(dict.fromkeys(ranked))
        else:
            # Absent or empty reviewers: the old single-name key counts as a list of one.
            if spec_name is not None and not isinstance(spec_name, str):
                die(2, f"spec_reviewer in {ROSTER} must be a worker name string")
            if spec_name is not None and spec_name not in workers:
                die(2, f"spec_reviewer '{spec_name}' is not in {ROSTER}")
            names = [spec_name] if spec_name is not None else []
        for name in workers:
            if name not in names:
                names.append(name)
        thrifty = thrifty_on(data)
        for name in names:
            entry = workers[name]
            if thrifty and not is_cheap(entry):
                print(f"worker.py: skip {name}: thrifty mode, tier is not cheap", file=sys.stderr)
                continue
            family = entry.get("family") if isinstance(entry, dict) else None
            if family is None:
                print(f"worker.py: skip {name}: no family", file=sys.stderr)
                continue
            if not isinstance(family, str):
                print(f"worker.py: skip {name}: family is not a string", file=sys.stderr)
                continue
            if family.lower() == writer_family.lower():
                print(f"worker.py: skip {name}: same family ({family})", file=sys.stderr)
                continue
            # A dead candidate (missing binary, no cmd, probe timeout) makes
            # probe_ok die(); that must skip to the next candidate, not end the search.
            try:
                ok = probe_ok(name)
            except SystemExit:
                ok = False
            if ok:
                print(name)
                sys.exit(0)
            print(f"worker.py: skip {name}: probe failed", file=sys.stderr)
        if thrifty:
            die(3, f"thrifty mode: no cheap reviewer outside family '{writer_family}' passed its probe")
        die(3, f"no reviewer outside family '{writer_family}' passed its probe")
    elif args[:1] == ["thrifty"]:
        print("on" if thrifty_on(load_roster()) else "off")
        sys.exit(0)
    elif args[:1] == ["workers"]:
        data = load_roster()
        workers = data.get("workers", {})
        if not isinstance(workers, dict):
            die(2, f"'workers' in {ROSTER} must be a table of [workers.<name>] entries")
        thrifty = thrifty_on(data)
        for name, entry in workers.items():
            if not thrifty or is_cheap(entry):
                print(name)
        sys.exit(0)
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
               "worker.py thrifty | worker.py workers | "
               "worker.py run <worker> <dir> <brief-file> [timeout]")


if __name__ == "__main__":
    main()
