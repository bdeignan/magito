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

3. **Dispatch the disjoint issues.** Create each worktree as a sibling of the repo, never under `/tmp`: `git worktree add -b <branch> ../<repo-name>.worktrees/<branch>` (the `-b` form — the branch usually doesn't exist yet). Launch one executor per worktree — `haiku-executor` by default, or a shell worker the user names from `~/.magito/workers.toml` ("12 and 14 via omp, 15 via haiku"). Shell workers go through the launcher, never a hand-built command line: probe once with `python3 ../implement-issue/scripts/worker.py probe <worker>` before fan-out (degrade loudly per the contract), then launch each with `python3 ../implement-issue/scripts/worker.py run <worker> <worktree> <brief-file> [timeout]`. Write each brief to a file per [the worker contract](../implement-issue/references/worker-contract.md): the worktree path, the full spec pasted in, the verification floor in full, the staging rule, the DONE/BLOCKED protocol, and — where useful — exact repo-relative paths to in-worktree standing docs (e.g. `docs/agents/conventions.md`) instead of pasting their contents. The brief must carry the discipline — executors cannot load skills. Collect each executor's `DONE` (with its staged files) or `BLOCKED`. Background executors notify on completion — never poll, busy-wait, or schedule wakeups while one runs.

4. **Review every result.** Run `reviewing-changes` on every worktree's staged diff against its branch point — non-negotiable, for every worktree. One skill invocation covers one worktree — N worktrees means N invocations; never mark a second diff "reviewed the same way" on the strength of the first. Hand-rolling the review with your own subagents is not an invocation either — call the skill, so each review runs the current contract rather than a remembered copy of it. A manual `git diff` eyeball is not a substitute; if you catch yourself doing that instead, stop and run the skill.

5. **Combine and open PRs.** Accept a worktree's result only if step 4 produced its `reviewing-changes` two-axis result — no result, no acceptance. For each accepted result, curate the staged changes into conventional commits, push the branch, and open a PR that closes the issue — with a brief 2–4 line body summarizing what changed, not just `Closes #N`, so the squash-merge commit isn't empty. Tear down finished worktrees (`git worktree remove`); once the last one is removed, the `.worktrees` sibling dir should be empty or gone too. Surface any `BLOCKED` issue back to the user instead of guessing.

## Cost honesty

State up front exactly how many executors you're about to launch and which worker backs each. If the issues turn out to share more files than expected, say so and fall back to sequential `/implement-issue` rather than forcing parallelism that will just conflict.
