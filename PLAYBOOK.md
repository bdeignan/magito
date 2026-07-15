# The Magito Playbook

Human-facing quick reference: which play to call in which situation, and where you
stay in the loop. **Skills are the source of truth** — this document promises
behavior, not mechanics. If it ever disagrees with a skill, the skill is right and
this file needs a PR.

## The promises

What magito guarantees you, no matter how the internals change:

1. **You own every merge.** Agents branch, commit, and open PRs; the merge is
   always yours. The review gate blocks unreviewed landings mechanically, not by
   politeness.
2. **Nothing lands unreviewed.** Every PR or merge needs a fresh two-axis review
   (Standards + Spec). Any commit after the review goes stale and re-blocks. (The
   mechanical block on raw `git merge`/`gh pr create` arms in repos opted in via
   `/setup-project`; the skills demand the review everywhere regardless.)
3. **Delegation is explicit.** No work goes to an external model unless you name a
   worker ("via omp"). Default paths never spend your prepaid credits.
4. **One approval per worker launch** (in default permission mode). A dead or
   denied worker stops loudly and asks you; nothing silently falls back onto your
   subscription.
5. **Machine-local files are yours.** `~/.magito/` (bench.toml, workers.toml,
   handoffs) is bootstrapped once with your consent and never overwritten by an
   agent on its own initiative.
6. **Staging is always explicit.** No agent bulk-stages — a hook blocks
   `git add -A` everywhere, in every repo.
7. **Costs are stated before they're incurred.** Dispatch declares its executor
   count and workers up front; magi's deliberate mode asks before convening.

## Offense — making things

| Situation | Play | Where you're in the loop |
|---|---|---|
| Vague idea, not issue-shaped yet | `/grilling`, then `/to-issues` | answer the interview; approve the breakdown |
| One well-specified issue | `/implement-issue N` | approve the plan; say "ship it" before the PR |
| One issue, big but zero-discretion | `/implement-issue N via omp` | same, plus one worker-launch approval |
| Several independent issues | `/dispatch A B via omp` | one approval per worker; merge each PR |
| New repo or project kickoff | `/setup-project` | pick the template choices |

**Play-calling discipline:** dispatch is the expensive play — don't call it when a
single `/implement-issue` gains the same yards. Route to cheap workers only what's
written to the less-capable-implementer standard (complete spec, exact commands,
zero discretion); keep judgement work in your own huddle.

## Defense — protecting the repo

| Situation | Play | Where you're in the loop |
|---|---|---|
| Anything about to land | `reviewing-changes` (agents run it; the gate enforces it) | read the two-axis report; you merge |
| Behavior needs proving, not asserting | `verifying` | — |
| A skill or doc got bloated | `/decruft` | approve the cuts |

**The defensive line plays every snap without being called:** `staging-guard`
blocks bulk staging, `review-gate` blocks unreviewed merges and PRs. If a landing
is blocked, that's the system working — review, then retry.

## Special teams

| Situation | Play | Where you're in the loop |
|---|---|---|
| Oracle-free decision, quick read | `/magi <question>` (poll) | — (cheap tier, no gate) |
| Decision where being wrong is expensive | `/magi deliberate <decision>` | explicit cost consent first |
| A plan feels too smooth | `/challenging-assumptions` | verdict lands on your desk |
| Something's missing but unclear what | `/finding-lacunae` | scope questions |
| Cold session start | `/catch-up` | pick what to resume |
| Session end, work unfinished | `/handoff` | — |
| Output too dense to read | `/speaking-plainly` | — |

## Score states — playing the budget

- **Fresh quota, exploratory work** (winning): drive in-session. Delegation adds
  overhead and saves nothing that matters.
- **Subscription burning, mechanical backlog** (losing): shift implementation to
  prepaid workers — "via omp" at home, "via gemini" at work. The roster
  (`~/.magito/workers.toml`) is per-machine; worker names are your tiers
  (`omp` cheap and fast, `omp-slow` stronger, `gemini-pro` at work).
- **Unsure** (tied): call the default plays. They never delegate, never spend
  prepaid credits, and always stop at your gates.

## Every human-in-the-loop moment, in one place

Plan approval before code · "ship it" before any PR · one prompt per worker launch
· the one-time roster/bench bootstrap write · magi deliberate cost consent · every
merge. Everything else is designed to run without you — and to stop loudly the
moment it can't.

---

Update cycle: `git pull && python install.py`. When this playbook drifts from a
skill, the skill wins — fix this file.
