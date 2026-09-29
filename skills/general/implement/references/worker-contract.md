# Worker contract

The delegable build-slice of an issue: what a driver hands to an executor — a Claude
subagent or a headless shell CLI — and what comes back. The `implement` single-issue path
(SKILL.md step 4) and the parallel fan-out (`references/parallel.md` step 3) both delegate
against this contract. The worker implements and stages; the driver owns branch, commit,
review, merge, and PR.

## The brief

A brief must be self-contained: workers cannot reach the tracker, load skills, or ask
the user. The default rule is **paste, do not reference** — but it has one qualified
exception. The contract essentials below are always pasted in full; in-worktree
standing docs are the only thing that may be named by exact repo-relative path.

Every brief carries:

1. **The assigned directory** — a worktree path (the parallel fan-out) or the repo tree on its
   feature branch (implement). The worker never touches files outside it.
2. **The full issue spec, pasted in** — body, acceptance criteria, any repo
   conventions the work needs. Never a bare issue number or URL.
3. **The verification floor, in full** (workers cannot load `verifying`):
   - Red-green where the behavior is specifiable (watch the test fail first);
     characterization / eval-threshold / smoke where it is not.
   - Invariant + schema checks at every data boundary touched: columns/dtypes/
     nullability, no NaN/inf where forbidden, values in range, row counts / key
     uniqueness, no train/test leakage.
   - Seed all randomness; float asserts with tolerance, never equality.
4. **The staging rule**: stage only the files you changed, listed explicitly —
   `git -C <dir> add <file1> <file2> ...`; never `git add -A` or `git add .`.
5. **The report protocol**: `DONE` with the list of staged files, `DONE (no-op)` if
   the change is already in place, or `BLOCKED: <reason>` when the spec is ambiguous
   and the codebase does not disambiguate — never guess.
6. **The prohibitions**: no commit, no merge, no push, no worktree create/remove,
   nothing outside the assigned directory.

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

This does not change how work is judged.

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
python3 <skills>/implement/scripts/worker.py probe <worker>
python3 <skills>/implement/scripts/worker.py run <worker> <dir> <brief-file> [timeout]
```

(`<skills>` is your tool's installed skills directory — `~/.claude/skills` for Claude
Code, `~/.agents/skills` for most others.)

Each worker declares `cmd` — an **argv template**, not a shell line: it is split
into arguments and placeholders are substituted per argument, so it cannot contain
`&&`, `|`, `;`, or a leading `cd` (the launcher sets the working directory itself,
and rejects such entries loudly). `{cwd}` is the assigned directory, `{brief}`
receives the brief file's content as one argument. An optional `model` field
follows magi's bench convention: substituted where `cmd` contains `{model}`,
documentation otherwise. An optional `family` field is a free lowercase string that
names the model family (`openai`, `google`, `anthropic`, ...). Two workers are the
same family when their `family` strings are equal after lowercasing. A top-level
`spec_reviewer` key names the worker tried first when the pipeline asks for a spec
reviewer from a different family. It must sit above the first `[workers.*]` table:
TOML reads any key written below a table header as part of that table, so a
`spec_reviewer` placed there silently becomes a field of that worker.

```toml
# ~/.magito/workers.toml — machine-local, never synced
spec_reviewer = "codex"   # top-level: above every [workers.*] table

[workers.codex]
cmd = "codex exec --sandbox workspace-write --ephemeral -C {cwd} {brief}"
family = "openai"

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

First time a worker is named and `~/.magito/workers.toml` does not exist: create it.
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

Before dispatching to a named worker, probe it once: `python3 <skills>/implement/scripts/worker.py probe <worker>`
sends "Reply with exactly: VERDICT-OK" and checks the token comes back. The
launcher strips approval-bypass flags from the probe itself — a ping needs no
permissions, and permission tooling rightly balks at bypass flags on a command that
does not need them.

- **Dead at probe** (missing binary, auth failure, quota, timeout): stop and ask the
  user — fall back to `haiku-executor`, or abort. Never substitute silently: the user
  named that worker to move spend off the Claude subscription, and a silent fallback
  moves it back.
- **Dies mid-run** (timeout, nonzero exit, garbage output): that issue reports
  `BLOCKED` like any executor failure. No automatic retry on another worker or model.

Picking a spec reviewer is the one exception to "stop and ask." The user named no single
worker for it, so there is no spend choice to override. `python3
<skills>/implement/scripts/worker.py reviewer <writer-family>` tries `spec_reviewer`
first, then every other worker in file order. It skips any worker with no `family`, a
family equal to the writer's, or a failed probe, and says so on stderr. It prints the
name of the first worker that passes, alone on stdout. It exits 3 when none passes.

## Nested-CLI gotchas (verified July 2026)

- **Nested claude**: spawn with `env -u CLAUDECODE claude -p ...` — Claude Code
  refuses to start inside itself otherwise.
- **Claude billing**: a subprocess `claude -p` bills API pay-as-you-go when
  `ANTHROPIC_API_KEY` is set in its environment, and the logged-in subscription
  otherwise. Do not leak the key into a worker's env unless API billing is intended.
- **codex as driver**: its `workspace-write` sandbox blocks child processes' network
  by default — a spawned worker cannot reach its API without
  `[sandbox_workspace_write] network_access = true`.
- **omp workers**: always `--no-session --no-skills --max-time <s>` — omp otherwise
  auto-discovers skills and instruction files, and the brief is the contract, not
  what the worker finds. Give `--model` the full `provider/model` path; a bare fuzzy
  name can resolve to a different provider and fail on missing auth.
- **Timeouts are the driver's job**: most CLIs enforce no print-mode timeout of their
  own. Pair the worker-side cap (omp `--max-time`) with a driver-side timeout on the
  shell call.
- **Claude Code permission modes**: run fan-out sessions in default (prompting)
  mode — the first `python3 .../scripts/worker.py` launch prompts once, and "do not ask again this
  session" covers the rest of the batch. Auto mode may deny the launch outright; if
  you are then offered a fallback to `haiku-executor`, present it as a billing
  decision, never a convenience. The launcher's single stable prefix
  (`python3 .../scripts/worker.py`) is also what makes a tight allow rule possible
  if the user ever wants zero prompts.
- **Env vars and non-interactive shells**: workers inherit the driver's environment,
  and a driver's shell tool runs non-interactive shells — exports living only in
  `.zshrc` (read by interactive shells alone) may never arrive, depending on how the
  driver itself was launched. This hits any env prerequisite: BYOK keys like
  `OPENROUTER_API_KEY`, gemini's cloud-project variables, etc. Diagnose:
  `zsh -ic 'echo $VAR'` shows it, `zsh -c 'echo $VAR'` does not. Fix at the root, per
  machine: export from `~/.zshenv` (read by every zsh) or use the tool's native auth
  store (`omp /login`, codex/claude/gemini logins). Never persist `zsh -ic` wrappers
  into `cmd` templates — that couples the roster to shell-init quirks.
