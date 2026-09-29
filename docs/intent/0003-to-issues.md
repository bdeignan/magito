# Intent: `to-issues` for the pipeline

Status: accepted · Opened: 2026-09-28 · Accepted: 2026-09-28 · Parent: [0001](./0001-agentic-pipeline.md), migration step 4

## Problem

Intent 0001 puts `to-issues` between the two human gates: an accepted intent goes in, and
issues ready to build come out. Today's `to-issues` was built for a human-driven flow. It
asks the user to approve the breakdown, it writes issues in an older template with no
"done when" or "touches" field, it has no spec review by a second model, and the local
tracker has no made or use-by dates.

## Proposed outcome

`to-issues` takes an accepted intent doc and publishes issues in the format intent 0001
set. A reviewer from a different model family attacks the issues before any build starts.
Local issues carry a made date and a use-by date. Then `to-issues` hands off to `implement`.

## Decisions so far

- Inherited from intent 0001, not re-argued here: the issue format fields (title, intent
  link, behavior, done when, touches, depends on, out of scope, made and use-by dates for
  local issues); an issue that cannot fill "done when" is not ready and goes back; a spec
  ambiguity the intent does not settle is escalation 1; the spec stage labels each issue
  small or large; each intent can override the repo's default tracker.
- **Field mapping.** Every field is a body section in every tracker, so one template serves
  all three. "Depends on" is also written to the tracker's native edge where one exists:
  GitHub's blocked-by link, Jira's "is blocked by" link, and the local `Blocked by:` header.
  The body section is for the reader. The native edge is what `implement` reads for order.
- **No breakdown approval when the input is an accepted intent.** The spec review takes
  over the approval's job. The only stop is escalation 1. A direct `/to-issues` run with no
  accepted intent behind it keeps the approval step, since no gate 1 happened.
  - **The branch keys on a file, not on the caller.** A model cannot reliably tell which
    skill called it. It can read one line. The rule is: if the input is an intent doc whose
    header says `Status: accepted`, do not ask for approval. Otherwise, ask.
  - **The rule sits at the top of the skill,** above the process steps, stated as one
    short "if this, then that" line. A weak model follows the first rule it reads more
    reliably than a condition buried in step 4.
  - **A headless run with a weak model is part of "done when."** Prose cannot guarantee
    this behavior, so it is measured. Run `to-issues` through a shell worker, with the
    cheapest model on the roster, on an accepted-intent fixture in a scratch repo with a
    local tracker. It passes when issue files exist afterwards and the output asks no
    question. Run it again on a draft intent, where it must stop and ask. Gemini 3.5 Flash
    is the target at work. At home, the cheapest working roster entry stands in.
- **The spec reviewer is named in the roster and runs through `worker.py`.**
  - `~/.magito/workers.toml` gains a top-level `spec_reviewer = "<worker>"` line, for
    example `gemini` at work and `codex` at home. Each worker entry gains a `family` field
    (such as `openai`, `google`, `anthropic`), so "a different model family" is a lookup,
    not a guess.
  - `to-issues` writes the draft issues as files and does not publish them yet. It writes a
    brief holding the intent doc and the drafts, then runs
    `worker.py run <spec_reviewer> <dir> <brief>`.
  - The reviewer's family must differ from the writer's. If the named worker fails its
    probe, `to-issues` tries the next roster worker from a different family. If none works,
    it uses a fresh-context subagent, says so in the session, and records the fallback so
    that the PR body can report it.
  - The review runs before publishing, so a rejected issue never reaches the tracker.
- **The spec review uses a fixed checklist and a line-per-issue verdict.**
  - The reviewer answers one line per issue, in a form a script can parse:
    `VERDICT <issue-file> PASS`, `VERDICT <issue-file> FIX: <reason>`, or
    `VERDICT <issue-file> AMBIGUOUS: <what the intent does not settle>`.
  - It checks five things per issue: "done when" is present and verifiable by another
    agent (a red check names a command that fails today; a reviewable check names specific
    criteria); the issue is faithful to the intent and adds nothing outside it or under its
    "Out of scope"; the issue is a thin end-to-end slice that is buildable alone; "depends
    on" is correct and has no cycles; the small or large label fits.
  - **FIX:** the writer revises and the review runs again, at most two rounds. After that,
    it escalates to the user.
  - **AMBIGUOUS:** it escalates at once (escalation 1). The writer never guesses.
  - **PASS on every issue:** publish, then hand off to `implement`.
- **Local issues live in `.scratch/<intent-number>-<slug>/NN-slug.md`.** The directory
  name links each issue to its intent. Two header lines join `Status:` and `Blocked by:`:
  `Made: <date>` and `Use by: <date>`. The default period is 14 days, and a repo can change
  it with `use_by_days` in `.magito/config.toml`. The local tracker template's layout
  section changes to match.
- **`.scratch/` setup stays with `setup-magito`, plus one self-heal in `to-issues`.**
  `setup-magito` already adds `.scratch/` to `.git/info/exclude` and writes a short
  `.scratch/README.md` when the local tracker is chosen. No line goes into
  `SYSTEM-INSTRUCTIONS.md`: every tool loads that file every session, and this rule
  matters only to the one skill that writes local issues. The gap is an intent that
  switches to the local tracker in a repo whose default is GitHub, where `setup-magito`
  never prepared `.scratch/`. So before `to-issues` writes any file under `.scratch/`, it
  checks that `.scratch/` is in `.git/info/exclude` and adds it if absent, with the same
  idempotent one-liner `setup-magito` uses.
- **Draft issues wait in `.scratch/<intent-number>-<slug>/drafts/` during the spec
  review,** whatever the tracker. The **list open tickets** glob
  (`.scratch/*/[0-9][0-9]-*.md`) does not reach into `drafts/`, so a draft is never
  mistaken for a published ticket. For a GitHub or Jira intent, the drafts are deleted
  once published.
- **The plain-language Summary stays at the top of every issue,** above the intent 0001
  fields. The global voice rule requires it, and it is the only section written for the
  human.
- **An intent overrides the tracker with an optional `Tracker:` header field,** for example
  `Status: draft · Opened: <date> · Tracker: local`. `to-issues` reads that field first. If
  it is absent, `to-issues` uses the default in `.magito/config.toml`. If that file is
  absent too, it uses `docs/agents/issue-tracker.md`, as today. `intent` writes the field
  only when the user asks for a different tracker and never raises the topic on its own.
- **Expired issues are re-checked by `implement`, not `to-issues`.** Intent 0001 says an
  expired issue is re-checked "before it is built," and only `implement` knows when that
  is. `to-issues` only writes the dates. The re-check itself belongs to migration step 5.

## Affected users and systems

- `skills/general/to-issues/SKILL.md` and its `references/readability.md`.
- `docs/agents/issue-tracker.md` and the tracker templates under
  `skills/general/setup-magito/references/` (GitHub, local, other).
- `implement`, which reads the issues this step writes.
- `skills/general/intent/SKILL.md`, for the optional `Tracker:` header field.
- `worker.py` and `~/.magito/workers.toml`, if the spec review runs on a shell worker.

## Out of scope

- The build loop, the test lock, integration, and the PR body (migration step 5).
- Gemini and Cursor roster entries, budgets, and thrifty mode (migration step 6).

## Constraints

- Stdlib-only Python. Hooks are insurance, not the floor (ADR 0012).
- Skills name tracker operations, never a backend (ADR 0015).

## Open questions

None.
