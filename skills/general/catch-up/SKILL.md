---
name: catch-up
description: Load the project's current state at the start of a session — read the durable docs, open issues, git status, and the session journal, then summarize where things stand and what to do next.
disable-model-invocation: true
---

# Catch Up

Rebuild context at the start of a session by working through this checklist in order,
then summarizing. Don't act yet — orient first.

Every source below resolves to exactly one status: `read`, `missing` (checked, not
there), `skipped: <reason>` (deliberately not checked), or `failed: <reason>` (checked,
the attempt errored). No source may be silently omitted from the final report — if you
didn't check it, its status is `skipped`, not absent from the list.

1. Session journal: run `~/.magito/bin/journal read 2` — the last two sessions for this
   project. There is nothing to start or record; a session begins by reading. Show what
   it prints. If the project has no entries yet it says so plainly — that's still
   `read`, not `missing`. If the command exits non-zero, status is
   `failed: <the error>` — show it and move on. A journal failure never stops the rest
   of this checklist; every other source below is still readable on its own.

   Two entries is the default because it is enough to see what landed and what was
   flagged next. Raise it when the user asks for more history, or when the newest entry
   points back at older ones — and say which N you used, so the cost is never a surprise.
2. `CLAUDE.md` / `AGENTS.md` at the repo root. If neither exists, status is `missing`.
3. `docs/agents/GLOSSARY.md` (in a multi-context repo, routing to per-area glossaries lives in `docs/agents/INDEX.md`). If it doesn't exist, status is
   `missing`.
4. The most recent few ADRs under `docs/adr/`. If the directory doesn't exist or is
   empty, status is `missing`.
5. Open issues from the configured tracker
   (`bash <skills>/implement-issue/scripts/issues.sh list` — `<skills>` is your tool's
   installed skills directory, `~/.claude/skills` for Claude Code or `~/.agents/skills`
   for most others — or `.scratch/`). If no tracker is configured, status is
   `skipped: no tracker configured — run /setup-project`.
6. Git reality: the current branch, `git status`, and the last few commits.
7. Open PRs (`gh pr list`).

Then give a tight **where we are / what's next**: the current branch and whether it's
clean, the issue most likely in progress, what the recent journal entries flagged, and
the obvious next action. When a journal entry disagrees with live git or the tracker,
**live state wins** — treat a session's named next step as a hint to re-validate against
the tracker, not as ground truth. Surface the contradiction (an entry says X shipped but
the branch shows otherwise) rather than smoothing it over.

End the summary with one `sources:` line, listing every source's status in the order
above — journal, CLAUDE.md, docs/agents/GLOSSARY.md, ADRs, tracker, git, PRs — e.g.:

```
sources: journal=read, CLAUDE.md=read, docs/agents/GLOSSARY.md=missing, ADRs=missing, tracker=read, git=read, PRs=read
```

Then ask what the user wants to pick up — or, if a recent session names a clear next
step, offer to start there.

Adopting the journal in a project that already has its own notes or handoff habit? See
[`references/adopting-the-journal.md`](references/adopting-the-journal.md).
