---
name: to-issues
description: Turn an accepted intent doc into reviewed, buildable issues and publish them to the tracker, then hand off to implement. Also breaks a plan or conversation into issues when there is no intent doc. Use once the decisions are made. Do not use it to decide what to build — that is intent.
---

# To Issues

**First rule. If the input is an intent doc whose header line says `Status: accepted`, never
ask the user to approve the breakdown. Go from drafting to publishing without stopping. Stop
only for an escalation named in step 5 or step 6.** Any other input (a plan, a conversation, a
draft intent) gets the approval step in step 4, because no human signed it off yet.

Each issue is a thin slice that works end to end and can be built alone. The agent that
builds it is weaker than you and remembers nothing of this conversation, so the body carries
everything.

## Write for a less-capable implementer

- Spell out the full deliverable. If the issue asks for a document, config, or skill, include
  the complete text to write, or an exact path to copy from.
- Links are background only. Everything needed to build is in the body.
- Exact commands over descriptions: "run `python install.py`", not "reinstall".
- Decisions are made here, not downstream. An issue that holds an open question is not ready.
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
   says `Status: accepted`. For an issue reference, fetch its body and comments.

2. **Pick the tracker.** The repo default is `tracker` in `.magito/config.toml`, or, when
   that file is absent, the tracker `docs/agents/issue-tracker.md` describes. The operations
   for the repo default are always in `docs/agents/issue-tracker.md`.

   An intent doc can override the default with a `Tracker:` field in its header line. Only
   when that field names a tracker different from the default, read the operations from the
   matching template instead: `<skills>/setup-magito/references/issue-tracker-<value>.md.template`
   for `github` or `local`. An override to `other` cannot work, because only the repo's own
   file can describe that tracker: escalate. `<skills>` is your tool's installed skills
   directory: `~/.claude/skills` for Claude Code, `~/.agents/skills` for most others.

3. **Draft the issues** as files in `.scratch/<NNNN>-<slug>/drafts/`, one file per issue,
   named `01-<slug>.md`, `02-<slug>.md`, in dependency order. With no intent doc, use a short
   free slug for the directory. Before writing the first file, make sure `.scratch/` is a
   line in `.git/info/exclude`, exactly as the "Private-state excludes" section of
   `<skills>/setup-magito/SKILL.md` does it.

   Use the issue template below. Every issue needs at least one edge case in "Done when":
   empty input, a boundary value, a duplicate, a missing file. Happy-path-only is not ready.
   Label each issue **small** (one area, roughly under 100 changed lines) or **large**. In
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
   Reply with one VERDICT line per issue file and nothing else." Then:

   - With a worker name: `python3 <skills>/implement/scripts/worker.py run <name> <main-worktree-root> .scratch/<NNNN>-<slug>/review-brief.md`.
   - With none: give the same brief to a fresh-context subagent, and tell the user in one line
     that the review fell back to a subagent. If your tool has no subagents, stop and escalate
     "no spec reviewer available."

   Run `git status --short` at the main worktree root just before and just after the review.
   If the two outputs differ, the reviewer changed a file: stop and escalate, because a
   reviewer that writes is not a review.

   The checklist the reviewer applies to each issue:
   1. "Done when" is present and another agent can verify it. A red check names a command
      that fails before the work and passes after it. A reviewable check names specific
      things to look for.
   2. It is faithful to the intent. It adds nothing outside the intent or under its
      "Out of scope."
   3. It is a thin end-to-end slice that can be built alone.
   4. "Depends on" is correct and has no cycles.
   5. The small or large label fits the work.

   The reply format, one line per issue:

   ```
   VERDICT 01-slug.md PASS
   VERDICT 02-slug.md FIX: <what is wrong>
   VERDICT 03-slug.md AMBIGUOUS: <what the intent does not settle>
   ```

6. **Act on the verdicts.**
   - **AMBIGUOUS** on any issue: stop and escalate to the user at once, quoting the line. Do
     not guess.
   - **FIX** on any issue: revise those drafts and run step 5 again. After two FIX rounds,
     stop and escalate with the remaining FIX lines.
   - **PASS** on every issue: add a last line to each draft,
     `Spec review: <worker or "subagent"> (<family>), round <n>`, then publish.

7. **Publish** in dependency order, blockers first. For each draft:
   1. Replace every draft file name in its "Depends on" with the identifier the tracker gave
      that blocker when it was published.
   2. Publish it with the tracker's **publish a ticket** operation. The text after `# ` on the
      first line is the title. The body is everything after that first line: remove the
      `# <title>` line from the body, so that the title appears only once.
   3. Record each blocker with the tracker's **blocking edges** operation.
   4. Delete the draft file.

   Then delete `review-brief.md` and the empty `drafts/` folder.

8. **Hand off.** For an accepted intent, call the `implement` skill with the published
   tickets. Otherwise, report the published tickets and stop.

<issue-template>
# <short title: what this issue delivers>

## Summary

<one plain paragraph for a reader who did not do this work: what this issue delivers and why
it matters. No file paths or symbols here.>

**Intent:** <link to the intent doc>, <which decisions this issue carries>

**Size:** small | large

## Behavior

<the end-to-end behavior, with every text, config, or command the builder needs, in full>

## Done when

**Red check:** <a command that fails before the work and passes after it>
**Reviewable check:** <numbered, specific things a reviewer verifies>

(One or both. At least one edge case.)

## Touches

<files or areas likely to change: a hint for merge order, not a lock>

## Depends on

<the blocking issues, or "None. It can start immediately.">

## Out of scope

<what this issue does not do, and where that work belongs>
</issue-template>

Never edit the intent doc. Once accepted, it is a signed-off record.
