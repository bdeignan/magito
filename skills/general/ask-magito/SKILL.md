---
name: ask-magito
description: Ask which skill or flow fits your situation — a router over magito's skills, plus the promises magito makes you. Reach for it on a new machine or project, or any time you can't remember what to run.
disable-model-invocation: true
---

# Ask Magito

You don't remember every skill, so ask. This is the map: what magito guarantees you, and
what to run when.

**Skills are the source of truth.** This router promises behavior and points at skills. If it
ever disagrees with a skill, the skill is right and this file needs a PR.

## What magito guarantees you

No matter how the internals change:

1. **You own every merge.** Agents branch, commit, and open PRs; the merge is always yours.
2. **Nothing lands unreviewed by accident.** Every PR or merge reaches a deliberate choice
   first — a full two-axis review, a lightweight pass, or a knowing skip. When you are
   driving, skipping is legitimate, and the system asks rather than blocks. An unsupervised
   fan-out is the exception: every worktree gets a real review (ADR 0013).
3. **Delegation is explicit.** No work goes to an external model unless you name a worker
   ("via omp"). Default paths never spend prepaid credits.
4. **One approval per worker launch** (default permission mode). A dead or denied worker stops
   loudly; nothing silently falls back onto your subscription.
5. **Machine-local files are yours.** `~/.magito/` is bootstrapped once with your consent and
   never overwritten on an agent's own initiative. (`bin/` is the exception — `install.py`
   owns it.)
6. **Staging is always explicit.** No agent bulk-stages — a hook blocks `git add -A`
   everywhere.
7. **Costs are stated before they're incurred.** A fan-out declares its executor count and
   workers up front; magi's deliberate mode asks before convening.

**Every human-in-the-loop moment, in one place:** plan approval before code · "ship it"
before any PR · one prompt per worker launch · the one-time roster/bench bootstrap · magi
deliberate cost consent · every merge. Everything else runs without you, and stops loudly the
moment it can't.

## The main flow: idea → ship

The route most work travels — the spine, `orient → decide → build → record`.

1. **`/catch-up`** — start a session here. It rebuilds context from the journal, the tracker,
   and live git, then names the obvious next move.
2. **`/grilling`** — sharpen the idea by interview, one question at a time. It opens with a
   reconnaissance pass over the code, so questions build on what already exists instead of
   re-solving it.
3. **Branch — one issue, or many?**
   - A vague idea that isn't issue-shaped yet → **`/to-issues`** splits it into
     independently-grabbable tracer-bullet issues.
   - Already one clear issue → go straight to `/implement`.
4. **`/implement <n>`** — takes one issue from spec to open PR: plan, branch, build (holding
   the verification floor), self-review, PR. Several independent issues — **`/implement <a>
   <b>`** — fan out to a worker each, and the fan-out drives `/reviewing-changes` on every
   worktree non-negotiably. A session ends with `/handoff` (see Crossing sessions).

**When the effort is too big for one session — `/wayfinder`, between grilling and implement.**
Plain `/grilling` sharpens a plan you can hold in a single sitting. When the work is larger
than that — the destination is still foggy and settling it will take several sessions —
`/wayfinder` charts it as a **map** issue with child **decision tickets**, and you resolve one
per session until the way is clear. It's a container that hands off *to* grilling, not a rival
to it: reach for wayfinder when a single grilling would overflow the session, and for plain
grilling otherwise. Wayfinder itself says that if charting surfaces no fog, you don't need a
map — so the honest default stays one session with `/grilling` and `/to-issues`.

## Standalone

Off the main flow — reached deliberately when a situation calls for it.

- **Still on the real problem?** — the weekly course-check. Build a dossier (the week's `git
  log` plus the one higher-order goal), then run **`/magi deliberate`** framed about the
  *work, not you*. A hung or abstaining tribunal is the "you're fine" signal. It's a
  composition of skills, not its own skill — run it on a fixed cadence, since the cadence
  catches drift you can't see from inside.
- **`/decruft`** — a harsh structural review that hunts the cruft AI agents leave: dead
  fallbacks, thin wrappers, speculative generality. It proposes; you approve the cuts.
- **`/challenging-assumptions`** — an adversarial pre-mortem of a plan before you commit:
  hidden assumptions, failure modes, a ship-or-rethink verdict. Reach for it when an approach
  feels too smooth.
- **`/finding-lacunae`** — research for a missing keystone: what's absent that the field,
  constraints, or alternatives say should be there.
- **`/magi <question>`** — a three-seat tribunal for an oracle-free call. The poll is cheap
  and ungated; **`/magi deliberate`** is the expensive tier and asks for cost consent first.
- **`/reviewing-changes`** — the two-axis review (Standards + Spec) on its own, against any
  fixed point. `/implement` offers it; reach for it directly to review a branch or PR.
- **`/speaking-plainly`** — reset your writing voice, or rewrite dense text plainly without
  losing the facts.
- **`/teach`** — learn a concept over several sessions, using the current directory as a
  workspace.

## Vocabulary underneath

Model-invoked references that run *beneath* the other skills. Reach for them when the
**words**, not the process, are the problem — or let the skills above pull them in.

- **`/domain-modeling`** — sharpen the project's domain language: challenge a fuzzy term,
  resolve an overloaded word, record a hard-to-reverse decision as an ADR. It keeps
  `docs/agents/GLOSSARY.md` honest.
- **`/verifying`** — the testing discipline: find the real seam, red-green where behavior is
  specifiable, pin-and-guard where it isn't, and invariant + schema checks at every data
  boundary.

## Crossing sessions

- **`/handoff`** — at session end with work unfinished, compact the session into a
  `.magito/journal/` entry. You don't continue in place; a fresh session reads it via
  `/catch-up`.

## Precondition

**`/setup-magito`** — run before your first flow in a new repo, and re-run any time to
change a choice or repair drift. One idempotent pass over the whole system: it inventories
every config item — issue tracker, review gate, `docs/agents/`, permissions, private-state
excludes, the journal, delegation and magi rosters, Python toolchain, stale symlinks —
reports each as configured / missing / stale, then fills only the gaps. Safe to re-run; it
never overwrites a user's file without asking.

## Playing the budget

- **Fresh quota, exploratory work:** drive in-session. Delegation adds overhead and saves
  nothing that matters.
- **Subscription burning, mechanical backlog:** shift implementation to prepaid workers ("via
  omp"). The roster (`~/.magito/workers.toml`) is per-machine — check it for the names
  actually configured here rather than assuming one.
- **Unsure:** call the default plays. They never delegate, never spend prepaid credits, and
  always stop at your gates.

---

*Reviewers you can fan out to as subagents — a layer beneath the skills, invoked from within a
skill or by hand, never typed as `/commands`: `ousterhout-reviewer` (design and abstraction),
`production-safety-reviewer`, `researcher-persona`, and `haiku-executor` (the default build
worker).*
