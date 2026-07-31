<!-- CONVENTIONS.md — agreed patterns the code doesn't announce. On-demand via INDEX.md,
     not auto-loaded. Same two gates as everything in this folder: not rederivable from the
     code, and stable across a pure refactor. -->

# magito — conventions

## Seams between skills

**Skills chain at their ends, not in their middles.**

Where one skill needs another, ask: **does the user have a decision to make here?**

| Answer | Seam | What it looks like |
|---|---|---|
| Yes | **Recommend** | The skill finishes, then says "now run `/B`". The user types it. |
| No, and it's small | **Inline** | Not a seam at all. State the two or three rules directly, or share a file under `references/`. |
| No, and it's non-negotiable | **Invoke** | Skill A calls skill B. |

**Ask, then invoke** is the fourth shape, and it is the right one when the decision is real
but the next move belongs to the same skill. `implement-issue` names its recommendation,
asks, and then runs `reviewing-changes` or records the skip. That is not a recommend — the
user never leaves the skill — and it is not a bare invoke, because the choice was surfaced.
Reach for it when handing the user back to the prompt would only make them type their way
back in.

**Invoke is the narrow case and has to earn itself.** `dispatch` invokes `reviewing-changes`
on every worktree and calls it non-negotiable — there is no decision to make, and turning it
into a recommendation would make it skippable, which is the whole reason it is not one.
`implement-issue` reaching `verifying` is the same shape.

**Before writing skill A to invoke skill B, check that B does not carry
`disable-model-invocation`.** That field blocks every model invocation, including one skill
calling another:

```
Skill catch-up cannot be used with Skill tool due to disable-model-invocation
```

A user-invoked skill can call a model-invocable one — `handoff` calls `domain-modeling` this
way. The reverse fails. This check is cheap and skipping it has already produced one skill
written against a seam that could not exist.

**The failure mode this rule prevents** is the seam that is none of the three: an automatic
invocation the user did not choose and cannot see. That is not a correctness bug, it is a
memorability bug. You remember what you type. A system that chains itself invisibly teaches
nothing about its own shape, and a system you cannot hold in your head is one you stop
reaching for.

## Skill invocation

A skill is either **user-invoked** (`disable-model-invocation: true`) or **model-invocable**.
The split follows from the seam rule, and the test is whether the skill is a step or part of
a step.

**User-invoked — the workflow you drive.** The default path is four verbs:

```
/catch-up  →  /grilling  →  /implement-issue  →  /handoff
   orient       decide          build             record
```

`/wayfinder` sits between orient and decide when the work is too big for one session, and
hands back to `/grilling` per ticket. The rest of the user-invoked skills are off-spine:
reached deliberately when a situation calls for them. `PLAYBOOK.md` covers situation → play;
the spine is what happens when no special situation applies.

**Model-invocable — parts of a step, never stations on the line.** `reviewing-changes` and
`verifying` fire inside build. `domain-modeling` fires inside decide and record.
`speaking-plainly` fires wherever prose goes dense. You never type them because there is
nothing to decide.

That is the real reason those keep model invocation, better than "something calls them": a
skill with no decision attached is not a step, so there is nothing for the user to enter.
