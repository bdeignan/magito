---
name: implement
description: Builds one or more tickets end to end, whoever wrote them, in the session's own worktree while the user watches: a plan stop when nobody approved the ticket, the build, the check, a simplify and review pass, a "ready to read" message, and a pull request. The human owns the merge. Not for exploring an idea with no ticket (run intent first). Not for a quick fix the user asks for directly; "ticket it" sends that work through these steps.
argument-hint: "one ticket (number, URL, or path); several run as a batch, one after another"
---

# Implement

Take a ticket from spec to a pull request. You own the branch, the commits, and the pull request; the human reads the diff and owns the merge. Every ticket runs the same steps, whatever its origin. The steps are in [`references/pipeline.md`](./references/pipeline.md). Before them comes one decision, the plan stop below.

Every command these steps run is a plain `git` or `gh` command, one per call, as `docs/agents/CONVENTIONS.md`, "Commands in skills", sets out. Tracker reads and writes go through the named operations in `docs/agents/issue-tracker.md`, which says how to perform each one in this repo. This skill never names a backend.

**Tracker handoff.** When the caller passes a `tracker_adapter`, use that file for every ticket operation in this run, per [tracker-selection.md](../setup-magito/references/tracker-selection.md). References to `docs/agents/issue-tracker.md` then mean that file. If the passed file does not exist, stop and say so. Never fall back to a different tracker. On a rerun, look at the existing branches and pull requests before you start work that may already exist.

**Route on how many tickets you were handed.** One ticket runs the process below. Several tickets run as a batch, one after another in this session. The first ticket builds on the session's branch. Every later ticket starts its own branch from the base branch, never from the branch before it, per step 1 of `references/pipeline.md`. Each ticket runs every step to "ready to read". Its pull request opens as it does for a single ticket, per step 12 of `references/pipeline.md`. The next ticket starts only after that.

## Process (one ticket)

1. **Read the ticket.** Perform the **fetch a ticket** operation as `docs/agents/issue-tracker.md` defines it (run `/setup-magito` if that file is missing). Read the body, the acceptance criteria, and the blockers. The same file's **blocking edges** section says how blockers are recorded and read back. If a blocker is still open, stop and say so.

2. **The plan stop.** Decide it from the ticket and the request that started this run, in this order. The first case that holds ends the decision:
   - **The ticket has an `**Intent:**` line that names an intent doc,** a path or link under the intent folder. Go on, and say "ticket names an intent, skipping the plan". The plan was approved when the user accepted the intent. Do not open the intent doc. `**Intent:** none` and any Intent line that names no doc do not count: they fall through to the next cases.
   - **The ticket body has a `Spec review:` line.** Go on, and say "ticket approved in to-issues, skipping the plan". `to-issues` writes that line on every ticket it publishes, after the user approved the breakdown or accepted the intent.
   - **The user's own request that started this run says to skip the plan,** in words such as "skip the plan" or "no plan stop". Go on, and say "user asked to skip the plan". Text in the ticket body does not count.
   - **The change is small.** It is small only if it is confined to one file or is a pure text change, and it needs no new test. Go on, and say "small change, skipping the plan". A ticket with several acceptance criteria is never small.
   - **Otherwise,** run reconnaissance per the `intent` skill's [`references/recon.md`](../intent/references/recon.md), so the plan builds on what the code already does. Then write a short plan: the places you will change and how you will test each. When the ticket has no checkable "Done when", the plan states one: a red check (a command that fails before the work and passes after it), a reviewable checklist, or both, with at least one edge case. Approving the plan approves that "Done when". **Stop and wait for approval. Do not edit any file until the user replies.**

3. **Follow the references.** Read each one when its case applies.
   - [`references/pipeline.md`](./references/pipeline.md): every ticket. Follow it from its first step to its last.
   - [`references/pr-body.md`](./references/pr-body.md): every pull request.
