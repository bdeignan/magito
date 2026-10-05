---
name: intent
description: Take a vague change to a signed-off intent doc through a one-question-at-a-time interview. Use when the user is still deciding what they want, or says "grill me." Do not use it when the change already fits one issue whose "done when" the user can state now — send that straight to `to-issues`.
---

# Intent

A vague change arrives with real decisions still open. This skill turns it into a signed-off
**intent doc**: one Markdown file recording the problem, the decisions made, and what is still
open, that other skills read and build from.

## When not to use this

Skip straight to `to-issues` when the change already fits one issue and the user can state its
"done when" now — a bug with a known fix, a small feature with an obvious test. Reach for
`intent` when the user is still deciding what they want, or when a request for an issue turns
up open design questions.

## Recon first

Before the first question, survey the code and docs the change touches, unconditionally, per
[references/recon.md](./references/recon.md). Show the brief before asking anything.

## Open the doc at once

Create `<intent_dir>/NNNN-<slug>.md` immediately, with status `draft`. `intent_dir` comes from
`.magito/config.toml` (`setup-magito` sets it; default `docs/intent`). `NNNN` is the next free
number: scan `<intent_dir>` for the highest existing number and add one, zero-padded to four
digits.

Header line: `Status: draft · Opened: <today's date>`.

The header line can also carry an optional `Tracker:` field, for example
`Status: draft · Opened: 2026-09-28 · Tracker: local`. It overrides the repo's default tracker
for this intent's issues. The value is `github`, `local`, or `other`. Write it only when the
user asks for a different tracker. Never raise the topic on your own.

Sections, in this order:

- Problem
- Proposed outcome
- Decisions so far
- Affected users and systems
- Out of scope
- Constraints
- Open questions
- Not yet clear — only when it has content

Update the doc as each decision settles. A settled answer moves straight into "Decisions so
far"; an unsettled one goes into "Open questions." Never batch these edits to the end.

## Converse

Ask one question at a time, waiting for an answer before the next. Give every question a
recommended answer. Call `research`, `challenging-assumptions`, `magi` (only where it is installed), or `domain-modeling`
when a question needs one of them.

Mark each open question **agent** (you can settle it alone) or **user** (only the user can
answer it). While the user answers a live question, dispatch every agent question to a
background subagent that runs `research` on it, and fold each answer into the doc as it lands. When the tool cannot run a background subagent, settle the agent questions yourself between the user's answers.

An open question is one you can already state precisely, even without an answer. Something you
can tell is coming but cannot yet phrase that precisely goes into "Not yet clear" instead, and
graduates into "Open questions" once it sharpens.

## Resume a draft

When the user asks to continue an intent, read the draft, then run recon again: the code can
have changed since the draft was written. Resume at its "Open questions" and "Not yet clear"
sections. They are the map; no other planning document needs loading. This is how an effort
spans several sessions — no separate skill for it.

## Accept means go

On "accept": set status to `accepted`, add an `Accepted:` date to the header line, commit the
doc in owner mode, then call `to-issues` directly. The user's next signal from the pipeline is
an escalation or the PR, not a prompt to type the next command.

"Accept, but hold" does the same, except it does not call `to-issues`. Use it to batch several
intents, or to hand off to another machine.

Once accepted, the doc is a record and is never updated again. A doc has only two statuses:
`draft` (open questions remain) and `accepted` (signed off).

In guest mode, the doc is never committed — it is already excluded from git, per
`setup-magito`.

## ADRs

The accepted intent is itself the record of its own decisions. Write an ADR only when a
decision sets a rule that future, unrelated work must follow. Call `domain-modeling` to write
it.
