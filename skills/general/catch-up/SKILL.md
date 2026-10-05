---
name: catch-up
description: Load the project's current state at the start of a session, or when asked to catch up — read the durable docs, open issues, git status, and the session journal, then summarize where things stand and what to do next. Do not use it mid-session or once the state is already loaded — it repeats work already done and breaks the flow of a task in progress.
---

# Catch Up

Rebuild context at the start of a session by working through this checklist in order,
then summarizing. Do not act yet — orient first.

Every source below resolves to exactly one status: `read`, `missing` (checked, not
there), `skipped: <reason>` (deliberately not checked), or `failed: <reason>` (checked,
the attempt errored). No source can be silently omitted from the final report — if you
did not check it, its status is `skipped`, not absent from the list.

1. Session journal: glob `.magito/journal/*.md` in the repo root and sort the matches by
   filename, descending — filenames are `YYYY-MM-DD-HHMMSS-slug-hex.md`, so a lexical
   sort is already chronological. Read the newest two files with your file-reading tool
   and show what they say. There is nothing to start or record. If the directory does not exist or has no matching files, status is
   `missing`. If a read errors, status is `failed: <the error>` — show it and move on.
   A journal failure never stops the rest of this checklist; every other source below is
   still readable on its own.

   On a tool with no glob or file-reading tool, fall back to
   `~/.magito/bin/journal read 2`, which prints the same newest-two-entries view.

   Two entries is the default because it is enough to see what landed and what was
   flagged next. Raise it when the user asks for more history, or when the newest entry
   points back at older ones — and say which N you used, so the cost is never a surprise.
2. `CLAUDE.md` / `AGENTS.md` at the repo root. If neither exists, status is `missing`.
3. `docs/agents/GLOSSARY.md` (in a multi-context repo, routing to per-area glossaries lives in `docs/agents/INDEX.md`). If it does not exist, status is
   `missing`.
4. The most recent few ADRs under `docs/adr/`. If the directory does not exist or is
   empty, status is `missing`.
5. Open tickets — perform the **list open tickets** operation the way
   `docs/agents/issue-tracker.md` defines it for this repo. That file is the whole answer
   to which tracker this repo uses and how to reach it; read it, run what it says, show
   what comes back. If the file does not exist, status is
   `skipped: no tracker configured — run /setup-magito`.
6. Git reality: the current branch, `git status`, and the last few commits.
7. Open PRs. Run `gh pr list` only when `git remote -v` shows a GitHub remote. Otherwise the status is
   `skipped: no GitHub remote`.

Then give a tight **where we are / what is next**: the current branch and whether it is
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
