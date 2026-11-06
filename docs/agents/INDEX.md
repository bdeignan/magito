<!-- INDEX.md — the router for docs/agents/: "working on X → read Y." Auto-loaded every
     session (imported from CLAUDE.md), so keep it a ROUTER, not a knowledge base: one line
     per destination, never content that belongs in the target file. Add a row when you add
     a doc here; delete the row when you delete the doc. New to this folder? Read README.md
     once — it explains what belongs here and why. -->

# magito — agent docs index

What is this folder and what belongs in it? See [README.md](./README.md) — read once.

## Auto-loaded every session
The `@docs/agents/INDEX.md` line in `CLAUDE.md` pulls in this INDEX, which imports the rest
of the bundle so it loads with the session:

@OVERVIEW.md
@GLOSSARY.md

(OVERVIEW — why magito exists and the deliberate approach; GLOSSARY — project vocabulary,
currently deferred, see the file.)

## Routing — working on X → read Y
| Working on / question | Read |
|---|---|
| Why magito is built this way | [OVERVIEW.md](./OVERVIEW.md) |
| How the user works day to day, and which workflow a change serves | [../WORKFLOWS.md](../WORKFLOWS.md) |
| Where work is tracked, and how to perform a tracker operation | [issue-tracker.md](./issue-tracker.md) |
| Install, symlink layout, where files map to each tool | `CLAUDE.md` — "Installing" and "Repo Layout" |
| Machine-local config (`~/.magito/`: bench, workers, `bin/`) | `CLAUDE.md` — "Machine-Local Config" |
| The session journal (per-entry files, reading and writing) | `bin/journal`, `skills/general/catch-up/references/adopting-the-journal.md` |
| Designing or changing a skill — seams, invocation, the spine | [CONVENTIONS.md](./CONVENTIONS.md) |
| Skill, hook, and agent design conventions | `CLAUDE.md` — "Skill and Agent Design Notes" |
| Why work is supervised, with no review gate or marker, and why stops happen where the user can see them | `docs/adr/0021` |
| How a skill writes a shell command, and when it can stop work | [CONVENTIONS.md](./CONVENTIONS.md) — "Commands in skills" and "Stopping work" |
| Which workers and reviewers this machine can use | `skills/general/workers/SKILL.md` |
| Why skills name tracker operations instead of `gh`, including intent overrides | `docs/adr/0015`, `docs/adr/0017` |
| Delegating a build (shell workers, worktrees) | `skills/general/implement/references/worker-contract.md` |
| Why magito keeps no worktree rules of its own (Desktop makes the worktree) | `docs/adr/0021` |
| The magi tribunal | `skills/claude/magi/SKILL.md` |
| Why a past decision was made | `docs/adr/` |

magito is a single-context repo, so there is no multi-context routing table here.
