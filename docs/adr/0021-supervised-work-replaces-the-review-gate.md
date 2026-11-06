# Supervised work replaces the review gate

Status: accepted, 2026-11-06. Supersedes ADRs 0011, 0012, 0013, 0014, 0018, 0019, and 0020.

## Context

magito grew a review gate, a review marker, a roster of worker command-line tools, an
automatic review by another model family, and a script floor (`gitflow.sh`, `issues.sh`, and
two hooks). It also grew its own worktree rules. All of it guarded work that nobody watched:
the parallel fan-out, the pipeline from an accepted intent to a pull request, and a ticket
after its plan was approved. ADRs 0011, 0013, 0014, 0018, and 0020 built that gate in steps.
ADR 0012 made the scripts its floor. ADR 0019 placed the worktrees it needed.

Intent 0010 settled that the user now watches every build in Claude Code Desktop. Intent 0011
found that the guard machinery had stopped guarding against a real risk and had started to cost
the user directly. A build session raised permission prompts from wrapper scripts, chained
commands, and bookkeeping commands, and a marker could hold a pull request until someone
recorded a review.

## Decision

**Work is supervised by default.** The user reads every diff before a pull request opens. One
exception: a Low-risk ticket opens its pull request before the user reads it.

**Stops happen where the user can see them.** A skill or script stops work with an immediate
refusal, in the same command or step, that says what is wrong and how to fix it. Or it asks
the user a question in the live session, as the plan stop and the "ready to read" stop do. It
never holds work on a sign-off that waits somewhere the user cannot see, such as a marker file
or a recorded attestation. The rule lives in `docs/agents/CONVENTIONS.md`, "Stopping work".

**These are removed:** the review gate, the review marker, the roster, `gitflow.sh`,
`issues.sh`, both hooks (`review-gate.py` and `staging-guard.py`), and magito's own worktree
rules. Desktop makes the worktree. The skills use plain `git` and `gh` commands, one per call,
as `docs/agents/CONVENTIONS.md`, "Commands in skills", sets out. The staging rule stays in the
shared instructions that every tool reads.

This ADR records the decision. The tickets built from intent 0011 remove the files one by one,
so the files named above can exist for a while after this ADR is accepted.

## Supersedes

- ADR 0011, the review gate that records a decision.
- ADR 0012, scripts as the enforcement floor. `gitflow.sh` was that floor, and it goes.
- ADR 0013, gates where supervision is absent. Supervision is now present everywhere.
- ADR 0014, the fan-out marks its own branches.
- ADR 0018, the pipeline review between the gates.
- ADR 0019, worktrees inside the repo under `.magito/worktrees/`.
- ADR 0020, every entry runs the same steps with a recorded review.

Each of those ADRs stays as a record of what was believed when it was written. Only its status
line changes.

## Costs

- A slip that a hook or a script used to catch, such as a bulk `git add`, now shows only in the
  diff the user reads before the pull request opens.
- A Low-risk pull request opens before the user reads it, so a mistake there is found in the
  pull request, not before it.
- No automatic second opinion from another model family remains in the build path. The user's
  read is the review.
