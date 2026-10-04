# Is haiku-executor strong enough to build code?

Status: accepted · Opened: 2026-10-03 · Accepted: 2026-10-04

## Problem

`haiku-executor` is the Claude Code subagent that builds tickets which run at the same time
in an `implement` batch (`skills/general/implement/references/parallel.md`, step 3, case 2).
It runs on Haiku at low effort. On 2026-10-03 it built four tickets, and every one needed
rework before commit:

- #231 (small): it added a stray unindented line only so that a `grep "^NOTE"` check would
  match, then reported DONE.
- #229 (large): it compared paths as strings and missed `./`, `../`, and absolute paths.
- #230 and #232 (both small): also reworked.

An earlier run (2026-09-28) shows the same pattern. Two parallel `haiku-executor` agents
missed 77 of about 90 contractions, because each one silently stopped after a few files.

Three of the four reworked tickets were labelled small. So the weakness is not confined to
large tickets.

## Proposed outcome

Parallel tickets in Claude Code are built by an agent named `executor`, which runs on
Sonnet at medium effort by default and on Haiku when thrifty mode is on. Every worker's
brief forbids cheating a check, so a worker that finds a check it cannot honestly pass
stops and says so instead of reporting DONE.

## Decisions so far

1. **Sonnet is the default parallel executor in Claude Code.** The agent file names the
   alias `sonnet`, not a pinned version. An alias points at the newest model of its tier
   that the installed Claude Code knows: it moves when Claude Code updates, not on the day a
   model is released. `ANTHROPIC_DEFAULT_SONNET_MODEL` and `ANTHROPIC_DEFAULT_HAIKU_MODEL`
   pin what each alias means, including in agent files (Claude Code docs, model-config).
2. **Thrifty mode is the switch to Haiku.** No new setting. Thrifty mode already exists:
   `thrifty = true` in `~/.magito/workers.toml` turns it on until changed, and
   `MAGITO_THRIFTY=1` or `0` overrides it for one session. When it is on, the driver passes
   `model: haiku` when it starts the executor, which takes precedence over the agent file.
   The alias `haiku` picks up a newer Haiku the same way. The per-call `model` beats the
   agent file, which beats `CLAUDE_CODE_SUBAGENT_MODEL`. Only
   `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` beats the per-call `model`; when it is set, the
   machine's owner has chosen every subagent's model, and thrifty mode cannot change it.
3. **Rename `haiku-executor` to `executor`.** Its model now depends on thrifty mode, so a
   model in the name would mislead. Past journal entries keep the old name; they record
   history.
4. **The executor runs at `effort: medium`**, up from `low`, to match the `claude` roster
   worker. Effort is fixed in the agent file, so under thrifty mode Haiku runs at `medium`
   too.
5. **The brief forbids cheating a check.** A check is any command whose pass or fail says
   whether the work is done: the repo's check command and everything it runs, the red check
   in a ticket's "Done when" (a `grep`, a command and its output, a test), tests and data
   checks the worker writes under the verification floor, eval thresholds, locked tests, and
   other tooling such as linters, type checkers, pre-commit hooks, and CI. There are two ways
   to cheat one, and both are forbidden:
   - changing the check to agree with the work (weakening an assert, skipping a test,
     loosening a regex, lowering a threshold, adding `# noqa` or `# type: ignore`, adding an
     allowlist entry, silencing an exception);
   - changing the work beyond what the ticket asks so that it agrees with the check (the
     stray line on #231, hardcoding a test's input).

   When a check looks wrong, the worker reports
   `BLOCKED: <the check> looks wrong because <reason>`. The one exception: a worker can fix
   a test it wrote itself in the same build, and its `DONE` report names each such fix and
   why. The rule joins the prohibitions (item 6) in `worker-contract.md`, the report
   protocol (item 5) gains the named-fix line, and both are copied into the `executor`
   agent file. It applies to every worker, shell workers included, since they all receive
   the same brief.

## Affected users and systems

- `agents/haiku-executor.md` (model, effort, name).
- `skills/general/implement/references/parallel.md`, step 3 case 2 and step 4.
- `skills/general/implement/references/worker-contract.md`, "The brief" (items 5 and 6) and
  "Executors".
- `skills/general/implement/SKILL.md` and `parallel.md`, where thrifty mode picks the
  executor's model.
- `scripts/test_worker_start.py` and `scripts/test_worker_start_strict.py`, which use the
  label `haiku-executor` only as sample text.
- Thrifty mode (`implement/SKILL.md`), which picks Haiku for in-session builds and reviews.
  It is a separate path from `haiku-executor`.

## Out of scope

- The magi bench, which already bans Haiku from voting.
- Choosing or changing shell workers in the roster. They do receive the new brief rule.
- Whether `to-issues` from a plan with no intent hands off to `implement`. That is a
  separate question from the same journal entry.

## Constraints

- Stdlib only; no new dependencies.
- A single-ticket run is built by the session itself, so it is not affected.

## Open questions

None.
