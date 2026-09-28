# Intent: the `intent` skill

Status: accepted · Opened: 2026-09-28 · Accepted: 2026-09-28 · Parent: [0001](./0001-agentic-pipeline.md), migration step 3

## Problem

The pipeline in intent 0001 starts with an intent doc, but no skill produces one. Today the
same work is split across `grilling` (a one-question-at-a-time interview) and `wayfinder`
(a map of decision tickets for work too big for one session). Neither writes an intent doc,
and `wayfinder` keeps its map on the tracker, which guest repos and local-only work cannot
always use.

## Proposed outcome

One skill, `intent`, takes a vague change to a signed-off intent doc:

1. **Recon.** Survey the code and docs the change touches, per `grilling`'s
   `references/recon.md`, and show a short brief of what already exists.
2. **Open the doc at once** with status `draft`, in `intent_dir` from
   `.magito/config.toml`. Each settled answer goes into "Decisions so far" when it is
   settled. Each unsettled one goes into "Open questions."
3. **Converse.** `grilling`'s interview: one question at a time, each with a recommended
   answer. Call `research`, `challenging-assumptions`, `magi`, or `domain-modeling` when a
   question needs them.
4. **Span sessions.** A draft's open questions are the map. The next session reads the doc
   and resumes. This replaces `wayfinder`'s map tickets.
5. **Sign-off.** The user accepts, the status becomes `accepted`, and the doc is committed in
   owner mode. This is gate 1.

## Decisions so far

- **Threshold.** A change skips `intent` when it fits in one issue whose "done when" the user
  can state now: a bug with a known fix, or a small feature with an obvious test. `intent` is
  for any change where the user is still deciding what they want. When a request for an
  issue shows open design questions, `intent` offers itself.
- **Accept means go.** Accepting marks the doc `accepted` and hands straight to `to-issues`,
  which chains into `implement`. The user next hears from the pipeline on an escalation or
  at the PR. "Accept, but hold" signs the doc off without starting the build, for batching
  intents or starting on another machine.
- **No done state.** The doc has two statuses: `draft` (open questions remain, so the next
  session resumes it) and `accepted` (signed off). After acceptance it is a record and is
  never updated. What gets finished is the issues and PRs, not the intent. The Anthropic
  playbook treats `intent.md` the same way: approved, merged, then an audit trail.
- **ADRs only for standing rules.** The accepted intent is the record of its decisions. An
  ADR is written only when a decision sets a rule that future, unrelated work must follow
  (for example, ADR 0016). Then `intent` calls `domain-modeling` to write it.
- **From `wayfinder`, keep three ideas and drop the machinery.**
  - Keep a "Not yet clear" section, separate from "Open questions," for decisions that
    are coming but cannot be phrased precisely yet. It appears only when it has content.
  - Keep an "Out of scope" section, so `to-issues` does not re-argue scope per issue.
  - Keep marking which open questions the agent can settle alone. While the user answers
    one question, `intent` sends those to `research` subagents in the background and folds
    the answers into the doc.
  - Drop the tracker map ticket, labels, claiming, `research/<name>` branches, and the
    "task" and "prototype" ticket types. A throwaway prototype can still answer a question.
- **`grilling` disappears as a skill.** Its interview becomes how `intent` converses, and
  `intent`'s description triggers on "grill me." Its `references/recon.md` moves under
  `intent`. Every pointer to `grilling` or `wayfinder` (for example, `implement` step 2,
  `ask-magito`, and the spine in `docs/agents/CONVENTIONS.md`) moves to `intent`.
  The "Wayfinding operations" section leaves `docs/agents/issue-tracker.md` and the three
  `setup-magito` tracker templates, since nothing uses it any more.

## Affected users and systems

- `skills/general/grilling/` and `skills/general/wayfinder/`, which merge into the new skill.
- `docs/intent/`, and the `intent_dir` key from #175.

## Out of scope

- Rewriting `to-issues` and `implement`. They are migration steps 4 and 5. This intent only
  hands off to them.
- Removing `ask-magito` (migration step 7).

## Constraints

- Works in Claude Code, Gemini CLI, and Cursor.
- Guest mode: the doc lives at `intent_dir` and is excluded from git, per #175.

## Open questions

None.
