# Close two guardrail gaps found in the pipeline build (pilot run for #194)

Status: accepted · Opened: 2026-09-29 · Accepted: 2026-09-29

## Problem

Two gaps surfaced while building the v0.6.0 pipeline.

1. The headless evals count commits but never check their order. A ticket that commits its
   code before its test still passes, so the "test first" rule is not measured (#199).
2. `install.py` does not know about Codex's guardrail hooks. When their links went missing,
   every Codex command failed with exit code 127 until someone repaired them by hand (#200).

This intent is also the pilot for #194. The session is measured, so the human answers only
escalations.

## Proposed outcome

- Both evals fail any ticket branch whose oldest commit is not test-only.
- A reinstall links the two hooks for Codex and registers them in `~/.codex/hooks.json`.

## Decisions so far

- This intent is the pilot for #194. Chosen by the user on 2026-09-29.
- The work is #199 and #200, taken as the two-ticket change the pilot needs.

- **Hooks are quality of life, never required.** Every workflow and every alignment rule must
  work with hooks off. The user may lose hooks on a work machine that runs Codex. This restates
  ADR 0012 and applies it to #200.
- **Deterministic scripts must not fossilize a process.** Both tickets are audited so that they
  add no rigid step, no error spam, and no needless hurdle. The audit runs on the ticket text
  before any ticket is filed. A ticket that fails the audit is changed, not filed as written.
- The user ran a Codex session on 2026-09-28 that healed a frequent hook error by hand. That
  noise is the failure to avoid.

- **The Codex hook command fails open.** It exits 0 silently when its script file is missing
  and runs the script otherwise. A broken link becomes harmless instead of loud. Decided by the
  user on 2026-09-29.
- **The example config ships the Codex hook keys on**, with a comment that says a machine
  without hooks deletes both keys. Decided by the user on 2026-09-29.
- **#199 keeps a hard fail.** "Test-only" widens to: the oldest commit changes at least one
  `test_*.py` file and no source file. Helper and fixture files may ride along. A later commit
  must change a source file. Decided by the user on 2026-09-29.
- **A hand-made registration counts as already configured.** The installer splits each existing
  command with `shlex.split` and compares the script path, so a quoted or unquoted path
  matches. It also matches a fail-open wrapper of the same script. Settled by the agent, since
  the audit showed the duplicate.

- **The fail-open command is an explicit `sh -c` wrapper**, so it does not depend on whether
  Codex runs commands through a shell:
  `sh -c 'test -x "$0" || exit 0; exec "$0"' '<path>'`. Verified in a scratch script on
  2026-09-29: a present script runs and receives stdin, and a missing script exits 0 with no
  output. Not yet verified inside Codex itself. The ticket's test must run the registered
  command string under `sh` for both cases.

- **Claude Code registrations do not get the fail-open form.** Its hooks are healthy, and this
  intent stays scoped to Codex. Decided by the user on 2026-09-29, on one condition: a machine
  where Claude Code cannot run hooks must still work normally with magito.
- **That condition already holds, and the tickets must keep it holding.** Verified on
  2026-09-29: no skill, script, or instruction file requires a hook, and `install.py` with a
  Claude stanza that has no `hooks` key dry-runs clean and links skills, agents, and `bin/`.
  #200 adds a check to its test: a Codex stanza with no `hooks` keys installs clean, creates no
  hook links, and writes no `hooks.json`.

## Audit findings so far

Verified against `install.py` and `~/.codex/hooks.json`:

- **#200 double-fires hooks.** The installer skips a command only on an exact string match. The
  hand-made `~/.codex/hooks.json` holds single-quoted paths, such as
  `'/Users/brian/.codex/hooks/review-gate.py'`. The installer would write the unquoted form
  beside them, so each hook would run twice on every Bash call.
- **#200 leaves the noisy failure in place.** A registered command that points at a missing
  script exits 127 and prints an error on every Codex command. The ticket restores the link
  on reinstall, but it does nothing when the link is missing between reinstalls.
- **#200 gives no opt-out.** The example config turns the Codex hooks on. A machine without
  hooks needs to omit two keys by hand, and nothing says so.
- **#200 backups are fine.** The installer backs up only when it changes the file.
- **#199 is a magito-internal eval, not a user workflow.** Rigidity there costs a wasted
  real-model run, not a blocked user. Its risk is a false failure: a first commit that holds
  a test plus a helper file, or a test file not named `test_*.py`.

## Affected users and systems

- `scripts/eval-implement.sh`, `scripts/eval-integrate.sh` and their fake-worker test scripts.
- `install.py`, `install.toml.example`, `CLAUDE.md`, `scripts/check.sh`.
- Codex users of magito (the repo owner).

## Out of scope

- Enforcing test-first order inside `implement` itself.
- Running the evals against a real model.
- Editing the user's own `install.toml`.
- Hooks for Gemini CLI or omp.
- Changing the hooks themselves.

## Constraints

- Stdlib-only Python 3.11+.
- `bash scripts/check.sh` must exit 0.

## Open questions

None. Every question is settled.
