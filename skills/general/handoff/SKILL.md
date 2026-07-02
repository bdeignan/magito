---
name: handoff
description: Compact the current session into a handoff document in the OS temp dir so a fresh agent — or future you — can continue the work.
disable-model-invocation: true
argument-hint: "what the next session will focus on"
---

# Handoff

Write a handoff document so a fresh session can continue without re-deriving everything. Save it to a durable, deterministic path **outside the workspace**: `~/.magito/handoffs/<repo-slug>.md`, where `<repo-slug>` is the repo root's absolute path with every `/` replaced by `-` (e.g. `/Users/you/code/proj` → `-Users-you-code-proj.md`). Create `~/.magito/handoffs/` if needed, and overwrite any existing handoff for this repo (latest-wins). Don't use the OS temp dir (it's cleared after a few days and on reboot) and don't write into the workspace (it risks being committed).

A good handoff is a condensed brief, not a transcript: **objective**, **current state**, **next steps**, **open threads / decisions still pending**, and a **suggested skills** section naming what the next session should invoke. Keep it tight — the next agent reads this to orient, not to relive the session.

- **Don't duplicate artifacts.** PRDs, ADRs, issues, commits, diffs already exist — reference them by path or URL instead of restating them.
- **Capture durable decisions first.** If terms or architectural decisions crystallized this session and aren't yet written down, run `domain-modeling` to land them in `CONTEXT.md` / ADRs before wrapping — those belong in the repo, not in the handoff.
- **Redact secrets** — API keys, tokens, PII.
- If the user named a focus for the next session, tailor the doc to it.
