---
name: implement-issue
description: Implement an issue end-to-end — plan (for non-trivial work), branch, build, verify, self-review, and open a PR for you to merge.
disable-model-invocation: true
argument-hint: "issue number, URL, or path"
---

# Implement Issue

Take one issue from spec to open PR in a single sequential pass. You own the git lifecycle; the human owns the merge. The deterministic git steps run through [`scripts/gitflow.sh`](./scripts/gitflow.sh) and the deterministic tracker reads/writes through [`scripts/issues.sh`](./scripts/issues.sh); everything else is judgement.

## Process

1. **Read the issue.** Fetch it from the configured tracker — `bash scripts/issues.sh view <n>` in GitHub mode, or the file under `.scratch/` in local mode (run `/setup-project` if unset). Read the body, acceptance criteria, and blockers. If a blocker is still open, stop and say so.

2. **Plan — conditionally, and announce which path you took.** Skip the plan only if BOTH hold: (a) the change is confined to one file, or is a pure config/text tweak, and (b) it needs no new test seam — verification is just running the existing suite. If so, say it explicitly — "one-liner → skipping the plan step, implementing directly" — then build. An issue with multiple acceptance criteria is never a one-liner; "well-specified" is a reason the plan will be short, not a reason to skip it. Otherwise write a short plan (the seams you'll touch and how you'll test them), then **stop and wait for approval — do not edit any file until the user replies.** Never skip the plan silently, and never dive into a non-trivial issue unplanned.

3. **Branch.** `bash scripts/gitflow.sh branch <issue> <slug>` creates a `feat/`/`fix/` branch off the current base. One issue works in the current tree on its own branch — no worktree. (Worktrees are for parallel work — that's `/dispatch`.)

4. **Build.** Implement the slice, holding this floor non-negotiable at every seam — it applies even when the issue's acceptance criteria say nothing about tests; ACs are a floor, not the ceiling:
   - Red-green where the behavior is specifiable in advance — watch the test fail for the right reason first. Pin-and-guard (characterization / eval-threshold / smoke) where it isn't.
   - ALWAYS invariant + schema checks at every data boundary the diff crosses: columns/dtypes/nullability, no NaN/inf where forbidden, values in range, row counts, key uniqueness, no train/test leakage.
   - Run typechecks and single test files as you go. Reach the `verifying` skill for the full method behind this floor.
   - *(Claude Code only, optional)* If the issue is well-specified and large enough to pollute your context, delegate the implementation to a `haiku-executor` sub-agent and review what it stages — sub-agents can't load skills, so the floor above is yours to enforce in review. Keep judgement-heavy or exploratory work on yourself.

5. **Commit.** `bash scripts/gitflow.sh commit "<conventional message>" <file>...` stages only the files you name, in conventional-commit form. Curate into coherent commits; never `git add -A`.

6. **Self-review.** Run the `reviewing-changes` skill against the branch point before involving the human. Fix what it surfaces.

7. **Run the full suite once**, and report the result honestly. A failing suite blocks the PR.

8. **Checkpoint, then land it — branch on the tracker from step 1.**
   - **GitHub mode:** show the diff and review summary, wait for explicit "ship it," then `bash scripts/gitflow.sh push` and `bash scripts/gitflow.sh pr <issue> "<title>"` to open a PR that closes the issue. **Never merge** — the PR merge button is the human's gate.
   - **Local mode:** there's no PR to gate, so this checkpoint IS the human's gate. Show the diff and review summary, stop, and wait for explicit approval — only then `bash scripts/gitflow.sh merge` (a `--no-ff` merge into the base branch), then mark the issue done in `.scratch/`. **Never merge without that explicit approval.**
