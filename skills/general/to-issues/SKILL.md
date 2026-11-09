---
name: to-issues
description: Turn an accepted intent doc into reviewed, buildable tickets and publish them to the tracker, then offer one session card per ticket that is ready to start. Also breaks a plan or conversation into tickets when there is no intent doc, and publishes a single ticket for a bug or request the user wants built ("ticket it"). Use once the decisions are made. Do not use it to decide what to build — that is intent.
---

# To Issues

**First rule. If the input is an intent doc whose header line says `Status: accepted`, never
ask the user to approve the breakdown. Go from drafting to publishing without stopping. Stop
only where steps 6 and 7 say to stop.** Any other input (a plan, a conversation, a
draft intent) gets the approval step in step 4, because no human signed it off yet.

Each ticket is a thin slice that works end to end and can be built alone. The agent that
builds it is weaker than you and remembers nothing of this conversation, so the body carries
everything.

## Write for a less-capable implementer

- Describe required behavior and observable acceptance criteria. Supply exact text only when
  wording itself is the deliverable; otherwise let the builder choose the implementation.
- Links are background only. Everything needed to build is in the body.
- Exact commands over descriptions: "run `python install.py`", not "reinstall".
- Decisions are made here, not downstream. A ticket that holds an open question is not ready.
- "Done when" must be checkable by a weak agent: command output, file contents, observable
  behavior. Never "code is clean" or "works well."
- Plain words throughout. The [readability standard](./references/readability.md) governs
  word choice and gives the six-item self-check for the summary.

## Process

Every path below that starts with `.scratch/` is in the folder the planner works in.

1. **Read the input.** For an intent doc, read the whole file. Note the intent number and slug
   from its filename (`0003-to-issues.md` gives `0003` and `to-issues`), and whether its header
   says `Status: accepted`. For a ticket reference, fetch its body and comments.

2. **Resolve the tracker adapter** through
   [tracker-selection.md](../setup-magito/references/tracker-selection.md). Read that adapter
   for every tracker operation below. `<skills>` is the folder that holds this skill's own
   folder: the parent of the directory its `SKILL.md` is in.

3. **Draft the tickets** as files in `.scratch/<NNNN>-<slug>/drafts/`, one file per ticket,
   named `01-<slug>.md`, `02-<slug>.md`, in dependency order. With no intent doc, use a short
   free slug for the directory. Before writing the first file, make sure `.scratch/` is a
   line in `.git/info/exclude`, exactly as the "Private-state excludes" section of
   `<skills>/setup-magito/SKILL.md` does it.

   If `drafts/` already holds numbered drafts, an earlier run stopped partway. Keep them,
   skip drafting, and go to step 5. Only numbered files in `drafts/` are draft tickets.

   Use the ticket template below. Every ticket needs at least one edge case in "Done when":
   empty input, a boundary value, a duplicate, a missing file. Happy-path-only is not ready.
   Label each ticket **small** (one area, roughly under 100 changed lines) or **large**. In
   "Depends on", name other drafts by their file name (`01-<slug>.md`).

4. **Approval, only when the input is not an accepted intent.** Show a numbered list: title,
   depends on, size. Ask whether the granularity and order are right. Revise until the user
   approves. For an accepted intent, skip this step entirely.

5. **Spec review by a fresh-context subagent.** Write the brief to
   `.scratch/<NNNN>-<slug>/review-brief.md`. It holds the full intent doc
   (or the plan you worked from), every draft file in full, the checklist below, and these
   instructions:

   "You are reviewing, not building. Do not create, edit, or delete any file. Report every
   defect you find now, in this one reply. Do not hold any back for a later round. Reply with
   one VERDICT line per ticket file and one COVERAGE line for the complete set. NOTE lines are
   not verdicts. A NOTE never blocks.

   A `FIX` verdict must name the checklist item, 1 to 5, that the ticket fails, and quote the
   sentence that fails it. Or it must name the decision that the ticket contradicts: a decision
   in the intent doc, or, when the set has no intent doc, a decision in the plan the user
   approved. Anything else is a NOTE line.

   Wording taste is a NOTE. For a ticket that changes only prose, a reviewable check is enough:
   do not ask for a test that pins wording."

   Give the whole brief to a fresh-context subagent, one that has seen none of this
   conversation, and take its reply as the round's verdicts. When your tool cannot start a
   subagent, review the drafts yourself against the same checklist, in the same reply format,
   and tell the user so in one line.

   The checklist the reviewer applies to each ticket:
   1. "Done when" is present and another agent can verify it. A red check names a command
      that fails before the work and passes after it. A reviewable check names specific
      things to look for.
   2. It is faithful to the intent. It adds nothing outside the intent or under its
      "Out of scope."
   3. It is a thin end-to-end slice that can be built alone.
   4. "Depends on" is correct and has no cycles.
   5. The small or large label fits the work.

   Also check the complete set against every required intent outcome. Report missing
   coverage, duplicated scope, and dependencies that prevent the set delivering the intent.
   All individual tickets passing is insufficient when an outcome is absent.

   The reply format:

   ```
   VERDICT 01-slug.md PASS
   VERDICT 02-slug.md FIX: <what is wrong>
   NOTE 02-slug.md: <a remark that does not block>
   VERDICT 03-slug.md AMBIGUOUS: <what the intent does not settle>
   COVERAGE PASS
   # Or: COVERAGE FIX: <missing outcome> / COVERAGE AMBIGUOUS: <unsettled intent>
   ```

6. **Act on the verdicts.** Require exactly one verdict for each draft filename and exactly
   one COVERAGE verdict. Missing, duplicate, unknown, or malformed verdicts are a failed
   review; stop and report them. NOTE lines are not verdicts. They do not count toward the
   rule of exactly one verdict per draft file. Apply the following rules to both ticket and
   coverage verdicts:
   - **FIX or AMBIGUOUS** on any ticket: revise those drafts and run step 5 again. For an
     AMBIGUOUS line, revise the draft to say what the intent settles. Run at most three review rounds. After round 3, if any FIX or AMBIGUOUS line is left,
     stop and show the user the remaining lines.
   - **PASS** on every ticket and COVERAGE: publish. Each published body ends with
     `Spec review: subagent, round <n>`, or `Spec review: planner, round <n>` when you
     reviewed the drafts yourself.

   NOTE lines follow their own rules:
   - A reply can hold several NOTE lines for one draft file and none for another.
   - A NOTE line never stands in for a verdict. A reply with a NOTE line for a file and no
     `VERDICT` line for that file is a failed review, as a missing verdict is.
   - Never run another review round for a NOTE. You can apply a NOTE to a draft before
     publishing when the change is plainly right, and you list each one you applied when you
     report the published tickets. A draft changed for a NOTE after every verdict
     was PASS is published without a new review round.

7. **Publish** by following [publication.md](./references/publication.md). It looks for
   each ticket before publishing it, so a rerun after an interruption never publishes a
   ticket twice.

8. **Hand off.** Never call `implement` yourself. After publishing, stop and offer one session
   card per ticket that is ready to start. A ticket is ready when all its blockers are
   closed: run the ready check in the tracker adapter from step 2 for each published ticket.
   - **Each card** starts a worker session with Sonnet, Worktree on, and Auto mode. Its brief
     is "Run `/implement <ticket>`". With the local tracker, the brief also carries the full
     ticket body, because a worker cannot read the planner's `.scratch/`.
   - **A blocked ticket** gets no card yet. Tell the user which tickets are blocked, and that
     when one of their blockers merges, they ask you for the next cards. Then run the ready
     check again on the tickets that had no card, and offer a card for each one that is now
     ready.
   - **When your tool cannot offer a card,** print one line per ready ticket: "Run
     `/implement <ticket>` in a new session." With the local tracker, print the ticket body
     under its line, to paste into that session.

   For a single "ticket it" request, offer the one card the same way.

<issue-template>
# <short title: what this ticket delivers>

## Summary

<one plain paragraph for a reader who did not do this work: what this ticket delivers and why
it matters. No file paths or symbols here.>

**Intent:** <link to the intent doc>, <which decisions this ticket carries>

**Size:** small | large

**Risk:** Low | Normal | High
<Low is docs, comments, copy, or deleting dead code. High is a contract other tickets rely
on, data at external edges, security, or CI or install config. Normal is everything else.>

## Behavior

<required behavior, constraints, and commands needed to verify it>

## Done when

**Red check:** <a command that fails before the work and passes after it>
**Reviewable check:** <numbered, specific things a reviewer verifies>

(One or both. At least one edge case.)

## Touches

<files or areas likely to change: a hint for merge order, not a lock>

## Depends on

<the blocking tickets, or "None. It can start immediately.">

## Out of scope

<what this ticket does not do, and where that work belongs>
</issue-template>

Never edit the intent doc. Once accepted, it is a signed-off record.
