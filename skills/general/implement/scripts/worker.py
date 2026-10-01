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
    python3 worker.py review <worker> <dir> <brief-file> [timeout-seconds]
    python3 worker.py reviewer <writer-family> [--skip <worker>]...
    python3 worker.py ready [--family <family>]
    python3 worker.py start (--family <family> [--label <text>] | --builder <worker>)
                            [--intent <path>] [--small]
    python3 worker.py thrifty
    python3 worker.py workers

probe strips approval-bypass flags (a ping needs no permissions) and checks the
worker answers VERDICT-OK. reviewer picks a working worker whose family differs
from the writer's, trying the top-level `reviewers` list first (or the older
`spec_reviewer` name); --skip passes over a named candidate, for a run whose
reviewer failed in the middle of a review. It also passes over a candidate whose
`requires_env` names an unset variable, and any entry it cannot use. ready reports,
one line per roster worker, whether its program is installed, its `requires_env`
variables are set, and its probe answers; then whether an allow rule for this
launcher exists; then, with --family, which worker reviewer would pick. start prints
the one line that opens a run: who builds, who reviews (the same pick as reviewer, or
the subagent fallback whenever that pick fails), and whether a plan stop comes. Judgement
(bootstrap, fallback choice) stays with the driver; this script only fails loudly. Thrifty mode (env MAGITO_THRIFTY=1, or `thrifty = true`
in the roster; MAGITO_THRIFTY=0 forces it off) limits reviewer to workers whose `tier`
is `cheap`, with no tier counting as `strong`. thrifty prints on or off. workers prints
the roster's worker names in file order, only cheap ones when thrifty is on, no probe.
review runs one review round: it snapshots <dir> (plus <dir>/.scratch), runs the worker,
snapshots again, saves the full output to a file named on stderr, and prints only the
VERDICT and COVERAGE lines. ready exits 0 whenever the roster parsed as TOML, whatever
is wrong with a single entry or setting. Exit: 0 ok, 2 config error, 3 probe fail or no reviewer
found, 4 the reviewer changed files, 5 no verdict line, 124 timeout, otherwise the
worker's own exit code. Stdlib only,
by design.
"""
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
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
SHELL_OPS = ("&&", "||", "|", ";", "cd")
RESERVED = "subagent"  # the review record's word for a review by a fresh-context subagent
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


class Fault(Exception):
    """A top-level roster setting that the reviewer pick rejects."""


def die(code, msg):
    print(f"worker.py: {msg}", file=sys.stderr)
    sys.exit(code)


def read_roster():
    """(data, None), or (None, why it could not be read). Never exits."""
    if not ROSTER.exists():
        return None, f"{ROSTER} not found — bootstrap it per worker-contract.md"
    try:
        with open(ROSTER, "rb") as f:
            return tomllib.load(f), None
    except tomllib.TOMLDecodeError as e:
        return None, f"{ROSTER} is not valid TOML: {e}"
    except OSError as e:
        # A directory at the roster path, or a file this user cannot read.
        return None, f"{ROSTER} cannot be read: {e}"


def load_roster():
    data, problem = read_roster()
    if problem:
        die(2, problem)
    return data


def resolve(name):
    data = load_roster()
    entry = data.get("workers", {}).get(name)
    if entry is None:
        live = ", ".join(data.get("workers", {})) or "none"
        die(2, f"no worker '{name}' in {ROSTER} (live: {live})")
    if "cmd" not in entry:
        die(2, f"worker '{name}' declares no cmd")
    return entry


def thrifty_state(data) -> bool:
    env = os.environ.get("MAGITO_THRIFTY")
    if env == "0":
        return False
    if env == "1":
        return True
    flag = data.get("thrifty", False)
    if not isinstance(flag, bool):
        raise Fault(f"thrifty in {ROSTER} must be true or false, got: {flag!r}")
    return flag


def thrifty_on(data) -> bool:
    try:
        return thrifty_state(data)
    except Fault as e:
        die(2, str(e))


def is_cheap(entry) -> bool:
    return isinstance(entry, dict) and entry.get("tier") == "cheap"


def program_of(tokens):
    """The program a cmd runs: its first token that is not `env`, an option, the
    argument of `-u`, or a NAME=value assignment. None when nothing is left."""
    after_u = False
    for tok in tokens:
        if after_u:
            after_u = False
        elif tok == "-u":
            after_u = True
        elif tok != "env" and not tok.startswith("-") and not ASSIGNMENT.match(tok):
            return tok
    return None


def entry_fault(name, entry):
    """Why a roster entry cannot be used at all, or None. probe and run keep their
    own messages for these; ready and the reviewer pick turn them into a skip."""
    if name == RESERVED:
        return f"the name {RESERVED} is reserved"
    if not isinstance(entry, dict):
        return "not a table"
    if "cmd" not in entry:
        return "no cmd"
    if not isinstance(entry["cmd"], str):
        return "cmd is not a string"
    try:
        tokens = shlex.split(entry["cmd"])
    except ValueError:
        return "cmd cannot be parsed"
    for bad in SHELL_OPS:
        if bad in tokens:
            return f"cmd contains shell operator '{bad}'"
    if any("{model}" in tok for tok in tokens):
        if not entry.get("model"):
            return "cmd uses {model} but declares no model"
        if not isinstance(entry["model"], str):
            return "model is not a string"
    if program_of(tokens) is None:
        return "cmd names no program"
    return None


def env_state(entry):
    """('ok' | 'invalid' | 'missing', the missing names) for an entry's requires_env.
    A variable counts as set only when it is present and not the empty string."""
    need = entry.get("requires_env")
    if need is None:
        return "ok", []
    if not isinstance(need, list) or not all(isinstance(n, str) for n in need):
        return "invalid", []
    missing = [n for n in need if not os.environ.get(n)]
    return ("missing", missing) if missing else ("ok", [])


def workers_table(data):
    workers = data.get("workers", {})
    if not isinstance(workers, dict):
        raise Fault(f"'workers' in {ROSTER} must be a table of [workers.<name>] entries")
    return workers


def reviewer_order(data, workers, quiet=False):
    """Candidate names in pick order: the `reviewers` list (or the older
    `spec_reviewer`), then every other worker in file order."""
    ranked = data.get("reviewers")
    spec_name = data.get("spec_reviewer")
    if ranked is not None:
        if (not isinstance(ranked, list)
                or not all(isinstance(n, str) for n in ranked)):
            raise Fault(f"reviewers in {ROSTER} must be a list of worker name strings, "
                        f"got: {ranked!r}")
        for n in ranked:
            if n not in workers:
                raise Fault(f"reviewers names '{n}', which is not in {ROSTER}")
    if ranked:
        if spec_name is not None and not quiet:
            print("worker.py: spec_reviewer ignored; reviewers is set", file=sys.stderr)
        names = list(dict.fromkeys(ranked))
    else:
        # Absent or empty reviewers: the old single-name key counts as a list of one.
        if spec_name is not None and not isinstance(spec_name, str):
            raise Fault(f"spec_reviewer in {ROSTER} must be a worker name string")
        if spec_name is not None and spec_name not in workers:
            raise Fault(f"spec_reviewer '{spec_name}' is not in {ROSTER}")
        names = [spec_name] if spec_name is not None else []
    for name in workers:
        if name not in names:
            names.append(name)
    return names


def skip_reason(name, entry, writer_family, thrifty, skip):
    """Why the pick passes over a candidate without probing it, or None."""
    if name in skip:
        return "excluded by the caller"
    fault = entry_fault(name, entry)
    if fault:
        return f"invalid entry ({fault})"
    if thrifty and not is_cheap(entry):
        return "thrifty mode, tier is not cheap"
    family = entry.get("family")
    # An empty family must never count as "a different family".
    if family is None or family == "":
        return "no family"
    if not isinstance(family, str):
        return "family is not a string"
    if family.lower() == writer_family.lower():
        return f"same family ({family})"
    state, missing = env_state(entry)
    if state == "invalid":
        return "requires_env is not a list of strings"
    if missing:
        return f"missing {','.join(missing)}"
    return None


def live_probe(name) -> bool:
    # A dead candidate (missing binary, probe timeout) makes probe_ok die(); for
    # a pick or a report that is a failed probe, not the end of the search. The
    # same holds for any error one entry can raise while its command is built.
    try:
        return probe_ok(name)
    except (Exception, SystemExit):
        return False


def pick_reviewer(data, writer_family, skip=(), probe=live_probe, quiet=False):
    """The first candidate from another family that answers its probe, or None.
    Raises Fault for a roster setting it cannot use. The one pick every caller shares."""
    workers = workers_table(data)
    names = reviewer_order(data, workers, quiet)
    thrifty = thrifty_state(data)
    for name in names:
        reason = skip_reason(name, workers[name], writer_family, thrifty, skip)
        if reason is None:
            if probe(name):
                return name
            reason = "probe failed"
        if not quiet:
            print(f"worker.py: skip {name}: {reason}", file=sys.stderr)
    return None


def allow_rule_present() -> bool:
    """True when a permissions.allow string naming this launcher exists in the user's
    Claude Code settings or the current repo's. A fact only: it says nothing about
    what a permission mode will do with the launch."""
    files = [Path.home() / ".claude" / "settings.json"]
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            root = Path(r.stdout.strip())
            files += [root / ".claude" / "settings.json", root / ".claude" / "settings.local.json"]
    except OSError:
        pass
    for f in files:
        try:
            allow = json.loads(f.read_text())["permissions"]["allow"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if isinstance(allow, list) and any(isinstance(s, str) and "worker.py" in s for s in allow):
            return True
    return False


def ready_line(name, entry):
    """One worker's report line, and whether its probe answered."""
    fault = entry_fault(name, entry)
    if fault:
        return f"{name}: invalid entry ({fault})", False
    family = entry.get("family")
    if family is None or family == "":
        shown = "none"
    else:
        shown = family if isinstance(family, str) else "invalid"
    installed = shutil.which(program_of(shlex.split(entry["cmd"]))) is not None
    state, missing = env_state(entry)
    for var in missing:
        print(f"worker.py: {name} needs {var}: export it from ~/.zshenv "
              "(a non-interactive shell does not read .zshrc)", file=sys.stderr)
    env = f"missing {','.join(missing)}" if missing else state
    if installed and state == "ok":
        probe = "ok" if live_probe(name) else "failed"
    else:
        probe = "skipped"
    line = f"{name}: family={shown} installed={'yes' if installed else 'no'} env={env} probe={probe}"
    return line, probe == "ok"


def ready(family):
    """Report every roster worker. Exits 0 whenever the roster parsed as TOML."""
    data = load_roster()
    # A fault in a top-level setting is reported with or without --family, and
    # never ends the report.
    settings_ok = True
    try:
        workers = workers_table(data)
    except Fault as e:
        print(f"worker.py: {e}", file=sys.stderr)
        workers, settings_ok = {}, False
    if settings_ok:
        try:
            reviewer_order(data, workers)
            thrifty_state(data)
        except Fault as e:
            print(f"worker.py: {e}", file=sys.stderr)
            settings_ok = False
    answered = {}
    for name, entry in workers.items():
        # One entry's fault must never end the report.
        try:
            line, answered[name] = ready_line(name, entry)
        except (Exception, SystemExit) as e:
            line, answered[name] = f"{name}: invalid entry ({e})", False
        print(line)
    print(f"launcher allow rule: {'present' if allow_rule_present() else 'absent'}")
    if family is not None:
        name = None
        if settings_ok:
            # Reuse the probe results gathered above; never probe a second time.
            name = pick_reviewer(data, family, probe=lambda n: answered.get(n, False), quiet=True)
        print(f"reviewer for {family}: {name or 'none'}")
    sys.exit(0)


NO_REVIEWER = "reviewer: none from another family, using a subagent"
START_USAGE = ("usage: worker.py start (--family <family> [--label <text>] | --builder <worker>) "
               "[--intent <path>] [--small]")


def no_reviewer_message(data, writer_family) -> str:
    """What reviewer says when no candidate passed. Call only after a pick returned None."""
    if thrifty_state(data):
        return f"thrifty mode: no cheap reviewer outside family '{writer_family}' passed its probe"
    return f"no reviewer outside family '{writer_family}' passed its probe"


def start_reviewer(builder_family) -> str:
    """The reviewer part of the start line. Every failure of the pick that reviewer
    runs becomes the subagent fallback: a fault here is never an error for start."""
    data, problem = read_roster()
    if data is None:
        if not ROSTER.exists():
            problem = f"no roster at {ROSTER}: run the workers skill to create one"
        print(f"worker.py: {problem}", file=sys.stderr)
        return NO_REVIEWER
    try:
        name = pick_reviewer(data, builder_family)
        if name is None:
            print(f"worker.py: {no_reviewer_message(data, builder_family)}", file=sys.stderr)
            return NO_REVIEWER
    except Fault as e:
        print(f"worker.py: {e}", file=sys.stderr)
        return NO_REVIEWER
    return f"reviewer: {name} ({data['workers'][name]['family']})"


def start_plan(intent, small) -> str:
    """The plan part of the start line. An accepted intent wins over --small."""
    if intent is not None:
        path = Path(intent)
        try:
            with open(path, encoding="utf-8") as f:
                head = [f.readline() for _ in range(5)]
        except (OSError, UnicodeDecodeError) as e:
            print(f"worker.py: cannot read intent file {path}: {e}", file=sys.stderr)
            head = []
        if any(line.startswith("Status: accepted") for line in head):
            digits = re.match(r"\d+", path.name)
            number = digits.group(0) if digits else path.name.removesuffix(".md")
            return f"plan: already approved (intent {number})"
    if small:
        return "plan: skipped, small change"
    return "plan: I will show it and wait for you"


def start(args):
    """Print the one line that opens a run: who builds, who reviews, and the plan stop."""
    opts, small, rest = {}, False, list(args)
    while rest:
        flag = rest.pop(0)
        if flag == "--small" and not small:
            small = True
        elif flag in ("--family", "--label", "--builder", "--intent") and flag not in opts \
                and rest and not rest[0].startswith("--"):
            opts[flag] = rest.pop(0)
        else:
            die(2, START_USAGE)
    family, label, builder = opts.get("--family"), opts.get("--label"), opts.get("--builder")
    if (family is None) == (builder is None) or (label is not None and family is None):
        die(2, START_USAGE)
    if builder is not None:
        # A person named this worker, so the run must not go on without it.
        entry = load_roster().get("workers")
        entry = entry.get(builder) if isinstance(entry, dict) else None
        if entry is None:
            die(2, f"no worker '{builder}' in {ROSTER}")
        family = entry.get("family") if isinstance(entry, dict) else None
        if not isinstance(family, str) or not family:
            die(2, f"worker '{builder}' in {ROSTER} needs a family that is a non-empty string")
        who = f"builder: {builder} ({family})"
    else:
        who = f"builder: {label or 'this session'} ({family})"
    print(" · ".join([who, start_reviewer(family), start_plan(opts.get("--intent"), small)]))
    sys.exit(0)


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
    for bad in SHELL_OPS:
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


def run(argv, cwd, timeout, capture, keep_on_timeout=False):
    """Run a worker. On timeout, kill its process group and die with 124 — or, with
    keep_on_timeout, return code 124 and whatever it printed before the kill."""
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
        out, err = p.communicate()
        msg = f"worker timed out after {timeout}s (process group killed)"
        if not keep_on_timeout:
            die(124, msg)
        print(f"worker.py: {msg}", file=sys.stderr)
        return SimpleNamespace(returncode=124, stdout=out or "", stderr=err or "")
    return SimpleNamespace(returncode=p.returncode, stdout=out or "", stderr=err or "")


SNAPSHOT = Path(__file__).resolve().parents[2] / "to-issues" / "scripts" / "worktree_snapshot.py"
VERDICT_LINE = re.compile(r"^[\s>*`-]*((?:VERDICT|COVERAGE)\b.*?)[`\s]*$")


def review(name, cwd, brief_file, timeout):
    """One review round: snapshot, run, snapshot, compare, then the verdict lines.

    The snapshot covers <dir>'s tracked and untracked files plus <dir>/.scratch,
    which git ignores but where to-issues keeps its drafts. A reviewer that
    changed anything has no verdict worth acting on (exit 4)."""
    if not Path(cwd).is_dir():
        die(2, f"assigned directory does not exist: {cwd}")
    cwd = str(Path(cwd).resolve())
    try:
        brief = Path(brief_file).read_text()
    except OSError as e:
        die(2, f"cannot read brief file: {e}")
    argv = build_argv(resolve(name), name, cwd, brief)
    work = Path(tempfile.mkdtemp(prefix="magito-review-"))

    def snapshot(label):
        path = work / f"{label}.json"
        r = subprocess.run([sys.executable, str(SNAPSHOT), "capture", cwd, f"{cwd}/.scratch", str(path)],
                           capture_output=True, text=True)
        if r.returncode:
            die(2, f"snapshot failed: {r.stderr.strip()}")
        return path

    before = snapshot("before")
    # A timeout still gets the file check: a reviewer that edited files and then
    # hung must exit 4, not 124. Its partial output is saved like any other.
    r = run(argv, cwd, timeout, capture=True, keep_on_timeout=True)
    output = work / "review.txt"
    output.write_text(r.stdout + r.stderr)
    print(f"review output: {output}", file=sys.stderr)
    after = snapshot("after")
    cmp = subprocess.run([sys.executable, str(SNAPSHOT), "compare", str(before), str(after)],
                         capture_output=True, text=True)
    if cmp.returncode:
        print(cmp.stdout.strip(), file=sys.stderr)
        die(4, "the reviewer changed files — discard its verdict, revert, and review again")
    # Read stdout only. `codex exec` prints its final answer there and everything
    # else on stderr: the echoed brief and the files it read, which can quote
    # verdict lines. Still drop an echo in case a CLI prints the brief on stdout,
    # and keep each verdict line once.
    answer = r.stdout.replace(brief.strip(), "", 1)
    verdicts = []
    for line in answer.splitlines():
        m = VERDICT_LINE.match(line)
        if m and m.group(1) not in verdicts:
            verdicts.append(m.group(1))
    if r.returncode:
        sys.exit(r.returncode)
    if not verdicts:
        die(5, f"no VERDICT or COVERAGE line in the reviewer's output ({output})")
    print("\n".join(verdicts))
    sys.exit(0)


def main():
    args = sys.argv[1:]
    if "--skip" in args and args[:1] != ["reviewer"]:
        die(2, "--skip is an option of `worker.py reviewer` only")
    if len(args) >= 2 and args[0] == "probe":
        name = args[1]
        if probe_ok(name, echo_failure=True):
            print(f"PROBE OK: {name}")
            sys.exit(0)
        die(3, f"probe failed for '{name}' (no VERDICT-OK)")
    elif len(args) >= 2 and args[0] == "reviewer":
        writer_family, rest, skip = args[1], args[2:], []
        while rest:
            # A name is required after each --skip, and another option is not a name.
            if rest[0] != "--skip" or len(rest) < 2 or rest[1].startswith("--"):
                die(2, "usage: worker.py reviewer <writer-family> [--skip <worker>]...")
            skip.append(rest[1])
            rest = rest[2:]
        data = load_roster()
        try:
            name = pick_reviewer(data, writer_family, skip)
        except Fault as e:
            die(2, str(e))
        if name:
            print(name)
            sys.exit(0)
        die(3, no_reviewer_message(data, writer_family))
    elif args[:1] == ["ready"]:
        if args[1:] and (args[1] != "--family" or len(args) != 3):
            die(2, "usage: worker.py ready [--family <family>]")
        ready(args[2] if args[1:] else None)
    elif args[:1] == ["start"]:
        start(args[1:])
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
    elif len(args) >= 4 and args[0] == "review":
        name, cwd, brief_file = args[1], args[2], args[3]
        try:
            timeout = int(args[4]) if len(args) > 4 else 600
        except ValueError:
            die(2, f"timeout must be an integer number of seconds, got: {args[4]}")
        review(name, cwd, brief_file, timeout)
    else:
        die(2, "usage: worker.py probe <worker> | "
               "worker.py reviewer <writer-family> [--skip <worker>]... | "
               "worker.py ready [--family <family>] | "
               "worker.py start (--family <family> [--label <text>] | --builder <worker>) "
               "[--intent <path>] [--small] | "
               "worker.py thrifty | worker.py workers | "
               "worker.py run <worker> <dir> <brief-file> [timeout] | "
               "worker.py review <worker> <dir> <brief-file> [timeout]")


if __name__ == "__main__":
    main()
