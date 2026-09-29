---
name: implement
description: Implement one or more issues end-to-end, once each has a ready definition of done. One issue runs a single sequential pass — plan (for non-trivial work), branch, build, verify, self-review, open a PR. Several independent issues fan out to a worker each. You own the git lifecycle; the human owns the merge. Do not use it to explore an idea or draft a spec — an issue with no definition of done is not ready to build; run intent or to-issues first, then come back here.
argument-hint: "one issue (number, URL, or path) for the sequential path; several, or a label, for the parallel fan-out"
---

# Implement

**First rule. If the ticket body has an `**Intent:**` line that links an intent doc whose header line says `Status: accepted`, and it also has a `Spec review:` line, it is a pipeline ticket. Never ask the user to approve the plan, never offer the review, and never wait for "ship it". Follow [`references/pipeline.md`](./references/pipeline.md) instead of steps 2 and 6 to 8 below, and stop only for an escalation named there.** Decide from the ticket, not from who called you. Every other ticket keeps the process below exactly as written: plan approval, the review offer, and "ship it."

Take an issue from spec to open PR. You own the git lifecycle; the human owns the merge. The deterministic git steps run through [`scripts/gitflow.sh`](./scripts/gitflow.sh); everything else is judgement. Tracker reads and writes go through the named operations in `docs/agents/issue-tracker.md`, which says how to perform each one in this repo — this skill never names a backend. Commands below run from your actual working directory, not the skill directory, so they address the scripts as `<skills>/implement/scripts/...` (`<skills>` is your tool's installed skills directory — `~/.claude/skills` for Claude Code, `~/.agents/skills` for most others).

**Tracker handoff.** Resolve the adapter through
[tracker-selection.md](../setup-magito/references/tracker-selection.md). When `to-issues`
passes `tracker_adapter` and `main_root`, use them for every ticket operation below and in
references, including fetching blockers and closing tickets. References to
`docs/agents/issue-tracker.md` mean that selected adapter for this run. Resolve local ticket
paths against the passed main root, not the implementation worktree. A passed adapter file
that does not exist stops the run; never fall back to a different tracker. On a rerun,
inspect existing branches and PRs before starting duplicate implementation work.

**Route on how many issues you were handed.** One issue takes the sequential path below — the default. Several *independent* issues fan out to a worker each: read [`references/parallel.md`](./references/parallel.md), loaded only when you actually have more than one. Keeping the parallel prose in a reference is deliberate — the single-issue path stays cheap, and fanning out is the expensive exception.

**Thrifty mode.** Before you name a shell worker, run `python3 <skills>/implement/scripts/worker.py workers` and name only a worker it prints. A worker absent from that output is never launched: if the user names one, say so and stop. Run `python3 <skills>/implement/scripts/worker.py thrifty`. When it prints `on`, use the cheapest subagent model the tool offers for in-session builds and reviews (`haiku` in Claude Code). This applies to the parallel path too.

## Process (one issue)

1. **Read the issue.** Perform the **fetch a ticket** operation as `docs/agents/issue-tracker.md` defines it (run `/setup-magito` if that file is missing). Read the body, acceptance criteria, and blockers — the same file's **blocking edges** section says how blockers are recorded and read back here. If a blocker is still open, stop and say so.

2. **Plan — conditionally, and announce which path you took.** Skip the plan only if BOTH hold: (a) the change is confined to one file, or is a pure config/text tweak, and (b) it needs no new test seam — verification is just running the existing suite. If so, say it explicitly — "one-liner → skipping the plan step, implementing directly" — then build. An issue with multiple acceptance criteria is never a one-liner; "well-specified" is a reason the plan will be short, not a reason to skip it. Otherwise write a short plan (the seams you will touch and how you will test them), then **stop and wait for approval — do not edit any file until the user replies.** Never skip the plan silently, and never start a non-trivial issue unplanned. Before planning non-trivial work, run reconnaissance first — the `intent` skill's [`references/recon.md`](../intent/references/recon.md) — so the plan builds on what the code already does instead of re-solving it.

3. **Branch.** `bash <skills>/implement/scripts/gitflow.sh branch <issue> <slug>` creates a `feat/`/`fix/` branch off the current base. One issue works in the current tree on its own branch — no worktree. (Worktrees are for the parallel path — see [`references/parallel.md`](./references/parallel.md).)

4. **Build.** Implement the slice, holding this floor non-negotiable at every seam — it applies even when the issue's acceptance criteria say nothing about tests; ACs are a floor, not the ceiling:
   - Red-green where the behavior is specifiable in advance — watch the test fail for the right reason first. Pin-and-guard (characterization / eval-threshold / smoke) where it is not.
   - ALWAYS invariant + schema checks at every data boundary the diff crosses: columns/dtypes/nullability, no NaN/inf where forbidden, values in range, row counts, key uniqueness, no train/test leakage.
   - Run typechecks and single test files as you go. Reach the `verifying` skill for the full method behind this floor.
   - *(Optional)* If the issue is well-specified and large enough to pollute your context, delegate the build to a worker per [references/worker-contract.md](./references/worker-contract.md): a `haiku-executor` sub-agent (Claude Code only), or a shell worker the user names from `~/.magito/workers.toml` (any driver — "via omp"). Probe a named worker first and degrade loudly, per the contract. Workers cannot load skills, so the brief carries the floor above (and may name in-worktree standing docs by exact repo-relative path instead of pasting them, where useful) and you enforce it in review of what they stage. Keep judgement-heavy or exploratory work on yourself.

5. **Commit.** `bash <skills>/implement/scripts/gitflow.sh commit "<conventional message>" <file>...` stages only the files you name, in conventional-commit form. Curate into coherent commits; never `git add -A`.

6. **Self-review — offer it, do not assume it.** The review costs real money, so ask before running it, then record the answer either way.

   Say which way you are leaning and why, then ask. **Recommend the review** when the diff touches hooks, the review or merge gate, security, or a data boundary, or when it runs past roughly 100 changed lines. **Default to skipping** on a small or docs-only diff. The user can ask for a review you did not recommend, or decline one you did. (`reviewing-changes` has its own ~30-line threshold, which decides something else: whether a review that is already happening fans out to two sub-agents or stays a single inline pass.)

   - **Reviewed** — run the `reviewing-changes` skill against the branch point. Fix what it surfaces, including any doc-staleness finding it flags, discretionary like any other finding. A doc fix lands in this same PR as a follow-up commit. That new commit stales the decision and forces a re-review, which is this same loop, not new machinery. The skill records `reviewed` itself as its last step.
   - **Skipped** — say so and move on. On an ordinary branch there is nothing to record:
     the gate applies only to branches created for an unsupervised executor (ADR 0013), and
     writing a marker here would newly gate a branch that was never gated, blocking the next
     merge. Record the skip **only if this branch already has a marker** — read
     `<main-worktree>/.magito/review-<branch-slug>` with your file-reading tool, never a
     compound shell command that builds the path, which the classifier refuses even read-only.
     If it exists, overwrite it with your file-writing tool: one line, `<sha> skipped: <reason>`.
     Read the sha, the branch, and the main worktree path with separate commands
     (`git rev-parse HEAD`, `git rev-parse --abbrev-ref HEAD`, `git worktree list --porcelain
     | head -1`) — Claude Code's classifier refuses the one-liner below but allows each of
     those and the file write. Resolve against the **main** worktree, never cwd, or a linked
     worktree gets its own marker that will not count at merge time. Fallback for tools without
     a file-writing tool:

     ```bash
     d="$(git worktree list --porcelain | head -1 | cut -d' ' -f2-)/.magito" && printf '%s skipped: %s\n' "$(git rev-parse HEAD)" "<reason>" >| "$d/review-$(git rev-parse --abbrev-ref HEAD | tr '/' '-')"
     ```

   Asking is the point, not the record. On ordinary work nothing blocks the merge either way,
   so this question is the only thing standing between the work and the base branch — and the
   user can wave it through. That is the real situation, so describe it that way rather than
   implying a gate that is not running. Where a marker does exist, the gate wants a fresh
   decision rather than a completed review, so either answer lands; never record `reviewed`
   when no review ran, since one false entry makes the whole record worthless.

7. **Run the full suite once**, and report the result honestly. A failing suite blocks the PR.

8. **Checkpoint, then land it — branch on whether this repo lands work through a PR.** That is a question about the repo's host, not about the tracker: a repo can keep its tickets in Jira and still land every change through a GitHub PR. Decide with `git remote -v` — a remote means the PR path.
   - **PR path:** show the diff and review summary, wait for explicit "ship it," then `bash <skills>/implement/scripts/gitflow.sh push` and `bash <skills>/implement/scripts/gitflow.sh pr <issue> "<title>" "<body>"` to open a PR that closes the issue. Write the PR body following [references/pr-body.md](./references/pr-body.md). PR creation stays on `gitflow.sh pr` and never routes through the tracker config (`docs/adr/0015`). **Never merge** — the PR merge button is the human's gate.
   - **No-PR path:** there is no PR to gate, so this checkpoint IS the human's gate. Show the diff and review summary, stop, and wait for explicit approval — only then `bash <skills>/implement/scripts/gitflow.sh merge` (a `--no-ff` merge into the base branch), then perform the **close a ticket** operation. **Never merge without that explicit approval.**
