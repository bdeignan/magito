<!-- OVERVIEW.md — project INTENT only: why this exists, the deliberate approach, and the
     alternatives deliberately rejected. NOT an architecture tour or a feature list.
     Litmus for every line: "would a pure refactor (moves code, same intent) invalidate
     this? → then cut it." Hard cap: half a page. Growing past that means you are
     documenting the code — stop. Auto-loaded every session. -->

# magito — overview

## Purpose
magito is one person's version-controlled configuration layer for agentic CLIs. It keeps
skills, subagents, shared instructions, and guardrails in one repo and installs them
into whatever coding tools that person uses (Claude Code, Codex, Gemini, and others), so the
same governed behavior follows them across tools and machines. It is a miniature, portable
take on the governed multi-agent idea — not a framework built for anyone else to adopt.

## Deliberate approach
- **Install by symlink, not copy.** Each tool's native config path points back at this repo,
  so there is one source of truth and editing a skill or instruction takes effect without a
  copy step in between.
- **Stdlib-only Python.** The installer must run on a bare Python with no
  dependency step — it is plumbing, not an application.
- **Skills are prose; the user is the check.** Behavior lives in prose skills an agent reads,
  and the core rules are restated in a shared instruction file every tool reads. magito keeps
  no enforcement layer of scripts or hooks (ADR 0021). A slip shows in the diff the user reads,
  and a skill runs plain commands, as `CONVENTIONS.md`, "Commands in skills", sets out.
- **Work is supervised, and stops happen where the user can see them.** magito assumes the
  user watches every build in Claude Code Desktop and reads the diff before a pull request
  opens, except for a Low-risk ticket, whose pull request opens before the read (ADR 0021).
  So it keeps no review gate and no review marker. A skill or script stops work by refusing
  at once or by asking a question in the live session, and never with a sign-off that waits
  where the user cannot see it.
- **It has to degrade cleanly when switched off.** Removing magito should leave a
  well-documented repo, not a broken one — which makes the claim testable when a new model
  lands.

## Rejected alternatives
- **Copy files into each tool's config** — edits would not be live and the copies would drift
  from the source. Symlinks keep one truth.
- **A large fixed documentation tree** (ARCHITECTURE / MAP / PATTERNS / …) — most of it
  fails the two-gate filter this very folder enforces; kept deliberately small instead.
- **Per-repo single-file handoffs** — they overwrote each other under concurrent sessions;
  replaced first by an append-only SQLite session ledger, then by the per-entry session
  journal, which removes the shared file (and later the shared database) entirely.
