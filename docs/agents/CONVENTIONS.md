<!-- CONVENTIONS.md — agreed patterns the code does not announce. On-demand via INDEX.md,
     not auto-loaded. Same two gates as everything in this folder: not rederivable from the
     code, and stable across a pure refactor. -->

# magito — conventions

## Seams between skills

**A skill hands off to another only where the user has no decision to make.**

The pipeline in `docs/intent/0001-agentic-pipeline.md` runs on invokes: an accepted intent
calls `to-issues`, and `intent` calls `research` or `magi` in the middle of an interview when a
question needs one. Both are fine, because in neither case is there anything for the user to
decide. Where one skill needs another, ask: **does the user have a decision to make here?**

| Answer | Seam | What it looks like |
|---|---|---|
| Yes | **Recommend** | The skill finishes, then says "now run `/B`". The user types it. |
| No, and it is small | **Inline** | Not a seam at all. State the two or three rules directly, or share a file under `references/`. |
| No, and it is non-negotiable | **Invoke** | Skill A calls skill B. |

**Ask, then invoke** is the fourth shape, and it is the right one when the decision is real
but the next move belongs to the same skill. `to-issues` shows its breakdown and asks the
user to approve it when the input is not an accepted intent, and then goes on to publish.
That is not a recommend — the user never leaves the skill — and it is not a bare invoke,
because the choice was surfaced.
Reach for it when handing the user back to the prompt would only make them type their way
back in.

**Invoke is the default inside any `implement` run, as it is inside the pipeline, and recommend stays the default between skills that the user starts by hand.** `implement` runs
its review step on every ticket with no question, whether or not an accepted intent covers
the ticket — there is no decision to make, and turning the review into a recommendation
makes it skippable, which is the whole reason it is not one (ADR 0020). `implement` reaching
`verifying` is the same shape.

**The failure mode Invoke has to guard against** is the seam that is none of the three: an
automatic invocation the user did not choose and cannot see. Every skill is model-invocable
(see "Skill invocation" below), so nothing on the mechanics stops skill A from calling skill
B — the guard is judgment at the point you write the call, not a check `install.py` runs for
you. Before writing an Invoke seam, check that B's `description:` on its own would tell a
reader why the call fires. If it would not, the seam belongs in the doc, spelled out, not
buried silently in the code.

**Reuse a rule by pointing, not restating.** The seams above route *behavior* — one skill's
procedure triggering another's. Reusing a **rule** — a definition, a policy, a gate — is a
different problem. A rule has exactly one canonical home, and everything else points to it. A
paraphrase in a second place is not reuse, it is a fork: the copies drift, the wordings
diverge, and a reader finds two statements of one rule with no way to tell which is current.
That is the rot the two-gate filter exists to prevent, turned on magito's own docs.

The test is what you are reusing. **Behavior** — a procedure a skill runs — takes a seam
above. **A rule** — a definition or policy that must stay identical everywhere it appears —
gets named and linked: `docs/agents/README.md` owns the two gates,
`implement/references/worker-contract.md` owns the brief protocol, and a skill that needs one
points rather than recopies.

The one exception, and its cost: when an agent must apply a rule *at the point of decision*
mid-flow — `intent/references/recon.md` states both gates inline because promotion is judged
right there — a restatement is allowed, but as a synced copy, not a fork. Name the canonical
source and flag it "change one, change the other," the way `hooks/staging-guard.py` and
`hooks/review-gate.py` already do. The unflagged paraphrase is the failure; the flagged,
sourced copy is the accepted cost.

## Skill invocation

Every skill is model-invocable. No `SKILL.md` carries a flag that blocks the model from
starting it, or blocks one skill from calling another. The reason is the pipeline
(`docs/intent/0001-agentic-pipeline.md`, migration step 1, "Skills can call skills"): an
automated pipeline is skills calling skills, so a skill that nothing else can call cannot be
a pipeline step. `docs/adr/0016-every-skill-is-model-invocable.md` records the change and
names the flag it replaces.

With no flag to enforce the split, the `description:` field is the only thing that decides
when a skill fires. Write it to say when to use the skill, and, where a wrong trigger would
be disruptive, to say when not to as well. `handoff` names its trigger as "only when the
session is wrapping up" and its anti-trigger as "not as a running status update," because
firing on the wrong one interrupts the wrong moment.

**The spine is a habit the description encodes, not a mechanism that enforces it.** The
default workflow is still four verbs, run in order:

```
/catch-up  →  /intent  →  /implement  →  /handoff
   orient       decide        build            record
```

`/intent` spans multiple sessions on its own — a later session resumes an existing draft at its
open questions — so nothing else sits between orient and decide. The rest of the skills are
off-spine: reached deliberately when a situation calls for them, which the README section "Which skill when" lists in one line each.
Nothing stops the model from starting any of these on its own now; what keeps `catch-up` at
the start of a session and `handoff` at the end is that each one's description says so.

**A skill with no decision attached fires wherever its description matches**, not on a
spine position. `reviewing-changes` and `verifying` fire inside build; `domain-modeling`
fires inside decide and record; `speaking-plainly` fires wherever prose goes dense. That was
already true before this change — dropping the flag only removed the mechanism that also
happened to block them from being called by another skill.

## Reaching for a tool

**Never wrap a read-only operation in a script to make it "one stable command."** A permission
audit (#150) found no agent CLI charges less for a script than for the command inside it, and
the ones that inspect commands charge more — while reading a file is free on every tool. So
phrase an operation as a file read where you can, a plain native command otherwise, and reserve
wrapper scripts for work that carries real behaviour: a gate, an argument check. `issues.sh`'s
mutating verbs earn their wrapper; `list`/`view` did not, which is why the tracker doc leads
with plain `gh` for those. For the `awk`-vs-`head` split between scripts and prose, see the
comment in `gitflow.sh`'s `main_worktree`.
