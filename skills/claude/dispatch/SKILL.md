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

3. **Dispatch the disjoint issues.** Create each worktree with `bash <skills>/implement-issue/scripts/gitflow.sh worktree add <branch>`. It prints the path it created. Use the script, not raw `git worktree add`. It picks the layout: a sibling of the repo, never under `/tmp` and never nested inside the repo. It also marks the branch as fan-out work, and that mark is the only thing that makes the review gate apply (ADR 0014). Hand-roll the `git` command instead and this fan-out lands ungated. Launch one executor per worktree — `haiku-executor` by default, or a shell worker the user names from `~/.magito/workers.toml` ("12 and 14 via omp, 15 via haiku"). Shell workers go through the launcher, never a hand-built command line: probe once with `python3 ~/.claude/skills/implement-issue/scripts/worker.py probe <worker>` before fan-out (degrade loudly per the contract), then launch each with `python3 ~/.claude/skills/implement-issue/scripts/worker.py run <worker> <worktree> <brief-file> [timeout]`. Write each brief to a file per the worker contract at `~/.claude/skills/implement-issue/references/worker-contract.md`: the worktree path, the full spec pasted in, the verification floor in full, the staging rule, the DONE/BLOCKED protocol, and — where useful — exact repo-relative paths to in-worktree standing docs (e.g. `docs/agents/conventions.md`) instead of pasting their contents. The brief must carry the discipline — executors cannot load skills. Collect each executor's `DONE` (with its staged files) or `BLOCKED`. Background executors notify on completion — never poll, busy-wait, or schedule wakeups while one runs.

4. **Commit each result, then review it — in that order.** Working inside the worktree (`cd <worktree-path>`), curate the executor's staged changes into conventional commits, then run `reviewing-changes` against the branch point.

   The order is load-bearing. `reviewing-changes` pins its decision to the current sha, so reviewing the staged diff first records the branch point, and your commits then stale it — the gate blocks the pull request every time. Committing first means the decision names the sha you will actually push. Nothing has landed at this point; the commits are local to the worktree.

   The review itself is non-negotiable, for every worktree. One skill invocation covers one worktree — N worktrees means N invocations; never mark a second diff "reviewed the same way" on the strength of the first. Hand-rolling the review with your own subagents is not an invocation either — call the skill, so each review runs the current contract rather than a remembered copy of it. A manual `git diff` eyeball is not a substitute; if you catch yourself doing that instead, stop and run the skill. `/implement-issue` offers its review as a prompt you can decline; a fan-out does not. Parallel builds are the least supervised work this system does, which is exactly where the review earns its cost.

5. **Open PRs, then tear down.** Accept a worktree's result only if step 4 produced its `reviewing-changes` two-axis result — no result, no acceptance. Push and open the PR **from inside the worktree**, through the script: `cd <worktree-path> && bash <skills>/implement-issue/scripts/gitflow.sh push`, then `gitflow.sh pr <issue> "<title>" "<body>"`. Run these from the main checkout instead and they refuse outright, because the script reads the current branch from the working directory and the main checkout is on the base branch. Write the body per `~/.claude/skills/implement-issue/references/pr-body.md`; do not leave it as only `Closes #N`. The script is where the fan-out gate actually runs, so it refuses a branch whose review decision is missing or stale. That refusal is the gate doing its job: go back to step 4, don't reach for raw `gh pr create`.

   Tear down finished worktrees with `gitflow.sh worktree remove <path>`, which uses `git worktree remove` (never `rm -rf`) and clears the branch's marker. A dirty worktree makes it refuse rather than destroy an executor's uncommitted work — read what is there before deciding to pass `--force`. Order matters: tear down **after** the PR is open, since removal clears the marker the gate reads. Once the last one is removed, the `.worktrees` sibling dir should be empty or gone too. Surface any `BLOCKED` issue back to the user instead of guessing.

## Cost honesty

State up front exactly how many executors you're about to launch and which worker backs each. If the issues turn out to share more files than expected, say so and fall back to sequential `/implement-issue` rather than forcing parallelism that will just conflict.
