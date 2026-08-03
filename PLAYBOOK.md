# The Magito Playbook

Human-facing quick reference: which play to call in which situation, and where you
stay in the loop. **Skills are the source of truth** — this document promises
behavior, not mechanics. If it ever disagrees with a skill, the skill is right and
this file needs a PR.

## The promises

What magito guarantees you, no matter how the internals change:

1. **You own every merge.** Agents branch, commit, and open PRs; the merge is
   always yours.
2. **Nothing lands unreviewed by accident.** Every PR or merge reaches a deliberate
   choice first — the full two-axis pass (Standards + Spec), a lightweight single
   pass for small, low-risk diffs, or a knowing skip. When you are driving, skipping
   is a legitimate answer and the system asks rather than blocks. Work landed by an
   unsupervised fan-out is the exception: there every worktree gets a real review,
   because a worker's own claim to have reviewed cannot be trusted (ADR 0013).
3. **Delegation is explicit.** No work goes to an external model unless you name a
   worker ("via omp"). Default paths never spend your prepaid credits.
4. **One approval per worker launch** (in default permission mode). A dead or
   denied worker stops loudly and asks you; nothing silently falls back onto your
   subscription.
5. **Machine-local files are yours.** `~/.magito/` (bench.toml, workers.toml,
   handoffs) is bootstrapped once with your consent and never overwritten by an
   agent on its own initiative. The exception is magito-managed: `bin/` (owned by
   `install.py`) is refreshed automatically and isn't a user file.
6. **Staging is always explicit.** No agent bulk-stages — a hook blocks
   `git add -A` everywhere, in every repo.
7. **Costs are stated before they're incurred.** A fan-out declares its executor
   count and workers up front; magi's deliberate mode asks before convening.

## Offense — making things

| Situation | Play | Where you're in the loop |
|---|---|---|
| Vague idea, not issue-shaped yet | `/grilling`, then `/to-issues` | answer the interview; approve the breakdown |
| One well-specified issue | `/implement N` | approve the plan; say "ship it" before the PR |
| One issue, big but zero-discretion | `/implement N via omp` | same, plus one worker-launch approval |
| Several independent issues | `/implement A B via omp` | one approval per worker; merge each PR |
| New repo or project kickoff | `/setup-project` | pick the template choices |

**Play-calling discipline:** the parallel fan-out is the expensive play — don't call it when a
single `/implement` gains the same yards. Route to cheap workers only what's
written to the less-capable-implementer standard (complete spec, exact commands,
zero discretion); keep judgement work in your own huddle.

## Defense — protecting the repo

| Situation | Play | Where you're in the loop |
|---|---|---|
| Anything about to land | `reviewing-changes` (agents offer it; the gate wants your answer on record) | pick review or skip; read the report; you merge |
| Behavior needs proving, not asserting | `verifying` | — |
| A skill or doc got bloated | `/decruft` | approve the cuts |

**The defensive line plays every snap without being called:** `gitflow.sh` refuses
to stage in bulk or commit on the base branch, and `staging-guard` catches the same
thing on raw `git` where hooks are allowed. These are checks in the path, so they
hold in every tool — see ADR 0012.

`review-gate` blocks a merge or PR only on a branch the `/implement` fan-out created —
those branches carry a review-decision marker, and nothing else does. Work you did by
hand meets no gate (ADR 0013, ADR 0014).

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
| Heads-down a while — still on the real problem? | the weekly course-check (below) | you read the ruling; a hung/abstain vote means "on course" |

## Course correction — are you still on the right problem?

A recurring guard against *productive procrastination*: polishing legible, low-value
work (edge-case mining, gold-plating, structured procrastination) while the higher-order
question goes unresolved. This is a **composition of existing skills, not its own skill**
— deliberately so, until a few weeks of use prove it's worth wrapping.

1. **Dossier.** The week's `git log` + notes + the one higher-order goal the work was
   meant to serve. Put in a falsifiable number where you can ("what share of real inputs
   does this branch actually touch") — the check is only as good as the evidence you feed
   it.
2. **(Optional) `/grilling`.** Interview yourself to surface what you've been stepping
   around.
3. **`/magi deliberate`**, framed about the *work, not you*:
   > "Does the last week's work advance [goal X], or is it refining low-frequency cases
   > while [higher-order question Y] stays open? Evidence: [dossier]."

Run it on a **fixed cadence** (e.g. every Friday) whether or not you feel off-course —
the cadence is what catches drift you can't see from inside it. A hung or abstaining
tribunal is itself the "you're fine" signal. Each run leaves a dated dossier in the
target repo's `docs/decisions/`; enough of them become the corpus for a future tally.

## Score states — playing the budget

- **Fresh quota, exploratory work** (winning): drive in-session. Delegation adds
  overhead and saves nothing that matters.
- **Subscription burning, mechanical backlog** (losing): shift implementation to
  prepaid workers — e.g. "via omp". The roster (`~/.magito/workers.toml`) is
  per-machine, so check it for the worker names actually configured on this
  machine rather than assuming a name here.
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
