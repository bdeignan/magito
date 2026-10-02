# Worker contract

The delegable build-slice of a ticket: what a driver hands to an executor — a Claude
subagent or a headless shell CLI — and what comes back. The build step of `implement`
([pipeline.md](./pipeline.md) step 3) and a batch run ([parallel.md](./parallel.md)) both
delegate against this contract. The worker implements and stages; the driver owns branch, commit,
review, merge, and PR.

## The brief

A brief must be self-contained: workers cannot reach the tracker, load skills, or ask
the user. The default rule is **paste, do not reference** — but it has one qualified
exception. The contract essentials below are always pasted in full; in-worktree
standing docs are the only thing that may be named by exact repo-relative path.

Every brief carries:

1. **The assigned directory** — always the ticket's worktree path. Every build happens in
   a worktree. The worker never touches files outside it.
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
python3 <skills>/implement/scripts/worker.py ready [--family <family>]
python3 <skills>/implement/scripts/worker.py start (--family <family> [--label <text>] | --builder <worker>) [--intent <path>] [--small]
python3 <skills>/implement/scripts/worker.py record <worktree> <builder-family> <reviewer|subagent>
```

`record` writes the review record for the branch in `<worktree>` as `<sha> reviewed by <name>`,
into the marker that `gitflow.sh worktree add` created; it never creates a marker. With the
word `subagent` it runs the reviewer pick again first, and exit 6 means a roster worker
answers its probe: review with the worker it names, not with a subagent.

`start` prints the one line that opens a run, for example
`builder: this session (anthropic) · reviewer: codex (openai) · plan: already approved (intent 0005)`.
The builder part names this session, a labelled builder such as a subagent, or the roster
worker given with `--builder`. The reviewer part is the same pick `reviewer` makes for the
builder's family. Whenever that pick fails, for a missing roster as for a failed probe, the
part reads `reviewer: none from another family, using a subagent`, the reason goes to stderr,
and the command still exits 0. The plan part says whether the run stops for plan approval: no
stop for an accepted intent given with `--intent`, none for `--small`, and a stop otherwise.

`ready` reports every roster worker on one line each: its family, whether its program is
installed, whether its required variables are set, and whether its probe answers. A last line
says whether an allow rule for this launcher exists in the Claude Code settings. With
`--family`, it also names the worker that `reviewer` would pick for that family. It exits 0
whenever the roster parses, whatever is wrong with one entry.

(`<skills>` is your tool's installed skills directory — `~/.claude/skills` for Claude
Code, `~/.agents/skills` for most others.)

`MAGITO_WORKERS_FILE` can select a separate roster for an isolated eval. When unset, the
launcher uses `~/.magito/workers.toml`. The eval roster follows the same format.

Each worker declares `cmd` — an **argv template**, not a shell line: it is split
into arguments and placeholders are substituted per argument, so it cannot contain
`&&`, `|`, `;`, or a leading `cd` (the launcher sets the working directory itself,
and rejects such entries loudly). `{cwd}` is the assigned directory, `{brief}`
receives the brief file's content as one argument. An optional `model` field
follows magi's bench convention: substituted where `cmd` contains `{model}`,
documentation otherwise. An optional `family` field is a free lowercase string that
names the model family (`openai`, `google`, `anthropic`, ...). Two workers are the
same family when their `family` strings are equal after lowercasing. An optional `tier` field
labels how strong the pinned model is; a worker with no `tier` counts as
`strong`. An optional `requires_env` field is a list of environment variable names the tool
needs, such as `requires_env = ["GOOGLE_CLOUD_PROJECT"]`. When one is unset or empty, `ready`
names it and the reviewer pick passes over that worker without probing it. A worker cannot
be named `subagent`: the review record keeps that word for a fresh-context subagent. A
worker name is one plain word of letters, digits, `.`, `_`, or `-`. No command lists,
probes, launches, picks, or records a worker with any other name. A top-level `reviewers` key is a list of worker names, ranked: the
pipeline tries them in that order when it asks for a spec reviewer from a different family,
then every other worker in file order. Each candidate must pass the family rule and its
probe, so when the first reviewer is out of quota the next one takes over. The older
`spec_reviewer = "name"` key still works and counts as a list of one when `reviewers` is
absent or empty. When both are set, `reviewers` wins and stderr says so. A `reviewers`
value that is not a list of strings, or that names a worker the roster lacks, exits 2.
Top-level keys must sit above the first `[workers.*]` table: TOML reads any key written
below a table header as part of that table, so a `reviewers` placed there silently becomes
a field of that worker. [`workers.toml.example`](./workers.toml.example) is a ready roster
with one commented entry per popular tool, each pinned to that tool's strongest model, plus
one cheap entry per tool for thrifty mode.

**Thrifty mode** restricts every step to cheap models. It is on when the environment
variable `MAGITO_THRIFTY` is `1` (one session), or when the roster has the top-level key
`thrifty = true` (the whole machine). `MAGITO_THRIFTY=0` turns it off for a session even when
the roster says `true`. A `thrifty` value that is not `true` or `false` exits 2. While it is
on, `worker.py reviewer` considers only workers whose `tier` is `cheap`, and exits 3 with
`thrifty mode: no cheap reviewer outside family '<family>' passed its probe` when none
passes. `worker.py thrifty` prints `on` or `off`. `worker.py workers` prints the worker
names, one per line in file order, and only the cheap ones while thrifty mode is on. It does
not probe, and an empty result exits 0 with no output. Skills call these two commands
instead of reading the environment and the roster themselves. magito does not track spend.

```toml
# ~/.magito/workers.toml — machine-local, never synced
reviewers = ["codex", "omp"]   # top-level: above every [workers.*] table

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

The `workers` skill creates and checks the roster. It reports which workers on the machine
are ready, and when `~/.magito/workers.toml` does not exist it offers to copy
[`workers.toml.example`](./workers.toml.example) there. Never write that file from here, and
never overwrite an existing one: it is the user's file. Expect the driver's permission system
to ask once before the file is written: the entries are templates that launch agents with
approval prompts bypassed, so a flag on persisting them is correct behavior, not an error.

Every entry in the example is commented out, and the user turns on the ones for the tools
they have. Each comment above an entry records the date its model id was checked, or says
`unverified: check with <command>`. Treat an unverified id as a guess until that command
confirms it. A newer model elsewhere does not establish availability in a given tool. The
Cursor entries need `agent login` first, and `agent models` is the authority for the exact
ids on the installed CLI and account. The Cursor and omp entries take their family from the
pinned model, not from the tool. A different model means a separate entry with its own name.

**agy is never a worker candidate.** It earns its magi seat behind a pty wrapper, but a
worker needs what it lacks: reliable non-TTY output (open stdout-drop bug,
google-antigravity/antigravity-cli#76), structured completion, and session isolation — its
`-c` resumes globally and cross-contaminates concurrent workers.

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

Picking a reviewer is the one exception to "stop and ask." The user named no single
worker for it, so there is no spend choice to override. For a run, `worker.py start` makes
this pick and prints it in the start line, and `worker.py record` runs it again before a
subagent review can be recorded. `python3
<skills>/implement/scripts/worker.py reviewer <writer-family>` tries the workers named in
`reviewers`, in that order, then every other worker in file order. When `reviewers` is
absent or empty, `spec_reviewer` counts as a list of one. It skips any worker with no `family`, a
family equal to the writer's, a missing required variable, an entry it cannot use, or a failed
probe, and says so on stderr. `--skip <worker>`, which can be repeated, passes over a named
candidate: use it to reach another reviewer after one failed in the middle of a review. It prints the
name of the first worker that passes, alone on stdout. It exits 3 when none passes.

### Reviewer replies in a run

The review step in [pipeline.md](./pipeline.md) uses the reviewer that the start line names:
the same pick as `worker.py reviewer <builder-family>`, made by `worker.py start`. The brief
carries the ticket body and `git diff <base>...HEAD`, and tells the reviewer to change no
files and to answer with `VERDICT PASS` or one or more `VERDICT FIX: <finding>` lines.
Reading a reply: any `VERDICT FIX` line means FIX, even beside a `VERDICT PASS`. A reply with
neither token, or a nonzero exit, counts as a failed review, so run it again, as
pipeline.md step 6 says. `worker.py review` verifies the no-write rule with
`worktree_snapshot.py`; never trust the reviewer's word for it.

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
