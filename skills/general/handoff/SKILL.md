---
name: handoff
description: Closes the session by writing one short entry to the project's session journal, so a fresh agent, or the user later, can pick the work up. Use only when the session is wrapping up. Do not use it mid-session or as a running status update: an entry written early misses what still happens, and one per task turns the journal into noise.
argument-hint: "what the next session will focus on"
---

# Handoff

Close out the session by writing **one new file** to the project's session journal.

Compose the filename yourself: `.magito/journal/YYYY-MM-DD-HHMMSS-<slug>-<hex>.md` in the
repo root, where the timestamp is the current date and time and `<hex>` is six hex digits
you pick to keep the name unique. Create that file directly with your file-writing tool.
No shell call and no approval.

On a tool with no file-writing tool, fall back to `~/.magito/bin/journal name
"<short-topic-slug>"`, which prints this same filename format, then write there some
other way.

Pick the slug from what the session was *about* (`journal-replaces-ledger`,
`fix-heredoc-parsing`), not from a random name. The filename is the first thing the next
session sees.

## The entry

```markdown
# 2026-07-28 · journal replaces the ledger

**Landed:** ...
**Next:** ...
**Gotcha:** ...
```

**Aim for 200 words; 300 is a hard ceiling.**

**Spend the budget on the gotcha.** Landed and Next are a sentence or two each. The
gotcha is the part with durable value, and gotchas are specific: "worker reports cannot be
trusted" is nearly worthless next to "the worker claimed a prior DONE report that never
existed, so judge the diff yourself." Vague is not the same as brief.

Past 300 words you are writing a transcript. If a detail needs that much room it belongs
in an issue, an ADR, or a commit message — link it instead.

If the session landed nothing worth keeping, say exactly that and stop:

```markdown
**Landed:** nothing — abandoned early.
```

## Before you write

- **Reconcile against live state.** An entry written from session memory drifts from
  reality. Check `git status`, `git log`, and the tracker — the **list open tickets**
  operation, performed the way `docs/agents/issue-tracker.md` defines it for this repo.
  Correct anything that disagrees; a ticket you think is still open may have merged.
- **Capture durable decisions first.** If terms or architectural decisions crystallized
  and are not written down yet, run `domain-modeling` to land them in
  `docs/agents/GLOSSARY.md` or an ADR **before** writing the entry. Those belong in the
  repo, not in a journal entry.
- **Do not duplicate artifacts.** Issues, PRs, ADRs, and commits already exist. Reference
  them by number or path.
- **Redact secrets** — API keys, tokens, PII.
- If the user named a focus for the next session, work it into **Next**.

Writing the file either works or it does not. If it fails, show the user the full entry
text along with the error, so the content is not lost.
