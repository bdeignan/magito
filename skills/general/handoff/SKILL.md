---
name: handoff
description: Compact the current session into a short summary and clock it out into the machine-local session ledger, so a fresh agent — or future you — can continue the work.
disable-model-invocation: true
argument-hint: "what the next session will focus on"
---

# Handoff

Close out the session by running `~/.magito/bin/clock out "<summary>"`.
It records a `clock_out` row in the machine-local session ledger — there is no file to
write, and nothing lands in the workspace.

Write `<summary>` as **one short paragraph** covering three things:
1. What you finished this session.
2. What is still open, or the next step.
3. Any gotcha or surprise worth keeping.

Keep it tight — a sentence per point, not a transcript. If the session landed nothing
worth keeping, say so plainly, e.g.:

```
~/.magito/bin/clock out "abandoned, nothing landed"
```

- **Reconcile against live state before writing.** A summary written from session
  memory drifts from reality. Before clocking out, verify what you're about to claim
  against live sources — `git status`, `git log`, and the tracker
  (`bash ../implement-issue/scripts/issues.sh list`) — and correct any claim that
  disagrees (an issue you think is still open may have merged).
- **Capture durable decisions first.** If terms or architectural decisions crystallized
  this session and aren't yet written down, run `domain-modeling` to land them in
  `CONTEXT.md` / ADRs **before** clocking out — those belong in the repo, not in the
  summary.
- **Don't duplicate artifacts.** PRDs, ADRs, issues, commits, diffs already exist —
  reference them by path or URL instead of restating them.
- **Redact secrets** — API keys, tokens, PII.
- If the user named a focus for the next session, work it into the "what's still open"
  sentence.
