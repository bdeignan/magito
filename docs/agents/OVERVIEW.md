<!-- OVERVIEW.md — project INTENT only: why this exists, the deliberate approach, and the
     alternatives deliberately rejected. NOT an architecture tour or a feature list.
     Litmus for every line: "would a pure refactor (moves code, same intent) invalidate
     this? → then cut it." Hard cap: half a page. Growing past that means you're
     documenting the code — stop. Auto-loaded every session. -->

# magito — overview

## Purpose
magito is one person's version-controlled configuration layer for agentic CLIs. It keeps
skills, subagents, shared instructions, and guardrail hooks in one repo and installs them
into whatever coding tools that person uses (Claude Code, Codex, Gemini, and others), so the
same governed behavior follows them across tools and machines. It is a miniature, portable
take on the governed multi-agent idea — not a framework built for anyone else to adopt.

## Deliberate approach
- **Install by symlink, not copy.** Each tool's native config path points back at this repo,
  so there is one source of truth and editing a skill or instruction takes effect without a
  copy step in between.
- **Stdlib-only Python.** The installer and hooks must run on a bare Python with no
  dependency step — they are plumbing, not an application.
- **Skills are the product; hooks are the backstop.** Behavior lives in prose skills an agent
  reads. Where prose keeps failing to hold a rule (bulk-staging, landing unreviewed work), a
  hook blocks it — a skill can ask, a hook can enforce.
- **A tool-neutral floor.** The same core rules are inlined in a shared instruction file so
  tools without hooks still get the prose version.

## Rejected alternatives
- **Copy files into each tool's config** — edits wouldn't be live and the copies would drift
  from the source. Symlinks keep one truth.
- **A large fixed documentation tree** (ARCHITECTURE / MAP / PATTERNS / …) — most of it
  fails the two-gate filter this very folder enforces; kept deliberately small instead.
- **Per-repo single-file handoffs** — they overwrote each other under concurrent sessions;
  replaced by the append-only session ledger.
