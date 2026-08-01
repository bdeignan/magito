---
name: implement-issue
description: Implement an issue end-to-end — plan (for non-trivial work), branch, build, verify, self-review, and open a PR for you to merge.
disable-model-invocation: true
argument-hint: "issue number, URL, or path"
---

# Implement Issue

Take one issue from spec to open PR in a single sequential pass. You own the git lifecycle; the human owns the merge. The deterministic git steps run through [`scripts/gitflow.sh`](./scripts/gitflow.sh) and the deterministic tracker reads/writes through [`scripts/issues.sh`](./scripts/issues.sh); everything else is judgement. Commands below run from your actual working directory, not the skill directory, so they address the scripts as `<skills>/implement-issue/scripts/...` (`<skills>` is your tool's installed skills directory — `~/.claude/skills` for Claude Code, `~/.agents/skills` for most others).

## Process

1. **Read the issue.** Fetch it from the configured tracker — `bash <skills>/implement-issue/scripts/issues.sh view <n>` in GitHub mode, or the file under `.scratch/` in local mode (run `/setup-project` if unset). Read the body, acceptance criteria, and blockers. If a blocker is still open, stop and say so.

2. **Plan — conditionally, and announce which path you took.** Skip the plan only if BOTH hold: (a) the change is confined to one file, or is a pure config/text tweak, and (b) it needs no new test seam — verification is just running the existing suite. If so, say it explicitly — "one-liner → skipping the plan step, implementing directly" — then build. An issue with multiple acceptance criteria is never a one-liner; "well-specified" is a reason the plan will be short, not a reason to skip it. Otherwise write a short plan (the seams you'll touch and how you'll test them), then **stop and wait for approval — do not edit any file until the user replies.** Never skip the plan silently, and never dive into a non-trivial issue unplanned.

3. **Branch.** `bash <skills>/implement-issue/scripts/gitflow.sh branch <issue> <slug>` creates a `feat/`/`fix/` branch off the current base. One issue works in the current tree on its own branch — no worktree. (Worktrees are for parallel work — that's `/dispatch`.)

4. **Build.** Implement the slice, holding this floor non-negotiable at every seam — it applies even when the issue's acceptance criteria say nothing about tests; ACs are a floor, not the ceiling:
   - Red-green where the behavior is specifiable in advance — watch the test fail for the right reason first. Pin-and-guard (characterization / eval-threshold / smoke) where it isn't.
   - ALWAYS invariant + schema checks at every data boundary the diff crosses: columns/dtypes/nullability, no NaN/inf where forbidden, values in range, row counts, key uniqueness, no train/test leakage.
   - Run typechecks and single test files as you go. Reach the `verifying` skill for the full method behind this floor.
   - *(Optional)* If the issue is well-specified and large enough to pollute your context, delegate the build to a worker per [references/worker-contract.md](./references/worker-contract.md): a `haiku-executor` sub-agent (Claude Code only), or a shell worker the user names from `~/.magito/workers.toml` (any driver — "via omp"). Probe a named worker first and degrade loudly, per the contract. Workers can't load skills, so the brief carries the floor above (and may name in-worktree standing docs by exact repo-relative path instead of pasting them, where useful) and you enforce it in review of what they stage. Keep judgement-heavy or exploratory work on yourself.

5. **Commit.** `bash <skills>/implement-issue/scripts/gitflow.sh commit "<conventional message>" <file>...` stages only the files you name, in conventional-commit form. Curate into coherent commits; never `git add -A`.

6. **Self-review — offer it, don't assume it.** The review costs real money, so ask before running it, then record the answer either way.

   Say which way you're leaning and why, then ask. **Recommend the review** when the diff touches hooks, the review or merge gate, security, or a data boundary, or when it runs past roughly 100 changed lines. **Default to skipping** on a small or docs-only diff. The user can ask for a review you didn't recommend, or decline one you did. (`reviewing-changes` has its own ~30-line threshold, which decides something else: whether a review that is already happening fans out to two sub-agents or stays a single inline pass.)

   - **Reviewed** — run the `reviewing-changes` skill against the branch point. Fix what it surfaces, including any doc-staleness finding it flags, discretionary like any other finding. A doc fix lands in this same PR as a follow-up commit. That new commit stales the decision and forces a re-review, which is this same loop, not new machinery. The skill records `reviewed` itself as its last step.
   - **Skipped** — say so and move on. On an ordinary branch there is nothing to record:
     the gate applies only to branches created for an unsupervised executor (ADR 0013), and
     writing a marker here would newly gate a branch that was never gated, blocking the next
     merge. Record the skip **only if this branch already has a marker** — check with
     `ls "$(git worktree list --porcelain | head -1 | cut -d' ' -f2-)/.magito/review-<branch-slug>"`.
     If it exists, overwrite it with your file-writing tool: one line, `<sha> skipped: <reason>`.
     Read the sha, the branch, and the main worktree path with separate commands
     (`git rev-parse HEAD`, `git rev-parse --abbrev-ref HEAD`, `git worktree list --porcelain
     | head -1`) — Claude Code's classifier refuses the one-liner below but allows each of
     those and the file write. Resolve against the **main** worktree, never cwd, or a linked
     worktree gets its own marker that won't count at merge time. Fallback for tools without
     a file-writing tool:

     ```bash
     d="$(git worktree list --porcelain | head -1 | cut -d' ' -f2-)/.magito" && printf '%s skipped: %s\n' "$(git rev-parse HEAD)" "<reason>" >| "$d/review-$(git rev-parse --abbrev-ref HEAD | tr '/' '-')"
     ```

   Asking is the point, not the record. On ordinary work nothing blocks the merge either way,
   so this question is the only thing standing between the work and the base branch — and the
   user can wave it through. That is the real situation, so describe it that way rather than
   implying a gate that isn't running. Where a marker does exist, the gate wants a fresh
   decision rather than a completed review, so either answer lands; never record `reviewed`
   when no review ran, since one false entry makes the whole record worthless.

7. **Run the full suite once**, and report the result honestly. A failing suite blocks the PR.

8. **Checkpoint, then land it — branch on the tracker from step 1.**
   - **GitHub mode:** show the diff and review summary, wait for explicit "ship it," then `bash <skills>/implement-issue/scripts/gitflow.sh push` and `bash <skills>/implement-issue/scripts/gitflow.sh pr <issue> "<title>" "<body>"` to open a PR that closes the issue. Write the PR body following [references/pr-body.md](./references/pr-body.md). **Never merge** — the PR merge button is the human's gate.
   - **Local mode:** there's no PR to gate, so this checkpoint IS the human's gate. Show the diff and review summary, stop, and wait for explicit approval — only then `bash <skills>/implement-issue/scripts/gitflow.sh merge` (a `--no-ff` merge into the base branch), then mark the issue done in `.scratch/`. **Never merge without that explicit approval.**
