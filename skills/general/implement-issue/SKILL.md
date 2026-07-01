---
name: implement-issue
description: Implement an issue end-to-end — plan (for non-trivial work), branch, build, verify, self-review, and open a PR for you to merge.
disable-model-invocation: true
argument-hint: "issue number, URL, or path"
---

# Implement Issue

Take one issue from spec to open PR in a single sequential pass. You own the git lifecycle; the human owns the merge. The deterministic git steps run through [`scripts/gitflow.sh`](./scripts/gitflow.sh); everything else is judgement.

## Process

1. **Read the issue.** Fetch it from the configured tracker (`gh` or local `.scratch/`; run `/setup-project` if unset). Read the body, acceptance criteria, and blockers. If a blocker is still open, stop and say so.

2. **Plan — conditionally.** If you could describe the whole diff in one sentence, skip straight to building. Otherwise write a short plan — the seams you'll touch and how you'll test them — and get a thumbs-up before writing code. Don't dive into a non-trivial issue unplanned.

3. **Branch.** `bash scripts/gitflow.sh branch <issue> <slug>` creates a `feat/`/`fix/` branch off the current base. One issue works in the current tree on its own branch — no worktree. (Worktrees are for parallel work — that's `/dispatch`.)

4. **Build.** Implement the slice. Reach the `verifying` skill at each seam — red-green where the behavior is specifiable, pin-and-guard where it isn't, invariants at the data boundaries. Run typechecks and single test files as you go.
   - *(Claude Code only, optional)* If the issue is well-specified and large enough to pollute your context, delegate the implementation to a `haiku-executor` sub-agent and review what it stages. Keep judgement-heavy or exploratory work on yourself.

5. **Commit.** `bash scripts/gitflow.sh commit "<conventional message>" <file>...` stages only the files you name, in conventional-commit form. Curate into coherent commits; never `git add -A`.

6. **Self-review.** Run the `reviewing-changes` skill against the branch point before involving the human. Fix what it surfaces.

7. **Run the full suite once**, and report the result honestly. A failing suite blocks the PR.

8. **Checkpoint, then PR.** Show the diff and the review summary, and wait for "ship it." Then `bash scripts/gitflow.sh push` and `bash scripts/gitflow.sh pr <issue> "<title>"` to open a PR that closes the issue. **Never merge** — that is the human's gate.
