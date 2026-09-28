# Intent: agentic pipeline from intent to PR

Status: accepted · Opened: 2026-09-28 · Accepted: 2026-09-28

## Problem

magito's workflow (grill, to-issues, implement, review, open a PR) puts the human in every
step by design. When coding by hand, that cost little, because the human already knew the
code. With agents writing most of the code, the human is no longer close to it, so each
review and each architecture question costs more. Delivery slows down and the human gets
buried in reviews.

## Proposed outcome

The human works at two points: the start and the end.

1. **Intent** (human and agent). Brainstorm, research, and argue until both agree on the
   change in behavior. The output is an intent doc. The human signs it off. This is gate 1.
2. **Spec and slice** (agent). The intent becomes issues. A different model attacks the spec
   before any build starts.
3. **Build loop** (agents, in parallel). One worktree per issue. Red check first, implement
   to green, light fresh-context review, fix, repeat up to a cap.
4. **Integrate** (agent). Merge the issue branches onto one integration branch, resolve
   conflicts, run the full checks, then one heavier review of the whole diff, including
   simplification.
5. **PR** (human). The human reviews and owns the merge. This is gate 2.

Between the gates, the human hears from the pipeline only on an escalation.

## Decisions so far

- **The check is the floor.** An agent reporting DONE is not verification. Every repo has
  one local check command (tests, linter, type checker) that exits non-zero on failure.
  No CI server is required.
- **An issue is not a spike or a prototype.** Every issue has a definition of done that
  another agent can verify, in one or both of two kinds:
  - a *red check*: a test or script that fails before the work and passes after it;
  - a *reviewable check*: specific criteria a reviewer verifies with file and line
    citations. Data work uses invariants, schema checks, snapshots, and metric thresholds.
- **The orchestrator verifies, not the worker.** After a worker returns, the orchestrator
  runs the check command itself. No agent-tool hooks are needed: hooks are banned at
  work, and external CLIs cannot run Claude Code hooks anyway.
- **Tests stay real.** The red run is recorded as evidence before the implementation.
  Test files are locked while the agent fixes code: the orchestrator compares the changed
  files against the red commit and rejects a fix round that edited a test. The reviewer checks whether each test
  would fail if the behavior broke. Mutation testing (`mutmut`) runs on changed files
  before a PR, not on every loop.
- **Parallel issues can touch the same files.** Worktrees isolate the work. Conflicts are
  resolved at integration: merge in dependency order, then by finish order, with
  `git rerere` on and the full checks after each merge. Issues with a real dependency
  carry a "depends on" link and run in order.
- **Escalations.** The pipeline stops and asks the human only when:
  1. the spec review finds an ambiguity the intent does not settle;
  2. an issue hits its retry cap (three review-and-fix rounds) without its check passing;
  3. passing a check would need a locked test changed, or scope beyond the issue;
  4. a merge conflict is semantic: both sides apply cleanly, but together the checks fail.
  The agent decides everything else and records it in the PR body.
- **Skills can call skills.** Drop `disable-model-invocation` and the Codex
  `allow_implicit_invocation: false` policy. An automated pipeline is skills calling skills.
- **Two repo modes.** *Owner*: magito files are committed. *Guest*: the same files in the
  same places, all listed in `.git/info/exclude`. The tools read from disk, so guest mode
  needs no second layout.
- **Per-repo settings live in `.magito/config.toml`**, excluded in every repo: mode, default
  tracker, check command, and intent location. The committed `docs/agents/issue-tracker.md`
  cannot be the source of truth in a guest repo.
- **Trackers.** Each repo sets a default: GitHub, Jira, or local. Each intent can override
  it. Local issues carry a made date and a use-by date. An expired issue is re-checked
  against the current code before it is built. It is not deleted.
- **Repair audit.** `setup-magito` becomes a re-runnable check-and-repair step with a
  readiness checklist that grows with magito. It records which magito version last
  audited each repo.
- **Workers.** A subagent and an external CLI are interchangeable workers, chosen by token
  budget, task complexity, and time. Work uses Claude Code, Gemini CLI (`gemini -p`), and
  Cursor (`agent -p --force`), not Codex. Default routing:
  1. Build with subagents in the current CLI.
  2. Review with a different model family than the builder.
  3. Match the model to the issue size, which the spec stage labels small or large.
  4. When a tool's quota runs out, fall back to the next worker on the roster.
- **Budgets live in the machine-local roster** (`~/.magito/workers.toml`). At work: Claude
  Code $600 a month, Cursor $200 a month, Gemini CLI a daily quota that costs nothing
  extra. So Gemini takes the most frequent calls (per-commit reviews, spec reviews), Claude
  Code orchestrates and builds, and Cursor is the second opinion and the fallback.
  A **thrifty mode**, switched on by the user in a session or in the roster, restricts
  every step to cheap models. magito does not track spend itself.

## Affected users and systems

- The one user of magito, at home and at work.
- Skills on the spine: `grilling`, `wayfinder`, `to-issues`, `implement`,
  `reviewing-changes`, `verifying`, `setup-magito`, `ask-magito`.
- `install.py` (invocation-policy validation, a new Cursor skills target), `gitflow.sh`,
  the review gate hooks, `docs/agents/CONVENTIONS.md`, and ADRs 0013, 0014, and 0015.

## Constraints

- Stdlib-only Python, with no runtime dependencies.
- Works in Claude Code, Gemini CLI, and Cursor. Hooks exist only in Claude Code, so they
  stay insurance, not the floor (ADR 0012).
- Free: no paid CI or services.
- The design is top-down. Existing skills are kept, merged, or removed to fit it, not the
  other way around.

- **Issue format.** Every issue, in any tracker, has: title, intent link, behavior, done
  when (a red check, a reviewable check, or both), touches (a hint for merge order, not a
  lock), depends on, out of scope, and made and use-by dates for local issues. An issue
  that cannot fill "done when" is not ready, and the spec reviewer sends it back.
- **Review is a slot, reviewed per commit.** magito does not build a review engine. The
  review step uses roborev where it is installed, triggered by command rather than a hook,
  and falls back to a fresh-context subagent review where it is not. roborev covers
  standards and simplification. The spec check (does the change do what the issue says)
  stays magito's job.

- **Skill map.**
  - Spine: `intent`, `to-issues`, `implement`.
  - `intent` is new. It absorbs `grilling` and `wayfinder`, and it also triggers when the
    user asks to be grilled. It calls `research`, `challenging-assumptions`,
    `finding-lacunae`, `domain-modeling`, and `magi` as needed.
  - `to-issues` writes issues in the agreed format, runs the spec review with a different
    model, and publishes them.
  - `implement` runs the build loop, the review slot, integration, and the PR. It absorbs
    `reviewing-changes` as the fallback reviewer, with the spec check. `decruft` becomes
    the simplification pass at integration. `verifying` stays as the builders' testing
    guide.
  - Session and repo care: `catch-up`, `handoff`, `setup-magito` (audit and repair).
  - Off-spine, unchanged: `magi`, `teach`, `speaking-plainly`, `writing-for-agents`,
    `wait-what`, `to-questionnaire`.
  - Removed: `ask-magito`. A short README section replaces it.

## Migration order

Each step is usable on its own.

0. A check command for magito (`scripts/check.sh`), so the pipeline has something that
   can fail.
1. Turn on model invocation for every skill.
2. Per-repo config (`.magito/config.toml`) and `setup-magito` as audit and repair.
3. `intent`, absorbing `grilling` and `wayfinder`, with the `docs/intent/` convention.
4. `to-issues`: the new issue format, the spec review, and local issues with use-by dates.
5. `implement`: the build loop, orchestrator-run checks, the test lock, the review slot,
   integration, escalations, and the PR body.
6. Workers: Gemini and Cursor roster entries, budgets, thrifty mode, and a Cursor skills
   target in `install.py`.
7. Clean-up: remove `ask-magito`, update the README, and write ADRs that replace the
   affected parts of ADRs 0013, 0014, and 0015.

A one-week roborev trial on a real project runs alongside, with no dependency on these
steps. The issues for steps 0 to 2 are written by hand in the new format, because the new
`to-issues` does not exist yet.
