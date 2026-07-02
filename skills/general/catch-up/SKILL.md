---
name: catch-up
description: Load the project's current state at the start of a session — read the durable docs, open issues, git status, and the latest handoff, then summarize where things stand and what to do next.
disable-model-invocation: true
---

# Catch Up

Rebuild context at the start of a session by reading the durable state in this order, then summarizing. Don't act yet — orient first.

1. **Instructions** — `CLAUDE.md` / `AGENTS.md` at the repo root.
2. **Domain** — `CONTEXT.md` (or `CONTEXT-MAP.md`) and the most recent few ADRs under `docs/adr/`.
3. **Work in flight** — open issues from the configured tracker (`gh issue list`, or `.scratch/`), and the last handoff for this repo at `~/.magito/handoffs/<repo-slug>.md` (repo root path with every `/` replaced by `-`), if it exists.
4. **Git reality** — the current branch, `git status`, the last few commits, and open PRs (`gh pr list`).

Then give a tight **where we are / what's next**: the current branch and whether it's clean, the issue most likely in progress, what the last handoff flagged, and the obvious next action. Surface contradictions (a handoff says X shipped but the branch shows otherwise) rather than smoothing them over. End by asking what the user wants to pick up — or, if a handoff names a clear next step, offer to start there.
