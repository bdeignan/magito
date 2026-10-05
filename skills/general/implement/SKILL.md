---
name: implement
description: Implement one or more tickets end-to-end, whoever wrote them. Every ticket runs the same steps — a plan stop only when no accepted intent covers it, then a build in its own worktree, the check, a review by another model family, and an open pull request. When a ticket has no checkable "Done when", the plan stop states one for the user to approve. You own the git lifecycle; the human owns the merge. Do not use it to explore an idea that has no ticket yet — run intent first. Do not use it for a quick fix the user asks for directly with no ticket — that work needs no worktree and no paid review; when the user wants the full steps for it, they say "ticket it", and to-issues publishes one ticket that this skill then builds.
argument-hint: "one ticket (number, URL, or path); several from one accepted intent land as one pull request; several others run as a batch"
---

# Implement

Take a ticket from spec to open PR. You own the git lifecycle; the human owns the merge. Every ticket runs the same steps, whatever its origin. The one difference between tickets is a single stop for plan approval, and it comes only when no accepted intent covers the ticket. After that stop the run goes on to an open pull request with no further question, and it stops only for an escalation named in [`references/pipeline.md`](./references/pipeline.md).

The deterministic steps run through [`scripts/gitflow.sh`](./scripts/gitflow.sh) and [`scripts/worker.py`](./scripts/worker.py); everything else is judgement. Tracker reads and writes go through the named operations in `docs/agents/issue-tracker.md`, which says how to perform each one in this repo — this skill never names a backend. Commands below run from your actual working directory, not the skill directory, so they address the scripts as `<skills>/implement/scripts/...` (`<skills>` is your tool's installed skills directory — `~/.claude/skills` for Claude Code, `~/.agents/skills` for most others).

**Tracker handoff.** Resolve the adapter through
[tracker-selection.md](../setup-magito/references/tracker-selection.md). When `to-issues`
passes `tracker_adapter` and `main_root`, use them for every ticket operation below and in
references, including fetching blockers and closing tickets. References to
`docs/agents/issue-tracker.md` mean that selected adapter for this run. Resolve local ticket
paths against the passed main root, not the implementation worktree. A passed adapter file
that does not exist stops the run; never fall back to a different tracker. On a rerun,
inspect existing branches and PRs before starting duplicate implementation work.

**Route on how many tickets you were handed.** One ticket runs the process below. Two or more tickets from the same accepted intent run one at a time onto one integration branch and open one pull request: read [`references/integrate.md`](./references/integrate.md). Several tickets otherwise run as a batch, each through the same steps: read [`references/parallel.md`](./references/parallel.md). Each reference stays out of context until its case applies, so the one-ticket run stays cheap.

**Thrifty mode.** Before you name a shell worker, run `python3 <skills>/implement/scripts/worker.py workers` and name only a worker it prints. A worker absent from that output is never launched: if the user names one, say so and stop. Run `python3 <skills>/implement/scripts/worker.py thrifty`. When it prints `on`, use the cheapest subagent model the tool offers for in-session builds and reviews (`haiku` in Claude Code). This applies to a batch too: in Claude Code, pass `model: haiku` when you start the `executor` subagent, and pass no model when thrifty mode is off, so its agent file's `sonnet` applies. Both commands exit non-zero when the machine has no roster file; then no roster worker can be named, thrifty mode counts as off, and the run goes on.

## Process (one ticket)

1. **Read the ticket.** Perform the **fetch a ticket** operation as `docs/agents/issue-tracker.md` defines it (run `/setup-magito` if that file is missing). Read the body, acceptance criteria, and blockers — the same file's **blocking edges** section says how blockers are recorded and read back here. If a blocker is still open, stop and say so.

2. **Decide two facts.** They are the inputs to the next step, and neither is a judgement about how the run goes.
   - **Does the ticket come from an accepted intent?** It does when its body has an `**Intent:**` line that links an intent doc. Take that doc's path, resolved against the main worktree root. Do not judge the doc's status yourself: the start command reads it.
   - **Is the change small?** It is small only if BOTH hold: (a) the change is confined to one file, or is a pure config/text tweak, and (b) it needs no new test seam — verification is just running the existing suite. A ticket with several acceptance criteria is never small; "well-specified" is a reason the plan will be short, not a reason to skip it. A ticket with no checkable "Done when" is never small either, so it always reaches the plan stop.

3. **Run the start command, and show its line to the user, unchanged, before any other work.**

   ```
   python3 <skills>/implement/scripts/worker.py start --family <your-family> [--intent <path>] [--small]
   ```

   Your family is the family of the model you run as: `anthropic` for Claude, `google` for Gemini, `openai` for GPT and Codex models. When the user named a roster worker to build, pass `--builder <worker>` in place of `--family`. Pass `--intent <path>` when the ticket has an intent link, and `--small` when the change is small. The command prints one line, for example:

   ```
   builder: this session (anthropic) · reviewer: codex (openai) · plan: already approved (intent 0005)
   ```

   Keep the reviewer the line names: the review step uses it. The script made the pick, so do not replace it with a reviewer of your own choosing. When the line says `reviewer: none from another family, using a subagent` and the tool you run in cannot start a fresh-context subagent, no review of any kind is possible: stop here, before any build, with escalation 7 in `references/pipeline.md`.

4. **The plan stop.** The last part of the line decides it, and nothing else does.
   - `plan: I will show it and wait for you` — the one stop before the build. Run reconnaissance first, the `intent` skill's [`references/recon.md`](../intent/references/recon.md), so the plan builds on what the code already does. Then write a short plan: the seams you will touch and how you will test each. When the ticket has no checkable "Done when", as often happens with a ticket someone else wrote, the plan states one: a red check (a command that fails before the work and passes after it), a reviewable checklist, or both, with at least one edge case. Approving the plan approves that "Done when". When the work can lead to a fix that is not certain yet, write that fix into the plan as a conditional step, for example "validate X; if it fails, fix Y", so that approving the plan covers the fix. The plan does not say whether the run will end in a pull request: step 5 of the steps decides that from the commits. Then **stop and wait for approval — do not edit any file until the user replies.**
   - `plan: skipped, small change` — say "small change, skipping the plan" and go on.
   - `plan: already approved (intent ...)` — the user signed off on what to build when they accepted the intent. Go on without a stop.

5. **Follow [`references/pipeline.md`](./references/pipeline.md)** from its first step to its last. It holds the worktree, the build and its floor, the check, the commit test, the review, the record, the pull request, and the last message.
