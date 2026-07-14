# Worker contract

The delegable build-slice of an issue: what a driver hands to an executor — a Claude
subagent or a headless shell CLI — and what comes back. `implement-issue` (step 4)
and `dispatch` (step 3) both delegate against this contract. The worker implements
and stages; the driver owns branch, commit, review, merge, and PR.

## The brief

A brief must be self-contained: workers cannot reach the tracker, load skills, or ask
the user. Paste, don't reference. Every brief carries:

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
   nothing outside the assigned directory.

The report is not the result. Judge a worker by `git -C <dir> diff --cached` — review
examines the staged diff regardless of what the worker claimed.

## Executors

**Claude subagent** (Claude Code drivers only): `haiku-executor`, the default. Zero
config; bills the Claude subscription.

**Shell workers** (any driver): headless CLI commands resolved by name from
`~/.magito/workers.toml` — machine-local, gitignored, never synced. Each worker
declares `cmd`, a template with `{cwd}` (assigned directory) and `{brief}`
placeholders. An optional `model` field follows magi's bench convention: substituted
where `cmd` contains `{model}`, documentation otherwise.

```toml
# ~/.magito/workers.toml — machine-local, never synced
[workers.omp]
cmd = "omp -p --no-session --no-skills --approval-mode yolo --max-time 600 --cwd {cwd} {brief}"
# model comes from omp's own modelRoles (deprecation-proofing lives inside each tool)

[workers.omp-slow]
cmd = "omp -p --no-session --no-skills --approval-mode yolo --max-time 900 --cwd {cwd} --model {model} {brief}"
model = "openrouter/deepseek/deepseek-v4-pro"
```

Which model backs a worker is the durable choice; volatile flag syntax stays in
`cmd`. Prefer each tool's own alias layer (omp modelRoles, claude aliases, codex
profiles) so a model sunset is a one-line fix outside this repo.

## Bootstrap

First time a worker is named and `~/.magito/workers.toml` doesn't exist: create it.
Probe the installed candidates — omp, codex, claude, gemini; **never agy** (open
non-TTY stdout-drop bug, google-antigravity/antigravity-cli#76; no structured output;
its `-c` resumes globally and cross-contaminates concurrent workers). Write live
candidates as entries, comment out the dead, tell the user what you wrote, proceed.
Never overwrite an existing `workers.toml` — it is the user's file.

## Probe and fallback

Before dispatching to a named worker, ping it once: send "Reply with exactly:
VERDICT-OK" through its `cmd` and confirm the token on stdout.

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
