# Roster setup

How to create and fix the roster in `~/.magito/workers.toml`. A build or a review does not
need this file: the `workers` skill reads it when a machine has no roster or a worker entry
fails. The roster format and the rules a build follows are in the
[worker contract](../../implement/references/worker-contract.md).
`<skills>` is the folder that holds this skill's own folder: the parent of the directory its `SKILL.md` is in.

## Contents

- Bootstrap
- Probing an entry
- Nested-CLI gotchas
- History (verified on 2026-07)

## Bootstrap

The `workers` skill creates and checks the roster. It reports which workers on the machine
are ready, and when `~/.magito/workers.toml` does not exist it offers to copy
[`workers.toml.example`](../../implement/references/workers.toml.example) there. Never write that file from here, and
never overwrite an existing one: it is the user's file. Expect the driver's permission system
to ask once before the file is written: the entries are templates that launch agents with
approval prompts bypassed, so a flag on persisting them is correct behavior, not an error.

Every entry in the example is commented out, and the user turns on the ones for the tools
they have. Each comment above an entry says `unverified: check with <command>` when its model id
is a guess. The dates of the checks are in the History block at the end of the example. Treat an unverified id as a guess until that command
confirms it. A newer model elsewhere does not establish availability in a given tool. The
Cursor entries need `agent login` first, and `agent models` is the authority for the exact
ids on the installed CLI and account. The Cursor and omp entries take their family from the
pinned model, not from the tool. A different model means a separate entry with its own name.

**agy is never a worker candidate.** It earns its magi seat behind a pty wrapper, but a
worker needs what it lacks: reliable non-TTY output (open stdout-drop bug,
google-antigravity/antigravity-cli#76), structured completion, and session isolation — its
`-c` resumes globally and cross-contaminates concurrent workers.

## Probing an entry

`python3 <skills>/implement/scripts/worker.py probe <worker>` sends "Reply with exactly:
VERDICT-OK" and checks the token comes back. The launcher strips approval-bypass flags from
the probe itself: a ping needs no permissions, and permission tooling rightly balks at bypass
flags on a command that does not need them. When a probe fails, run it by hand to see the
tool's own error. The most common cause is a login that has expired.

## Nested-CLI gotchas

- **Nested claude**: spawn with `env -u CLAUDECODE claude -p ...` — Claude Code
  refuses to start inside itself otherwise.
- **omp workers**: always `--no-session --no-skills --max-time <s>` — omp otherwise
  auto-discovers skills and instruction files, and the brief is the contract, not
  what the worker finds. Give `--model` the full `provider/model` path; a bare fuzzy
  name can resolve to a different provider and fail on missing auth.
- **Env vars and non-interactive shells**: workers inherit the driver's environment,
  and a driver's shell tool runs non-interactive shells — exports living only in
  `.zshrc` (read by interactive shells alone) may never arrive, depending on how the
  driver itself was launched. This hits any env prerequisite: BYOK keys like
  `OPENROUTER_API_KEY`, gemini's cloud-project variables, etc. Diagnose:
  `zsh -ic 'echo $VAR'` shows it, `zsh -c 'echo $VAR'` does not. Fix at the root, per
  machine: set it in the environment the worker starts from (for zsh, `~/.zshenv`, read by every zsh) or use the tool's native auth
  store (`omp /login`, codex/claude/gemini logins). Never persist `zsh -ic` wrappers
  into `cmd` templates — that couples the roster to shell-init quirks.

## History (verified on 2026-07)

The notes under "Nested-CLI gotchas" were last verified in July 2026.
