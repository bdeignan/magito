# Make the workflow use the workers and reviewers a machine has

Status: accepted · Opened: 2026-10-01 · Accepted: 2026-10-01

## Problem

The user ran magito v0.6.0 on a work machine with Sonnet 5 as the driver. Two things went
against what they expected.

1. The session did not seem to notice that workers and reviewers were available.
2. In another session, after the build, the agent asked whether to run `reviewing-changes`.
   The user expected the review and the pull request to happen without a question.

The user's first reading is that the workflow does not wire in workers and reviewers from
other model families or other command-line tools firmly enough.

Recon on 2026-10-01 found that these are the facts today:

- Review and pull request are automatic only for a pipeline ticket. `implement` asks about the
  review and waits for "ship it" on every other ticket. That question is the designed
  behavior on the manual path (ADR 0013, ADR 0018).
- A reviewer from a different model family is picked only on the pipeline path and in
  `to-issues` step 5. The manual path reviews with `reviewing-changes`, which uses subagents
  of the driver's own model. It never reads the roster.
- A worker builds only when the user names one. On the pipeline path the wording is "build it
  yourself, or through a worker", so the driver can always build alone.
- The roster is `~/.magito/workers.toml`, one file per machine. `setup-magito` reports it and
  offers the example. Nothing else tells a session that a roster exists.
- When the roster file is missing, `worker.py reviewer` exits 2. `pipeline.md` step 5 names
  only exit 3 as the case that falls back to a subagent.

So the report has at least two possible causes. Either the tickets were not pipeline tickets
and the workflow did what it was written to do, or they were pipeline tickets and the driver
did not follow the pipeline path.

The user then said, as the main user, that they do not know what separates a pipeline ticket
from any other ticket. A second recon pass on 2026-10-01 looked at that boundary and found:

- **One switch controls three separate things.** Whether a ticket links an accepted intent
  decides who approved what to build, whether the run stops for the human, and how strong the
  review is. Nothing lets the user have one without the others.
- **The path without an accepted intent gets the most stops and the weakest review.** It
  asks for plan approval, offers a review that defaults to a skip on a small diff, reviews
  with the driver's own model family, and waits for "ship it". That is the path the README
  recommends for work the user already understands.
- **`implement` has four behaviors, not two.** One manual ticket, a manual fan-out of several
  tickets (review is mandatory but uses the driver's own family), one pipeline ticket, and an
  integrated pipeline run.
- **The run never says which behavior it chose.** The plan step announces a skipped plan.
  Nothing announces "this is a pipeline ticket" or "this is not, so I will stop three times".
- **The test is two text markers, and one of them is weak.** `to-issues` adds a
  `Spec review:` line to every ticket it publishes, with or without an intent. Only the
  `**Intent:**` line and the linked doc's status separate the two kinds.
- **The status can change after the ticket is written.** A ticket cut from a draft intent
  becomes a pipeline ticket when that intent is later accepted.
- **Intent 0001's worker routing is only partly built.** It decided four rules: build with
  subagents, review with a different family, match the model to the ticket size, and fall
  back when a quota runs out. The review rule and the reviewer fallback exist. Nothing reads
  the `Size:` label, and no build goes to a worker unless the user names one.

## Proposed outcome

`implement` has one set of steps. Every ticket runs them, alone or in a batch.

1. A script opens the run. It reads the roster, picks a reviewer from another model family,
   and prints one start line: who builds, who reviews, and whether a plan stop comes.
2. A ticket with no accepted intent stops once for plan approval. A small change skips that
   stop and says so. A ticket from an accepted intent never stops here.
3. The ticket is built in its own worktree by the driver, or by a worker the user named.
4. The driver runs the check. The reviewer from another family reviews, for up to three
   rounds. A subagent reviews only after the script confirms the roster has no one.
5. With a clean tree and at least one commit ahead of the base, the run opens the pull
   request. With no commit, it posts its findings on the ticket and opens nothing.
6. The session's last message says who built, who reviewed, and what was found. The pull
   request body says none of that.

The user acts at plan approval when there is one, at an escalation, and at the merge. A thin
skill reports whether each roster worker is ready on the machine.

## Decisions so far

- **Every `implement` run reviews and opens the pull request without a question.** The
  review comes from a different model family when the roster has one. This holds whatever
  the ticket's origin. Decided by the user on 2026-10-01. It replaces ADR 0013's rule for
  work the user drives by hand.
- **One stop stays for a ticket with no accepted intent: approval of the plan.** Nobody has
  agreed on what to build there, so the plan is where the user agrees. The review offer and
  "ship it" go away. Decided by the user on 2026-10-01.
- **The run decides at the end whether to open a pull request, from a fixed test.** Some
  tickets validate and produce findings, not a change to merge, and that is known only at
  run time. The plan does not declare an ending. A fix that validation can lead to is written
  into the plan as a conditional step, so plan approval covers it. Decided by the user on
  2026-10-01. It replaces an earlier idea that the plan names the ending.
- **The test is: the branch has at least one commit ahead of the base.** Then the run reviews
  and opens the pull request. With no commit ahead, it opens nothing and reports its
  findings. The test makes no judgment of whether the change is material. Decided by the
  user on 2026-10-01.
- **Work must be committed before the test runs, on every kind of ticket.** A run that
  leaves its work uncommitted has no commit ahead of the base, and the test then reports
  "nothing to merge" while the change sits in the working tree. So the test refuses a
  working tree with uncommitted changes. Decided by the user on 2026-10-01. Recon found that
  `gitflow.sh merge` already refuses such a tree, and `gitflow.sh push` and `gitflow.sh pr`
  do not.
- **After plan approval, a ticket with no accepted intent follows the same steps as a
  pipeline ticket.** It gets its own worktree, a review marker, tests committed first and
  locked when the ticket names a red check, the check run by the driver, and up to three
  review rounds. `implement` becomes one path with one optional stop in front of it. Decided
  by the user on 2026-10-01.
- **A small change still skips the plan.** The existing rule stays: one file or a pure text
  or config tweak, no new test, and never a ticket with several acceptance criteria. The run
  announces the skip. Such a ticket has no stop before the pull request. Decided by the user
  on 2026-10-01.
- **The driver builds unless the user names a worker.** No routing by ticket size is added.
  The reviewer comes from a family other than the builder's, whoever built. Decided by the
  user on 2026-10-01. Intent 0001's rule to match the model to the ticket size stays unbuilt.
- **Each run starts with one line that names the builder and the reviewer it found.** For
  example: `builder: this session (anthropic) · reviewer: codex (openai)`. Proposed by the
  agent with the decision above; the user has not objected.
- **When no reviewer from another family is available, a fresh-context subagent reviews.**
  The run does not stop. This covers a missing roster file, an invalid one, and a roster
  where every worker from another family fails its probe. Decided by the user on 2026-10-01.
- **The subagent review must never become the habit.** The user saw sessions at work that
  never tried the roster. A run must try the roster on every review, and it reaches the
  subagent only after that attempt fails. Decided by the user on 2026-10-01. How this is
  enforced is an open question below.
- **A script enforces "try the roster first", not prose.** One command opens every run: it
  reads the roster, probes for a reviewer from another family, and prints the start line.
  The record of a subagent review can be written only through a command that first re-checks
  the roster, and that command refuses when a worker from another family answers. So a run
  that skips the roster cannot open a pull request. Decided by the user on 2026-10-01.
- **The script stays simple, and it is tested.** Facts about one tool live in the roster as
  data, never in the script as a special case. The tests include a run against a real
  reviewer, because the pilot showed that a fake worker misses real failures. Decided by the
  user on 2026-10-01.
- **The same script reports whether each worker is ready on this machine.** For each roster
  entry it reports: the tool is installed, the environment variables it needs are set, its
  probe answers, and its model family. Decided by the user on 2026-10-01.
- **A worker's required environment variables are declared in its roster entry.** Gemini CLI
  needs `GOOGLE_CLOUD_PROJECT`, and a driver sometimes misses that. The script names the
  missing variable and says to export it from `~/.zshenv`. Proposed by the agent on
  2026-10-01 as the way to meet the decision above; the field name is not settled.
- **A thin skill wraps the script and becomes the one owner of roster care.** It reports
  every time it runs. It writes one thing only: when the roster file is missing, it offers to
  seed one from the example and writes after the user agrees. It never edits an existing
  roster; for a broken entry it names the line to change. A second run changes nothing.
  `setup-magito` and the worker contract's "First roster" section point at it. Decided by
  the user on 2026-10-01.
- **One reviewer fallback covers every failure of the pick.** A missing roster, an invalid
  roster, and a roster with no working worker from another family all lead to the subagent
  review. Settled by the agent on 2026-10-01 from the user's decision above; it answers what
  `pipeline.md` step 5 does on exit 2.
- **The commit test applies to every ticket, with or without an accepted intent.** A ticket
  from an accepted intent that produces no commit opens no pull request. Settled by the
  agent on 2026-10-01: the user chose one set of steps for both kinds of ticket.
- **A pull request never says where its review came from.** No reviewer name, no model
  family, and no note that a subagent reviewed. These are magito details that matter only to
  the user and their agents. Decided by the user on 2026-10-01. It reverses the "Pipeline
  tickets" section of `pr-body.md` and one sentence of ADR 0018.
- **The pull request body keeps only what a code reviewer needs, in ordinary words.** Review
  rounds and verdicts leave it. The failing-then-passing test stays under "How it was
  verified". Each choice the agent made alone stays, written as "Chose X over Y because Z".
  No magito term appears. Decided by the user on 2026-10-01.
- **The session's last message carries what the pull request leaves out.** It names who
  built, who reviewed, how many rounds ran, and what the reviewer found. No file is written
  for it. Decided by the user on 2026-10-01.
- **A run that ends with no commit reports its findings in two places.** It posts a comment
  on the ticket in ordinary words, and it states the findings in the session's last message.
  It leaves the ticket open; the user decides what happens next. Decided by the user on
  2026-10-01.
- **The fan-out stops being a separate route.** Several tickets with no accepted intent run
  the shared steps, several at once. One stop covers the batch: the agent shows which tickets
  run in parallel, which run in order because they share files, the plan for each, and who
  builds each. Each ticket then gets its own worktree, the check, the review from another
  family, and its own pull request. Parallel builds still go to workers or subagents, because
  one driver cannot build several tickets at once. `parallel.md` shrinks to how to split and
  run a batch, with no review rule of its own. Decided by the user on 2026-10-01.
- **The two kinds of ticket get no name.** "Pipeline ticket" leaves the skills, the glossary,
  and the README. Where a skill needs the idea it says "a ticket from an accepted intent".
  "The pipeline" stays as the name of the whole route from `/intent` to the merge. The start
  line tells the user whether a plan stop comes. Decided by the user on 2026-10-01.
- **Every way into the work runs the same steps.** A ticket without an intent enters the
  usual route partway and runs the steps from there. A batch runs the same steps several at
  once. No entry point has a route of its own. Decided by the user on 2026-10-01, in the
  words "all agents should sing to the same hymn sheet". An ADR records this rule, because
  later work on any skill must follow it.
- **The readiness report says whether an allow rule for the worker launcher exists, and
  claims nothing more about auto mode.** A script cannot see the permission mode, and the
  classifier can refuse an allowed command. Settled by the agent on 2026-10-01 from recon.

## Affected users and systems

- `skills/general/implement/SKILL.md` and its references `pipeline.md`, `parallel.md`,
  `integrate.md`, and `worker-contract.md`.
- `skills/general/implement/scripts/worker.py`.
- `skills/general/reviewing-changes/SKILL.md`, which `implement` stops offering.
- `skills/general/implement/scripts/gitflow.sh`: the commit test and the clean-tree check.
- `skills/general/implement/references/pr-body.md`, ADR 0013, and ADR 0018.
- `README.md`: the cheat sheet, "Which skill when", and "What magito promises".
- A new thin skill for roster care.
- `scripts/eval-implement.sh`, `scripts/eval-integrate.sh`, and the stdlib tests for
  `gitflow.sh` and `worker.py`. They encode today's two routes and must change with them.
- `docs/agents/GLOSSARY.md`: the entries for "pipeline ticket" and "escalation".
- `skills/general/to-issues/SKILL.md`, which picks the spec reviewer the same way.
- `skills/general/setup-magito/SKILL.md`, which reports the roster.
- The user on a work machine: guest mode is likely, hooks are off, and the installed tools
  differ from the home machine.

## Out of scope

- Routing a build to a worker by ticket size, and falling back between build workers when a
  quota runs out. Intent 0001 planned both. The driver builds unless the user names a worker.
- Predicting whether Claude Code's auto mode will allow a worker launch.
- Editing an existing roster. The new skill reports the line to change and stops there.
- `to-issues` for a plan with no intent. It still asks the user to approve the breakdown,
  publishes, and stops.
- `reviewing-changes` itself. It stays a skill the user can run on any diff by hand.
- Open-ended exploration with no checkable "done when". That stays with `/research`.

## Constraints

- Gates and automation belong where supervision is absent (ADR 0013). This intent moves the
  line: after plan approval nobody watches a hand-started ticket, so the gate applies there.
- A worker the user named is a spend choice. The driver never swaps it silently
  (`worker-contract.md`, "Probe and fallback").
- `~/.magito/workers.toml` is the user's file. An agent never overwrites it.
- Every workflow must work with hooks off (ADR 0012).
- magito stays ambient: it surfaces through skills and explicit gates only. Nothing a
  teammate reads, such as a pull request, carries magito's own vocabulary or bookkeeping.
- A step must do work. A step that only records something is not added.

## Open questions

- **user** — Does the work machine have a `~/.magito/workers.toml`, and which tools on it can
  act as a worker from a family other than Anthropic? This does not block the design. The
  new skill answers it on that machine.
- **agent** — Does one `python3` command that writes the review record pass Claude Code's
  classifier? `CLAUDE.md` records refusals of compound shell commands that wrote the marker.
  The ticket that builds the command must test it in a real session.

## Not yet clear

- Whether a weaker driver model follows the single path reliably once the script opens every
  run. The user's first report can also come from a model that skipped a step.
