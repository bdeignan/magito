---
name: catch-up
description: Load the project's current state at the start of a session — read the durable docs, open issues, git status, and the session ledger, then summarize where things stand and what to do next.
disable-model-invocation: true
---

# Catch Up

Rebuild context at the start of a session by working through this checklist in order,
then summarizing. Don't act yet — orient first.

Every source below resolves to exactly one status: `read`, `missing` (checked, not
there), or `skipped: <reason>` (deliberately not checked). No source may be silently
omitted from the final report — if you didn't check it, its status is `skipped`, not
absent from the list.

1. Clock in: run `python3 ../implement-issue/scripts/clock in`. It records this
   session's `clock_in` row in the ledger and prints an orientation payload — recent
   session summaries for this repo, any unfinished sessions, and a one-line rollup of
   recent activity. Show that payload. If the repo has no earlier sessions, the payload
   says so plainly — that's still `read`, not `missing`.
2. `CLAUDE.md` / `AGENTS.md` at the repo root. If neither exists, status is `missing`.
3. `CONTEXT.md` (or `CONTEXT-MAP.md`) at the repo root. If it doesn't exist, status is
   `missing`.
4. The most recent few ADRs under `docs/adr/`. If the directory doesn't exist or is
   empty, status is `missing`.
5. Open issues from the configured tracker
   (`bash ../implement-issue/scripts/issues.sh list`, or `.scratch/`). If no tracker is
   configured, status is `skipped: no tracker configured — run /setup-project`.
6. Git reality: the current branch, `git status`, and the last few commits.
7. Open PRs (`gh pr list`).

Then give a tight **where we are / what's next**: the current branch and whether it's
clean, the issue most likely in progress, what the ledger's recent sessions flagged, and
the obvious next action. When the ledger's summaries disagree with live git or the
tracker, **live state wins** — treat a session's named next step as a hint to
re-validate against the tracker, not as ground truth. Surface the contradiction (a
summary says X shipped but the branch shows otherwise) rather than smoothing it over.

End the summary with one `sources:` line, listing every source's status in this fixed
order — CLAUDE.md, CONTEXT.md, ADRs, tracker, ledger, git, PRs — e.g.:

```
sources: CLAUDE.md=read, CONTEXT.md=missing, ADRs=missing, tracker=read, ledger=read, git=read, PRs=read
```

Then ask what the user wants to pick up — or, if a recent session names a clear next
step, offer to start there.
