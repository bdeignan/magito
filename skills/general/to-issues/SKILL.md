---
name: to-issues
description: Turn an accepted intent doc into reviewed, buildable tickets and publish them to the tracker, then hand off to implement. Also breaks a plan or conversation into tickets when there is no intent doc. Use once the decisions are made. Do not use it to decide what to build — that is intent.
---

# To Issues

**First rule. If the input is an intent doc whose header line says `Status: accepted`, never
ask the user to approve the breakdown. Go from drafting to publishing without stopping. Stop
only for an escalation named in steps 5 to 7.** Any other input (a plan, a conversation, a
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

Every path below that starts with `.magito/` or `.scratch/` is relative to the **main
worktree root**, which `git worktree list --porcelain | head -1` prints as `worktree <path>`.
Never resolve them against the current directory: inside a linked worktree, that directory
is a different folder.

1. **Read the input.** For an intent doc, read the whole file. Note the intent number and slug
   from its filename (`0003-to-issues.md` gives `0003` and `to-issues`), and whether its header
   says `Status: accepted`. For a ticket reference, fetch its body and comments.

2. **Resolve the tracker adapter** through
   [tracker-selection.md](../setup-magito/references/tracker-selection.md). Keep its absolute
   path and the absolute main worktree root with the tickets throughout this run. Read that
   adapter for every tracker operation below. `<skills>` means the installed skills directory.

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

5. **Spec review by a different model family.** Your family is the family of the model you
   run as: `anthropic` for Claude, `google` for Gemini, `openai` for GPT and Codex models.
   Run:

   ```
   python3 <skills>/implement/scripts/worker.py reviewer <your-family>
   ```

   It prints a worker name, or exits non-zero when no worker from another family works.
   Write the brief to `.scratch/<NNNN>-<slug>/review-brief.md`. It holds the full intent doc
   (or the plan you worked from), every draft file in full, the checklist below, and this
   instruction: "You are reviewing, not building. Do not create, edit, or delete any file.
   Reply with one VERDICT line per ticket file and one COVERAGE line for the complete set." Then:

   A reviewer must not change any file. Check this by file contents, since `git status`
   cannot see the excluded drafts. `S` below means
   `python3 <skills>/to-issues/scripts/worktree_snapshot.py`, `T` means the absolute ticket
   directory, and `E` means a new temporary directory outside the repo, from `mktemp -d`.
   1. Before the review: `S capture <main-root> T E/before.json`.
   2. Run the review, saving its output to `E/review.txt`.
   3. After the review: `S capture <main-root> T E/after.json`, then
      `S compare E/before.json E/after.json`.

   If any of these commands fails, or `compare` lists a changed file, stop and escalate with
   its output. A subagent review gets the same three steps.

   - With a worker name: `python3 <skills>/implement/scripts/worker.py run <name> <main-worktree-root> <main-worktree-root>/.scratch/<NNNN>-<slug>/review-brief.md`.
   - With none: give the same brief to a fresh-context subagent, and tell the user in one line
     that the review fell back to a subagent. If your tool has no subagents, stop and escalate
     "no spec reviewer available."

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
   VERDICT 03-slug.md AMBIGUOUS: <what the intent does not settle>
   COVERAGE PASS
   # Or: COVERAGE FIX: <missing outcome> / COVERAGE AMBIGUOUS: <unsettled intent>
   ```

6. **Act on the verdicts.** Require exactly one verdict for each draft filename and exactly
   one COVERAGE verdict. Missing, duplicate, unknown, or malformed verdicts are a failed
   review; stop and report them. Apply the following rules to both ticket and coverage verdicts:
   - **AMBIGUOUS** on any ticket: stop and escalate to the user at once, quoting the line. Do
     not guess.
   - **FIX** on any ticket: revise those drafts and run step 5 again. After two FIX rounds,
     stop and escalate with the remaining FIX lines.
   - **PASS** on every ticket and COVERAGE: publish. Each published body ends with
     `Spec review: <worker or "subagent"> (<family>), round <n>`.

7. **Publish** by following [publication.md](./references/publication.md). It looks for
   each ticket before publishing it, so a rerun after an interruption never publishes a
   ticket twice.

8. **Hand off.** For an accepted intent, call `implement` with the published ticket
   identifiers and these two named fields: `tracker_adapter: <absolute-path>` and
   `main_root: <absolute-path>`. `implement` uses that adapter for every ticket operation.
   Otherwise, report the published tickets and stop.

<issue-template>
# <short title: what this ticket delivers>

## Summary

<one plain paragraph for a reader who did not do this work: what this ticket delivers and why
it matters. No file paths or symbols here.>

**Intent:** <link to the intent doc>, <which decisions this ticket carries>

**Size:** small | large

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
