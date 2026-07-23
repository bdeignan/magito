# Worker contract

The delegable build-slice of an issue: what a driver hands to an executor — a Claude
subagent or a headless shell CLI — and what comes back. `implement-issue` (step 4)
and `dispatch` (step 3) both delegate against this contract. The worker implements
and stages; the driver owns branch, commit, review, merge, and PR.

## The brief

A brief must be self-contained: workers cannot reach the tracker, load skills, or ask
the user. The default rule is **paste, don't reference** — but it has one qualified
exception. The contract essentials below are always pasted in full; in-worktree
standing docs are the only thing that may be named by exact repo-relative path.

Every brief carries:

1. **The assigned directory** — a worktree path (dispatch) or the repo tree on its
   feature branch (implement-issue). The worker never touches files outside it.
2. **The full issue spec, pasted in** — body, acceptance criteria, any repo
   conventions the work needs. Never a bare issue number or URL.
3. **The verification floor, in full** (workers can't load `verifying`):
   - Red-green where the behavior is specifiable (watch the test fail first);
     characterization / eval-threshold / smoke where it isn't.
   - Invariant + schema checks at every data boundary touched: columns/dtypes/
     nullability, no NaN/inf where forbidden, values in range, row counts / key
     uniqueness, no train/test leakage.
   - Seed all randomness; float asserts with tolerance, never equality.
4. **The staging rule**: stage only the files you changed, listed explicitly —
   `git -C <dir> add <file1> <file2> ...`; never `git add -A` or `git add .`.
5. **The report protocol**: `DONE` with the list of staged files, `DONE (no-op)` if
   the change is already in place, or `BLOCKED: <reason>` when the spec is ambiguous
   and the codebase doesn't disambiguate — never guess.
6. **The prohibitions**: no commit, no merge, no push, no worktree create/remove,
   no session-ledger access (`clock in`/`out`/`checkpoint` — the driver owns the
   ledger), nothing outside the assigned directory.

### Referenceable in-worktree docs

Standing project docs that already live in the repo — conventions, gotchas, the area's
flow, `docs/agents/GLOSSARY.md`, and similar — may be named by exact repo-relative
path instead of pasted in full, because `docs/agents/` (and any other tracked doc) is
physically present inside the worker's assigned directory.

Determinism guard: the **driver** resolves `docs/agents/INDEX.md`'s routing and picks
the exact file(s) that apply. The brief names that exact path with a one-line reason,
for example: "read `docs/agents/conventions.md` for the async-job pattern before
touching the scheduler." The brief must **never** tell the worker to "consult the
index" or "read what you need" — that would make the worker's context non-deterministic
and unreviewable.

Reachability basis: tracked files exist in every worktree by construction. A flag like
`--no-skills` blocks skill auto-discovery, not plain file reads, so the worker can open
a named path just fine.

This does not change how work is judged. Review still examines the staged diff
(`git -C <dir> diff --cached`), not the worker's claims about what it read.

The report is not the result. Judge a worker by `git -C <dir> diff --cached` — review
examines the staged diff regardless of what the worker claimed.

Write the brief to a file and hand the path to the launcher — it passes the content
to the worker as a single argument, so long briefs survive without shell-quoting.

## Executors

**Claude subagent** (Claude Code drivers only): `haiku-executor`, the default. Zero
config; bills the Claude subscription.

**Shell workers** (any driver): headless CLI commands resolved by name from
`~/.magito/workers.toml` — machine-local, never synced. Always probe and launch
through the launcher script, never a hand-built command line:

```bash
python3 <skills>/implement-issue/scripts/worker.py probe <worker>
python3 <skills>/implement-issue/scripts/worker.py run <worker> <dir> <brief-file> [timeout]
```

(`<skills>` is your tool's installed skills directory — `~/.claude/skills` for Claude
Code, `~/.agents/skills` for most others.)

Each worker declares `cmd` — an **argv template**, not a shell line: it is split
into arguments and placeholders are substituted per argument, so it cannot contain
`&&`, `|`, `;`, or a leading `cd` (the launcher sets the working directory itself,
and rejects such entries loudly). `{cwd}` is the assigned directory, `{brief}`
receives the brief file's content as one argument. An optional `model` field
follows magi's bench convention: substituted where `cmd` contains `{model}`,
documentation otherwise.

```toml
# ~/.magito/workers.toml — machine-local, never synced
[workers.omp]
cmd = "omp -p --no-session --no-skills --approval-mode yolo --max-time 600 --cwd {cwd} {brief}"
# model comes from omp's own modelRoles (deprecation-proofing lives inside each tool)

[workers.omp-slow]
cmd = "omp -p --no-session --no-skills --approval-mode yolo --max-time 900 --cwd {cwd} --model {model} {brief}"
model = "openrouter/deepseek/deepseek-v4-pro"

[workers.gemini]
cmd = "gemini --approval-mode yolo -p {brief} --model {model}"
model = "gemini-3.5-flash"
```

Worker names are your role tiers: `omp` vs `omp-slow` vs `gemini-pro` are just
entries pointing at different models, so "cheap by default, strong on request" is a
naming convention, not a mechanism. Which model backs a worker is the durable
choice; the volatile id lives only in this machine-local file (one line to update
on a sunset), or better, in each tool's own alias layer (omp modelRoles, claude
aliases, codex profiles). CLIs with no working-directory flag (gemini, claude) need
no `{cwd}` at all — the launcher sets the working directory itself.

## Bootstrap

First time a worker is named and `~/.magito/workers.toml` doesn't exist: create it.
Probe the installed candidates — omp, codex, claude, gemini; **never agy**. It earns
its magi seat behind a pty wrapper, but a worker needs what it lacks: reliable
non-TTY output (open stdout-drop bug, google-antigravity/antigravity-cli#76),
structured completion, and session isolation — its `-c` resumes globally and
cross-contaminates concurrent workers. Write live
candidates as entries, comment out the dead, tell the user what you wrote, proceed.
Never overwrite an existing `workers.toml` — it is the user's file. Expect the
driver's permission system to ask once before the file is written: the entries are
templates that launch agents with approval prompts bypassed, so a flag on persisting
them is correct behavior, not an error.

## Probe and fallback

Before dispatching to a named worker, probe it once: `worker.sh probe <worker>`
sends "Reply with exactly: VERDICT-OK" and checks the token comes back. The
launcher strips approval-bypass flags from the probe itself — a ping needs no
permissions, and permission tooling rightly balks at bypass flags on a command that
doesn't need them.

- **Dead at probe** (missing binary, auth failure, quota, timeout): stop and ask the
  user — fall back to `haiku-executor`, or abort. Never substitute silently: the user
  named that worker to move spend off the Claude subscription, and a silent fallback
  moves it back.
- **Dies mid-run** (timeout, nonzero exit, garbage output): that issue reports
  `BLOCKED` like any executor failure. No automatic retry on another worker or model.

## Nested-CLI gotchas (verified July 2026)

- **Nested claude**: spawn with `env -u CLAUDECODE claude -p ...` — Claude Code
  refuses to start inside itself otherwise.
- **Claude billing**: a subprocess `claude -p` bills API pay-as-you-go when
  `ANTHROPIC_API_KEY` is set in its environment, and the logged-in subscription
  otherwise. Don't leak the key into a worker's env unless API billing is intended.
- **codex as driver**: its `workspace-write` sandbox blocks child processes' network
  by default — a spawned worker can't reach its API without
  `[sandbox_workspace_write] network_access = true`.
- **omp workers**: always `--no-session --no-skills --max-time <s>` — omp otherwise
  auto-discovers skills and instruction files, and the brief is the contract, not
  what the worker finds. Give `--model` the full `provider/model` path; a bare fuzzy
  name can resolve to a different provider and fail on missing auth.
- **Timeouts are the driver's job**: most CLIs enforce no print-mode timeout of their
  own. Pair the worker-side cap (omp `--max-time`) with a driver-side timeout on the
  shell call.
- **Claude Code permission modes**: run dispatch sessions in default (prompting)
  mode — the first `worker.sh` launch prompts once, and "don't ask again this
  session" covers the rest of the batch. Auto mode may deny the launch outright; if
  you're then offered a fallback to `haiku-executor`, present it as a billing
  decision, never a convenience. The launcher's single stable prefix
  (`python3 .../scripts/worker.py`) is also what makes a tight allow rule possible
  if the user ever wants zero prompts.
- **Session ledger is off-limits to workers**: because workers inherit the driver's
  environment, a worker whose instruction file carries magito's "clock out when the
  session wraps" convention (omp reads `~/.omp/agent/AGENTS.md`, symlinked to the shared
  system instructions) could otherwise close the *driver's* own session with its narrow
  subtask summary — this actually happened, see #94. The launcher backstops it: `worker.py`
  runs every worker with `MAGITO_WORKER=1` set and `CLAUDE_CODE_SESSION_ID` scrubbed, so
  `~/.magito/bin/clock` refuses any ledger access from inside a worker. Don't strip either
  from the launcher's worker env; the prohibition above is the prose floor for workers that
  never reach the launcher.
- **Env vars and non-interactive shells**: workers inherit the driver's environment,
  and a driver's shell tool runs non-interactive shells — exports living only in
  `.zshrc` (read by interactive shells alone) may never arrive, depending on how the
  driver itself was launched. This hits any env prerequisite: BYOK keys like
  `OPENROUTER_API_KEY`, gemini's cloud-project variables, etc. Diagnose:
  `zsh -ic 'echo $VAR'` shows it, `zsh -c 'echo $VAR'` doesn't. Fix at the root, per
  machine: export from `~/.zshenv` (read by every zsh) or use the tool's native auth
  store (`omp /login`, codex/claude/gemini logins). Never persist `zsh -ic` wrappers
  into `cmd` templates — that couples the roster to shell-init quirks.
