---
name: catch-up
description: Load the project's current state at the start of a session — read the durable docs, open issues, git status, and the latest handoff, then summarize where things stand and what to do next.
disable-model-invocation: true
---

# Catch Up

Rebuild context at the start of a session by working through this checklist in order,
then summarizing. Don't act yet — orient first.

Every source below resolves to exactly one status: `read`, `missing` (checked, not
there), or `skipped: <reason>` (deliberately not checked). No source may be silently
omitted from the final report — if you didn't check it, its status is `skipped`, not
absent from the list.

1. `CLAUDE.md` / `AGENTS.md` at the repo root. If neither exists, status is `missing`.
2. `CONTEXT.md` (or `CONTEXT-MAP.md`) at the repo root. If it doesn't exist, status is
   `missing`.
3. The most recent few ADRs under `docs/adr/`. If the directory doesn't exist or is
   empty, status is `missing`.
4. Open issues from the configured tracker
   (`bash ../implement-issue/scripts/issues.sh list`, or `.scratch/`). If no tracker is
   configured, status is `skipped: no tracker configured — run /setup-project`.
5. The last handoff for this repo at `~/.magito/handoffs/<repo-slug>.md` (repo root
   path with every `/` replaced by `-`). If the file doesn't exist, status is
   `missing`, not skipped.
6. Git reality: the current branch, `git status`, and the last few commits.
7. Open PRs (`gh pr list`).

Then give a tight **where we are / what's next**: the current branch and whether it's
clean, the issue most likely in progress, what the last handoff flagged, and the
obvious next action. Surface contradictions (a handoff says X shipped but the branch
shows otherwise) rather than smoothing them over.

End the summary with one `sources:` line enumerating every source's status, in the
order above, e.g.:

```
sources: CLAUDE.md=read, CONTEXT.md=missing, ADRs=missing, tracker=read, handoff=read, git=read, PRs=read
```

Then ask what the user wants to pick up — or, if a handoff names a clear next step,
offer to start there.
