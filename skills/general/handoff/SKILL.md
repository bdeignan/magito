---
name: handoff
description: Close the session by writing one short entry to the project's session journal, so a fresh agent — or future you — can pick the work up.
disable-model-invocation: true
argument-hint: "what the next session will focus on"
---

# Handoff

Close out the session by writing **one new file** to the project's session journal.

Get the path from `~/.magito/bin/journal name "<short-topic-slug>"` — it prints
`.magito/journal/YYYY-MM-DD-HHMM-<slug>.md`. Then create that file with your own
file-writing tool. No shell write, no approval, and nothing to clock out.

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

**Cap the whole entry at 150 words.** This is a hard number, not a nudge — the old
ledger's summaries averaged 550 tokens against a spec that already said "one short
paragraph," so the soft wording did not hold. Three tight sentences beat a transcript.
If a detail needs more room than that, it belongs in an issue, an ADR, or a commit
message. Link it instead.

If the session landed nothing worth keeping, say exactly that and stop:

```markdown
**Landed:** nothing — abandoned early.
```

## Before you write

- **Reconcile against live state.** An entry written from session memory drifts from
  reality. Check `git status`, `git log`, and the tracker
  (`bash <skills>/implement-issue/scripts/issues.sh list` — `<skills>` is your tool's
  installed skills directory, `~/.claude/skills` for Claude Code or `~/.agents/skills`
  for most others). Correct anything that disagrees; an issue you think is still open may
  have merged.
- **Capture durable decisions first.** If terms or architectural decisions crystallized
  and aren't written down yet, run `domain-modeling` to land them in
  `docs/agents/GLOSSARY.md` or an ADR **before** writing the entry. Those belong in the
  repo, not in a journal entry.
- **Don't duplicate artifacts.** Issues, PRs, ADRs, and commits already exist. Reference
  them by number or path.
- **Redact secrets** — API keys, tokens, PII.
- If the user named a focus for the next session, work it into **Next**.

Writing the file either works or it doesn't. If it fails, show the user the full entry
text along with the error, so the content isn't lost.
