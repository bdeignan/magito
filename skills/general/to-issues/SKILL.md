---
name: to-issues
description: Turn an accepted intent doc into reviewed, buildable issues and publish them to the tracker, then hand off to implement. Also breaks a plan or conversation into issues when there is no intent doc. Use once the decisions are made. Do not use it to decide what to build — that is intent.
---

# To Issues

**First rule. If the input is an intent doc whose header line says `Status: accepted`, never
ask the user to approve the breakdown. Go from drafting to publishing without stopping. Stop
only for the escalations in step 6.** Any other input (a plan, a conversation, a draft intent)
gets the approval step in step 4, because no human signed it off yet.

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

1. **Read the input.** For an intent doc, read the whole file. Note the intent number and slug
   from its filename (`0003-to-issues.md` gives `0003` and `to-issues`), and whether its header
   says `Status: accepted`. For an issue reference, fetch its body and comments.

2. **Pick the tracker.** Use the first one found:
   1. A `Tracker:` field in the intent doc's header line.
   2. `tracker` in `.magito/config.toml` at the main worktree root.
   3. `docs/agents/issue-tracker.md`.

   Then read the operations for that tracker. For `local`, read
   `<skills>/setup-magito/references/issue-tracker-local.md.template`. For `github`, read
   `<skills>/setup-magito/references/issue-tracker-github.md.template`. For `other`, or when
   the tracker came from step 2.3, read `docs/agents/issue-tracker.md`. `<skills>` is your
   tool's installed skills directory: `~/.claude/skills` for Claude Code, `~/.agents/skills`
   for most others.

3. **Draft the issues** as files in `.scratch/<NNNN>-<slug>/drafts/`, one file per issue,
   named `01-<slug>.md`, `02-<slug>.md`, in dependency order. With no intent doc, use a short
   free slug for the directory. Before writing the first file, make sure `.scratch/` is a
   line in `.git/info/exclude`:

   ```
   e="$(git rev-parse --git-common-dir)/info/exclude"
   grep -qxF .scratch/ "$e" 2>/dev/null || echo .scratch/ >> "$e"
   ```

   Use the issue template below. Every issue needs at least one edge case in "Done when":
   empty input, a boundary value, a duplicate, a missing file. Happy-path-only is not ready.
   Label each issue **small** (one area, roughly under 100 changed lines) or **large**.

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
   Write a brief file holding: the full intent doc (or the plan you worked from), every draft
   file in full, the checklist below, and this instruction: "Reply with one VERDICT line per
   issue file and nothing else." Then:

   - With a worker name: `python3 <skills>/implement/scripts/worker.py run <name> <repo-root> <brief-file>`.
   - With none: give the same brief to a fresh-context subagent, and tell the user in one line
     that the review fell back to a subagent. If your tool has no subagents, stop and escalate
     "no spec reviewer available."

   The checklist the reviewer applies to each issue:
   1. "Done when" is present and another agent can verify it. A red check names a command
      that fails today. A reviewable check names specific things to look for.
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

7. **Publish** in dependency order, blockers first, with the tracker's **publish a ticket**
   operation. For each "Depends on," also run the tracker's **blocking edges** operation. For
   `local`, publishing means moving the draft out of `drafts/` into its directory, adding the
   `Status:`, `Blocked by:`, `Made:`, and `Use by:` header lines. For any other tracker,
   delete the drafts once every issue is published.

8. **Hand off.** For an accepted intent, call the `implement` skill with the published
   tickets. Otherwise, report the published tickets and stop.

<issue-template>
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

Do not close or modify any parent issue.
