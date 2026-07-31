<!-- OVERVIEW.md — project INTENT only: why this exists, the deliberate approach, and the
     alternatives deliberately rejected. NOT an architecture tour or a feature list.
     Litmus for every line: "would a pure refactor (moves code, same intent) invalidate
     this? → then cut it." Hard cap: half a page. Growing past that means you're
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
- **Stdlib-only Python.** The installer and hooks must run on a bare Python with no
  dependency step — they are plumbing, not an application.
- **Skills ask; scripts enforce; hooks are optional.** Behavior lives in prose skills an
  agent reads. Where prose keeps failing to hold a rule, the check moves into a script the
  agent already calls, which works in every tool on every machine. Hooks catch only what a
  script cannot see, and exist in one tool, so they are insurance rather than the floor. The
  core rules are also restated in a shared instruction file every tool reads.
- **Gates only where supervision is absent.** magito assumes a human in the loop and active.
  A gate that blocks that person to collect an attestation nobody reads is ceremony; the
  unsupervised fan-out is the one place it still earns its cost.
- **It has to degrade cleanly when switched off.** Removing magito should leave a
  well-documented repo, not a broken one — which makes the claim testable when a new model
  lands.

## Rejected alternatives
- **Copy files into each tool's config** — edits wouldn't be live and the copies would drift
  from the source. Symlinks keep one truth.
- **A large fixed documentation tree** (ARCHITECTURE / MAP / PATTERNS / …) — most of it
  fails the two-gate filter this very folder enforces; kept deliberately small instead.
- **Per-repo single-file handoffs** — they overwrote each other under concurrent sessions;
  replaced first by an append-only SQLite session ledger, then by the per-entry session
  journal, which removes the shared file (and later the shared database) entirely.
