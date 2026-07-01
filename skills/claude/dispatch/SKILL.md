---
name: dispatch
description: Implement several independent issues in parallel — partition by the file-touch graph (shared-file work runs sequentially, disjoint work runs in isolated worktrees), dispatch a scoped executor per worktree, then review, combine, and open PRs. The high-cost parallel path; use only for genuinely independent issues.
disable-model-invocation: true
argument-hint: "issue numbers, or a label to pull from"
---

# Dispatch

Run several issues at once. This is the expensive exception, not the default — parallel agents burn far more tokens and only pay off when the issues are genuinely independent and worth it. For a single issue, or dependent work, use `/implement-issue` sequentially.

The seam that makes parallelism safe: each executor's blast radius is **one worktree**, staging is its edge, and **you** — the orchestrator — own every commit, merge, and PR. Never merge to the base branch; that is the human's gate.

## Process

1. **Collect the issues.** From the numbers given, or by pulling a ready-for-agent label from the tracker. Read each spec.

2. **Build the file-touch graph.** Explore to estimate which files each issue touches. This partitions the set:
   - **Shared-file cluster** — issues that touch common files. Run these **sequentially** in the main tree (no worktree); parallel worktrees would only collide at merge, and combining their commits is trivial when serialized.
   - **Disjoint issues** — independent file sets. These can run **in parallel**, one worktree each.

3. **Dispatch the disjoint issues.** Create a worktree per issue (`git worktree add`). Launch one `haiku-executor` per worktree with a tight brief: the worktree path, the issue spec, "stage only the files you changed — never `git add -A`," and "reach the `verifying` skill at the seams." Collect each executor's `DONE` (with its staged files) or `BLOCKED`.

4. **Review every result.** Run `reviewing-changes` on each worktree's staged diff against its branch point. An executor's output is a proposal, not a commit.

5. **Combine and open PRs.** For each accepted result, curate the staged changes into conventional commits, push the branch, and open a PR that closes the issue. Tear down finished worktrees (`git worktree remove`). Surface any `BLOCKED` issue back to the user instead of guessing.

## Cost honesty

State up front roughly how many executors you're about to launch. If the issues turn out to share more files than expected, say so and fall back to sequential `/implement-issue` rather than forcing parallelism that will just conflict.
